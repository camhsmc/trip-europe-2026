# Cam & Kara — Europe 2026 PWA

Static photo-journal PWA for the April 2026 trip. Hosted on GitHub Pages from `docs/`.
Two parallel trips share the site:
- **Cam** — Normandy → grandpa's WWII sites (Aachen/Schevenhütte/Höfen) → Paris with dad, uncle Doug, brothers
- **Kara** — Saarland castle → Rhine Valley (Bacharach/Bingen/Rüdesheim) → Trier + Luxembourg → Paris

## Architecture
- Single-file vanilla JS/HTML/CSS (`docs/index.html`) — no framework, no build step
- Map: Leaflet 1.9.4 + CartoDB dark tiles (with sepia CSS filter for warmth)
- Data: `docs/data/itinerary.json` + `docs/data/photos.json`
- Photos: full + thumbs in Supabase Storage bucket `trip-photos` (project `optzbdbavpnxstpxrpbh`); thumbs also committed to `docs/photos/thumbs/` for fast first paint
- Originals (HEIC/JPG/PNG) in `originals/` — gitignored

## Key data conventions
- `photos[].photographer = "Kara"` marks her trip's photos. Polyline-split rule: `photographer === "Kara" && category !== "paris"` → Kara's separate Germany line; everything else → main line. Joint Paris days merge into one line by design.
- `itinerary[].trip = "kara"` marks Kara's day cards (days 102–105). Cam uses days 1–8.
- Day cards carry `data-trip` and `data-date` for filtering.
- Clicking a day pill or card → hide other-date cards in both sections, plot all photos for that date.
- Clicking a section header (Cam / Kara) → zoom map to just that trip's photos, scoped to the current day if one is selected. Left panel state preserved.

## Current state (2026-04-25)
- 163 photos (136 Cam, 27 Kara), 12 itinerary entries (8 Cam + 4 Kara: Saarland, Rhine, Trier, Luxembourg)
- Captions are read-only (no in-page editing)
- Warm sepia/dusk palette
- Polyline arrows tried + removed (didn't render cleanly)

## Adding photos
1. Drop originals into `originals/`
2. Use a one-shot processor script in `scripts/` (see `add-batch2-photos.py` as the most recent template) — converts via `sips`, uploads to Supabase, appends entries to `photos.json`
3. Get Supabase service key from `~/.secrets.md` → `SUPABASE_SERVICE_KEY` env var
4. Commit thumbs + json + script

## Known quirks
- `mdls`-extracted UTC timestamps are ~7h offset from actual UTC (Spotlight oddity); display layer adds another `TRIP_OFFSET_HOURS = 2`. Existing photos all use the same convention so relative ordering is correct, but the absolute clock time shown in the lightbox is not real-world correct. Not fixed — leave alone unless Cam asks.
- IMG_6556 (Kara, 4/18) is tagged as Bacharach per Cam's confirmation, even though that day was mainly Trier + Luxembourg. Plotted at Bacharach coords.

## Recent session — 2026-04-25
- Added Kara's 13 photos (first batch) + tagged them; split her Germany route from Cam's main route
- Fixed IMG_0890 (was mislabeled "Arc de Triomphe" — actually the Catacombs; GPS was wrong because phone lost signal underground)
- Built Cam/Kara sections in left panel with blurbs
- Warmed the palette (sepia/dusk) and locked captions to read-only
- Added click-day-to-focus (hides other-date cards, shows both trips' cards if both have content for that date)
- Added clickable section headers that zoom the map to one trip's photos (respects current day)
- Added 15 more photos (10 PXL from Kara's Pixel + 5 IMG from her roommate's iPhone)
- Added Luxembourg City as a separate Kara day card (day 105, 4/18)
- Tried directional arrowheads on polylines, then removed them
