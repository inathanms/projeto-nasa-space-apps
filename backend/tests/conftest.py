from collections.abc import Callable

import pytest

from tests.synthetic_fits import (
    Star,
    make_channel_cutout_bytes,
    make_cutout_bytes,
    make_visit_cutout_bytes,
)


@pytest.fixture
def synthetic_cutout() -> Callable[..., bytes]:
    """Factory returning synthetic cutout bytes; accepts `make_cutout_bytes` kwargs."""
    return make_cutout_bytes


@pytest.fixture
def synthetic_cutout_bytes() -> bytes:
    """Default synthetic cutout: M101 center, no rotation, one star at the center."""
    return make_cutout_bytes()


@pytest.fixture
def synthetic_visit_bytes() -> list[bytes]:
    """Five exposures of one sky: backgrounds 1..5, shifted/rotated WCS, one star at the center."""
    return make_visit_cutout_bytes(5)


@pytest.fixture
def synthetic_channel_bytes() -> dict[str, bytes]:
    """D1-D6 cutouts of one observation; a star appears only in D3."""
    return make_channel_cutout_bytes(stars_per_detector={"D3": [Star(north_px=10, east_px=-8)]})
