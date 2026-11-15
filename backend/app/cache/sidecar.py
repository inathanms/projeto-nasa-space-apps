"""Sidecar JSON stored next to each cached PNG (spec cache 4.3/4.4, REQ-522/524).

The sidecar is the "write finished" marker: a PNG counts as cached only when its sidecar exists.
It also holds the serialized `X-*` headers, the single source for headers on PNG/redirect hits.
"""

import hashlib
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from app import processing
from app.api.image_headers import metadata_headers, position_headers, stack_summary
from app.cache.keys import image_cache_params
from app.processing.reprojection import PIXEL_SCALE_ARCSEC
from app.processing.timeutils import mjd_to_iso
from app.services.image_service import ImageRequest, ImageResult

SCHEMA_VERSION = 1


class SidecarImage(BaseModel):
    width: int
    height: int
    bytes: int
    sha256: str
    pixel_scale_arcsec: float
    native_pixel_scale_arcsec: float
    valid_pixel_fraction: float


class SidecarObservation(BaseModel):
    observation_id: str
    observation_time: str
    detectors: list[str]
    wavelength_min_um: list[float]
    wavelength_max_um: list[float]


class SidecarScale(BaseModel):
    min: list[float]
    max: list[float]


class SidecarStack(BaseModel):
    count: list[int]
    observation_ids: list[str]
    time_span_seconds: float
    truncated: bool


class Sidecar(BaseModel):
    """Content of `{hash}.json`. `public_url` is None only for renders that were not stored."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal[1] = SCHEMA_VERSION
    key: str
    public_url: str | None
    render_version: str
    created_at: str
    params: dict[str, Any]
    image: SidecarImage
    observation: SidecarObservation
    scale: SidecarScale
    stack: SidecarStack | None
    headers: dict[str, str]

    @classmethod
    def from_result(
        cls,
        req: ImageRequest,
        result: ImageResult,
        *,
        key: str,
        public_url: str | None,
        created_at: datetime | None = None,
    ) -> "Sidecar":
        """Build from a render of the normalized `req`."""
        render_version = processing.RENDER_VERSION
        params = {k: v for k, v in image_cache_params(req).items() if k != "render_version"}
        refs = result.anchors
        summary = stack_summary(result)
        return cls(
            key=key,
            public_url=public_url,
            render_version=render_version,
            created_at=(created_at or datetime.now(UTC)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            params=params,
            image=SidecarImage(
                width=result.width,
                height=result.height,
                bytes=len(result.png),
                sha256=hashlib.sha256(result.png).hexdigest(),
                pixel_scale_arcsec=round(result.pixel_scale_arcsec, 6),
                native_pixel_scale_arcsec=PIXEL_SCALE_ARCSEC,
                valid_pixel_fraction=round(result.valid_fraction, 4),
            ),
            observation=SidecarObservation(
                observation_id=result.record.observation_id,
                observation_time=mjd_to_iso(result.record.start_mjd),
                detectors=[r.detector.value for r in refs],
                wavelength_min_um=[r.wavelength_min_um for r in refs],
                wavelength_max_um=[r.wavelength_max_um for r in refs],
            ),
            scale=SidecarScale(min=list(result.vmins), max=list(result.vmaxs)),
            stack=None
            if summary is None
            else SidecarStack(
                count=list(summary.counts),
                observation_ids=list(summary.observation_ids),
                time_span_seconds=summary.time_span_seconds,
                truncated=summary.truncated,
            ),
            headers=metadata_headers(result) | position_headers(req.ra, req.dec, render_version),
        )

    def to_json_response(self, url: str, cache_status: str) -> dict[str, Any]:
        """Body of `response_format=json` (4.3): sidecar content plus `url` and `cache_status`."""
        body = self.model_dump(mode="json", exclude={"schema_version", "public_url", "headers"})
        return {"url": url, "cache_status": str(cache_status).lower()} | body
