import io
import logging
import re

import httpx
from astropy.io.votable import parse

from app.clients.http import get_bytes
from app.config import Settings
from app.domain.errors import UpstreamError, UpstreamInvalidResponseError
from app.domain.models import Collection, Detector, ImageRecord, SiaResult

logger = logging.getLogger(__name__)

_BANDPASS = re.compile(r"^SPHEREx-D([1-6])$")
_REQUIRED = (
    "obs_id",
    "energy_bandpassname",
    "em_min",
    "em_max",
    "t_min",
    "t_max",
    "t_exptime",
    "s_ra",
    "s_dec",
    "s_region",
    "access_url",
    "dataproduct_subtype",
)


def parse_region(region: str) -> list[tuple[float, float]]:
    """'POLYGON ICRS ra1 dec1 ...' (degrees) -> [(ra, dec)], without the closing duplicate point."""
    tokens = region.split()
    if tokens and tokens[0].upper() == "POLYGON":
        tokens = tokens[1:]
    if tokens and tokens[0].upper() == "ICRS":
        tokens = tokens[1:]
    values = [float(t) for t in tokens]
    if len(values) < 6 or len(values) % 2:
        raise ValueError("malformed polygon")
    points = [(round(values[i], 6), round(values[i + 1], 6)) for i in range(0, len(values), 2)]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points


class IrsaSiaClient:
    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self._http = http
        self._settings = settings

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
        params = {
            "COLLECTION": str(collection.value),
            "POS": f"CIRCLE {ra} {dec} {radius}",
            "MAXREC": str(self._settings.irsa_sia_maxrec),
        }
        if start_mjd is not None or end_mjd is not None:
            lo = "-inf" if start_mjd is None else f"{start_mjd}"
            hi = "+inf" if end_mjd is None else f"{end_mjd}"
            params["TIME"] = f"{lo} {hi}"
        content = await get_bytes(
            self._http,
            self._settings.irsa_sia_url,
            params,
            self._settings,
            event="irsa_sia",
            timeout=self._settings.irsa_sia_timeout_seconds,
        )
        return self._parse(content)

    def _parse(self, content: bytes) -> SiaResult:
        try:
            votable = parse(io.BytesIO(content), verify="ignore")
            resources = [r for r in votable.resources if r.type == "results"]
            infos = list(votable.infos) + [i for r in resources for i in r.infos]
            status = next((i for i in infos if i.name == "QUERY_STATUS"), None)
            if status is not None and str(status.value).upper() == "ERROR":
                logger.error(
                    "IRSA SIA query error",
                    extra={"event": "irsa_sia_error", "irsa_message": status.content},
                )
                raise UpstreamError("IRSA reported an error for the query.")
            truncated = status is not None and str(status.value).upper() == "OVERFLOW"
            tables = [t for r in resources for t in r.tables]
            if not tables:
                raise ValueError("no results table")
            table = tables[0].to_table(use_names_over_ids=True)
            missing = [c for c in _REQUIRED if c not in table.colnames]
            if missing:
                raise ValueError(f"missing columns {missing}")
        except UpstreamError:
            raise
        except Exception as exc:  # noqa: BLE001 - astropy raises many unrelated types
            logger.warning(
                "invalid SIA VOTable",
                extra={"event": "irsa_sia_invalid", "error": f"{type(exc).__name__}: {exc}"},
            )
            raise UpstreamInvalidResponseError("IRSA returned an invalid VOTable.") from None

        records: dict[tuple[str, Detector], ImageRecord] = {}
        for row in table:
            if str(row["dataproduct_subtype"]).strip().lower() != "science":
                continue
            match = _BANDPASS.match(str(row["energy_bandpassname"]).strip())
            if not match:
                logger.warning(
                    "unexpected energy_bandpassname",
                    extra={"event": "sia_row_discarded", "value": str(row["energy_bandpassname"])},
                )
                continue
            detector = Detector(f"D{match.group(1)}")
            try:
                record = ImageRecord(
                    observation_id=str(row["obs_id"]),
                    detector=detector,
                    wavelength_min_um=round(float(row["em_min"]) * 1e6, 4),
                    wavelength_max_um=round(float(row["em_max"]) * 1e6, 4),
                    start_mjd=float(row["t_min"]),
                    end_mjd=float(row["t_max"]),
                    exposure_seconds=float(row["t_exptime"]),
                    center_ra=round(float(row["s_ra"]), 6),
                    center_dec=round(float(row["s_dec"]), 6),
                    footprint=parse_region(str(row["s_region"])),
                    access_url=str(row["access_url"]),
                )
            except (ValueError, TypeError):
                logger.warning(
                    "malformed SIA row",
                    extra={"event": "sia_row_discarded", "obs_id": str(row["obs_id"])},
                )
                continue
            key = (record.observation_id, detector)
            if key in records:
                logger.warning(
                    "duplicate SIA row",
                    extra={"event": "sia_row_duplicate", "obs_id": key[0], "detector": detector},
                )
                continue
            records[key] = record
        return SiaResult(records=list(records.values()), truncated=truncated)
