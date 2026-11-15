from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    port: int = 8000
    log_level: str = "info"
    cors_allowed_origins: str = "http://localhost:3000"
    app_version: str = "0.1.0"

    irsa_sia_url: str = "https://irsa.ipac.caltech.edu/SIA"
    irsa_allowed_host: str = "irsa.ipac.caltech.edu"
    irsa_default_collection: str = "spherex_qr3"
    irsa_sia_maxrec: int = 5000
    irsa_sia_timeout_seconds: float = 30
    irsa_cutout_timeout_seconds: float = 60
    irsa_max_retries: int = 1
    irsa_max_cutout_bytes: int = 104_857_600
    http_user_agent: str = "sphereye/0.1 (+hackathon)"

    max_concurrent_renders: int = 4
    render_queue_timeout_seconds: float = 30
    visit_gap_days: float = 2.0
    max_output_edge_px: int = 4096
    cutout_fetch_concurrency: int = 3
    stack_max_exposures: int = 8
    max_cutouts_per_request: int = 12
    max_fetch_pixels_per_request: int = 16_646_400
    flags_reject_names: str = "NONFUNC,MISSING_DATA,HOT,COLD,OVERFLOW,SUR_ERROR,PHANMISS"

    cache_enabled: bool = False
    s3_endpoint_url: str | None = None
    s3_region: str = "auto"
    s3_bucket: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: SecretStr | None = None
    s3_addressing_style: Literal["path", "virtual"] = "path"
    s3_checksum_mode: Literal["when_required", "when_supported"] = "when_required"
    s3_connect_timeout_seconds: float = 5
    s3_read_timeout_seconds: float = 20
    s3_max_attempts: int = 3
    s3_max_pool_connections: int = 20
    s3_public_base_url: str | None = None
    s3_key_prefix: str = ""
    api_public_base_url: str | None = None
    position_quantum_arcsec: float = 6.15
    sia_cache_ttl_seconds: int = 21600
    image_meta_l1_ttl_seconds: int = 3600
    memory_cache_max_items: int = 512
    storage_circuit_open_seconds: float = 60

    @model_validator(mode="after")
    def _validate_cache(self) -> "Settings":
        if not self.cache_enabled:
            return self
        required = {
            "S3_ENDPOINT_URL": self.s3_endpoint_url,
            "S3_BUCKET": self.s3_bucket,
            "S3_ACCESS_KEY_ID": self.s3_access_key_id,
            "S3_SECRET_ACCESS_KEY": self.s3_secret_access_key,
            "S3_PUBLIC_BASE_URL": self.s3_public_base_url,
            "API_PUBLIC_BASE_URL": self.api_public_base_url,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError("CACHE_ENABLED=true requires: " + ", ".join(missing))
        if self.s3_key_prefix and not self.s3_key_prefix.endswith("/"):
            raise ValueError("S3_KEY_PREFIX must end with '/' when not empty")
        parts = urlsplit(self.s3_public_base_url or "")
        if (
            parts.scheme != "https"
            or not parts.netloc
            or parts.query
            or parts.fragment
            or (self.s3_public_base_url or "").endswith("/")
        ):
            raise ValueError(
                "S3_PUBLIC_BASE_URL must be https, without query string and without trailing '/'"
            )
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def flags_reject_list(self) -> list[str]:
        return [n.strip() for n in self.flags_reject_names.split(",") if n.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
