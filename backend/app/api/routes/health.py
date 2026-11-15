from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import SettingsDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = Field(description="Service status.", examples=["ok"])
    version: str = Field(description="API version.", examples=["0.1.0"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Liveness probe. Does not call any external service.",
)
def health(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(status="ok", version=settings.app_version)
