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
    client = make_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "0.1.0",
        # REQ-554 (enabled follows the suite mode, see SPHEREYE_TEST_CACHE)
        "cache": {"enabled": client.app.state.settings.cache_enabled, "circuit_open": False},
    }
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
        "x-cache",
        "x-center-ra",
        "x-center-dec",
        "x-render-version",
    } <= exposed

    preflight = client.options("/image", headers={**origin, "Access-Control-Request-Method": "GET"})
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin(make_client):
    response = make_client().get("/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


def test_cache_headers_and_response_format_documented(make_client):
    schema = make_client().get("/openapi.json").json()
    operation = schema["paths"]["/image"]["get"]
    new_headers = {"X-Cache", "X-Center-Ra", "X-Center-Dec", "X-Render-Version"}
    assert new_headers <= set(operation["responses"]["200"]["headers"])
    redirect = operation["responses"]["302"]
    assert {"Location", "Cache-Control"} | new_headers <= set(redirect["headers"])
    assert redirect["headers"]["Cache-Control"]["schema"]["example"] == "public, max-age=86400"
    content = operation["responses"]["200"]["content"]
    assert {"image/png", "application/json"} <= set(content)
    assert content["application/json"]["schema"]["$ref"].endswith("/ImageJsonResponse")
    body = schema["components"]["schemas"]["ImageJsonResponse"]["properties"]
    assert {"url", "cache_status", "key", "params", "image", "scale", "stack"} <= set(body)

    params = {p["name"]: p for p in operation["parameters"]}
    response_format = params["response_format"]
    assert response_format["schema"]["default"] == "png"
    assert response_format["example"] == "png"
    ref = response_format["schema"].get("$ref") or response_format["schema"]["allOf"][0]["$ref"]
    assert schema["components"]["schemas"][ref.rsplit("/", 1)[-1]]["enum"] == [
        "png",
        "json",
        "redirect",
    ]
    # Mandatory notes of spec cache 4.2.
    for phrase in (
        "recommended for the frontend",
        "do not expose",
        "Cache-Control: public, max-age=86400",
    ):
        assert phrase in operation["description"], phrase
