"""Public response contract shared by the live API and offline examples."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, model_validator

CollectionName = Literal["spherex_dr1", "spherex_qr3"]
TimelineCollection = Literal["spherex_dr1", "spherex_qr3", "spherex_dr1_deep", "spherex_qr3_deep"]
RA = Annotated[float, Field(ge=0, lt=360, allow_inf_nan=False)]
Dec = Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False)]


class Frame(BaseModel):
    frame_id: str
    observed_at_utc: AwareDatetime
    collection: TimelineCollection
    detector: str
    wavelength_um: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    bandwidth_um: Annotated[float, Field(gt=0, allow_inf_nan=False)]
    calibration_version: str
    source_url: HttpUrl
    cutout_url: HttpUrl
    valid_fraction: Annotated[float, Field(ge=0, le=1)]
    image_src: str


class Sequence(BaseModel):
    sequence_id: str
    ra_deg: RA
    dec_deg: Dec
    fov_arcmin: Literal[6] = 6
    collections: Annotated[list[CollectionName], Field(min_length=1, max_length=2)]
    fetched_at_utc: AwareDatetime
    generated_at_utc: AwareDatetime
    processing_version: str
    frames: tuple[Frame, Frame]

    @model_validator(mode="after")
    def validate_frames(self) -> "Sequence":
        first, second = self.frames
        if first.observed_at_utc >= second.observed_at_utc:
            raise ValueError("As datas dos dois quadros precisam estar em ordem crescente.")
        if any(frame.collection not in self.collections for frame in self.frames):
            raise ValueError("A coleção do quadro precisa constar na sequência.")
        return self


class ServiceError(BaseModel):
    code: Literal["insufficient_coverage", "archive_unavailable", "search_timeout", "server_busy",
                  "exposure_not_found", "unusable_exposure", "incompatible_exposure"]
    message: str


class ErrorResponse(BaseModel):
    detail: ServiceError


class Health(BaseModel):
    status: Literal["ok"] = "ok"


class CatalogExposure(BaseModel):
    image_id: str
    frame_id: str
    observed_at_utc: AwareDatetime
    collection: TimelineCollection
    detector: str
    source_url: HttpUrl
    cutout_url: HttpUrl


class Timeline(BaseModel):
    ra_deg: RA
    dec_deg: Dec
    fov_arcmin: Literal[6] = 6
    incomplete_collections: list[TimelineCollection]
    exposures: list[CatalogExposure]
