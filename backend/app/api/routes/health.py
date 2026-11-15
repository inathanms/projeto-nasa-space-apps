from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import SettingsDep, StoreDep

router = APIRouter(tags=["health"])


class CacheHealth(BaseModel):
    enabled: bool = Field(description="CACHE_ENABLED.", examples=[True])
    circuit_open: bool = Field(
        description=(
            "True while the storage circuit breaker is open (storage skipped after repeated "
            "failures)."
        ),
        examples=[False],
    )


class HealthResponse(BaseModel):
    status: str = Field(description="Service status.", examples=["ok"])
    version: str = Field(description="API version.", examples=["0.1.0"])
    cache: CacheHealth = Field(description="Image/SIA cache state (no storage call is made).")


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description=(
        "Liveness probe. Does not call any external service (neither IRSA nor the storage)."
    ),
)
def health(settings: SettingsDep, store: StoreDep) -> HealthResponse:
    breaker = getattr(store, "breaker", None)
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        cache=CacheHealth(
            enabled=settings.cache_enabled,
            circuit_open=bool(breaker is not None and breaker.is_open),
        ),
    )
