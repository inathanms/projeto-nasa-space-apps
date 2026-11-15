import numpy as np
import pytest
from PIL import Image

from app.processing import resample
from app.processing.resample import upscale_rgba


def _random_rgba(height: int, width: int) -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.integers(0, 256, size=(height, width, 4), dtype=np.uint8)


def _half_transparent_white(size: int = 16) -> np.ndarray:
    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[:, size // 2 :] = 255
    return rgba


@pytest.mark.parametrize("factor", [1, 2, 4])
@pytest.mark.parametrize("shape", [(10, 10), (20, 30)])
def test_output_dimensions(factor, shape):
    out = upscale_rgba(_random_rgba(*shape), factor)
    assert out.shape == (shape[0] * factor, shape[1] * factor, 4)
    assert out.dtype == np.uint8


def test_factor_one_returns_input_without_pillow(monkeypatch):
    rgba = _random_rgba(8, 8)

    def boom(*args, **kwargs):
        raise AssertionError("Pillow must not be called")

    monkeypatch.setattr(resample.Image, "fromarray", boom)
    out = upscale_rgba(rgba, 1)
    assert out is rgba


def test_no_dark_halo_at_opaque_border():
    out = upscale_rgba(_half_transparent_white(), 4)
    opaque = out[..., 3] == 255
    assert opaque.any()
    luminance = out[..., :3].mean(axis=-1)
    assert luminance[opaque].min() >= 0.9 * 255


def test_resizing_rgb_without_alpha_weighting_would_halo():
    # Documenta a razão do RGBa: o RGB=0 dos pixels transparentes contamina a borda
    # quando a cor é interpolada sem ponderar pelo alfa.
    rgb = Image.fromarray(_half_transparent_white()[..., :3], mode="RGB")
    arr = np.asarray(rgb.resize((64, 64), Image.Resampling.LANCZOS))
    assert arr.mean(axis=-1)[:, 32:].min() < 0.9 * 255


def test_fully_transparent_region_stays_transparent():
    out = upscale_rgba(_half_transparent_white(), 4)
    assert (out[:, :20, 3] == 0).all()


@pytest.mark.parametrize("factor", [0, -1])
def test_invalid_factor_raises(factor):
    with pytest.raises(ValueError):
        upscale_rgba(_random_rgba(4, 4), factor)
