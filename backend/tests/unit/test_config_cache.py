import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings
from app.processing import RENDER_VERSION

FULL = {
    "cache_enabled": True,
    "s3_endpoint_url": "https://acct.example-storage.test",
    "s3_bucket": "bucket",
    "s3_access_key_id": "AKID-VISIBLE-ID",
    "s3_secret_access_key": "super-secret-value",
    "s3_public_base_url": "https://pub.example.test",
    "api_public_base_url": "https://api.example.test",
}


def make(**overrides) -> Settings:
    data = {**FULL, **overrides}
    data = {k: v for k, v in data.items() if v is not None}
    return Settings(_env_file=None, **data)


def test_render_version():
    assert RENDER_VERSION == "r1"


def test_defaults_cache_disabled_needs_nothing():
    s = Settings(_env_file=None)
    assert s.cache_enabled is False
    assert s.s3_region == "auto"
    assert s.s3_addressing_style == "path"
    assert s.s3_checksum_mode == "when_required"
    assert s.s3_connect_timeout_seconds == 5
    assert s.s3_read_timeout_seconds == 20
    assert s.s3_max_attempts == 3
    assert s.s3_max_pool_connections == 20
    assert s.s3_key_prefix == ""
    assert s.position_quantum_arcsec == 6.15
    assert s.sia_cache_ttl_seconds == 21600
    assert s.image_meta_l1_ttl_seconds == 3600
    assert s.memory_cache_max_items == 512
    assert s.storage_circuit_open_seconds == 60
    assert s.s3_secret_access_key is None


def test_full_config_ok():
    s = make(s3_key_prefix="dev/")
    assert isinstance(s.s3_secret_access_key, SecretStr)
    assert s.s3_secret_access_key.get_secret_value() == "super-secret-value"


def test_missing_bucket_lists_name_without_values():
    with pytest.raises(ValidationError) as exc:
        make(s3_bucket=None)
    msg = str(exc.value)
    assert "S3_BUCKET" in msg
    assert "super-secret-value" not in msg
    assert "AKID-VISIBLE-ID" not in msg
    assert "S3_ENDPOINT_URL" not in msg


def test_missing_all_lists_all_names():
    with pytest.raises(ValidationError) as exc:
        Settings(_env_file=None, cache_enabled=True)
    msg = str(exc.value)
    for name in (
        "S3_ENDPOINT_URL",
        "S3_BUCKET",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
        "S3_PUBLIC_BASE_URL",
        "API_PUBLIC_BASE_URL",
    ):
        assert name in msg


def test_prefix_without_slash_fails():
    with pytest.raises(ValidationError, match="S3_KEY_PREFIX"):
        make(s3_key_prefix="dev")


@pytest.mark.parametrize(
    "url",
    ["https://pub.example.test/", "http://pub.example.test", "https://pub.example.test?q=1"],
)
def test_public_base_url_invalid(url):
    with pytest.raises(ValidationError, match="S3_PUBLIC_BASE_URL"):
        make(s3_public_base_url=url)


def test_cache_disabled_ignores_everything():
    s = Settings(_env_file=None, cache_enabled=False, s3_public_base_url="http://x/")
    assert s.cache_enabled is False


def test_repr_does_not_leak_secret():
    s = make()
    assert "super-secret-value" not in repr(s)
    assert "super-secret-value" not in str(s)
