import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.errors import register_exception_handlers
from app.api.routes import epochs, health, image
from app.config import Settings, get_settings
from app.logging import setup_logging

CREDIT = "Data: NASA/JPL-Caltech/IPAC — SPHEREx, via NASA/IPAC Infrared Science Archive (IRSA)"

DESCRIPTION = f"""
Public API of the **SPHEREye**: find when NASA's SPHEREx telescope observed a
position of the sky (`/epochs`) and get a display-ready PNG of that region (`/image`).

Coordinates are ICRS degrees, times ISO 8601 UTC (and MJD), wavelengths µm, brightness MJy/sr.

{CREDIT}
"""


def _add_parameter_examples(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy each parameter's schema example to the parameter itself (shown by Swagger UI)."""
    for path in schema.get("paths", {}).values():
        for operation in path.values():
            for param in operation.get("parameters", []):
                examples = param.get("schema", {}).get("examples")
                if "example" not in param and examples:
                    param["example"] = examples[0]
    return schema


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(headers={"User-Agent": settings.http_user_agent}) as http:
            app.state.http = http
            app.state.render_semaphore = asyncio.Semaphore(settings.max_concurrent_renders)
            yield

    app = FastAPI(
        title="SPHEREye API",
        version=settings.app_version,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_methods=["GET", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=image.EXPOSED_HEADERS,
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(epochs.router)
    app.include_router(image.router)

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            app.openapi_schema = _add_parameter_examples(
                get_openapi(
                    title=app.title,
                    version=app.version,
                    description=app.description,
                    routes=app.routes,
                )
            )
        return app.openapi_schema

    app.openapi = openapi
    return app


app = create_app()
