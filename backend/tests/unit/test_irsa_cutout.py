import httpx
import pytest
import respx

from app.clients import http as http_module
from app.clients.irsa_cutout import IrsaCutoutClient
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamInvalidResponseError, UpstreamTimeoutError

URL = "https://irsa.ipac.caltech.edu/ibe/data/spherex/qr3/x.fits"


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    async def fake_sleep(seconds: float) -> None:
        pass

    monkeypatch.setattr(http_module, "sleep", fake_sleep)


async def fetch(url: str = URL, settings: Settings | None = None) -> bytes:
    async with httpx.AsyncClient() as http:
        client = IrsaCutoutClient(http, settings or Settings(irsa_max_retries=1))
        return await client.fetch(url, 210.80227, 54.34895, 300)


@respx.mock
async def test_fetch_returns_raw_bytes_and_params():
    route = respx.get(URL).respond(200, content=b"SIMPLE  =")
    assert await fetch() == b"SIMPLE  ="
    request = route.calls.last.request
    assert request.url.params["center"] == "210.80227,54.34895"
    assert request.url.params["size"] == "300pix"
    assert request.headers["user-agent"] == Settings().http_user_agent


@respx.mock
@pytest.mark.parametrize(
    "url",
    [
        "https://evil.example.com/x.fits",
        "https://irsa.ipac.caltech.edu.evil.com/x.fits",
        "https://evilirsa.ipac.caltech.edu/x.fits",
        "file:///etc/passwd",
        "http://127.0.0.1/x",
    ],
)
async def test_ac013_invalid_host_makes_no_request(url):
    with pytest.raises(UpstreamInvalidResponseError):
        await fetch(url)
    assert respx.calls.call_count == 0


@respx.mock
async def test_subdomain_allowed():
    url = "https://sub.irsa.ipac.caltech.edu/x.fits"
    respx.get(url).respond(200, content=b"ok")
    assert await fetch(url) == b"ok"


@respx.mock
async def test_redirect_within_host_followed():
    respx.get(URL).respond(302, headers={"location": "/ibe/other.fits"})
    final = respx.get("https://irsa.ipac.caltech.edu/ibe/other.fits").respond(200, content=b"data")
    assert await fetch() == b"data"
    assert final.call_count == 1


@respx.mock
async def test_redirect_to_other_host_rejected():
    respx.get(URL).respond(302, headers={"location": "https://evil.example.com/x"})
    evil = respx.get("https://evil.example.com/x").respond(200, content=b"x")
    with pytest.raises(UpstreamInvalidResponseError):
        await fetch()
    assert evil.call_count == 0


@respx.mock
async def test_size_limit_streaming():
    respx.get(URL).respond(200, content=b"x" * 100)
    with pytest.raises(UpstreamInvalidResponseError):
        await fetch(settings=Settings(irsa_max_cutout_bytes=50))


@respx.mock
async def test_size_limit_at_boundary_ok():
    respx.get(URL).respond(200, content=b"x" * 50)
    assert len(await fetch(settings=Settings(irsa_max_cutout_bytes=50))) == 50


@respx.mock
async def test_503_retried_then_upstream_error():
    route = respx.get(URL).respond(503)
    with pytest.raises(UpstreamError) as exc:
        await fetch()
    assert route.call_count == 2
    assert "irsa.ipac" not in exc.value.message


@respx.mock
async def test_timeout_maps_to_timeout_error():
    route = respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamTimeoutError):
        await fetch()
    assert route.call_count == 2


@respx.mock
async def test_404_not_retried():
    route = respx.get(URL).respond(404)
    with pytest.raises(UpstreamError):
        await fetch()
    assert route.call_count == 1
