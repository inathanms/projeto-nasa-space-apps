"""FastAPI entry point for the Planet X explorer."""

import logging
import os
from collections import OrderedDict
from contextlib import contextmanager
from functools import lru_cache
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from .errors import ArchiveUnavailable, InsufficientCoverage, SearchTimeout
from .models import ErrorResponse, Frame, Health, Sequence, Timeline

logger = logging.getLogger("uvicorn.error")
app = FastAPI(
    title="Planet X · SPHEREx",
    description="Explora exposições SPHEREx ao longo do tempo em um campo de 6′ × 6′.",
    version="1.1.0",
)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
    allow_methods=["GET"],
    expose_headers=["X-Cache"],
)

CACHE_SIZE = 32
CACHE_TTL_SECONDS = 24 * 60 * 60
cache: OrderedDict[tuple, tuple[float, Sequence]] = OrderedDict()
cache_lock = Lock()
# One FITS pipeline at a time keeps peak memory bounded on the free service.
processing_slot = BoundedSemaphore(1)


def _get_cached(key: tuple) -> Sequence | None:
    with cache_lock:
        if key not in cache:
            return None
        expiry, sequence = cache[key]
        if monotonic() >= expiry:
            del cache[key]
            return None
        cache.move_to_end(key)
        return sequence


def _save_cached(key: tuple, sequence: Sequence) -> None:
    with cache_lock:
        now = monotonic()
        for expired_key in [item for item, (expiry, _) in cache.items() if expiry <= now]:
            del cache[expired_key]
        cache[key] = (now + CACHE_TTL_SECONDS, sequence)
        cache.move_to_end(key)
        while len(cache) > CACHE_SIZE:
            cache.popitem(last=False)


@app.get("/health")
def health() -> Health:
    return Health()


@app.get(
    "/api/v1/sequence",
    responses={
        404: {"model": ErrorResponse, "description": "Campo sem dois quadros comparáveis."},
        503: {"model": ErrorResponse, "description": "Arquivo ou servidor temporariamente indisponível."},
        504: {"model": ErrorResponse, "description": "O orçamento de busca foi esgotado."},
    },
)
def get_sequence(
    response: Response,
    ra_deg: Annotated[float, Query(ge=0, lt=360, allow_inf_nan=False, description="Ascensão reta ICRS em graus.")],
    dec_deg: Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False, description="Declinação ICRS em graus.")],
) -> Sequence:
    # Import on demand so /health and coordinate validation do not load the science stack.
    from .irsa import COLLECTIONS
    from .processing import PROCESSING_VERSION
    from .sequence import build_sequence

    # Round to a precision well below one SPHEREx pixel. Inputs close to
    # 360° may round to the equivalent 0° rather than leaving the valid range.
    ra_deg = round(ra_deg, 6) % 360
    dec_deg = round(dec_deg, 6) + 0.0
    key = (ra_deg, dec_deg, 6, COLLECTIONS, PROCESSING_VERSION)
    cached = _get_cached(key)
    if cached is not None:
        response.headers["X-Cache"] = "HIT"
        logger.info("Cache HIT para %s", cached.sequence_id)
        return cached

    if not processing_slot.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail={"code": "server_busy", "message": "Outra busca está em andamento. Tente em instantes."},
            headers={"Retry-After": "5"},
        )
    try:
        cached = _get_cached(key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return cached
        started = monotonic()
        sequence = build_sequence(ra_deg, dec_deg)
        _save_cached(key, sequence)
        response.headers["X-Cache"] = "MISS"
        logger.info("Cache MISS para %s em %.2fs", sequence.sequence_id, monotonic() - started)
        return sequence
    except InsufficientCoverage as exc:
        logger.info("Cobertura insuficiente para RA %.6f Dec %.6f: %s", ra_deg, dec_deg, exc)
        raise HTTPException(
            status_code=404,
            detail={"code": "insufficient_coverage", "message": str(exc)},
        ) from exc
    except SearchTimeout as exc:
        logger.warning("Busca no IRSA excedeu o prazo: %s", exc)
        raise HTTPException(
            status_code=504,
            detail={"code": "search_timeout", "message": "A busca no IRSA demorou. Tente em instantes."},
        ) from exc
    except (ArchiveUnavailable, ValidationError) as exc:
        logger.warning("IRSA indisponível para RA %.6f Dec %.6f: %s", ra_deg, dec_deg, exc)
        raise HTTPException(
            status_code=503,
            detail={"code": "archive_unavailable", "message": "Os dados do IRSA estão temporariamente indisponíveis."},
        ) from exc
    finally:
        processing_slot.release()


@lru_cache(maxsize=8)
def _catalog(ra_deg: float, dec_deg: float, refresh_window: int):
    from .timeline import build_catalog

    return build_catalog(ra_deg, dec_deg)


@contextmanager
def _timeline_slot():
    if not processing_slot.acquire(blocking=False):
        raise HTTPException(
            503, detail={"code": "server_busy", "message": "Outra consulta está em andamento."},
            headers={"Retry-After": "5"},
        )
    try:
        yield
    except SearchTimeout as exc:
        raise HTTPException(504, detail={"code": "search_timeout", "message": str(exc)}) from exc
    except (ArchiveUnavailable, ValidationError) as exc:
        logger.warning("Erro do IRSA na linha do tempo: %s", exc)
        raise HTTPException(
            503, detail={"code": "archive_unavailable", "message": "Os dados do IRSA estão indisponíveis."},
        ) from exc
    finally:
        processing_slot.release()


QueryRA = Annotated[float, Query(ge=0, lt=360, allow_inf_nan=False)]
QueryDec = Annotated[float, Query(ge=-90, le=90, allow_inf_nan=False)]
ImageID = Annotated[str, Query(pattern=r"^[a-f0-9]{24}$")]


@app.get("/api/v1/timeline", responses={503: {"model": ErrorResponse}, 504: {"model": ErrorResponse}})
def get_timeline(ra_deg: QueryRA, dec_deg: QueryDec) -> Timeline:
    """List catalog exposures without downloading their FITS images."""
    with _timeline_slot():
        return _catalog(round(ra_deg, 6) % 360, round(dec_deg, 6) + 0.0, int(monotonic() // 300)).timeline


@app.get(
    "/api/v1/timeline/frame",
    responses={code: {"model": ErrorResponse} for code in (404, 409, 503, 504)},
)
def get_timeline_frame(
    ra_deg: QueryRA, dec_deg: QueryDec, image_id: ImageID, reference_id: ImageID | None = None,
) -> Frame:
    """Render one catalog exposure, optionally using a fixed comparison reference."""
    from .timeline import IncompatibleExposure, UnusableExposure, build_frame

    ra_deg = round(ra_deg, 6) % 360
    dec_deg = round(dec_deg, 6) + 0.0
    with _timeline_slot():
        catalog = _catalog(ra_deg, dec_deg, int(monotonic() // 300))
        candidate = catalog.candidates.get(image_id)
        reference = catalog.candidates.get(reference_id) if reference_id else None
        if candidate is None or (reference_id and reference is None):
            raise HTTPException(404, detail={"code": "exposure_not_found", "message": "Exposição fora do catálogo deste campo."})
        try:
            return build_frame(ra_deg, dec_deg, candidate, reference)
        except UnusableExposure as exc:
            raise HTTPException(404, detail={"code": "unusable_exposure", "message": str(exc)}) from exc
        except IncompatibleExposure as exc:
            raise HTTPException(409, detail={"code": "incompatible_exposure", "message": str(exc)}) from exc
