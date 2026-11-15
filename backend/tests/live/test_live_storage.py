"""Live check of the S3-compatible object storage (spec section 6, "Live (opcional)").

Writes one object under a unique prefix, reads it back, checks its public URL and removes
what it created. This is the only test allowed to call DeleteObject.

Run with: uv run pytest -m live_storage   (skipped when the S3_* variables are missing)
"""

import uuid

import anyio.to_thread
import httpx
import pytest
from pydantic import SecretStr

from app.config import Settings
from app.storage.s3_store import S3ObjectStore, build_s3_client

pytestmark = pytest.mark.live_storage

REQUIRED = (
    "s3_endpoint_url",
    "s3_bucket",
    "s3_access_key_id",
    "s3_secret_access_key",
    "s3_public_base_url",
)
CACHE_CONTROL = "public, max-age=31536000, immutable"
PAYLOAD = b"\x89PNG\r\n\x1a\nlive-storage-probe"


def _is_set(value: object) -> bool:
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    return bool(value)


def _settings_or_skip() -> Settings:
    settings = Settings(_env_file=None)
    missing = [name.upper() for name in REQUIRED if not _is_set(getattr(settings, name))]
    if missing:
        pytest.skip("live storage variables missing: " + ", ".join(missing))
    return settings


async def test_live_storage_roundtrip() -> None:
    settings = _settings_or_skip()
    client = build_s3_client(settings)
    bucket = settings.s3_bucket
    assert bucket is not None
    store = S3ObjectStore(client, bucket, settings.s3_public_base_url or "")

    prefix = f"test/{uuid.uuid4()}/"
    key = f"{prefix}probe.png"
    try:
        await store.put_bytes(key, PAYLOAD, "image/png", CACHE_CONTROL)

        assert await store.exists(key) is True
        assert await store.get_bytes(key) == PAYLOAD

        url = store.public_url(key)
        assert url == f"{settings.s3_public_base_url}/{key}"
        async with httpx.AsyncClient(timeout=30) as http:
            response = await http.get(url)
        assert response.status_code == 200, response.text[:200]
        assert response.headers["content-type"].startswith("image/png")
        assert "immutable" in response.headers["cache-control"]
        assert response.content == PAYLOAD
    finally:
        # Cleanup of the test's own object only (the one place DeleteObject is used).
        await anyio.to_thread.run_sync(lambda: client.delete_object(Bucket=bucket, Key=key))
