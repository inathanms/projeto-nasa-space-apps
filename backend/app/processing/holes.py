import numpy as np
from scipy import ndimage

_EIGHT_CONNECTED = np.ones((3, 3), dtype=bool)
_SMOOTH_SIGMA = 1.2


def fill_small_holes(data: np.ndarray, max_area_px: int = 40) -> np.ndarray:
    """Fill small isolated NaN holes, keeping large or border-touching NaN regions.

    Each fillable hole takes the nearest valid value, then a light gaussian blur is
    applied inside the filled pixels only. Valid pixels are never changed.
    """
    out = np.array(data, dtype=np.float32, copy=True)
    invalid = np.isnan(out)
    if not invalid.any() or invalid.all():
        return out

    labels, count = ndimage.label(invalid, structure=_EIGHT_CONNECTED)
    areas = np.bincount(labels.ravel(), minlength=count + 1)

    # NaN touching the image edge is real detector coverage, not a bad pixel.
    border = np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]])
    keep = np.zeros(count + 1, dtype=bool)
    keep[np.unique(border)] = True
    keep |= areas > max_area_px
    keep[0] = True
    fill_mask = invalid & ~keep[labels]
    if not fill_mask.any():
        return out

    rows, cols = ndimage.distance_transform_edt(
        invalid, return_distances=False, return_indices=True
    )
    nearest = out[rows, cols]
    # Blur the fully populated image so filled patches blend with their surroundings.
    smoothed = ndimage.gaussian_filter(nearest, sigma=_SMOOTH_SIGMA)
    out[fill_mask] = smoothed[fill_mask]
    return out
