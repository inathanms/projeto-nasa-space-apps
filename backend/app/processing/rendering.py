import io
from dataclasses import dataclass
from enum import StrEnum

import matplotlib
import numpy as np
from astropy.visualization import (
    AsinhStretch,
    LinearStretch,
    LogStretch,
    SqrtStretch,
)
from PIL import Image

from app.domain.errors import EmptyImageError

_VMAX_EPSILON = 1e-6


class Stretch(StrEnum):
    ASINH = "asinh"
    LINEAR = "linear"
    LOG = "log"
    SQRT = "sqrt"


class Colormap(StrEnum):
    GRAY = "gray"
    INFERNO = "inferno"
    MAGMA = "magma"
    VIRIDIS = "viridis"
    PLASMA = "plasma"
    CIVIDIS = "cividis"


_STRETCHES = {
    Stretch.ASINH: AsinhStretch(a=0.1),
    Stretch.LINEAR: LinearStretch(),
    Stretch.LOG: LogStretch(a=1000),
    Stretch.SQRT: SqrtStretch(),
}


@dataclass(frozen=True)
class RenderedImage:
    png: bytes
    width: int
    height: int
    valid_fraction: float


def compute_scale(
    data: np.ndarray,
    percentile_low: float,
    percentile_high: float,
    scale_min: float | None = None,
    scale_max: float | None = None,
) -> tuple[float, float]:
    """Return (vmin, vmax) in the data unit (MJy/sr); explicit bounds win."""
    finite = data[np.isfinite(data)]
    if finite.size == 0:
        raise EmptyImageError("Image has no finite pixels")
    vmin, vmax = np.percentile(finite, [percentile_low, percentile_high])
    if scale_min is not None:
        vmin = scale_min
    if scale_max is not None:
        vmax = scale_max
    if vmin == vmax:
        vmax = vmin + _VMAX_EPSILON
    return float(vmin), float(vmax)


def normalize_stretch(data: np.ndarray, vmin: float, vmax: float, stretch: Stretch) -> np.ndarray:
    """Return float64 in [0, 1]: linear clip to [vmin, vmax], then the stretch. NaN maps to 0."""
    if vmax == vmin:
        vmax = vmin + _VMAX_EPSILON
    # Replace NaN before the stretch so no invalid-value warnings propagate.
    safe = np.where(np.isfinite(data), data, vmin).astype(np.float64)
    x = np.clip((safe - vmin) / (vmax - vmin), 0.0, 1.0)
    return np.clip(_STRETCHES[Stretch(stretch)](x), 0.0, 1.0)


def render_rgba(
    data: np.ndarray,
    vmin: float,
    vmax: float,
    stretch: Stretch,
    colormap: Colormap,
) -> np.ndarray:
    """Map FITS-oriented data (row 0 at the bottom) to a uint8 (H, W, 4) RGBA array.

    The result is in PNG row order (row 0 at the top). NaN pixels get alpha 0.
    """
    valid = np.isfinite(data)
    x = normalize_stretch(data, vmin, vmax, stretch)

    rgba = matplotlib.colormaps[Colormap(colormap).value](x, bytes=True)
    rgba[~valid, 3] = 0
    return np.ascontiguousarray(np.flipud(rgba))


def encode_png(rgba: np.ndarray) -> RenderedImage:
    """Encode a uint8 (H, W, 4) RGBA array as PNG; valid fraction = share of pixels with alpha > 0."""
    height, width = rgba.shape[:2]
    buf = io.BytesIO()
    Image.fromarray(np.ascontiguousarray(rgba), mode="RGBA").save(buf, format="PNG", optimize=False)
    alpha = rgba[..., 3]
    return RenderedImage(
        png=buf.getvalue(),
        width=width,
        height=height,
        valid_fraction=float((alpha > 0).mean()) if alpha.size else 0.0,
    )


def render_png(
    data: np.ndarray,
    vmin: float,
    vmax: float,
    stretch: Stretch,
    colormap: Colormap,
) -> RenderedImage:
    """`render_rgba` + `encode_png`: FITS-oriented data to an RGBA PNG, NaN transparent."""
    return encode_png(render_rgba(data, vmin, vmax, stretch, colormap))
