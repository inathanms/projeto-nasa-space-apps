import pytest

from app.storage.memory_store import InMemoryObjectStore
from app.storage.protocols import StorageUnavailableError


async def test_roundtrip_and_put_log():
    store = InMemoryObjectStore()
    assert await store.get_bytes("a") is None
    assert not await store.exists("a")
    await store.put_bytes("a", b"x", "image/png", "no-store")
    assert await store.get_bytes("a") == b"x"
    assert await store.exists("a")
    assert store.put_log == [("a", "image/png", "no-store")]
    assert store.public_url("a").endswith("/a")


async def test_fail_raises_on_every_operation():
    store = InMemoryObjectStore(fail=StorageUnavailableError("boom"))
    with pytest.raises(StorageUnavailableError):
        await store.get_bytes("a")
    with pytest.raises(StorageUnavailableError):
        await store.put_bytes("a", b"x", "t", "c")
    with pytest.raises(StorageUnavailableError):
        await store.exists("a")
    assert store.objects == {}


async def test_delay_is_applied():
    store = InMemoryObjectStore(delay=0.05)
    loop_time = __import__("time").monotonic()
    await store.put_bytes("a", b"x", "t", "c")
    assert __import__("time").monotonic() - loop_time >= 0.04
