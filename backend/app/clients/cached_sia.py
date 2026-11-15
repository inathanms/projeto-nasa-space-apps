"""SIA client with a two-layer cache: in-process L1 and object-store L2 (REQ-541..546)."""

import json
import logging
from dataclasses import asdict
from datetime import UTC, datetime, timedelta

from app.cache.keys import sia_key
from app.cache.lru import TTLCacheL1
from app.cache.normalize import normalize_sia_args
from app.cache.singleflight import SingleFlight
from app.clients.protocols import SiaClient
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamInvalidResponseError, UpstreamTimeoutError
from app.domain.models import Collection, Detector, ImageRecord, SiaResult
from app.storage.protocols import ObjectStore

logger = logging.getLogger(__name__)

_UPSTREAM_ERRORS = (UpstreamError, UpstreamTimeoutError, UpstreamInvalidResponseError)


def _record_to_dict(record: ImageRecord) -> dict:
    data = asdict(record)
    data["detector"] = record.detector.value
    data["footprint"] = [list(point) for point in record.footprint]
    return data


def _record_from_dict(data: dict) -> ImageRecord:
    data = dict(data)
    data["detector"] = Detector(data["detector"])
    data["footprint"] = [(float(p[0]), float(p[1])) for p in data["footprint"]]
    return ImageRecord(**data)


def serialize_sia_result(result: SiaResult, fetched_at: datetime) -> bytes:
    payload = {
        "fetched_at": fetched_at.isoformat(),
        "records": [_record_to_dict(r) for r in result.records],
        "truncated": result.truncated,
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def deserialize_sia_result(raw: bytes) -> tuple[SiaResult, datetime]:
    """Raises ValueError/KeyError/TypeError on corrupt payloads."""
    payload = json.loads(raw)
    fetched_at = datetime.fromisoformat(payload["fetched_at"])
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    records = [_record_from_dict(r) for r in payload["records"]]
    return SiaResult(records=records, truncated=bool(payload["truncated"])), fetched_at


class CachedSiaClient:
    def __init__(
        self,
        inner: SiaClient,
        store: ObjectStore | None,
        settings: Settings,
        l1: TTLCacheL1,
        singleflight: SingleFlight | None = None,
    ) -> None:
        """Pass a process-wide `singleflight` when the client is built per request."""
        self._inner = inner
        self._store = store
        self._settings = settings
        self._l1 = l1
        self._singleflight = singleflight or SingleFlight()

    async def search(
        self,
        ra: float,
        dec: float,
        radius: float,
        collection: Collection,
        start_mjd: float | None = None,
        end_mjd: float | None = None,
    ) -> SiaResult:
        s = self._settings
        args = normalize_sia_args(
            ra,
            dec,
            radius,
            collection,
            start_mjd,
            end_mjd,
            s.irsa_sia_maxrec,
            s.position_quantum_arcsec,
        )
        key = sia_key(args, s.s3_key_prefix)
        cached = self._l1.get(key)
        if cached is not None:
            return cached
        return await self._singleflight.do(key, lambda: self._load(key, args, collection))

    async def _load(self, key: str, args: dict, collection: Collection) -> SiaResult:
        l1_key = key
        stale: SiaResult | None = None
        l2_unavailable = False
        if self._store is not None:
            try:
                raw = await self._store.get_bytes(key)
            except Exception as exc:  # noqa: BLE001 - any storage error: L2 skipped
                logger.warning(
                    "sia_l2_unavailable",
                    extra={"event": "sia_l2_unavailable", "error": type(exc).__name__},
                )
                raw = None
                l2_unavailable = True
            if raw is not None:
                try:
                    result, fetched_at = deserialize_sia_result(raw)
                except (ValueError, KeyError, TypeError):
                    logger.warning("sia_l2_corrupt", extra={"event": "sia_l2_corrupt", "key": key})
                else:
                    ttl = timedelta(seconds=self._settings.sia_cache_ttl_seconds)
                    age = datetime.now(UTC) - fetched_at
                    if age <= ttl:
                        self._l1_set(l1_key, result, ttl - age)
                        return result
                    stale = result

        try:
            result = await self._inner.search(
                args["ra"],
                args["dec"],
                args["radius"],
                collection,
                args["time_start_mjd"],
                args["time_end_mjd"],
            )
        except _UPSTREAM_ERRORS as exc:
            if stale is not None:
                logger.warning(
                    "serving stale SIA result after upstream error",
                    extra={"event": "sia_stale_served", "key": key, "error": type(exc).__name__},
                )
                return stale
            raise

        self._l1_set(l1_key, result, timedelta(seconds=self._settings.sia_cache_ttl_seconds))
        if self._store is not None and not l2_unavailable:
            try:
                await self._store.put_bytes(
                    key,
                    serialize_sia_result(result, datetime.now(UTC)),
                    "application/json",
                    "no-store",
                )
            except Exception as exc:  # noqa: BLE001 - any storage error: still return it
                logger.warning(
                    "sia_l2_write_failed",
                    extra={"event": "sia_l2_write_failed", "error": type(exc).__name__},
                )
        return result

    def _l1_set(self, key: str, result: SiaResult, ttl: timedelta) -> None:
        self._l1.set(key, result, ttl=max(ttl.total_seconds(), 1.0))
