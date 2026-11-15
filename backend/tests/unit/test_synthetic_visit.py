import io
from itertools import pairwise
from pathlib import Path

import httpx
import numpy as np
import respx
from astropy.io import fits
from astropy.wcs import WCS

from app.clients.irsa_sia import IrsaSiaClient
from app.config import Settings
from app.domain.models import Collection, Detector
from app.processing.reprojection import pixel_count, reproject_to_north_up
from app.services.epochs_service import group_observations
from tests.synthetic_fits import (
    DEFAULT_DEC,
    DEFAULT_RA,
    MovingObject,
    Star,
    make_channel_cutout_bytes,
    make_visit_cutout_bytes,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"
SIZE = 0.25
N = pixel_count(SIZE)


def _image(data: bytes) -> tuple[np.ndarray, fits.Header]:
    with fits.open(io.BytesIO(data)) as hdul:
        return hdul["IMAGE"].data.astype(np.float64), hdul["IMAGE"].header.copy()


def _north_up(data: bytes) -> np.ndarray:
    img, header = _image(data)
    return reproject_to_north_up(img, header, DEFAULT_RA, DEFAULT_DEC, SIZE)


def _peak(img: np.ndarray) -> tuple[int, int]:
    row, col = np.unravel_index(np.nanargmax(img), img.shape)
    return int(row), int(col)


def test_frames_have_distinct_backgrounds_and_independent_noise():
    frames = make_visit_cutout_bytes(5, stars=[])
    images = [_image(f)[0] for f in frames]
    medians = [float(np.median(i)) for i in images]
    # background level + default zodi 0.5
    assert np.allclose(medians, [1.5, 2.5, 3.5, 4.5, 5.5], atol=0.02)
    residuals = [i - np.median(i) for i in images]
    assert abs(np.corrcoef(residuals[0].ravel(), residuals[1].ravel())[0, 1]) < 0.05
    assert not np.array_equal(residuals[0], residuals[1])


def test_frames_have_distinct_wcs():
    frames = make_visit_cutout_bytes(4)
    wcss = [WCS(_image(f)[1]) for f in frames]
    crvals = {tuple(np.round(w.wcs.crval, 7)) for w in wcss}
    assert len(crvals) == 4
    angles = {round(float(np.arctan2(w.wcs.pc[1][0], w.wcs.pc[0][0])), 6) for w in wcss}
    assert len(angles) == 4


def test_frames_are_deterministic():
    assert make_visit_cutout_bytes(3, seed=7) == make_visit_cutout_bytes(3, seed=7)


def test_fixed_star_reprojects_to_same_position():
    frames = make_visit_cutout_bytes(5, stars=[Star(north_px=12, east_px=-9)])
    peaks = [_peak(_north_up(f)) for f in frames]
    for peak in peaks[1:]:
        assert abs(peak[0] - peaks[0][0]) <= 1
        assert abs(peak[1] - peaks[0][1]) <= 1


def test_moving_object_changes_position_per_frame():
    mover = MovingObject(
        start_north_px=-20, start_east_px=0, step_north_px=10, step_east_px=0, amplitude=80.0
    )
    frames = make_visit_cutout_bytes(5, stars=[Star(amplitude=20.0)], moving_object=mover)
    center = (N - 1) / 2
    for i, frame in enumerate(frames):
        img = _north_up(frame)
        row, col = _peak(img)  # the mover (80) outshines the fixed star (20)
        assert abs(row - (center + (-20 + 10 * i))) <= 1.5
        assert abs(col - center) <= 1.5
    rows = [_peak(_north_up(f))[0] for f in frames]
    assert len(set(rows)) >= 4


def test_channel_cutouts_have_distinct_sources():
    cutouts = make_channel_cutout_bytes(
        ["D1", "D2", "D3"], stars_per_detector={"D3": [Star(north_px=15, east_px=10)]}
    )
    assert set(cutouts) == {"D1", "D2", "D3"}
    d1, d3 = _north_up(cutouts["D1"]), _north_up(cutouts["D3"])
    assert np.nanmax(d3) - np.nanmedian(d3) > 20
    assert np.nanmax(d1) - np.nanmedian(d1) < 1
    center = (N - 1) / 2
    row, col = _peak(d3)
    assert abs(row - (center + 15)) <= 1
    assert abs(col - (center - 10)) <= 1


async def _load_visit_multi():
    xml = (FIXTURES / "sia_visit_multi.xml").read_text()
    settings = Settings(irsa_max_retries=1)
    with respx.mock:
        respx.get(settings.irsa_sia_url).mock(return_value=httpx.Response(200, text=xml))
        async with httpx.AsyncClient() as http:
            return await IrsaSiaClient(http, settings).search(
                DEFAULT_RA, DEFAULT_DEC, 0.1, Collection.QR3
            )


async def test_visit_multi_votable_groups_into_two_visits():
    result = await _load_visit_multi()
    assert not result.truncated
    assert all(
        r.access_url.startswith("https://irsa.ipac.caltech.edu/ibe/data/spherex/")
        for r in result.records
    )
    observations, visits = group_observations(result.records, visit_gap_days=2.0)
    assert len(visits) == 2
    assert len(visits[0].observation_ids) == 12
    assert len(visits[1].observation_ids) == 4
    assert visits[1].start_mjd - visits[0].end_mjd > 150
    first = [o for o in observations if o.visit_index == 0]
    gaps = [(b.start_mjd - a.start_mjd) * 86400 for a, b in pairwise(first)]
    assert all(100 < g < 300 for g in gaps)
    assert all(abs(o.exposure_seconds - 113.5826) < 1e-6 for o in observations)


async def test_visit_multi_votable_has_one_detector_pair_per_observation():
    """Like real IRSA data: an exposure covers a point with D1+D4, D2+D5 or D3+D6 only.

    Visit 1 cycles the three pairs (``_5`` has D2 alone); visit 2 has no D3/D6 at all.
    """
    result = await _load_visit_multi()
    observations, _ = group_observations(result.records, visit_gap_days=2.0)
    pairs = [{"D1", "D4"}, {"D2", "D5"}, {"D3", "D6"}]
    dets = {o.observation_id: {i.detector.value for i in o.images} for o in observations}
    assert all(any(d <= p for p in pairs) for d in dets.values())
    first = [dets[o.observation_id] for o in observations if o.visit_index == 0]
    assert all(any(p <= d for d in first) for p in pairs)
    assert dets["2026W20_2A_0464_5"] == {"D2"}
    second = set().union(*(dets[o.observation_id] for o in observations if o.visit_index == 1))
    assert second == {"D1", "D2", "D4", "D5"}
    assert len(result.records) == 31
    assert Detector.D3 not in {r.detector for r in result.records if "W46" in r.observation_id}
