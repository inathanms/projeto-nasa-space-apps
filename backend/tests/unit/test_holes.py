import numpy as np

from app.processing.holes import fill_small_holes


def _ramp(size: int = 40) -> np.ndarray:
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    return 100.0 + 2.0 * x + 1.0 * y


def _punch(data: np.ndarray, pixels: list[tuple[int, int]]) -> np.ndarray:
    out = data.copy()
    for r, c in pixels:
        out[r, c] = np.nan
    return out


def _square(r: int, c: int, n: int) -> list[tuple[int, int]]:
    return [(r + i, c + j) for i in range(n) for j in range(n)]


def test_fills_single_pixel_hole() -> None:
    truth = _ramp()
    data = _punch(truth, [(20, 20)])
    out = fill_small_holes(data)
    assert np.isfinite(out).all()
    assert abs(out[20, 20] - truth[20, 20]) < 3.0


def test_fills_3x3_hole() -> None:
    truth = _ramp()
    data = _punch(truth, _square(20, 20, 3))
    out = fill_small_holes(data)
    assert np.isfinite(out).all()
    assert np.abs(out - truth).max() < 8.0


def test_fills_diagonal_l_shaped_hole() -> None:
    truth = _ramp()
    # (20,20)-(21,20)-(22,21): the last pixel connects only diagonally.
    data = _punch(truth, [(20, 20), (21, 20), (22, 21)])
    out = fill_small_holes(data)
    assert np.isfinite(out).all()
    assert np.abs(out - truth).max() < 5.0


def test_diagonal_neighbors_count_as_one_component() -> None:
    data = _punch(_ramp(), [(10, 10), (11, 11), (12, 12)])
    assert np.isfinite(fill_small_holes(data, max_area_px=3)).all()
    assert np.isnan(fill_small_holes(data, max_area_px=2)[11, 11])


def test_large_hole_stays_nan() -> None:
    data = _punch(_ramp(), _square(10, 10, 8))  # 64 px > 40
    out = fill_small_holes(data)
    assert np.isnan(out[10:18, 10:18]).all()


def test_border_touching_nan_stays_nan() -> None:
    data = _punch(_ramp(), [(0, 5), (5, 0), (39, 39), (20, 39)])
    out = fill_small_holes(data)
    for r, c in [(0, 5), (5, 0), (39, 39), (20, 39)]:
        assert np.isnan(out[r, c])


def test_hole_adjacent_to_border_but_not_touching_is_filled() -> None:
    data = _punch(_ramp(), [(1, 1)])
    assert np.isfinite(fill_small_holes(data)).all()


def test_valid_pixels_unchanged() -> None:
    data = _punch(_ramp(), _square(10, 10, 3) + _square(25, 25, 8) + [(0, 0)])
    out = fill_small_holes(data)
    valid = np.isfinite(data)
    np.testing.assert_array_equal(out[valid], data[valid].astype(np.float32))


def test_input_not_mutated() -> None:
    data = _punch(_ramp(), [(20, 20)])
    snapshot = data.copy()
    fill_small_holes(data)
    np.testing.assert_array_equal(data, snapshot)


def test_no_nan_returns_equal_copy() -> None:
    data = _ramp()
    out = fill_small_holes(data)
    assert out is not data
    np.testing.assert_array_equal(out, data.astype(np.float32))


def test_all_nan_returns_all_nan() -> None:
    out = fill_small_holes(np.full((10, 10), np.nan))
    assert np.isnan(out).all()


def test_custom_max_area() -> None:
    data = _punch(_ramp(), _square(20, 20, 3))  # 9 px
    assert np.isnan(fill_small_holes(data, max_area_px=8)[20:23, 20:23]).all()
    assert np.isfinite(fill_small_holes(data, max_area_px=9)).all()


def test_dtype_is_float32() -> None:
    assert fill_small_holes(_punch(_ramp(), [(5, 5)])).dtype == np.float32
    assert fill_small_holes(_ramp().astype(np.float32)).dtype == np.float32
