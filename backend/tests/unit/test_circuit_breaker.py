import pytest

from app.storage.circuit_breaker import CircuitBreaker, GuardedStore
from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError


class Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_opens_on_third_consecutive_failure():
    b = CircuitBreaker(threshold=3, open_seconds=60, clock=Clock())
    b.record_failure()
    b.record_failure()
    assert b.allow() and not b.is_open
    b.record_failure()
    assert b.is_open and not b.allow()


def test_success_resets_counter():
    b = CircuitBreaker(threshold=3, open_seconds=60, clock=Clock())
    b.record_failure()
    b.record_failure()
    b.record_success()
    b.record_failure()
    b.record_failure()
    assert not b.is_open


def test_closes_after_open_seconds_and_reopens_on_one_failure():
    clock = Clock()
    b = CircuitBreaker(threshold=3, open_seconds=60, clock=clock)
    for _ in range(3):
        b.record_failure()
    clock.now = 59
    assert b.is_open
    clock.now = 60
    assert b.allow()
    b.record_failure()
    assert b.is_open


async def test_guarded_store_passes_through_and_counts_failures():
    inner = InMemoryObjectStore()
    guarded = GuardedStore(inner, CircuitBreaker(clock=Clock()))
    await guarded.put_bytes("k", b"v", "t", "c")
    assert await guarded.get_bytes("k") == b"v"
    assert await guarded.exists("k")
    assert guarded.public_url("k") == inner.public_url("k")


async def test_store_not_called_while_open():
    inner = InMemoryObjectStore(fail=StorageUnavailableError("down"))
    guarded = GuardedStore(inner, CircuitBreaker(clock=Clock()))
    for op in (
        guarded.get_bytes("k"),
        guarded.put_bytes("k", b"v", "t", "c"),
        guarded.exists("k"),
    ):
        with pytest.raises(StorageUnavailableError):
            await op
    assert guarded.breaker.is_open
    calls = len(inner.calls)
    for _ in range(2):
        with pytest.raises(StorageUnavailableError):
            await guarded.get_bytes("k")
    assert len(inner.calls) == calls


async def test_non_storage_errors_do_not_trip_breaker():
    inner = InMemoryObjectStore(fail=ValueError("bug"))
    guarded = GuardedStore(inner, CircuitBreaker(clock=Clock()))
    for _ in range(5):
        with pytest.raises(ValueError):
            await guarded.get_bytes("k")
    assert not guarded.breaker.is_open
