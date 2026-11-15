import io
import warnings

import matplotlib
import numpy as np
import pytest
from PIL import Image

from app.domain.errors import EmptyImageError
from app.processing.rendering import (
    Colormap,
    Stretch,
    compute_scale,
    encode_png,
    render_png,
    render_rgba,
)


def _decode(png: bytes) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"))


def test_ac011_explicit_scale_max_pixel_is_colormap_max():
    data = np.array([[0.0, 5.0], [7.0, 10.0]])
    vmin, vmax = compute_scale(data, 1, 99, scale_min=0, scale_max=10)
    assert (vmin, vmax) == (0.0, 10.0)
    out = render_png(data, vmin, vmax, Stretch.LINEAR, Colormap.VIRIDIS)
    px = _decode(out.png)
    top = np.array(matplotlib.colormaps["viridis"](1.0, bytes=True))
    low = np.array(matplotlib.colormaps["viridis"](0.0, bytes=True))
    # data row 1 is flipped to PNG row 0
    assert (px[0, 1] == top).all()
    assert (px[1, 0] == low).all()


def test_nan_is_transparent_without_warnings():
    data = np.array([[np.nan, 1.0], [2.0, 3.0]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        out = render_png(data, 0.0, 3.0, Stretch.LOG, Colormap.GRAY)
    px = _decode(out.png)
    assert px[1, 0, 3] == 0  # NaN at data (0,0) -> PNG last row
    assert px[0, 0, 3] == 255


def test_vertical_flip():
    data = np.zeros((4, 3))
    data[0, 1] = 1.0
    px = _decode(render_png(data, 0.0, 1.0, Stretch.LINEAR, Colormap.GRAY).png)
    assert px[3, 1, 0] == 255
    assert px[0, 1, 0] == 0


def test_dimensions_and_valid_fraction():
    data = np.ones((5, 8))
    data[0, :4] = np.nan
    out = render_png(data, 0.0, 1.0, Stretch.LINEAR, Colormap.GRAY)
    assert (out.width, out.height) == (8, 5)
    assert out.valid_fraction == pytest.approx(36 / 40)
    assert _decode(out.png).shape == (5, 8, 4)


def test_empty_image_error():
    with pytest.raises(EmptyImageError):
        compute_scale(np.full((3, 3), np.nan), 1, 99)


def test_vmin_equals_vmax():
    vmin, vmax = compute_scale(np.full((3, 3), 2.0), 1, 99)
    assert vmax == pytest.approx(vmin + 1e-6)
    assert vmax > vmin


def test_percentiles_ignore_nan():
    data = np.array([np.nan, 0.0, 10.0])
    assert compute_scale(data, 0, 100) == (0.0, 10.0)


@pytest.mark.parametrize("stretch", list(Stretch))
@pytest.mark.parametrize("colormap", list(Colormap))
def test_all_stretches_and_colormaps(stretch, colormap):
    data = np.linspace(-1, 5, 12).reshape(3, 4)
    out = render_png(data, 0.0, 4.0, stretch, colormap)
    assert out.png.startswith(b"\x89PNG")


def test_render_rgba_is_png_ordered_and_render_png_composes_it():
    data = np.array([[np.nan, 1.0], [2.0, 3.0]])
    rgba = render_rgba(data, 0.0, 3.0, Stretch.LINEAR, Colormap.GRAY)
    assert rgba.shape == (2, 2, 4) and rgba.dtype == np.uint8
    assert rgba[1, 0, 3] == 0  # NaN at data row 0 -> last PNG row
    composed = render_png(data, 0.0, 3.0, Stretch.LINEAR, Colormap.GRAY)
    assert encode_png(rgba) == composed
    assert (_decode(composed.png) == rgba).all()


def test_encode_png_valid_fraction_counts_any_nonzero_alpha():
    rgba = np.full((2, 4, 4), 255, dtype=np.uint8)
    rgba[0, :2, 3] = 0
    rgba[1, 0, 3] = 7  # partially transparent edge pixel, e.g. after upscaling
    out = encode_png(rgba)
    assert (out.width, out.height) == (4, 2)
    assert out.valid_fraction == pytest.approx(6 / 8)
