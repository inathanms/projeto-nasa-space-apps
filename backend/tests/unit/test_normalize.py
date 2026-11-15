import pytest

from app.cache.normalize import normalize_dec, normalize_ra, normalize_request, normalize_sia_args
from app.domain.models import Collection, Detector, ImageMode
from app.services.image_service import ImageRequest

Q = 6.15


def make(**kw) -> ImageRequest:
    base = {
        "ra": 210.80227,
        "dec": 54.34892,
        "observation_id": "2026W20_2A_0464_3",
        "collection": Collection.QR3,
        "detector": Detector.D2,
    }
    return ImageRequest(**{**base, **kw})


def test_ra_quantized_to_grid():
    assert normalize_ra(210.80227, Q) == 210.8015
    assert normalize_ra(210.80180, Q) == 210.8015
    assert normalize_ra(210.80250, Q) == 210.803208


def test_ra_wraps_to_zero():
    # AC-502: rounds to 360.0 with a 1-degree quantum -> 0.0
    assert normalize_ra(359.9999, 3600.0) == 0.0
    assert normalize_ra(360.0, 3600.0) == 0.0


def test_ac502_ra_rounding_up_to_360_is_zero_with_default_quantum():
    # 360 is not a multiple of 6.15": the grid point above 359.9999 is 360.0005, i.e. ~360,
    # which must become 0.0 (on the grid), not 0.0005 (off the grid, re-normalizes to 0.0).
    assert normalize_ra(359.9999, Q) == 0.0
    assert normalize_ra(359.99999, Q) == 0.0


def test_normalization_is_idempotent():
    # The route normalizes and the cache service / CachedSiaClient normalize again: the
    # second pass must not move the position (else query echo, key and render disagree).
    values = [i * 0.0137 for i in range(-1000, 27000)] + [359.9991, 359.9999, -0.0001, 719.9999]
    for value in values:
        ra = normalize_ra(value, Q)
        assert 0.0 <= ra < 360.0
        assert normalize_ra(ra, Q) == ra, value
        dec = normalize_dec(value / 4 - 90, Q)
        assert normalize_dec(dec, Q) == dec, value


def test_ra_near_360_stays_below_360():
    for ra in (359.9999, 359.99999, 359.999999, 359.9985):
        out = normalize_ra(ra, Q)
        assert 0.0 <= out < 360.0


def test_ra_negative_and_tiny_negative():
    assert normalize_ra(-0.0000001, Q) == 0.0
    assert str(normalize_ra(-0.0000001, Q)) == "0.0"
    assert 0.0 <= normalize_ra(-10.0, Q) < 360.0
    assert normalize_ra(-10.0, Q) == pytest.approx(350.0, abs=Q / 3600)


def test_dec_clamped_at_poles():
    assert normalize_dec(90.0004, Q) == 90.0
    assert normalize_dec(-90.0004, Q) == -90.0
    assert normalize_dec(95.0, Q) == 90.0
    assert normalize_dec(-120.0, Q) == -90.0


def test_dec_no_negative_zero():
    assert str(normalize_dec(-0.0000001, Q)) == "0.0"


def test_dec_quantized():
    assert normalize_dec(54.34892, Q) == pytest.approx(54.34892, abs=Q / 3600 / 2)
    assert normalize_dec(54.34892, Q) == round(normalize_dec(54.34892, Q), 6)


def test_quantum_must_be_positive():
    with pytest.raises(ValueError):
        normalize_ra(1.0, 0)
    with pytest.raises(ValueError):
        normalize_dec(1.0, -1)


def test_normalize_request_rounds_values():
    req = make(
        size=1.23456,
        percentile_low=1.04,
        percentile_high=99.56,
        scale_min=0.123456789,
        scale_max=1234.56789,
    )
    out = normalize_request(req, Q)
    assert out.ra == 210.8015
    assert out.size == 1.23
    assert out.percentile_low == 1.0
    assert out.percentile_high == 99.6
    assert out.scale_min == 0.123457
    assert out.scale_max == 1234.57
    assert req.ra == 210.80227  # input untouched (frozen dataclass)


def test_normalize_request_rgb_scales():
    req = make(
        mode=ImageMode.RGB,
        detector=None,
        scale_mins=(0.1234567, 1.0, 2.0),
        scale_maxs=(10.123456789, 20.0, 30.0),
    )
    out = normalize_request(req, Q)
    assert out.scale_mins == (0.123457, 1.0, 2.0)
    assert out.scale_maxs == (10.1235, 20.0, 30.0)


def test_normalize_request_is_idempotent():
    once = normalize_request(make(size=0.987654, scale_min=0.123456789), Q)
    assert normalize_request(once, Q) == once


def test_normalize_request_keeps_none_scales():
    out = normalize_request(make(), Q)
    assert out.scale_min is None and out.scale_mins is None


def test_normalize_sia_args():
    args = normalize_sia_args(
        210.80227, 90.0004, 0.001000004, Collection.QR3, 60000.1234567, None, 500, Q
    )
    assert args == {
        "collection": "spherex_qr3",
        "ra": 210.8015,
        "dec": 90.0,
        "radius": 0.001,
        "time_start_mjd": 60000.123457,
        "time_end_mjd": None,
        "maxrec": 500,
    }


def test_normalize_sia_args_accepts_string_collection():
    args = normalize_sia_args(1.0, 1.0, 0.001, "spherex_dr1", None, None, None, Q)
    assert args["collection"] == "spherex_dr1"
