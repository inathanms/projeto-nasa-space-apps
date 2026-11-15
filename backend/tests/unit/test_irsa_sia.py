import logging
from pathlib import Path

import httpx
import pytest
import respx

from app.clients import http as http_module
from app.clients.irsa_sia import IrsaSiaClient, parse_region
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamInvalidResponseError, UpstreamTimeoutError
from app.domain.models import Collection, Detector

FIXTURES = Path(__file__).parent.parent / "fixtures"
SIA_URL = "https://irsa.ipac.caltech.edu/SIA"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(http_module, "sleep", fake_sleep)
    return sleeps


@pytest.fixture
def settings() -> Settings:
    return Settings(irsa_max_retries=1)


async def search(settings: Settings, **kwargs):
    async with httpx.AsyncClient() as http:
        return await IrsaSiaClient(http, settings).search(
            210.80227, 54.34895, 0.001, Collection.QR3, **kwargs
        )


@respx.mock
async def test_parses_real_fixture(settings):
    route = respx.get(SIA_URL).respond(200, text=fixture("sia_m101_qr3.xml"))
    result = await search(settings)

    assert route.call_count == 1
    assert len(result.records) == 50
    assert result.truncated is True  # the real response hit MAXREC=50
    first = result.records[0]
    assert first.observation_id == "2026W20_2A_0464_3"
    assert first.detector is Detector.D2
    assert first.wavelength_min_um == 1.1033
    assert first.wavelength_max_um == 1.6499
    assert first.start_mjd == pytest.approx(61177.456981)
    assert first.exposure_seconds == pytest.approx(113.5826)
    assert (first.center_ra, first.center_dec) == (212.0232, 52.652924)
    assert len(first.footprint) == 4
    assert first.footprint[0] == (211.776795, 55.094819)
    assert first.access_url.startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/")
    assert len({(r.observation_id, r.detector) for r in result.records}) == 50
    assert {r.detector for r in result.records} == set(Detector)
    assert len({int(r.start_mjd) for r in result.records}) > 1


@respx.mock
async def test_request_params(settings):
    route = respx.get(SIA_URL).respond(200, text=fixture("sia_empty.xml"))
    await search(settings)
    params = route.calls.last.request.url.params
    assert params["COLLECTION"] == "spherex_qr3"
    assert params["POS"] == "CIRCLE 210.80227 54.34895 0.001"
    assert params["MAXREC"] == "5000"
    assert "TIME" not in params


@respx.mock
async def test_empty_is_valid(settings):
    respx.get(SIA_URL).respond(200, text=fixture("sia_empty.xml"))
    result = await search(settings)
    assert result.records == []
    assert result.truncated is False


@respx.mock
async def test_overflow_sets_truncated(settings):
    respx.get(SIA_URL).respond(200, text=fixture("sia_overflow.xml"))
    result = await search(settings)
    assert len(result.records) == 3
    assert result.truncated is True


@respx.mock
async def test_ac005_time_window_in_query(settings):
    route = respx.get(SIA_URL).respond(200, text=fixture("sia_empty.xml"))
    await search(settings, start_mjd=61177.0 - 1e-6, end_mjd=61178.5 + 1e-6)
    time_param = route.calls.last.request.url.params["TIME"]
    lo, hi = time_param.split()
    assert float(lo) == pytest.approx(61177.0 - 1e-6, abs=1e-9)
    assert float(hi) == pytest.approx(61178.5 + 1e-6, abs=1e-9)


@respx.mock
async def test_open_ended_time_window(settings):
    route = respx.get(SIA_URL).respond(200, text=fixture("sia_empty.xml"))
    await search(settings, start_mjd=61177.0)
    assert route.calls.last.request.url.params["TIME"] == "61177.0 +inf"
    await search(settings, end_mjd=61178.0)
    assert route.calls.last.request.url.params["TIME"] == "-inf 61178.0"


@respx.mock
async def test_discards_non_science_and_odd_detectors(settings, caplog):
    xml = fixture("sia_overflow.xml")
    xml = xml.replace("<TD>science</TD>", "<TD>calibration</TD>", 1)
    xml = xml.replace("<TD>SPHEREx-D5</TD>", "<TD>SPHEREx-D9</TD>", 1)
    respx.get(SIA_URL).respond(200, text=xml)
    with caplog.at_level(logging.WARNING):
        result = await search(settings)
    assert len(result.records) == 1
    assert any("bandpass" in r.message for r in caplog.records)


@respx.mock
async def test_duplicate_rows_keep_first(settings, caplog):
    xml = fixture("sia_overflow.xml")
    rows = xml.split("<TR>")
    xml = "<TR>".join(rows[:2]) + "<TR>" + rows[1] + "<TR>" + "<TR>".join(rows[2:])
    respx.get(SIA_URL).respond(200, text=xml)
    with caplog.at_level(logging.WARNING):
        result = await search(settings)
    assert len(result.records) == 3
    assert any("duplicate" in r.message for r in caplog.records)


@respx.mock
async def test_query_status_error(settings, caplog):
    xml = fixture("sia_empty.xml").replace(
        '<INFO name="QUERY_STATUS" value="OK"/>',
        '<INFO name="QUERY_STATUS" value="ERROR">secret internal detail</INFO>',
    )
    respx.get(SIA_URL).respond(200, text=xml)
    with caplog.at_level(logging.ERROR), pytest.raises(UpstreamError) as exc:
        await search(settings)
    assert "secret internal detail" not in exc.value.message
    assert any(getattr(r, "irsa_message", "") == "secret internal detail" for r in caplog.records)


@respx.mock
@pytest.mark.parametrize("body", ["<html>not a votable</html>", "", "garbage"])
async def test_invalid_votable(settings, body):
    respx.get(SIA_URL).respond(200, text=body)
    with pytest.raises(UpstreamInvalidResponseError):
        await search(settings)


@respx.mock
async def test_ac014_503_twice_two_attempts(settings, no_backoff):
    route = respx.get(SIA_URL).respond(503)
    with pytest.raises(UpstreamError) as exc:
        await search(settings)
    assert route.call_count == 2
    assert no_backoff == [1.0]
    assert "irsa.ipac" not in exc.value.message


@respx.mock
async def test_retry_then_success(settings):
    route = respx.get(SIA_URL).mock(
        side_effect=[httpx.Response(502), httpx.Response(200, text=fixture("sia_empty.xml"))]
    )
    result = await search(settings)
    assert route.call_count == 2
    assert result.records == []


@respx.mock
async def test_ac015_timeout(settings):
    route = respx.get(SIA_URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(UpstreamTimeoutError):
        await search(settings)
    assert route.call_count == 2


@respx.mock
async def test_4xx_not_retried(settings):
    route = respx.get(SIA_URL).respond(400)
    with pytest.raises(UpstreamError):
        await search(settings)
    assert route.call_count == 1


@respx.mock
async def test_transport_error_is_upstream_error(settings):
    respx.get(SIA_URL).mock(side_effect=httpx.ConnectError("boom https://irsa.ipac.caltech.edu"))
    with pytest.raises(UpstreamError) as exc:
        await search(settings)
    assert "irsa" not in exc.value.message


@respx.mock
async def test_user_agent_and_duration_log(settings, caplog):
    route = respx.get(SIA_URL).respond(200, text=fixture("sia_empty.xml"))
    with caplog.at_level(logging.INFO):
        await search(settings)
    assert route.calls.last.request.headers["user-agent"] == settings.http_user_agent
    assert any(
        getattr(r, "event", "") == "irsa_sia" and hasattr(r, "duration_ms") for r in caplog.records
    )


def test_parse_region_drops_closing_point():
    assert parse_region("POLYGON ICRS 1 2 3 4 5 6 1 2") == [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
    assert parse_region("POLYGON ICRS 1.0000004 2 3 4 5 6") == [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
