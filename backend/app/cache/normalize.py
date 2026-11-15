"""Parameter normalization (REQ-501..503): quantized position and rounded floats.

The renderer must use the normalized request so the image always matches its cache key.
"""

import math
from dataclasses import replace

from app.domain.models import Collection
from app.services.image_service import ImageRequest

_POSITION_DECIMALS = 6
_SIGNIFICANT_DIGITS = 6


def _quantize(value: float, quantum_deg: float) -> float:
    steps = math.floor(value / quantum_deg + 0.5)
    return round(steps * quantum_deg, _POSITION_DECIMALS)


def normalize_ra(ra: float, quantum_arcsec: float) -> float:
    """Round to the quantum grid (anchored at 0) and keep the result in [0, 360).

    360 is generally not a multiple of the quantum (6.15"), so wrapping is done *before*
    rounding, and a value that rounds up to the grid point just past 360 (e.g. 359.9999 ->
    360.0005) becomes 0.0, the grid point equivalent to 360 (AC-502). Wrapping after rounding
    would give 0.0005, which is off the grid and re-normalizes to 0.0: the function must be
    idempotent because the route, the cache service and the SIA cache all normalize.
    """
    if quantum_arcsec <= 0:
        raise ValueError("quantum_arcsec must be positive")
    quantized = _quantize(ra % 360.0, quantum_arcsec / 3600)
    return 0.0 if quantized >= 360.0 else quantized + 0.0


def normalize_dec(dec: float, quantum_arcsec: float) -> float:
    """Round to the quantum grid, then clamp into [-90, 90]."""
    if quantum_arcsec <= 0:
        raise ValueError("quantum_arcsec must be positive")
    return min(90.0, max(-90.0, _quantize(dec, quantum_arcsec / 3600))) + 0.0


def significant(value: float, digits: int = _SIGNIFICANT_DIGITS) -> float:
    """Round to `digits` significant figures (REQ-503)."""
    return float(f"{value:.{digits}g}")


def _opt_sig(value: float | None) -> float | None:
    return None if value is None else significant(value)


def _opt_sig_tuple(values: tuple[float, ...] | None) -> tuple[float, ...] | None:
    return None if values is None else tuple(significant(v) for v in values)


def normalize_request(req: ImageRequest, quantum_arcsec: float) -> ImageRequest:
    """Return a new request with normalized position, size, percentiles and scale bounds."""
    return replace(
        req,
        ra=normalize_ra(req.ra, quantum_arcsec),
        dec=normalize_dec(req.dec, quantum_arcsec),
        size=round(req.size, 2),
        percentile_low=round(req.percentile_low, 1),
        percentile_high=round(req.percentile_high, 1),
        scale_min=_opt_sig(req.scale_min),
        scale_max=_opt_sig(req.scale_max),
        scale_mins=_opt_sig_tuple(req.scale_mins),
        scale_maxs=_opt_sig_tuple(req.scale_maxs),
    )


def normalize_sia_args(
    ra: float,
    dec: float,
    radius: float,
    collection: Collection | str,
    start_mjd: float | None,
    end_mjd: float | None,
    maxrec: int | None,
    quantum_arcsec: float,
) -> dict:
    """Normalized SIA query arguments, ready for `sia_key` (REQ-514)."""
    return {
        "collection": Collection(collection).value,
        "ra": normalize_ra(ra, quantum_arcsec),
        "dec": normalize_dec(dec, quantum_arcsec),
        "radius": significant(radius),
        "time_start_mjd": None if start_mjd is None else round(start_mjd, 6),
        "time_end_mjd": None if end_mjd is None else round(end_mjd, 6),
        "maxrec": maxrec,
    }
