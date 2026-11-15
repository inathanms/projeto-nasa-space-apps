from dataclasses import dataclass, field
from enum import StrEnum


class Detector(StrEnum):
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"
    D5 = "D5"
    D6 = "D6"


class ImageMode(StrEnum):
    SINGLE = "single"
    RGB = "rgb"


DEFAULT_RGB_DETECTORS = (Detector.D3, Detector.D2, Detector.D1)  # R, G, B: longest λ is red


class Collection(StrEnum):
    QR3 = "spherex_qr3"
    QR3_DEEP = "spherex_qr3_deep"
    DR1 = "spherex_dr1"
    DR1_DEEP = "spherex_dr1_deep"


@dataclass(frozen=True)
class ImageRecord:
    """One SIA row: a single detector image of one observation. MJD in days, wavelengths in µm."""

    observation_id: str
    detector: Detector
    wavelength_min_um: float
    wavelength_max_um: float
    start_mjd: float
    end_mjd: float
    exposure_seconds: float
    center_ra: float
    center_dec: float
    footprint: list[tuple[float, float]]
    access_url: str


@dataclass(frozen=True)
class SiaResult:
    records: list[ImageRecord]
    truncated: bool = False


@dataclass
class Observation:
    observation_id: str
    start_mjd: float
    end_mjd: float
    exposure_seconds: float
    images: list[ImageRecord] = field(default_factory=list)
    visit_index: int = 0


@dataclass
class Visit:
    visit_index: int
    start_mjd: float
    end_mjd: float
    observation_ids: list[str] = field(default_factory=list)
    detectors: list[Detector] = field(default_factory=list)  # union over the visit, D1..D6
