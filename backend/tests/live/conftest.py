import asyncio
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clients.irsa_cutout import IrsaCutoutClient
from app.clients.irsa_sia import IrsaSiaClient
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamTimeoutError
from app.domain.models import Collection, ImageRecord
from app.main import create_app
from app.processing.fits_reader import CutoutHdus, open_cutout

RA, DEC = 210.80227, 54.34895
CUTOUT_SIZE_DEG = 0.25
CUTOUT_SIZE_PX = 147  # ceil(0.25 deg * 3600 / 6.15")


def skip_on_upstream(exc: BaseException) -> None:
    pytest.skip(f"IRSA unavailable: {type(exc).__name__}: {exc}")


def run_upstream[T](factory: Callable[[], T]) -> T:
    try:
        return factory()
    except (httpx.HTTPError, UpstreamError, UpstreamTimeoutError, OSError) as exc:
        skip_on_upstream(exc)
        raise


def skip_if_upstream_down(response: httpx.Response) -> None:
    if response.status_code in (502, 503, 504):
        pytest.skip(f"IRSA unavailable: HTTP {response.status_code} {response.text[:200]}")


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(_env_file=None)


@pytest.fixture(scope="session")
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings)) as c:
        yield c


@dataclass(frozen=True)
class RealCutout:
    record: ImageRecord
    hdus: CutoutHdus


@pytest.fixture(scope="session")
def real_cutouts(settings: Settings) -> list[RealCutout]:
    """Cutouts (0.25 deg at M101) of a few real D2/D5 records, largest first."""

    async def fetch() -> list[RealCutout]:
        headers = {"User-Agent": settings.http_user_agent}
        async with httpx.AsyncClient(headers=headers) as http:
            sia = await IrsaSiaClient(http, settings).search(RA, DEC, 0.001, Collection.QR3)
            cutout = IrsaCutoutClient(http, settings)
            found = []
            for record in sia.records[:4]:
                raw = await cutout.fetch(record.access_url, RA, DEC, CUTOUT_SIZE_PX)
                found.append(RealCutout(record, open_cutout(raw)))
            return found

    cutouts = run_upstream(lambda: asyncio.run(fetch()))
    if not cutouts:
        pytest.skip("IRSA returned no images for M101")
    return sorted(cutouts, key=lambda c: -min(c.hdus.image_data.shape))
