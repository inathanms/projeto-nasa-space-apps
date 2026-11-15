import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.domain.models import DEFAULT_RGB_DETECTORS, Collection, Detector, ImageMode
from app.processing.rendering import Colormap, Stretch

M101_RA = 210.80227
M101_DEC = 54.34895
OBSERVATION_ID_PATTERN = r"^[A-Za-z0-9_]{1,64}$"

_RA = Field(
    ge=0,
    lt=360,
    allow_inf_nan=False,
    description="Right ascension, ICRS degrees. 0 <= ra < 360.",
    examples=[M101_RA],
)
_DEC = Field(
    ge=-90,
    le=90,
    allow_inf_nan=False,
    description="Declination, ICRS degrees. -90 <= dec <= 90.",
    examples=[M101_DEC],
)


def _collection_field() -> Any:
    return Field(
        None,
        description=(
            "IRSA SPHEREx collection. Defaults to IRSA_DEFAULT_COLLECTION (spherex_qr3 unless "
            "configured otherwise)."
        ),
        examples=["spherex_qr3"],
    )


def to_utc(value: datetime | None) -> datetime | None:
    """Naive datetimes are taken as UTC; aware ones are converted to UTC."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso_z(value: datetime | None) -> str | None:
    """ISO 8601 UTC with Z suffix, second precision."""
    return None if value is None else value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",")]


def parse_detectors(value: str) -> tuple[Detector, ...]:
    """'D3, D2, D1' -> 3 distinct detectors in R, G, B order (strict uppercase enum)."""
    parts = _csv(value)
    if len(parts) != 3:
        raise ValueError("detectors must have exactly 3 comma-separated values (R,G,B)")
    try:
        detectors = tuple(Detector(p) for p in parts)
    except ValueError:
        raise ValueError("detectors values must be D1, D2, D3, D4, D5 or D6") from None
    if len(set(detectors)) != 3:
        raise ValueError("detectors must be 3 distinct detectors")
    return detectors


def parse_triplet(value: str, name: str) -> tuple[float, ...]:
    """'0.1, 0.2, 0.3' -> 3 finite floats in R, G, B order."""
    parts = _csv(value)
    if len(parts) != 3:
        raise ValueError(f"{name} must have exactly 3 comma-separated numbers (R,G,B)")
    try:
        numbers = tuple(float(p) for p in parts)
    except ValueError:
        raise ValueError(f"{name} must contain only numbers") from None
    if not all(math.isfinite(n) for n in numbers):
        raise ValueError(f"{name} values must be finite numbers")
    return numbers


def _join(values: tuple[Any, ...]) -> str:
    return ",".join(str(v) for v in values)


class ResponseFormat(StrEnum):
    """How GET /image returns the image (spec cache 4.2)."""

    PNG = "png"
    JSON = "json"
    REDIRECT = "redirect"


# --- Query parameters -------------------------------------------------------------------


class EpochsQuery(BaseModel):
    """Query parameters of GET /epochs."""

    ra: float = _RA
    dec: float = _DEC
    radius: float = Field(
        0.001,
        gt=0,
        le=1.0,
        allow_inf_nan=False,
        description="Search radius around (ra, dec), degrees. 0 < radius <= 1.",
        examples=[0.001],
    )
    collection: Collection | None = _collection_field()
    detector: Detector | None = Field(
        None,
        description=(
            "Only return images from this detector (D1 0.75-1.09 µm ... D6 4.42-5.00 µm). "
            "Observations without it are omitted; visits then list only this detector, so "
            "`rgb_available` is false. Default: all detectors."
        ),
        examples=["D2"],
    )
    start_time: datetime | None = Field(
        None,
        description="Inclusive lower time bound, ISO 8601 UTC (naive values are taken as UTC).",
        examples=["2026-05-01T00:00:00Z"],
    )
    end_time: datetime | None = Field(
        None,
        validate_default=True,
        description="Inclusive upper time bound, ISO 8601 UTC. Must be >= start_time.",
        examples=["2026-05-31T23:59:59Z"],
    )

    @field_validator("start_time")
    @classmethod
    def _start_utc(cls, v: datetime | None) -> datetime | None:
        return to_utc(v)

    @field_validator("end_time")
    @classmethod
    def _end_after_start(cls, v: datetime | None, info: ValidationInfo) -> datetime | None:
        v = to_utc(v)
        start = info.data.get("start_time")
        if v is not None and start is not None and start > v:
            raise ValueError("end_time must be greater than or equal to start_time")
        return v


class ImageQuery(BaseModel):
    """Query parameters of GET /image."""

    ra: float = Field(
        ge=0,
        lt=360,
        allow_inf_nan=False,
        description="Center of the output image, right ascension in ICRS degrees. [0, 360).",
        examples=[M101_RA],
    )
    dec: float = Field(
        ge=-90,
        le=90,
        allow_inf_nan=False,
        description="Center of the output image, declination in ICRS degrees. [-90, 90].",
        examples=[M101_DEC],
    )
    observation_id: str = Field(
        pattern=OBSERVATION_ID_PATTERN,
        description="Observation id as returned by GET /epochs (letters, digits, underscore).",
        examples=["2026W20_2A_0464_3"],
    )
    mode: ImageMode = Field(
        ImageMode.SINGLE,
        description=(
            "single: one detector rendered with `colormap`. rgb: false-color infrared "
            "composite of three detectors (`detectors`, R,G,B); infrared is invisible to the "
            "eye, so the colors are a representation, not what a human would see. rgb "
            "requires align=true and forbids detector/scale_min/scale_max."
        ),
        examples=["single"],
    )
    detector: Detector | None = Field(
        None,
        validate_default=True,
        description=(
            "SPHEREx detector D1-D6 (each covers a wavelength band). Required when "
            "mode=single; not allowed when mode=rgb (use detectors)."
        ),
        examples=["D2"],
    )
    detectors: str | None = Field(
        None,
        validate_default=True,
        description=(
            "mode=rgb only: 3 distinct detectors separated by commas, in R,G,B order (spaces "
            "allowed). Default D3,D2,D1 (longest wavelength in red). Each channel comes from the "
            "exposure of the same visit closest in time to observation_id that has it; 404 "
            "DETECTOR_NOT_AVAILABLE if no exposure of the visit has one of them."
        ),
        examples=["D3,D2,D1"],
    )
    collection: Collection | None = _collection_field()
    size: float = Field(
        1.0,
        ge=0.01,
        le=3.0,
        allow_inf_nan=False,
        description=(
            "Side of the square field of view, degrees. 0.01 <= size <= 3.0. "
            "At SPHEREx's 6.15\"/px, 1.0 deg gives 585 px (minimum 16 px when align=true). "
            "A larger size shows more sky, not more detail. With align=false the image is the "
            "native cutout as delivered, which can be smaller near the detector edge."
        ),
        examples=[1.0],
    )
    upscale: int = Field(
        1,
        ge=1,
        le=4,
        description=(
            "Integer enlargement of the final image (Lanczos, premultiplied alpha). 1 <= upscale "
            "<= 4. Only smooths the presentation; it adds no information. The final side "
            "(pixels x upscale) must not exceed MAX_OUTPUT_EDGE_PX (default 4096), otherwise "
            "422 REQUEST_TOO_LARGE."
        ),
        examples=[2],
    )
    align: bool = Field(
        True,
        description=(
            'true: reproject to a north-up, east-left grid centered on (ra, dec) at 6.15"/px, '
            "so different dates line up pixel by pixel. false: native detector orientation. "
            "Must be true when mode=rgb or stack=true."
        ),
        examples=[True],
    )
    stack: bool = Field(
        False,
        description=(
            "true: median-combine the exposures of the reference observation's visit (up to "
            "STACK_MAX_EXPOSURES, closest in time, background matched) to reduce noise; per "
            "channel in mode=rgb. Requires align=true. The cutout budget may reduce the "
            "number of frames (X-Stack-Truncated). Median stacking suppresses objects that "
            "move between exposures (asteroids, comets). Use stack=false to look for moving "
            "objects."
        ),
        examples=[False],
    )
    fill_holes: bool = Field(
        False,
        description=(
            "true: fill small isolated holes left by masked pixels (up to ~40 px in area, not "
            "touching the image edge) by interpolating their neighbours, purely cosmetic. "
            "Large gaps and areas outside the detector stay transparent. false (default): "
            "every masked or uncovered pixel is transparent."
        ),
        examples=[False],
    )
    subtract_zodi: bool = Field(
        True,
        description="Subtract the zodiacal light model (ZODI extension) when available.",
        examples=[True],
    )
    stretch: Stretch = Field(
        Stretch.ASINH,
        description="Brightness stretch applied after normalization (to each channel in rgb).",
        examples=["asinh"],
    )
    colormap: Colormap = Field(
        Colormap.INFERNO,
        description=(
            "Colormap used for the PNG in mode=single. Ignored when mode=rgb (the three "
            "detectors become the red, green and blue channels)."
        ),
        examples=["inferno"],
    )
    percentile_low: float = Field(
        1.0,
        ge=0,
        lt=100,
        allow_inf_nan=False,
        description=(
            "Lower percentile of valid pixels used as vmin (per channel in rgb). "
            "0 <= x < percentile_high."
        ),
        examples=[1.0],
    )
    percentile_high: float = Field(
        99.5,
        gt=0,
        le=100,
        allow_inf_nan=False,
        validate_default=True,
        description=(
            "Upper percentile of valid pixels used as vmax (per channel in rgb). "
            "percentile_low < x <= 100."
        ),
        examples=[99.5],
    )
    scale_min: float | None = Field(
        None,
        allow_inf_nan=False,
        validate_default=True,
        description=(
            "mode=single only: explicit vmin in MJy/sr (overrides percentiles). Requires "
            "scale_max. Reuse X-Scale-Min of a previous image to keep brightness stable across "
            "dates."
        ),
        examples=[0.0123],
    )
    scale_max: float | None = Field(
        None,
        allow_inf_nan=False,
        validate_default=True,
        description=(
            "mode=single only: explicit vmax in MJy/sr. Requires scale_min and must be > scale_min."
        ),
        examples=[4.5678],
    )
    scale_mins: str | None = Field(
        None,
        validate_default=True,
        description=(
            "mode=rgb only: 3 comma-separated vmin values in MJy/sr, R,G,B order (overrides "
            "percentiles). Requires scale_maxs. Reuse X-Scale-Min of a previous rgb image."
        ),
        examples=["0.1,0.2,0.3"],
    )
    scale_maxs: str | None = Field(
        None,
        validate_default=True,
        description=(
            "mode=rgb only: 3 comma-separated vmax values in MJy/sr, R,G,B order. Requires "
            "scale_mins; each value must be greater than the matching scale_mins value."
        ),
        examples=["5,8,12"],
    )
    response_format: ResponseFormat = Field(
        ResponseFormat.PNG,
        description=(
            "png (default): the PNG bytes with metadata in X-* headers. json (recommended for "
            "the frontend): the public URL of the image plus all metadata in one call. "
            "redirect: 302 to the public URL, for <img src>; browsers and fetch follow it "
            "without exposing the X-* headers of the 302, so use json to read metadata."
        ),
        examples=["png"],
    )

    @field_validator("detector")
    @classmethod
    def _detector_for_mode(cls, v: Detector | None, info: ValidationInfo) -> Detector | None:
        mode = info.data.get("mode")
        if mode == ImageMode.SINGLE and v is None:
            raise ValueError("detector is required when mode=single")
        if mode == ImageMode.RGB and v is not None:
            raise ValueError("detector is not allowed when mode=rgb; use detectors")
        return v

    @field_validator("detectors")
    @classmethod
    def _detectors_for_mode(cls, v: str | None, info: ValidationInfo) -> str | None:
        mode = info.data.get("mode")
        if v is None:
            return (
                _join(tuple(d.value for d in DEFAULT_RGB_DETECTORS))
                if mode == ImageMode.RGB
                else None
            )
        if mode == ImageMode.SINGLE:
            raise ValueError("detectors is only allowed when mode=rgb")
        return _join(tuple(d.value for d in parse_detectors(v)))

    @field_validator("align")
    @classmethod
    def _align_for_mode(cls, v: bool, info: ValidationInfo) -> bool:
        if info.data.get("mode") == ImageMode.RGB and not v:
            raise ValueError("mode=rgb requires align=true")
        return v

    @field_validator("stack")
    @classmethod
    def _stack_needs_align(cls, v: bool, info: ValidationInfo) -> bool:
        if v and info.data.get("align") is False:
            raise ValueError("stack=true requires align=true")
        return v

    @field_validator("percentile_high")
    @classmethod
    def _percentiles_ordered(cls, v: float, info: ValidationInfo) -> float:
        low = info.data.get("percentile_low")
        if low is not None and not low < v:
            raise ValueError("percentile_high must be greater than percentile_low")
        return v

    @field_validator("scale_min")
    @classmethod
    def _scale_min_for_mode(cls, v: float | None, info: ValidationInfo) -> float | None:
        if v is not None and info.data.get("mode") == ImageMode.RGB:
            raise ValueError("scale_min is not allowed when mode=rgb; use scale_mins")
        return v

    @field_validator("scale_max")
    @classmethod
    def _scale_pair(cls, v: float | None, info: ValidationInfo) -> float | None:
        if v is not None and info.data.get("mode") == ImageMode.RGB:
            raise ValueError("scale_max is not allowed when mode=rgb; use scale_maxs")
        if "scale_min" not in info.data:
            return v  # scale_min itself is invalid; that error is already reported
        low = info.data["scale_min"]
        if (low is None) != (v is None):
            raise ValueError("scale_min and scale_max must be provided together")
        if low is not None and not low < v:
            raise ValueError("scale_max must be greater than scale_min")
        return v

    @field_validator("scale_mins")
    @classmethod
    def _scale_mins_valid(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is None:
            return None
        if info.data.get("mode") == ImageMode.SINGLE:
            raise ValueError("scale_mins is only allowed when mode=rgb; use scale_min")
        return _join(parse_triplet(v, "scale_mins"))

    @field_validator("scale_maxs")
    @classmethod
    def _scale_maxs_valid(cls, v: str | None, info: ValidationInfo) -> str | None:
        if v is not None and info.data.get("mode") == ImageMode.SINGLE:
            raise ValueError("scale_maxs is only allowed when mode=rgb; use scale_max")
        if "scale_mins" not in info.data:
            return v  # scale_mins itself is invalid; that error is already reported
        lows = info.data["scale_mins"]
        if (lows is None) != (v is None):
            raise ValueError("scale_mins and scale_maxs must be provided together")
        if v is None:
            return None
        highs = parse_triplet(v, "scale_maxs")
        if not all(
            lo < hi for lo, hi in zip(parse_triplet(lows, "scale_mins"), highs, strict=True)
        ):
            raise ValueError("each scale_maxs value must be greater than its scale_mins value")
        return _join(highs)

    @property
    def detector_tuple(self) -> tuple[Detector, ...] | None:
        return None if self.detectors is None else parse_detectors(self.detectors)

    @property
    def scale_mins_tuple(self) -> tuple[float, ...] | None:
        return None if self.scale_mins is None else parse_triplet(self.scale_mins, "scale_mins")

    @property
    def scale_maxs_tuple(self) -> tuple[float, ...] | None:
        return None if self.scale_maxs is None else parse_triplet(self.scale_maxs, "scale_maxs")


# --- /epochs response -------------------------------------------------------------------


class EpochsQueryEcho(BaseModel):
    ra: float = Field(
        description="RA searched, degrees: the requested value rounded to the position grid.",
        examples=[210.8015],
    )
    dec: float = Field(
        description="Dec searched, degrees: the requested value rounded to the position grid.",
        examples=[54.348917],
    )
    radius: float = Field(description="Search radius, degrees.", examples=[0.001])
    collection: Collection = Field(description="Collection queried.", examples=["spherex_qr3"])
    detector: Detector | None = Field(description="Detector filter, if any.", examples=[None])
    start_time: str | None = Field(
        description="Lower time bound, ISO 8601 UTC.", examples=["2026-05-01T00:00:00Z"]
    )
    end_time: str | None = Field(
        description="Upper time bound, ISO 8601 UTC.", examples=["2026-05-31T23:59:59Z"]
    )


class SkyPoint(BaseModel):
    ra: float = Field(description="Right ascension, ICRS degrees.", examples=[212.450503])
    dec: float = Field(description="Declination, ICRS degrees.", examples=[52.949064])


class DetectorImage(BaseModel):
    detector: Detector = Field(description="Detector of this image.", examples=["D2"])
    wavelength_min_um: float = Field(
        description="Lower wavelength of the detector band, µm.", examples=[1.1033]
    )
    wavelength_max_um: float = Field(
        description="Upper wavelength of the detector band, µm.", examples=[1.6499]
    )
    image_center: SkyPoint = Field(description="Center of the full detector image.")
    footprint: list[tuple[float, float]] = Field(
        description="Image corners as [ra, dec] pairs in degrees (polygon, not closed).",
        examples=[[[212.227543, 55.391716], [216.510588, 53.000415], [212.633564, 50.474454]]],
    )


class ObservationOut(BaseModel):
    observation_id: str = Field(description="IRSA obs_id.", examples=["2026W20_2A_0464_1"])
    visit_index: int = Field(description="Index of the visit it belongs to.", examples=[0])
    start_time: str = Field(description="Start, ISO 8601 UTC.", examples=["2026-05-17T10:53:45Z"])
    end_time: str = Field(description="End, ISO 8601 UTC.", examples=["2026-05-17T10:55:41Z"])
    start_mjd: float = Field(description="Start, MJD (UTC days).", examples=[61177.453996])
    end_mjd: float = Field(description="End, MJD (UTC days).", examples=[61177.455328])
    exposure_seconds: float = Field(description="Exposure time, seconds.", examples=[113.58])
    detectors: list[DetectorImage] = Field(description="Images of this observation, D1 to D6.")


class VisitOut(BaseModel):
    visit_index: int = Field(description="Visit index, starting at 0.", examples=[0])
    start_time: str = Field(description="Start, ISO 8601 UTC.", examples=["2026-05-17T10:53:45Z"])
    end_time: str = Field(description="End, ISO 8601 UTC.", examples=["2026-05-17T10:59:58Z"])
    start_mjd: float = Field(description="Start, MJD (UTC days).", examples=[61177.453996])
    end_mjd: float = Field(description="End, MJD (UTC days).", examples=[61177.458313])
    observation_ids: list[str] = Field(
        description="Observations in this visit, in time order.",
        examples=[["2026W20_2A_0464_1", "2026W20_2A_0464_3"]],
    )
    detectors: list[Detector] = Field(
        description="Detectors with at least one image in this visit, D1 to D6.",
        examples=[["D1", "D2", "D3", "D4", "D5", "D6"]],
    )
    rgb_available: bool = Field(
        description=(
            "True when the visit has D1, D2 and D3, so GET /image?mode=rgb (default "
            "detectors D3,D2,D1) works with any observation_id of this visit. Always false "
            "when /epochs is filtered by `detector`, since the visit then only sees that one."
        ),
        examples=[True],
    )


class EpochsResponse(BaseModel):
    query: EpochsQueryEcho = Field(description="Effective query parameters.")
    total_observations: int = Field(description="Number of observations.", examples=[2])
    total_visits: int = Field(description="Number of visits.", examples=[1])
    truncated: bool = Field(
        description="True when IRSA truncated the result at IRSA_SIA_MAXREC rows.",
        examples=[False],
    )
    visits: list[VisitOut] = Field(description="Visits in time order.")
    observations: list[ObservationOut] = Field(description="Observations in time order.")


# --- /image?response_format=json ------------------------------------------------------


class ImageJsonImage(BaseModel):
    width: int = Field(description="PNG width, pixels.", examples=[585])
    height: int = Field(description="PNG height, pixels.", examples=[585])
    bytes: int = Field(description="PNG size, bytes.", examples=[412337])
    sha256: str = Field(description="SHA-256 of the PNG, hex.", examples=["3f9a0c1e..."])
    pixel_scale_arcsec: float = Field(
        description="Pixel scale of the PNG, arcsec per pixel.", examples=[6.15]
    )
    native_pixel_scale_arcsec: float = Field(
        description="Native SPHEREx pixel scale, arcsec per pixel.", examples=[6.15]
    )
    valid_pixel_fraction: float = Field(
        description="Fraction of non-transparent pixels, 0-1.", examples=[0.982]
    )


class ImageJsonObservation(BaseModel):
    observation_id: str = Field(
        description="Reference observation id.", examples=["2026W20_2A_0464_3"]
    )
    observation_time: str = Field(
        description="Start time (t_min) of the reference image, ISO 8601 UTC.",
        examples=["2026-05-17T10:58:03Z"],
    )
    detectors: list[str] = Field(
        description="Detector per channel (1 in single, 3 in rgb, R,G,B order).", examples=[["D2"]]
    )
    wavelength_min_um: list[float] = Field(
        description="Lower band wavelength per channel, µm.", examples=[[1.1033]]
    )
    wavelength_max_um: list[float] = Field(
        description="Upper band wavelength per channel, µm.", examples=[[1.6499]]
    )


class ImageJsonScale(BaseModel):
    min: list[float] = Field(description="vmin per channel, MJy/sr.", examples=[[0.0123]])
    max: list[float] = Field(description="vmax per channel, MJy/sr.", examples=[[4.5678]])


class ImageJsonStack(BaseModel):
    count: list[int] = Field(description="Frames combined per channel.", examples=[[5]])
    observation_ids: list[str] = Field(
        description="Observation ids used, in time order.",
        examples=[["2026W20_2A_0464_1", "2026W20_2A_0464_3"]],
    )
    time_span_seconds: float = Field(
        description="Seconds from the first t_min to the last t_max.", examples=[612.4]
    )
    truncated: bool = Field(
        description="True when the cutout budget reduced the frames.", examples=[False]
    )


class ImageJsonResponse(BaseModel):
    """Body of GET /image?response_format=json (spec cache 4.3)."""

    url: str = Field(
        description=(
            "Where to load the PNG: the public storage URL on hit/miss, or this API's "
            "/image?...&response_format=png URL on bypass."
        ),
        examples=["https://storage.example/images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a.png"],
    )
    cache_status: Literal["hit", "miss", "bypass"] = Field(
        description="hit: served from the cache; miss: rendered and stored now; bypass: cache "
        "disabled or unavailable.",
        examples=["hit"],
    )
    key: str = Field(
        description="Storage key of the PNG.",
        examples=["images/r1/spherex_qr3/2026W20_2A_0464_3/3f9a0c1e5b7d2a4c8e6f1b3d5a7c9e0f.png"],
    )
    render_version: str = Field(description="Rendering algorithm version.", examples=["r1"])
    created_at: str = Field(
        description="When the image was rendered, ISO 8601 UTC.", examples=["2026-11-15T12:03:44Z"]
    )
    params: dict[str, Any] = Field(
        description="Normalized parameters that determine the image (cache key input).",
        examples=[{"collection": "spherex_qr3", "ra": 210.8015, "dec": 54.348917}],
    )
    image: ImageJsonImage = Field(description="PNG properties.")
    observation: ImageJsonObservation = Field(description="Observation(s) rendered.")
    scale: ImageJsonScale = Field(
        description="Scale used per channel; reuse as scale_min/scale_max across dates."
    )
    stack: ImageJsonStack | None = Field(description="Stack summary; null when stack=false.")


# --- Errors -----------------------------------------------------------------------------


class ErrorBody(BaseModel):
    code: str = Field(description="Machine-readable error code.", examples=["VALIDATION_ERROR"])
    message: str = Field(description="Human-readable message.", examples=["Invalid parameters."])
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra context, e.g. the invalid fields.",
        examples=[{"fields": [{"field": "ra", "message": "Input should be less than 360"}]}],
    )


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "OBSERVATION_NOT_FOUND",
                    "message": "No image found for observation_id=2026W20_2A_0464_9 "
                    "detector=D2 at the requested position.",
                    "details": {},
                }
            }
        }
    )

    error: ErrorBody = Field(description="Error envelope.")
