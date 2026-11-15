import anyio


class InMemoryObjectStore:
    """Test double implementing ObjectStore."""

    def __init__(self, delay: float = 0, fail: Exception | None = None) -> None:
        self.delay = delay
        self.fail = fail
        self.objects: dict[str, bytes] = {}
        self.put_log: list[tuple[str, str, str]] = []
        self.calls: list[str] = []

    async def _enter(self, op: str) -> None:
        self.calls.append(op)
        if self.delay:
            await anyio.sleep(self.delay)
        if self.fail is not None:
            raise self.fail

    async def get_bytes(self, key: str) -> bytes | None:
        await self._enter("get")
        return self.objects.get(key)

    async def put_bytes(self, key: str, data: bytes, content_type: str, cache_control: str) -> None:
        await self._enter("put")
        self.objects[key] = data
        self.put_log.append((key, content_type, cache_control))

    async def exists(self, key: str) -> bool:
        await self._enter("exists")
        return key in self.objects

    def public_url(self, key: str) -> str:
        return f"https://cache.test/{key}"
