#!/bin/bash
# ============================================================
# Process photos: HEIC/PNG/JPEG → web-ready JPEGs + thumbnails
# Then upload to Supabase Storage
# ============================================================
# Usage: ./process-photos.sh
# Prerequisites: sips (macOS built-in), curl
# ============================================================

ORIGINALS_DIR="../originals"
OUTPUT_DIR="../docs/photos"
FULL_DIR="$OUTPUT_DIR/full"
THUMB_DIR="$OUTPUT_DIR/thumbs"
JSON_FILE="../docs/data/photos.json"

# Supabase config
SUPABASE_PROJECT="optzbdbavpnxstpxrpbh"
SUPABASE_URL="https://${SUPABASE_PROJECT}.supabase.co"
BUCKET="trip-photos"

# You'll need to set this — get it from Supabase dashboard → Settings → API → service_role key
SUPABASE_KEY="${SUPABASE_SERVICE_KEY:-}"

# ============================================================
# Step 1: Convert to JPEG
# ============================================================
echo "=== Step 1: Converting to JPEG ==="
mkdir -p "$FULL_DIR" "$THUMB_DIR"

count=0
shopt -s nullglob nocaseglob
total=$(ls "$ORIGINALS_DIR"/*.{HEIC,JPEG,JPG,PNG} 2>/dev/null | wc -l | tr -d ' ')

for f in "$ORIGINALS_DIR"/*.{HEIC,JPEG,JPG,PNG}; do
  [ -f "$f" ] || continue
  fname=$(basename "$f")
  base="${fname%.*}"
  outfile="$FULL_DIR/${base}.jpg"
  thumbfile="$THUMB_DIR/${base}.jpg"

  count=$((count + 1))

  if [ -f "$outfile" ]; then
    echo "[$count/$total] Skip (exists): $base.jpg"
    continue
  fi

  echo "[$count/$total] Converting: $fname → $base.jpg"

  # Convert to JPEG, max 1920px on longest side
  sips -s format jpeg -Z 1920 "$f" --out "$outfile" > /dev/null 2>&1

  # Generate thumbnail, max 400px
  sips -s format jpeg -Z 400 "$f" --out "$thumbfile" > /dev/null 2>&1
done

echo "=== Conversion complete: $count files ==="

# ============================================================
# Step 2: Upload to Supabase Storage
# ============================================================
if [ -z "$SUPABASE_KEY" ]; then
  echo ""
  echo "=== Step 2: SKIPPED (no SUPABASE_SERVICE_KEY set) ==="
  echo "To upload, run:"
  echo "  export SUPABASE_SERVICE_KEY='your-service-role-key'"
  echo "  ./process-photos.sh"
  exit 0
fi

echo ""
echo "=== Step 2: Uploading to Supabase Storage ==="

# Upload full-size photos
for f in "$FULL_DIR"/*.jpg; do
  fname=$(basename "$f")
  echo "Uploading full/$fname..."
  code=$(curl -s -o /tmp/upload_resp -w "%{http_code}" -X POST \
    "${SUPABASE_URL}/storage/v1/object/${BUCKET}/full/${fname}" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Content-Type: image/jpeg" \
    -H "x-upsert: true" \
    --data-binary @"$f")
  if [ "$code" != "200" ]; then echo "  FAILED HTTP $code: $(cat /tmp/upload_resp)"; fi
done

# Upload thumbnails
for f in "$THUMB_DIR"/*.jpg; do
  fname=$(basename "$f")
  echo "Uploading thumbs/$fname..."
  code=$(curl -s -o /tmp/upload_resp -w "%{http_code}" -X POST \
    "${SUPABASE_URL}/storage/v1/object/${BUCKET}/thumbs/${fname}" \
    -H "apikey: ${SUPABASE_KEY}" \
    -H "Content-Type: image/jpeg" \
    -H "x-upsert: true" \
    --data-binary @"$f")
  if [ "$code" != "200" ]; then echo "  FAILED HTTP $code: $(cat /tmp/upload_resp)"; fi
done

echo ""
echo "=== Step 3: Updating photos.json with URLs ==="

# Update photos.json with Supabase URLs
python3 << PY
import json

with open("$JSON_FILE") as f:
    photos = json.load(f)

base_url = "${SUPABASE_URL}/storage/v1/object/public/${BUCKET}"

for p in photos:
    jpg = p["jpg"]
    p["url"] = f"{base_url}/full/{jpg}"
    p["thumb_url"] = f"{base_url}/thumbs/{jpg}"

with open("$JSON_FILE", "w") as f:
    json.dump(photos, f, indent=2)

print(f"Updated {len(photos)} photo URLs")
PY

echo "=== All done! ==="
