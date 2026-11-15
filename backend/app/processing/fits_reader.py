import io
import logging
import zlib
from dataclasses import dataclass

import numpy as np
from astropy.io import fits

from app.domain.errors import UpstreamInvalidResponseError

logger = logging.getLogger(__name__)

_GZIP_MAGIC = b"\x1f\x8b"
_FITS_MAGIC = b"SIMPLE"


@dataclass(frozen=True)
class CutoutHdus:
    """HDUs of a SPHEREx cutout MEF. Image and zodi in MJy/sr; flags is an integer bitmask."""

    image_data: np.ndarray
    image_header: fits.Header
    flags_data: np.ndarray | None
    flags_header: fits.Header | None
    zodi_data: np.ndarray | None


def _gunzip(data: bytes, max_bytes: int | None) -> bytes:
    """Decompress (possibly multi-member) gzip, aborting once output exceeds max_bytes."""
    out: list[bytes] = []
    total = 0
    remaining = data
    try:
        while remaining:
            d = zlib.decompressobj(wbits=16 + zlib.MAX_WBITS)
            # max_length bounds memory per call, so a gzip bomb never fully inflates.
            limit = 0 if max_bytes is None else max_bytes - total + 1
            chunk = d.decompress(remaining, limit)
            total += len(chunk)
            if max_bytes is not None and total > max_bytes:
                raise UpstreamInvalidResponseError("Decompressed cutout is too large")
            if not d.eof:
                raise UpstreamInvalidResponseError("Cutout is not a valid gzip stream")
            out.append(chunk)
            remaining = d.unused_data
    except zlib.error as exc:
        raise UpstreamInvalidResponseError("Cutout is not a valid gzip stream") from exc
    return b"".join(out)


def open_cutout(data: bytes, max_bytes: int | None = None) -> CutoutHdus:
    """Parse cutout bytes (optionally gzipped) and return the IMAGE/FLAGS/ZODI HDUs by EXTNAME.

    max_bytes caps the decompressed size in bytes (gzip bomb protection).
    """
    if data[:2] == _GZIP_MAGIC:
        data = _gunzip(data, max_bytes)
    if max_bytes is not None and len(data) > max_bytes:
        raise UpstreamInvalidResponseError("Cutout is too large")
    if not data.startswith(_FITS_MAGIC):
        raise UpstreamInvalidResponseError("Cutout is not a FITS file")

    try:
        with fits.open(io.BytesIO(data), memmap=False, lazy_load_hdus=False) as hdul:
            by_name = _index_by_extname(hdul)
            image = by_name.get("IMAGE")
            if image is None or image.data is None or image.data.ndim != 2:
                raise UpstreamInvalidResponseError("Cutout has no 2D IMAGE extension")
            flags = by_name.get("FLAGS")
            zodi = by_name.get("ZODI")
            if flags is None:
                logger.warning("FLAGS extension missing", extra={"event": "flags_hdu_missing"})
            if zodi is None:
                logger.warning("ZODI extension missing", extra={"event": "zodi_hdu_missing"})
            return CutoutHdus(
                image_data=np.asarray(image.data, dtype=np.float32).copy(),
                image_header=image.header.copy(),
                flags_data=None if flags is None else np.array(flags.data),
                flags_header=None if flags is None else flags.header.copy(),
                zodi_data=None if zodi is None else np.asarray(zodi.data, dtype=np.float32).copy(),
            )
    except UpstreamInvalidResponseError:
        raise
    except Exception as exc:
        raise UpstreamInvalidResponseError("Cutout FITS could not be parsed") from exc


def _index_by_extname(hdul: fits.HDUList) -> dict[str, fits.hdu.base.ExtensionHDU]:
    found: dict[str, fits.hdu.base.ExtensionHDU] = {}
    for hdu in hdul:
        name = str(hdu.header.get("EXTNAME", "")).strip().upper()
        if name and name not in found:
            found[name] = hdu
    return found
