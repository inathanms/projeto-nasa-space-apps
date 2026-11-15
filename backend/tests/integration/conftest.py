import asyncio
from collections.abc import Callable, Iterator
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

FIXTURES = Path(__file__).parent.parent / "fixtures"
SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
M101 = {"ra": 210.80227, "dec": 54.34895}
OBS_ID = "2026W20_2A_0464_3"


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


@pytest.fixture
def make_app() -> Callable[..., FastAPI]:
    """create_app with Settings overrides; `sia`/`cutout` fakes replace the IRSA clients."""

    def factory(sia: FakeSia | None = None, cutout: FakeCutout | None = None, **overrides):
        app = create_app(Settings(_env_file=None, **overrides))
        if sia is not None:
            app.dependency_overrides[deps.get_sia_client] = lambda: sia
        if cutout is not None:
            app.dependency_overrides[deps.get_cutout_client] = lambda: cutout
        return app

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
