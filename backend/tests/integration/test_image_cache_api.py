"""/image with the cache (spec cache 4.2, 4.3, 4.5): InMemoryObjectStore via dependency_overrides."""

import json
from urllib.parse import parse_qs, urlsplit

import pytest

from app import processing
from app.cache.keys import sidecar_key
from app.domain.errors import EmptyImageError, UpstreamError, UpstreamTimeoutError
from app.storage import s3_store
from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError
from tests.integration.conftest import (
    API_PUBLIC_BASE_URL,
    M101,
    OBS_ID,
    STORAGE_PUBLIC_BASE_URL,
    FakeCutout,
    FakeSia,
)
from tests.synthetic_fits import make_cutout_bytes

IMAGE_PARAMS = {**M101, "observation_id": OBS_ID, "detector": "D2"}
JSON_KEYS = {
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


def image_keys(store: InMemoryObjectStore, suffix: str = "") -> list[str]:
    return sorted(k for k in store.objects if "images/" in k and k.endswith(suffix))


@pytest.fixture
def cache_client(make_cache_client):
    def factory(cutout: FakeCutout | None = None, sia: FakeSia | None = None, **kwargs):
        cutout = cutout or FakeCutout(make_cutout_bytes())
        sia = sia or FakeSia()
        client, harness = make_cache_client(sia=sia, cutout=cutout, **kwargs)
        return client, harness, sia, cutout

    return factory


# --- AC-501: normalization shares one key -------------------------------------------------


def test_ac501_nearby_ra_share_the_key(cache_client):
    client, harness, _, cutout = cache_client()
    first = client.get("/image", params={**IMAGE_PARAMS, "ra": 210.80227})
    second = client.get("/image", params={**IMAGE_PARAMS, "ra": 210.80180})

    assert first.status_code == second.status_code == 200
    assert first.headers["x-cache"] == "MISS"
    assert second.headers["x-cache"] == "HIT"
    for response in (first, second):
        assert response.headers["x-center-ra"] == "210.801500"
        assert response.headers["x-center-dec"] == "54.348917"
        assert response.headers["x-render-version"] == processing.RENDER_VERSION
        assert response.headers["cache-control"] == "public, max-age=86400"
    assert second.content == first.content
    assert len(cutout.calls) == 1
    # REQ-525: the png miss was stored in background (PNG first, then sidecar).
    assert len(image_keys(harness.store, ".png")) == 1
    assert len(image_keys(harness.store, ".json")) == 1

    other = client.get("/image", params={**IMAGE_PARAMS, "ra": 210.80250})
    assert other.status_code == 200
    assert other.headers["x-cache"] == "MISS"
    assert other.headers["x-center-ra"] == "210.803208"
    assert len(image_keys(harness.store, ".png")) == 2


def test_png_hit_headers_match_the_miss(cache_client):
    client, _, _, _ = cache_client()
    miss = client.get("/image", params=IMAGE_PARAMS)
    hit = client.get("/image", params=IMAGE_PARAMS)
    x_headers = {k: v for k, v in miss.headers.items() if k.startswith("x-") and k != "x-cache"}
    assert x_headers
    assert {k: hit.headers[k] for k in x_headers} == x_headers


def test_png_hit_with_missing_png_rerenders(cache_client):
    """Sidecar present but PNG deleted: re-render (MISS), never 500."""
    client, harness, _, cutout = cache_client()
    assert client.get("/image", params=IMAGE_PARAMS).status_code == 200
    (png_key,) = image_keys(harness.store, ".png")
    del harness.store.objects[png_key]

    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 200
    assert response.headers["x-cache"] == "MISS"
    assert len(cutout.calls) == 2
    assert png_key in harness.store.objects


# --- AC-505/506: response_format=json -----------------------------------------------------


def test_ac505_json_miss_then_hit(cache_client):
    client, harness, sia, cutout = cache_client()
    params = {**IMAGE_PARAMS, "response_format": "json"}

    first = client.get("/image", params=params)
    assert first.status_code == 200, first.text
    assert first.headers["content-type"] == "application/json"
    body = first.json()
    assert set(body) == JSON_KEYS
    assert body["cache_status"] == "miss"
    assert first.headers["x-cache"] == "MISS"
    # AC-506: both objects exist when the response arrives.
    assert harness.store.objects.keys() >= {body["key"], sidecar_key(body["key"])}
    assert body["url"] == f"{STORAGE_PUBLIC_BASE_URL}/{body['key']}"
    assert body["key"].startswith(f"images/{processing.RENDER_VERSION}/spherex_qr3/{OBS_ID}/")
    assert body["params"]["ra"] == 210.8015
    assert body["params"]["dec"] == 54.348917
    assert body["image"]["bytes"] == len(harness.store.objects[body["key"]])
    assert body["observation"]["detectors"] == ["D2"]
    assert len(body["scale"]["min"]) == len(body["scale"]["max"]) == 1
    assert body["stack"] is None

    second = client.get("/image", params=params)
    assert second.status_code == 200
    assert second.json()["cache_status"] == "hit"
    assert second.json()["url"] == body["url"]
    assert second.headers["x-cache"] == "HIT"
    assert len(sia.calls) == 1
    assert len(cutout.calls) == 1


def test_json_hit_after_png_miss(cache_client):
    client, _, _, cutout = cache_client()
    assert client.get("/image", params=IMAGE_PARAMS).headers["x-cache"] == "MISS"
    body = client.get("/image", params={**IMAGE_PARAMS, "response_format": "json"}).json()
    assert body["cache_status"] == "hit"
    assert len(cutout.calls) == 1


# --- AC-510: response_format=redirect -----------------------------------------------------


def test_ac510_redirect_hit(cache_client):
    client, harness, _, cutout = cache_client()
    params = {**IMAGE_PARAMS, "response_format": "redirect"}

    miss = client.get("/image", params=params)
    assert miss.status_code == 302
    assert miss.headers["x-cache"] == "MISS"
    (png_key,) = image_keys(harness.store, ".png")
    assert sidecar_key(png_key) in harness.store.objects  # stored before answering

    hit = client.get("/image", params=params)
    assert hit.status_code == 302
    assert hit.headers["location"] == f"{STORAGE_PUBLIC_BASE_URL}/{png_key}"
    assert hit.headers["x-cache"] == "HIT"
    assert hit.headers["cache-control"] == "public, max-age=86400"
    for header in ("x-scale-min", "x-scale-max", "x-observation-id", "x-center-ra"):
        assert header in hit.headers, header
    assert hit.headers["x-render-version"] == processing.RENDER_VERSION
    assert len(cutout.calls) == 1


# --- AC-511 / REQ-551/553: cache disabled ------------------------------------------------


@pytest.fixture
def no_storage_client(make_client, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no storage client may be built with CACHE_ENABLED=false")

    monkeypatch.setattr(s3_store, "build_s3_client", forbidden)

    def factory(cutout: FakeCutout | None = None):
        cutout = cutout or FakeCutout(make_cutout_bytes())
        client = make_client(
            sia=FakeSia(),
            cutout=cutout,
            cache_enabled=False,
            api_public_base_url=API_PUBLIC_BASE_URL,
        )
        client.follow_redirects = False
        assert client.app.state.store is None
        return client, cutout

    return factory


def _api_path(url: str) -> str:
    assert url.startswith(f"{API_PUBLIC_BASE_URL}/image?"), url
    return url.removeprefix(API_PUBLIC_BASE_URL)


def test_ac511_cache_disabled_png_is_bypass(no_storage_client):
    client, _ = no_storage_client()
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.headers["x-cache"] == "BYPASS"
    assert response.headers["x-center-ra"] == "210.801500"


def test_ac511_cache_disabled_json_points_to_the_api(no_storage_client):
    client, _ = no_storage_client()
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": "json"})
    assert response.status_code == 200
    body = response.json()
    assert body["cache_status"] == "bypass"
    assert response.headers["x-cache"] == "BYPASS"
    query = parse_qs(urlsplit(body["url"]).query)
    assert query["response_format"] == ["png"]
    assert query["ra"] == ["210.8015"]
    # The bypass URL renders the same image.
    again = client.get(_api_path(body["url"]))
    assert again.status_code == 200
    assert again.headers["content-type"] == "image/png"
    assert again.headers["x-center-ra"] == "210.801500"
    assert again.headers["x-scale-min"] == json.dumps(body["scale"]["min"][0])


def test_ac511_cache_disabled_redirect_points_to_the_api(no_storage_client):
    client, cutout = no_storage_client()
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": "redirect"})
    assert response.status_code == 302
    assert response.headers["x-cache"] == "BYPASS"
    assert response.headers["cache-control"] == "public, max-age=86400"
    location = _api_path(response.headers["location"])
    assert "response_format=png" in location
    assert cutout.calls == []  # nothing to store, so no render before the redirect
    assert client.get(location).status_code == 200


# --- REQ-552 / Review Focus 5: storage failing --------------------------------------------


@pytest.mark.parametrize("response_format", ["png", "json", "redirect"])
def test_storage_failure_on_miss_is_bypass(cache_client, response_format):
    store = InMemoryObjectStore(fail=StorageUnavailableError("connection refused"))
    client, _, _, _ = cache_client(store=store)
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": response_format})
    assert response.status_code == (302 if response_format == "redirect" else 200), response.text
    assert response.headers["x-cache"] == "BYPASS"
    if response_format == "json":
        body = response.json()
        assert body["cache_status"] == "bypass"
        assert body["url"].startswith(f"{API_PUBLIC_BASE_URL}/image?")
        assert "response_format=png" in body["url"]
    if response_format == "redirect":
        assert response.headers["location"].startswith(f"{API_PUBLIC_BASE_URL}/image?")
    assert store.objects == {}


def test_storage_generic_exception_on_json_miss_is_bypass(cache_client):
    """Not only StorageUnavailableError: any store exception degrades to BYPASS, not 500."""
    store = InMemoryObjectStore(fail=RuntimeError("boom"))
    client, _, _, _ = cache_client(store=store)
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": "json"})
    assert response.status_code == 200, response.text
    assert response.json()["cache_status"] == "bypass"


def test_ac512_breaker_opens_and_stops_calling_the_store(cache_client):
    store = InMemoryObjectStore(fail=StorageUnavailableError("down"))
    client, harness, _, _ = cache_client(store=store)
    for i in range(3):
        response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.5 + i / 10})
        assert response.status_code == 200
        assert response.headers["x-cache"] == "BYPASS"
    assert harness.guarded.breaker.is_open
    assert client.get("/health").json()["cache"]["circuit_open"] is True
    calls = len(store.calls)
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": "json"})
    assert response.json()["cache_status"] == "bypass"
    assert len(store.calls) == calls


# --- AC-519: errors are never cached ------------------------------------------------------


@pytest.mark.parametrize("response_format", ["png", "json", "redirect"])
@pytest.mark.parametrize(
    ("case", "status"),
    [
        ("not_found", 404),
        ("too_large", 422),
        ("empty", 422),
        ("bad_fits", 502),
        ("upstream", 502),
        ("timeout", 504),
    ],
)
def test_ac519_errors_store_no_image(cache_client, case, status, response_format):
    params = {**IMAGE_PARAMS, "response_format": response_format}
    cutout = FakeCutout(make_cutout_bytes())
    if case == "not_found":
        params["observation_id"] = "2026W20_2A_0464_9"
    elif case == "too_large":
        params |= {"size": 3.0, "upscale": 4}
    elif case == "empty":
        cutout = FakeCutout(b"", error=EmptyImageError("no valid pixel"))
    elif case == "bad_fits":
        cutout = FakeCutout(b"garbage")
    elif case == "upstream":
        cutout = FakeCutout(b"", error=UpstreamError("IRSA 503"))
    elif case == "timeout":
        cutout = FakeCutout(b"", error=UpstreamTimeoutError("IRSA timeout"))
    client, harness, _, _ = cache_client(cutout=cutout)

    for _ in range(2):  # the second one too: nothing cached in between
        response = client.get("/image", params=params)
        assert response.status_code == status, response.text
        assert set(response.json()["error"]) == {"code", "message", "details"}
    assert image_keys(harness.store) == []
    assert all("images/" not in key for key, *_ in harness.store.put_log)


# --- validation ---------------------------------------------------------------------------


def test_invalid_response_format_is_422(cache_client):
    client, harness, _, cutout = cache_client()
    response = client.get("/image", params={**IMAGE_PARAMS, "response_format": "webp"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [f["field"] for f in error["details"]["fields"]] == ["response_format"]
    assert cutout.calls == []
    assert harness.store.calls == []


def test_default_response_format_is_png(cache_client):
    client, _, _, _ = cache_client()
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.headers["content-type"] == "image/png"
