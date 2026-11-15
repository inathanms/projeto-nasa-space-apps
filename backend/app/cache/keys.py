"""Deterministic cache keys (REQ-504, REQ-511..515)."""

import hashlib
import json
import re

from app import processing
from app.domain.models import ImageMode
from app.services.image_service import ImageRequest

MAX_KEY_BYTES = 512
_KEY_PATTERN = re.compile(r"^[A-Za-z0-9/_.-]+$")
_OBSERVATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,64}$")


def canonical_hash(params: dict) -> str:
    """First 32 hex chars of the SHA-256 of the canonical JSON of `params` (REQ-512)."""
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:32]


def _check_prefix(prefix: str) -> None:
    if prefix and not prefix.endswith("/"):
        raise ValueError("key prefix must end with '/'")


def _check_key(key: str) -> str:
    if not _KEY_PATTERN.fullmatch(key):
        raise ValueError("cache key has characters outside [A-Za-z0-9/_.-]")
    if len(key.encode("ascii")) >= MAX_KEY_BYTES:
        raise ValueError(f"cache key must be shorter than {MAX_KEY_BYTES} bytes")
    if any(part in ("", ".", "..") for part in key.split("/")):
        raise ValueError("cache key has an empty or relative path segment")
    return key


def _explicit(values: tuple[float, ...] | None) -> list[float] | None:
    return None if values is None else list(values)


def image_cache_params(req: ImageRequest) -> dict:
    """Parameters that determine the output pixels, without the irrelevant ones (REQ-504)."""
    rgb = req.mode == ImageMode.RGB
    params: dict = {
        "render_version": processing.RENDER_VERSION,
        "collection": req.collection.value,
        "observation_id": req.observation_id,
        "ra": req.ra,
        "dec": req.dec,
        "mode": req.mode.value,
        "size": req.size,
        "upscale": req.upscale,
        "align": req.align,
        "stack": req.stack,
        "fill_holes": req.fill_holes,
        "subtract_zodi": req.subtract_zodi,
        "stretch": req.stretch.value,
    }
    if rgb:
        params["detectors"] = [d.value for d in req.channels]
        low_explicit = req.scale_mins is not None
        high_explicit = req.scale_maxs is not None
        params["scale_mins"] = _explicit(req.scale_mins)
        params["scale_maxs"] = _explicit(req.scale_maxs)
    else:
        params["detector"] = req.channels[0].value
        params["colormap"] = req.colormap.value
        low_explicit = req.scale_min is not None
        high_explicit = req.scale_max is not None
        params["scale_min"] = req.scale_min
        params["scale_max"] = req.scale_max
    if not low_explicit:
        params["percentile_low"] = req.percentile_low
    if not high_explicit:
        params["percentile_high"] = req.percentile_high
    return {k: v for k, v in params.items() if v is not None}


def sidecar_key(png_key: str) -> str:
    if not png_key.endswith(".png"):
        raise ValueError("expected a .png key")
    return png_key[: -len(".png")] + ".json"


def image_key(req: ImageRequest, prefix: str) -> str:
    """`{prefix}images/{RENDER_VERSION}/{collection}/{observation_id}/{hash}.png` (REQ-511)."""
    _check_prefix(prefix)
    if not _OBSERVATION_ID_PATTERN.fullmatch(req.observation_id):
        raise ValueError("invalid observation_id for a cache key")
    digest = canonical_hash(image_cache_params(req))
    key = (
        f"{prefix}images/{processing.RENDER_VERSION}/{req.collection.value}/"
        f"{req.observation_id}/{digest}.png"
    )
    _check_key(key)
    _check_key(sidecar_key(key))
    return key


def sia_key(args: dict, prefix: str) -> str:
    """`{prefix}sia/{collection}/{hash}.json` over normalized SIA args (REQ-514)."""
    _check_prefix(prefix)
    key = f"{prefix}sia/{args['collection']}/{canonical_hash(args)}.json"
    return _check_key(key)
