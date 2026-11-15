class DomainError(Exception):
    """Base for errors mapped to the HTTP error envelope (spec 4.4)."""

    code = "INTERNAL_ERROR"
    http_status = 500

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ObservationNotFoundError(DomainError):
    code = "OBSERVATION_NOT_FOUND"
    http_status = 404


class EmptyImageError(DomainError):
    code = "EMPTY_IMAGE"
    http_status = 422


class UpstreamError(DomainError):
    code = "UPSTREAM_ERROR"
    http_status = 502


class UpstreamInvalidResponseError(DomainError):
    code = "UPSTREAM_INVALID_RESPONSE"
    http_status = 502


class UpstreamTimeoutError(DomainError):
    code = "UPSTREAM_TIMEOUT"
    http_status = 504


class ServerBusyError(DomainError):
    code = "SERVER_BUSY"
    http_status = 503


class DetectorNotAvailableError(DomainError):
    code = "DETECTOR_NOT_AVAILABLE"
    http_status = 404


class RequestTooLargeError(DomainError):
    code = "REQUEST_TOO_LARGE"
    http_status = 422
