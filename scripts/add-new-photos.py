#!/usr/bin/env python3
"""
One-shot: convert + upload + JSON-append the 13 newly-added originals.
Idempotent — skips conversions/uploads that already exist for these IDs only.
"""
import json
import os
import subprocess
import sys
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

# id, day, date, category, location, caption
ENTRIES = [
    ("IMG_0821", 2, "2026-04-16", "travel",       "Saarland, Germany",     "Saarland — westbound on the autobahn"),
    ("IMG_0823", 3, "2026-04-17", "travel",       "Boppard, Rhine Valley", "Rhine Valley pit stop near Boppard"),
    ("IMG_0832", 3, "2026-04-17", "travel",       "Bingen am Rhein",       "Bingen on the Rhine"),
    ("IMG_0834", 3, "2026-04-17", "travel",       "Rüdesheim am Rhein",    "Rüdesheim am Rhein"),
    ("IMG_0836", 3, "2026-04-17", "travel",       "Rüdesheim am Rhein",    "Vines above Rüdesheim"),
    ("IMG_0838", 3, "2026-04-17", "travel",       "Rüdesheim am Rhein",    "Rüdesheim riverside"),
    ("IMG_0847", 3, "2026-04-17", "travel",       "Hessen countryside",    "Hessen on the way to Aachen"),
    ("IMG_0858", 4, "2026-04-18", "travel",       "Trier",                 "Porta Nigra, Trier"),
    ("IMG_0864", 4, "2026-04-18", "travel",       "Trier",                 "Wandering Trier"),
    ("IMG_0873", 6, "2026-04-20", "paris",        "Île de la Cité",        "Notre-Dame from across the Seine"),
    ("IMG_0879", 7, "2026-04-21", "paris",        "Le Marais",             "Marais streets"),
    ("IMG_0889", 7, "2026-04-21", "paris",        "Arc de Triomphe",       "Arc de Triomphe"),
    ("IMG_0890", 7, "2026-04-21", "paris",        "Arc de Triomphe",       "Arc de Triomphe up close"),
]


def mdls_field(path: Path, key: str) -> str:
    out = subprocess.check_output(["mdls", "-name", key, "-raw", str(path)], text=True)
    return out.strip()


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
            body = f.read()
        sys.exit(f"Upload failed for {remote_path}: HTTP {code}: {body}")


def main():
    with open(JSON_FILE) as f:
        photos = json.load(f)
    existing_ids = {p["id"] for p in photos}

    new_entries = []
    for pid, day, date, category, location, caption in ENTRIES:
        src = ORIG / f"{pid}.HEIC"
        if not src.exists():
            sys.exit(f"missing original: {src}")

        full_jpg = FULL / f"{pid}.jpg"
        thumb_jpg = THUMB / f"{pid}.jpg"
        print(f"[{pid}] converting…")
        convert(src, full_jpg, 1920)
        convert(src, thumb_jpg, 400)

        print(f"[{pid}] uploading…")
        upload(full_jpg, f"full/{pid}.jpg")
        upload(thumb_jpg, f"thumbs/{pid}.jpg")

        if pid in existing_ids:
            print(f"[{pid}] already in photos.json, skipping JSON append")
            continue

        # EXIF
        lat = float(mdls_field(src, "kMDItemLatitude"))
        lng = float(mdls_field(src, "kMDItemLongitude"))
        ts_raw = mdls_field(src, "kMDItemContentCreationDate")  # "2026-04-16 20:35:18 +0000"
        ts = ts_raw.replace(" +0000", "Z").replace(" ", "T")

        new_entries.append({
            "id": pid,
            "filename": f"{pid}.HEIC",
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
            "photographer": "",
        })

    if new_entries:
        photos.extend(new_entries)
        photos.sort(key=lambda p: p["timestamp"])
        with open(JSON_FILE, "w") as f:
            json.dump(photos, f, indent=2)
        print(f"\nAppended {len(new_entries)} entries; photos.json now has {len(photos)} total.")
    else:
        print("\nNo new JSON entries needed.")


if __name__ == "__main__":
    main()
