from typing import Protocol


class StorageUnavailableError(Exception):
    """The object storage could not serve the request (network, 5xx, credentials)."""


class ObjectStore(Protocol):
    async def get_bytes(self, key: str) -> bytes | None: ...

    async def put_bytes(
        self, key: str, data: bytes, content_type: str, cache_control: str
    ) -> None: ...

    async def exists(self, key: str) -> bool: ...

    def public_url(self, key: str) -> str: ...
