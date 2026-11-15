from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import SettingsDep, get_epochs_service
from app.api.errors import error_responses
from app.api.schemas import (
    DetectorImage,
    EpochsQuery,
    EpochsQueryEcho,
    EpochsResponse,
    ObservationOut,
    SkyPoint,
    VisitOut,
    iso_z,
)
from app.domain.models import DEFAULT_RGB_DETECTORS, Collection, ImageRecord, Observation, Visit
from app.processing.timeutils import iso_to_mjd, mjd_to_iso
from app.services.epochs_service import EpochsService

router = APIRouter(tags=["epochs"])

_COORD_DECIMALS = 6


def _detector_image(rec: ImageRecord) -> DetectorImage:
    return DetectorImage(
        detector=rec.detector,
        wavelength_min_um=rec.wavelength_min_um,
        wavelength_max_um=rec.wavelength_max_um,
        image_center=SkyPoint(
            ra=round(rec.center_ra, _COORD_DECIMALS), dec=round(rec.center_dec, _COORD_DECIMALS)
        ),
        footprint=[
            (round(ra, _COORD_DECIMALS), round(dec, _COORD_DECIMALS)) for ra, dec in rec.footprint
        ],
    )


def _observation(obs: Observation) -> ObservationOut:
    return ObservationOut(
        observation_id=obs.observation_id,
        visit_index=obs.visit_index,
        start_time=mjd_to_iso(obs.start_mjd),
        end_time=mjd_to_iso(obs.end_mjd),
        start_mjd=round(obs.start_mjd, 6),
        end_mjd=round(obs.end_mjd, 6),
        exposure_seconds=round(obs.exposure_seconds, 2),
        detectors=[_detector_image(r) for r in obs.images],
    )


def _visit(visit: Visit) -> VisitOut:
    return VisitOut(
        visit_index=visit.visit_index,
        start_time=mjd_to_iso(visit.start_mjd),
        end_time=mjd_to_iso(visit.end_mjd),
        start_mjd=round(visit.start_mjd, 6),
        end_mjd=round(visit.end_mjd, 6),
        observation_ids=list(visit.observation_ids),
        detectors=list(visit.detectors),
        rgb_available=set(DEFAULT_RGB_DETECTORS) <= set(visit.detectors),
    )


@router.get(
    "/epochs",
    response_model=EpochsResponse,
    summary="List SPHEREx observations of a sky position",
    description=(
        "Queries the IRSA SIA2 service for SPHEREx images covering (ra, dec) and returns them "
        "grouped by observation (one image per detector) and by visit (observations separated "
        "by at most VISIT_GAP_DAYS). Times are ISO 8601 UTC and MJD, wavelengths in µm, "
        "coordinates in ICRS degrees. An empty result is not an error."
    ),
    responses=error_responses(422, 502, 504),
)
async def list_epochs(
    params: Annotated[EpochsQuery, Query()],
    settings: SettingsDep,
    service: Annotated[EpochsService, Depends(get_epochs_service)],
) -> EpochsResponse:
    collection = params.collection or Collection(settings.irsa_default_collection)
    start_iso, end_iso = iso_z(params.start_time), iso_z(params.end_time)
    result = await service.list_epochs(
        ra=params.ra,
        dec=params.dec,
        radius=params.radius,
        collection=collection,
        detector=params.detector,
        start_time_mjd=_to_mjd(params.start_time),
        end_time_mjd=_to_mjd(params.end_time),
    )
    return EpochsResponse(
        query=EpochsQueryEcho(
            ra=params.ra,
            dec=params.dec,
            radius=params.radius,
            collection=collection,
            detector=params.detector,
            start_time=start_iso,
            end_time=end_iso,
        ),
        total_observations=len(result.observations),
        total_visits=len(result.visits),
        truncated=result.truncated,
        visits=[_visit(v) for v in result.visits],
        observations=[_observation(o) for o in result.observations],
    )


def _to_mjd(value: datetime | None) -> float | None:
    return None if value is None else iso_to_mjd(value.replace(tzinfo=None).isoformat())
