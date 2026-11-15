import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta

import pytest

from app.cache.keys import sia_key
from app.cache.lru import TTLCacheL1
from app.cache.normalize import normalize_sia_args
from app.clients.cached_sia import CachedSiaClient, serialize_sia_result
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamTimeoutError
from app.domain.models import Collection, Detector, ImageRecord, SiaResult
from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError

COLL = Collection.QR3


def make_result(truncated: bool = False) -> SiaResult:
    rec = ImageRecord(
        observation_id="obs1",
        detector=Detector.D2,
        wavelength_min_um=0.75,
        wavelength_max_um=5.0,
        start_mjd=60000.0,
        end_mjd=60000.1,
        exposure_seconds=100.0,
        center_ra=210.8,
        center_dec=54.3,
        footprint=[(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)],
        access_url="https://example.test/a.fits",
    )
    return SiaResult(records=[rec], truncated=truncated)


class FakeInner:
    def __init__(self, result=None, error=None, gate: asyncio.Event | None = None):
        self.result = result or make_result()
        self.error = error
        self.gate = gate
        self.calls = 0

    async def search(self, ra, dec, radius, collection, start_mjd=None, end_mjd=None):
        self.calls += 1
        if self.gate is not None:
            await self.gate.wait()
        if self.error is not None:
            raise self.error
        return self.result


def build(inner, store, ttl=21600):
    settings = Settings(sia_cache_ttl_seconds=ttl)
    l1 = TTLCacheL1(16, ttl)
    return CachedSiaClient(inner, store, settings, l1), settings, l1


def l2_key(settings, ra=210.8, dec=54.3, radius=0.1):
    args = normalize_sia_args(
        ra,
        dec,
        radius,
        COLL,
        None,
        None,
        settings.irsa_sia_maxrec,
        settings.position_quantum_arcsec,
    )
    return sia_key(args, settings.s3_key_prefix)


async def call(client):
    return await client.search(210.8, 54.3, 0.1, COLL)


async def test_second_call_served_from_l1():
    inner = FakeInner()
    client, _, _ = build(inner, InMemoryObjectStore())
    first = await call(client)
    second = await call(client)
    assert inner.calls == 1
    assert first == second


async def test_l2_written_with_json_no_store_and_roundtrips():
    inner = FakeInner(result=make_result(truncated=True))
    store = InMemoryObjectStore()
    client, settings, _ = build(inner, store)
    await call(client)
    key = l2_key(settings)
    assert store.put_log == [(key, "application/json", "no-store")]
    payload = json.loads(store.objects[key])
    assert payload["truncated"] is True
    assert set(payload) == {"fetched_at", "records", "truncated"}

    # new process: empty L1, same L2 => no inner call, identical result
    inner2 = FakeInner(error=UpstreamError("boom"))
    client2, _, _ = build(inner2, store)
    result = await call(client2)
    assert inner2.calls == 0
    assert result == make_result(truncated=True)
    assert isinstance(result.records[0].footprint[0], tuple)


async def test_expired_l2_refetches_and_rewrites():
    store = InMemoryObjectStore()
    inner = FakeInner()
    client, settings, _ = build(inner, store)
    key = l2_key(settings)
    old = datetime.now(UTC) - timedelta(hours=7)
    store.objects[key] = serialize_sia_result(make_result(), old)
    await call(client)
    assert inner.calls == 1
    assert [p[0] for p in store.put_log] == [key]
    fetched = datetime.fromisoformat(json.loads(store.objects[key])["fetched_at"])
    assert datetime.now(UTC) - fetched < timedelta(minutes=1)


@pytest.mark.parametrize("error", [UpstreamError("x"), UpstreamTimeoutError("t")])
async def test_stale_served_on_upstream_error(caplog, error):
    store = InMemoryObjectStore()
    inner = FakeInner(error=error)
    client, settings, _ = build(inner, store)
    key = l2_key(settings)
    store.objects[key] = serialize_sia_result(make_result(), datetime.now(UTC) - timedelta(hours=7))
    with caplog.at_level(logging.WARNING):
        result = await call(client)
    assert result == make_result()
    assert any(getattr(r, "event", None) == "sia_stale_served" for r in caplog.records)


async def test_upstream_error_without_l2_propagates():
    client, _, _ = build(FakeInner(error=UpstreamError("x")), InMemoryObjectStore())
    with pytest.raises(UpstreamError):
        await call(client)


async def test_store_none_uses_l1_and_inner_only():
    inner = FakeInner()
    client, _, _ = build(inner, None)
    await call(client)
    await call(client)
    assert inner.calls == 1


async def test_store_unavailable_never_breaks_call():
    store = InMemoryObjectStore(fail=StorageUnavailableError("down"))
    inner = FakeInner()
    client, _, _ = build(inner, store)
    assert await call(client) == make_result()
    assert await call(client) == make_result()  # L1
    assert inner.calls == 1


async def test_put_failure_is_swallowed():
    class PutFails(InMemoryObjectStore):
        async def put_bytes(self, *a, **k):
            raise StorageUnavailableError("down")

    client, _, _ = build(FakeInner(), PutFails())
    assert await call(client) == make_result()


async def test_concurrent_identical_calls_hit_inner_once():
    gate = asyncio.Event()
    inner = FakeInner(gate=gate)
    client, _, _ = build(inner, InMemoryObjectStore())
    tasks = [asyncio.create_task(call(client)) for _ in range(10)]
    await asyncio.sleep(0.01)
    gate.set()
    results = await asyncio.gather(*tasks)
    assert inner.calls == 1
    assert all(r == make_result() for r in results)


@pytest.mark.parametrize("raw", [b"not json", b'{"fetched_at": "x"}', b'{"records": 1}'])
async def test_corrupt_l2_is_a_miss(raw):
    store = InMemoryObjectStore()
    inner = FakeInner()
    client, settings, _ = build(inner, store)
    key = l2_key(settings)
    store.objects[key] = raw
    assert await call(client) == make_result()
    assert inner.calls == 1
    json.loads(store.objects[key])  # rewritten with valid JSON


async def test_nearby_positions_share_cache_entry():
    inner = FakeInner()
    client, _, _ = build(inner, InMemoryObjectStore())
    await client.search(210.8000, 54.3, 0.1, COLL)
    await client.search(210.8001, 54.3, 0.1, COLL)
    assert inner.calls == 1
