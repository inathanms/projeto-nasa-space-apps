import warnings
from collections.abc import Sequence

import numpy as np
from astropy.stats import sigma_clipped_stats


def stack_frames(frames: Sequence[np.ndarray]) -> np.ndarray:
    """Combine reprojected frames (MJy/sr, NaN = invalid) into one float32 frame.

    Each frame's background is subtracted, the frames are median-combined pixel by
    pixel, and the median of the estimated backgrounds is added back. A single frame
    is returned unchanged (as a float32 copy).
    """
    if not frames:
        raise ValueError("stack_frames requires at least one frame")
    arrays = [np.asarray(f, dtype=np.float32) for f in frames]
    shape = arrays[0].shape
    if arrays[0].ndim != 2 or any(a.shape != shape for a in arrays):
        raise ValueError("all frames must be 2D arrays with the same shape")
    if len(arrays) == 1:
        return arrays[0].copy()

    backgrounds: list[float] = []
    centered: list[np.ndarray] = []
    for arr in arrays:
        finite = np.isfinite(arr)
        if not finite.any():
            centered.append(arr)
            continue
        _, median, _ = sigma_clipped_stats(arr, mask=~finite, sigma=3.0, maxiters=5)
        backgrounds.append(float(median))
        centered.append(arr - np.float32(median))

    # Frames have different sky levels (zodiacal light varies per epoch); the median
    # would otherwise mix them and leave steps where coverage changes between frames.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="All-NaN slice", category=RuntimeWarning)
        combined = np.nanmedian(np.stack(centered), axis=0)

    if backgrounds:
        combined = combined + np.float32(np.median(backgrounds))
    return combined.astype(np.float32, copy=False)
