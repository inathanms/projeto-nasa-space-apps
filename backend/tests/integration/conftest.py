import asyncio
import os
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import deps
from app.clients import http as http_module
from app.clients.irsa_sia import IrsaSiaClient
from app.config import Settings
from app.domain.models import Collection, SiaResult
from app.main import create_app
from app.storage.circuit_breaker import CircuitBreaker, GuardedStore
from app.storage.memory_store import InMemoryObjectStore

FIXTURES = Path(__file__).parent.parent / "fixtures"
SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
M101 = {"ra": 210.80227, "dec": 54.34895}
OBS_ID = "2026W20_2A_0464_3"

# Settings of a cache-enabled app; the storage itself is an InMemoryObjectStore injected via
# dependency_overrides (its public_url is https://cache.test/<key>), so nothing leaves the process.
STORAGE_PUBLIC_BASE_URL = "https://cache.test"
API_PUBLIC_BASE_URL = "https://api.test"
CACHE_SETTINGS = {
    "cache_enabled": True,
    "s3_endpoint_url": "https://storage.invalid",
    "s3_bucket": "test-bucket",
    "s3_access_key_id": "test-key-id",
    "s3_secret_access_key": "test-secret",
    "s3_public_base_url": STORAGE_PUBLIC_BASE_URL,
    "api_public_base_url": API_PUBLIC_BASE_URL,
}
# VAL-502: `SPHEREYE_TEST_CACHE=1 uv run pytest` runs every integration test of `make_app`
# with the cache enabled over an InMemoryObjectStore.
CACHE_FOR_ALL = os.environ.get("SPHEREYE_TEST_CACHE", "").lower() in {"1", "true", "yes"}


def sia_fixture(name: str = "sia_m101_qr3.xml") -> bytes:
    return (FIXTURES / name).read_bytes()


def parsed_fixture(name: str = "sia_m101_qr3.xml") -> SiaResult:
    return IrsaSiaClient(None, Settings())._parse(sia_fixture(name))  # type: ignore[arg-type]


def access_url(obs_id: str = OBS_ID, detector: str = "D2") -> str:
    rec = next(
        r
        for r in parsed_fixture().records
        if r.observation_id == obs_id and r.detector.value == detector
    )
    return rec.access_url


class FakeSia:
    def __init__(self, result: SiaResult | None = None) -> None:
        self.result = result or parsed_fixture()
        self.calls: list[tuple] = []

    async def search(
        self,
        ra: float,
        dec: float,
        radius: float,
        collection: Collection,
        start_mjd: float | None = None,
        end_mjd: float | None = None,
    ) -> SiaResult:
        self.calls.append((ra, dec, radius, collection, start_mjd, end_mjd))
        return self.result


class FakeCutout:
    def __init__(self, payload: bytes, delay: float = 0.0, error: Exception | None = None) -> None:
        self.payload = payload
        self.delay = delay
        self.error = error
        self.calls: list[tuple[str, float, float, int]] = []

    async def fetch(self, access_url: str, ra: float, dec: float, size_px: int) -> bytes:
        self.calls.append((access_url, ra, dec, size_px))
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.payload


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    async def fake_sleep(seconds: float) -> None:
        pass

    monkeypatch.setattr(http_module, "sleep", fake_sleep)


@dataclass
class CacheHarness:
    """Objects of a cache-enabled app: the raw in-memory store and its guarded wrapper."""

    app: FastAPI
    store: InMemoryObjectStore
    guarded: GuardedStore


def _install_cache(
    app: FastAPI, store: InMemoryObjectStore | None, sia: FakeSia | None
) -> CacheHarness:
    settings: Settings = app.state.settings
    store = store or InMemoryObjectStore()
    guarded = GuardedStore(
        store, CircuitBreaker(open_seconds=settings.storage_circuit_open_seconds)
    )
    app.dependency_overrides[deps.get_object_store] = lambda: guarded
    if sia is not None:
        # Fake the upstream only, so the SIA cache (CachedSiaClient) stays in the path.
        app.dependency_overrides[deps.get_irsa_sia_client] = lambda: sia
    return CacheHarness(app, store, guarded)


@pytest.fixture
def make_app() -> Callable[..., FastAPI]:
    """create_app with Settings overrides; `sia`/`cutout` fakes replace the IRSA clients."""

    def factory(sia: FakeSia | None = None, cutout: FakeCutout | None = None, **overrides):
        if CACHE_FOR_ALL:
            overrides = CACHE_SETTINGS | overrides
        app = create_app(Settings(_env_file=None, **overrides))
        if app.state.settings.cache_enabled:
            _install_cache(app, None, sia)
        elif sia is not None:
            app.dependency_overrides[deps.get_sia_client] = lambda: sia
        if cutout is not None:
            app.dependency_overrides[deps.get_cutout_client] = lambda: cutout
        return app

    return factory


@pytest.fixture
def make_cache_app() -> Callable[..., CacheHarness]:
    """Cache-enabled app over an InMemoryObjectStore (injected with dependency_overrides)."""

    def factory(
        sia: FakeSia | None = None,
        cutout: FakeCutout | None = None,
        store: InMemoryObjectStore | None = None,
        **overrides,
    ) -> CacheHarness:
        app = create_app(Settings(_env_file=None, **(CACHE_SETTINGS | overrides)))
        harness = _install_cache(app, store, sia)
        if cutout is not None:
            app.dependency_overrides[deps.get_cutout_client] = lambda: cutout
        return harness

    return factory


@pytest.fixture
def make_client(make_app) -> Iterator[Callable[..., TestClient]]:
    """TestClient (lifespan running) for `make_app(...)`; server errors become 500 responses."""
    clients: list[TestClient] = []

    def factory(*args, **kwargs) -> TestClient:
        client = TestClient(make_app(*args, **kwargs), raise_server_exceptions=False)
        client.__enter__()
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def make_cache_client(make_cache_app) -> Iterator[Callable[..., tuple[TestClient, CacheHarness]]]:
    """(TestClient with lifespan, CacheHarness) for `make_cache_app(...)`; redirects not followed."""
    clients: list[TestClient] = []

    def factory(*args, **kwargs) -> tuple[TestClient, CacheHarness]:
        harness = make_cache_app(*args, **kwargs)
        client = TestClient(harness.app, raise_server_exceptions=False, follow_redirects=False)
        client.__enter__()
        clients.append(client)
        return client, harness

    yield factory
    for client in clients:
        client.__exit__(None, None, None)
