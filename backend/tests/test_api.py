"""Verify the browser-facing contract without calling the archive."""

import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import httpx

from app import main
from app.errors import ArchiveUnavailable, InsufficientCoverage, SearchTimeout
from app.models import Frame, Sequence

QUERY = {"ra_deg": 210.80227, "dec_deg": 54.34895}


def example() -> Sequence:
    start = datetime(2025, 6, 3, tzinfo=timezone.utc)
    end = datetime(2025, 12, 1, tzinfo=timezone.utc)
    captured = datetime(2026, 11, 14, tzinfo=timezone.utc)
    product = "https://irsa.ipac.caltech.edu/"
    frames = tuple(
        Frame(
            frame_id=f"test-{index}", observed_at_utc=when, collection="spherex_dr1", detector="D1",
            wavelength_um=0.9, bandwidth_um=0.025, calibration_version="test",
            source_url=product, cutout_url=product, valid_fraction=0.95, image_src="data:image/png;base64,",
        )
        for index, when in enumerate((start, end), 1)
    )
    return Sequence(
        sequence_id="test", ra_deg=QUERY["ra_deg"], dec_deg=QUERY["dec_deg"], collections=["spherex_dr1"],
        fetched_at_utc=captured, generated_at_utc=captured, processing_version="test", frames=frames,
    )


class ApiTests(unittest.TestCase):
    def setUp(self):
        main.cache.clear()

    def request(self, url, **kwargs):
        async def request_once():
            transport = httpx.ASGITransport(app=main.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
                return await client.get(url, **kwargs)

        return asyncio.run(request_once())

    def test_health_and_cors(self):
        response = self.request("/health", headers={"Origin": "http://localhost:3000"})
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:3000")
        self.assertNotIn(
            "access-control-allow-origin",
            self.request("/health", headers={"Origin": "https://example.org"}).headers,
        )

    def test_non_finite_and_out_of_range_coordinates(self):
        for params, field in [
            ({"ra_deg": "NaN", "dec_deg": 0}, "ra_deg"),
            ({"ra_deg": 360, "dec_deg": 0}, "ra_deg"),
            ({"ra_deg": 1, "dec_deg": 91}, "dec_deg"),
            ({"ra_deg": 1, "dec_deg": "-Inf"}, "dec_deg"),
        ]:
            with self.subTest(params=params):
                response = self.request("/api/v1/sequence", params=params)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"][0]["loc"], ["query", field])

    def test_archive_failures_map_to_distinct_browser_states(self):
        for exception, status, code in [
            (InsufficientCoverage("sem par"), 404, "insufficient_coverage"),
            (ArchiveUnavailable("fora de serviço"), 503, "archive_unavailable"),
            (SearchTimeout("demorou"), 504, "search_timeout"),
        ]:
            with self.subTest(code=code):
                with patch("app.sequence.build_sequence", side_effect=exception):
                    response = self.request("/api/v1/sequence", params=QUERY)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.json()["detail"]["code"], code)

    def test_cache_reuses_result_for_normalized_coordinates(self):
        with patch("app.sequence.build_sequence", return_value=example()) as build:
            first = self.request("/api/v1/sequence", params=QUERY)
            second = self.request("/api/v1/sequence", params={**QUERY, "ra_deg": 210.80227001})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.headers["X-Cache"], "MISS")
        self.assertEqual(second.headers["X-Cache"], "HIT")
        self.assertEqual(first.json(), second.json())
        build.assert_called_once_with(210.80227, 54.34895)

    def test_second_cold_search_returns_retry_after(self):
        with patch("app.sequence.build_sequence") as build:
            main.processing_slot.acquire()
            try:
                response = self.request("/api/v1/sequence", params=QUERY)
            finally:
                main.processing_slot.release()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertEqual(response.json()["detail"]["code"], "server_busy")
        build.assert_not_called()
