import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.schemas import ErrorResponse
from app.domain.errors import DomainError

logger = logging.getLogger(__name__)


def error_response(
    status: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    """JSON error envelope of spec 4.4."""
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or {}}},
    )


def _field_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    fields = []
    for err in exc.errors():
        loc = [str(p) for p in err.get("loc", ())]
        if loc and loc[0] in ("query", "path", "header", "body"):
            loc = loc[1:]
        message = str(err.get("msg", "Invalid value")).removeprefix("Value error, ")
        fields.append(
            {"field": ".".join(loc) or "request", "message": message, "type": err["type"]}
        )
    return fields


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    log = logger.warning if exc.http_status < 500 else logger.error
    log(
        exc.message,
        extra={"event": "domain_error", "code": exc.code, "path": request.url.path},
    )
    return error_response(exc.http_status, exc.code, exc.message, exc.details)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = _field_errors(exc)
    names = ", ".join(sorted({f["field"] for f in fields}))
    return error_response(
        422, "VALIDATION_ERROR", f"Invalid request parameters: {names}.", {"fields": fields}
    )


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", extra={"event": "internal_error", "path": request.url.path})
    return error_response(500, "INTERNAL_ERROR", "Internal server error.")


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)


_ERROR_DOCS: dict[int, tuple[str, str, str]] = {
    404: (
        "OBSERVATION_NOT_FOUND",
        (
            "No image for this observation_id + detector at the requested position "
            "(OBSERVATION_NOT_FOUND) or, in mode=rgb, no observation of the reference's "
            "visit has a requested detector (DETECTOR_NOT_AVAILABLE, details: "
            "missing_detectors, available_detectors)."
        ),
        "No image found for observation_id=2026W20_2A_0464_9 detector=D2 at the requested "
        + "position.",
    ),
    422: (
        "VALIDATION_ERROR",
        (
            "Invalid parameters or combinations (VALIDATION_ERROR) or, on /image, no valid "
            "pixel (EMPTY_IMAGE; in mode=rgb details.empty_channels) or a request that is too "
            "large (REQUEST_TOO_LARGE): final side above MAX_OUTPUT_EDGE_PX (details: "
            "requested_edge_px, max_edge_px, suggestion) or cutout budget exceeded even with "
            "one frame per channel (details: total_cutouts, fetch_pixels, max_cutouts, "
            "max_fetch_pixels, suggestion)."
        ),
        "Invalid request parameters: ra.",
    ),
    502: (
        "UPSTREAM_ERROR",
        "IRSA failed (UPSTREAM_ERROR) or sent unusable data (UPSTREAM_INVALID_RESPONSE).",
        "Upstream returned HTTP 503.",
    ),
    503: (
        "SERVER_BUSY",
        "Too many concurrent renders; retry later.",
        "Server is busy rendering other images; retry later.",
    ),
    504: ("UPSTREAM_TIMEOUT", "IRSA did not answer in time.", "Upstream request timed out."),
}


def error_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` entries for the given error statuses, in the spec 4.4 envelope."""
    docs: dict[int | str, dict[str, Any]] = {}
    for status in (*statuses, 500):
        code, description, message = _ERROR_DOCS.get(
            status, ("INTERNAL_ERROR", "Unexpected server error.", "Internal server error.")
        )
        details = (
            {"fields": [{"field": "ra", "message": "Input should be less than 360"}]}
            if code == "VALIDATION_ERROR"
            else {}
        )
        docs[status] = {
            "model": ErrorResponse,
            "description": description,
            "content": {
                "application/json": {
                    "example": {"error": {"code": code, "message": message, "details": details}}
                }
            },
        }
    return docs
