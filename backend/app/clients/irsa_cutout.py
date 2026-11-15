import httpx

from app.clients.http import get_bytes
from app.config import Settings


class IrsaCutoutClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings

    async def fetch(self, access_url: str, ra: float, dec: float, size_px: int) -> bytes:
        """Raw FITS bytes (possibly gzipped) of a `size_px`-pixel cutout centered on (ra, dec).

        IRSA clips the cutout at the detector edge, so it may come back smaller.
        """
        return await get_bytes(
            self._http,
            access_url,
            {"center": f"{ra},{dec}", "size": f"{size_px}pix"},
            self._settings,
            event="irsa_cutout",
            timeout=self._settings.irsa_cutout_timeout_seconds,
            max_bytes=self._settings.irsa_max_cutout_bytes,
        )
