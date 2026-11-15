import numpy as np
import pytest

from app.processing.fits_reader import open_cutout
from app.processing.reprojection import pixel_count, reproject_to_north_up
from tests.synthetic_fits import DEFAULT_DEC, DEFAULT_RA, Star, make_cutout_bytes

SIZE = 0.25
N = pixel_count(SIZE)
CENTER = (N - 1) / 2  # 0-based index of the grid center


def _brightest(img: np.ndarray) -> tuple[int, int]:
    row, col = np.unravel_index(np.nanargmax(img), img.shape)
    return int(row), int(col)


@pytest.mark.parametrize(
    ("size", "expected"), [(0.25, 146), (1.0, 585), (0.01, 16), (0.02, 16), (0.03, 18)]
)
def test_pixel_count(size, expected):
    assert pixel_count(size) == expected


@pytest.mark.parametrize("rotation_deg", [0.0, 37.0, 180.0])
def test_ac009_north_up_east_left(rotation_deg):
    offset = 20
    results = {}
    for name, star in {"north": Star(north_px=offset), "east": Star(east_px=offset)}.items():
        hdus = open_cutout(make_cutout_bytes(rotation_deg=rotation_deg, stars=[star]))
        aligned = reproject_to_north_up(
            hdus.image_data, hdus.image_header, DEFAULT_RA, DEFAULT_DEC, SIZE
        )
        assert aligned.shape == (N, N) and aligned.dtype == np.float32
        png_order = np.flipud(aligned)  # what rendering does before encoding the PNG
        results[name] = _brightest(png_order)

    north_row, north_col = results["north"]
    assert north_row == pytest.approx(CENTER - offset, abs=1)  # above the center
    assert north_col == pytest.approx(CENTER, abs=1)

    east_row, east_col = results["east"]
    assert east_col == pytest.approx(CENTER - offset, abs=1)  # left of the center
    assert east_row == pytest.approx(CENTER, abs=1)


def test_output_is_fits_row_order_before_flip():
    hdus = open_cutout(make_cutout_bytes(stars=[Star(north_px=20)]))
    aligned = reproject_to_north_up(
        hdus.image_data, hdus.image_header, DEFAULT_RA, DEFAULT_DEC, SIZE
    )
    row, _ = _brightest(aligned)
    assert row > CENTER  # FITS row 0 is south, so north is at high row indices


def test_pixels_outside_source_are_nan():
    hdus = open_cutout(make_cutout_bytes(shape=(100, 100), rotation_deg=37.0))
    aligned = reproject_to_north_up(
        hdus.image_data, hdus.image_header, DEFAULT_RA, DEFAULT_DEC, SIZE
    )
    assert np.isnan(aligned[0, 0]) and np.isnan(aligned[-1, -1])
    assert np.isfinite(aligned[N // 2, N // 2])


@pytest.mark.parametrize(("ra", "dec"), [(359.999, 10.0), (0.0, -30.0)])
def test_ra_wrap_positions(ra, dec):
    hdus = open_cutout(make_cutout_bytes(ra=ra, dec=dec, stars=[Star(north_px=10)]))
    aligned = reproject_to_north_up(hdus.image_data, hdus.image_header, ra, dec, SIZE)
    assert np.isfinite(aligned).all()
    row, col = _brightest(np.flipud(aligned))
    assert row == pytest.approx(CENTER - 10, abs=1)
    assert col == pytest.approx(CENTER, abs=1)


@pytest.mark.parametrize("dec", [90.0, -90.0])
def test_pole_center(dec):
    hdus = open_cutout(make_cutout_bytes(ra=45.0, dec=dec, rotation_deg=37.0))
    aligned = reproject_to_north_up(hdus.image_data, hdus.image_header, 45.0, dec, SIZE)
    assert np.isfinite(aligned).all()
    row, col = _brightest(aligned)
    assert row == pytest.approx(CENTER, abs=1) and col == pytest.approx(CENTER, abs=1)
