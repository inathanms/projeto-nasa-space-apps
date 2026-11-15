"""Image cache orchestration (PAT-502): normalize -> key -> lookup -> single-flight -> render
-> store. Storage problems never fail a request: they degrade to BYPASS (REQ-552).
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal
from urllib.parse import urlencode

from pydantic import ValidationError

from app.cache.keys import image_cache_params, image_key, sidecar_key
from app.cache.lru import TTLCacheL1
from app.cache.normalize import normalize_request
from app.cache.sidecar import Sidecar
from app.cache.singleflight import SingleFlight
from app.config import Settings
from app.services.image_service import ImageRequest, ImageService
from app.storage.protocols import ObjectStore, StorageUnavailableError

logger = logging.getLogger(__name__)

IMMUTABLE_CACHE_CONTROL = "public, max-age=31536000, immutable"
PNG_CONTENT_TYPE = "image/png"
SIDECAR_CONTENT_TYPE = "application/json"

CacheLayer = Literal["l1", "l2", "none"]


class CacheStatus(StrEnum):
    """Lowercase for the JSON body (`cache_status`); `.header` for `X-Cache`."""

    HIT = "hit"
    MISS = "miss"
    BYPASS = "bypass"

    @property
    def header(self) -> str:
        return self.value.upper()


class CachedPngMissingError(LookupError):
    """The sidecar exists but its PNG does not (deleted or partial state)."""


@dataclass
class CacheOutcome:
    """Result of `lookup_or_render`.

    `url`: public URL on HIT/MISS, API URL (`bypass_url`) on BYPASS. `png` is set on every
    render and on hits with `need_png=True`. `persist` is set only on a miss with
    `persist_before_return=False`: the upload already runs detached from the request, and
    awaiting `persist()` (e.g. from FastAPI `BackgroundTasks`) waits for it; it never raises.
    """

    status: CacheStatus
    layer: CacheLayer
    sidecar: Sidecar | None
    png: bytes | None
    url: str
    persist: Callable[[], Awaitable[None]] | None = None


@dataclass(frozen=True)
class _Rendered:
    png: bytes
    sidecar: Sidecar
    stored: "asyncio.Task[float | None] | None"  # upload ms, or None when the upload failed


class _StorageFailure(Exception):
    pass


class ImageCacheService:
    def __init__(
        self,
        render: ImageService,
        store: ObjectStore | None,
        l1: TTLCacheL1,
        singleflight: SingleFlight,
        settings: Settings,
        background: set[asyncio.Task] | None = None,
    ) -> None:
        """`background`: set holding detached uploads; pass a process-wide set when the service
        is built per request, so `drain_background` at shutdown sees every upload."""
        self._renderer = render
        self._store = store if settings.cache_enabled else None
        self._l1 = l1
        self._singleflight = singleflight
        self._settings = settings
        self._background: set[asyncio.Task] = set() if background is None else background

    # --- public API -----------------------------------------------------------------------

    async def lookup_or_render(
        self, req: ImageRequest, *, need_png: bool, persist_before_return: bool
    ) -> CacheOutcome:
        req = normalize_request(req, self._settings.position_quantum_arcsec)
        png_key = image_key(req, self._settings.s3_key_prefix)
        if self._store is None:
            return await self._render_uncached(req, png_key)

        started = time.perf_counter()
        storage_ok = True
        try:
            hit = await self._lookup(png_key, need_png=need_png)
        except _StorageFailure:
            hit, storage_ok = None, False
        lookup_ms = _ms(started)
        if hit is not None:
            sidecar, png, layer = hit
            self._log(CacheStatus.HIT, layer, png_key, lookup_ms)
            return CacheOutcome(
                CacheStatus.HIT, layer, sidecar, png, self._store.public_url(png_key)
            )

        rendered = await self._render_shared(req, png_key)
        if not persist_before_return:

            async def persist() -> None:
                await self._wait_stored(rendered)

            status = CacheStatus.MISS if storage_ok else CacheStatus.BYPASS
            self._log(status, "none", png_key, lookup_ms)
            return CacheOutcome(
                status,
                "none",
                rendered.sidecar,
                rendered.png,
                rendered.sidecar.public_url if storage_ok else self.bypass_url(req),
                persist=persist,
            )

        # The public URL exists only if both objects were written (REQ-525); otherwise BYPASS.
        upload_ms = await self._wait_stored(rendered)
        stored = upload_ms is not None
        status = CacheStatus.MISS if stored else CacheStatus.BYPASS
        self._log(status, "none", png_key, lookup_ms, upload_ms)
        url = rendered.sidecar.public_url if stored else self.bypass_url(req)
        return CacheOutcome(status, "none", rendered.sidecar, rendered.png, url)

    async def render_and_store(self, req: ImageRequest) -> Sidecar:
        """Render and write PNG then sidecar (REQ-522); raises if the cache cannot store it.

        Public for the future pre-render job: it does not look the key up first.
        """
        if self._store is None:
            raise StorageUnavailableError("image cache is disabled")
        req = normalize_request(req, self._settings.position_quantum_arcsec)
        rendered = await self._render_shared(req, image_key(req, self._settings.s3_key_prefix))
        if await self._wait_stored(rendered) is None:
            raise StorageUnavailableError("could not store the rendered image")
        return rendered.sidecar

    async def fetch_png(self, sidecar: Sidecar) -> bytes:
        """GetObject of the PNG of a cached sidecar (REQ-527); checks size and SHA-256."""
        if self._store is None:
            raise StorageUnavailableError("image cache is disabled")
        data = await self._store.get_bytes(sidecar.key)
        if data is None:
            raise CachedPngMissingError(sidecar.key)
        if len(data) != sidecar.image.bytes or _sha256(data) != sidecar.image.sha256:
            raise CachedPngMissingError(f"{sidecar.key}: content does not match the sidecar")
        return data

    def bypass_url(self, req: ImageRequest) -> str:
        """`{API_PUBLIC_BASE_URL}/image?{normalized params}&response_format=png` (REQ-553).

        Relative (`/image?...`) when API_PUBLIC_BASE_URL is not configured.
        """
        req = normalize_request(req, self._settings.position_quantum_arcsec)
        query = []
        for name, value in image_cache_params(req).items():
            if name == "render_version":
                continue
            if isinstance(value, bool):
                value = "true" if value else "false"
            elif isinstance(value, list):
                value = ",".join(str(v) for v in value)
            query.append((name, str(value)))
        query.append(("response_format", "png"))
        base = (self._settings.api_public_base_url or "").rstrip("/")
        return f"{base}/image?{urlencode(query, safe=',')}"

    async def drain(self) -> None:
        """Wait for detached uploads (tests and shutdown)."""
        await drain_background(self._background)

    # --- internals ------------------------------------------------------------------------

    async def _render_uncached(self, req: ImageRequest, png_key: str) -> CacheOutcome:
        """CACHE_ENABLED=false: v0.1 behavior, no storage calls (REQ-551)."""
        result = await self._renderer.render(req)
        sidecar = Sidecar.from_result(req, result, key=png_key, public_url=None)
        self._log(CacheStatus.BYPASS, "none", png_key, None)
        return CacheOutcome(CacheStatus.BYPASS, "none", sidecar, result.png, self.bypass_url(req))

    async def _lookup(
        self, png_key: str, *, need_png: bool
    ) -> tuple[Sidecar, bytes | None, CacheLayer] | None:
        """Sidecar from L1 then L2; with `need_png`, also the PNG. None = miss."""
        assert self._store is not None
        sc_key = sidecar_key(png_key)
        layer: CacheLayer = "l1"
        sidecar = self._l1.get(sc_key)
        if not isinstance(sidecar, Sidecar):
            layer = "l2"
            raw = await self._storage_call("get", png_key, self._store.get_bytes(sc_key))
            if raw is None:
                return None
            sidecar = self._parse_sidecar(raw, png_key)
            if sidecar is None:
                return None
            self._l1.set(sc_key, sidecar, ttl=self._settings.image_meta_l1_ttl_seconds)
        if not need_png:
            return sidecar, None, layer
        try:
            png = await self._storage_call("get", png_key, self.fetch_png(sidecar))
        except CachedPngMissingError:
            logger.warning(
                "cached png missing or corrupted",
                extra={"event": "cached_png_missing", "key": png_key},
            )
            return None
        return sidecar, png, layer

    def _parse_sidecar(self, raw: bytes, png_key: str) -> Sidecar | None:
        try:
            sidecar = Sidecar.model_validate_json(raw)
        except ValidationError as exc:
            reason = "; ".join(sorted({str(e["type"]) for e in exc.errors()}))
            logger.warning(
                "invalid sidecar treated as miss",
                extra={"event": "sidecar_invalid", "key": png_key, "reason": reason},
            )
            return None
        if sidecar.key != png_key:
            logger.warning(
                "invalid sidecar treated as miss",
                extra={"event": "sidecar_invalid", "key": png_key, "reason": "key_mismatch"},
            )
            return None
        return sidecar

    async def _render_shared(self, req: ImageRequest, png_key: str) -> _Rendered:
        """Single-flight around `ImageService.render` (REQ-531/532).

        Waiters await the shared task, so only the leader enters the render semaphore. The
        upload is started inside the shared task, detached from any client, so a cancelled
        request still gets its result stored (spec 9.3). Errors reach every waiter; nothing
        is written because the upload only starts after a successful render (REQ-526).
        """
        return await self._singleflight.do(png_key, lambda: self._render_job(req, png_key))

    async def _render_job(self, req: ImageRequest, png_key: str) -> _Rendered:
        result = await self._renderer.render(req)
        public_url = self._store.public_url(png_key) if self._store is not None else None
        sidecar = Sidecar.from_result(req, result, key=png_key, public_url=public_url)
        stored = self._spawn(self._store_objects(result.png, sidecar))
        return _Rendered(result.png, sidecar, stored)

    async def _store_objects(self, png: bytes, sidecar: Sidecar) -> float | None:
        """PUT the PNG, then the sidecar (REQ-522/523). Returns upload ms, None on failure."""
        assert self._store is not None
        started = time.perf_counter()
        sc_key = sidecar_key(sidecar.key)
        try:
            await self._storage_call(
                "put",
                sidecar.key,
                self._store.put_bytes(sidecar.key, png, PNG_CONTENT_TYPE, IMMUTABLE_CACHE_CONTROL),
            )
            await self._storage_call(
                "put",
                sidecar.key,
                self._store.put_bytes(
                    sc_key,
                    sidecar.model_dump_json().encode(),
                    SIDECAR_CONTENT_TYPE,
                    IMMUTABLE_CACHE_CONTROL,
                ),
            )
        except _StorageFailure:
            return None
        self._l1.set(sc_key, sidecar, ttl=self._settings.image_meta_l1_ttl_seconds)
        upload_ms = _ms(started)
        logger.info(
            "image stored",
            extra={"event": "image_cache_stored", "key": sidecar.key, "upload_ms": upload_ms},
        )
        return upload_ms

    async def _wait_stored(self, rendered: _Rendered) -> float | None:
        if rendered.stored is None:
            return None
        return await asyncio.shield(rendered.stored)

    async def _storage_call[T](self, op: str, key: str, call: Awaitable[T]) -> T:
        """Run a store call; any storage exception becomes `_StorageFailure` (logged)."""
        try:
            return await call
        except CachedPngMissingError:
            raise
        except Exception as exc:  # any storage error degrades to BYPASS
            logger.error(
                "storage unavailable",
                extra={
                    "event": "storage_unavailable",
                    "op": op,
                    "key": key,
                    "error": type(exc).__name__,
                },
            )
            raise _StorageFailure from exc

    def _spawn(self, coro: Awaitable[float | None]) -> "asyncio.Task[float | None]":
        task = asyncio.ensure_future(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return task

    def _log(
        self,
        status: CacheStatus,
        layer: CacheLayer,
        key: str,
        lookup_ms: float | None,
        upload_ms: float | None = None,
    ) -> None:
        logger.info(
            "image cache",
            extra={
                "event": "image_cache",
                "cache_status": status.value,
                "cache_layer": layer,
                "key": key,
                "lookup_ms": lookup_ms,
                "upload_ms": upload_ms,
            },
        )


async def drain_background(tasks: set[asyncio.Task]) -> None:
    """Wait until every task in `tasks` (detached uploads) has finished."""
    while pending := [t for t in tasks if not t.done()]:
        await asyncio.gather(*pending, return_exceptions=True)


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
