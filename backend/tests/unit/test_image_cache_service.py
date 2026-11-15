import asyncio
import hashlib
import json
import logging
import time

import pytest

from app.cache.keys import image_key, sidecar_key
from app.cache.lru import TTLCacheL1
from app.cache.normalize import normalize_request
from app.cache.sidecar import Sidecar
from app.cache.singleflight import SingleFlight
from app.config import Settings
from app.domain.errors import (
    EmptyImageError,
    ObservationNotFoundError,
    RequestTooLargeError,
    UpstreamError,
    UpstreamTimeoutError,
)
from app.domain.models import Collection, Detector, ImageMode, ImageRecord
from app.services.image_cache_service import (
    IMMUTABLE_CACHE_CONTROL,
    CachedPngMissingError,
    CacheOutcome,
    CacheStatus,
    ImageCacheService,
)
from app.services.image_service import ImageRequest, ImageResult
from app.storage.circuit_breaker import CircuitBreaker, GuardedStore
from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError

PNG = b"\x89PNG\r\n\x1a\nfake-image-bytes"
API = "https://api.test"
QUANTUM = 6.15


def settings(**overrides) -> Settings:
    base = {
        "_env_file": None,
        "cache_enabled": True,
        "s3_endpoint_url": "https://storage.test",
        "s3_bucket": "bucket",
        "s3_access_key_id": "id",
        "s3_secret_access_key": "secret",
        "s3_public_base_url": "https://cache.test",
        "api_public_base_url": API,
    }
    return Settings(**(base | overrides))


def record(obs: str = "2026W20_2A_0464_3", det: Detector = Detector.D2, t0: float = 61000.0):
    return ImageRecord(
        observation_id=obs,
        detector=det,
        wavelength_min_um=1.1033,
        wavelength_max_um=1.6499,
        start_mjd=t0,
        end_mjd=t0 + 0.001,
        exposure_seconds=100.0,
        center_ra=210.8,
        center_dec=54.35,
        footprint=[(210.0, 54.0), (211.0, 54.0), (211.0, 55.0)],
        access_url="https://irsa.ipac.caltech.edu/x.fits",
    )


def make_result(req: ImageRequest, png: bytes = PNG) -> ImageResult:
    rgb = req.mode == ImageMode.RGB
    anchors = tuple(record(det=d) for d in req.channels)
    n = len(anchors)
    used = tuple((a, record(obs="2026W20_2A_0464_1", det=a.detector, t0=60999.99)) for a in anchors)
    return ImageResult(
        png=png,
        width=585,
        height=585,
        valid_fraction=0.98213,
        vmins=(0.0123,) * n,
        vmaxs=(4.5678,) * n,
        upscale=1,
        pixel_scale_arcsec=6.15,
        reference=anchors[0],
        anchors=anchors,
        timings_ms={},
        mode=ImageMode.RGB if rgb else ImageMode.SINGLE,
        stack=req.stack,
        used_frames=used if req.stack else tuple((a,) for a in anchors),
    )


class FakeImageService:
    """Counts renders; the semaphore mimics ImageService.render's MAX_CONCURRENT_RENDERS slot."""

    def __init__(self, delay: float = 0.0, error: Exception | None = None, png: bytes = PNG):
        self.delay = delay
        self.error = error
        self.png = png
        self.calls: list[ImageRequest] = []
        self.semaphore_acquisitions = 0
        self.started = asyncio.Event()
        self._semaphore = asyncio.Semaphore(1)

    async def render(self, req: ImageRequest) -> ImageResult:
        self.calls.append(req)
        self.started.set()
        async with self._semaphore:
            self.semaphore_acquisitions += 1
            if self.delay:
                await asyncio.sleep(self.delay)
            if self.error is not None:
                raise self.error
            return make_result(req, self.png)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def request(**overrides) -> ImageRequest:
    base = {
        "ra": 210.80227,
        "dec": 54.34895,
        "observation_id": "2026W20_2A_0464_3",
        "collection": Collection.QR3,
        "detector": Detector.D2,
    }
    return ImageRequest(**(base | overrides))


def build(store=None, render=None, cfg=None, clock=None):
    render = render or FakeImageService()
    cfg = cfg or settings()
    l1 = TTLCacheL1(max_items=64, default_ttl=3600, clock=clock)
    service = ImageCacheService(render, store, l1, SingleFlight(), cfg)
    return service, render


def keys_for(req: ImageRequest, prefix: str = "") -> tuple[str, str]:
    png_key = image_key(normalize_request(req, QUANTUM), prefix)
    return png_key, sidecar_key(png_key)


async def json_lookup(service: ImageCacheService, req: ImageRequest) -> CacheOutcome:
    return await service.lookup_or_render(req, need_png=False, persist_before_return=True)


async def png_lookup(service: ImageCacheService, req: ImageRequest) -> CacheOutcome:
    return await service.lookup_or_render(req, need_png=True, persist_before_return=False)


# --- AC-505 / AC-506 / AC-501: miss -> hit ------------------------------------------------


async def test_ac505_json_miss_then_hit_same_url_render_once():
    store = InMemoryObjectStore()
    service, render = build(store)

    first = await json_lookup(service, request())
    second = await json_lookup(service, request())

    assert first.status == CacheStatus.MISS
    assert second.status == CacheStatus.HIT
    assert first.url == second.url
    png_key, _ = keys_for(request())
    assert first.url == f"https://cache.test/{png_key}"
    assert len(render.calls) == 1


async def test_ac506_json_miss_objects_exist_when_returning():
    store = InMemoryObjectStore()
    service, _ = build(store)

    outcome = await json_lookup(service, request())

    png_key, sc_key = keys_for(request())
    assert outcome.persist is None
    assert store.objects[png_key] == PNG
    sidecar = Sidecar.model_validate_json(store.objects[sc_key])
    assert sidecar == outcome.sidecar
    assert sidecar.key == png_key
    assert sidecar.public_url == outcome.url


async def test_ac501_quantized_positions_share_key_and_hit():
    store = InMemoryObjectStore()
    service, render = build(store)

    first = await json_lookup(service, request(ra=210.80227))
    second = await json_lookup(service, request(ra=210.80180))
    other = await json_lookup(service, request(ra=210.80250))

    assert second.status == CacheStatus.HIT
    assert first.sidecar.key == second.sidecar.key
    assert second.sidecar.headers["X-Center-Ra"] == "210.801500"
    assert other.status == CacheStatus.MISS
    assert other.sidecar.key != first.sidecar.key
    assert render.calls[0].ra == 210.8015  # renders the normalized request (REQ-501)
    assert len(render.calls) == 2


async def test_render_version_change_creates_new_key(monkeypatch):
    store = InMemoryObjectStore()
    service, _ = build(store)
    first = await json_lookup(service, request())
    monkeypatch.setattr("app.processing.RENDER_VERSION", "r2")
    second = await json_lookup(service, request())
    assert second.status == CacheStatus.MISS
    assert "/images/r2/" in "/" + second.sidecar.key
    assert second.sidecar.key != first.sidecar.key
    assert second.sidecar.headers["X-Render-Version"] == "r2"


# --- AC-507: png miss returns before the upload ----------------------------------------------


async def test_ac507_png_miss_returns_before_upload_then_persists():
    store = InMemoryObjectStore(delay=1.0)
    service, _ = build(store, cfg=settings())
    png_key, sc_key = keys_for(request())

    started = time.perf_counter()
    outcome = await service.lookup_or_render(request(), need_png=True, persist_before_return=False)
    elapsed = time.perf_counter() - started

    assert outcome.status == CacheStatus.MISS
    assert outcome.png == PNG
    # 1 s of sidecar GET; uploads (2 x 1 s) are not awaited.
    assert elapsed < 1.9
    assert png_key not in store.objects
    assert outcome.persist is not None

    await outcome.persist()
    assert store.objects[png_key] == PNG
    assert sc_key in store.objects


async def test_persist_callable_never_raises_on_storage_failure(caplog):
    class FailingPut(InMemoryObjectStore):
        async def put_bytes(self, key, data, content_type, cache_control):
            raise StorageUnavailableError("down")

    service, _ = build(FailingPut())
    outcome = await png_lookup(service, request())
    with caplog.at_level(logging.ERROR):
        await outcome.persist()
    assert any(getattr(r, "event", None) == "storage_unavailable" for r in caplog.records)
    # Next request is a miss again (nothing stored).
    assert (await png_lookup(service, request())).status == CacheStatus.MISS


# --- AC-508 / Review Focus 3: incomplete or invalid sidecars ---------------------------------


async def test_ac508_png_without_sidecar_is_miss_and_rewritten():
    store = InMemoryObjectStore()
    png_key, sc_key = keys_for(request())
    store.objects[png_key] = b"stale-partial-write"
    service, render = build(store)

    outcome = await json_lookup(service, request())

    assert outcome.status == CacheStatus.MISS
    assert len(render.calls) == 1
    assert store.objects[png_key] == PNG
    assert sc_key in store.objects


@pytest.mark.parametrize(
    "payload",
    [
        b"{not json",
        b'{"schema_version": 1}',
        "schema_version_99",
        "wrong_key",
    ],
)
async def test_corrupted_or_unknown_sidecar_is_miss_with_warning(payload, caplog):
    store = InMemoryObjectStore()
    png_key, sc_key = keys_for(request())
    seed, _ = build(InMemoryObjectStore())
    good = (await json_lookup(seed, request())).sidecar
    if payload == "schema_version_99":
        data = json.loads(good.model_dump_json())
        data["schema_version"] = 99
        payload = json.dumps(data).encode()
    elif payload == "wrong_key":
        payload = good.model_copy(update={"key": "images/r1/other.png"}).model_dump_json().encode()
    store.objects[sc_key] = payload
    service, render = build(store)

    with caplog.at_level(logging.WARNING):
        outcome = await json_lookup(service, request())

    assert outcome.status == CacheStatus.MISS
    assert len(render.calls) == 1
    assert Sidecar.model_validate_json(store.objects[sc_key]).key == png_key
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(getattr(r, "event", None) == "sidecar_invalid" for r in warnings)


async def test_png_hit_with_png_missing_rerenders_and_rewrites():
    store = InMemoryObjectStore()
    service, render = build(store)
    await json_lookup(service, request())
    png_key, _ = keys_for(request())
    del store.objects[png_key]

    outcome = await service.lookup_or_render(request(), need_png=True, persist_before_return=True)

    assert outcome.status == CacheStatus.MISS
    assert outcome.png == PNG
    assert len(render.calls) == 2
    assert store.objects[png_key] == PNG


async def test_png_hit_with_corrupted_png_rerenders():
    store = InMemoryObjectStore()
    service, render = build(store)
    await json_lookup(service, request())
    png_key, _ = keys_for(request())
    store.objects[png_key] = b"truncated"

    outcome = await service.lookup_or_render(request(), need_png=True, persist_before_return=True)

    assert outcome.status == CacheStatus.MISS
    assert len(render.calls) == 2


# --- PNG hit, headers from the sidecar ------------------------------------------------------


async def test_png_hit_reads_png_from_store_and_headers_from_sidecar():
    store = InMemoryObjectStore()
    service, render = build(store)
    await json_lookup(service, request())

    hit = await png_lookup(service, request())

    assert hit.status == CacheStatus.HIT
    assert hit.layer == "l1"
    assert hit.png == PNG
    assert hit.persist is None
    headers = hit.sidecar.headers
    assert headers["X-Scale-Min"] == "0.0123"
    assert headers["X-Detector"] == "D2"
    assert headers["X-Center-Dec"] == "54.348917"
    assert headers["X-Render-Version"] == "r1"
    assert "Cache-Control" not in headers
    assert "X-Cache" not in headers
    assert len(render.calls) == 1


async def test_fetch_png_missing_raises():
    store = InMemoryObjectStore()
    service, _ = build(store)
    sidecar = (await json_lookup(service, request())).sidecar
    assert await service.fetch_png(sidecar) == PNG
    del store.objects[sidecar.key]
    with pytest.raises(CachedPngMissingError):
        await service.fetch_png(sidecar)


# --- AC-509 / REQ-532 / Review Focus 4: single-flight ---------------------------------------


async def test_ac509_ten_concurrent_render_once_and_waiters_skip_semaphore():
    store = InMemoryObjectStore()
    render = FakeImageService(delay=0.05)
    service, _ = build(store, render)

    outcomes = await asyncio.gather(*(json_lookup(service, request()) for _ in range(10)))

    assert len(render.calls) == 1
    assert render.semaphore_acquisitions == 1
    assert {o.url for o in outcomes} == {outcomes[0].url}
    assert all(o.sidecar == outcomes[0].sidecar for o in outcomes)
    assert all(o.png == PNG for o in outcomes)
    assert all(o.status == CacheStatus.MISS for o in outcomes)
    assert [k for k, *_ in store.put_log].count(outcomes[0].sidecar.key) == 1


async def test_single_flight_error_reaches_all_waiters_and_nothing_stored():
    store = InMemoryObjectStore()
    render = FakeImageService(delay=0.05, error=EmptyImageError("empty"))
    service, _ = build(store, render)

    results = await asyncio.gather(
        *(json_lookup(service, request()) for _ in range(5)), return_exceptions=True
    )

    assert len(render.calls) == 1
    assert all(isinstance(r, EmptyImageError) for r in results)
    assert len({id(r) for r in results}) == 1
    assert store.objects == {}
    render.error = None
    assert (await json_lookup(service, request())).status == CacheStatus.MISS  # entry released
    assert len(render.calls) == 2


async def test_cancelled_client_does_not_abort_render_or_store():
    store = InMemoryObjectStore()
    render = FakeImageService(delay=0.1)
    service, _ = build(store, render)

    first = asyncio.ensure_future(json_lookup(service, request()))
    await render.started.wait()
    second = asyncio.ensure_future(json_lookup(service, request()))
    await asyncio.sleep(0)
    first.cancel()

    outcome = await second
    assert outcome.status == CacheStatus.MISS
    assert len(render.calls) == 1
    await service.drain()
    png_key, sc_key = keys_for(request())
    assert png_key in store.objects and sc_key in store.objects
    with pytest.raises(asyncio.CancelledError):
        await first


async def test_cancelled_png_client_still_stores():
    store = InMemoryObjectStore()
    render = FakeImageService(delay=0.05)
    service, _ = build(store, render)

    task = asyncio.ensure_future(png_lookup(service, request()))
    await render.started.wait()
    task.cancel()
    await asyncio.sleep(0.1)
    await service.drain()

    png_key, sc_key = keys_for(request())
    assert png_key in store.objects and sc_key in store.objects


# --- AC-519 / REQ-526: errors are never cached ----------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        EmptyImageError("empty"),
        RequestTooLargeError("too large"),
        ObservationNotFoundError("missing"),
        UpstreamError("bad gateway"),
        UpstreamTimeoutError("timeout"),
    ],
)
@pytest.mark.parametrize("persist_before_return", [True, False])
async def test_ac519_render_errors_never_create_objects(error, persist_before_return):
    store = InMemoryObjectStore()
    service, _ = build(store, FakeImageService(error=error))

    with pytest.raises(type(error)):
        await service.lookup_or_render(
            request(), need_png=True, persist_before_return=persist_before_return
        )
    await service.drain()

    assert store.objects == {}
    assert store.put_log == []


# --- Write order (REQ-522) ------------------------------------------------------------------


async def test_render_and_store_writes_png_then_sidecar():
    store = InMemoryObjectStore()
    service, _ = build(store)

    sidecar = await service.render_and_store(request())

    png_key, sc_key = keys_for(request())
    assert sidecar.key == png_key
    assert store.put_log == [
        (png_key, "image/png", IMMUTABLE_CACHE_CONTROL),
        (sc_key, "application/json", IMMUTABLE_CACHE_CONTROL),
    ]
    assert IMMUTABLE_CACHE_CONTROL == "public, max-age=31536000, immutable"


async def test_sidecar_not_written_when_png_put_fails():
    class FailingPng(InMemoryObjectStore):
        async def put_bytes(self, key, data, content_type, cache_control):
            if key.endswith(".png"):
                raise StorageUnavailableError("down")
            await super().put_bytes(key, data, content_type, cache_control)

    store = FailingPng()
    service, _ = build(store)

    with pytest.raises(StorageUnavailableError):
        await service.render_and_store(request())
    assert store.objects == {}

    outcome = await json_lookup(service, request())
    assert outcome.status == CacheStatus.BYPASS
    assert store.objects == {}


async def test_render_and_store_requires_cache():
    service, _ = build(None, cfg=settings(cache_enabled=False))
    with pytest.raises(StorageUnavailableError):
        await service.render_and_store(request())


# --- AC-512 / REQ-552 / Review Focus 5: storage failures ------------------------------------


async def test_ac512_failing_store_bypasses_and_opens_breaker():
    clock = FakeClock()
    inner = InMemoryObjectStore(fail=StorageUnavailableError("connection refused"))
    breaker = CircuitBreaker(threshold=3, open_seconds=60, clock=clock)
    service, render = build(GuardedStore(inner, breaker))

    statuses = []
    for _ in range(4):
        outcome = await png_lookup(service, request())
        statuses.append(outcome.status)
        assert outcome.png == PNG
        await outcome.persist()

    assert statuses == [CacheStatus.BYPASS] * 4
    assert breaker.is_open
    assert len(inner.calls) == 3  # get, put (1st request), get (2nd) -> open
    assert len(render.calls) == 4

    clock.now += 61
    await png_lookup(service, request())
    assert len(inner.calls) == 4  # half-open: tried again


@pytest.mark.parametrize("error", [ConnectionError("reset"), StorageUnavailableError("5xx")])
async def test_review5_store_exception_in_json_flow_is_bypass_with_api_url(error):
    service, render = build(InMemoryObjectStore(fail=error))

    outcome = await json_lookup(service, request())

    assert outcome.status == CacheStatus.BYPASS
    assert outcome.layer == "none"
    assert outcome.url.startswith(f"{API}/image?")
    assert "response_format=png" in outcome.url
    assert outcome.png == PNG
    assert len(render.calls) == 1


async def test_store_fails_only_on_write_json_is_bypass():
    class FailingPut(InMemoryObjectStore):
        async def put_bytes(self, key, data, content_type, cache_control):
            raise ConnectionError("reset")

    service, _ = build(FailingPut())
    outcome = await json_lookup(service, request())
    assert outcome.status == CacheStatus.BYPASS
    assert outcome.url.startswith(f"{API}/image?")


async def test_png_hit_with_store_failing_on_png_get_is_bypass():
    class FailingPngGet(InMemoryObjectStore):
        fail_png = False

        async def get_bytes(self, key):
            if self.fail_png and key.endswith(".png"):
                raise StorageUnavailableError("down")
            return await super().get_bytes(key)

    store = FailingPngGet()
    service, render = build(store)
    await json_lookup(service, request())
    store.fail_png = True

    outcome = await png_lookup(service, request())
    assert outcome.status == CacheStatus.BYPASS
    assert outcome.png == PNG
    assert len(render.calls) == 2


# --- REQ-551 / REQ-553: cache disabled ------------------------------------------------------


async def test_cache_disabled_never_calls_store_and_bypasses():
    store = InMemoryObjectStore()
    service, render = build(store, cfg=settings(cache_enabled=False))

    outcome = await json_lookup(service, request())
    png = await png_lookup(service, request())

    assert store.calls == []
    assert outcome.status == png.status == CacheStatus.BYPASS
    assert outcome.layer == "none"
    assert outcome.persist is None and png.persist is None
    assert outcome.sidecar.public_url is None
    assert outcome.url.startswith(f"{API}/image?")
    assert len(render.calls) == 2


async def test_store_none_bypasses():
    service, _ = build(None)
    outcome = await png_lookup(service, request())
    assert outcome.status == CacheStatus.BYPASS
    assert outcome.png == PNG


def test_bypass_url_uses_normalized_params_single():
    service, _ = build(None, cfg=settings(cache_enabled=False, api_public_base_url=API + "/"))
    url = service.bypass_url(request(ra=210.80227, scale_min=0.0123456789, scale_max=4.0))
    assert url.startswith(f"{API}/image?")
    assert "&ra=210.8015&dec=54.348917&" in url
    assert url.endswith("&response_format=png")
    assert "observation_id=2026W20_2A_0464_3" in url
    assert "collection=spherex_qr3" in url
    assert "detector=D2" in url
    assert "scale_min=0.0123457" in url
    assert "percentile_low" not in url  # explicit scale -> percentiles irrelevant (REQ-504)
    assert "align=true" in url and "stack=false" in url
    assert "render_version" not in url


def test_bypass_url_rgb_and_relative_without_base():
    service, _ = build(None, cfg=settings(cache_enabled=False, api_public_base_url=None))
    url = service.bypass_url(request(mode=ImageMode.RGB, detector=None))
    assert url.startswith("/image?")
    assert "detectors=D3,D2,D1" in url
    assert "colormap" not in url
    assert "detector=" not in url.replace("detectors=", "")


# --- REQ-547: L1 ----------------------------------------------------------------------------


async def test_l1_serves_sidecar_until_ttl_then_l2():
    clock = FakeClock()
    store = InMemoryObjectStore()
    service, _ = build(store, cfg=settings(image_meta_l1_ttl_seconds=100), clock=clock)
    await json_lookup(service, request())
    calls_after_miss = len(store.calls)

    hit = await json_lookup(service, request())
    assert hit.layer == "l1"
    assert len(store.calls) == calls_after_miss  # no GET

    clock.now += 101
    hit2 = await json_lookup(service, request())
    assert hit2.layer == "l2"
    assert store.calls[calls_after_miss:] == ["get"]

    hit3 = await json_lookup(service, request())
    assert hit3.layer == "l1"  # L2 hit refills L1


# --- GUD-501: logs --------------------------------------------------------------------------


async def test_gud501_logs_status_layer_key_and_durations(caplog):
    store = InMemoryObjectStore()
    service, _ = build(store)
    with caplog.at_level(logging.INFO, logger="app.services.image_cache_service"):
        await json_lookup(service, request())
        await json_lookup(service, request())

    events = [r for r in caplog.records if getattr(r, "event", None) == "image_cache"]
    assert [(r.cache_status, r.cache_layer) for r in events] == [("miss", "none"), ("hit", "l1")]
    png_key, _ = keys_for(request())
    assert all(r.key == png_key for r in events)
    assert all(isinstance(r.lookup_ms, float) for r in events)
    assert isinstance(events[0].upload_ms, float)
    stored = [r for r in caplog.records if getattr(r, "event", None) == "image_cache_stored"]
    assert len(stored) == 1 and isinstance(stored[0].upload_ms, float)


# --- Sidecar model --------------------------------------------------------------------------


async def test_sidecar_content_and_json_response():
    service, _ = build(InMemoryObjectStore())
    sidecar = (await json_lookup(service, request())).sidecar

    assert sidecar.schema_version == 1
    assert sidecar.render_version == "r1"
    assert sidecar.created_at.endswith("Z")
    assert sidecar.image.bytes == len(PNG)
    assert sidecar.image.sha256 == hashlib.sha256(PNG).hexdigest()
    assert sidecar.image.valid_pixel_fraction == 0.9821
    assert sidecar.observation.detectors == ["D2"]
    assert sidecar.scale.min == [0.0123]
    assert sidecar.stack is None
    assert sidecar.params["ra"] == 210.8015
    assert "render_version" not in sidecar.params

    body = sidecar.to_json_response("https://cache.test/x.png", CacheStatus.HIT)
    assert body["url"] == "https://cache.test/x.png"
    assert body["cache_status"] == "hit"
    assert set(body) == {
        "url",
        "cache_status",
        "key",
        "render_version",
        "created_at",
        "params",
        "image",
        "observation",
        "scale",
        "stack",
    }
    json.dumps(body)


async def test_sidecar_rgb_stack():
    service, _ = build(InMemoryObjectStore())
    req = request(mode=ImageMode.RGB, detector=None, stack=True)
    sidecar = (await json_lookup(service, req)).sidecar

    assert sidecar.observation.detectors == ["D3", "D2", "D1"]
    assert sidecar.scale.max == [4.5678] * 3
    assert sidecar.stack.count == [2, 2, 2]
    assert sidecar.stack.observation_ids == ["2026W20_2A_0464_1", "2026W20_2A_0464_3"]
    assert sidecar.stack.truncated is False
    assert sidecar.headers["X-Stack-Count"] == "2,2,2"
    assert "X-Channel-Observation-Ids" in sidecar.headers


def test_cache_status_header_value():
    assert CacheStatus.HIT.header == "HIT"
    assert CacheStatus.BYPASS == "bypass"
