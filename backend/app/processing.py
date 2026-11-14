"""Create a two-epoch display from registered SPHEREx Level 2 cutouts.

The pixel flags and WAVE-TAB lookup are documented in the IRSA data tutorial:
https://caltech-ipac.github.io/irsa-tutorials/spherex-intro/
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from io import BytesIO
from math import isfinite

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import NoConvergence, WCS, WcsError
from numpy.typing import NDArray
from PIL import Image
from reproject import reproject_interp

PROCESSING_VERSION = "spherex-tan-v1"
FOV_ARCMIN = 6.0
PNG_SIZE = 128
MIN_SHARED_COVERAGE = 0.65
MIN_BAND_OVERLAP = 0.5

# Reject artifact and bad-measurement flags. FULLSAMPLE (12) and SOURCE (21)
# convey context and do not make a pixel invalid.
_ARTIFACT_BITS = (0, 1, 2, 6, 7, 9, 10, 11, 14, 15, 17, 19, 20, 22, 23, 24, 25, 26, 27, 28)
_INVALID_PIXEL_MASK = sum(1 << bit for bit in _ARTIFACT_BITS)


class InvalidCutout(ValueError):
    """A cutout or pair cannot be used for the comparison."""


@dataclass(frozen=True, slots=True)
class Cutout:
    detector: str
    wavelength_um: float
    bandwidth_um: float
    calibration_version: str
    obstime: datetime | None
    observation_id: str | None
    pixels: NDArray[np.float32]
    wcs: WCS


@dataclass(frozen=True, slots=True)
class RenderedFrame:
    png: bytes
    valid_fraction: float


def _observation_time(header: fits.Header) -> datetime | None:
    # DATE without the -OBS suffix is the product creation date.
    if "DATE-OBS" in header:
        return Time(header["DATE-OBS"], scale="utc").to_datetime(timezone=timezone.utc)
    if "MJD-OBS" in header:
        return Time(header["MJD-OBS"], format="mjd", scale="utc").to_datetime(timezone=timezone.utc)
    return None


def decode_cutout(fits_bytes: bytes, ra_deg: float, dec_deg: float) -> Cutout:
    """Read a cutout and evaluate its central wavelength at the exact target."""
    try:
        with fits.open(BytesIO(fits_bytes), memmap=False) as hdus:
            image_hdu, flags_hdu = hdus["IMAGE"], hdus["FLAGS"]
            header = image_hdu.header
            # A 0.1° cutout is typically about 60 native pixels on each side.
            # Reject full frames before decompressing their image planes.
            shape = (header["NAXIS2"], header["NAXIS1"])
            if header["NAXIS"] != 2 or min(shape) < 2 or max(shape) > 512:
                raise InvalidCutout("Unexpected cutout dimensions")
            if shape != (flags_hdu.header["NAXIS2"], flags_hdu.header["NAXIS1"]):
                raise InvalidCutout("IMAGE and FLAGS grids do not match")

            spatial_wcs = WCS(header, fobj=hdus).celestial
            sky = SkyCoord(ra=ra_deg, dec=dec_deg, unit="deg", frame="icrs")
            x, y = spatial_wcs.world_to_pixel(sky)
            height, width = shape
            if not (0 <= x <= width - 1 and 0 <= y <= height - 1):
                raise InvalidCutout("Cutout does not include the requested center")

            # The spectral WCS describes detector coordinates. The SIP optical
            # distortion belongs only to the spatial WCS.
            spectral_header = header.copy()
            for key in list(spectral_header):
                if key.startswith(("A_", "B_", "AP_", "BP_")):
                    del spectral_header[key]
            spectral_wcs = WCS(spectral_header, fobj=hdus, key="W")
            wavelength, bandwidth = spectral_wcs.pixel_to_world(x, y)
            wavelength_um = float(wavelength.to_value(u.um))
            bandwidth_um = float(bandwidth.to_value(u.um))
            if not all(isfinite(value) and value > 0 for value in (wavelength_um, bandwidth_um)):
                raise InvalidCutout("Invalid central wavelength or bandwidth")

            pixels = np.array(image_hdu.data, dtype=np.float32, copy=True)
            flags = np.asarray(flags_hdu.data)
            if flags.shape != pixels.shape or not np.issubdtype(flags.dtype, np.integer):
                raise InvalidCutout("Invalid pixel flag map")
            # Read additional mission-documented artifact bits when present.
            mask = _INVALID_PIXEL_MASK
            for key in flags_hdu.header:
                if key.startswith("MSKN") and flags_hdu.header[key] == "SAT_HALO":
                    bit = int(key[4:])
                    if 0 <= bit < 32:
                        mask |= 1 << bit
            pixels[(flags.astype(np.uint32) & mask) != 0] = np.nan
            pixels[~np.isfinite(pixels)] = np.nan
            if not np.any(np.isfinite(pixels)):
                raise InvalidCutout("Cutout contains no usable pixels")

            detector_number = int(header["DETECTOR"])
            if not 1 <= detector_number <= 6:
                raise InvalidCutout("Unknown SPHEREx detector")
            version = str(hdus[0].header.get("VERSION") or "").strip()
            if not version:
                raise InvalidCutout("Missing SPHEREx processing version")
            return Cutout(
                detector=f"D{detector_number}",
                wavelength_um=wavelength_um,
                bandwidth_um=bandwidth_um,
                calibration_version=version,
                obstime=_observation_time(header),
                observation_id=str(header["OBSID"]) if "OBSID" in header else None,
                pixels=pixels,
                wcs=spatial_wcs,
            )
    except InvalidCutout:
        raise
    except (OSError, EOFError, KeyError, TypeError, ValueError, IndexError, WcsError, NoConvergence) as exc:
        raise InvalidCutout(f"Could not interpret SPHEREx cutout: {exc}") from exc


def spectral_compatible(a: Cutout, b: Cutout) -> bool:
    """Require one detector and at least 50% overlap of both central passbands."""
    if a.detector != b.detector:
        return False
    a_low, a_high = a.wavelength_um - a.bandwidth_um / 2, a.wavelength_um + a.bandwidth_um / 2
    b_low, b_high = b.wavelength_um - b.bandwidth_um / 2, b.wavelength_um + b.bandwidth_um / 2
    overlap = min(a_high, b_high) - max(a_low, b_low)
    return overlap >= MIN_BAND_OVERLAP * max(a.bandwidth_um, b.bandwidth_um)


def _target_grid(ra_deg: float, dec_deg: float) -> WCS:
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.cunit = ["deg", "deg"]
    wcs.wcs.radesys = "ICRS"
    wcs.wcs.crval = [ra_deg, dec_deg]
    wcs.wcs.crpix = [(PNG_SIZE + 1) / 2] * 2
    degrees_per_pixel = (FOV_ARCMIN / 60) / PNG_SIZE
    wcs.wcs.cdelt = [-degrees_per_pixel, degrees_per_pixel]
    return wcs


def _encode_png(
    image: NDArray[np.float64],
    shared: NDArray[np.bool_],
    lo: float,
    hi: float,
) -> bytes:
    # Quantize both images with the same asinh stretch. FITS row 0 is south
    # on this grid whereas PNG row 0 is shown at the top.
    scaled = np.zeros(image.shape, dtype=np.float64)
    scaled[shared] = np.clip((image[shared] - lo) / (hi - lo), 0, 1)
    intensity = np.rint(255 * np.arcsinh(8 * scaled) / np.arcsinh(8)).astype(np.uint8)
    alpha = np.where(shared, 255, 0).astype(np.uint8)
    grayscale_alpha = np.stack((intensity, alpha), axis=-1)
    output = BytesIO()
    Image.fromarray(np.flipud(grayscale_alpha)).save(output, format="PNG", optimize=True)
    return output.getvalue()


def render_pair(a: Cutout, b: Cutout, ra_deg: float, dec_deg: float) -> tuple[RenderedFrame, RenderedFrame]:
    """Align the epochs and preserve the same contrast and valid area in both PNGs."""
    if not spectral_compatible(a, b):
        raise InvalidCutout("Central passbands do not overlap sufficiently")

    target = _target_grid(ra_deg, dec_deg)
    try:
        first, first_footprint = reproject_interp((a.pixels, a.wcs), target, shape_out=(PNG_SIZE, PNG_SIZE))
        second, second_footprint = reproject_interp((b.pixels, b.wcs), target, shape_out=(PNG_SIZE, PNG_SIZE))
    except (ValueError, WcsError, NoConvergence) as exc:
        raise InvalidCutout(f"Could not align SPHEREx cutouts: {exc}") from exc

    shared = (first_footprint > 0) & (second_footprint > 0) & np.isfinite(first) & np.isfinite(second)
    fraction = float(shared.mean())
    if fraction < MIN_SHARED_COVERAGE:
        raise InvalidCutout(f"Too little common usable coverage ({fraction:.1%})")
    valid_values = np.concatenate((first[shared], second[shared]))
    lo, hi = np.percentile(valid_values, [2.0, 99.5])
    if hi <= lo:
        raise InvalidCutout("Cutouts have no usable dynamic range")
    return (
        RenderedFrame(_encode_png(first, shared, lo, hi), fraction),
        RenderedFrame(_encode_png(second, shared, lo, hi), fraction),
    )


def project_cutout(cutout: Cutout, ra_deg: float, dec_deg: float) -> NDArray[np.float64]:
    try:
        pixels, footprint = reproject_interp(
            (cutout.pixels, cutout.wcs), _target_grid(ra_deg, dec_deg),
            shape_out=(PNG_SIZE, PNG_SIZE),
        )
    except (ValueError, WcsError, NoConvergence) as exc:
        raise InvalidCutout(f"Could not align SPHEREx cutout: {exc}") from exc
    pixels[footprint <= 0] = np.nan
    return pixels


def render_exposure(pixels: NDArray[np.float64], reference: NDArray[np.float64]) -> RenderedFrame:
    """Use one reference scale for the entire comparison, without stretching each frame."""
    valid = np.isfinite(pixels)
    reference_valid = np.isfinite(reference)
    if not valid.any() or not reference_valid.any():
        raise InvalidCutout("Recorte sem pixels válidos na grade de exibição.")
    lo, hi = np.percentile(reference[reference_valid], [2.0, 99.5])
    if hi <= lo:
        raise InvalidCutout("Recorte sem variação de intensidade suficiente.")
    return RenderedFrame(_encode_png(pixels, valid, lo, hi), float(valid.mean()))
