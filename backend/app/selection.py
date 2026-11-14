"""Rank download candidates using approximate footprints and observing epochs."""

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .irsa import Candidate

# Footprint vertex order of the SPHEREx SIA2 polygons follows the detector
# axes. Position along the second axis approximates the LVF wavelength.
# Accurate wavelength and bandwidth still come from each FITS spectral WCS.
BANDWIDTH_FRACTION = {"D1": 0.055, "D2": 0.062, "D3": 0.057,
                      "D4": 0.081, "D5": 0.087, "D6": 0.094}


@dataclass(frozen=True)
class Position:
    spectral_axis: float
    distance_to_edge: float


def footprint_position(candidate: Candidate, ra_deg: float, dec_deg: float) -> Position | None:
    tokens = candidate.region.split()
    if len(tokens) < 10 or tokens[:2] != ["POLYGON", "ICRS"]:
        return None
    try:
        ra, dec = np.radians(np.array(tokens[2:10], dtype=float).reshape(4, 2)).T
        ra0, dec0 = np.radians([ra_deg, dec_deg])
        delta = ra - ra0
        denominator = np.sin(dec0) * np.sin(dec) + np.cos(dec0) * np.cos(dec) * np.cos(delta)
        if not np.isfinite(denominator).all() or (denominator <= 0).any():
            return None
        x = np.cos(dec) * np.sin(delta) / denominator
        y = (np.cos(dec0) * np.sin(dec) - np.sin(dec0) * np.cos(dec) * np.cos(delta)) / denominator
        points = np.stack((x, y), axis=1)
        first_axis = (points[1] - points[0] + points[2] - points[3]) / 2
        second_axis = (points[3] - points[0] + points[2] - points[1]) / 2
        middle = points.mean(axis=0)
        a, b = np.linalg.solve(np.stack((first_axis, second_axis), axis=1), -middle) + 0.5
    except (ValueError, np.linalg.LinAlgError):
        return None
    return Position(float(b), float(min(a, b, 1 - a, 1 - b)))


def rank_pairs(candidates: list[Candidate], ra_deg: float, dec_deg: float) -> list[tuple[Candidate, Candidate]]:
    by_detector: dict[str, list[tuple[Candidate, Position | None]]] = defaultdict(list)
    # obs_publisher_did contains the collection; source URLs also remove
    # duplicate rows from multiple SIA2 time windows.
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.frame_id in seen or candidate.source_url in seen:
            continue
        seen.update((candidate.frame_id, candidate.source_url))
        position = footprint_position(candidate, ra_deg, dec_deg)
        if position is None or position.distance_to_edge > -0.01:
            by_detector[candidate.detector].append((candidate, position))

    ranked = []
    for detector, rows in by_detector.items():
        rows.sort(key=lambda item: item[0].t_min)
        for (first, a), (second, b) in combinations(rows, 2):
            time_gap = second.t_min - first.t_max
            if time_gap < 1:
                continue
            if None not in (first.em_min, first.em_max, second.em_min, second.em_max) and (
                first.em_min >= second.em_max or second.em_min >= first.em_max
            ):
                continue

            # Prefer visits months apart, close spectral positions, and
            # fields clear of detector edges. Similar candidates can share
            # one FITS download as pairs are tried.
            epoch_score = 1.6 * min(time_gap / 180, 1) + 0.15 * min(time_gap / 365, 1)
            if a is None or b is None:
                spectral_penalty, edge_penalty = 1.5, 0.5
            else:
                bandwidth = BANDWIDTH_FRACTION.get(detector, 0.06)
                spectral_penalty = abs(a.spectral_axis - b.spectral_axis) / bandwidth
                edge_penalty = max(0.035 - min(a.distance_to_edge, b.distance_to_edge), 0) * 20
            # Barnard and other cool stars are well captured at shorter
            # wavelengths, but this is only a tie breaker for any target.
            detector_penalty = int(detector[-1]) * 0.025
            score = epoch_score - spectral_penalty - edge_penalty - detector_penalty
            ranked.append((score, first, second))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [(first, second) for _, first, second in ranked]
