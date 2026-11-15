import logging

import numpy as np
import pytest

from app.domain.errors import UpstreamInvalidResponseError
from app.processing.fits_reader import open_cutout
from tests.synthetic_fits import make_cutout_bytes


def test_reads_all_hdus(synthetic_cutout_bytes):
    hdus = open_cutout(synthetic_cutout_bytes)
    assert hdus.image_data.dtype == np.float32
    assert hdus.image_data.shape == (240, 240)
    assert hdus.flags_data is not None and hdus.flags_data.dtype.kind == "i"
    assert hdus.flags_header["MP_HOT"] == 10
    assert np.all(hdus.zodi_data == np.float32(0.5))
    assert hdus.image_header["CTYPE1"] == "RA---TAN"


def test_gzip_is_decompressed():
    hdus = open_cutout(make_cutout_bytes(gzip=True))
    assert hdus.image_data.shape == (240, 240)


def test_extnames_out_of_order_are_resolved_by_name():
    hdus = open_cutout(make_cutout_bytes(extensions=("ZODI", "FLAGS", "IMAGE")))
    assert np.all(hdus.zodi_data == np.float32(0.5))
    assert hdus.image_data.max() > 10  # star lives in IMAGE, not in the constant ZODI
    assert "MP_HOT" in hdus.flags_header


def test_missing_image_raises():
    with pytest.raises(UpstreamInvalidResponseError):
        open_cutout(make_cutout_bytes(extensions=("FLAGS", "ZODI")))


def test_missing_optional_hdus_warn(caplog):
    with caplog.at_level(logging.WARNING):
        hdus = open_cutout(make_cutout_bytes(extensions=("IMAGE",)))
    assert hdus.flags_data is None and hdus.flags_header is None and hdus.zodi_data is None
    events = {getattr(r, "event", None) for r in caplog.records}
    assert {"flags_hdu_missing", "zodi_hdu_missing"} <= events


@pytest.mark.parametrize(
    "payload",
    [b"<html>error</html>", b"", b"SIMPLE  =  garbage" + b" " * 100, b"\x1f\x8bnot-gzip"],
)
def test_invalid_payload_raises(payload):
    with pytest.raises(UpstreamInvalidResponseError):
        open_cutout(payload)
