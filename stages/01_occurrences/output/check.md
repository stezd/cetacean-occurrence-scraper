fail: open-repo GBIF+OBIS fetch/clean/GEBCO-mask/10km-thinning/25km-KDE-background passed, but Pembimbing 2 verified social_media_verified CSV not yet supplied

Generated: 2026-11-14T14:41:55+07:00

## Integrity Checks
- Rows with taxonKey != 2417522: 0
- Rows with missing coordinates: 0
- Rows with year < 2010: 0
- Unverified social-media rows in clean output: 0
- Thinned slices with min pairwise distance < 10.0 km: 0
- Clean rows with GEBCO elevation >= 0 m: 0
- GEBCO raster land mask: APPLIED (`gebco_2026_indopacific_90E_160E_40S_20N.nc`; elevation >= 0 m quarantined as `on_land`; OBIS-flagged=20, GEBCO-extra=502, total=522)
- 25 km Gaussian KDE ocean background: APPLIED (ID=10000, AU=10000; 0 on land; bandwidth=25.0 km; seed=20261114)
- Social-media verified stream loaded: NO (0 rows)

## Counts by Domain & Source Stream (Raw -> Clean Post-Dedupe)
| Domain | Stream | Raw | Clean (Post-Dedupe) |
|---|---|---:|---:|
| ID | gbif | 573 | 400 |
| ID | obis | 194 | 0 |
| ID | social_media_verified | 0 | 0 |
| AU | gbif | 7892 | 5765 |
| AU | obis | 2948 | 8 |
| AU | social_media_verified | 0 | 0 |

## Land Mask Breakdown (Pre-Dedupe)
| Domain | OBIS Only | Both OBIS & GEBCO | GEBCO Extra | Total `on_land` |
|---|---:|---:|---:|---:|
| ID | 1 | 1 | 31 | 33 |
| AU | 5 | 13 | 471 | 489 |

## Seasonal Thinning (10 km Haversine)
| Domain | Season | Pre-Thin | Post-Thin (10 km) | Min Pairwise km | Output File |
|---|---|---:|---:|---:|---|
| ID | NWM | 14 | 7 | 10.31 | `rhincodon_id_nwm.csv` |
| ID | TR1 | 92 | 40 | 10.14 | `rhincodon_id_tr1.csv` |
| ID | SEM | 40 | 19 | 11.42 | `rhincodon_id_sem.csv` |
| ID | TR2 | 254 | 88 | 10.20 | `rhincodon_id_tr2.csv` |
| AU | NWM | 1735 | 365 | 10.01 | `rhincodon_au_nwm.csv` |
| AU | TR1 | 766 | 157 | 10.11 | `rhincodon_au_tr1.csv` |
| AU | SEM | 1563 | 317 | 10.02 | `rhincodon_au_sem.csv` |
| AU | TR2 | 1632 | 357 | 10.03 | `rhincodon_au_tr2.csv` |
- `ID` `UNKNOWN`-season clean rows (excluded from seasonal slices): 0
- `AU` `UNKNOWN`-season clean rows (excluded from seasonal slices): 77

## Bias-Corrected Background Points (25 km Gaussian KDE, Ocean Cells Only)
| Domain | Clean Presences (KDE Input) | Background Points | On-Land Points | Min Elev (m) | Max Elev (m) | Seed | Output File |
|---|---:|---:|---:|---:|---:|---:|---|
| ID | 400 | 10000 | 0 | -7167 | -1 | 20261114 | `background_id.csv` |
| AU | 5773 | 10000 | 0 | -5959 | -1 | 20261115 | `background_au.csv` |

## Quarantine Breakdown
- Total quarantined rows: 5434
| Reason | Count |
|---|---:|
| `duplicate_cross_source` | 4189 |
| `high_uncertainty` | 547 |
| `on_land` | 522 |
| `date_range_not_date` | 172 |
| `not_observation` | 4 |

## Output SHA-256 Checksums
| File | SHA-256 |
|---|---|
| `background_au.csv` | `a98784182ce2061a7ff0923746ca6bfaffa84542ae92a990009b88d76ad72253` |
| `background_id.csv` | `a4480a95294c57e9fb0a39d5bcaf81d6ae23fe03f40c0a8f77a835438d3ba78d` |
| `quarantine.csv` | `6145154083322095b37b6a872cac089efe5dda46b34ecfd4162ed9f9eebec0af` |
| `rhincodon_au_clean.csv` | `b7f3be876fa2fef9b3a96020d3a6b5d2fb24300acfc89f69abd3e6feda59ed10` |
| `rhincodon_au_nwm.csv` | `519813e3ad0d52b0c296ddbf06f7b6ed67830fe143d65c5ce4283805c1451ad1` |
| `rhincodon_au_sem.csv` | `b673bea50d3977348456fa5f3153fe4273c49ca468a181a2eddfb280dc8940c2` |
| `rhincodon_au_tr1.csv` | `f68eb061f413e9dd3817a526ca3e5f0618bf6a91aa8c7cc5157096ab00a6a9b0` |
| `rhincodon_au_tr2.csv` | `0515fef0fd9b36b8d36f57afefae34aa6219743667bbd626f1dfdf3d57b26ad6` |
| `rhincodon_id_clean.csv` | `cbf4bac0765bde1ac7ba9f22ce94161e44348d681f6a3309412235f0764c998d` |
| `rhincodon_id_nwm.csv` | `7eccf2993c909f6d47faa00614b5eea63bb47610db3c6a4d3ddb9317600f5264` |
| `rhincodon_id_sem.csv` | `1b25a598660367a5c27279a92c3da099fd334dbb5588bb49525679ef9059dff1` |
| `rhincodon_id_tr1.csv` | `73a4466a9bbe75afb8053867c146eb7c394a46406697030c43d1543b55e2ef71` |
| `rhincodon_id_tr2.csv` | `d3fa91273965d67928420e34b334f16009cd63166ed080de255672ff78295215` |
