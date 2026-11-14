"""Render the offline, explicitly synthetic blink exercise (stdlib only)."""
import json
import math
from pathlib import Path
import random
import struct
import zlib

OUT = Path(__file__).resolve().parents[1] / "public/examples/prototipo"
N = 360
rng = random.Random(108)
stars = [(rng.uniform(0, N), rng.uniform(0, N), rng.uniform(.4, 1.7),
          rng.uniform(14, 100)) for _ in range(440)]
stars += [(74, 89, 2.4, 212), (271, 92, 2.0, 210), (297, 240, 2.4, 216),
          (120, 247, 2.2, 205), (205, 283, 1.9, 198), (157, 53, 2.5, 228)]
background = [rng.random() for _ in range(N * N)]

def chunk(name, data):
    return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name + data))

def render(frame, filename):
    plane = [16 + 15 * v for v in background]
    for y in range(N):
        for x in range(N):
            ridge = y - 275 + x * 0.62 + 13 * math.sin(x / 51)
            plane[y*N+x] += (7 + 4 * math.sin(x / 35 + y / 43)) * math.exp(-ridge**2 / 3150)
    for sx, sy, sigma, power in stars + [(154 + frame * 22, 175 - frame * 10, 1.9, 224)]:
        extent = math.ceil(sigma * 7)
        for y in range(max(0, int(sy)-extent), min(N, int(sy)+extent+1)):
            for x in range(max(0, int(sx)-extent), min(N, int(sx)+extent+1)):
                d = (x-sx)**2 + (y-sy)**2
                plane[y*N+x] += power * (.94 * math.exp(-d / (2*sigma*sigma)) +
                                          .06 * math.exp(-d / (12*sigma*sigma)))
    rows = bytearray()
    for y in range(N):
        rows.append(0)
        for v in plane[y*N:(y+1)*N]:
            rows.extend((min(255, int(v*.90)), min(255, int(v*.96)), min(255, int(v))))
    (OUT / filename).write_bytes(b"\x89PNG\r\n\x1a\n" +
        chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 2, 0, 0, 0)) +
        chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))

OUT.mkdir(parents=True, exist_ok=True)
frames = []
for i, date in enumerate(("2025-04-01T00:00:00Z", "2025-10-01T00:00:00Z")):
    filename = f"epoca-{i+1}.png"
    render(i, filename)
    frames.append(dict(frame_id=f"simulado-{i+1}", observed_at_utc=date,
        collection="Simulação", detector="Exemplo", wavelength_um=2.14,
        bandwidth_um=.06, calibration_version="Simulação", source_url=None,
        cutout_url=None, valid_fraction=1, image_src=f"/examples/prototipo/{filename}"))
sequence = dict(sequence_id="prototipo", is_synthetic=True, ra_deg=210.80227, dec_deg=54.34895,
    fov_arcmin=6, collections=["Simulação"], fetched_at_utc=None,
    generated_at_utc=None, processing_version="synthetic-v1", frames=frames)
(OUT / "manifest.json").write_text(json.dumps(sequence, indent=2, ensure_ascii=False) + "\n")
