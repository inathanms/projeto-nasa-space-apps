import warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning
from reproject import reproject_interp

PIXEL_SCALE_ARCSEC = 6.15
MIN_PIXELS = 16


def pixel_count(size_deg: float) -> int:
    """Side of the square output grid in pixels for a side of `size_deg` degrees at 6.15"/px."""
    return max(MIN_PIXELS, round(size_deg * 3600 / PIXEL_SCALE_ARCSEC))


def north_up_wcs(ra: float, dec: float, n: int) -> WCS:
    """TAN WCS of an n x n grid centered on (ra, dec) degrees, north up and east left."""
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.cdelt = [-PIXEL_SCALE_ARCSEC / 3600, PIXEL_SCALE_ARCSEC / 3600]
    wcs.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    wcs.wcs.cunit = ["deg", "deg"]
    wcs.wcs.radesys = "ICRS"
    wcs.pixel_shape = (n, n)
    return wcs


def reproject_to_north_up(
    data: np.ndarray, header: fits.Header, ra: float, dec: float, size_deg: float
) -> np.ndarray:
    """Reproject `data` (with WCS in `header`) onto the north-up grid of `size_deg` degrees.

    Returns a float32 (n, n) array in FITS row order (row 0 = south). Pixels outside the
    source image are NaN. The vertical flip to PNG order is the rendering step's job.
    """
    n = pixel_count(size_deg)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        # SPHEREx IMAGE headers also carry a spectral (wavelength) WCS; keep only sky axes.
        source_wcs = WCS(header).celestial
    out = reproject_interp(
        (np.asarray(data, dtype=np.float32), source_wcs),
        north_up_wcs(ra, dec, n),
        shape_out=(n, n),
        order="bilinear",
        return_footprint=False,
    )
    return np.asarray(out, dtype=np.float32)
