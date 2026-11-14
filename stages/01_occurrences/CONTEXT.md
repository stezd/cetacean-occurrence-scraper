# 01_occurrences - fetch, verify, and thin occurrences

One job: assemble cleaned, seasonally tagged (`NWM`, `TR1`, `SEM`, `TR2`), and 10 km spatially thinned whale shark (*Rhincodon typus*, `taxonKey=2417522`, `2010–2026`) occurrence records and 25 km KDE bias backgrounds for Indonesia (`ID`) and Australia (`AU`).

## Inputs
- Reference (every run): `../../PROJECT_OVERVIEW.md`
- Reference (every run): `../../_shared/occurrence-pipeline-spec.md`
- Reference (every run): `../../_shared/codebase-conventions.md`
- Reference (every run): `../../fetch_gbif_cetaceans.py`

Do NOT load: `../../literature/`, `../../ipb-thesis-latex/`, or `../../_archive/`.

## Process
1. If any Reference input above is missing, stop and report which file is missing.
2. Fetch open repository records (`2010–2026`, `hasCoordinate=true`, `hasGeospatialIssue=false`, `taxonKey=2417522`) from GBIF and OBIS for `ID` (target domain) and `AU` (source domain).
3. Merge social-media sighting records verified as `status_verifikasi = valid` by **Pembimbing 2 (Dosen FPIK IPB)**; quarantine unverified or rejected rows in `output/quarantine.csv`.
4. Apply the 8-stage cleaning rules in [occurrence-pipeline-spec.md](../../_shared/occurrence-pipeline-spec.md): remove land points (`depth >= 0` m), coordinate uncertainty `> 10000` m, museum/fossil specimens, and cross-source duplicates `(round(lat, 4), round(lon, 4), event_date)`.
5. Partition by monsoon season (`NWM` Dec–Feb, `TR1` Mar–May, `SEM` Jun–Aug, `TR2` Sep–Nov) and run `10 km` haversine spatial thinning per domain × season.

## Outputs
- `output/rhincodon_id_clean.csv` and `output/rhincodon_au_clean.csv`
- `output/rhincodon_<domain>_<season>.csv` (10 km thinned presence slices)
- `output/quarantine.csv` (rejected rows with reason codes)
- `output/check.md` (stage verification report)

## Check
Run the stage audit and write `output/check.md` with first line `pass` or `fail: <why>`. `pass` requires:
1. Zero rows with `taxonKey != 2417522`, missing coordinates, or `year < 2010`.
2. Zero unverified social-media rows (`status_verifikasi != valid`) in the cleaned outputs.
3. Minimum pairwise haversine distance `>= 10.0 km` within every `<domain>_<season>` thinned file.
4. Pre/post-thinning counts per domain (`ID`, `AU`), stream (`gbif`, `obis`, `social_media_verified`), and season (`NWM`, `TR1`, `SEM`, `TR2`) recorded with SHA-256 checksums.
