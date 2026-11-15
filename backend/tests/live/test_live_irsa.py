import io
import warnings

import numpy as np
import pytest
from astropy.wcs import WCS, FITSFixedWarning
from PIL import Image

from app.processing.flags import NEVER_MASK, build_mask, flag_definitions
from app.processing.reprojection import PIXEL_SCALE_ARCSEC
from tests.live.conftest import CUTOUT_SIZE_DEG, DEC, RA, RealCutout, skip_if_upstream_down

pytestmark = pytest.mark.live

REQUIRED_HEADERS = [
    "X-Observation-Id",
    "X-Detector",
    "X-Observation-Time",
    "X-Wavelength-Min-Um",
    "X-Wavelength-Max-Um",
    "X-Scale-Min",
    "X-Scale-Max",
    "X-Image-Width",
    "X-Image-Height",
    "X-Pixel-Scale-Arcsec",
    "X-Valid-Pixel-Fraction",
]


def test_val007_epochs_and_image_for_m101(client):
    epochs = client.get("/epochs", params={"ra": RA, "dec": DEC})
    skip_if_upstream_down(epochs)
    assert epochs.status_code == 200, epochs.text
    body = epochs.json()
    assert body["total_observations"] >= 1
    first = body["observations"][0]
    detector = first["detectors"][0]["detector"]

    image = client.get(
        "/image",
        params={
            "ra": RA,
            "dec": DEC,
            "observation_id": first["observation_id"],
            "detector": detector,
        },
    )
    skip_if_upstream_down(image)
    assert image.status_code == 200, image.text
    assert image.headers["content-type"] == "image/png"
    for name in REQUIRED_HEADERS:
        assert name in image.headers, name
    assert image.headers["X-Observation-Id"] == first["observation_id"]
    assert float(image.headers["X-Pixel-Scale-Arcsec"]) == PIXEL_SCALE_ARCSEC

    png = Image.open(io.BytesIO(image.content))
    assert png.mode == "RGBA"
    assert png.size == (
        int(image.headers["X-Image-Width"]),
        int(image.headers["X-Image-Height"]),
    )
    alpha = np.asarray(png)[..., 3]
    assert alpha.max() == 255
    assert float(image.headers["X-Valid-Pixel-Fraction"]) == pytest.approx(
        (alpha > 0).mean(), abs=1e-3
    )


def test_val008_flags_header_convention(real_cutouts: list[RealCutout], settings):
    for cutout in real_cutouts:
        header = cutout.hdus.flags_header
        assert header is not None, "FLAGS HDU missing"
        defs = flag_definitions(header)
        assert defs, "no flag definitions parsed (neither MP_* nor MSKN/MSKM)"
        missing = [n for n in settings.flags_reject_list if n not in defs]
        assert not missing, f"FLAGS_REJECT_NAMES missing in header: {missing}"
        assert "SOURCE" in defs

        data = cutout.hdus.flags_data
        source_only = np.full(data.shape, 1 << defs["SOURCE"], dtype=data.dtype)
        assert not build_mask(source_only, header, settings.flags_reject_list).any()
        assert "SOURCE" in NEVER_MASK
        for name in settings.flags_reject_list:
            single = np.full(data.shape, 1 << defs[name], dtype=np.int64)
            assert build_mask(single, header, settings.flags_reject_list).all(), name


def _angular_sep_arcsec(ra1, dec1, ra2, dec2) -> float:
    d_ra = (ra1 - ra2) * np.cos(np.radians((dec1 + dec2) / 2))
    return float(np.hypot(d_ra, dec1 - dec2) * 3600)


def test_val009_wcs_celestial_matches_request(real_cutouts: list[RealCutout]):
    cutout = real_cutouts[0]
    header = cutout.hdus.image_header
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        full = WCS(header)
        celestial = full.celestial

    assert celestial.naxis == 2
    assert celestial.wcs.ctype[0].startswith("RA---TAN")
    assert celestial.wcs.ctype[1].startswith("DEC--TAN")
    if "-SIP" in celestial.wcs.ctype[0]:
        assert celestial.sip is not None, ".celestial dropped the SIP distortion"
    assert WCS(header, key="A").wcs.ctype[0] == "LINEAR"

    ny, nx = cutout.hdus.image_data.shape
    x, y = celestial.world_to_pixel_values(RA, DEC)
    assert -0.5 <= x <= nx - 0.5 and -0.5 <= y <= ny - 0.5

    # The cutout is centered on the request unless it is clipped at the detector edge.
    expected = round(0.25 * 3600 / PIXEL_SCALE_ARCSEC)
    cx, cy = (nx - 1) / 2 if nx >= expected else x, (ny - 1) / 2 if ny >= expected else y
    ra_c, dec_c = celestial.all_pix2world(cx, cy, 0)
    assert _angular_sep_arcsec(float(ra_c), float(dec_c), RA, DEC) < PIXEL_SCALE_ARCSEC
    if nx >= expected and ny >= expected:
        assert abs(x - cx) < 1 and abs(y - cy) < 1


def test_image_near_detector_edge_is_transparent_where_no_data(
    real_cutouts: list[RealCutout], client
):
    expected = round(CUTOUT_SIZE_DEG * 3600 / PIXEL_SCALE_ARCSEC)
    clipped = [c for c in real_cutouts if min(c.hdus.image_data.shape) < expected]
    if not clipped:
        pytest.skip("no clipped cutout among the sampled records")
    cutout = clipped[-1]
    ny, nx = cutout.hdus.image_data.shape
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        celestial = WCS(cutout.hdus.image_header).celestial
    x, y = celestial.world_to_pixel_values(RA, DEC)
    px = (2 if x < nx / 2 else nx - 3) if nx < expected else x
    py = (2 if y < ny / 2 else ny - 3) if ny < expected else y
    ra, dec = (float(v) for v in celestial.all_pix2world(px, py, 0))

    response = client.get(
        "/image",
        params={
            "ra": ra,
            "dec": dec,
            "observation_id": cutout.record.observation_id,
            "detector": cutout.record.detector.value,
        },
    )
    skip_if_upstream_down(response)
    assert response.status_code == 200, response.text
    fraction = float(response.headers["X-Valid-Pixel-Fraction"])
    assert 0 < fraction < 1
    alpha = np.asarray(Image.open(io.BytesIO(response.content)))[..., 3]
    assert (alpha == 0).any()
    assert set(np.unique(alpha)) <= {0, 255}
