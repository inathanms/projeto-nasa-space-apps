"""Build a sequence without retaining FITS payloads beyond the request."""

import base64
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic

import requests
from astropy.time import Time

from . import processing
from .errors import ArchiveUnavailable, InsufficientCoverage, SearchTimeout
from .irsa import COLLECTIONS, Candidate, cutout_url, download_cutout, remaining, search_images
from .models import Frame, Sequence
from .selection import rank_pairs

logger = logging.getLogger(__name__)
MAX_CANDIDATES = 8
SEARCH_SECONDS = 45
MAX_RESPONSE_BYTES = 500 * 1024


@dataclass(frozen=True)
class Exposure:
    candidate: Candidate
    cutout: processing.Cutout
    url: str
    observed_at: datetime
    fetched_at: datetime


def as_frame(exposure: Exposure, rendered: processing.RenderedFrame) -> Frame:
    cutout = exposure.cutout
    return Frame(
        frame_id=exposure.candidate.frame_id,
        observed_at_utc=exposure.observed_at,
        collection=exposure.candidate.collection,
        detector=cutout.detector,
        wavelength_um=cutout.wavelength_um,
        bandwidth_um=cutout.bandwidth_um,
        calibration_version=cutout.calibration_version,
        source_url=exposure.candidate.source_url,
        cutout_url=exposure.url,
        valid_fraction=rendered.valid_fraction,
        image_src="data:image/png;base64," + base64.b64encode(rendered.png).decode("ascii"),
    )


def load_exposure(
    session: requests.Session, candidate: Candidate, ra_deg: float, dec_deg: float, deadline: float,
) -> Exposure | None:
    url = cutout_url(candidate, ra_deg, dec_deg)
    payload = download_cutout(session, url, deadline)
    if payload is None:
        return None
    fetched_at = datetime.now(timezone.utc)
    try:
        cutout = processing.decode_cutout(payload, ra_deg, dec_deg)
    except processing.InvalidCutout as exc:
        logger.info("FITS rejeitado %s: %s", candidate.frame_id, exc)
        return None
    if cutout.detector != candidate.detector:
        raise ArchiveUnavailable("O detector do recorte difere do produto registrado no SIA2.")
    observed_at = cutout.obstime
    if observed_at is None:
        observed_at = Time(candidate.t_min, format="mjd", scale="utc").to_datetime(timezone.utc)
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return Exposure(candidate, cutout, url, observed_at.astimezone(timezone.utc), fetched_at)


def _render(
    first: Exposure, second: Exposure, ra_deg: float, dec_deg: float, deadline: float,
) -> Sequence | None:
    if not processing.spectral_compatible(first.cutout, second.cutout):
        return None
    first, second = sorted((first, second), key=lambda item: item.observed_at)
    if first.observed_at == second.observed_at:
        return None
    remaining(deadline)
    try:
        rendered = processing.render_pair(first.cutout, second.cutout, ra_deg, dec_deg)
    except processing.InvalidCutout as exc:
        logger.info("Par rejeitado %s / %s: %s", first.candidate.frame_id, second.candidate.frame_id, exc)
        return None
    remaining(deadline)
    frames = (as_frame(first, rendered[0]), as_frame(second, rendered[1]))
    identity = "|".join((
        str(ra_deg), str(dec_deg), processing.PROCESSING_VERSION, frames[0].frame_id, frames[1].frame_id,
    ))
    sequence = Sequence(
        sequence_id=f"spx-{hashlib.sha256(identity.encode()).hexdigest()[:16]}",
        ra_deg=ra_deg,
        dec_deg=dec_deg,
        collections=list(COLLECTIONS),
        fetched_at_utc=max(first.fetched_at, second.fetched_at),
        generated_at_utc=datetime.now(timezone.utc),
        processing_version=processing.PROCESSING_VERSION,
        frames=frames,
    )
    if len(sequence.model_dump_json().encode()) > MAX_RESPONSE_BYTES:
        raise ArchiveUnavailable("A sequência excede o limite de tamanho da API.")
    return sequence


def build_sequence(ra_deg: float, dec_deg: float) -> Sequence:
    deadline = monotonic() + SEARCH_SECONDS
    candidates: list[Candidate] = []
    attempted: dict[str, Exposure | None] = {}
    upstream_error: ArchiveUnavailable | SearchTimeout | None = None
    tested_pairs: set[tuple[str, str]] = set()
    with requests.Session() as session:
        for collection in COLLECTIONS:
            try:
                candidates.extend(search_images(session, collection, ra_deg, dec_deg, deadline))
            except (ArchiveUnavailable, SearchTimeout) as exc:
                upstream_error = exc
                logger.warning("SIA2 %s indisponível: %s", collection, exc)

        shortlist = rank_pairs(candidates, ra_deg, dec_deg)
        eligible_pairs = {(first.frame_id, second.frame_id) for first, second in shortlist}
        for first, second in shortlist:
            remaining(deadline)
            needed = sum(item.frame_id not in attempted for item in (first, second))
            if len(attempted) + needed > MAX_CANDIDATES:
                continue
            if any(item.frame_id in attempted and attempted[item.frame_id] is None for item in (first, second)):
                continue
            for candidate in (first, second):
                if candidate.frame_id not in attempted:
                    try:
                        attempted[candidate.frame_id] = load_exposure(session, candidate, ra_deg, dec_deg, deadline)
                    except (ArchiveUnavailable, SearchTimeout) as exc:
                        upstream_error = exc
                        attempted[candidate.frame_id] = None
                        logger.warning("IBE %s indisponível: %s", candidate.frame_id, exc)
                if attempted[candidate.frame_id] is None:
                    break

            # A new cutout may also pair with an exposure already downloaded.
            first_pass = (first.frame_id, second.frame_id)
            available = [(frame_id, value) for frame_id, value in attempted.items() if value is not None]
            loaded_pairs = [first_pass, *[
                (a, b) for a, _ in available for b, _ in available
                if (a, b) in eligible_pairs and (a, b) != first_pass
            ]]
            for pair in loaded_pairs:
                if pair in tested_pairs:
                    continue
                first_frame, second_frame = (attempted.get(frame_id) for frame_id in pair)
                if first_frame is None or second_frame is None:
                    continue
                tested_pairs.add(pair)
                sequence = _render(first_frame, second_frame, ra_deg, dec_deg, deadline)
                if sequence is not None:
                    logger.info(
                        "Sequência %s pronta em %.2fs: %d downloads tentados, %d produtos catalogados",
                        sequence.sequence_id, SEARCH_SECONDS - remaining(deadline), len(attempted), len(candidates),
                    )
                    return sequence
            if len(attempted) >= MAX_CANDIDATES:
                break

    remaining(deadline)
    if upstream_error is not None:
        raise upstream_error
    raise InsufficientCoverage("Nenhum par comparável foi encontrado no orçamento de busca deste campo.")
