import asyncio
import io
import logging

import httpx
import matplotlib
import numpy as np
import pytest
import respx
from PIL import Image

from app.domain.models import SiaResult
from tests.integration.conftest import (
    M101,
    OBS_ID,
    SIA_URL,
    FakeCutout,
    FakeSia,
    access_url,
    parsed_fixture,
    sia_fixture,
)
from tests.synthetic_fits import make_cutout_bytes

IMAGE_PARAMS = {**M101, "observation_id": OBS_ID, "detector": "D2"}
EXPECTED_HEADERS = {
    "x-observation-id",
    "x-detector",
    "x-observation-time",
    "x-wavelength-min-um",
    "x-wavelength-max-um",
    "x-scale-min",
    "x-scale-max",
    "x-image-width",
    "x-image-height",
    "x-pixel-scale-arcsec",
    "x-native-pixel-scale-arcsec",
    "x-upscale",
    "x-valid-pixel-fraction",
    "cache-control",
}


def png_array(response) -> np.ndarray:
    image = Image.open(io.BytesIO(response.content))
    assert image.mode == "RGBA"
    return np.asarray(image)


def fake_client(make_client, payload: bytes | None = None, **kwargs):
    cutout = FakeCutout(make_cutout_bytes() if payload is None else payload)
    sia = FakeSia()
    return make_client(sia=sia, cutout=cutout, **kwargs), sia, cutout


@respx.mock
def test_ac008_end_to_end_png_and_headers(make_client):
    sia = respx.get(SIA_URL).respond(200, content=sia_fixture())
    cutout = respx.get(access_url()).respond(200, content=make_cutout_bytes(gzip=True))

    response = make_client().get("/image", params={**IMAGE_PARAMS, "size": 0.25, "align": True})

    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    assert EXPECTED_HEADERS <= set(response.headers)
    rgba = png_array(response)
    assert rgba.shape == (146, 146, 4)

    h = response.headers
    assert h["x-observation-id"] == OBS_ID
    assert h["x-detector"] == "D2"
    assert h["x-observation-time"] == "2026-05-17T10:58:03Z"
    assert h["x-wavelength-min-um"] == "1.1033"
    assert h["x-wavelength-max-um"] == "1.6499"
    assert h["x-image-width"] == h["x-image-height"] == "146"
    assert h["x-pixel-scale-arcsec"] == "6.15"
    assert h["x-native-pixel-scale-arcsec"] == "6.15"
    assert h["x-upscale"] == "1"
    assert float(h["x-scale-min"]) < float(h["x-scale-max"])
    assert float(h["x-valid-pixel-fraction"]) == pytest.approx(1.0)
    assert h["cache-control"] == "public, max-age=86400"

    # REQ-501: the render uses the position rounded to the 6.15" grid.
    assert sia.calls.last.request.url.params["POS"] == "CIRCLE 210.8015 54.348917 0.001"
    params = cutout.calls.last.request.url.params
    assert params["center"] == "210.8015,54.348917"  # REQ-501: normalized position
    assert params["size"] == "220pix"  # ceil(0.25 * 1.5 * 3600 / 6.15)


def test_align_false_uses_requested_size_and_native_grid(make_client):
    client, _, cutout = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.1, "align": False})
    assert response.status_code == 200
    assert cutout.calls[-1][3] == 59  # ceil(0.1 * 3600 / 6.15), no margin
    assert png_array(response).shape == (240, 240, 4)  # the synthetic cutout as delivered


def test_minimum_output_is_16_px(make_client):
    client, _, _ = fake_client(make_client)
    assert png_array(client.get("/image", params={**IMAGE_PARAMS, "size": 0.01})).shape[0] == 16


# --- Phase A: size, upscale, output limit (spec-tool-spherex-image-quality) -------------


@respx.mock
def test_ac101_default_size_is_one_degree(make_client):
    respx.get(SIA_URL).respond(200, content=sia_fixture())
    cutout = respx.get(access_url()).respond(
        200, content=make_cutout_bytes(shape=(879, 879), stars=())
    )
    response = make_client().get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 200, response.text
    assert png_array(response).shape == (585, 585, 4)
    assert response.headers["x-image-width"] == response.headers["x-image-height"] == "585"
    assert float(response.headers["x-valid-pixel-fraction"]) == pytest.approx(1.0)
    assert cutout.calls.last.request.url.params["size"] == "879pix"


@respx.mock
def test_ac102_max_size_caps_cutout_at_2040_px(make_client):
    respx.get(SIA_URL).respond(200, content=sia_fixture())
    cutout = respx.get(access_url()).respond(200, content=make_cutout_bytes())
    response = make_client().get("/image", params={**IMAGE_PARAMS, "size": 3.0})
    assert response.status_code == 200, response.text
    assert cutout.calls.last.request.url.params["size"] == "2040pix"
    assert png_array(response).shape == (1756, 1756, 4)
    assert response.headers["x-image-width"] == response.headers["x-image-height"] == "1756"


@pytest.mark.parametrize("size", [3.1, 0.005])
def test_ac103_size_out_of_range(make_client, size):
    client, sia, cutout = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, "size": size})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert [f["field"] for f in error["details"]["fields"]] == ["size"]
    assert sia.calls == [] and cutout.calls == []


def test_ac104_upscale_headers_and_dimensions(make_client):
    client, _, _ = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 1.0, "upscale": 2})
    assert response.status_code == 200, response.text
    assert png_array(response).shape == (1170, 1170, 4)
    h = response.headers
    assert h["x-image-width"] == h["x-image-height"] == "1170"
    assert h["x-upscale"] == "2"
    assert h["x-pixel-scale-arcsec"] == "3.075"
    assert h["x-native-pixel-scale-arcsec"] == "6.15"


@pytest.mark.parametrize(("upscale", "scale"), [(1, "6.15"), (3, "2.05"), (4, "1.5375")])
def test_pixel_scale_header_formatting(make_client, upscale, scale):
    client, _, _ = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.1, "upscale": upscale})
    assert response.status_code == 200
    assert response.headers["x-pixel-scale-arcsec"] == scale
    assert response.headers["x-image-width"] == str(59 * upscale)


@pytest.mark.parametrize("upscale", [0, 5, 1.5, "x"])
def test_upscale_validation(make_client, upscale):
    client, sia, _ = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, "upscale": upscale})
    assert response.status_code == 422
    assert response.json()["error"]["details"]["fields"][0]["field"] == "upscale"
    assert sia.calls == []


@respx.mock
def test_ac105_too_large_without_any_irsa_call(make_client):
    route = respx.route().respond(500)
    response = make_client().get("/image", params={**IMAGE_PARAMS, "size": 3.0, "upscale": 4})
    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "REQUEST_TOO_LARGE",
        "message": "Output image side 7024 px exceeds the limit of 4096 px.",
        "details": {
            "requested_edge_px": 7024,
            "max_edge_px": 4096,
            "suggestion": "reduce size or upscale",
        },
    }
    assert not route.called and respx.calls.call_count == 0


def test_max_output_edge_from_settings(make_client):
    client, sia, cutout = fake_client(make_client, max_output_edge_px=1000)
    response = client.get("/image", params={**IMAGE_PARAMS, "upscale": 2})
    assert response.status_code == 422
    assert response.json()["error"]["details"]["requested_edge_px"] == 1170
    assert sia.calls == [] and cutout.calls == []
    assert client.get("/image", params={**IMAGE_PARAMS, "size": 0.25}).status_code == 200


@pytest.mark.parametrize("upscale", [1, 2])
def test_ac107_align_false_uses_smaller_cutout_as_delivered(make_client, upscale):
    # Near the detector edge IRSA returns less than the requested 586 px square.
    payload = make_cutout_bytes(shape=(200, 300))
    client, _, cutout = fake_client(make_client, payload)
    response = client.get("/image", params={**IMAGE_PARAMS, "align": False, "upscale": upscale})
    assert response.status_code == 200, response.text
    assert cutout.calls[-1][3] == 586
    assert png_array(response).shape == (200 * upscale, 300 * upscale, 4)
    assert response.headers["x-image-width"] == str(300 * upscale)
    assert response.headers["x-image-height"] == str(200 * upscale)
    assert float(response.headers["x-valid-pixel-fraction"]) == pytest.approx(1.0)


def test_upscale_valid_fraction_matches_png_alpha(make_client):
    client, _, _ = fake_client(make_client, make_cutout_bytes(shape=(60, 60)))
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.25, "upscale": 2})
    assert response.status_code == 200
    alpha = png_array(response)[..., 3]
    fraction = float(response.headers["x-valid-pixel-fraction"])
    assert fraction == pytest.approx((alpha > 0).mean(), abs=1e-4)
    assert 0 < fraction < 1


def _holed_payload() -> bytes:
    hole = {(r, c): ["HOT"] for r in range(100, 103) for c in range(100, 103)}
    return make_cutout_bytes(flag_pixels=hole)


@pytest.mark.parametrize("align", [False, True])
def test_fill_holes_default_keeps_masked_pixels_transparent(make_client, align):
    client, _, _ = fake_client(make_client, _holed_payload())
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.25, "align": align})
    assert response.status_code == 200
    assert (png_array(response)[..., 3] == 0).any()
    assert float(response.headers["x-valid-pixel-fraction"]) < 1.0


@pytest.mark.parametrize("align", [False, True])
def test_fill_holes_true_fills_small_masked_holes(make_client, align):
    client, _, _ = fake_client(make_client, _holed_payload())
    response = client.get(
        "/image", params={**IMAGE_PARAMS, "size": 0.25, "align": align, "fill_holes": True}
    )
    assert response.status_code == 200
    assert (png_array(response)[..., 3] == 255).all()
    assert float(response.headers["x-valid-pixel-fraction"]) == 1.0


def test_fill_holes_keeps_uncovered_area_transparent(make_client):
    client, _, _ = fake_client(make_client, make_cutout_bytes(shape=(60, 60)))
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.25, "fill_holes": True})
    assert response.status_code == 200
    assert 0 < float(response.headers["x-valid-pixel-fraction"]) < 1


def test_sia_resolution_uses_small_radius_and_collection(make_client):
    client, sia, _ = fake_client(make_client)
    client.get("/image", params={**IMAGE_PARAMS, "collection": "spherex_qr3_deep"})
    ra, dec, radius, collection, *_ = sia.calls[-1]
    # REQ-501: normalized position (6.15" grid).
    assert (ra, dec, radius, collection.value) == (210.8015, 54.348917, 0.001, "spherex_qr3_deep")


def test_ac011_explicit_scale(make_client):
    # IMAGE = 10.5, ZODI = 0.5 -> every pixel is exactly 10 MJy/sr after subtraction.
    payload = make_cutout_bytes(stars=(), background=10.0, noise_sigma=0.0, zodi_level=0.5)
    client, _, _ = fake_client(make_client, payload)
    response = client.get(
        "/image", params={**IMAGE_PARAMS, "align": False, "scale_min": 0, "scale_max": 10}
    )
    assert response.status_code == 200
    assert response.headers["x-scale-min"] == "0.0"
    assert response.headers["x-scale-max"] == "10.0"
    top = matplotlib.colormaps["inferno"](1.0, bytes=True)
    assert tuple(png_array(response)[5, 5]) == tuple(top)


def test_flags_hot_pixel_transparent_source_opaque(make_client):
    payload = make_cutout_bytes(flag_pixels={(10, 20): ["HOT"], (10, 30): ["SOURCE"]})
    client, _, _ = fake_client(make_client, payload)
    rgba = png_array(client.get("/image", params={**IMAGE_PARAMS, "align": False}))
    rows = rgba.shape[0]
    assert rgba[rows - 1 - 10, 20, 3] == 0
    assert rgba[rows - 1 - 10, 30, 3] == 255


def test_flags_reject_names_from_settings(make_client):
    payload = make_cutout_bytes(flag_pixels={(10, 20): ["HOT"]})
    client, _, _ = fake_client(make_client, payload, flags_reject_names="COLD")
    rgba = png_array(client.get("/image", params={**IMAGE_PARAMS, "align": False}))
    assert rgba[rgba.shape[0] - 1 - 10, 20, 3] == 255


def test_empty_image_when_everything_masked(make_client):
    shape = (40, 40)
    every_pixel = {(r, c): ["HOT"] for r in range(shape[0]) for c in range(shape[1])}
    client, _, _ = fake_client(make_client, make_cutout_bytes(shape=shape, flag_pixels=every_pixel))
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_IMAGE"


def test_empty_image_when_cutout_does_not_overlap(make_client):
    far = make_cutout_bytes(ra=100.0, dec=-20.0)
    client, _, _ = fake_client(make_client, far)
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "EMPTY_IMAGE"


def test_partial_coverage_is_transparent(make_client):
    client, _, _ = fake_client(make_client, make_cutout_bytes(shape=(60, 60)))
    response = client.get("/image", params={**IMAGE_PARAMS, "size": 0.25})
    assert response.status_code == 200
    fraction = float(response.headers["x-valid-pixel-fraction"])
    assert 0 < fraction < 1
    assert (png_array(response)[..., 3] == 0).any()


def test_missing_zodi_still_renders(make_client, caplog):
    client, _, _ = fake_client(make_client, make_cutout_bytes(extensions=("IMAGE", "FLAGS")))
    with caplog.at_level(logging.WARNING):
        assert client.get("/image", params=IMAGE_PARAMS).status_code == 200
    assert "zodi_hdu_missing" in {getattr(r, "event", None) for r in caplog.records}


def test_invalid_fits_is_502(make_client):
    client, _, _ = fake_client(make_client, b"<html>not fits</html>")
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_INVALID_RESPONSE"


def test_gzip_bomb_is_rejected(make_client):
    import gzip

    bomb = gzip.compress(b"SIMPLE  =" + b"\0" * 2_000_000)
    client, _, _ = fake_client(make_client, bomb, irsa_max_cutout_bytes=1_000_000)
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_INVALID_RESPONSE"


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"ra": 400}, "ra"),
        ({"dec": -91}, "dec"),
        ({"scale_min": 1}, "scale_max"),
        ({"scale_max": 1}, "scale_max"),
        ({"scale_min": 2, "scale_max": 1}, "scale_max"),
        ({"scale_min": 1, "scale_max": 1}, "scale_max"),
        ({"scale_min": "inf", "scale_max": 1}, "scale_min"),
        ({"percentile_low": 50, "percentile_high": 40}, "percentile_high"),
        ({"percentile_low": 99.5}, "percentile_high"),
        ({"percentile_high": 101}, "percentile_high"),
        ({"percentile_low": -1}, "percentile_low"),
        ({"size": 0.001}, "size"),
        ({"size": 3.5}, "size"),
        ({"fill_holes": "maybe"}, "fill_holes"),
        ({"observation_id": "../etc/passwd"}, "observation_id"),
        ({"observation_id": "a" * 65}, "observation_id"),
        ({"detector": "D0"}, "detector"),
        ({"stretch": "cubic"}, "stretch"),
        ({"colormap": "jet"}, "colormap"),
        ({"align": "maybe"}, "align"),
        ({"collection": "wise"}, "collection"),
    ],
)
def test_ac007_image_validation(make_client, params, field):
    client, sia, cutout = fake_client(make_client)
    response = client.get("/image", params={**IMAGE_PARAMS, **params})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in [f["field"] for f in error["details"]["fields"]]
    assert sia.calls == [] and cutout.calls == []


def test_ac007_missing_required_image_params(make_client):
    client, _, _ = fake_client(make_client)
    response = client.get("/image", params=M101)
    fields = {f["field"] for f in response.json()["error"]["details"]["fields"]}
    assert response.status_code == 422
    assert fields == {"observation_id", "detector"}


@respx.mock
@pytest.mark.parametrize(
    ("observation_id", "detector"),
    [("2026W20_2A_0464_9", "D2"), (OBS_ID, "D1")],
)
def test_ac012_not_found_without_cutout(make_client, observation_id, detector):
    respx.get(SIA_URL).respond(200, content=sia_fixture())
    response = make_client().get(
        "/image", params={**M101, "observation_id": observation_id, "detector": detector}
    )
    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "OBSERVATION_NOT_FOUND"
    assert observation_id in error["message"]
    assert respx.calls.call_count == 1  # only the SIA query


@respx.mock
def test_ac013_foreign_access_url_is_never_contacted(make_client):
    original = next(r for r in parsed_fixture().records if r.observation_id == OBS_ID)
    evil = type(original)(**{**original.__dict__, "access_url": "https://evil.example.com/x.fits"})
    evil_route = respx.get("https://evil.example.com/x.fits").respond(200, content=b"SIMPLE")
    client = make_client(sia=FakeSia(SiaResult(records=[evil])))
    response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_INVALID_RESPONSE"
    assert "evil" not in response.text
    assert not evil_route.called


@respx.mock
def test_ac014_cutout_retries_then_upstream_error(make_client):
    respx.get(SIA_URL).respond(200, content=sia_fixture())
    cutout = respx.get(access_url()).respond(503)
    response = make_client(irsa_max_retries=1).get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"
    assert cutout.call_count == 2


@respx.mock
def test_ac014_sia_retries_on_image_route(make_client):
    sia = respx.get(SIA_URL).respond(503)
    response = make_client(irsa_max_retries=1).get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "UPSTREAM_ERROR"
    assert sia.call_count == 2


@respx.mock
def test_ac015_cutout_timeout(make_client):
    respx.get(SIA_URL).respond(200, content=sia_fixture())
    respx.get(access_url()).mock(side_effect=httpx.ReadTimeout("slow"))
    response = make_client().get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"


async def test_ac016_server_busy(make_app):
    cutout = FakeCutout(make_cutout_bytes(), delay=0.5)
    app = make_app(
        sia=FakeSia(), cutout=cutout, max_concurrent_renders=1, render_queue_timeout_seconds=0.1
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Two different images: with the cache on, identical requests share one render
            # (single-flight, REQ-532) and would not compete for the semaphore.
            responses = await asyncio.gather(
                client.get("/image", params=IMAGE_PARAMS),
                client.get("/image", params={**IMAGE_PARAMS, "stretch": "linear"}),
            )
    assert sorted(r.status_code for r in responses) == [200, 503]
    busy = next(r for r in responses if r.status_code == 503)
    assert busy.json()["error"]["code"] == "SERVER_BUSY"
    assert len(cutout.calls) == 1


def test_semaphore_released_after_errors(make_client):
    cutout = FakeCutout(b"garbage")
    client = make_client(
        sia=FakeSia(), cutout=cutout, max_concurrent_renders=1, render_queue_timeout_seconds=0.1
    )
    for _ in range(3):
        assert client.get("/image", params=IMAGE_PARAMS).status_code == 502


def test_unexpected_error_is_500_without_internals(make_client, caplog):
    cutout = FakeCutout(b"", error=RuntimeError("secret /internal/path"))
    client = make_client(sia=FakeSia(), cutout=cutout)
    with caplog.at_level(logging.ERROR):
        response = client.get("/image", params=IMAGE_PARAMS)
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": "Internal server error.", "details": {}}
    }
    record = next(r for r in caplog.records if getattr(r, "event", None) == "internal_error")
    assert record.exc_info is not None


def test_step_durations_are_logged(make_client, caplog):
    client, _, _ = fake_client(make_client)
    with caplog.at_level(logging.INFO):
        assert client.get("/image", params=IMAGE_PARAMS).status_code == 200
    events = {
        r.event: r
        for r in caplog.records
        if getattr(r, "event", "").startswith("image_")
        and not r.event.startswith("image_cache")  # cache events carry lookup_ms/upload_ms
    }
    assert {"image_sia", "image_cutout", "image_processing"} <= set(events)
    assert all(isinstance(r.duration_ms, float) for r in events.values())
