# Stage 01 Social Media Tooling (Stream 2 & Stream 3)

This package collects public opportunistic whale shark (*Rhincodon typus*, `taxonKey=2417522`) sightings and manages Pembimbing 2's verification workflow before records enter [run_stage01.py](../run_stage01.py).

## Components

- [scraper.py](scraper.py): CLI for append-only raw JSONL capture from public YouTube Data API v3 (`YOUTUBE_API_KEY` env var) and public RSS/Atom/WP-JSON feeds (robots.txt enforced, throttled), plus documented stubs and export importers for `instagram`, `tiktok`, and `x`.
- [sheet_converter.py](sheet_converter.py): Converts raw JSONL to an unverified UTF-8-BOM sheet and validates Pembimbing 2's reviewed CSV into `stages/01_occurrences/input/social_media_verified.csv`.
- [verification_sheet_template.csv](verification_sheet_template.csv): Empty UTF-8-BOM verification template matching [PROJECT_OVERVIEW.md](../../../PROJECT_OVERVIEW.md) Section 2.A and `normalize_social_media_row()`.
- [README_VERIFIKASI.md](README_VERIFIKASI.md): Bahasa Indonesia baku verification guide for Pembimbing 2.
- [test_social_media.py](test_social_media.py): Offline unit tests and end-to-end round-trip check against `run_stage01.py`.

## Quick Usage

```powershell
# 1. Collect public RSS/news (capped requests, throttled, robots.txt checked)
.venv\Scripts\python.exe -I stages\01_occurrences\social_media\scraper.py --sources rss --max-requests 10

# 2. Or collect YouTube metadata (requires YOUTUBE_API_KEY in environment or .env)
.venv\Scripts\python.exe -I stages\01_occurrences\social_media\scraper.py --sources youtube --max-queries 2 --max-results 5

# 3. Inspect or import manual/official-API export for Instagram, TikTok, or X
.venv\Scripts\python.exe -I stages\01_occurrences\social_media\scraper.py --show-stub-spec instagram

# 4. Generate unverified CSV for Pembimbing 2
.venv\Scripts\python.exe -I stages\01_occurrences\social_media\sheet_converter.py jsonl-to-sheet

# 5. Validate reviewed CSV and write stages/01_occurrences/input/social_media_verified.csv
.venv\Scripts\python.exe -I stages\01_occurrences\social_media\sheet_converter.py validate --in-csv <reviewed.csv>
```
