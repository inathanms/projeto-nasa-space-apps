"""Pure planning of which cutouts to fetch for an RGB/single image (REQ-208, REQ-301..305, REQ-401..404)."""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from app.config import Settings
from app.domain.errors import (
    DetectorNotAvailableError,
    ObservationNotFoundError,
    RequestTooLargeError,
)
from app.domain.models import Detector, ImageRecord, Observation
from app.processing.reprojection import PIXEL_SCALE_ARCSEC
from app.services.epochs_service import group_observations

ALIGN_MARGIN = 1.5
MAX_FETCH_PX = 2040


def fetch_pixels(size: float, align: bool) -> int:
    """Cutout side in native pixels for a `size`-degree view (REQ-102).

    Aligning adds a 1.5x margin so the rotated source still covers the output grid.
    Capped at 2040 px, the SPHEREx detector side.
    """
    factor = ALIGN_MARGIN if align else 1.0
    return min(math.ceil(size * factor * 3600 / PIXEL_SCALE_ARCSEC), MAX_FETCH_PX)


@dataclass(frozen=True)
class FramePlan:
    """Frames to fetch per channel.

    `reference` is an image of the reference observation (id and time for the response);
    `anchors[c]` is the frame of channel c that must not be dropped: the reference itself in
    mode=single, the in-visit observation closest in time that has c in mode=rgb.
    """

    channels: tuple[Detector, ...]
    reference: ImageRecord
    anchors: dict[Detector, ImageRecord]
    frames: dict[Detector, list[ImageRecord]]  # per channel, temporal order, anchor included
    fetch_px: int
    total_cutouts: int
    stack_truncated: bool  # True only when the request budget (not STACK_MAX_EXPOSURES) cut frames


def _by_distance(
    observations: list[Observation], det: Detector, ref: Observation
) -> list[ImageRecord]:
    """Images of `det` in `observations`, closest in time to `ref` first (ties: ref, older)."""
    found = [
        (o, next(i for i in o.images if i.detector == det))
        for o in observations
        if any(i.detector == det for i in o.images)
    ]
    found.sort(
        key=lambda c: (
            abs(c[0].start_mjd - ref.start_mjd),
            c[0].observation_id != ref.observation_id,
            c[0].start_mjd,
            c[0].observation_id,
        )
    )
    return [img for _, img in found]


def plan_frames(
    records: list[ImageRecord],
    reference_observation_id: str,
    channels: Sequence[Detector],
    *,
    stack: bool,
    size: float,
    align: bool,
    settings: Settings,
) -> FramePlan:
    """Choose the frames per channel and enforce the cutout/pixel budget before any download.

    One channel (mode=single): the reference observation must have the detector. Three
    channels (mode=rgb): each channel is anchored on the observation of the reference's visit
    that has that detector and is closest in time to the reference, because one exposure
    covers a sky position with only one detector pair (D1+D4, D2+D5 or D3+D6).
    """
    ref_images = {r.detector: r for r in records if r.observation_id == reference_observation_id}
    if not ref_images:
        raise ObservationNotFoundError(
            f"No image found for observation_id={reference_observation_id} "
            "at the requested position.",
            details={"observation_id": reference_observation_id},
        )
    channels = tuple(channels)
    if len(channels) == 1 and channels[0] not in ref_images:
        raise ObservationNotFoundError(
            f"No image found for observation_id={reference_observation_id} "
            f"detector={channels[0].value} at the requested position.",
            details={"observation_id": reference_observation_id, "detector": channels[0].value},
        )

    observations, _ = group_observations(records, settings.visit_gap_days)
    ref_obs = next(o for o in observations if o.observation_id == reference_observation_id)
    in_visit = [o for o in observations if o.visit_index == ref_obs.visit_index]
    candidates = {d: _by_distance(in_visit, d, ref_obs) for d in channels}

    missing = sorted(d.value for d in channels if not candidates[d])
    if missing:
        available = sorted({i.detector.value for o in in_visit for i in o.images})
        raise DetectorNotAvailableError(
            f"Detector(s) {', '.join(missing)} not available in the visit of observation_id="
            f"{reference_observation_id} at the requested position.",
            details={"missing_detectors": missing, "available_detectors": available},
        )

    anchors = {d: candidates[d][0] for d in channels}
    reference = next((ref_images[d] for d in channels if d in ref_images), ref_obs.images[0])
    fetch_px = fetch_pixels(size, align)

    def select(k: int) -> dict[Detector, list[ImageRecord]]:
        # candidates are sorted by distance with the anchor first, so the anchor always stays
        return {
            d: sorted(candidates[d][:k], key=lambda r: (r.start_mjd, r.observation_id))
            for d in channels
        }

    k = settings.stack_max_exposures if stack else 1
    k = max(k, 1)
    frames = select(k)
    baseline = sum(len(v) for v in frames.values())

    def fits(fr: dict[Detector, list[ImageRecord]]) -> bool:
        total = sum(len(v) for v in fr.values())
        return (
            total <= settings.max_cutouts_per_request
            and total * fetch_px**2 <= settings.max_fetch_pixels_per_request
        )

    while not fits(frames) and k > 1:
        k -= 1
        frames = select(k)

    total = sum(len(v) for v in frames.values())
    if not fits(frames):
        raise RequestTooLargeError(
            "Request needs more cutouts than allowed.",
            details={
                "total_cutouts": total,
                "fetch_pixels": total * fetch_px**2,
                "max_cutouts": settings.max_cutouts_per_request,
                "max_fetch_pixels": settings.max_fetch_pixels_per_request,
                "suggestion": "reduce size, disable stack, or use mode=single",
            },
        )
    return FramePlan(
        channels=channels,
        reference=reference,
        anchors=anchors,
        frames=frames,
        fetch_px=fetch_px,
        total_cutouts=total,
        stack_truncated=total < baseline,
    )
