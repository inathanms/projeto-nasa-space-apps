import numpy as np
import pytest

from app.processing.composite import compose_rgb
from app.processing.rendering import Stretch, normalize_stretch


def _blank(h=6, w=8):
    return np.zeros((h, w))


def test_ac202_star_only_in_red_channel():
    r, g, b = _blank(), _blank(), _blank()
    y, x = 1, 3
    r[y, x] = 10.0
    out = compose_rgb([r, g, b], [0, 0, 0], [10, 10, 10], Stretch.LINEAR)
    px = out[r.shape[0] - 1 - y, x]
    assert px[0] > 200
    assert px[1] < 10 and px[2] < 10
    assert px[3] == 255


def test_ac206_nan_in_one_channel_makes_pixel_transparent():
    r, g, b = _blank(), _blank(), _blank()
    g[2, 4] = np.nan
    out = compose_rgb([r, g, b], [0, 0, 0], [1, 1, 1], Stretch.LINEAR)
    assert out[r.shape[0] - 1 - 2, 4, 3] == 0
    assert out[r.shape[0] - 1 - 2, 3, 3] == 255
    assert out[r.shape[0] - 1 - 3, 4, 3] == 255
    assert (out[..., 3] == 0).sum() == 1


def test_per_channel_scale_is_independent():
    base = np.linspace(0, 1, 48).reshape(6, 8)
    r = base
    g = 1000 + base * 500
    b = -5 + base * 2
    out = compose_rgb([r, g, b], [0, 1000, -5], [1, 1500, -3], Stretch.LINEAR)
    assert (out[..., 0] == out[..., 1]).all()
    assert (out[..., 0] == out[..., 2]).all()


@pytest.mark.parametrize("stretch", list(Stretch))
def test_every_stretch_runs(stretch):
    base = np.linspace(0, 1, 48).reshape(6, 8)
    out = compose_rgb([base, base, base], [0] * 3, [1] * 3, stretch)
    assert out.shape == (6, 8, 4)
    assert out.dtype == np.uint8


def test_dtype_and_shape():
    out = compose_rgb([_blank(), _blank(), _blank()], [0] * 3, [1] * 3, Stretch.ASINH)
    assert out.dtype == np.uint8
    assert out.shape == (6, 8, 4)


def test_orientation_row_zero_goes_to_last_row():
    r = _blank()
    r[0, 2] = 1.0
    out = compose_rgb([r, _blank(), _blank()], [0] * 3, [1] * 3, Stretch.LINEAR)
    assert out[-1, 2, 0] == 255
    assert out[0, 2, 0] == 0


@pytest.mark.parametrize(
    ("channels", "vmins", "vmaxs"),
    [
        ([_blank()] * 2, [0] * 3, [1] * 3),
        ([_blank()] * 4, [0] * 3, [1] * 3),
        ([_blank(), _blank(), _blank(5, 5)], [0] * 3, [1] * 3),
        ([_blank()] * 3, [0] * 2, [1] * 3),
        ([_blank()] * 3, [0] * 3, [1] * 4),
        ([np.zeros((2, 2, 2))] * 3, [0] * 3, [1] * 3),
    ],
)
def test_invalid_inputs_raise(channels, vmins, vmaxs):
    with pytest.raises(ValueError):
        compose_rgb(channels, vmins, vmaxs, Stretch.LINEAR)


def test_normalize_stretch_limits_and_nan():
    data = np.array([np.nan, -5.0, 0.0, 5.0, 10.0, 20.0])
    out = normalize_stretch(data, 0.0, 10.0, Stretch.LINEAR)
    assert out.dtype == np.float64
    np.testing.assert_allclose(out, [0, 0, 0, 0.5, 1, 1])
