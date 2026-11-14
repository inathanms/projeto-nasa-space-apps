"""Export the two PNGs and provenance that the frontend uses offline.

Run from backend/ with `python -m scripts.generate_example --help`.
"""

import argparse
import base64
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

from astropy.time import Time

from app.models import CollectionName, Frame, Sequence
from app.processing import PROCESSING_VERSION, decode_cutout, render_pair

PUBLIC_EXAMPLES = Path(__file__).resolve().parents[2] / "frontend" / "public" / "examples"
PNG_PREFIX = "data:image/png;base64,"


def from_fits(args: argparse.Namespace) -> Sequence:
    from app.irsa import cutout_url, parse_votable

    if not all((args.collection, args.votable, args.fetched_at)):
        raise ValueError("--frame requires --collection, --votable and --fetched-at")
    fetched = datetime.fromisoformat(args.fetched_at)
    if fetched.tzinfo is None:
        raise ValueError("--fetched-at must include a UTC offset")
    candidates, _ = parse_votable(args.votable.read_bytes(), args.collection)
    loaded = []
    for frame_id, path in args.frame:
        matches = [
            candidate
            for candidate in candidates
            if frame_id == candidate.frame_id or Path(candidate.source_url).stem == frame_id
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one archive record for {frame_id}. Found {len(matches)}.")
        candidate = matches[0]
        cutout = decode_cutout(Path(path).read_bytes(), args.ra_deg, args.dec_deg)
        if candidate.detector != cutout.detector:
            raise ValueError(f"Detector differs between the archive record and FITS for {frame_id}")
        basename = Path(candidate.source_url).name
        if cutout.observation_id and not basename.startswith(
            f"level2_{cutout.observation_id}{cutout.detector}_"
        ):
            raise ValueError(f"FITS OBSID differs from the archive record for {frame_id}")
        observation = cutout.obstime or Time(candidate.t_min, format="mjd").to_datetime(
            timezone=timezone.utc
        )
        if abs(Time(observation).mjd - candidate.t_min) > 1 / 1440:
            raise ValueError(f"FITS observation differs from the archive record for {frame_id}")
        loaded.append((observation, candidate, cutout))

    loaded.sort(key=lambda item: item[0])
    rendered = render_pair(loaded[0][2], loaded[1][2], args.ra_deg, args.dec_deg)
    first, second = (
        Frame(
            frame_id=candidate.frame_id,
            observed_at_utc=observation,
            collection=candidate.collection,
            detector=cutout.detector,
            wavelength_um=cutout.wavelength_um,
            bandwidth_um=cutout.bandwidth_um,
            calibration_version=cutout.calibration_version,
            source_url=candidate.source_url,
            cutout_url=cutout_url(candidate, args.ra_deg, args.dec_deg),
            valid_fraction=image.valid_fraction,
            image_src=PNG_PREFIX + base64.b64encode(image.png).decode("ascii"),
        )
        for (observation, candidate, cutout), image in zip(loaded, rendered, strict=True)
    )
    return Sequence(
        sequence_id=args.slug,
        ra_deg=args.ra_deg,
        dec_deg=args.dec_deg,
        collections=[args.collection],
        fetched_at_utc=fetched.astimezone(timezone.utc),
        generated_at_utc=datetime.now(timezone.utc),
        processing_version=PROCESSING_VERSION,
        frames=(first, second),
    )


def write_example(sequence: Sequence, slug: str) -> Path:
    output = PUBLIC_EXAMPLES / slug
    output.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, frame in enumerate(sequence.frames, 1):
        if not frame.image_src.startswith(PNG_PREFIX):
            raise ValueError(f"Unexpected image format for {frame.frame_id}")
        filename = f"frame-{index}.png"
        (output / filename).write_bytes(base64.b64decode(frame.image_src[len(PNG_PREFIX):], validate=True))
        frames.append(frame.model_copy(update={"image_src": f"/examples/{slug}/{filename}"}))
    local = sequence.model_copy(update={"sequence_id": slug, "frames": tuple(frames)})
    manifest = output / "manifest.json"
    payload = {**local.model_dump(mode="json"), "is_synthetic": False}
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="Subdirectory in frontend/public/examples/")
    parser.add_argument("ra_deg", type=float, help="ICRS right ascension in decimal degrees")
    parser.add_argument("dec_deg", type=float, help="ICRS declination in decimal degrees")
    parser.add_argument(
        "--frame",
        nargs=2,
        action="append",
        metavar=("PRODUCT_ID", "FITS"),
        help="Offline mode: repeat twice with a VOTable product ID or source filename stem",
    )
    parser.add_argument("--collection", choices=get_args(CollectionName))
    parser.add_argument("--votable", type=Path, help="Original SIA metadata for the downloaded cutouts")
    parser.add_argument("--fetched-at", help="Timestamp when the last input file was retrieved, in ISO 8601")
    args = parser.parse_args()

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.slug):
        parser.error("slug must use lower-case ASCII letters, digits and single hyphens")
    if not (0 <= args.ra_deg < 360 and -90 <= args.dec_deg <= 90):
        parser.error("coordinates must satisfy 0 <= RA < 360 and -90 <= Dec <= 90")
    try:
        if args.frame:
            if len(args.frame) != 2:
                parser.error("provide exactly two --frame arguments")
            sequence = from_fits(args)
        else:
            from app.sequence import build_sequence

            sequence = build_sequence(args.ra_deg, args.dec_deg)
        print(write_example(sequence, args.slug))
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Example export failed: {exc}\n")


if __name__ == "__main__":
    main()
