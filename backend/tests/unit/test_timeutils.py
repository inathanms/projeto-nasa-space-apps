import pytest

from app.processing.timeutils import iso_to_mjd, mjd_to_iso


def test_mjd_to_iso_format():
    iso = mjd_to_iso(61177.456981)
    assert iso.startswith("2026-05-17T10:5")
    assert iso.endswith("Z")
    assert len(iso) == 20


def test_mjd_zero_epoch():
    assert mjd_to_iso(51544.0) == "2000-01-01T00:00:00Z"


def test_roundtrip():
    assert iso_to_mjd(mjd_to_iso(61177.456981)) == pytest.approx(61177.456981, abs=1e-5)


def test_iso_to_mjd_accepts_z_and_plain():
    assert iso_to_mjd("2000-01-01T00:00:00Z") == pytest.approx(51544.0)
    assert iso_to_mjd("2000-01-01T00:00:00") == pytest.approx(51544.0)
