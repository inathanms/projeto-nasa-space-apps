import logging

import numpy as np
from astropy.io import fits

from app.processing.fits_reader import open_cutout
from app.processing.flags import build_mask, flag_definitions
from tests.synthetic_fits import MP_BITS, make_cutout_bytes

REJECT = ["NONFUNC", "MISSING_DATA", "HOT", "COLD", "OVERFLOW", "SUR_ERROR", "PHANMISS"]


def _hdus(**kwargs):
    return open_cutout(make_cutout_bytes(**kwargs))


def test_flag_definitions_reads_mp_keywords():
    hdus = _hdus()
    assert flag_definitions(hdus.flags_header) == MP_BITS


def test_hot_masked_source_only_kept():
    hdus = _hdus(
        flag_pixels={
            (5, 5): ["HOT"],
            (6, 6): ["SOURCE"],
            (7, 7): ["SOURCE", "HOT"],
            (8, 8): ["TRANSIENT"],
        }
    )
    mask = build_mask(hdus.flags_data, hdus.flags_header, REJECT)
    assert mask.dtype == bool and mask.shape == hdus.flags_data.shape
    assert mask[5, 5] and mask[7, 7]
    assert not mask[6, 6]
    assert not mask[8, 8]
    assert mask.sum() == 2


def test_source_never_masked_even_if_requested():
    hdus = _hdus(flag_pixels={(6, 6): ["SOURCE"]})
    mask = build_mask(hdus.flags_data, hdus.flags_header, ["SOURCE", "HOT"])
    assert not mask.any()


def test_unknown_reject_names_ignored():
    hdus = _hdus(flag_pixels={(5, 5): ["HOT"]})
    mask = build_mask(hdus.flags_data, hdus.flags_header, ["DOES_NOT_EXIST", "HOT"])
    assert mask[5, 5] and mask.sum() == 1


def test_no_mp_keywords_means_no_mask(caplog):
    hdus = _hdus(flag_pixels={(5, 5): ["HOT"]}, flag_definitions=None)
    with caplog.at_level(logging.WARNING):
        mask = build_mask(hdus.flags_data, hdus.flags_header, REJECT)
    assert not mask.any()
    assert any(getattr(r, "event", None) == "flags_definitions_missing" for r in caplog.records)


def test_high_bit_of_int32():
    bits = {"HOT": 31}
    hdus = _hdus(flag_pixels={(1, 1): ["HOT"]}, flag_definitions=bits)
    assert hdus.flags_data[1, 1] < 0
    mask = build_mask(hdus.flags_data, hdus.flags_header, ["HOT"])
    assert mask[1, 1] and mask.sum() == 1


def test_mask_applied_to_image_becomes_nan():
    hdus = _hdus(flag_pixels={(5, 5): ["HOT"], (6, 6): ["SOURCE"]})
    data = hdus.image_data.copy()
    data[build_mask(hdus.flags_data, hdus.flags_header, REJECT)] = np.nan
    assert np.isnan(data[5, 5])
    assert np.isfinite(data[6, 6])


def test_msk_convention_of_real_qr3_cutouts():
    hdus = _hdus(
        flag_convention="MSK",
        flag_pixels={(5, 5): ["HOT"], (6, 6): ["SOURCE"], (7, 7): ["NONLINEAR"]},
    )
    assert flag_definitions(hdus.flags_header) == MP_BITS
    mask = build_mask(hdus.flags_data, hdus.flags_header, REJECT)
    assert mask[5, 5] and not mask[6, 6] and not mask[7, 7]
    assert mask.sum() == 1


def test_msk_falls_back_to_index_when_mask_value_is_odd():
    header = fits.Header()
    header["MSKN0010"] = "HOT"
    header["MSKM0010"] = 3  # not a power of two
    header["MSKN0011"] = "COLD"  # no MSKM at all
    header["MSKN0012"] = ""  # empty names are ignored
    assert flag_definitions(header) == {"HOT": 10, "COLD": 11}
