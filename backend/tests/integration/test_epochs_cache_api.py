"""/epochs with the SIA cache (REQ-505, REQ-541..546, AC-514)."""

import json

import httpx
import respx

from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError
from tests.integration.conftest import M101, OBS_ID, SIA_URL, FakeCutout, FakeSia, sia_fixture
from tests.synthetic_fits import make_cutout_bytes


def sia_keys(store: InMemoryObjectStore) -> list[str]:
    return [k for k in store.objects if k.startswith("sia/")]


def test_ac514_epochs_twice_then_image_call_sia_once(make_cache_client):
    sia = FakeSia()
    client, harness = make_cache_client(sia=sia, cutout=FakeCutout(make_cutout_bytes()))

    first = client.get("/epochs", params=M101)
    second = client.get("/epochs", params=M101)
    assert first.status_code == second.status_code == 200
    assert second.json() == first.json()
    assert len(sia.calls) == 1

    image = client.get("/image", params={**M101, "observation_id": OBS_ID, "detector": "D2"})
    assert image.status_code == 200
    assert len(sia.calls) == 1  # REQ-546: /image resolution reuses the /epochs SIA cache

    (key,) = sia_keys(harness.store)
    assert key.startswith("sia/spherex_qr3/")
    payload = json.loads(harness.store.objects[key])
    assert {"fetched_at", "records", "truncated"} <= set(payload)
    assert (key, "application/json", "no-store") in harness.store.put_log  # REQ-544


def test_ac514_nearby_positions_share_the_sia_entry(make_cache_client):
    sia = FakeSia()
    client, _ = make_cache_client(sia=sia)
    a = client.get("/epochs", params={**M101, "ra": 210.80227})
    b = client.get("/epochs", params={**M101, "ra": 210.80180})
    assert a.json()["query"]["ra"] == b.json()["query"]["ra"] == 210.8015
    assert len(sia.calls) == 1


@respx.mock
def test_ac514_with_the_real_irsa_client(make_cache_client):
    """Through the real IrsaSiaClient (respx): 2 /epochs + 1 /image = 1 HTTP call to SIA."""
    route = respx.get(SIA_URL).respond(200, content=sia_fixture())
    client, _ = make_cache_client(cutout=FakeCutout(make_cutout_bytes()))
    assert client.get("/epochs", params=M101).status_code == 200
    assert client.get("/epochs", params=M101).status_code == 200
    image = client.get("/image", params={**M101, "observation_id": OBS_ID, "detector": "D2"})
    assert image.status_code == 200
    assert route.call_count == 1
    assert route.calls.last.request.url.params["POS"] == "CIRCLE 210.8015 54.348917 0.001"


def test_req505_query_echoes_normalized_position(make_cache_client):
    # 360 is not a multiple of 6.15": 359.9999 rounds to the grid point ~360, i.e. 0.0 (AC-502).
    sia = FakeSia()
    client, _ = make_cache_client(sia=sia)
    body = client.get("/epochs", params={"ra": 359.9999, "dec": 89.9999}).json()
    assert body["query"]["ra"] == 0.0
    ra, dec, *_ = sia.calls[-1]
    assert (ra, dec) == (body["query"]["ra"], body["query"]["dec"])  # echo == searched
    assert body["query"]["dec"] == 90.0


def test_req505_normalized_also_with_cache_disabled(make_client):
    sia = FakeSia()
    client = make_client(sia=sia, cache_enabled=False)
    body = client.get("/epochs", params=M101).json()
    assert (body["query"]["ra"], body["query"]["dec"]) == (210.8015, 54.348917)
    ra, dec, *_ = sia.calls[-1]
    assert (ra, dec) == (210.8015, 54.348917)


def test_epochs_store_failure_still_answers(make_cache_client):
    store = InMemoryObjectStore(fail=StorageUnavailableError("down"))
    sia = FakeSia()
    client, _ = make_cache_client(sia=sia, store=store)
    assert client.get("/epochs", params=M101).status_code == 200
    assert client.get("/epochs", params=M101).status_code == 200
    assert len(sia.calls) == 1  # L1 still serves the second one


@respx.mock
def test_epochs_upstream_errors_are_not_cached(make_cache_client):
    route = respx.get(SIA_URL).mock(return_value=httpx.Response(502))
    client, harness = make_cache_client()
    assert client.get("/epochs", params=M101).status_code == 502
    assert sia_keys(harness.store) == []
    route.mock(return_value=httpx.Response(200, content=sia_fixture()))
    assert client.get("/epochs", params=M101).status_code == 200  # the error was not cached
    assert len(sia_keys(harness.store)) == 1
