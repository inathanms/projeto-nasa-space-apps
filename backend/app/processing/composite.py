from collections.abc import Sequence

import numpy as np

from app.processing.rendering import Stretch, normalize_stretch


def compose_rgb(
    channels: Sequence[np.ndarray],
    vmins: Sequence[float],
    vmaxs: Sequence[float],
    stretch: Stretch,
) -> np.ndarray:
    """Combine 3 FITS-oriented 2D channels (R, G, B) into a uint8 (H, W, 4) RGBA array.

    Each channel is scaled with its own vmin/vmax (MJy/sr). Alpha is 0 where any channel is
    NaN. The result is in PNG row order (row 0 at the top).
    """
    if len(channels) != 3 or len(vmins) != 3 or len(vmaxs) != 3:
        raise ValueError("compose_rgb needs exactly 3 channels, 3 vmins and 3 vmaxs")
    arrays = [np.asarray(c) for c in channels]
    if any(a.ndim != 2 for a in arrays) or any(a.shape != arrays[0].shape for a in arrays):
        raise ValueError("all channels must be 2D arrays with the same shape")

    height, width = arrays[0].shape
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    valid = np.ones((height, width), dtype=bool)
    for i, (a, vmin, vmax) in enumerate(zip(arrays, vmins, vmaxs, strict=True)):
        rgba[..., i] = np.rint(normalize_stretch(a, vmin, vmax, stretch) * 255).astype(np.uint8)
        valid &= np.isfinite(a)
    rgba[..., 3] = np.where(valid, 255, 0)
    return np.ascontiguousarray(np.flipud(rgba))
