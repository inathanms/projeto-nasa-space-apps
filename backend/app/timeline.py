"""Catalog all candidate exposures and render a selected one on demand."""

import hashlib
from dataclasses import dataclass
from datetime import timezone
from functools import lru_cache
from time import monotonic

import numpy as np
import requests
from astropy.time import Time

from . import processing
from .errors import ArchiveUnavailable, SearchTimeout
from .irsa import TIMELINE_COLLECTIONS, Candidate, cutout_url, remaining, search_timeline
from .models import CatalogExposure, Frame, Timeline, TimelineCollection
from .sequence import as_frame, load_exposure


@dataclass(frozen=True)
class Catalog:
    timeline: Timeline
    candidates: dict[str, Candidate]


class UnusableExposure(ValueError):
    pass


class IncompatibleExposure(ValueError):
    pass


def catalog_from_candidates(
    ra_deg: float, dec_deg: float, candidates: list[Candidate],
    incomplete: list[TimelineCollection],
) -> Catalog:
    lookup = {}
    items = []
    seen = set()
    for candidate in sorted(candidates, key=lambda row: (row.t_min, row.detector, row.source_url)):
        if candidate.source_url in seen:
            continue
        seen.add(candidate.source_url)
        image_id = hashlib.sha256(candidate.source_url.encode()).hexdigest()[:24]
        lookup[image_id] = candidate
        items.append(CatalogExposure(
            image_id=image_id,
            frame_id=candidate.frame_id,
            observed_at_utc=Time(candidate.t_min, format="mjd", scale="utc").to_datetime(timezone.utc),
            collection=candidate.collection,
            detector=candidate.detector,
            source_url=candidate.source_url,
            cutout_url=cutout_url(candidate, ra_deg, dec_deg),
        ))
    return Catalog(Timeline(
        ra_deg=ra_deg, dec_deg=dec_deg, incomplete_collections=incomplete, exposures=items,
    ), lookup)


def build_catalog(ra_deg: float, dec_deg: float) -> Catalog:
    candidates: list[Candidate] = []
    incomplete: list[TimelineCollection] = []
    completed = 0
    with requests.Session() as session:
        for collection in TIMELINE_COLLECTIONS:
            try:
                rows, complete = search_timeline(session, collection, ra_deg, dec_deg, monotonic() + 13)
                candidates.extend(rows)
            except (ArchiveUnavailable, SearchTimeout):
                complete = False
            if complete:
                completed += 1
            else:
                incomplete.append(collection)
    if not completed and not candidates:
        raise ArchiveUnavailable("Não foi possível consultar o catálogo do IRSA.")
    return catalog_from_candidates(ra_deg, dec_deg, candidates, incomplete)


@lru_cache(maxsize=48)
def _project(ra_deg: float, dec_deg: float, candidate: Candidate):
    deadline = monotonic() + 12
    with requests.Session() as session:
        exposure = load_exposure(session, candidate, ra_deg, dec_deg, deadline)
    if exposure is None:
        raise UnusableExposure("O FITS não fornece um recorte válido para este campo.")
    try:
        pixels = processing.project_cutout(exposure.cutout, ra_deg, dec_deg)
    except processing.InvalidCutout as exc:
        raise UnusableExposure(str(exc)) from exc
    remaining(deadline)
    return exposure, pixels


def build_frame(
    ra_deg: float, dec_deg: float, candidate: Candidate, reference: Candidate | None,
) -> Frame:
    if reference is not None and candidate.detector != reference.detector:
        raise IncompatibleExposure("A exposição usa um detector diferente do quadro de referência.")
    exposure, pixels = _project(ra_deg, dec_deg, candidate)
    reference_pixels = pixels
    if reference is not None and reference.source_url != candidate.source_url:
        try:
            anchor, reference_pixels = _project(ra_deg, dec_deg, reference)
        except UnusableExposure as exc:
            raise IncompatibleExposure("A imagem de referência não está disponível.") from exc
        if not processing.spectral_compatible(exposure.cutout, anchor.cutout):
            raise IncompatibleExposure("As faixas espectrais no centro do campo não coincidem o suficiente.")
        overlap = np.isfinite(pixels) & np.isfinite(reference_pixels)
        if overlap.mean() < processing.MIN_SHARED_COVERAGE:
            raise IncompatibleExposure("A exposição tem pouca cobertura válida em comum com a referência.")
        pixels = np.where(overlap, pixels, np.nan)
    try:
        rendered = processing.render_exposure(pixels, reference_pixels)
    except processing.InvalidCutout as exc:
        raise UnusableExposure(str(exc)) from exc
    return as_frame(exposure, rendered)
