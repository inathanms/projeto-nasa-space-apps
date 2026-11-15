import asyncio
from typing import Annotated

import httpx
from fastapi import Depends, Request

from app.clients.irsa_cutout import IrsaCutoutClient
from app.clients.irsa_sia import IrsaSiaClient
from app.clients.protocols import CutoutClient, SiaClient
from app.config import Settings
from app.services.epochs_service import EpochsService
from app.services.image_service import ImageService


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http


def get_render_semaphore(request: Request) -> asyncio.Semaphore:
    return request.app.state.render_semaphore


SettingsDep = Annotated[Settings, Depends(get_settings)]
HttpDep = Annotated[httpx.AsyncClient, Depends(get_http_client)]


def get_sia_client(http: HttpDep, settings: SettingsDep) -> SiaClient:
    return IrsaSiaClient(http, settings)


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
