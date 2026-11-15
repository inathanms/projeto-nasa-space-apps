import asyncio
from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.cache.lru import TTLCacheL1
from app.cache.singleflight import SingleFlight
from app.clients.cached_sia import CachedSiaClient
from app.clients.irsa_cutout import IrsaCutoutClient
from app.clients.irsa_sia import IrsaSiaClient
from app.clients.protocols import CutoutClient, SiaClient
from app.config import Settings
from app.services.epochs_service import EpochsService
from app.services.image_cache_service import ImageCacheService
from app.services.image_service import ImageService
from app.storage.protocols import ObjectStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_render_semaphore(request: Request) -> asyncio.Semaphore:
    return request.app.state.render_semaphore


def get_object_store(request: Request) -> ObjectStore | None:
    """Process-wide store built in the lifespan; None when CACHE_ENABLED=false (or before the
    lifespan ran, e.g. /health on a client without lifespan)."""
    return getattr(request.app.state, "store", None)


def get_l1(request: Request) -> TTLCacheL1:
    """Process-wide in-memory cache shared by SIA results and image sidecars (REQ-542/547)."""
    return request.app.state.l1


SettingsDep = Annotated[Settings, Depends(get_settings)]
HttpDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]
StoreDep = Annotated[ObjectStore | None, Depends(get_object_store)]
L1Dep = Annotated[TTLCacheL1, Depends(get_l1)]


def get_irsa_sia_client(http: HttpDep, settings: SettingsDep) -> SiaClient:
    """Uncached IRSA SIA client (the upstream wrapped by the cache)."""
    return IrsaSiaClient(http, settings)


def get_sia_client(
    request: Request,
    inner: Annotated[SiaClient, Depends(get_irsa_sia_client)],
    store: StoreDep,
    l1: L1Dep,
    settings: SettingsDep,
) -> SiaClient:
    """SIA client used by /epochs and by /image's resolution: same cache for both (REQ-546)."""
    if not settings.cache_enabled:
        return inner
    return CachedSiaClient(
        inner, store, settings, l1, singleflight=request.app.state.sia_singleflight
    )


def get_cutout_client(http: HttpDep, settings: SettingsDep) -> CutoutClient:
    return IrsaCutoutClient(http, settings)


def get_epochs_service(
    sia: Annotated[SiaClient, Depends(get_sia_client)], settings: SettingsDep
) -> EpochsService:
    return EpochsService(sia, settings)


def get_image_service(
    sia: Annotated[SiaClient, Depends(get_sia_client)],
    cutout: Annotated[CutoutClient, Depends(get_cutout_client)],
    settings: SettingsDep,
    semaphore: Annotated[asyncio.Semaphore, Depends(get_render_semaphore)],
) -> ImageService:
    return ImageService(sia, cutout, settings, semaphore)


def get_image_cache_service(
    request: Request,
    render: Annotated[ImageService, Depends(get_image_service)],
    store: StoreDep,
    l1: L1Dep,
    settings: SettingsDep,
) -> ImageCacheService:
    state = request.app.state
    singleflight: SingleFlight = state.image_singleflight
    return ImageCacheService(
        render, store, l1, singleflight, settings, background=state.image_cache_tasks
    )
