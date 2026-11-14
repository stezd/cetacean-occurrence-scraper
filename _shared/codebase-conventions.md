# Codebase Conventions & Fetcher Contract

Factory reference for `whale-scraper` code, CLI contracts, CSV schemas, and environment traps. For research scope and locked modeling decisions, read [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md).

## Commands

```bash
# Setup
python -m venv .venv && .venv/Scripts/activate   # Windows; source .venv/bin/activate elsewhere
pip install -r requirements.txt

# Fetch occurrence data (country_code, max_records — both optional, default ID / 1500)
python fetch_gbif_cetaceans.py
python fetch_gbif_cetaceans.py AU 5000
python fetch_gbif_cetaceans.py PH 1000

# Verify markdown links and stage contracts across the workspace
python -I _tools/links.py
```

Output path for the legacy fetcher is **derived, not passed**: `data/cetaceans_<country_code_lowercase>.csv`. `data/cetaceans_id.csv` is a committed generated artifact of the initial Stage 0 *Cetacea* (`taxonKey=733`) exploration, not a hand-maintained source file. Re-running the fetcher overwrites it wholesale — there is no merge or dedupe step, so records that drop out of the GBIF query between runs will silently disappear.

There is no unit test suite, linter, formatter, or CI configuration in this repo. Verification of a pipeline stage means running its script and checking `output/check.md` (plus `python -I _tools/links.py` for documentation integrity).

## Architecture (`fetch_gbif_cetaceans.py`)

Single-script ETL:

`fetch_gbif_cetaceans.py` → paginate the GBIF occurrence REST API → normalize each record into a flat dict → write CSV.

- **Pagination contract:** The API is queried 100 records at a time by `offset`, bounded by `max_records`, stopping on `endOfRecords` or an empty `results` array. A network failure mid-pagination prints a warning and `break`s — it does **not** raise, so a partially-fetched CSV is written and looks like a successful run. The `data.get('count')` field in the progress line is GBIF's total match count and is not the number of records you will end up with.
- **Query filters:** `hasCoordinate=true`, `hasGeospatialIssue=false`, `taxonKey=733` (legacy *Cetacea* default; target species *Rhincodon typus* is `taxonKey=2417522`). `fetch_occurrences` already accepts `taxon_key`.
- **CSV schema contract (16 columns):** Column names come from `list(records[0].keys())`. Inserting or reordering keys changes the CSV header for downstream consumers:
  `gbif_id, scientific_name, species, family, country, latitude, longitude, coordinate_uncertainty_m, year, month, season, event_date, locality, basis_of_record, dataset_name, occurrence_url`
- **Season tagging (`determine_season`):** Buckets `month` into the four Indonesian monsoon slices (`NWM` Dec–Feb, `TR1` Mar–May, `SEM` Jun–Aug, `TR2` Sep–Nov), returning `UNKNOWN` when month is missing. These tags are the temporal slices the modeling stage groups by, so the boundary months are load-bearing.

## Dependencies & Credentials

- `requests` and `httpx` are listed in `requirements.txt` for upcoming scraping/environmental stages; `fetch_gbif_cetaceans.py` uses only the Python standard library.
- `.env` (untracked, gitignored) holds Copernicus Marine (CMEMS) and NASA Earthdata credentials, per `.env.example`, provisioned for Stage 02 (`02_predictors`).
