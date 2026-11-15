import logging
import time
from collections.abc import Callable

from app.storage.protocols import ObjectStore, StorageUnavailableError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    def __init__(
        self,
        threshold: int = 3,
        open_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = threshold
        self.open_seconds = open_seconds
        self._clock = clock
        self._failures = 0
        self._opened_at: float | None = None

    @property
    def is_open(self) -> bool:
        if self._opened_at is None:
            return False
        if self._clock() - self._opened_at >= self.open_seconds:
            # half-open: let the next call through; one more failure re-opens.
            self._opened_at = None
            self._failures = self.threshold - 1
            return False
        return True

    def allow(self) -> bool:
        return not self.is_open

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self.threshold:
            self._opened_at = self._clock()


class GuardedStore:
    def __init__(self, store: ObjectStore, breaker: CircuitBreaker) -> None:
        self._store = store
        self.breaker = breaker

    def _check(self) -> None:
        if not self.breaker.allow():
            raise StorageUnavailableError("storage circuit breaker is open")

    def _failed(self, op: str, exc: StorageUnavailableError) -> None:
        self.breaker.record_failure()
        logger.error(
            "storage unavailable",
            extra={"event": "storage_unavailable", "op": op, "circuit_open": self.breaker.is_open},
        )

    async def get_bytes(self, key: str) -> bytes | None:
        self._check()
        try:
            result = await self._store.get_bytes(key)
        except StorageUnavailableError as exc:
            self._failed("get", exc)
            raise
        self.breaker.record_success()
        return result

    async def put_bytes(self, key: str, data: bytes, content_type: str, cache_control: str) -> None:
        self._check()
        try:
            await self._store.put_bytes(key, data, content_type, cache_control)
        except StorageUnavailableError as exc:
            self._failed("put", exc)
            raise
        self.breaker.record_success()

    async def exists(self, key: str) -> bool:
        self._check()
        try:
            result = await self._store.exists(key)
        except StorageUnavailableError as exc:
            self._failed("exists", exc)
            raise
        self.breaker.record_success()
        return result

    def public_url(self, key: str) -> str:
        return self._store.public_url(key)
