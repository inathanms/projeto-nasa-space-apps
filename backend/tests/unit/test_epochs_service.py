import pytest

from app.config import Settings
from app.domain.models import Collection, Detector, ImageRecord, SiaResult
from app.services.epochs_service import EpochsService, group_observations


def rec(obs: str, det: str, start: float, end: float | None = None, exp: float = 100.0):
    return ImageRecord(
        observation_id=obs,
        detector=Detector(det),
        wavelength_min_um=1.0,
        wavelength_max_um=2.0,
        start_mjd=start,
        end_mjd=start + 0.01 if end is None else end,
        exposure_seconds=exp,
        center_ra=10.0,
        center_dec=20.0,
        footprint=[(0, 0), (1, 0), (1, 1)],
        access_url=f"https://irsa.ipac.caltech.edu/{obs}/{det}",
    )


class FakeSiaClient:
    def __init__(self, result: SiaResult) -> None:
        self.result = result
        self.calls: list[tuple] = []

    async def search(self, ra, dec, radius, collection, start_mjd=None, end_mjd=None):
        self.calls.append((ra, dec, radius, collection, start_mjd, end_mjd))
        return self.result


def test_groups_by_observation_id():
    obs, _ = group_observations(
        [rec("A", "D1", 100.0, 100.02), rec("A", "D2", 100.01, 100.05), rec("B", "D1", 101)],
        2.0,
    )
    assert [o.observation_id for o in obs] == ["A", "B"]
    assert obs[0].start_mjd == 100.0
    assert obs[0].end_mjd == 100.05
    assert len(obs[0].images) == 2


def test_orders_observations_by_time_and_detectors_d1_to_d6():
    records = [rec("late", "D1", 200), rec("early", "D6", 100), rec("early", "D2", 100)]
    obs, _ = group_observations(records, 2.0)
    assert [o.observation_id for o in obs] == ["early", "late"]
    assert [i.detector for i in obs[0].images] == [Detector.D2, Detector.D6]


def test_detector_filter_drops_observations_without_it():
    records = [rec("A", "D1", 100), rec("A", "D2", 100), rec("B", "D1", 101)]
    obs, visits = group_observations(records, 2.0, Detector.D2)
    assert [o.observation_id for o in obs] == ["A"]
    assert [i.detector for i in obs[0].images] == [Detector.D2]
    assert visits[0].observation_ids == ["A"]


def test_visit_split_only_when_gap_exceeds_threshold():
    # B starts exactly 2.0 after A ends (not split); C starts 2.5 after B ends (split).
    records = [rec("A", "D1", 100, 100.5), rec("B", "D1", 102.5, 103), rec("C", "D1", 105.5, 106)]
    obs, visits = group_observations(records, 2.0)
    assert [o.visit_index for o in obs] == [0, 0, 1]
    assert [v.visit_index for v in visits] == [0, 1]
    assert visits[0].observation_ids == ["A", "B"]
    assert (visits[0].start_mjd, visits[0].end_mjd) == (100, 103)
    assert visits[1].observation_ids == ["C"]


def test_empty():
    assert group_observations([], 2.0) == ([], [])


@pytest.mark.asyncio
async def test_list_epochs_empty_and_not_truncated():
    svc = EpochsService(FakeSiaClient(SiaResult([])), Settings())
    res = await svc.list_epochs(1, 2, 0.001, Collection.QR3, None, None, None)
    assert (res.observations, res.visits, res.truncated) == ([], [], False)


@pytest.mark.asyncio
async def test_list_epochs_propagates_truncated_and_passes_window():
    sia = FakeSiaClient(SiaResult([rec("A", "D1", 100)], truncated=True))
    svc = EpochsService(sia, Settings())
    res = await svc.list_epochs(1, 2, 0.5, Collection.DR1, None, 50.0, 150.0)
    assert res.truncated is True
    assert sia.calls == [(1, 2, 0.5, Collection.DR1, 50.0, 150.0)]


@pytest.mark.asyncio
async def test_list_epochs_local_time_window_filter():
    sia = FakeSiaClient(
        SiaResult([rec("old", "D1", 10), rec("in", "D1", 100), rec("new", "D1", 500)])
    )
    svc = EpochsService(sia, Settings())
    res = await svc.list_epochs(1, 2, 0.1, Collection.QR3, None, 50.0, 200.0)
    assert [o.observation_id for o in res.observations] == ["in"]


@pytest.mark.asyncio
async def test_list_epochs_detector_filter_and_gap_from_settings():
    sia = FakeSiaClient(
        SiaResult([rec("A", "D3", 100, 100.1), rec("B", "D3", 101, 101.1), rec("C", "D1", 102)])
    )
    svc = EpochsService(sia, Settings(visit_gap_days=0.5))
    res = await svc.list_epochs(1, 2, 0.1, Collection.QR3, Detector.D3, None, None)
    assert [o.observation_id for o in res.observations] == ["A", "B"]
    assert len(res.visits) == 2


def test_visit_detectors_are_union_sorted_and_rgb_needs_d1_d2_d3():
    records = [
        rec("A", "D5", 100),
        rec("A", "D2", 100),
        rec("B", "D1", 100.5),
        rec("B", "D3", 100.5),
        rec("C", "D1", 200),
        rec("C", "D4", 200),
    ]
    _, visits = group_observations(records, 2.0)
    assert [v.detectors for v in visits] == [
        [Detector.D1, Detector.D2, Detector.D3, Detector.D5],
        [Detector.D1, Detector.D4],
    ]


def test_visit_detectors_respect_detector_filter():
    records = [rec("A", "D1", 100), rec("A", "D2", 100), rec("A", "D3", 100)]
    _, visits = group_observations(records, 2.0, Detector.D2)
    assert visits[0].detectors == [Detector.D2]
