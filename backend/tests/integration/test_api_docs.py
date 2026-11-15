import httpx
import respx

from app.main import CREDIT
from tests.integration.conftest import M101, OBS_ID, FakeCutout, FakeSia
from tests.synthetic_fits import make_cutout_bytes


def test_ac001_docs_and_openapi(make_client):
    client = make_client()
    docs = client.get("/docs")
    assert docs.status_code == 200
    assert "swagger-ui" in docs.text.lower()

    schema = client.get("/openapi.json").json()
    assert schema["openapi"].startswith("3.")
    assert CREDIT in schema["info"]["description"]
    assert {"/health", "/epochs", "/image"} <= set(schema["paths"])

    for path, item in schema["paths"].items():
        operation = item["get"]
        assert operation.get("description"), path
        for param in operation.get("parameters", []):
            assert param.get("description"), (path, param["name"])
            assert "example" in param, (path, param["name"])


def test_ac001_image_responses_documented(make_client):
    operation = make_client().get("/openapi.json").json()["paths"]["/image"]["get"]
    ok = operation["responses"]["200"]
    assert "image/png" in ok["content"]
    assert {"X-Scale-Min", "X-Scale-Max", "X-Valid-Pixel-Fraction", "Cache-Control"} <= set(
        ok["headers"]
    )
    assert {"X-Upscale", "X-Pixel-Scale-Arcsec", "X-Native-Pixel-Scale-Arcsec"} <= set(
        ok["headers"]
    )
    assert "REQUEST_TOO_LARGE" in operation["responses"]["422"]["description"]
    for phrase in ("6.15 arcsec", "more sky, not more detail", "fill_holes"):
        assert phrase in operation["description"], phrase
    params = {p["name"]: p for p in operation["parameters"]}
    assert params["size"]["schema"]["default"] == 1.0
    assert params["size"]["schema"]["maximum"] == 3.0
    assert (params["upscale"]["schema"]["minimum"], params["upscale"]["schema"]["maximum"]) == (
        1,
        4,
    )
    assert params["fill_holes"]["schema"]["default"] is False
    for status in ("404", "422", "502", "503", "504"):
        response = operation["responses"][status]
        assert response["description"]
        example = response["content"]["application/json"]["example"]
        assert set(example["error"]) == {"code", "message", "details"}


@respx.mock
def test_ac002_health_without_irsa(make_client):
    respx.route().mock(side_effect=httpx.ConnectError("down"))
    response = make_client().get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0"}
    assert respx.calls.call_count == 0


def test_ac017_cors_exposes_image_headers(make_client):
    client = make_client(sia=FakeSia(), cutout=FakeCutout(make_cutout_bytes()))
    origin = {"Origin": "http://localhost:3000"}
    response = client.get(
        "/image", params={**M101, "observation_id": OBS_ID, "detector": "D2"}, headers=origin
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    exposed = {
        h.strip().lower() for h in response.headers["access-control-expose-headers"].split(",")
    }
    assert {
        "x-scale-min",
        "x-scale-max",
        "x-valid-pixel-fraction",
        "x-upscale",
        "x-native-pixel-scale-arcsec",
    } <= exposed

    preflight = client.options("/image", headers={**origin, "Access-Control-Request-Method": "GET"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin(make_client):
    response = make_client().get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers
