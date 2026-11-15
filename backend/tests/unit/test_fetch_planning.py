import pytest

from app.config import Settings
from app.domain.errors import (
    DetectorNotAvailableError,
    ObservationNotFoundError,
    RequestTooLargeError,
)
from app.domain.models import Detector, ImageRecord
from app.services.fetch_planning import plan_frames

D1, D2, D3, D4, D5, D6 = Detector
RGB = (D1, D2, D3)
PAIRS = ((D1, D4), (D2, D5), (D3, D6))


def rec(obs: str, det: Detector, mjd: float) -> ImageRecord:
    return ImageRecord(
        observation_id=obs,
        detector=det,
        wavelength_min_um=1.0,
        wavelength_max_um=2.0,
        start_mjd=mjd,
        end_mjd=mjd + 0.01,
        exposure_seconds=100.0,
        center_ra=10.0,
        center_dec=20.0,
        footprint=[],
        access_url=f"https://irsa.ipac.caltech.edu/{obs}_{det.value}.fits",
    )


def visit(n: int, start: float = 60000.0, dets=RGB, prefix: str = "o") -> list[ImageRecord]:
    return [rec(f"{prefix}{i:02d}", d, start + i * 0.5) for i in range(n) for d in dets]


def paired(n: int, start: float = 60000.0, prefix: str = "o", pairs=PAIRS) -> list[ImageRecord]:
    """Like real SPHEREx data: observation i covers the point with one pair, cycling `pairs`."""
    return [
        rec(f"{prefix}{i:02d}", d, start + i * 0.001)
        for i in range(n)
        for d in pairs[i % len(pairs)]
    ]


def settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


def plan(records, ref, channels=RGB, *, stack=True, size=0.1, align=False, **kw):
    return plan_frames(
        records, ref, channels, stack=stack, size=size, align=align, settings=settings(**kw)
    )


def ids(p, det):
    return [r.observation_id for r in p.frames[det]]


def test_ac304_twelve_obs_keeps_reference_plus_seven_closest():
    p = plan(visit(12), "o05", channels=(D1,))
    assert ids(p, D1) == [f"o{i:02d}" for i in range(1, 9)]  # tie at o01/o09 -> earlier
    assert len(p.frames[D1]) == 8
    assert not p.stack_truncated


def test_ac304_total_within_budget_not_truncated_by_stack_max():
    p = plan(visit(12), "o00", channels=(D1,), stack=True)
    assert ids(p, D1) == [f"o{i:02d}" for i in range(8)]
    assert not p.stack_truncated  # cut by STACK_MAX_EXPOSURES only


def test_reference_always_included_even_if_not_oldest_or_closest_ties():
    p = plan(visit(12), "o11", channels=(D1,))
    got = ids(p, D1)
    assert "o11" in got and got[-1] == "o11" and len(got) == 8


def test_temporal_order_with_unsorted_input():
    recs = list(reversed(visit(5)))
    p = plan(recs, "o02", channels=(D1,))
    assert ids(p, D1) == [f"o{i:02d}" for i in range(5)]


def test_ac307_budget_reduces_to_one_frame_per_channel():
    p = plan(visit(8), "o03", size=3.0, align=True)
    assert p.fetch_px == 2040
    assert p.total_cutouts == 3
    assert all(ids(p, d) == ["o03"] for d in RGB)
    assert p.stack_truncated


def test_budget_partial_reduction():
    # 4 cutouts allowed over 3 channels -> k=1 (3 total)
    p = plan(visit(8), "o03", max_cutouts_per_request=7)
    assert p.total_cutouts == 6
    assert all(len(p.frames[d]) == 2 for d in RGB)
    assert p.stack_truncated


def test_ac308_too_large_raises_without_downloads():
    with pytest.raises(RequestTooLargeError) as e:
        plan(visit(3), "o01", stack=False, max_cutouts_per_request=2)
    d = e.value.details
    assert d["total_cutouts"] == 3 and d["max_cutouts"] == 2
    assert d["fetch_pixels"] == 3 * p_px(0.1) ** 2
    assert "suggestion" in d and "max_fetch_pixels" in d


def p_px(size):
    return plan(visit(1), "o00", stack=False, size=size).fetch_px


def test_ac309_other_visit_never_enters():
    recs = visit(3, 60000.0, prefix="a") + visit(3, 60100.0, prefix="b")
    p = plan(recs, "a01")
    for d in RGB:
        assert ids(p, d) == ["a00", "a01", "a02"]
    p = plan(recs, "b00")
    assert ids(p, D1) == ["b00", "b01", "b02"]


def test_channel_with_only_reference():
    recs = visit(3, dets=(D1, D2)) + [rec("o01", D3, 60000.5)]
    p = plan(recs, "o01")
    assert ids(p, D3) == ["o01"]
    assert ids(p, D1) == ["o00", "o01", "o02"]
    assert not p.stack_truncated


def test_channel_candidates_only_with_that_detector():
    recs = visit(3, dets=(D1, D2, D3))
    recs = [r for r in recs if not (r.observation_id == "o02" and r.detector == D2)]
    p = plan(recs, "o01")
    assert ids(p, D2) == ["o00", "o01"]
    assert ids(p, D1) == ["o00", "o01", "o02"]


def test_detector_not_available_details():
    recs = visit(2, dets=(D1, D2))
    with pytest.raises(DetectorNotAvailableError) as e:
        plan(recs, "o00", channels=(D1, D4, D3))
    assert e.value.details == {
        "missing_detectors": ["D3", "D4"],
        "available_detectors": ["D1", "D2"],
    }


def test_observation_not_found():
    with pytest.raises(ObservationNotFoundError) as e:
        plan(visit(2), "nope")
    assert e.value.details == {"observation_id": "nope"}


def test_single_reference_without_detector_is_observation_not_found():
    with pytest.raises(ObservationNotFoundError) as e:
        plan(paired(6), "o00", channels=(D2,))  # o01 has D2, but single needs the reference
    assert e.value.details == {"observation_id": "o00", "detector": "D2"}


def test_single_anchor_is_the_reference():
    p = plan(paired(6), "o01", channels=(D2,), stack=False)
    assert p.anchors == {D2: p.reference}
    assert p.reference.observation_id == "o01" and p.reference.detector == D2
    assert ids(p, D2) == ["o01"]


# --- mode=rgb: one channel per detector pair, anchored on the closest exposure ---------


def anchor_ids(p) -> dict[Detector, str]:
    return {d: r.observation_id for d, r in p.anchors.items()}


def test_rgb_anchors_closest_observation_of_the_visit():
    # o00 D1+D4, o01 D2+D5, o02 D3+D6, o03 D1+D4, ...
    p = plan(paired(12), "o02", channels=(D3, D2, D1), stack=False)
    assert anchor_ids(p) == {D3: "o02", D2: "o01", D1: "o03"}
    assert p.reference.observation_id == "o02"
    assert {d: ids(p, d) for d in p.channels} == {D3: ["o02"], D2: ["o01"], D1: ["o03"]}
    assert p.total_cutouts == 3 and p.channels == (D3, D2, D1)


def test_rgb_reference_wins_for_its_own_detectors():
    p = plan(visit(4), "o02", stack=False)
    assert all(r.observation_id == "o02" for r in p.anchors.values())


def test_rgb_anchor_tie_prefers_older_observation():
    recs = [rec("a", D1, 60000.0), rec("r", D2, 60000.1), rec("r", D3, 60000.1)]
    recs += [rec("b", D1, 60000.2)]
    p = plan(recs, "r", stack=False)
    assert anchor_ids(p) == {D1: "a", D2: "r", D3: "r"}


def test_rgb_reference_record_is_a_reference_image():
    p = plan(paired(6), "o00", channels=(D3, D2, D1), stack=False)
    # The reference (D1+D4) has no channel of its own except B.
    assert p.reference.observation_id == "o00" and p.reference.detector == D1
    p = plan(paired(6), "o00", channels=(D3, D2, D5), stack=False)
    assert p.reference.observation_id == "o00" and p.reference.detector == D1


def test_rgb_detector_missing_from_whole_visit():
    no_d3 = paired(6, pairs=PAIRS[:2])
    other_visit = paired(3, start=60100.0, prefix="b")  # has D3, but another visit
    with pytest.raises(DetectorNotAvailableError) as e:
        plan(no_d3 + other_visit, "o01", channels=(D3, D2, D1))
    assert e.value.details == {
        "missing_detectors": ["D3"],
        "available_detectors": ["D1", "D2", "D4", "D5"],
    }


def test_rgb_stack_frames_closest_to_reference_with_anchor():
    p = plan(paired(12), "o02", channels=(D3, D2, D1), stack_max_exposures=3)
    assert ids(p, D3) == ["o02", "o05", "o08"]
    assert ids(p, D2) == ["o01", "o04", "o07"]  # distance 1, 2, 5; o10 dropped
    assert ids(p, D1) == ["o00", "o03", "o06"]  # distance 2, 1, 4
    assert all(p.anchors[d] in p.frames[d] for d in p.channels)
    assert not p.stack_truncated


def test_rgb_stack_budget_keeps_anchors():
    p = plan(paired(12), "o02", channels=(D3, D2, D1), size=3.0, align=True)
    assert p.total_cutouts == 3 and p.stack_truncated
    assert {d: p.frames[d] for d in p.channels} == {d: [p.anchors[d]] for d in p.channels}


def test_stack_false_one_frame_per_channel():
    p = plan(visit(5), "o02", stack=False)
    assert p.total_cutouts == 3
    assert all(ids(p, d) == ["o02"] for d in RGB)
    assert not p.stack_truncated
    assert p.channels == RGB


def test_single_channel_with_stack():
    p = plan(visit(5), "o02", channels=(D2,))
    assert p.channels == (D2,)
    assert list(p.frames) == [D2]
    assert ids(p, D2) == [f"o{i:02d}" for i in range(5)]
    assert p.total_cutouts == 5
