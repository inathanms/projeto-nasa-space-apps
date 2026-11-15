import logging
from typing import Any

import anyio.to_thread
import boto3
from botocore.client import BaseClient
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings
from app.storage.protocols import StorageUnavailableError

logger = logging.getLogger(__name__)

_NOT_FOUND = {"NoSuchKey", "404", "NotFound"}
_THROTTLED = {"429", "SlowDown", "TooManyRequests"}


def build_s3_client(settings: Settings) -> BaseClient:
    config = Config(
        signature_version="s3v4",
        s3={"addressing_style": settings.s3_addressing_style},
        retries={"max_attempts": settings.s3_max_attempts, "mode": "standard"},
        connect_timeout=settings.s3_connect_timeout_seconds,
        read_timeout=settings.s3_read_timeout_seconds,
        max_pool_connections=settings.s3_max_pool_connections,
        request_checksum_calculation=settings.s3_checksum_mode,
        response_checksum_validation=settings.s3_checksum_mode,
    )
    secret = settings.s3_secret_access_key
    # CON-502: `aws_access_key_id`/`aws_secret_access_key` are boto3's generic keyword names for
    # S3 credentials (spec cache 4.7), used with any S3-compatible endpoint; they are not
    # provider-specific logic. This is the only place in app/ allowed to spell them
    # (tests/unit/test_provider_agnostic.py).
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=secret.get_secret_value() if secret is not None else None,
        config=config,
    )


def _code(exc: ClientError) -> str:
    return str(exc.response.get("Error", {}).get("Code", ""))


def _status(exc: ClientError) -> str:
    return str(exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode", ""))


def _is_not_found(exc: ClientError) -> bool:
    return _code(exc) in _NOT_FOUND or _status(exc) == "404"


def _is_throttled(exc: ClientError) -> bool:
    return _code(exc) in _THROTTLED or _status(exc) == "429"


class S3ObjectStore:
    def __init__(self, client: Any, bucket: str, public_base_url: str) -> None:
        self._client = client
        self._bucket = bucket
        self._public_base_url = public_base_url.rstrip("/")

    async def get_bytes(self, key: str) -> bytes | None:
        def _get() -> bytes:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
            return response["Body"].read()

        try:
            return await anyio.to_thread.run_sync(_get)
        except ClientError as exc:
            if _is_not_found(exc):
                return None
            raise StorageUnavailableError(f"get failed: {_code(exc) or _status(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError(f"get failed: {type(exc).__name__}") from exc

    async def put_bytes(self, key: str, data: bytes, content_type: str, cache_control: str) -> None:
        def _put() -> None:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl=cache_control,
            )

        try:
            await anyio.to_thread.run_sync(_put)
        except ClientError as exc:
            if _is_throttled(exc) and await self._confirm_exists(key):
                logger.info(
                    "put throttled but object exists",
                    extra={"event": "storage_put_throttled_exists", "key": key},
                )
                return
            raise StorageUnavailableError(f"put failed: {_code(exc) or _status(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError(f"put failed: {type(exc).__name__}") from exc

    async def exists(self, key: str) -> bool:
        try:
            return await self._head(key)
        except ClientError as exc:
            raise StorageUnavailableError(f"head failed: {_code(exc) or _status(exc)}") from exc
        except BotoCoreError as exc:
            raise StorageUnavailableError(f"head failed: {type(exc).__name__}") from exc

    async def _confirm_exists(self, key: str) -> bool:
        try:
            return await self._head(key)
        except (ClientError, BotoCoreError):
            return False

    async def _head(self, key: str) -> bool:
        def _do() -> bool:
            try:
                self._client.head_object(Bucket=self._bucket, Key=key)
            except ClientError as exc:
                if _is_not_found(exc):
                    return False
                raise
            return True

        return await anyio.to_thread.run_sync(_do)

    def public_url(self, key: str) -> str:
        return f"{self._public_base_url}/{key}"
