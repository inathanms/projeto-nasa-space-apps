from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app import processing
from app.api.deps import SettingsDep, get_image_cache_service
from app.api.errors import error_responses
from app.api.image_headers import metadata_headers, position_headers
from app.api.schemas import ImageJsonResponse, ImageQuery, ResponseFormat
from app.cache.normalize import normalize_request
from app.config import Settings
from app.domain.models import Collection
from app.services.image_cache_service import CacheOutcome, CacheStatus, ImageCacheService
from app.services.image_service import ImageRequest, ImageResult

router = APIRouter(tags=["image"])

CACHE_CONTROL = "public, max-age=86400"
# 302 of response_format=redirect (spec cache 4.2).
REDIRECT_CACHE_CONTROL = "public, max-age=86400"

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
    (
        "X-Cache",
        (
            "HIT: served from the image cache; MISS: rendered now (and stored); BYPASS: cache "
            "disabled or storage unavailable, rendered without the cache."
        ),
        "HIT",
        "string",
    ),
    (
        "X-Center-Ra",
        (
            "RA of the image center, degrees, 6 decimals: the requested ra rounded to the "
            "POSITION_QUANTUM_ARCSEC grid (default 6.15 arcsec), which is what was rendered."
        ),
        "210.801500",
        "string",
    ),
    (
        "X-Center-Dec",
        "Dec of the image center, degrees, 6 decimals (normalized like X-Center-Ra).",
        "54.348917",
        "string",
    ),
    (
        "X-Render-Version",
        "Version of the rendering algorithm that produced the image.",
        "r1",
        "string",
    ),
]
EXPOSED_HEADERS = [name for name, *_ in IMAGE_HEADERS]

_HEADER_DOCS = {
    name: {"description": desc, "schema": {"type": kind, "example": example}}
    for name, desc, example, kind in IMAGE_HEADERS
}

_PNG_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "model": ImageJsonResponse,
        "description": (
            "response_format=png (default): RGBA PNG of the requested region. Invalid or "
            "uncovered pixels are transparent. Metadata (including the scale used) is returned "
            "in X-* headers. response_format=json: the image URL and all metadata as JSON "
            "(ImageJsonResponse); `url` is the public storage URL on hit/miss and this API's "
            "/image?...&response_format=png on bypass."
        ),
        "content": {
            "image/png": {"schema": {"type": "string", "format": "binary"}},
        },
        "headers": _HEADER_DOCS
        | {
            "Cache-Control": {
                "description": "Archive images never change, so responses are cacheable.",
                "schema": {"type": "string", "example": CACHE_CONTROL},
            }
        },
    },
    302: {
        "description": (
            "response_format=redirect: Location is the public URL of the cached PNG (rendered "
            "and stored first on a miss), or this API's /image?...&response_format=png on "
            "bypass. Browsers and fetch follow the redirect and do not expose the X-* headers "
            "of the 302; use response_format=json to read metadata."
        ),
        "headers": {
            "Location": {
                "description": "URL of the PNG.",
                "schema": {"type": "string", "format": "uri"},
            },
            "Cache-Control": {
                "description": "The 302 itself is cacheable for one day.",
                "schema": {"type": "string", "example": REDIRECT_CACHE_CONTROL},
            },
        }
        | _HEADER_DOCS,
    },
}


def image_headers(result: ImageResult) -> dict[str, str]:
    """Response headers of a rendered PNG: the `X-*` metadata plus `Cache-Control`."""
    return metadata_headers(result) | {"Cache-Control": CACHE_CONTROL}


def _outcome_headers(outcome: CacheOutcome, cache_control: str) -> dict[str, str]:
    """`X-*` from the sidecar (same source on hit, miss and bypass) + `X-Cache` + caching."""
    assert outcome.sidecar is not None
    return outcome.sidecar.headers | {
        "X-Cache": outcome.status.header,
        "Cache-Control": cache_control,
    }


def _image_request(params: ImageQuery, settings: Settings) -> ImageRequest:
    """Normalized request (REQ-501): rendering and cache key use the same values."""
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
    return normalize_request(request, settings.position_quantum_arcsec)


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
        "pixel remains (details.empty_channels in mode=rgb).\n\n"
        "**Cache and `response_format`.** (ra, dec) are rounded to a grid of "
        "POSITION_QUANTUM_ARCSEC (default 6.15 arcsec, one native pixel; at most half a pixel "
        "of shift) and the other floats are rounded too, so nearby requests share one cached "
        "image; X-Center-Ra/X-Center-Dec give the rendered center and X-Cache says HIT, MISS "
        "or BYPASS. `response_format`:\n"
        "- `png` (default): the PNG bytes, metadata in X-* headers.\n"
        "- `json`: **recommended for the frontend**: returns the public URL of the image and "
        "all its metadata (scale, observation, image size) in one call.\n"
        "- `redirect`: 302 to the image URL, for using the API directly in `<img src>`. "
        "Browsers and `fetch` follow the redirect and **do not expose** the X-* headers of "
        "the 302; to get metadata (e.g. the scale), use `json`. The 302 carries "
        "`Cache-Control: public, max-age=86400`.\n\n"
        "When the cache is disabled or the storage is unavailable (BYPASS), `json` returns and "
        "`redirect` points to this API's `/image?...&response_format=png` URL."
    ),
    responses=_PNG_RESPONSE | error_responses(404, 422, 502, 503, 504),
)
async def get_image(
    params: Annotated[ImageQuery, Query()],
    settings: SettingsDep,
    service: Annotated[ImageCacheService, Depends(get_image_cache_service)],
    background: BackgroundTasks,
) -> Response:
    request = _image_request(params, settings)
    fmt = params.response_format

    if fmt == ResponseFormat.PNG:
        outcome = await service.lookup_or_render(
            request, need_png=True, persist_before_return=False
        )
        if outcome.persist is not None:
            # Upload after the response (REQ-525); `persist` never raises.
            background.add_task(outcome.persist)
        return Response(
            content=outcome.png,
            media_type="image/png",
            headers=_outcome_headers(outcome, CACHE_CONTROL),
        )

    if fmt == ResponseFormat.REDIRECT and not settings.cache_enabled:
        # REQ-551/553: nothing to store, so do not render twice; the API URL renders on load.
        headers = position_headers(request.ra, request.dec, processing.RENDER_VERSION) | {
            "X-Cache": CacheStatus.BYPASS.header,
            "Cache-Control": REDIRECT_CACHE_CONTROL,
        }
        return RedirectResponse(service.bypass_url(request), status_code=302, headers=headers)

    # json/redirect need the public URL to exist before answering (REQ-525).
    outcome = await service.lookup_or_render(request, need_png=False, persist_before_return=True)
    assert outcome.sidecar is not None
    if fmt == ResponseFormat.JSON:
        return JSONResponse(
            outcome.sidecar.to_json_response(outcome.url, outcome.status),
            headers={"X-Cache": outcome.status.header},
        )
    return RedirectResponse(
        outcome.url, status_code=302, headers=_outcome_headers(outcome, REDIRECT_CACHE_CONTROL)
    )
