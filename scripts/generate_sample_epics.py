"""Render sample EPIC card images for OCR testing.

Output: samples/epics/{persona}.jpg — 1024×640, fields modelled on the
real ECI EPIC layout. Idempotent (deterministic ordering + fixed PIL
options).

Difficulty mix:
  - 3 clean (riya, ravi, dedup_a)
  - 1 light Gaussian blur (priya)
  - 1 JPEG q=35 + 3° rotation (dedup_b)

Usage:
  python scripts/generate_sample_epics.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "samples" / "epics"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CARD_W, CARD_H = 1024, 640
HEADER_H = 88
ACCENT = (200, 30, 30)
INK = (24, 24, 24)
PALE = (242, 242, 240)


PERSONAS = [
    {
        "id": "riya",
        "epic": "ABC1234567",
        "name": "RIYA SHARMA",
        "father": "RAJESH SHARMA",
        "dob": "12/04/2007",
        "gender": "FEMALE",
        "address": "42, MG ROAD, BOMMANAHALLI, BENGALURU 560068",
        "blur": 0.0,
        "jpg_quality": 92,
        "rotate": 0,
    },
    {
        "id": "ravi",
        "epic": "BIH7821093",
        "name": "RAVI KUMAR",
        "father": "SHYAM KUMAR",
        "dob": "08/11/1962",
        "gender": "MALE",
        "address": "12, OLD BYPASS, KANKARBAGH, PATNA 800020",
        "blur": 0.0,
        "jpg_quality": 92,
        "rotate": 0,
    },
    {
        "id": "priya",
        "epic": "TGS9912204",
        "name": "PRIYA REDDY",
        "father": "SURESH REDDY",
        "dob": "21/03/1996",
        "gender": "FEMALE",
        "address": "204-A, SR NAGAR MAIN RD, GOSHAMAHAL, HYDERABAD 500001",
        "blur": 1.2,  # light blur — DOCUMENT mode should still cope
        "jpg_quality": 88,
        "rotate": 0,
    },
    {
        "id": "dedup_a",
        "epic": "DUP1112223",
        "name": "ANJALI VERMA",
        "father": "MANOJ VERMA",
        "dob": "15/06/1990",
        "gender": "FEMALE",
        "address": "78, PARK STREET, LUCKNOW CENTRAL, LUCKNOW 226001",
        "blur": 0.0,
        "jpg_quality": 92,
        "rotate": 0,
    },
    {
        "id": "dedup_b",
        "epic": "DUP4445556",
        "name": "ANJALI VERMA",
        "father": "MANOJ VERMA",
        "dob": "15/06/1990",
        "gender": "FEMALE",
        "address": "203, SAPRU MARG, HAZRATGANJ, LUCKNOW 226001",
        "blur": 0.0,
        "jpg_quality": 35,  # heavy JPEG noise
        "rotate": 3,        # slight rotation — exercises text_detection fallback
    },
]


def _font(size: int) -> ImageFont.FreeTypeFont:
    """Pick the first installed TrueType we can find. Avoids relying on
    any particular OS font path."""
    candidates = [
        # Windows
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\calibri.ttf",
        # macOS
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(p: dict) -> Path:
    img = Image.new("RGB", (CARD_W, CARD_H), PALE)
    d = ImageDraw.Draw(img)

    f_header = _font(28)
    f_label = _font(20)
    f_value = _font(34)
    f_epic = _font(56)
    f_small = _font(18)

    # Header band.
    d.rectangle([0, 0, CARD_W, HEADER_H], fill=ACCENT)
    d.text((24, 18), "ELECTION COMMISSION OF INDIA", fill=(255, 255, 255), font=f_header)
    d.text((24, 54), "VOTER PHOTO IDENTITY CARD", fill=(255, 240, 240), font=f_label)

    # Photo box (just an outline — no actual face, by design).
    photo_w, photo_h = 220, 280
    photo_x, photo_y = 40, HEADER_H + 32
    d.rectangle(
        [photo_x, photo_y, photo_x + photo_w, photo_y + photo_h],
        outline=INK, width=3, fill=(220, 220, 220),
    )
    d.text((photo_x + 60, photo_y + 130), "PHOTO", fill=INK, font=f_label)

    # EPIC number — large, top-right.
    d.text((300, HEADER_H + 28), "EPIC No.", fill=INK, font=f_label)
    d.text((300, HEADER_H + 56), p["epic"], fill=ACCENT, font=f_epic)

    # Field grid (left column under photo, right column).
    rows = [
        ("Name", p["name"]),
        ("Father's Name", p["father"]),
        ("Date of Birth", p["dob"]),
        ("Gender", p["gender"]),
    ]
    rx, ry = 300, HEADER_H + 150
    for i, (label, value) in enumerate(rows):
        y = ry + i * 70
        d.text((rx, y), label, fill=(90, 90, 90), font=f_label)
        d.text((rx, y + 24), value, fill=INK, font=f_value)

    # Address — wraps below.
    ax = 40
    ay = photo_y + photo_h + 24
    d.text((ax, ay), "Address", fill=(90, 90, 90), font=f_label)
    d.text((ax, ay + 24), p["address"], fill=INK, font=f_value)

    # Footer disclaimer (matches our trust-boundary copy).
    d.text(
        (24, CARD_H - 28),
        "SAMPLE — synthetic Sankalp test card (docs/DATA.md §4)",
        fill=(120, 120, 120), font=f_small,
    )

    if p["blur"] > 0:
        img = img.filter(ImageFilter.GaussianBlur(radius=p["blur"]))
    if p["rotate"]:
        img = img.rotate(p["rotate"], resample=Image.BICUBIC, fillcolor=PALE, expand=False)

    out = OUT_DIR / f"{p['id']}.jpg"
    img.save(out, "JPEG", quality=p["jpg_quality"], optimize=True)
    return out


def main() -> int:
    paths = []
    for p in PERSONAS:
        out = render(p)
        size_kb = out.stat().st_size / 1024
        paths.append((out, size_kb))
    print(f"Wrote {len(paths)} sample EPIC images to {OUT_DIR}:")
    for path, size in paths:
        print(f"  {path.name:14s}  {size:6.1f} KiB")
    print(f"  total: {sum(s for _, s in paths):.1f} KiB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
