import asyncio
import logging
import time
from urllib.parse import urljoin, urlsplit

import httpx

from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamInvalidResponseError, UpstreamTimeoutError

logger = logging.getLogger(__name__)

RETRY_BACKOFF_SECONDS = 1.0
MAX_REDIRECTS = 5


async def sleep(seconds: float) -> None:
    """Indirection so tests can monkeypatch the backoff."""
    await asyncio.sleep(seconds)


def host_allowed(url: str, allowed_host: str) -> bool:
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    allowed = allowed_host.lower()
    return parts.scheme in ("http", "https") and (host == allowed or host.endswith("." + allowed))


class _Retryable(Exception):
    def __init__(self, error: Exception) -> None:
        self.error = error


async def get_bytes(
    http: httpx.AsyncClient,
    url: str,
    params: dict[str, str] | None,
    settings: Settings,
    *,
    event: str,
    timeout: float,
    max_bytes: int | None = None,
) -> bytes:
    """GET with retry on timeout/5xx, manual redirects restricted to the allowed host (SEC-001),
    and streamed reads capped at max_bytes (SEC-005). Raises Upstream* errors without the URL."""
    if not host_allowed(url, settings.irsa_allowed_host):
        raise UpstreamInvalidResponseError("Upstream URL host is not allowed.")

    attempts = settings.irsa_max_retries + 1
    for attempt in range(1, attempts + 1):
        started = time.perf_counter()
        status: int | None = None
        try:
            body, status = await _single_get(http, url, params, settings, timeout, max_bytes)
            return body
        except _Retryable as retry:
            if attempt == attempts:
                raise retry.error from None
            await sleep(RETRY_BACKOFF_SECONDS)
        finally:
            logger.info(
                "upstream call",
                extra={
                    "event": event,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "attempt": attempt,
                    "status": status,
                },
            )
    raise UpstreamError("Upstream request failed.")  # pragma: no cover


async def _single_get(
    http: httpx.AsyncClient,
    url: str,
    params: dict[str, str] | None,
    settings: Settings,
    timeout: float,
    max_bytes: int | None,
) -> tuple[bytes, int]:
    headers = {"User-Agent": settings.http_user_agent}
    current, current_params = url, params
    try:
        for _ in range(MAX_REDIRECTS + 1):
            async with http.stream(
                "GET",
                current,
                params=current_params,
                headers=headers,
                timeout=timeout,
                follow_redirects=False,
            ) as response:
                code = response.status_code
                if response.is_redirect and "location" in response.headers:
                    current = urljoin(str(response.url), response.headers["location"])
                    current_params = None
                    if not host_allowed(current, settings.irsa_allowed_host):
                        raise UpstreamInvalidResponseError(
                            "Upstream redirected to a disallowed host."
                        )
                    continue
                if code >= 500:
                    raise _Retryable(UpstreamError(f"Upstream returned HTTP {code}."))
                if code >= 400:
                    raise UpstreamError(f"Upstream returned HTTP {code}.")
                if response.is_redirect:
                    raise UpstreamInvalidResponseError("Upstream sent a redirect without Location.")
                declared = response.headers.get("content-length")
                if max_bytes and declared and declared.isdigit() and int(declared) > max_bytes:
                    raise UpstreamInvalidResponseError("Upstream response is too large.")
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if max_bytes is not None and size > max_bytes:
                        raise UpstreamInvalidResponseError("Upstream response is too large.")
                    chunks.append(chunk)
                return b"".join(chunks), code
        raise UpstreamInvalidResponseError("Too many upstream redirects.")
    except httpx.TimeoutException:
        raise _Retryable(UpstreamTimeoutError("Upstream request timed out.")) from None
    except httpx.TransportError as exc:
        logger.warning("upstream transport error", extra={"error_type": type(exc).__name__})
        raise UpstreamError("Upstream request failed.") from None
