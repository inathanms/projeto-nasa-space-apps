"""In-memory synthetic SPHEREx-like cutout MEFs for tests.

Typical use:
    data = make_cutout_bytes(rotation_deg=37, stars=[Star(north_px=20)])
    hdul = make_cutout_hdul(flag_pixels={(10, 10): ["HOT"]})

Star offsets are in 6.15" pixels on the sky (north/east of the center), so their
position in the north-up output grid is known regardless of the source rotation.
"""

import gzip as _gzip
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS

PIXEL_SCALE_ARCSEC = 6.15
DEFAULT_RA = 210.80227
DEFAULT_DEC = 54.34895
DEFAULT_SHAPE = (240, 240)

MP_BITS: dict[str, int] = {
    "TRANSIENT": 0,
    "OVERFLOW": 1,
    "SUR_ERROR": 2,
    "NONFUNC": 6,
    "MISSING_DATA": 9,
    "HOT": 10,
    "COLD": 11,
    "PHANMISS": 14,
    "NONLINEAR": 15,
    "SOURCE": 21,
}


@dataclass(frozen=True)
class Star:
    """Gaussian star offset from the cutout center. Offsets/sigma in px, amplitude in MJy/sr."""

    north_px: float = 0.0
    east_px: float = 0.0
    amplitude: float = 50.0
    sigma_px: float = 1.5


def star_sky_position(ra: float, dec: float, star: Star) -> tuple[float, float]:
    """(ra, dec) degrees of `star` relative to a center at (ra, dec) degrees."""
    center = SkyCoord(ra * u.deg, dec * u.deg, frame="icrs")
    scale = PIXEL_SCALE_ARCSEC * u.arcsec
    pos = center.spherical_offsets_by(star.east_px * scale, star.north_px * scale)
    return float(pos.ra.deg), float(pos.dec.deg)


def make_wcs_header(
    ra: float = DEFAULT_RA,
    dec: float = DEFAULT_DEC,
    shape: tuple[int, int] = DEFAULT_SHAPE,
    rotation_deg: float = 0.0,
) -> fits.Header:
    """TAN header at 6.15"/px centered on (ra, dec), rotated `rotation_deg` from north-up."""
    theta = np.deg2rad(rotation_deg)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [ra, dec]
    wcs.wcs.crpix = [(shape[1] + 1) / 2, (shape[0] + 1) / 2]
    wcs.wcs.cdelt = [-PIXEL_SCALE_ARCSEC / 3600, PIXEL_SCALE_ARCSEC / 3600]
    wcs.wcs.pc = [[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]]
    wcs.wcs.cunit = ["deg", "deg"]
    return wcs.to_header()


def make_cutout_hdul(
    *,
    ra: float = DEFAULT_RA,
    dec: float = DEFAULT_DEC,
    shape: tuple[int, int] = DEFAULT_SHAPE,
    rotation_deg: float = 0.0,
    stars: Sequence[Star] = (Star(),),
    background: float = 1.0,
    noise_sigma: float = 0.05,
    zodi_level: float = 0.5,
    seed: int = 1234,
    flag_pixels: Mapping[tuple[int, int], Iterable[str]] | None = None,
    flag_definitions: Mapping[str, int] | None = MP_BITS,
    extensions: Sequence[str] = ("IMAGE", "FLAGS", "ZODI"),
    flag_convention: str = "MP",
) -> fits.HDUList:
    """Build a MEF with IMAGE (float32), FLAGS (int32) and ZODI (constant float32) HDUs.

    IMAGE = background + zodi_level + gaussian noise + stars (MJy/sr).
    `flag_pixels` maps (row, col) to flag names (bits from `flag_definitions`).
    `flag_definitions=None` writes a FLAGS header without MP_* keywords.
    `extensions` controls which HDUs exist and their order.
    `flag_convention="MSK"` writes MSKN<bit>=NAME / MSKM<bit>=2**bit like real QR3 cutouts.
    """
    header = make_wcs_header(ra, dec, shape, rotation_deg)
    wcs = WCS(header)
    rng = np.random.default_rng(seed)
    image = background + zodi_level + rng.normal(0.0, noise_sigma, size=shape)
    yy, xx = np.mgrid[0 : shape[0], 0 : shape[1]]
    for star in stars:
        sx, sy = wcs.world_to_pixel_values(*star_sky_position(ra, dec, star))
        image += star.amplitude * np.exp(
            -((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * star.sigma_px**2)
        )

    bits = dict(MP_BITS if flag_definitions is None else flag_definitions)
    flags = np.zeros(shape, dtype=np.int64)
    for (row, col), names in (flag_pixels or {}).items():
        for name in names:
            flags[row, col] |= 1 << bits[name]
    flags = flags.astype(np.int32)  # bit 31 wraps to negative, like a real int32 FLAGS HDU
    flags_header = header.copy()
    for name, bit in (flag_definitions or {}).items():
        if flag_convention == "MSK":
            flags_header[f"MSKN{bit:04d}"] = name
            flags_header[f"MSKM{bit:04d}"] = 1 << bit
        else:
            flags_header[f"HIERARCH MP_{name}"] = bit

    builders = {
        "IMAGE": lambda: fits.ImageHDU(image.astype(np.float32), header=header, name="IMAGE"),
        "FLAGS": lambda: fits.ImageHDU(flags, header=flags_header, name="FLAGS"),
        "ZODI": lambda: fits.ImageHDU(
            np.full(shape, zodi_level, dtype=np.float32), header=header, name="ZODI"
        ),
    }
    return fits.HDUList([fits.PrimaryHDU()] + [builders[name]() for name in extensions])


def to_fits_bytes(hdul: fits.HDUList, *, gzip: bool = False) -> bytes:
    """Serialize `hdul` to FITS bytes, optionally gzip-compressed."""
    buf = io.BytesIO()
    hdul.writeto(buf)
    raw = buf.getvalue()
    return _gzip.compress(raw) if gzip else raw


def make_cutout_bytes(*, gzip: bool = False, **kwargs) -> bytes:
    """`make_cutout_hdul(**kwargs)` serialized as cutout response bytes."""
    return to_fits_bytes(make_cutout_hdul(**kwargs), gzip=gzip)


@dataclass(frozen=True)
class MovingObject:
    """Gaussian source whose offset from the true center advances by `step_*` px each frame."""

    start_north_px: float = 0.0
    start_east_px: float = 0.0
    step_north_px: float = 0.0
    step_east_px: float = 0.0
    amplitude: float = 50.0
    sigma_px: float = 1.5

    def star_at(self, frame: int) -> Star:
        return Star(
            north_px=self.start_north_px + self.step_north_px * frame,
            east_px=self.start_east_px + self.step_east_px * frame,
            amplitude=self.amplitude,
            sigma_px=self.sigma_px,
        )


def _add_stars(hdul: fits.HDUList, ra: float, dec: float, stars: Iterable[Star]) -> None:
    """Add Gaussian stars placed at sky offsets from (ra, dec) using the HDUL's own WCS."""
    image = hdul["IMAGE"]
    wcs = WCS(image.header)
    yy, xx = np.mgrid[0 : image.data.shape[0], 0 : image.data.shape[1]]
    data = image.data.astype(np.float64)
    for star in stars:
        sx, sy = wcs.world_to_pixel_values(*star_sky_position(ra, dec, star))
        data += star.amplitude * np.exp(-((xx - sx) ** 2 + (yy - sy) ** 2) / (2 * star.sigma_px**2))
    image.data = data.astype(np.float32)


def make_visit_cutout_bytes(
    n_frames: int = 5,
    *,
    ra: float = DEFAULT_RA,
    dec: float = DEFAULT_DEC,
    shape: tuple[int, int] = DEFAULT_SHAPE,
    stars: Sequence[Star] = (Star(),),
    background_levels: Sequence[float] | None = None,
    noise_sigma: float = 0.05,
    wcs_jitter_px: float = 3.0,
    rotation_jitter_deg: float = 3.0,
    moving_object: MovingObject | None = None,
    seed: int = 1234,
    gzip: bool = False,
    **kwargs,
) -> list[bytes]:
    """`n_frames` cutouts (IMAGE/FLAGS/ZODI MEFs) of the same sky, like exposures of one visit.

    Every frame has the same `stars` (offsets from the true center `ra`/`dec`) but its own
    background (`background_levels`, default 1..n MJy/sr), independent noise (seed + frame),
    WCS center displaced by up to `wcs_jitter_px` px and rotated by up to
    `rotation_jitter_deg` degrees (frame 0 gets zero jitter). `moving_object` is drawn at
    `moving_object.star_at(i)` in frame i. Extra kwargs go to `make_cutout_hdul`.
    """
    levels = list(background_levels or [float(i + 1) for i in range(n_frames)])
    if len(levels) != n_frames:
        raise ValueError("background_levels must have n_frames entries")
    rng = np.random.default_rng(seed)
    result = []
    for i in range(n_frames):
        jn, je = (rng.uniform(-1, 1, 2) * wcs_jitter_px) if i else (0.0, 0.0)
        rot = rng.uniform(-1, 1) * rotation_jitter_deg if i else 0.0
        center_ra, center_dec = star_sky_position(ra, dec, Star(north_px=jn, east_px=je))
        hdul = make_cutout_hdul(
            ra=center_ra,
            dec=center_dec,
            shape=shape,
            rotation_deg=rot,
            stars=(),
            background=levels[i],
            noise_sigma=noise_sigma,
            seed=seed + 1000 * (i + 1),
            **kwargs,
        )
        sky = list(stars)
        if moving_object is not None:
            sky.append(moving_object.star_at(i))
        _add_stars(hdul, ra, dec, sky)
        result.append(to_fits_bytes(hdul, gzip=gzip))
    return result


def make_channel_cutout_bytes(
    detectors: Sequence[str] = ("D1", "D2", "D3", "D4", "D5", "D6"),
    *,
    stars_per_detector: Mapping[str, Sequence[Star]] | None = None,
    default_stars: Sequence[Star] = (),
    seed: int = 1234,
    gzip: bool = False,
    **kwargs,
) -> dict[str, bytes]:
    """One cutout per detector of the same observation, with per-detector sources.

    `stars_per_detector` maps e.g. "D3" to its stars; detectors not listed get `default_stars`
    (none by default, so a star listed only for D3 appears in D3 alone). Noise is independent
    per detector. Extra kwargs (ra, dec, shape, background, ...) go to `make_cutout_hdul`.
    """
    per_detector = stars_per_detector or {}
    return {
        det: make_cutout_bytes(
            stars=per_detector.get(det, default_stars),
            seed=seed + 100 * int(det.lstrip("D")),
            gzip=gzip,
            **kwargs,
        )
        for det in detectors
    }
