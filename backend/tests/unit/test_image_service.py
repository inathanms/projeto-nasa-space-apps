import asyncio
import gzip
import logging

import numpy as np
import pytest

from app.config import Settings
from app.domain.errors import (
    DetectorNotAvailableError,
    ObservationNotFoundError,
    RequestTooLargeError,
    UpstreamError,
    UpstreamInvalidResponseError,
    UpstreamTimeoutError,
)
from app.domain.models import Collection, Detector, ImageMode, ImageRecord, SiaResult
from app.processing.fits_reader import open_cutout
from app.services.image_service import (
    ImageRequest,
    ImageService,
    check_output_size,
    fetch_pixels,
    output_edge_px,
    prepare_frame,
    process_cutout,
    render_channels,
)
from tests.synthetic_fits import DEFAULT_DEC, DEFAULT_RA, make_cutout_hdul, to_fits_bytes

SETTINGS = Settings(_env_file=None)


def request(**overrides) -> ImageRequest:
    base = {
        "ra": DEFAULT_RA,
        "dec": DEFAULT_DEC,
        "observation_id": "OBS_1",
        "detector": Detector.D2,
        "collection": Collection.QR3,
    }
    return ImageRequest(**(base | overrides))


@pytest.mark.parametrize(
    ("size", "align", "expected"),
    [
        (0.25, True, 220),  # ceil(0.25 * 1.5 * 3600 / 6.15) = ceil(219.5)
        (1.0, True, 879),
        (1.0, False, 586),  # ceil(585.4)
        (0.25, False, 147),
        (3.0, True, 2040),  # capped (2635 otherwise)
        (3.0, False, 1757),
        (0.01, False, 6),
    ],
)
def test_req102_fetch_pixels(size, align, expected):
    assert fetch_pixels(size, align) == expected


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({}, 585),
        ({"upscale": 2}, 1170),
        ({"size": 3.0, "upscale": 4}, 7024),
        ({"size": 0.05, "upscale": 4}, 116),
        ({"size": 0.01}, 16),  # MIN_PIXELS
        ({"size": 1.0, "align": False, "upscale": 2}, 1172),
    ],
)
def test_output_edge_px(overrides, expected):
    assert output_edge_px(request(**overrides)) == expected


def test_req104_check_output_size():
    check_output_size(request(size=3.0, upscale=2), SETTINGS)  # 3512 <= 4096
    with pytest.raises(RequestTooLargeError) as exc:
        check_output_size(request(size=3.0, upscale=4), SETTINGS)
    assert exc.value.http_status == 422
    assert exc.value.details == {
        "requested_edge_px": 7024,
        "max_edge_px": 4096,
        "suggestion": "reduce size or upscale",
    }
    with pytest.raises(RequestTooLargeError):
        check_output_size(request(), Settings(_env_file=None, max_output_edge_px=500))


def test_upscale_resizes_final_image_and_keeps_valid_fraction_coherent():
    raw = to_fits_bytes(make_cutout_hdul(shape=(30, 20)))
    one = process_cutout(raw, request(align=False), SETTINGS)
    three = process_cutout(raw, request(align=False, upscale=3), SETTINGS)
    assert (one.width, one.height) == (20, 30)
    assert (three.width, three.height) == (60, 90)
    assert three.valid_fraction == 1.0
    assert (one.vmin, one.vmax) == (three.vmin, three.vmax)


def test_upscale_happens_after_reprojection():
    raw = to_fits_bytes(make_cutout_hdul(rotation_deg=30))
    result = process_cutout(raw, request(size=0.1, upscale=2), SETTINGS)
    assert (result.width, result.height) == (118, 118)  # pixel_count(0.1) = 59


def _holed_cutout() -> bytes:
    hole = {(r, c): ["HOT"] for r in range(20, 23) for c in range(20, 23)}
    return to_fits_bytes(make_cutout_hdul(shape=(60, 60), flag_pixels=hole))


def test_fill_holes_off_keeps_masked_pixels_transparent():
    result = process_cutout(_holed_cutout(), request(align=False), SETTINGS)
    assert result.valid_fraction == pytest.approx(1 - 9 / 3600)


def test_fill_holes_on_fills_small_holes():
    result = process_cutout(_holed_cutout(), request(align=False, fill_holes=True), SETTINGS)
    assert result.valid_fraction == 1.0


def test_zodi_subtraction_toggle():
    raw = to_fits_bytes(make_cutout_hdul(stars=(), noise_sigma=0.0, background=1.0))
    on = process_cutout(raw, request(align=False, scale_min=0, scale_max=5), SETTINGS)
    off = process_cutout(
        raw, request(align=False, subtract_zodi=False, scale_min=0, scale_max=5), SETTINGS
    )
    assert on.png != off.png


def test_shape_mismatch_skips_zodi_and_flags(caplog):
    hdul = make_cutout_hdul(shape=(40, 40))
    hdul["ZODI"].data = np.zeros((10, 10), dtype=np.float32)
    hdul["FLAGS"].data = np.full((10, 10), -1, dtype=np.int32)
    with caplog.at_level(logging.WARNING):
        result = process_cutout(to_fits_bytes(hdul), request(align=False), SETTINGS)
    assert result.valid_fraction == 1.0
    events = {getattr(r, "event", None) for r in caplog.records}
    assert {"zodi_shape_mismatch", "flags_shape_mismatch"} <= events


def test_unusable_wcs_is_upstream_invalid():
    hdul = make_cutout_hdul(shape=(40, 40))
    for key in ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CDELT1", "CDELT2"):
        hdul["IMAGE"].header.remove(key, ignore_missing=True)
    with pytest.raises(UpstreamInvalidResponseError):
        process_cutout(to_fits_bytes(hdul), request(), SETTINGS)


class _Sia:
    def __init__(self, records):
        self.records = records

    async def search(self, *args, **kwargs):
        return SiaResult(records=self.records)


class _Cutout:
    def __init__(self):
        self.calls = 0

    async def fetch(self, *args):
        self.calls += 1
        return to_fits_bytes(make_cutout_hdul())


def _record(**overrides) -> ImageRecord:
    base = {
        "observation_id": "OBS_1",
        "detector": Detector.D2,
        "wavelength_min_um": 1.1,
        "wavelength_max_um": 1.6,
        "start_mjd": 61177.0,
        "end_mjd": 61177.1,
        "exposure_seconds": 100.0,
        "center_ra": DEFAULT_RA,
        "center_dec": DEFAULT_DEC,
        "footprint": [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)],
        "access_url": "https://irsa.ipac.caltech.edu/ibe/data/x.fits",
    }
    return ImageRecord(**(base | overrides))


async def test_render_returns_metadata():
    service = ImageService(_Sia([_record()]), _Cutout(), SETTINGS, asyncio.Semaphore(1))
    result = await service.render(request())
    assert (result.width, result.height) == (585, 585)
    assert result.vmin < result.vmax
    assert result.record.observation_id == "OBS_1"
    assert result.upscale == 1
    assert result.pixel_scale_arcsec == 6.15
    assert set(result.timings_ms) == {"sia", "cutout", "processing", "total"}


async def test_render_too_large_before_any_upstream_call():
    sia_calls = []

    class _CountingSia(_Sia):
        async def search(self, *args, **kwargs):
            sia_calls.append(args)
            return await super().search(*args, **kwargs)

    cutout = _Cutout()
    service = ImageService(_CountingSia([_record()]), cutout, SETTINGS, asyncio.Semaphore(1))
    with pytest.raises(RequestTooLargeError):
        await service.render(request(size=3.0, upscale=4))
    assert sia_calls == [] and cutout.calls == 0


async def test_render_not_found_wrong_detector():
    cutout = _Cutout()
    service = ImageService(
        _Sia([_record(detector=Detector.D1)]), cutout, SETTINGS, asyncio.Semaphore(1)
    )
    with pytest.raises(ObservationNotFoundError):
        await service.render(request())
    assert cutout.calls == 0


async def test_render_rejects_foreign_host_before_fetch():
    cutout = _Cutout()
    record = _record(access_url="https://evil.example.com/x.fits")
    service = ImageService(_Sia([record]), cutout, SETTINGS, asyncio.Semaphore(1))
    with pytest.raises(UpstreamInvalidResponseError):
        await service.render(request())
    assert cutout.calls == 0


# --- gzip handling in fits_reader -------------------------------------------------------


def test_gzip_bomb_aborts_before_full_inflation():
    bomb = gzip.compress(b"SIMPLE  =" + b"\0" * 5_000_000)
    with pytest.raises(UpstreamInvalidResponseError, match="too large"):
        open_cutout(bomb, max_bytes=1_000_000)


def test_plain_payload_over_limit_rejected():
    with pytest.raises(UpstreamInvalidResponseError, match="too large"):
        open_cutout(b"SIMPLE  =" + b" " * 100, max_bytes=50)


def test_gzip_within_limit_and_multi_member():
    raw = to_fits_bytes(make_cutout_hdul(shape=(20, 20)))
    half = len(raw) // 2
    data = gzip.compress(raw[:half]) + gzip.compress(raw[half:])
    hdus = open_cutout(data, max_bytes=len(raw))
    assert hdus.image_data.shape == (20, 20)


def test_truncated_gzip_rejected():
    data = gzip.compress(to_fits_bytes(make_cutout_hdul(shape=(20, 20))))
    with pytest.raises(UpstreamInvalidResponseError, match="gzip"):
        open_cutout(data[: len(data) // 2])


# --- Phase B: channels, RGB rendering, budget before the render slot -------------------


def test_channels_per_mode():
    assert request().channels == (Detector.D2,)
    rgb = request(detector=None, mode=ImageMode.RGB)
    assert rgb.channels == (Detector.D3, Detector.D2, Detector.D1)
    custom = request(
        detector=None, mode=ImageMode.RGB, detectors=(Detector.D6, Detector.D4, Detector.D2)
    )
    assert custom.channels == (Detector.D6, Detector.D4, Detector.D2)
    with pytest.raises(ValueError, match="detector"):
        _ = request(detector=None).channels


def test_render_channels_rgb_fill_holes_and_explicit_scale():
    frame = np.ones((20, 20), dtype=np.float32)
    holed = frame.copy()
    holed[10, 10] = np.nan
    req = request(
        detector=None,
        mode=ImageMode.RGB,
        fill_holes=True,
        scale_mins=(0.0, 0.0, 0.0),
        scale_maxs=(1.0, 2.0, 4.0),
    )
    result = render_channels([[frame], [holed], [frame]], req)
    assert result.valid_fraction == 1.0
    assert (result.vmins, result.vmaxs) == ((0.0, 0.0, 0.0), (1.0, 2.0, 4.0))


def test_render_channels_stacks_frames():
    rng = np.random.default_rng(0)
    frames = [rng.normal(1.0, 0.1, (30, 30)).astype(np.float32) for _ in range(5)]
    single = render_channels([frames[:1]], request(stack=True))
    stacked = render_channels([frames], request(stack=True))
    assert single.png != stacked.png


def test_prepare_frame_all_masked_returns_nan_grid():
    shape = (30, 30)
    every = {(r, c): ["HOT"] for r in range(shape[0]) for c in range(shape[1])}
    raw = to_fits_bytes(make_cutout_hdul(shape=shape, flag_pixels=every))
    frame = prepare_frame(raw, request(size=0.1), SETTINGS)
    assert frame.shape == (59, 59) and np.isnan(frame).all()


async def test_budget_and_detector_errors_never_take_a_render_slot():
    cutout = _Cutout()
    busy = Settings(_env_file=None, render_queue_timeout_seconds=0.01, max_cutouts_per_request=2)
    rgb = request(detector=None, mode=ImageMode.RGB)

    two = [_record(detector=d) for d in (Detector.D1, Detector.D2)]
    service = ImageService(_Sia(two), cutout, busy, asyncio.Semaphore(0))
    with pytest.raises(DetectorNotAvailableError):
        await service.render(rgb)

    three = [_record(detector=d) for d in (Detector.D1, Detector.D2, Detector.D3)]
    service = ImageService(_Sia(three), cutout, busy, asyncio.Semaphore(0))
    with pytest.raises(RequestTooLargeError):
        await service.render(rgb)
    assert cutout.calls == 0


# --- mode=rgb anchors -------------------------------------------------------------------


class _UrlCutout:
    """Cutout fake that fails for the URLs in `errors` and records every call."""

    def __init__(self, errors: dict[str, Exception] | None = None):
        self.errors = errors or {}
        self.urls: list[str] = []

    async def fetch(self, access_url, *args):
        self.urls.append(access_url)
        if access_url in self.errors:
            raise self.errors[access_url]
        return to_fits_bytes(make_cutout_hdul(shape=(60, 60)))


def _paired_visit() -> list[ImageRecord]:
    """OBS_0 D1+D4, OBS_1 D2+D5, OBS_2 D3+D6, OBS_3 D1+D4, ~4 min apart."""
    pairs = [(Detector.D1, Detector.D4), (Detector.D2, Detector.D5), (Detector.D3, Detector.D6)]
    return [
        _record(
            observation_id=f"OBS_{i}",
            detector=d,
            start_mjd=61177.0 + i * 0.003,
            end_mjd=61177.0013 + i * 0.003,
            access_url=f"https://irsa.ipac.caltech.edu/ibe/data/{i}{d.value}.fits",
        )
        for i in range(4)
        for d in pairs[i % 3]
    ]


def _rgb(**overrides) -> ImageRequest:
    return request(detector=None, mode=ImageMode.RGB, observation_id="OBS_2", size=0.1, **overrides)


async def test_rgb_result_has_reference_and_anchors():
    service = ImageService(_Sia(_paired_visit()), _UrlCutout(), SETTINGS, asyncio.Semaphore(1))
    result = await service.render(_rgb())
    assert (result.reference.observation_id, result.reference.detector) == ("OBS_2", Detector.D3)
    assert result.record is result.reference
    assert [(a.observation_id, a.detector) for a in result.anchors] == [
        ("OBS_2", Detector.D3),
        ("OBS_1", Detector.D2),
        ("OBS_3", Detector.D1),
    ]
    assert result.used_frames == tuple((a,) for a in result.anchors)


@pytest.mark.parametrize(
    "failure", [UpstreamError("HTTP 503"), UpstreamTimeoutError("slow")], ids=["5xx", "timeout"]
)
async def test_rgb_failed_anchor_propagates_even_if_not_the_reference(failure):
    anchor = next(r for r in _paired_visit() if r.observation_id == "OBS_1")
    cutout = _UrlCutout({anchor.access_url: failure})
    service = ImageService(_Sia(_paired_visit()), cutout, SETTINGS, asyncio.Semaphore(1))
    with pytest.raises(type(failure)):
        await service.render(_rgb())


async def test_rgb_stack_drops_failed_non_anchor_frame():
    extra = next(r for r in _paired_visit() if r.observation_id == "OBS_0")  # D1, not B anchor
    cutout = _UrlCutout({extra.access_url: UpstreamError("HTTP 503")})
    service = ImageService(_Sia(_paired_visit()), cutout, SETTINGS, asyncio.Semaphore(1))
    result = await service.render(_rgb(stack=True))
    assert result.stack_counts == (1, 1, 1)
    assert extra.access_url in cutout.urls
    assert result.used_frames[2] == (result.anchors[2],)
