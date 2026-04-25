#!/usr/bin/env python3
"""Process batch 2: 5 IMG_*.HEIC + 10 PXL_*.jpg from Kara's roommate group."""
import json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORIG = ROOT / "originals"
FULL = ROOT / "docs" / "photos" / "full"
THUMB = ROOT / "docs" / "photos" / "thumbs"
JSON_FILE = ROOT / "docs" / "data" / "photos.json"

SUPABASE_PROJECT = "optzbdbavpnxstpxrpbh"
BUCKET = "trip-photos"
BASE_URL = f"https://{SUPABASE_PROJECT}.supabase.co/storage/v1/object/public/{BUCKET}"
UPLOAD_URL = f"https://{SUPABASE_PROJECT}.supabase.co/storage/v1/object/{BUCKET}"

KEY = os.environ.get("SUPABASE_SERVICE_KEY")
if not KEY:
    sys.exit("SUPABASE_SERVICE_KEY not set")

# (orig_filename, photo_id, day, date, category, location, lat, lng, caption)
ENTRIES = [
    ("PXL_20260416_130413408.BURST-01.jpg", "PXL_20260416_130413", 102, "2026-04-16", "travel", "Saarland, Germany",       49.348875, 7.757487, "Saarland castle area"),
    ("PXL_20260416_130923963.jpg",          "PXL_20260416_130923", 102, "2026-04-16", "travel", "Saarland, Germany",       49.350362, 7.756905, "Saarland castle"),
    ("PXL_20260416_133347416.BURST-01.jpg", "PXL_20260416_133347", 102, "2026-04-16", "travel", "Saarland, Germany",       49.354283, 7.753545, "Saarland castle"),
    ("IMG_6448.HEIC",                       "IMG_6448",            102, "2026-04-16", "travel", "Saarland, Germany",       49.354,    7.753,    "Castle ruins, Saarland"),
    ("PXL_20260416_184204313.jpg",          "PXL_20260416_184204", 102, "2026-04-16", "travel", "Kaiserslautern area",     49.499488, 7.601913, "Kaiserslautern, evening"),
    ("PXL_20260417_112148351.BURST-01.jpg", "PXL_20260417_112148", 103, "2026-04-17", "travel", "Bacharach, Rhine Valley", 50.081197, 7.764267, "Bikes at Bacharach"),
    ("IMG_6472.HEIC",                       "IMG_6472",            103, "2026-04-17", "travel", "Bacharach, Rhine Valley", 50.058,    7.769,    "Bacharach on the Rhine"),
    ("PXL_20260417_132405303.BURST-01.jpg", "PXL_20260417_132405", 103, "2026-04-17", "travel", "Rüdesheim am Rhein",      49.993458, 7.858630, "Rüdesheim"),
    ("PXL_20260418_100857912.BURST-01.jpg", "PXL_20260418_100857", 104, "2026-04-18", "travel", "Trier",                   49.752062, 6.643017, "Trier"),
    ("IMG_6556.HEIC",                       "IMG_6556",            104, "2026-04-18", "travel", "Bacharach, Rhine Valley", 50.058,    7.769,    "Bacharach"),
    ("PXL_20260418_141337034.jpg",          "PXL_20260418_141337", 105, "2026-04-18", "travel", "Luxembourg City",         49.608745, 6.133697, "Luxembourg City"),
    ("PXL_20260420_111828031.BURST-01.jpg", "PXL_20260420_111828", 6,   "2026-04-20", "paris",  "Le Marais",               48.861863, 2.334075, "Marais"),
    ("PXL_20260420_113057861.jpg",          "PXL_20260420_113057", 6,   "2026-04-20", "paris",  "Île de la Cité",          48.858155, 2.337378, "Near Notre-Dame"),
    ("IMG_0068.HEIC",                       "IMG_0068",            6,   "2026-04-20", "paris",  "Jardin du Luxembourg",    48.8467,   2.3372,   "Jardin du Luxembourg"),
    ("IMG_6729.HEIC",                       "IMG_6729",            7,   "2026-04-21", "paris",  "Arc de Triomphe",         48.8738,   2.295,    "Arc de Triomphe rooftop"),
]


def mdls_creation(path: Path) -> str:
    """Returns ISO Z timestamp matching the existing convention (mdls UTC value as-is)."""
    out = subprocess.check_output(
        ["mdls", "-name", "kMDItemContentCreationDate", "-raw", str(path)], text=True
    ).strip()
    # Format: "2026-04-16 20:35:18 +0000"
    return out.replace(" +0000", "Z").replace(" ", "T")


def convert(src: Path, dest: Path, max_dim: int):
    if dest.exists():
        return
    subprocess.run(
        ["sips", "-s", "format", "jpeg", "-Z", str(max_dim), str(src), "--out", str(dest)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def upload(local: Path, remote_path: str):
    code = subprocess.check_output([
        "curl", "-s", "-o", "/tmp/upload_resp", "-w", "%{http_code}",
        "-X", "POST", f"{UPLOAD_URL}/{remote_path}",
        "-H", f"apikey: {KEY}",
        "-H", f"Authorization: Bearer {KEY}",
        "-H", "Content-Type: image/jpeg",
        "-H", "x-upsert: true",
        "--data-binary", f"@{local}",
    ], text=True).strip()
    if code != "200":
        with open("/tmp/upload_resp") as f:
            sys.exit(f"Upload failed for {remote_path}: HTTP {code}: {f.read()}")


def main():
    with open(JSON_FILE) as f:
        photos = json.load(f)
    existing_ids = {p["id"] for p in photos}

    new_entries = []
    for orig, pid, day, date, category, location, lat, lng, caption in ENTRIES:
        src = ORIG / orig
        if not src.exists():
            sys.exit(f"missing original: {src}")

        full_jpg = FULL / f"{pid}.jpg"
        thumb_jpg = THUMB / f"{pid}.jpg"
        print(f"[{pid}] convert + upload…")
        convert(src, full_jpg, 1920)
        convert(src, thumb_jpg, 400)
        upload(full_jpg, f"full/{pid}.jpg")
        upload(thumb_jpg, f"thumbs/{pid}.jpg")

        if pid in existing_ids:
            print(f"  already in JSON, skipping append")
            continue

        ts = mdls_creation(src)

        new_entries.append({
            "id": pid,
            "filename": orig,
            "jpg": f"{pid}.jpg",
            "url": f"{BASE_URL}/full/{pid}.jpg",
            "thumb_url": f"{BASE_URL}/thumbs/{pid}.jpg",
            "lat": lat,
            "lng": lng,
            "timestamp": ts,
            "date": date,
            "day": day,
            "category": category,
            "location": location,
            "caption": caption,
            "photographer": "Kara",
        })

    if new_entries:
        photos.extend(new_entries)
        photos.sort(key=lambda p: p["timestamp"])
        with open(JSON_FILE, "w") as f:
            json.dump(photos, f, indent=2)
        print(f"\nAppended {len(new_entries)} entries; photos.json now has {len(photos)} total.")


if __name__ == "__main__":
    main()
