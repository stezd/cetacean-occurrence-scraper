# 01_occurrences - fetch, verify, and thin occurrences

One job: assemble cleaned, seasonally tagged (`NWM`, `TR1`, `SEM`, `TR2`), and 10 km spatially thinned whale shark (*Rhincodon typus*, `taxonKey=2417522`, `2010–2026`) occurrence records and 25 km KDE bias backgrounds for Indonesia (`ID`) and Australia (`AU`).

## Inputs
- Reference (every run): `../../PROJECT_OVERVIEW.md`
- Reference (every run): `../../_shared/occurrence-pipeline-spec.md`
- Reference (every run): `../../_shared/codebase-conventions.md`
- Reference (every run): `../../fetch_gbif_cetaceans.py`
- Raster (land mask & ocean cells): `../../data/gebco/gebco_2026_indopacific_90E_160E_40S_20N.nc` (GEBCO_2026 subset `90E–160E, 40S–20N`; see `../../data/gebco/SOURCE.md`)

Do NOT load: `../../literature/`, `../../ipb-thesis-latex/`, or `../../_archive/`.

## Process
1. If any Reference input above is missing, stop and report which file is missing.
2. Fetch open repository records (`2010–2026`, `hasCoordinate=true`, `hasGeospatialIssue=false`, `taxonKey=2417522`) from GBIF and OBIS for `ID` (target domain) and `AU` (source domain), or pass `--from-raw` to rebuild from `raw/*.jsonl`.
3. Merge social-media sighting records verified as `status_verifikasi = valid` by **Pembimbing 2 (Dosen FPIK IPB)**; quarantine unverified or rejected rows in `output/quarantine.csv`.
4. Apply the cleaning rules in [occurrence-pipeline-spec.md](../../_shared/occurrence-pipeline-spec.md) before deduplication: remove land points using GEBCO `elevation >= 0` m (negative below sea level) plus secondary OBIS `ON_LAND` / `bathymetry <= 0` / `marine=False` checks (`on_land`), coordinate uncertainty `> 10000` m, museum/fossil specimens, and cross-source duplicates `(round(lat, 4), round(lon, 4), event_date)`.
5. Partition by monsoon season (`NWM` Dec–Feb, `TR1` Mar–May, `SEM` Jun–Aug, `TR2` Sep–Nov) and run `10 km` haversine spatial thinning per domain × season.
6. Sample `10,000` bias-corrected ocean-only (`GEBCO elevation < 0` m) background points per domain (`ID`, `AU`) from a `25 km` isotropic 2D Gaussian KDE built from that domain's clean presence points with a seeded RNG (`--background-seed`, default `20261114`).

## Outputs
- `output/rhincodon_id_clean.csv` and `output/rhincodon_au_clean.csv`
- `output/rhincodon_<domain>_<season>.csv` (10 km thinned presence slices)
- `output/background_id.csv` and `output/background_au.csv` (10,000 25 km KDE ocean background points per domain)
- `output/quarantine.csv` (rejected rows with reason codes)
- `output/check.md` (stage verification report)

## Check
Run `.venv\Scripts\python.exe -I stages/01_occurrences/run_stage01.py --from-raw` and write `output/check.md` with first line `pass` or `fail: <why>`. `pass` requires:
1. Zero rows with `taxonKey != 2417522`, missing coordinates, or `year < 2010`.
2. Zero unverified social-media rows (`status_verifikasi != valid`) in the cleaned outputs, and verified social-media stream loaded.
3. GEBCO raster land mask applied (`0` clean rows with GEBCO `elevation >= 0` m).
4. Minimum pairwise haversine distance `>= 10.0 km` within every `<domain>_<season>` thinned file.
5. `10,000` 25 km KDE background points per domain (`ID`, `AU`), all strictly on ocean cells (`GEBCO elevation < 0` m).
6. Pre/post-thinning counts, land-mask breakdown, background summary, and SHA-256 checksums recorded in `output/check.md`.
