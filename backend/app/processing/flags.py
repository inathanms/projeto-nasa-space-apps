import logging
import re
from collections.abc import Iterable

import numpy as np
from astropy.io import fits

logger = logging.getLogger(__name__)

_PREFIX = "MP_"
_MSK_NAME = re.compile(r"^MSKN\d{4}$")
NEVER_MASK = frozenset({"SOURCE"})


def flag_definitions(flags_header: fits.Header) -> dict[str, int]:
    """Bit definitions as {NAME: bit}.

    Reads `MP_<NAME> = <bit>` keywords and the convention found in real SPHEREx QR3 cutouts:
    `MSKN<nnnn> = <NAME>` with `MSKM<nnnn> = 2**bit` (falling back to bit = nnnn).
    """
    defs: dict[str, int] = {}
    for key, value in flags_header.items():
        key = key.upper().removeprefix("HIERARCH ").strip()
        if key.startswith(_PREFIX):
            try:
                defs[key[len(_PREFIX) :]] = int(value)
            except (TypeError, ValueError):
                continue
        elif _MSK_NAME.match(key) and isinstance(value, str) and value.strip():
            index = key[len("MSKN") :]
            defs[value.strip().upper()] = _msk_bit(flags_header.get(f"MSKM{index}"), int(index))
    return defs


def _msk_bit(mask_value: object, index: int) -> int:
    try:
        mask = int(mask_value)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return index
    return mask.bit_length() - 1 if mask > 0 and mask & (mask - 1) == 0 else index


def build_mask(
    flags_data: np.ndarray, flags_header: fits.Header, reject_names: Iterable[str]
) -> np.ndarray:
    """Boolean mask (True = bad pixel) of pixels with any rejected flag bit set (spec 4.3.1)."""
    defs = flag_definitions(flags_header)
    if not defs:
        logger.warning(
            "FLAGS header has no bit definitions; skipping mask",
            extra={"event": "flags_definitions_missing"},
        )
        return np.zeros(np.shape(flags_data), dtype=bool)

    reject_bits = 0
    for name in reject_names:
        name = name.strip().upper()
        if name in defs and name not in NEVER_MASK:
            reject_bits |= 1 << defs[name]
    # int64 so bit 31 of an int32 FLAGS array can be tested without overflow.
    return (np.asarray(flags_data).astype(np.int64) & reject_bits) != 0
