import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from moto import mock_aws

from app.config import Settings
from app.storage.protocols import StorageUnavailableError
from app.storage.s3_store import S3ObjectStore, build_s3_client

BUCKET = "test-bucket"
CC = "public, max-age=31536000, immutable"


def _settings(**kw) -> Settings:
    return Settings(
        s3_endpoint_url=None,
        s3_region="us-east-1",
        s3_bucket=BUCKET,
        s3_access_key_id="id",
        s3_secret_access_key="secret",
        s3_public_base_url="https://cdn.example.com",
        **kw,
    )


def _err(code: str, status: int, op: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}, op
    )


class StubClient:
    def __init__(self, put_exc=None, head_exc=None, get_exc=None):
        self.put_kwargs: list[dict] = []
        self.put_exc, self.head_exc, self.get_exc = put_exc, head_exc, get_exc

    def put_object(self, **kwargs):
        self.put_kwargs.append(kwargs)
        if self.put_exc:
            raise self.put_exc

    def head_object(self, **kwargs):
        if self.head_exc:
            raise self.head_exc
        return {}

    def get_object(self, **kwargs):
        if self.get_exc:
            raise self.get_exc
        raise AssertionError


async def test_put_object_only_uses_allowed_kwargs():
    stub = StubClient()
    store = S3ObjectStore(stub, BUCKET, "https://cdn.example.com")
    await store.put_bytes("k/a.png", b"data", "image/png", CC)
    assert len(stub.put_kwargs) == 1
    assert stub.put_kwargs[0] == {
        "Bucket": BUCKET,
        "Key": "k/a.png",
        "Body": b"data",
        "ContentType": "image/png",
        "CacheControl": CC,
    }


def test_client_config_matches_settings():
    s = _settings(s3_checksum_mode="when_supported")
    cfg = build_s3_client(s).meta.config
    assert cfg.request_checksum_calculation == s.s3_checksum_mode
    assert cfg.response_checksum_validation == s.s3_checksum_mode
    assert cfg.signature_version == "s3v4"
    assert cfg.s3["addressing_style"] == "path"
    assert cfg.retries["mode"] == "standard"
    assert cfg.retries["total_max_attempts"] == 4  # botocore: max_attempts (retries) + 1
    assert cfg.max_pool_connections == 20
    assert cfg.connect_timeout == 5
    assert cfg.read_timeout == 20


def test_client_default_checksum_mode_when_required():
    s = _settings()
    cfg = build_s3_client(s).meta.config
    assert cfg.request_checksum_calculation == "when_required"


async def test_roundtrip_with_moto():
    with mock_aws():
        client = build_s3_client(_settings())
        client.create_bucket(Bucket=BUCKET)
        store = S3ObjectStore(client, BUCKET, "https://cdn.example.com/")
        assert await store.get_bytes("x") is None
        assert not await store.exists("x")
        await store.put_bytes("x", b"hello", "image/png", CC)
        assert await store.get_bytes("x") == b"hello"
        assert await store.exists("x")
        head = client.head_object(Bucket=BUCKET, Key="x")
        assert head["ContentType"] == "image/png"
        assert head["CacheControl"] == CC
        assert store.public_url("x") == "https://cdn.example.com/x"


async def test_get_404_returns_none():
    store = S3ObjectStore(StubClient(get_exc=_err("404", 404, "GetObject")), BUCKET, "https://c")
    assert await store.get_bytes("k") is None


async def test_get_other_error_is_unavailable():
    store = S3ObjectStore(
        StubClient(get_exc=_err("InternalError", 500, "GetObject")), BUCKET, "https://c"
    )
    with pytest.raises(StorageUnavailableError):
        await store.get_bytes("k")


async def test_network_error_is_unavailable():
    exc = EndpointConnectionError(endpoint_url="https://x")
    store = S3ObjectStore(StubClient(get_exc=exc, put_exc=exc, head_exc=exc), BUCKET, "https://c")
    with pytest.raises(StorageUnavailableError):
        await store.get_bytes("k")
    with pytest.raises(StorageUnavailableError):
        await store.put_bytes("k", b"", "t", "c")
    with pytest.raises(StorageUnavailableError):
        await store.exists("k")


async def test_put_429_with_existing_object_is_success(caplog):
    caplog.set_level("INFO")
    store = S3ObjectStore(
        StubClient(put_exc=_err("SlowDown", 429, "PutObject")), BUCKET, "https://c"
    )
    await store.put_bytes("k", b"v", "t", "c")
    assert any(r.levelname == "INFO" for r in caplog.records)


async def test_put_429_without_object_is_error():
    stub = StubClient(
        put_exc=_err("SlowDown", 429, "PutObject"), head_exc=_err("404", 404, "HeadObject")
    )
    store = S3ObjectStore(stub, BUCKET, "https://c")
    with pytest.raises(StorageUnavailableError):
        await store.put_bytes("k", b"v", "t", "c")


async def test_put_other_error_is_unavailable_and_exists_error():
    stub = StubClient(
        put_exc=_err("AccessDenied", 403, "PutObject"),
        head_exc=_err("AccessDenied", 403, "HeadObject"),
    )
    store = S3ObjectStore(stub, BUCKET, "https://c")
    with pytest.raises(StorageUnavailableError):
        await store.put_bytes("k", b"v", "t", "c")
    with pytest.raises(StorageUnavailableError):
        await store.exists("k")
