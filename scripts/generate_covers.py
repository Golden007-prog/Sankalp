"""Generate the 5 anchor-AC Imagen covers — one shot, idempotent skip
when the GCS object already exists. Uses scene-style prompts vetted
against StoryAgent guardrails (no political/religious imagery).

Cost: ~$0.04 per Imagen 3 image × 5 = $0.20.

Usage:
  python scripts/generate_covers.py [--force]
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from tools.imagen import imagen_cover, reset_call_counter  # noqa: E402

COVERS = {
    "KA-151": (
        "A serene south Indian cityscape at dawn — palm trees, low-rise "
        "tech-park silhouettes, faint mist over a small lake; soft pastel "
        "watercolor style; no people, no text, no symbols."
    ),
    "BR-180": (
        "Wide aerial of the Ganga river at golden-hour sunrise near a "
        "north Indian city; long stone embankments and small boats blurred "
        "in the distance; warm light; no people, no text."
    ),
    "TG-064": (
        "Painterly silhouette of an old Hyderabad skyline at dusk; layered "
        "rooftops, kites in the sky; abstract teal-and-saffron palette; "
        "no people, no text."
    ),
    "WB-159": (
        "Quiet Kolkata street in early morning light — yellow taxi parked, "
        "tram tracks vanishing into mist, faint banyan tree; muted greens "
        "and ochres; no people, no text."
    ),
    "MH-176": (
        "Mumbai sea face at high tide — abstract blue horizon, a single "
        "fishing boat far out; gentle gradient sky; no people, no text."
    ),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Regenerate even if blob exists")
    parser.add_argument("--cap", type=int, default=10, help="Dev cap override")
    args = parser.parse_args()

    if not (os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() == "true"
            and os.environ.get("GOOGLE_CLOUD_PROJECT")):
        print("Skipping: GOOGLE_GENAI_USE_VERTEXAI=true + GOOGLE_CLOUD_PROJECT required.")
        return 0

    os.environ["SANKALP_IMAGEN_DEV_CAP"] = str(args.cap)
    reset_call_counter()

    bucket = os.environ.get("STORAGE_BUCKET")
    if not bucket:
        print("ERROR: STORAGE_BUCKET unset.", file=sys.stderr)
        return 2

    from google.cloud import storage  # local
    gcs = storage.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    bkt = gcs.bucket(bucket)

    for ac, prompt in COVERS.items():
        blob = bkt.blob(f"story/{ac}/cover.png")
        if blob.exists() and not args.force:
            print(f"  {ac:8s}  exists  https://storage.googleapis.com/{bucket}/story/{ac}/cover.png")
            continue
        print(f"  {ac:8s}  generating ...", end=" ", flush=True)
        t0 = time.perf_counter()
        out = imagen_cover(prompt, cover_key=ac)
        dt = time.perf_counter() - t0
        if out.get("ok"):
            print(f"ok  {out.get('image_url')}  ({dt:.1f}s)")
        else:
            print(f"FAIL  {out.get('error')}: {out.get('user_message') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
