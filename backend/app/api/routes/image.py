from collections.abc import Iterable
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import SettingsDep, get_image_service
from app.api.errors import error_responses
from app.api.schemas import ImageQuery
from app.domain.models import Collection, ImageMode
from app.processing.reprojection import PIXEL_SCALE_ARCSEC
from app.processing.timeutils import mjd_to_iso
from app.services.image_service import ImageRequest, ImageResult, ImageService

router = APIRouter(tags=["image"])

CACHE_CONTROL = "public, max-age=86400"

_PER_CHANNEL = " In mode=rgb: 3 comma-separated values, R,G,B order."

# (header, description, example, schema type)
IMAGE_HEADERS: list[tuple[str, str, Any, str]] = [
    ("X-Mode", "Rendering mode: single or rgb.", "single", "string"),
    (
        "X-Observation-Id",
        "Observation id of the (reference) image.",
        "2026W20_2A_0464_3",
        "string",
    ),
    ("X-Detector", "Detector of the image." + _PER_CHANNEL, "D2", "string"),
    (
        "X-Channel-Observation-Ids",
        (
            "Only in mode=rgb: observation id used for each channel, R,G,B order. One exposure "
            "covers a position with only one detector pair (D1+D4, D2+D5, D3+D6), so each "
            "channel comes from the exposure of the same visit closest in time to the reference."
        ),
        "2026W20_2A_0464_3,2026W20_2A_0464_2,2026W20_2A_0464_4",
        "string",
    ),
    (
        "X-Channel-Time-Span-Seconds",
        (
            "Only in mode=rgb: seconds from the earliest t_min to the latest t_max of the "
            "channel observations. Objects that move faster than this appear displaced between "
            "colors."
        ),
        347.6,
        "number",
    ),
    (
        "X-Observation-Time",
        "Start time (t_min) of the reference image, ISO 8601 UTC.",
        "2026-05-17T10:58:03Z",
        "string",
    ),
    (
        "X-Wavelength-Min-Um",
        "Lower wavelength of the detector band, µm." + _PER_CHANNEL,
        "1.1033",
        "string",
    ),
    (
        "X-Wavelength-Max-Um",
        "Upper wavelength of the detector band, µm." + _PER_CHANNEL,
        "1.6499",
        "string",
    ),
    ("X-Scale-Min", "vmin used for the stretch, MJy/sr." + _PER_CHANNEL, "0.0123", "string"),
    ("X-Scale-Max", "vmax used for the stretch, MJy/sr." + _PER_CHANNEL, "4.5678", "string"),
    ("X-Image-Width", "Final PNG width (native pixels x upscale), pixels.", 1170, "integer"),
    ("X-Image-Height", "Final PNG height (native pixels x upscale), pixels.", 1170, "integer"),
    ("X-Upscale", "Upscale factor applied to the final image.", 2, "integer"),
    (
        "X-Pixel-Scale-Arcsec",
        "Pixel scale of the returned PNG (6.15 / upscale), arcsec per pixel.",
        3.075,
        "number",
    ),
    (
        "X-Native-Pixel-Scale-Arcsec",
        "Native SPHEREx pixel scale, always 6.15 arcsec per pixel.",
        6.15,
        "number",
    ),
    ("X-Valid-Pixel-Fraction", "Fraction of non-transparent pixels, 0-1.", 0.982, "number"),
    (
        "X-Stack-Count",
        "Only with stack=true: frames actually combined (1 means no other exposure was "
        "available)." + _PER_CHANNEL,
        "5",
        "string",
    ),
    (
        "X-Stack-Observation-Ids",
        (
            "Only with stack=true: comma-separated observation ids used, in time order "
            "(in mode=rgb, the union over the channels)."
        ),
        "2026W20_2A_0464_1,2026W20_2A_0464_2,2026W20_2A_0464_3",
        "string",
    ),
    (
        "X-Stack-Time-Span-Seconds",
        (
            "Only with stack=true: seconds from the first t_min to the last t_max of the frames "
            "used."
        ),
        612.4,
        "number",
    ),
    (
        "X-Stack-Truncated",
        (
            "Only present (value true) when the per-request cutout budget reduced the number of "
            "stacked frames."
        ),
        "true",
        "string",
    ),
]
EXPOSED_HEADERS = [name for name, *_ in IMAGE_HEADERS]

_PNG_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "description": (
            "RGBA PNG of the requested region. Invalid or uncovered pixels are transparent. "
            "Metadata (including the scale used) is returned in X-* headers."
        ),
        "content": {"image/png": {"schema": {"type": "string", "format": "binary"}}},
        "headers": {
            name: {"description": desc, "schema": {"type": kind, "example": example}}
            for name, desc, example, kind in IMAGE_HEADERS
        }
        | {
            "Cache-Control": {
                "description": "Archive images never change, so responses are cacheable.",
                "schema": {"type": "string", "example": CACHE_CONTROL},
            }
        },
    }
}


def _join(values: Iterable[object]) -> str:
    return ",".join(str(v) for v in values)


def image_headers(result: ImageResult) -> dict[str, str]:
    """Response headers; floats keep Python repr (e.g. 0.0, 10.0, 3.075).

    Id and time come from the reference observation; per-channel values from each channel's
    anchor image (the reference itself in mode=single).
    """
    refs = result.anchors
    headers = {
        "X-Mode": result.mode.value,
        "X-Observation-Id": result.record.observation_id,
        "X-Detector": _join(r.detector.value for r in refs),
        "X-Observation-Time": mjd_to_iso(result.record.start_mjd),
        "X-Wavelength-Min-Um": _join(r.wavelength_min_um for r in refs),
        "X-Wavelength-Max-Um": _join(r.wavelength_max_um for r in refs),
        "X-Scale-Min": _join(result.vmins),
        "X-Scale-Max": _join(result.vmaxs),
        "X-Image-Width": str(result.width),
        "X-Image-Height": str(result.height),
        "X-Upscale": str(result.upscale),
        # Rounded so 6.15 / 3 reads 2.05, not 2.0500000000000003.
        "X-Pixel-Scale-Arcsec": str(round(result.pixel_scale_arcsec, 6)),
        "X-Native-Pixel-Scale-Arcsec": str(PIXEL_SCALE_ARCSEC),
        "X-Valid-Pixel-Fraction": str(round(result.valid_fraction, 4)),
        "Cache-Control": CACHE_CONTROL,
    }
    if result.mode == ImageMode.RGB:
        span_days = max(r.end_mjd for r in refs) - min(r.start_mjd for r in refs)
        headers["X-Channel-Observation-Ids"] = _join(r.observation_id for r in refs)
        headers["X-Channel-Time-Span-Seconds"] = str(round(span_days * 86400, 3))
    if result.stack:
        used = [r for frames in result.used_frames for r in frames]
        first_seen: dict[str, float] = {}
        for r in used:
            first_seen[r.observation_id] = min(
                r.start_mjd, first_seen.get(r.observation_id, r.start_mjd)
            )
        ordered = sorted(first_seen, key=lambda obs: (first_seen[obs], obs))
        span_days = max(r.end_mjd for r in used) - min(r.start_mjd for r in used)
        headers["X-Stack-Count"] = _join(result.stack_counts)
        headers["X-Stack-Observation-Ids"] = ",".join(ordered)
        headers["X-Stack-Time-Span-Seconds"] = str(round(span_days * 86400, 3))
        if result.stack_truncated:
            headers["X-Stack-Truncated"] = "true"
    return headers


@router.get(
    "/image",
    response_class=Response,
    summary="Render a SPHEREx image of a sky region as PNG",
    description=(
        "Resolves the image of `observation_id` + `detector` covering (ra, dec) via IRSA SIA2, "
        "downloads a server-side cutout, subtracts zodiacal light, masks bad pixels (FLAGS), "
        "optionally reprojects it north-up and returns a stretched, colormapped RGBA PNG. "
        "Reuse X-Scale-Min/X-Scale-Max as scale_min/scale_max to compare dates consistently.\n\n"
        "**Resolution:** each SPHEREx pixel covers 6.15 arcsec of sky. This is a property of "
        "the instrument (built for all-sky spectroscopy, not high-resolution photos). A larger "
        "`size` shows more sky, not more detail; `upscale` only smooths the presentation and "
        "adds no information. No super-resolution or generative technique is used.\n\n"
        "`fill_holes=true` (an extension beyond the spec) fills small isolated holes of masked "
        "pixels (up to ~40 px in area) by interpolation; with the default false, every "
        "masked or uncovered pixel is transparent.\n\n"
        "**mode=rgb** builds a false-color infrared composite: three detectors (`detectors`, "
        "default D3,D2,D1 = red, green, blue, longest wavelength in red) are reprojected to the "
        "same grid, scaled per channel (percentiles or `scale_mins`/`scale_maxs`) and combined; "
        "each channel comes from the exposure of the reference's visit that has that detector "
        "and is closest in time to `observation_id` (one exposure covers a position with only "
        "one detector pair: D1+D4, D2+D5 or D3+D6), see X-Channel-Observation-Ids; "
        "`colormap` is ignored. Infrared is invisible to the eye, so the colors are a "
        "representation. A pixel is transparent if any channel is invalid. Per-channel headers "
        "carry 3 comma-separated values in R,G,B order.\n\n"
        "**stack=true** median-combines the exposures of the same visit as `observation_id` "
        "(background matched per frame) to reduce noise; it also erases objects that move "
        "between exposures. Requires align=true.\n\n"
        "Errors specific to this route: 404 DETECTOR_NOT_AVAILABLE when no observation of "
        "the reference's visit has a requested rgb detector (details.missing_detectors, "
        "details.available_detectors). 422 REQUEST_TOO_LARGE, before contacting IRSA, when "
        "the final side (pixels x upscale) exceeds MAX_OUTPUT_EDGE_PX, or, before any cutout "
        "download, when the cutout budget (MAX_CUTOUTS_PER_REQUEST, "
        "MAX_FETCH_PIXELS_PER_REQUEST) is exceeded even with one frame per channel; stacks "
        "are first reduced to fit (X-Stack-Truncated: true). 422 EMPTY_IMAGE when no valid "
        "pixel remains (details.empty_channels in mode=rgb)."
    ),
    responses=_PNG_RESPONSE | error_responses(404, 422, 502, 503, 504),
)
async def get_image(
    params: Annotated[ImageQuery, Query()],
    settings: SettingsDep,
    service: Annotated[ImageService, Depends(get_image_service)],
) -> Response:
    request = ImageRequest(
        ra=params.ra,
        dec=params.dec,
        observation_id=params.observation_id,
        collection=params.collection or Collection(settings.irsa_default_collection),
        detector=params.detector,
        mode=params.mode,
        detectors=params.detector_tuple,
        size=params.size,
        upscale=params.upscale,
        align=params.align,
        stack=params.stack,
        fill_holes=params.fill_holes,
        subtract_zodi=params.subtract_zodi,
        stretch=params.stretch,
        colormap=params.colormap,
        percentile_low=params.percentile_low,
        percentile_high=params.percentile_high,
        scale_min=params.scale_min,
        scale_max=params.scale_max,
        scale_mins=params.scale_mins_tuple,
        scale_maxs=params.scale_maxs_tuple,
    )
    result = await service.render(request)
    return Response(content=result.png, media_type="image/png", headers=image_headers(result))
