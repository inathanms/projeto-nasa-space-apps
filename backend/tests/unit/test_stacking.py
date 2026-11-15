import numpy as np
import pytest

from app.processing.stacking import stack_frames

SHAPE = (64, 64)
SIGMA = 1.0


def _sky() -> np.ndarray:
    y, x = np.mgrid[: SHAPE[0], : SHAPE[1]]
    return 50.0 * np.exp(-(((x - 32) ** 2 + (y - 32) ** 2) / (2 * 2.0**2)))


def _noisy_frames(n: int, seed: int = 0, backgrounds=None) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    bgs = backgrounds if backgrounds is not None else [0.0] * n
    return [_sky() + bg + rng.normal(0, SIGMA, SHAPE) for bg in bgs]


def _bg_std(img: np.ndarray) -> float:
    return float(np.nanstd(img[:20, :20]))


def test_ac301_noise_reduced():
    frames = _noisy_frames(5, backgrounds=[0.0] * 5)
    out = stack_frames(frames)
    assert _bg_std(out) < 0.6 * _bg_std(frames[0])


def test_ac302_moving_object_removed():
    rng = np.random.default_rng(1)
    positions = [(10, 10), (20, 40), (45, 15), (50, 50), (30, 5)]
    frames = []
    for r, c in positions:
        f = rng.normal(10.0, SIGMA, SHAPE)
        f[r - 1 : r + 2, c - 1 : c + 2] += 200.0
        frames.append(f)
    out = stack_frames(frames)
    for r, c in positions:
        assert out[r, c] < 10.0 + 3 * SIGMA


def test_ac303_no_background_steps():
    frames = _noisy_frames(5, seed=2, backgrounds=[1, 2, 3, 4, 5])
    out = stack_frames(frames)
    mask = np.ones(SHAPE, dtype=bool)
    mask[22:42, 22:42] = False
    assert np.median(out[mask]) == pytest.approx(3.0, rel=0.05)
    # Without background matching the per-pixel median would still be ~3, but the
    # smooth sky must show no offset between image quadrants either.
    assert abs(np.median(out[:20, :20]) - np.median(out[-20:, -20:])) < 0.3


def test_ac305_single_frame_unchanged():
    frame = _noisy_frames(1, seed=3, backgrounds=[7.0])[0]
    frame[5, 5] = np.nan
    out = stack_frames([frame])
    np.testing.assert_array_equal(out, frame.astype(np.float32))
    assert out is not frame
    assert out.dtype == np.float32


def test_partial_coverage_uses_available_frames():
    frames = [np.full(SHAPE, 10.0) for _ in range(3)]
    frames[0][:, :10] = np.nan
    frames[1][:, :10] = np.nan
    frames[2][:, :5] = np.nan
    out = stack_frames(frames)
    assert np.isnan(out[:, :5]).all()
    assert np.isfinite(out[:, 5:]).all()
    assert out[0, 7] == pytest.approx(10.0)


def test_all_nan_frame_in_middle_is_ignored():
    frames = _noisy_frames(3, seed=4, backgrounds=[4.0, 4.0, 4.0])
    frames[1] = np.full(SHAPE, np.nan)
    out = stack_frames(frames)
    assert np.isfinite(out).all()
    assert np.median(out) == pytest.approx(4.0, abs=0.3)


def test_all_frames_nan_stays_nan():
    out = stack_frames([np.full(SHAPE, np.nan), np.full(SHAPE, np.nan)])
    assert np.isnan(out).all()
    assert out.dtype == np.float32


def test_different_shapes_raise():
    with pytest.raises(ValueError):
        stack_frames([np.zeros((4, 4)), np.zeros((4, 5))])


def test_empty_raises():
    with pytest.raises(ValueError):
        stack_frames([])


def test_input_not_mutated_and_float32():
    frames = _noisy_frames(3, seed=5, backgrounds=[1, 2, 3])
    frames[0][3, 3] = np.nan
    copies = [f.copy() for f in frames]
    out = stack_frames(frames)
    assert out.dtype == np.float32
    for f, c in zip(frames, copies, strict=True):
        np.testing.assert_array_equal(f, c)
