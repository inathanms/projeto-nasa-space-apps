"""Live RGB/stack tests against the real IRSA (run with `pytest -m live -s`)."""

import io
import resource
import time
from dataclasses import dataclass

import httpx
import numpy as np
import pytest
from PIL import Image

from tests.live.conftest import run_upstream, skip_if_upstream_down

pytestmark = pytest.mark.live

M101 = (210.80227, 54.34895)
ORION = (83.8221, -5.3911)
PAUSE_SECONDS = 5  # IRSA answers "Server busy" under bursts
RGB_DETECTORS = frozenset({"D1", "D2", "D3"})


@dataclass(frozen=True)
class Result:
    response: httpx.Response
    seconds: float
    rss_before_mb: float
    rss_after_mb: float


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024  # KiB on Linux


def _reference_observation(
    client, ra: float, dec: float, needed: frozenset[str] = frozenset()
) -> str:
    """First observation from /epochs whose visit has every detector in `needed`.

    Each observation covers the point with one detector pair only (D1+D4, D2+D5 or D3+D6),
    and in real data a visit often lacks a pair, so mode=rgb needs a suitable visit.
    """
    epochs = client.get("/epochs", params={"ra": ra, "dec": dec})
    skip_if_upstream_down(epochs)
    assert epochs.status_code == 200, epochs.text
    body = epochs.json()
    detectors = {
        o["observation_id"]: {d["detector"] for d in o["detectors"]} for o in body["observations"]
    }
    for visit in body["visits"]:
        ids = visit["observation_ids"]
        if needed <= set().union(*(detectors[i] for i in ids)):
            return ids[0]
    pytest.skip(f"no visit at ({ra}, {dec}) has {sorted(needed)}")


def _timed_image(client, label: str, ra: float, dec: float, **params) -> Result:
    time.sleep(PAUSE_SECONDS)
    needed = RGB_DETECTORS if params.get("mode") == "rgb" else frozenset()
    obs = _reference_observation(client, ra, dec, needed)
    before = _rss_mb()
    start = time.perf_counter()
    response = run_upstream(
        lambda: client.get("/image", params={"ra": ra, "dec": dec, "observation_id": obs, **params})
    )
    seconds = time.perf_counter() - start
    after = _rss_mb()
    skip_if_upstream_down(response)
    h = response.headers
    print(
        f"\n[live {label}] status={response.status_code} duration={seconds:.1f}s "
        f"ru_maxrss before={before:.0f}MB after={after:.0f}MB (delta {after - before:+.0f}MB) "
        f"png_bytes={len(response.content)} obs={obs} "
        f"stack_count={h.get('X-Stack-Count')} truncated={h.get('X-Stack-Truncated')} "
        f"span_s={h.get('X-Stack-Time-Span-Seconds')} size={h.get('X-Image-Width')}x"
        f"{h.get('X-Image-Height')} channel_obs={h.get('X-Channel-Observation-Ids')} "
        f"channel_span_s={h.get('X-Channel-Time-Span-Seconds')}"
    )
    return Result(response, seconds, before, after)


def _assert_rgb_png(result: Result) -> None:
    response = result.response
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    assert response.headers["X-Mode"] == "rgb"
    assert response.headers["X-Detector"] == "D3,D2,D1"
    for name in (
        "X-Wavelength-Min-Um",
        "X-Wavelength-Max-Um",
        "X-Scale-Min",
        "X-Scale-Max",
        "X-Channel-Observation-Ids",
    ):
        assert len(response.headers[name].split(",")) == 3, name
    assert float(response.headers["X-Channel-Time-Span-Seconds"]) > 0
    png = Image.open(io.BytesIO(response.content))
    assert png.mode == "RGBA"
    assert png.size == (
        int(response.headers["X-Image-Width"]),
        int(response.headers["X-Image-Height"]),
    )
    arr = np.asarray(png)
    assert arr[..., 3].max() == 255
    opaque = arr[arr[..., 3] > 0][:, :3]
    # False color: the three channels must not be identical everywhere.
    assert np.abs(opaque[:, 0].astype(int) - opaque[:, 2].astype(int)).mean() > 0.5


@pytest.fixture(scope="module")
def m101_rgb_stack(client) -> Result:
    return _timed_image(client, "m101 rgb stack", *M101, mode="rgb", stack="true", size=1.0)


@pytest.fixture(scope="module")
def orion_rgb(client) -> Result:
    return _timed_image(client, "orion rgb", *ORION, mode="rgb", size=1.0)


@pytest.fixture(scope="module")
def m101_single_stack(client) -> Result:
    obs = _reference_observation(client, *M101)
    time.sleep(PAUSE_SECONDS)
    dets = {
        d["detector"]
        for o in client.get("/epochs", params={"ra": M101[0], "dec": M101[1]}).json()[
            "observations"
        ]
        if o["observation_id"] == obs
        for d in o["detectors"]
    }
    det = "D2" if "D2" in dets else min(dets)
    return _timed_image(
        client,
        f"m101 single {det} stack",
        *M101,
        mode="single",
        detector=det,
        stack="true",
        size=0.5,
    )


def test_m101_single_stack(m101_single_stack: Result):
    r = m101_single_stack.response
    assert r.status_code == 200, r.text
    assert int(r.headers["X-Stack-Count"]) >= 1
    assert r.headers["X-Stack-Observation-Ids"]


def test_m101_rgb_stack(m101_rgb_stack: Result):
    _assert_rgb_png(m101_rgb_stack)
    h = m101_rgb_stack.response.headers
    counts = h["X-Stack-Count"].split(",")
    assert len(counts) == 3
    assert all(int(c) >= 1 for c in counts)
    assert h["X-Stack-Observation-Ids"]
    assert int(h["X-Image-Width"]) > 0


def test_orion_rgb_without_stack(orion_rgb: Result):
    _assert_rgb_png(orion_rgb)
    assert "X-Stack-Count" not in orion_rgb.response.headers
