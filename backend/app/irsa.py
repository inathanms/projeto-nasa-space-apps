"""IRSA SIA2 metadata and bounded IBE cutout downloads."""

import io
import logging
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import monotonic, sleep
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

import numpy as np
import requests
from astropy.io import votable

from .errors import ArchiveUnavailable, SearchTimeout
from .models import CollectionName, TimelineCollection

logger = logging.getLogger(__name__)
COLLECTIONS: tuple[CollectionName, CollectionName] = ("spherex_dr1", "spherex_qr3")
TIMELINE_COLLECTIONS: tuple[TimelineCollection, ...] = (
    *COLLECTIONS, "spherex_dr1_deep", "spherex_qr3_deep",
)
SIA_URL = "https://irsa.ipac.caltech.edu/SIA"
MAX_RECORDS = 400
MAX_VOTABLE_BYTES = 4 * 1024 * 1024
MAX_FITS_BYTES = 8 * 1024 * 1024
MISSION_START_MJD = 60700  # Before the first observations released by the mission.
SECOND_PER_DAY = 86400
MJD_AT_UNIX_EPOCH = 40587


@dataclass(frozen=True)
class Candidate:
    frame_id: str
    collection: TimelineCollection
    source_url: str
    t_min: float
    t_max: float
    detector: str
    region: str
    em_min: float | None
    em_max: float | None


def remaining(deadline: float) -> float:
    available = deadline - monotonic()
    if available <= 0:
        raise SearchTimeout("Orçamento da busca esgotado.")
    return available


def _retry_after(value: str | None) -> float | None:
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None
    return max(0, seconds) if math.isfinite(seconds) else None


def _get(
    session: requests.Session, url: str, deadline: float, size_limit: int, *,
    params: dict[str, str | int] | None = None, missing_ok: bool = False,
) -> bytes | None:
    for attempt in range(2):
        timeout = remaining(deadline)
        try:
            with session.get(
                url, params=params, timeout=(min(timeout, 4), min(timeout, 8)),
                stream=True, allow_redirects=False,
            ) as response:
                remaining(deadline)
                if missing_ok and response.status_code in {400, 404, 416}:
                    return None
                if response.status_code == 429 and attempt == 0:
                    delay = _retry_after(response.headers.get("Retry-After"))
                    if delay is not None and delay + 1 < remaining(deadline):
                        sleep(delay)
                        continue
                if response.status_code != 200:
                    raise ArchiveUnavailable(f"IRSA respondeu HTTP {response.status_code}.")
                length = response.headers.get("Content-Length", "")
                if length.isdecimal() and int(length) > size_limit:
                    raise ArchiveUnavailable("Resposta do IRSA acima do limite de tamanho.")
                data = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    remaining(deadline)
                    if len(data) + len(chunk) > size_limit:
                        raise ArchiveUnavailable("Resposta do IRSA acima do limite de tamanho.")
                    data.extend(chunk)
                return bytes(data)
        except requests.exceptions.Timeout as exc:
            raise SearchTimeout("O IRSA demorou para responder.") from exc
        except requests.exceptions.RequestException as exc:
            remaining(deadline)
            if "Read timed out" in str(exc):
                raise SearchTimeout("O IRSA demorou para enviar os dados.") from exc
            raise ArchiveUnavailable("Falha de comunicação com o IRSA.") from exc
    raise ArchiveUnavailable("O IRSA limitou a taxa de consulta.")


def _valid_source_url(url: str, collection: TimelineCollection) -> bool:
    release = collection.removeprefix("spherex_").removesuffix("_deep")
    try:
        parsed = urlsplit(url)
    except ValueError:
        return False
    return (
        parsed.scheme == "https"
        and parsed.netloc == "irsa.ipac.caltech.edu"
        and not parsed.query
        and not parsed.fragment
        and re.fullmatch(
            rf"/ibe/data/spherex/{release}/level2/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+/[1-6]/[A-Za-z0-9_-]+\.fits(?:\.gz)?",
            parsed.path,
        )
        is not None
    )


def cutout_url(candidate: Candidate, ra_deg: float, dec_deg: float) -> str:
    if not _valid_source_url(candidate.source_url, candidate.collection):
        raise ArchiveUnavailable("O IRSA retornou um URL de produto inesperado.")
    params = urlencode({"center": f"{ra_deg:.8f},{dec_deg:.8f}", "size": "0.1", "gzip": "false"})
    return f"{candidate.source_url}?{params}"


def _as_text(row, field: str) -> str:
    if field not in row.colnames or np.ma.is_masked(row[field]):
        return ""
    value = row[field]
    return value.decode("utf-8").strip() if isinstance(value, bytes) else str(value).strip()


def _as_float(row, field: str) -> float | None:
    try:
        value = float(_as_text(row, field))
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def parse_votable(data: bytes, collection: TimelineCollection) -> tuple[list[Candidate], bool]:
    # Check the protocol status even when the HTTP request succeeded. IRSA
    # marks a limited table OVERFLOW before TABLE in the same resource.
    if b"<!DOCTYPE" in data.upper():
        raise ArchiveUnavailable("VOTable não contém uma definição de documento esperada.")
    try:
        root = ElementTree.fromstring(data)
        results = next(
            resource for resource in root.findall(".//{*}RESOURCE")
            if resource.get("type") == "results"
        )
        statuses = {
            info.get("value") for info in results.findall(".//{*}INFO")
            if info.get("name") == "QUERY_STATUS"
        }
        if "ERROR" in statuses:
            raise ArchiveUnavailable("A consulta SIA2 ao IRSA falhou.")
        table = votable.parse_single_table(
            io.BytesIO(data), verify="ignore",
        ).to_table(use_names_over_ids=True)
    except (ElementTree.ParseError, ValueError, StopIteration, KeyError, OSError) as exc:
        raise ArchiveUnavailable("O IRSA não retornou uma VOTable utilizável.") from exc

    if not {"access_url", "t_min"}.issubset(table.colnames):
        raise ArchiveUnavailable("A VOTable do IRSA não contém as colunas necessárias.")

    candidates = []
    for row in table:
        source = _as_text(row, "access_url")
        t_min = _as_float(row, "t_min")
        if t_min is None or not _valid_source_url(source, collection):
            continue
        detector = f"D{urlsplit(source).path.split('/')[-2]}"
        obs_id = _as_text(row, "obs_id")
        frame_id = _as_text(row, "obs_publisher_did") or (
            f"{collection}:{obs_id}/{detector}" if obs_id else source.rsplit("/", 1)[-1]
        )
        candidates.append(Candidate(
            frame_id=frame_id,
            collection=collection,
            source_url=source,
            t_min=t_min,
            t_max=_as_float(row, "t_max") or t_min,
            detector=detector,
            region=_as_text(row, "s_region"),
            em_min=_as_float(row, "em_min"),
            em_max=_as_float(row, "em_max"),
        ))
    return candidates, "OVERFLOW" in statuses or len(table) == MAX_RECORDS


def _query(
    session: requests.Session, collection: TimelineCollection, ra_deg: float, dec_deg: float,
    deadline: float, interval: tuple[float, float] | None = None,
) -> tuple[list[Candidate], bool]:
    params = {
        "COLLECTION": collection,
        "POS": f"circle {ra_deg:.8f} {dec_deg:.8f} 0.01",
        "MAXREC": MAX_RECORDS,
        "RESPONSEFORMAT": "VOTABLE",
    }
    if interval:
        params["TIME"] = f"{interval[0]:.6f} {interval[1]:.6f}"
    data = _get(session, SIA_URL, deadline, MAX_VOTABLE_BYTES, params=params)
    return parse_votable(data, collection)


def search_images(
    session: requests.Session, collection: CollectionName, ra_deg: float, dec_deg: float, deadline: float,
) -> list[Candidate]:
    rows, truncated = _query(session, collection, ra_deg, dec_deg, deadline)
    if not truncated:
        return rows

    logger.info("SIA2 truncou %s em %d produtos; tentando janelas menores", collection, len(rows))
    latest = datetime.now(timezone.utc).timestamp() / SECOND_PER_DAY + MJD_AT_UNIX_EPOCH + 1
    middle = (MISSION_START_MJD + latest) / 2
    for interval in ((MISSION_START_MJD, middle), (middle, latest)):
        if remaining(deadline) < 8:
            break
        try:
            extra, truncated = _query(session, collection, ra_deg, dec_deg, deadline, interval)
        except (ArchiveUnavailable, SearchTimeout):
            logger.warning("Consulta parcial SIA2 para %s na janela %s", collection, interval)
            continue
        rows.extend(extra)
        if truncated:
            logger.warning("SIA2 ainda truncou %s na janela %s", collection, interval)
    return rows


def download_cutout(session: requests.Session, url: str, deadline: float) -> bytes | None:
    payload = _get(session, url, deadline, MAX_FITS_BYTES, missing_ok=True)
    if payload is not None and not payload.startswith(b"SIMPLE  ="):
        raise ArchiveUnavailable("O recorte do IRSA não contém um FITS reconhecível.")
    return payload


def search_timeline(
    session: requests.Session, collection: TimelineCollection, ra_deg: float, dec_deg: float,
    deadline: float,
) -> tuple[list[Candidate], bool]:
    """Split truncated time windows until complete or report partial coverage."""
    latest = datetime.now(timezone.utc).timestamp() / SECOND_PER_DAY + MJD_AT_UNIX_EPOCH + 1
    windows = [(float(MISSION_START_MJD), latest)]
    rows: dict[str, Candidate] = {}
    complete = True
    while windows:
        start, end = windows.pop(0)
        try:
            found, truncated = _query(session, collection, ra_deg, dec_deg, deadline, (start, end))
        except (ArchiveUnavailable, SearchTimeout):
            if not rows:
                raise
            return list(rows.values()), False
        rows.update((item.source_url, item) for item in found)
        if truncated:
            if end - start <= 1 / SECOND_PER_DAY:
                complete = False
                continue
            middle = round((start + end) / 2, 6)
            windows.extend(((start, middle), (middle, end)))
    return list(rows.values()), complete
