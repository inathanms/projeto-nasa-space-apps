import itertools

import httpx
import pytest
import respx
from astropy.time import Time

from tests.integration.conftest import M101, SIA_URL, sia_fixture


def get_epochs(client, **params):
    return client.get("/epochs", params={**M101, **params})


@pytest.fixture
def sia_route():
    with respx.mock(assert_all_called=False) as mock:
        yield mock.get(SIA_URL)


def test_ac003_m101_grouping(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture())
    response = get_epochs(make_client())
    assert response.status_code == 200
    body = response.json()

    request = sia_route.calls.last.request
    assert request.url.params["COLLECTION"] == "spherex_qr3"
    # REQ-501/505: (ra, dec) are rounded to the 6.15" grid before querying IRSA.
    assert request.url.params["POS"] == "CIRCLE 210.8015 54.348917 0.001"
    assert request.url.params["MAXREC"] == "5000"
    assert "TIME" not in request.url.params

    assert set(body) == {
        "query",
        "total_observations",
        "total_visits",
        "truncated",
        "visits",
        "observations",
    }
    assert body["query"] == {  # REQ-505: normalized position
        "ra": 210.8015,
        "dec": 54.348917,
        "radius": 0.001,
        "collection": "spherex_qr3",
        "detector": None,
        "start_time": None,
        "end_time": None,
    }
    assert body["truncated"] is True  # fixture was recorded with MAXREC=50 (OVERFLOW)

    observations = body["observations"]
    ids = [o["observation_id"] for o in observations]
    assert len(ids) == len(set(ids)) == body["total_observations"] > 1
    starts = [o["start_mjd"] for o in observations]
    assert starts == sorted(starts)

    first = next(o for o in observations if o["observation_id"] == "2026W20_2A_0464_3")
    assert first["start_time"] == "2026-05-17T10:58:03Z"
    assert first["start_mjd"] == 61177.456981
    assert first["exposure_seconds"] == pytest.approx(113.58)
    assert [d["detector"] for d in first["detectors"]] == ["D2", "D5"]
    d2 = first["detectors"][0]
    assert set(d2) == {
        "detector",
        "wavelength_min_um",
        "wavelength_max_um",
        "image_center",
        "footprint",
    }
    assert d2["wavelength_min_um"] == 1.1033 and d2["wavelength_max_um"] == 1.6499
    assert set(d2["image_center"]) == {"ra", "dec"}
    assert all(len(p) == 2 for p in d2["footprint"]) and len(d2["footprint"]) >= 3
    for value in [*d2["image_center"].values(), *(c for p in d2["footprint"] for c in p)]:
        assert round(value, 6) == value

    for obs in observations:
        detectors = [d["detector"] for d in obs["detectors"]]
        assert detectors == sorted(detectors)

    visits = body["visits"]
    assert body["total_visits"] == len(visits) > 1
    assert [v["visit_index"] for v in visits] == list(range(len(visits)))
    by_id = {o["observation_id"]: o for o in observations}
    for visit in visits:
        members = [by_id[i] for i in visit["observation_ids"]]
        assert all(m["visit_index"] == visit["visit_index"] for m in members)
        assert [m["start_mjd"] for m in members] == sorted(m["start_mjd"] for m in members)
        for prev, cur in itertools.pairwise(members):
            assert cur["start_mjd"] - prev["end_mjd"] <= 2.0
    for prev, cur in itertools.pairwise(visits):
        assert cur["start_mjd"] - prev["end_mjd"] > 2.0
    assert sum(len(v["observation_ids"]) for v in visits) == len(observations)


def test_ac004_detector_filter(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture())
    body = get_epochs(make_client(), detector="D2").json()
    assert body["query"]["detector"] == "D2"
    assert body["observations"]
    for obs in body["observations"]:
        assert [d["detector"] for d in obs["detectors"]] == ["D2"]
    ids = {o["observation_id"] for o in body["observations"]}
    assert "2026W21_1A_0114_4" not in ids  # only D3/D6 in the fixture


def test_ac005_time_window_sent_as_mjd(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture())
    response = get_epochs(
        make_client(), start_time="2026-05-01T00:00:00Z", end_time="2026-05-31T23:59:59Z"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"]["start_time"] == "2026-05-01T00:00:00Z"
    assert body["query"]["end_time"] == "2026-05-31T23:59:59Z"
    lo, hi = (float(v) for v in sia_route.calls.last.request.url.params["TIME"].split())
    assert lo == pytest.approx(Time("2026-05-01T00:00:00", scale="utc").mjd, abs=1e-6)
    assert hi == pytest.approx(Time("2026-05-31T23:59:59", scale="utc").mjd, abs=1e-6)


def test_open_ended_time_window(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture("sia_empty.xml"))
    assert get_epochs(make_client(), end_time="2026-05-31T23:59:59Z").status_code == 200
    lo, _ = sia_route.calls.last.request.url.params["TIME"].split()
    assert lo == "-inf"


def test_ac006_empty(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture("sia_empty.xml"))
    response = get_epochs(make_client())
    assert response.status_code == 200
    body = response.json()
    assert body["observations"] == [] and body["visits"] == []
    assert body["total_observations"] == 0 and body["total_visits"] == 0
    assert body["truncated"] is False


def test_collection_param_and_default_from_settings(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture("sia_empty.xml"))
    client = make_client(irsa_default_collection="spherex_dr1")
    assert get_epochs(client).json()["query"]["collection"] == "spherex_dr1"
    get_epochs(client, collection="spherex_qr3_deep")
    assert sia_route.calls.last.request.url.params["COLLECTION"] == "spherex_qr3_deep"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"ra": 400}, "ra"),
        ({"ra": 360}, "ra"),
        ({"ra": -0.1}, "ra"),
        ({"dec": -91}, "dec"),
        ({"dec": 90.5}, "dec"),
        ({"ra": "abc"}, "ra"),
        ({"ra": "nan"}, "ra"),
        ({"radius": 0}, "radius"),
        ({"radius": 1.5}, "radius"),
        ({"detector": "D7"}, "detector"),
        ({"collection": "other"}, "collection"),
        ({"start_time": "yesterday"}, "start_time"),
        ({"start_time": "2026-06-01T00:00:00Z", "end_time": "2026-05-01T00:00:00Z"}, "end_time"),
    ],
)
def test_ac007_epochs_validation(make_client, sia_route, params, field):
    response = get_epochs(make_client(), **params)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["message"]
    assert field in [f["field"] for f in error["details"]["fields"]]
    assert sia_route.calls.call_count == 0


def test_ac007_missing_required(make_client, sia_route):
    response = make_client().get("/epochs", params={"ra": 10})
    assert response.status_code == 422
    assert [f["field"] for f in response.json()["error"]["details"]["fields"]] == ["dec"]


def test_unknown_params_are_ignored(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture("sia_empty.xml"))
    assert get_epochs(make_client(), foo="bar").status_code == 200


def test_ac014_retries_then_upstream_error(make_client, sia_route):
    sia_route.respond(503)
    response = get_epochs(make_client(irsa_max_retries=1))
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"
    assert sia_route.call_count == 2


def test_ac015_timeout(make_client, sia_route):
    sia_route.mock(side_effect=httpx.ReadTimeout("slow"))
    response = get_epochs(make_client())
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


def test_invalid_votable_is_502(make_client, sia_route):
    sia_route.respond(200, content=b"<html>proxy error</html>")
    response = get_epochs(make_client())
    assert response.status_code == 502
    error = response.json()["error"]
    assert error["code"] == "UPSTREAM_INVALID_RESPONSE"
    assert "irsa.ipac" not in error["message"]


def rgb_flags(visits):
    return {v["observation_ids"][0].rsplit("_", 1)[0]: v["rgb_available"] for v in visits}


def test_visits_report_detectors_and_rgb_available(make_client):
    from tests.integration.conftest import FakeSia, parsed_fixture

    client = make_client(sia=FakeSia(parsed_fixture("sia_visit_multi.xml")))
    visits = get_epochs(client).json()["visits"]
    assert len(visits) == 2
    w20, w46 = visits
    assert w20["observation_ids"][0].startswith("2026W20")
    assert w20["detectors"] == ["D1", "D2", "D3", "D4", "D5", "D6"]
    assert w20["rgb_available"] is True
    assert w46["observation_ids"][0].startswith("2026W46")
    assert w46["detectors"] == ["D1", "D2", "D4", "D5"]
    assert w46["rgb_available"] is False


def test_detector_filter_makes_rgb_unavailable(make_client):
    from tests.integration.conftest import FakeSia, parsed_fixture

    client = make_client(sia=FakeSia(parsed_fixture("sia_visit_multi.xml")))
    visits = get_epochs(client, detector="D3").json()["visits"]
    assert [v["detectors"] for v in visits] == [["D3"]]
    assert [v["rgb_available"] for v in visits] == [False]


def test_m101_fixture_visits_have_consistent_rgb_flag(make_client, sia_route):
    sia_route.respond(200, content=sia_fixture())
    body = get_epochs(make_client()).json()
    by_id = {o["observation_id"]: o for o in body["observations"]}
    for visit in body["visits"]:
        present = {d["detector"] for i in visit["observation_ids"] for d in by_id[i]["detectors"]}
        assert visit["detectors"] == sorted(present)
        assert visit["rgb_available"] == {"D1", "D2", "D3"}.issubset(present)
