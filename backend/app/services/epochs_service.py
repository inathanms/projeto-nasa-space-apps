from dataclasses import dataclass, field

from app.clients.protocols import SiaClient
from app.config import Settings
from app.domain.models import Collection, Detector, ImageRecord, Observation, Visit


@dataclass
class EpochsResult:
    observations: list[Observation] = field(default_factory=list)
    visits: list[Visit] = field(default_factory=list)
    truncated: bool = False


def group_observations(
    records: list[ImageRecord],
    visit_gap_days: float,
    detector: Detector | None = None,
) -> tuple[list[Observation], list[Visit]]:
    """Group images by observation_id and observations into visits. Times in MJD (days).

    A new visit starts when an observation starts more than visit_gap_days after
    the previous observation ended. exposure_seconds is the max over the images.
    """
    by_obs: dict[str, list[ImageRecord]] = {}
    for rec in records:
        if detector is None or rec.detector == detector:
            by_obs.setdefault(rec.observation_id, []).append(rec)

    observations = [
        Observation(
            observation_id=obs_id,
            start_mjd=min(r.start_mjd for r in imgs),
            end_mjd=max(r.end_mjd for r in imgs),
            exposure_seconds=max(r.exposure_seconds for r in imgs),
            images=sorted(imgs, key=lambda r: r.detector.value),
        )
        for obs_id, imgs in by_obs.items()
    ]
    observations.sort(key=lambda o: (o.start_mjd, o.observation_id))

    visits: list[Visit] = []
    for obs in observations:
        if visits and obs.start_mjd - visits[-1].end_mjd <= visit_gap_days:
            visit = visits[-1]
            visit.end_mjd = max(visit.end_mjd, obs.end_mjd)
            visit.observation_ids.append(obs.observation_id)
        else:
            visit = Visit(
                visit_index=len(visits),
                start_mjd=obs.start_mjd,
                end_mjd=obs.end_mjd,
                observation_ids=[obs.observation_id],
            )
            visits.append(visit)
        obs.visit_index = visit.visit_index
        visit.detectors = sorted({*visit.detectors, *(r.detector for r in obs.images)})
    return observations, visits


class EpochsService:
    def __init__(self, sia: SiaClient, settings: Settings) -> None:
        self._sia = sia
        self._settings = settings

    async def list_epochs(
        self,
        ra: float,
        dec: float,
        radius: float,
        collection: Collection,
        detector: Detector | None = None,
        start_time_mjd: float | None = None,
        end_time_mjd: float | None = None,
    ) -> EpochsResult:
        """Observations covering (ra, dec) [deg], radius [deg], optional MJD window [days]."""
        result = await self._sia.search(ra, dec, radius, collection, start_time_mjd, end_time_mjd)
        # Defensive: keep images overlapping the window, in case upstream ignores TIME.
        records = [
            r
            for r in result.records
            if (end_time_mjd is None or r.start_mjd <= end_time_mjd)
            and (start_time_mjd is None or r.end_mjd >= start_time_mjd)
        ]
        observations, visits = group_observations(records, self._settings.visit_gap_days, detector)
        return EpochsResult(observations, visits, result.truncated)
