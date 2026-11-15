"""Metadata of a rendered image as `X-*` response headers.

Neutral module (no FastAPI imports) shared by the `/image` route and the cache sidecar, so the
header values are computed in one place. `Cache-Control` is not included: it depends on the
response kind (PNG, redirect) and is added by the route.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.domain.models import ImageMode, ImageRecord
from app.processing.reprojection import PIXEL_SCALE_ARCSEC
from app.processing.timeutils import mjd_to_iso
from app.services.image_service import ImageResult


def join_values(values: Iterable[object]) -> str:
    return ",".join(str(v) for v in values)


def time_span_seconds(records: Iterable[ImageRecord]) -> float:
    """Seconds from the earliest t_min to the latest t_max, rounded to ms."""
    records = list(records)
    span_days = max(r.end_mjd for r in records) - min(r.start_mjd for r in records)
    return round(span_days * 86400, 3)


@dataclass(frozen=True)
class StackSummary:
    counts: tuple[int, ...]
    observation_ids: tuple[str, ...]
    time_span_seconds: float
    truncated: bool


def stack_summary(result: ImageResult) -> StackSummary | None:
    """Frames combined with stack=true (None when stack=false); ids in time order."""
    if not result.stack:
        return None
    used = [r for frames in result.used_frames for r in frames]
    first_seen: dict[str, float] = {}
    for r in used:
        first_seen[r.observation_id] = min(
            r.start_mjd, first_seen.get(r.observation_id, r.start_mjd)
        )
    ordered = sorted(first_seen, key=lambda obs: (first_seen[obs], obs))
    return StackSummary(
        counts=result.stack_counts,
        observation_ids=tuple(ordered),
        time_span_seconds=time_span_seconds(used),
        truncated=result.stack_truncated,
    )


def metadata_headers(result: ImageResult) -> dict[str, str]:
    """`X-*` headers of a render; floats keep Python repr (e.g. 0.0, 10.0, 3.075).

    Id and time come from the reference observation; per-channel values from each channel's
    anchor image (the reference itself in mode=single).
    """
    refs = result.anchors
    headers = {
        "X-Mode": result.mode.value,
        "X-Observation-Id": result.record.observation_id,
        "X-Detector": join_values(r.detector.value for r in refs),
        "X-Observation-Time": mjd_to_iso(result.record.start_mjd),
        "X-Wavelength-Min-Um": join_values(r.wavelength_min_um for r in refs),
        "X-Wavelength-Max-Um": join_values(r.wavelength_max_um for r in refs),
        "X-Scale-Min": join_values(result.vmins),
        "X-Scale-Max": join_values(result.vmaxs),
        "X-Image-Width": str(result.width),
        "X-Image-Height": str(result.height),
        "X-Upscale": str(result.upscale),
        # Rounded so 6.15 / 3 reads 2.05, not 2.0500000000000003.
        "X-Pixel-Scale-Arcsec": str(round(result.pixel_scale_arcsec, 6)),
        "X-Native-Pixel-Scale-Arcsec": str(PIXEL_SCALE_ARCSEC),
        "X-Valid-Pixel-Fraction": str(round(result.valid_fraction, 4)),
    }
    if result.mode == ImageMode.RGB:
        headers["X-Channel-Observation-Ids"] = join_values(r.observation_id for r in refs)
        headers["X-Channel-Time-Span-Seconds"] = str(time_span_seconds(refs))
    summary = stack_summary(result)
    if summary is not None:
        headers["X-Stack-Count"] = join_values(summary.counts)
        headers["X-Stack-Observation-Ids"] = ",".join(summary.observation_ids)
        headers["X-Stack-Time-Span-Seconds"] = str(summary.time_span_seconds)
        if summary.truncated:
            headers["X-Stack-Truncated"] = "true"
    return headers


def position_headers(ra: float, dec: float, render_version: str) -> dict[str, str]:
    """Normalized center (6 decimals) and render version (spec cache 4.5)."""
    return {
        "X-Center-Ra": f"{ra:.6f}",
        "X-Center-Dec": f"{dec:.6f}",
        "X-Render-Version": render_version,
    }
