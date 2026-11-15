"""Phase B of spec-tool-spherex-image-quality: mode=rgb and stack=true on GET /image."""

import asyncio
import io
import logging
import time
from collections.abc import Callable, Mapping
from dataclasses import replace

import httpx
import numpy as np
import pytest
from PIL import Image

from app.domain.errors import UpstreamError, UpstreamTimeoutError
from app.domain.models import Detector, ImageRecord, SiaResult
from app.processing.timeutils import mjd_to_iso
from tests.integration.conftest import M101, FakeSia, parsed_fixture
from tests.synthetic_fits import (
    Star,
    make_channel_cutout_bytes,
    make_cutout_bytes,
    make_visit_cutout_bytes,
)

# sia_visit_multi.xml mirrors real IRSA geometry: each observation covers M101 with one
# detector pair. Visit 1 (W20 _1.._12) cycles D1+D4, D2+D5, D3+D6 (_5 has D2 only);
# visit 2 (W46 _1.._4) has only D1+D4 / D2+D5, so D3 is missing from the whole visit.
VISIT = "sia_visit_multi.xml"
W20 = "2026W20_2A_0464_"
REF = W20 + "3"  # D3+D6
NO_D3_VISIT = "2026W46_2A_0212_2"  # D2+D5, in a visit without D3
SMALL = {"size": 0.25}  # 146 px output, 220 px cutouts: fast and fully covered
RGB = {**M101, "observation_id": REF, "mode": "rgb", **SMALL}
SINGLE = {**M101, "observation_id": REF, "detector": "D3", **SMALL}
# Default D3,D2,D1 from REF: R is REF itself, G the previous exposure, B the next one.
RGB_ANCHORS = [REF, W20 + "2", W20 + "4"]


def records() -> list[ImageRecord]:
    return parsed_fixture(VISIT).records


def record(obs: str, det: str, recs: list[ImageRecord] | None = None) -> ImageRecord:
    return next(r for r in recs or records() if r.observation_id == obs and r.detector.value == det)


def every_observation_with(det: str) -> list[ImageRecord]:
    """The fixture plus a synthetic `det` image in every observation that lacks it.

    Stack tests need more frames of one detector than a real visit offers (4 at most).
    """
    recs = records()
    have = {r.observation_id for r in recs if r.detector.value == det}
    first: dict[str, ImageRecord] = {}
    for r in recs:
        first.setdefault(r.observation_id, r)
    extra = [
        replace(r, detector=Detector(det), access_url=f"{r.access_url}?synthetic={det}")
        for obs, r in first.items()
        if obs not in have
    ]
    return recs + extra


class MapCutout:
    """Cutout fake answering per access_url: `payload(record)` bytes, or the mapped error."""

    def __init__(
        self,
        payload: Callable[[ImageRecord], bytes],
        *,
        errors: Mapping[str, Exception] | None = None,
        delay: float = 0.0,
        recs: list[ImageRecord] | None = None,
    ) -> None:
        self._by_url = {r.access_url: r for r in recs or records()}
        self._payload = payload
        self._errors = dict(errors or {})
        self.delay = delay
        self.calls: list[ImageRecord] = []
        self.in_flight = 0
        self.max_in_flight = 0

    async def fetch(self, access_url: str, ra: float, dec: float, size_px: int) -> bytes:
        rec = self._by_url[access_url]
        self.calls.append(rec)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            if access_url in self._errors:
                raise self._errors[access_url]
            return self._payload(rec)
        finally:
            self.in_flight -= 1


_PLAIN = make_cutout_bytes()


def plain(_: ImageRecord) -> bytes:
    return _PLAIN


def by_detector(payloads: Mapping[str, bytes]) -> Callable[[ImageRecord], bytes]:
    return lambda rec: payloads[rec.detector.value]


def client_for(make_client, cutout: MapCutout, sia: FakeSia | None = None, **settings):
    sia = sia or FakeSia(parsed_fixture(VISIT))
    return make_client(sia=sia, cutout=cutout, **settings), sia


def png_array(response) -> np.ndarray:
    image = Image.open(io.BytesIO(response.content))
    assert image.mode == "RGBA"
    return np.asarray(image)


def error(response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text
    body = response.json()["error"]
    assert body["code"] == code
    return body


# --- RGB --------------------------------------------------------------------------------


def test_ac201_rgb_defaults_to_d3_d2_d1_from_closest_exposures(
    make_client, synthetic_channel_bytes
):
    cutout = MapCutout(by_detector(synthetic_channel_bytes))
    client, _ = client_for(make_client, cutout)
    response = client.get("/image", params=RGB)
    assert response.status_code == 200, response.text
    h = response.headers
    assert h["x-mode"] == "rgb"
    assert h["x-detector"] == "D3,D2,D1"
    assert h["x-observation-id"] == REF
    assert h["x-observation-time"] == mjd_to_iso(record(REF, "D3").start_mjd)
    assert h["x-channel-observation-ids"] == ",".join(RGB_ANCHORS)
    anchors = [record(obs, d) for obs, d in zip(RGB_ANCHORS, ("D3", "D2", "D1"), strict=True)]
    span = (anchors[2].end_mjd - anchors[1].start_mjd) * 86400  # from _2 t_min to _4 t_max
    assert float(h["x-channel-time-span-seconds"]) == pytest.approx(span, abs=1e-3)
    assert sorted((r.observation_id, r.detector.value) for r in cutout.calls) == sorted(
        (a.observation_id, a.detector.value) for a in anchors
    )
    assert png_array(response).shape == (146, 146, 4)


def test_rgb_per_channel_headers_from_anchors(make_client, synthetic_channel_bytes):
    client, _ = client_for(make_client, MapCutout(by_detector(synthetic_channel_bytes)))
    response = client.get("/image", params={**RGB, "detectors": "D6,D4,D2"})
    assert response.status_code == 200, response.text
    # D6 from REF itself; D4 from _4 (1 exposure later, _1 is 2 earlier); D2 from _2.
    anchors = [record(REF, "D6"), record(W20 + "4", "D4"), record(W20 + "2", "D2")]
    h = response.headers
    assert h["x-detector"] == "D6,D4,D2"
    assert h["x-observation-id"] == REF
    assert h["x-observation-time"] == mjd_to_iso(anchors[0].start_mjd)
    assert h["x-channel-observation-ids"] == ",".join(a.observation_id for a in anchors)
    assert h["x-wavelength-min-um"] == ",".join(str(a.wavelength_min_um) for a in anchors)
    assert h["x-wavelength-max-um"] == ",".join(str(a.wavelength_max_um) for a in anchors)
    mins = [float(v) for v in h["x-scale-min"].split(",")]
    maxs = [float(v) for v in h["x-scale-max"].split(",")]
    assert len(mins) == len(maxs) == 3
    assert all(lo < hi for lo, hi in zip(mins, maxs, strict=True))
    assert h["x-upscale"] == "1" and h["x-image-width"] == "146"
    assert not any(name.startswith("x-stack") for name in h)


def test_detectors_with_spaces_are_accepted(make_client, synthetic_channel_bytes):
    client, _ = client_for(make_client, MapCutout(by_detector(synthetic_channel_bytes)))
    response = client.get("/image", params={**RGB, "detectors": " D3, D2 ,D1 "})
    assert response.status_code == 200, response.text
    assert response.headers["x-detector"] == "D3,D2,D1"


def test_ac202_star_only_in_red_channel_is_red(make_client):
    payloads = make_channel_cutout_bytes(stars_per_detector={"D3": [Star(north_px=10)]})
    client, _ = client_for(make_client, MapCutout(by_detector(payloads)))
    response = client.get(
        "/image",
        params={**RGB, "stretch": "linear", "scale_mins": "0,0,0", "scale_maxs": "40,40,40"},
    )
    assert response.status_code == 200, response.text
    rgba = png_array(response).astype(int)
    # Grid center (n - 1) / 2 = 72.5; 10 px north is 10 rows up in the PNG.
    r, g, b, a = rgba[62:64, 72:74].reshape(-1, 4).max(axis=0)
    assert r > 200 and g < 30 and b < 30 and a == 255
    assert rgba[..., 0].argmax() // 146 in (62, 63)


def test_rgb_scale_reuse_changes_nothing_but_headers(make_client, synthetic_channel_bytes):
    client, _ = client_for(make_client, MapCutout(by_detector(synthetic_channel_bytes)))
    first = client.get("/image", params=RGB)
    again = client.get(
        "/image",
        params={
            **RGB,
            "scale_mins": first.headers["x-scale-min"],
            "scale_maxs": first.headers["x-scale-max"],
        },
    )
    assert again.status_code == 200, again.text
    # REQ-503 rounds scale_mins/scale_maxs to 6 significant digits, so the reused scale can
    # differ from the computed one in the 7th digit: at most 1 level per channel.
    diff = np.abs(png_array(again).astype(int) - png_array(first).astype(int))
    assert diff.max() <= 1


def test_ac205_explicit_rgb_scale_headers(make_client, synthetic_channel_bytes):
    client, _ = client_for(make_client, MapCutout(by_detector(synthetic_channel_bytes)))
    response = client.get("/image", params={**RGB, "scale_mins": "0,0,0", "scale_maxs": "10,20,30"})
    assert response.status_code == 200, response.text
    assert response.headers["x-scale-min"] == "0.0,0.0,0.0"
    assert response.headers["x-scale-max"] == "10.0,20.0,30.0"


def test_ac206_pixel_invalid_only_in_green_is_transparent(make_client):
    hole = {(r, c): ["HOT"] for r in range(118, 123) for c in range(118, 123)}
    payloads = make_channel_cutout_bytes(("D1", "D3"))
    payloads["D2"] = make_cutout_bytes(flag_pixels=hole, seed=99)
    client, _ = client_for(make_client, MapCutout(by_detector(payloads)))
    response = client.get("/image", params=RGB)
    assert response.status_code == 200, response.text
    alpha = png_array(response)[..., 3]
    assert (alpha == 0).sum() > 0
    assert alpha[70:76, 70:76].min() == 0  # the hole sits at the grid center
    assert 0.9 < float(response.headers["x-valid-pixel-fraction"]) < 1.0

    full = client.get("/image", params={**SINGLE, "detector": "D3"})
    assert (png_array(full)[..., 3] == 255).all()


def test_rgb_channel_all_nan_is_empty_image(make_client):
    shape = (40, 40)
    masked = make_cutout_bytes(
        shape=shape, flag_pixels={(r, c): ["HOT"] for r in range(40) for c in range(40)}
    )
    payloads = {"D1": masked, "D2": masked, "D3": make_cutout_bytes()}
    client, _ = client_for(make_client, MapCutout(by_detector(payloads)))
    body = error(client.get("/image", params=RGB), 422, "EMPTY_IMAGE")
    assert body["details"] == {"empty_channels": ["D2", "D1"]}  # R,G,B order


def test_ac204_detector_missing_from_the_whole_visit_is_404_without_downloads(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get(
        "/image", params={**RGB, "observation_id": NO_D3_VISIT, "detectors": "D3,D2,D1"}
    )
    body = error(response, 404, "DETECTOR_NOT_AVAILABLE")
    assert body["details"] == {
        "missing_detectors": ["D3"],
        "available_detectors": ["D1", "D2", "D4", "D5"],
    }
    assert cutout.calls == []


def test_rgb_reference_with_one_detector_borrows_the_other_channels(make_client):
    # _5 only has D2: R comes from _6 (next), B from _4 (previous); other visits never count.
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get("/image", params={**RGB, "observation_id": W20 + "5"})
    assert response.status_code == 200, response.text
    h = response.headers
    assert h["x-observation-id"] == W20 + "5"
    assert h["x-channel-observation-ids"] == f"{W20}6,{W20}5,{W20}4"
    assert h["x-observation-time"] == mjd_to_iso(record(W20 + "5", "D2").start_mjd)


def test_rgb_in_a_visit_with_other_detectors(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get(
        "/image", params={**RGB, "observation_id": NO_D3_VISIT, "detectors": "D5,D2,D1"}
    )
    assert response.status_code == 200, response.text
    # D1 tie between _1 and _3 (one exposure away each): the older one wins.
    w46 = "2026W46_2A_0212_"
    assert response.headers["x-channel-observation-ids"] == f"{w46}2,{w46}2,{w46}1"


def test_single_mode_missing_detector_keeps_observation_not_found(make_client):
    # REF lacks D2 although the neighbouring exposure has it: single never borrows.
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get("/image", params={**SINGLE, "detector": "D2"})
    body = error(response, 404, "OBSERVATION_NOT_FOUND")
    assert body["details"] == {"observation_id": REF, "detector": "D2"}
    assert cutout.calls == []


def test_rgb_unknown_observation_is_404(make_client):
    client, _ = client_for(make_client, MapCutout(plain))
    response = client.get("/image", params={**RGB, "observation_id": "2026W20_2A_0464_99"})
    error(response, 404, "OBSERVATION_NOT_FOUND")


async def test_ac207_rgb_downloads_run_concurrently(make_app, synthetic_channel_bytes):
    cutout = MapCutout(by_detector(synthetic_channel_bytes), delay=1.0)
    app = make_app(sia=FakeSia(parsed_fixture(VISIT)), cutout=cutout, cutout_fetch_concurrency=3)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            started = time.perf_counter()
            response = await client.get("/image", params=RGB)
            elapsed = time.perf_counter() - started
    assert response.status_code == 200, response.text
    assert len(cutout.calls) == 3 and cutout.max_in_flight == 3
    assert elapsed < 2.0


def test_fetch_concurrency_is_limited(make_client):
    cutout = MapCutout(plain, delay=0.05)
    client, _ = client_for(make_client, cutout, cutout_fetch_concurrency=2)
    response = client.get("/image", params={**RGB, "stack": True})
    assert response.status_code == 200, response.text
    assert len(cutout.calls) == 12  # 4 exposures per detector in the visit
    assert cutout.max_in_flight == 2


def test_rgb_uses_one_render_slot(make_client, synthetic_channel_bytes):
    client, _ = client_for(
        make_client,
        MapCutout(by_detector(synthetic_channel_bytes)),
        max_concurrent_renders=1,
        render_queue_timeout_seconds=0.1,
    )
    assert client.get("/image", params=RGB).status_code == 200


# --- Validation (REQ-203, REQ-301, 9.2) -------------------------------------------------

BASE = {**M101, "observation_id": REF}


@pytest.mark.parametrize(
    ("params", "field"),
    [
        ({"mode": "rgb", "detector": "D2"}, "detector"),
        ({"mode": "rgb", "align": False}, "align"),
        ({"mode": "single", "detector": "D2", "detectors": "D1,D2,D3"}, "detectors"),
        ({"detector": "D2", "detectors": "D1,D2,D3"}, "detectors"),
        ({"mode": "rgb", "detectors": "D1,D1,D2"}, "detectors"),
        ({"mode": "rgb", "detectors": "D1,D2"}, "detectors"),
        ({"mode": "rgb", "detectors": "D1,D2,D3,D4"}, "detectors"),
        ({"mode": "rgb", "detectors": "D1,D2,D7"}, "detectors"),
        ({"mode": "rgb", "detectors": "d3,d2,d1"}, "detectors"),
        ({"mode": "rgb", "detectors": ""}, "detectors"),
        ({"mode": "rgb", "scale_min": 0, "scale_max": 1}, "scale_min"),
        ({"mode": "rgb", "scale_max": 1}, "scale_max"),
        ({"mode": "rgb", "scale_mins": "0,0,0"}, "scale_maxs"),
        ({"mode": "rgb", "scale_maxs": "1,1,1"}, "scale_maxs"),
        ({"mode": "rgb", "scale_mins": "a,0,0", "scale_maxs": "1,1,1"}, "scale_mins"),
        ({"mode": "rgb", "scale_mins": "0,0", "scale_maxs": "1,1,1"}, "scale_mins"),
        ({"mode": "rgb", "scale_mins": "0,0,0", "scale_maxs": "1,x,1"}, "scale_maxs"),
        ({"mode": "rgb", "scale_mins": "0,0,nan", "scale_maxs": "1,1,1"}, "scale_mins"),
        ({"mode": "rgb", "scale_mins": "0,0,0", "scale_maxs": "1,1,inf"}, "scale_maxs"),
        ({"mode": "rgb", "scale_mins": "0,5,0", "scale_maxs": "1,1,1"}, "scale_maxs"),
        ({"mode": "rgb", "scale_mins": "0,1,0", "scale_maxs": "1,1,1"}, "scale_maxs"),
        ({"detector": "D2", "scale_mins": "0,0,0", "scale_maxs": "1,1,1"}, "scale_mins"),
        ({"detector": "D2", "scale_maxs": "1,1,1"}, "scale_maxs"),
        ({"mode": "single"}, "detector"),
        ({}, "detector"),
        ({"mode": "RGB"}, "mode"),
        ({"mode": "color", "detector": "D2"}, "mode"),
        ({"detector": "D2", "stack": True, "align": False}, "stack"),
        ({"mode": "rgb", "stack": True, "align": False}, "align"),
        ({"detector": "D2", "stack": "maybe"}, "stack"),
        ({"detector": "d2"}, "detector"),
    ],
)
def test_ac203_ac306_invalid_combinations(make_client, params, field):
    cutout = MapCutout(plain)
    client, sia = client_for(make_client, cutout)
    body = error(client.get("/image", params={**BASE, **params}), 422, "VALIDATION_ERROR")
    assert set(body) == {"code", "message", "details"}
    assert field in [f["field"] for f in body["details"]["fields"]]
    assert sia.calls == [] and cutout.calls == []


# --- Stack ------------------------------------------------------------------------------


def _visit_payload(frames: list[bytes]) -> Callable[[ImageRecord], bytes]:
    """Visit frames by time order in the first visit, rotated so REF gets frame 0.

    Frame 0 has no WCS jitter, so the single-frame baseline is not smoothed by reprojection.
    """
    starts: dict[str, float] = {}
    for r in records():
        if r.observation_id.startswith(W20):
            starts[r.observation_id] = min(r.start_mjd, starts.get(r.observation_id, r.start_mjd))
    order = sorted(starts, key=starts.__getitem__)
    ref = order.index(REF)
    return lambda rec: frames[(order.index(rec.observation_id) - ref) % len(frames)]


def _background_std(response) -> float:
    red = png_array(response)[..., 0].astype(float)
    return float(red[10:50, 10:50].std())  # star-free corner


def test_ac301_stack_of_five_reduces_noise(make_client):
    frames = make_visit_cutout_bytes(5, background_levels=[2.0] * 5)
    recs = every_observation_with("D3")
    client, _ = client_for(
        make_client,
        MapCutout(_visit_payload(frames), recs=recs),
        sia=FakeSia(SiaResult(records=recs)),
        stack_max_exposures=5,
    )
    params = {**SINGLE, "stretch": "linear", "scale_min": 1.6, "scale_max": 2.4}
    stacked = client.get("/image", params={**params, "stack": True})
    single = client.get("/image", params=params)
    assert stacked.status_code == single.status_code == 200, stacked.text
    assert stacked.headers["x-stack-count"] == "5"
    assert _background_std(stacked) < 0.6 * _background_std(single)
    assert "x-stack-count" not in single.headers


def test_ac304_twelve_observations_capped_at_eight(make_client):
    recs = every_observation_with("D2")
    cutout = MapCutout(plain, recs=recs)
    client, _ = client_for(
        make_client, cutout, sia=FakeSia(SiaResult(records=recs)), stack_max_exposures=8
    )
    ref = W20 + "10"
    response = client.get(
        "/image", params={**SINGLE, "observation_id": ref, "detector": "D2", "stack": True}
    )
    assert response.status_code == 200, response.text
    expected = [f"{W20}{i}" for i in range(5, 13)]
    h = response.headers
    assert h["x-stack-count"] == "8"
    assert h["x-stack-observation-ids"] == ",".join(expected)
    assert "x-stack-truncated" not in h
    assert sorted(r.observation_id for r in cutout.calls) == sorted(expected)
    used = [record(obs, "D2", recs) for obs in expected]
    span = (used[-1].end_mjd - used[0].start_mjd) * 86400
    assert float(h["x-stack-time-span-seconds"]) == pytest.approx(span, abs=1e-3)
    assert h["x-observation-id"] == ref
    assert h["x-observation-time"] == mjd_to_iso(record(ref, "D2", recs).start_mjd)
    assert not any(name.startswith("x-channel") for name in h)  # rgb only


def test_ac305_visit_with_only_the_reference(make_client):
    only_ref = SiaResult(records=[r for r in records() if r.observation_id == REF])
    client, _ = client_for(make_client, MapCutout(plain), sia=FakeSia(only_ref))
    stacked = client.get("/image", params={**SINGLE, "stack": True})
    plain_response = client.get("/image", params=SINGLE)
    assert stacked.status_code == 200, stacked.text
    assert stacked.headers["x-stack-count"] == "1"
    assert stacked.headers["x-stack-observation-ids"] == REF
    ref = record(REF, "D3")
    assert float(stacked.headers["x-stack-time-span-seconds"]) == pytest.approx(
        (ref.end_mjd - ref.start_mjd) * 86400, abs=1e-3
    )
    assert stacked.content == plain_response.content
    for name in ("x-scale-min", "x-scale-max", "x-valid-pixel-fraction"):
        assert stacked.headers[name] == plain_response.headers[name]


def test_ac307_rgb_stack_large_size_truncated_to_one_frame(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get("/image", params={**RGB, "stack": True, "size": 3.0})
    assert response.status_code == 200, response.text
    h = response.headers
    assert h["x-stack-count"] == "1,1,1"
    assert h["x-stack-truncated"] == "true"
    # The budget keeps exactly the channel anchors.
    assert h["x-stack-observation-ids"] == ",".join(sorted(RGB_ANCHORS))
    assert h["x-channel-observation-ids"] == ",".join(RGB_ANCHORS)
    assert len(cutout.calls) == 3
    assert {r.observation_id for r in cutout.calls} == set(RGB_ANCHORS)


def _calls(cutout: MapCutout, det: str) -> set[str]:
    return {r.observation_id for r in cutout.calls if r.detector.value == det}


def test_rgb_stack_frames_closest_to_the_reference(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, stack_max_exposures=3, max_cutouts_per_request=9)
    response = client.get("/image", params={**RGB, "stack": True})
    assert response.status_code == 200, response.text
    h = response.headers
    assert h["x-stack-count"] == "3,3,3"
    assert _calls(cutout, "D3") == {W20 + i for i in ("3", "6", "9")}
    assert _calls(cutout, "D2") == {W20 + i for i in ("2", "5", "8")}
    assert _calls(cutout, "D1") == {W20 + i for i in ("1", "4", "7")}
    assert h["x-stack-observation-ids"] == ",".join(W20 + str(i) for i in range(1, 10))
    assert h["x-channel-observation-ids"] == ",".join(RGB_ANCHORS)


def test_rgb_stack_counts_per_channel(make_client):
    # Visit 1 has D6 and D4 in 4 exposures each, D5 in 3 (_5 has D2 only).
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, stack_max_exposures=8)
    response = client.get("/image", params={**RGB, "detectors": "D6,D5,D4", "stack": True})
    assert response.status_code == 200, response.text
    h = response.headers
    assert h["x-stack-count"] == "4,3,4"
    assert "x-stack-truncated" not in h
    assert h["x-channel-observation-ids"] == f"{REF},{W20}2,{W20}4"
    used = sorted({(r.start_mjd, r.observation_id) for r in cutout.calls})
    assert h["x-stack-observation-ids"] == ",".join(obs for _, obs in used)


def test_ac308_budget_exceeded_without_downloads(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, max_cutouts_per_request=2)
    body = error(client.get("/image", params=RGB), 422, "REQUEST_TOO_LARGE")
    assert body["details"]["total_cutouts"] == 3
    assert body["details"]["max_cutouts"] == 2
    assert body["details"]["suggestion"] == "reduce size, disable stack, or use mode=single"
    assert cutout.calls == []


def test_ac308_budget_error_does_not_wait_for_a_render_slot(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, max_cutouts_per_request=2, max_concurrent_renders=0)
    error(client.get("/image", params=RGB), 422, "REQUEST_TOO_LARGE")
    error(
        client.get("/image", params={**RGB, "observation_id": NO_D3_VISIT}),
        404,
        "DETECTOR_NOT_AVAILABLE",
    )


@pytest.mark.parametrize(
    ("ref", "detector", "count"),
    [(NO_D3_VISIT, "D2", "2"), (W20 + "12", "D3", "4")],
)
def test_ac309_other_visits_never_enter_the_stack(make_client, ref, detector, count):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, stack_max_exposures=8)
    response = client.get(
        "/image",
        params={**SINGLE, "observation_id": ref, "detector": detector, "stack": True},
    )
    assert response.status_code == 200, response.text
    prefix = ref.rsplit("_", 1)[0]
    ids = response.headers["x-stack-observation-ids"].split(",")
    assert all(i.startswith(prefix) for i in ids)
    assert all(r.observation_id.startswith(prefix) for r in cutout.calls)
    assert response.headers["x-stack-count"] == count


def test_ac309_rgb_anchors_and_stack_stay_in_the_visit(make_client):
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout)
    response = client.get(
        "/image",
        params={**RGB, "observation_id": NO_D3_VISIT, "detectors": "D5,D2,D1", "stack": True},
    )
    assert response.status_code == 200, response.text
    assert all(r.observation_id.startswith("2026W46") for r in cutout.calls)
    assert response.headers["x-stack-count"] == "2,2,2"


@pytest.mark.parametrize("failure", [UpstreamError("HTTP 503"), UpstreamTimeoutError("slow")])
def test_failed_non_anchor_frame_is_dropped(make_client, caplog, failure):
    bad = record(W20 + "6", "D3")
    cutout = MapCutout(plain, errors={bad.access_url: failure})
    client, _ = client_for(make_client, cutout, stack_max_exposures=5)
    with caplog.at_level(logging.WARNING):
        response = client.get("/image", params={**SINGLE, "stack": True})
    assert response.status_code == 200, response.text
    assert response.headers["x-stack-count"] == "3"
    ids = response.headers["x-stack-observation-ids"].split(",")
    assert bad.observation_id not in ids and REF in ids
    dropped = [r for r in caplog.records if getattr(r, "event", None) == "stack_frame_dropped"]
    assert [r.observation_id for r in dropped] == [bad.observation_id]


def test_rgb_failed_non_anchor_frame_is_dropped(make_client):
    bad = record(W20 + "5", "D2")  # in the G stack, but G's anchor is _2
    cutout = MapCutout(plain, errors={bad.access_url: UpstreamError("HTTP 503")})
    client, _ = client_for(make_client, cutout, stack_max_exposures=3, max_cutouts_per_request=9)
    response = client.get("/image", params={**RGB, "stack": True})
    assert response.status_code == 200, response.text
    assert response.headers["x-stack-count"] == "3,2,3"
    assert response.headers["x-channel-observation-ids"] == ",".join(RGB_ANCHORS)


@pytest.mark.parametrize("stack", [False, True])
def test_rgb_failed_anchor_of_another_observation_fails_the_request(make_client, stack):
    anchor = record(W20 + "2", "D2")  # G anchor; not the reference observation
    cutout = MapCutout(plain, errors={anchor.access_url: UpstreamTimeoutError("slow")})
    client, _ = client_for(make_client, cutout)
    error(client.get("/image", params={**RGB, "stack": stack}), 504, "UPSTREAM_TIMEOUT")
    assert client.get("/image", params={**RGB, "observation_id": W20 + "6"}).status_code == 200


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (UpstreamError("HTTP 503"), 502, "UPSTREAM_ERROR"),
        (UpstreamTimeoutError("slow"), 504, "UPSTREAM_TIMEOUT"),
    ],
)
def test_failed_reference_frame_fails_the_request(make_client, failure, status, code):
    cutout = MapCutout(plain, errors={record(REF, "D3").access_url: failure})
    client, _ = client_for(make_client, cutout, stack_max_exposures=5)
    error(client.get("/image", params={**SINGLE, "stack": True}), status, code)
    # The render slot was released.
    again = {**SINGLE, "observation_id": W20 + "4", "detector": "D1"}
    assert client.get("/image", params=again).status_code == 200


def test_stack_rejects_foreign_host_before_any_download(make_client):
    evil = [
        type(r)(**{**r.__dict__, "access_url": "https://evil.example.com/x.fits"})
        if r.observation_id == W20 + "6"
        else r
        for r in records()
    ]
    cutout = MapCutout(plain)
    client, _ = client_for(make_client, cutout, sia=FakeSia(SiaResult(records=evil)))
    error(client.get("/image", params={**SINGLE, "stack": True}), 502, "UPSTREAM_INVALID_RESPONSE")
    assert cutout.calls == []


def test_stack_logs_plan_downloads_and_reprojections(make_client, caplog):
    client, _ = client_for(make_client, MapCutout(plain), stack_max_exposures=3)
    with caplog.at_level(logging.INFO):
        response = client.get("/image", params={**RGB, "stack": True})
    assert response.status_code == 200, response.text
    events: dict[str, list] = {}
    for r in caplog.records:
        events.setdefault(getattr(r, "event", ""), []).append(r)
    plan = events["render_plan"][0]
    assert (plan.mode, plan.stack, plan.total_cutouts, plan.fetch_px) == ("rgb", True, 9, 220)
    assert len(events["image_cutout"]) == len(events["image_reprojection"]) == 9
    assert all(isinstance(r.duration_ms, float) for r in events["image_cutout"])
    total = events["image_render"][0]
    assert total.mode == "rgb" and total.stack_counts == [3, 3, 3]
    assert isinstance(total.duration_ms, float)


# --- CORS / OpenAPI ---------------------------------------------------------------------


def test_cors_exposes_phase_b_headers(make_client):
    client, _ = client_for(make_client, MapCutout(plain))
    response = client.get(
        "/image",
        params={**RGB, "stack": True, "size": 3.0},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200, response.text
    exposed = {
        h.strip().lower() for h in response.headers["access-control-expose-headers"].split(",")
    }
    phase_b = {
        "x-mode",
        "x-detector",
        "x-stack-count",
        "x-stack-observation-ids",
        "x-stack-time-span-seconds",
        "x-stack-truncated",
        "x-channel-observation-ids",
        "x-channel-time-span-seconds",
    }
    assert phase_b <= exposed
    assert {name for name in response.headers if name.startswith("x-")} <= exposed


def test_val104_openapi_documents_phase_b(make_client):
    operation = make_client().get("/openapi.json").json()["paths"]["/image"]["get"]
    params = {p["name"]: p for p in operation["parameters"]}
    for name in ("mode", "detector", "detectors", "scale_mins", "scale_maxs", "stack"):
        assert params[name]["description"], name
        assert "example" in params[name], name
    assert params["detector"].get("required") is not True
    assert params["mode"]["schema"]["default"] == "single"
    assert params["stack"]["schema"]["default"] is False
    assert "Ignored when mode=rgb" in params["colormap"]["description"]
    assert (
        "Median stacking suppresses objects that move between exposures (asteroids, comets). "
        "Use stack=false to look for moving objects." in params["stack"]["description"]
    )
    assert "false-color" in params["mode"]["description"]
    for phrase in ("6.15 arcsec", "more sky, not more detail", "mode=rgb", "stack=true"):
        assert phrase in operation["description"], phrase
    assert "DETECTOR_NOT_AVAILABLE" in operation["responses"]["404"]["description"]
    assert "DETECTOR_NOT_AVAILABLE" in operation["description"]
    assert "REQUEST_TOO_LARGE" in operation["responses"]["422"]["description"]
    assert "max_cutouts" in operation["responses"]["422"]["description"]
    headers = operation["responses"]["200"]["headers"]
    for name in (
        "X-Mode",
        "X-Stack-Count",
        "X-Stack-Observation-Ids",
        "X-Stack-Time-Span-Seconds",
        "X-Stack-Truncated",
        "X-Channel-Observation-Ids",
        "X-Channel-Time-Span-Seconds",
    ):
        assert headers[name]["description"], name
    assert "R,G,B" in headers["X-Detector"]["description"]


def test_epochs_rgb_available_predicts_image_rgb(make_client, synthetic_channel_bytes):
    """The client flow: /epochs picks a visit, /image?mode=rgb works iff rgb_available."""
    cutout = MapCutout(by_detector(synthetic_channel_bytes))
    client, _ = client_for(make_client, cutout)
    visits = client.get("/epochs", params=M101).json()["visits"]
    assert [v["rgb_available"] for v in visits] == [True, False]
    ok, bad = visits
    for obs_id in ok["observation_ids"]:  # any observation of the visit works
        response = client.get("/image", params={**RGB, "observation_id": obs_id})
        assert response.status_code == 200, response.text
    body = error(
        client.get("/image", params={**RGB, "observation_id": bad["observation_ids"][0]}),
        404,
        "DETECTOR_NOT_AVAILABLE",
    )
    assert body["details"]["missing_detectors"] == ["D3"]
