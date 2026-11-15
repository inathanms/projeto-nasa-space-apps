from typing import Protocol

from app.domain.models import Collection, SiaResult


class SiaClient(Protocol):
    async def search(
        self,
        ra: float,
        dec: float,
        radius: float,
        collection: Collection,
        start_mjd: float | None = None,
        end_mjd: float | None = None,
    ) -> SiaResult:
        """Images covering (ra, dec) in degrees within radius degrees; optional MJD window."""
        ...


class CutoutClient(Protocol):
    async def fetch(self, access_url: str, ra: float, dec: float, size_px: int) -> bytes:
        """Raw FITS bytes of a `size_px`-pixel square cutout centered on (ra, dec) degrees."""
        ...
