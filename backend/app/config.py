from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

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

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @property
    def flags_reject_list(self) -> list[str]:
        return [n.strip() for n in self.flags_reject_names.split(",") if n.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
