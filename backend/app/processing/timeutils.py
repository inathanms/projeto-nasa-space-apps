from astropy.time import Time


def mjd_to_iso(mjd: float) -> str:
    """Convert MJD (UTC) to ISO 8601 with Z suffix, second precision."""
    t = Time(mjd, format="mjd", scale="utc")
    return t.to_datetime().strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_mjd(iso: str) -> float:
    """Convert ISO 8601 UTC (optional Z suffix) to MJD."""
    return float(Time(iso.removesuffix("Z"), format="isot", scale="utc").mjd)
