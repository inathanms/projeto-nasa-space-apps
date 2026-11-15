import asyncio
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from anyio import to_thread

from app.clients.http import host_allowed
from app.clients.protocols import CutoutClient, SiaClient
from app.config import Settings
from app.domain.errors import (
    EmptyImageError,
    RequestTooLargeError,
    ServerBusyError,
    UpstreamError,
    UpstreamInvalidResponseError,
    UpstreamTimeoutError,
)
from app.domain.models import DEFAULT_RGB_DETECTORS, Collection, Detector, ImageMode, ImageRecord
from app.processing.composite import compose_rgb
from app.processing.fits_reader import open_cutout
from app.processing.flags import build_mask
from app.processing.holes import fill_small_holes
from app.processing.rendering import Colormap, Stretch, compute_scale, encode_png, render_rgba
from app.processing.reprojection import PIXEL_SCALE_ARCSEC, pixel_count, reproject_to_north_up
from app.processing.resample import upscale_rgba
from app.processing.stacking import stack_frames
from app.services.fetch_planning import FramePlan, fetch_pixels, plan_frames

logger = logging.getLogger(__name__)

RESOLVE_RADIUS_DEG = 0.001

__all__ = [
    "ImageRequest",
    "ImageResult",
    "ImageService",
    "check_output_size",
    "fetch_pixels",
    "output_edge_px",
    "prepare_frame",
    "process_cutout",
    "render_channels",
]


@dataclass(frozen=True)
class ImageRequest:
    """Rendering parameters. Angles in degrees, scale bounds in MJy/sr, percentiles in [0, 100].

    mode=single uses `detector`; mode=rgb uses `detectors` (R, G, B; default D3, D2, D1).
    `scale_mins`/`scale_maxs` are the per-channel bounds of mode=rgb.
    """

    ra: float
    dec: float
    observation_id: str
    collection: Collection
    detector: Detector | None = None
    mode: ImageMode = ImageMode.SINGLE
    detectors: tuple[Detector, ...] | None = None
    size: float = 1.0
    upscale: int = 1
    align: bool = True
    stack: bool = False
    fill_holes: bool = False
    subtract_zodi: bool = True
    stretch: Stretch = Stretch.ASINH
    colormap: Colormap = Colormap.INFERNO
    percentile_low: float = 1.0
    percentile_high: float = 99.5
    scale_min: float | None = None
    scale_max: float | None = None
    scale_mins: tuple[float, ...] | None = None
    scale_maxs: tuple[float, ...] | None = None

    @property
    def channels(self) -> tuple[Detector, ...]:
        """Detectors rendered, in output order (1 for single, R, G, B for rgb)."""
        if self.mode == ImageMode.RGB:
            return tuple(self.detectors or DEFAULT_RGB_DETECTORS)
        if self.detector is None:
            raise ValueError("mode=single requires a detector")
        return (self.detector,)


@dataclass(frozen=True)
class ImageResult:
    """Rendered PNG plus metadata for response headers. Bounds in MJy/sr, durations in ms.

    Per-channel tuples (`anchors`, `vmins`, `vmaxs`, `used_frames`) follow `channels` order.
    `reference` is an image of the requested observation; `anchors` the main image of each
    channel (the reference itself in mode=single, see FramePlan); `used_frames` the images
    actually combined per channel (only the anchor when stack=false).
    """

    png: bytes
    width: int
    height: int
    valid_fraction: float
    vmins: tuple[float, ...]
    vmaxs: tuple[float, ...]
    upscale: int
    pixel_scale_arcsec: float
    reference: ImageRecord
    anchors: tuple[ImageRecord, ...]
    timings_ms: dict[str, float]
    mode: ImageMode = ImageMode.SINGLE
    stack: bool = False
    used_frames: tuple[tuple[ImageRecord, ...], ...] = ()
    stack_truncated: bool = False

    @property
    def record(self) -> ImageRecord:
        return self.reference

    @property
    def vmin(self) -> float:
        return self.vmins[0]

    @property
    def vmax(self) -> float:
        return self.vmaxs[0]

    @property
    def stack_counts(self) -> tuple[int, ...]:
        return tuple(len(frames) for frames in self.used_frames)


@dataclass(frozen=True)
class _Processed:
    png: bytes
    width: int
    height: int
    valid_fraction: float
    vmins: tuple[float, ...]
    vmaxs: tuple[float, ...]

    @property
    def vmin(self) -> float:
        return self.vmins[0]

    @property
    def vmax(self) -> float:
        return self.vmaxs[0]


def output_edge_px(req: ImageRequest) -> int:
    """Largest side of the final PNG in pixels, before any download (REQ-104).

    With align=false the native cutout is used as delivered, so its requested side is the bound.
    """
    native = pixel_count(req.size) if req.align else fetch_pixels(req.size, align=False)
    return native * req.upscale


def check_output_size(req: ImageRequest, settings: Settings) -> None:
    """Raise RequestTooLargeError when the final side exceeds MAX_OUTPUT_EDGE_PX."""
    edge = output_edge_px(req)
    if edge > settings.max_output_edge_px:
        raise RequestTooLargeError(
            f"Output image side {edge} px exceeds the limit of {settings.max_output_edge_px} px.",
            details={
                "requested_edge_px": edge,
                "max_edge_px": settings.max_output_edge_px,
                "suggestion": "reduce size or upscale",
            },
        )


def prepare_frame(raw: bytes, req: ImageRequest, settings: Settings) -> np.ndarray:
    """FITS bytes -> float32 frame in MJy/sr: ZODI subtracted, FLAGS masked (NaN) and, with
    align, reprojected to the north-up grid. A frame without valid pixels comes back all-NaN."""
    hdus = open_cutout(raw, max_bytes=settings.irsa_max_cutout_bytes)
    data = hdus.image_data

    if req.subtract_zodi and hdus.zodi_data is not None:
        if hdus.zodi_data.shape == data.shape:
            data = data - hdus.zodi_data
        else:
            logger.warning("ZODI shape mismatch; skipping", extra={"event": "zodi_shape_mismatch"})

    if hdus.flags_data is not None and hdus.flags_header is not None:
        if hdus.flags_data.shape == data.shape:
            mask = build_mask(hdus.flags_data, hdus.flags_header, settings.flags_reject_list)
            data = np.where(mask, np.float32(np.nan), data)
        else:
            logger.warning(
                "FLAGS shape mismatch; skipping", extra={"event": "flags_shape_mismatch"}
            )

    if not req.align:
        return data
    if not np.isfinite(data).any():
        n = pixel_count(req.size)
        return np.full((n, n), np.nan, dtype=np.float32)
    try:
        return reproject_to_north_up(data, hdus.image_header, req.ra, req.dec, req.size)
    except Exception as exc:  # noqa: BLE001 - bad WCS surfaces as many astropy errors
        logger.warning(
            "reprojection failed",
            extra={"event": "reprojection_failed", "error": f"{type(exc).__name__}: {exc}"},
        )
        raise UpstreamInvalidResponseError("Cutout WCS could not be used.") from None


def render_channels(frames: Sequence[Sequence[np.ndarray]], req: ImageRequest) -> _Processed:
    """Prepared frames per channel -> PNG: stack (median), fill holes, scale per channel,
    colormap (single) or RGB composite, upscale. Frames are in MJy/sr, FITS row order."""
    channels = [stack_frames(f) if req.stack else f[0] for f in frames]

    empty = [
        d.value for d, c in zip(req.channels, channels, strict=True) if not np.isfinite(c).any()
    ]
    if empty:
        if req.mode == ImageMode.SINGLE:
            raise EmptyImageError("No valid pixels in the requested region after masking.")
        raise EmptyImageError(
            f"No valid pixels in channel(s) {', '.join(empty)} in the requested region.",
            details={"empty_channels": empty},
        )

    if req.fill_holes:
        channels = [fill_small_holes(c) for c in channels]

    if req.mode == ImageMode.SINGLE:
        vmin, vmax = compute_scale(
            channels[0], req.percentile_low, req.percentile_high, req.scale_min, req.scale_max
        )
        vmins, vmaxs = (vmin,), (vmax,)
        rgba = render_rgba(channels[0], vmin, vmax, req.stretch, req.colormap)
    else:
        bounds = [
            compute_scale(
                c,
                req.percentile_low,
                req.percentile_high,
                None if req.scale_mins is None else req.scale_mins[i],
                None if req.scale_maxs is None else req.scale_maxs[i],
            )
            for i, c in enumerate(channels)
        ]
        vmins = tuple(b[0] for b in bounds)
        vmaxs = tuple(b[1] for b in bounds)
        rgba = compose_rgb(channels, vmins, vmaxs, req.stretch)

    # Upscale only the final RGBA, after reprojection at the native scale (CON-102).
    rendered = encode_png(upscale_rgba(rgba, req.upscale))
    return _Processed(
        rendered.png, rendered.width, rendered.height, rendered.valid_fraction, vmins, vmaxs
    )


def process_cutout(raw: bytes, req: ImageRequest, settings: Settings) -> _Processed:
    """Single cutout, single frame: FITS bytes -> masked, (re)projected, scaled PNG."""
    return render_channels([[prepare_frame(raw, req, settings)]], req)


def _interleave(plan: FramePlan) -> list[tuple[Detector, ImageRecord]]:
    """Frame-major job order (R0, G0, B0, R1, ...) so channels progress together."""
    depth = max(len(f) for f in plan.frames.values())
    return [
        (det, plan.frames[det][i])
        for i in range(depth)
        for det in plan.channels
        if i < len(plan.frames[det])
    ]


class ImageService:
    def __init__(
        self,
        sia: SiaClient,
        cutout: CutoutClient,
        settings: Settings,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self._sia = sia
        self._cutout = cutout
        self._settings = settings
        self._semaphore = semaphore

    async def render(self, req: ImageRequest) -> ImageResult:
        """Validate sizes and budget, resolve frames via SIA, fetch cutouts and render (4.5)."""
        total_started = time.perf_counter()
        timings: dict[str, float] = {}
        check_output_size(req, self._settings)

        started = time.perf_counter()
        sia = await self._sia.search(req.ra, req.dec, RESOLVE_RADIUS_DEG, req.collection)
        timings["sia"] = self._log_step("image_sia", started, req)

        # Detector and budget errors (404/422) are raised here: before any download or render slot.
        plan = plan_frames(
            sia.records,
            req.observation_id,
            req.channels,
            stack=req.stack,
            size=req.size,
            align=req.align,
            settings=self._settings,
        )
        for frames in plan.frames.values():
            for record in frames:
                if not host_allowed(record.access_url, self._settings.irsa_allowed_host):
                    raise UpstreamInvalidResponseError("Upstream image URL host is not allowed.")
        logger.info(
            "render plan",
            extra={
                "event": "render_plan",
                "observation_id": req.observation_id,
                "mode": req.mode.value,
                "stack": req.stack,
                "total_cutouts": plan.total_cutouts,
                "fetch_px": plan.fetch_px,
                "stack_truncated": plan.stack_truncated,
            },
        )

        try:
            await asyncio.wait_for(
                self._semaphore.acquire(), self._settings.render_queue_timeout_seconds
            )
        except TimeoutError:
            logger.warning("render queue full", extra={"event": "server_busy"})
            raise ServerBusyError("Server is busy rendering other images; retry later.") from None
        try:
            used = await self._load_frames(plan, req, timings)
            started = time.perf_counter()
            processed = await to_thread.run_sync(
                render_channels, [[f for _, f in used[d]] for d in plan.channels], req
            )
            render_ms = self._log_step(
                "image_processing", started, req, upscale=req.upscale, fill_holes=req.fill_holes
            )
            timings["processing"] = round(timings.get("processing", 0.0) + render_ms, 1)
        finally:
            self._semaphore.release()

        used_frames = tuple(tuple(rec for rec, _ in used[d]) for d in plan.channels)
        del used
        timings["total"] = self._log_step(
            "image_render",
            total_started,
            req,
            mode=req.mode.value,
            stack=req.stack,
            total_cutouts=plan.total_cutouts,
            fetch_px=plan.fetch_px,
            stack_counts=[len(f) for f in used_frames],
        )
        return ImageResult(
            png=processed.png,
            width=processed.width,
            height=processed.height,
            valid_fraction=processed.valid_fraction,
            vmins=processed.vmins,
            vmaxs=processed.vmaxs,
            upscale=req.upscale,
            pixel_scale_arcsec=PIXEL_SCALE_ARCSEC / req.upscale,
            reference=plan.reference,
            anchors=tuple(plan.anchors[d] for d in plan.channels),
            timings_ms=timings,
            mode=req.mode,
            stack=req.stack,
            used_frames=used_frames,
            stack_truncated=plan.stack_truncated,
        )

    async def _load_frames(
        self, plan: FramePlan, req: ImageRequest, timings: dict[str, float]
    ) -> dict[Detector, list[tuple[ImageRecord, np.ndarray]]]:
        """Download and prepare every planned frame (REQ-210, REQ-405).

        At most CUTOUT_FETCH_CONCURRENCY downloads run at once, and a download slot is held
        until its bytes are reprojected, so no more raw cutouts than that live in memory.
        Frames of the same channel are prepared one at a time. A non-anchor frame whose
        download fails is dropped; a failing anchor propagates its error.
        """
        slots = asyncio.Semaphore(max(1, self._settings.cutout_fetch_concurrency))
        locks = {det: asyncio.Lock() for det in plan.channels}
        download_ms: list[float] = []
        prepare_ms: list[float] = []

        async def load(det: Detector, record: ImageRecord) -> np.ndarray | None:
            ids = {"observation_id": record.observation_id, "detector": det.value}
            async with slots:
                started = time.perf_counter()
                try:
                    raw = await self._cutout.fetch(
                        record.access_url, req.ra, req.dec, plan.fetch_px
                    )
                except (UpstreamError, UpstreamTimeoutError) as exc:
                    if record.observation_id == plan.anchors[det].observation_id:
                        raise
                    logger.warning(
                        "stack frame dropped after download failure",
                        extra={"event": "stack_frame_dropped", "code": exc.code, **ids},
                    )
                    return None
                download_ms.append(
                    self._log_step(
                        "image_cutout", started, req, bytes=len(raw), fetch_px=plan.fetch_px, **ids
                    )
                )
                async with locks[det]:
                    started = time.perf_counter()
                    frame = await to_thread.run_sync(prepare_frame, raw, req, self._settings)
                    del raw
                    prepare_ms.append(self._log_step("image_reprojection", started, req, **ids))
                return frame

        jobs = _interleave(plan)
        tasks = [asyncio.ensure_future(load(det, rec)) for det, rec in jobs]
        try:
            frames = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        timings["cutout"] = round(sum(download_ms), 1)
        timings["processing"] = round(sum(prepare_ms), 1)

        used: dict[Detector, list[tuple[ImageRecord, np.ndarray]]] = {d: [] for d in plan.channels}
        for (det, rec), frame in zip(jobs, frames, strict=True):
            if frame is not None:
                used[det].append((rec, frame))
        return used

    @staticmethod
    def _log_step(event: str, started: float, req: ImageRequest, **extra: object) -> float:
        duration = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            event.replace("_", " "),
            extra={
                "event": event,
                "duration_ms": duration,
                "observation_id": req.observation_id,
                "detector": ",".join(d.value for d in req.channels),
                **extra,
            },
        )
        return duration
