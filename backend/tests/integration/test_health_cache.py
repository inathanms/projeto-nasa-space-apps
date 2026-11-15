"""/health cache block (REQ-554, AC-521) and the storage wiring of the lifespan (CON-501)."""

import asyncio

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.storage import s3_store
from app.storage.circuit_breaker import GuardedStore
from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError
from tests.integration.conftest import CACHE_SETTINGS, M101, OBS_ID, FakeCutout, FakeSia
from tests.synthetic_fits import make_cutout_bytes


def test_ac521_health_reports_cache_without_storage_calls(make_cache_client):
    client, harness = make_cache_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["cache"] == {"enabled": True, "circuit_open": False}
    assert harness.store.calls == []


def test_ac521_health_reports_open_circuit_without_storage_calls(make_cache_client):
    store = InMemoryObjectStore(fail=StorageUnavailableError("down"))
    client, _ = make_cache_client(
        sia=FakeSia(), cutout=FakeCutout(make_cutout_bytes()), store=store
    )
    params = {**M101, "observation_id": OBS_ID, "detector": "D2"}
    for size in (0.5, 0.6, 0.7):
        assert client.get("/image", params={**params, "size": size}).status_code == 200
    calls = len(store.calls)
    body = client.get("/health").json()
    assert body["cache"] == {"enabled": True, "circuit_open": True}
    assert len(store.calls) == calls


def test_health_cache_disabled(make_client):
    body = make_client(cache_enabled=False).get("/health").json()
    assert body["cache"] == {"enabled": False, "circuit_open": False}


class RecordingClient:
    """Stands in for the boto3 client: records every attribute used."""

    def __init__(self) -> None:
        self.used: list[str] = []

    def __getattr__(self, name: str):
        self.used.append(name)
        raise AssertionError(f"unexpected storage call at startup/health: {name}")


def test_lifespan_builds_one_guarded_store_without_bucket_calls(monkeypatch):
    built: list[RecordingClient] = []

    def fake_build(settings: Settings) -> RecordingClient:
        built.append(RecordingClient())
        return built[-1]

    monkeypatch.setattr(s3_store, "build_s3_client", fake_build)
    app = create_app(Settings(_env_file=None, **CACHE_SETTINGS, storage_circuit_open_seconds=7))
    with TestClient(app) as client:
        assert client.get("/health").json()["cache"] == {"enabled": True, "circuit_open": False}
        assert client.get("/health").status_code == 200
        store = app.state.store
        assert isinstance(store, GuardedStore)
        assert app.state.breaker is store.breaker
        assert store.breaker.open_seconds == 7
        assert store.public_url("images/x.png") == "https://cache.test/images/x.png"
    assert len(built) == 1
    assert built[0].used == []


def test_lifespan_without_cache_has_no_store(monkeypatch):
    def forbidden(settings: Settings):
        raise AssertionError("no storage client with CACHE_ENABLED=false")

    monkeypatch.setattr(s3_store, "build_s3_client", forbidden)
    app = create_app(Settings(_env_file=None, cache_enabled=False))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert app.state.store is None
        assert app.state.breaker is None


async def test_lifespan_shutdown_drains_detached_uploads():
    app = create_app(Settings(_env_file=None, cache_enabled=False))
    finished: list[bool] = []

    async def upload() -> None:
        await asyncio.sleep(0.05)
        finished.append(True)

    async with app.router.lifespan_context(app):
        task = asyncio.ensure_future(upload())
        app.state.image_cache_tasks.add(task)
    assert finished == [True]
