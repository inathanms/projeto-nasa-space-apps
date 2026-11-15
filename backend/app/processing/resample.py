import numpy as np
from PIL import Image


def upscale_rgba(rgba: np.ndarray, factor: int) -> np.ndarray:
    """Amplia uma imagem RGBA uint8 (H, W, 4) por `factor` com Lanczos."""
    if factor < 1:
        raise ValueError(f"factor must be >= 1, got {factor}")
    if factor == 1:
        return rgba

    height, width = rgba.shape[:2]
    # RGBa (alfa pré-multiplicado): evita halo escuro na fronteira entre pixels
    # transparentes (RGB=0) e opacos, pois o Lanczos não mistura cor de pixels invisíveis.
    image = Image.fromarray(rgba, mode="RGBA").convert("RGBa")
    image = image.resize((width * factor, height * factor), Image.Resampling.LANCZOS)
    return np.asarray(image.convert("RGBA"), dtype=np.uint8)
