# Whale Shark (*Rhincodon typus*) Habitat Suitability Modeling

## 1. Project Background & Research Questions

### The Problem
- **Scope Pivot (Single Species):** Originally explored across Order *Cetacea* (`taxonKey=733`), the research scope is locked to a single focal species: **Whale Shark (*Rhincodon typus* / Hiu Paus, GBIF `taxonKey=2417522`, Class *Elasmobranchii*)**.
- **Data Deficiency & Sampling Bias in Indonesia:** Structured database records (GBIF/OBIS) for *Rhincodon typus* in Indonesian waters (`ID`) are sparse and heavily clustered around coastal lift-net (*bagan*) and tourism sites (Teluk Saleh, Botubarani/Gorontalo, Derawan/Talisayan, Teluk Cenderawasih, Probolinggo), whereas neighboring Australia (`AU`, especially Ningaloo Reef & Coral Sea) holds dense telemetry and survey records. Meanwhile, many real Indonesian encounters are posted opportunistically on social media by fishers, dive operators, and tourists.

### Locked Research Questions (Phase 1)
- **RQ1 (Cross-Regional Domain Adaptation):** Does combining dense Australian (`AU`) source records with sparse Indonesian (`ID`) target records via **Kernel Mean Matching (KMM) instance-weighted domain adaptation** improve spatial block cross-validation accuracy (CBI, AUC-ROC, TSS) across Indonesian waters compared to an Indonesia-only baseline and naive unadapted transfer ($\text{AU} \rightarrow \text{ID}$)?
- **RQ2 (Expert-Verified Citizen Science):** Does augmenting open repository records (GBIF + OBIS) with social-media sightings verified by a marine science domain expert (**Pembimbing 2 — Dosen FPIK IPB**) expand environmental niche coverage and reduce clamping/extrapolation uncertainty (MESS)?

---

## 2. Research Architecture & Locked Methodology

### A. Occurrence Data ($y$) & Bias Correction (`stages/01_occurrences/`)
1. **Target Taxon & Temporal Window:** *Rhincodon typus* (GBIF `taxonKey=2417522`), filtered to **`2010–2026`** (`coordinateUncertaintyInMeters <= 10000` m, land points `depth >= 0` m removed, fossil/museum specimens excluded).
   - *Historical baseline (superseded Stage 0 exploration):* Order *Cetacea* (`taxonKey=733`, 951 raw ID records in `data/cetaceans_id.csv`).
2. **Three Occurrence Streams:**
   - **Stream 1 — Open Biodiversity Repositories:** Georeferenced occurrence and tracking records from GBIF (`taxonKey=2417522`) and OBIS across Indonesia (`ID`, target domain) and Australia (`AU`, source domain).
   - **Stream 2 — Social Media Scraping:** Opportunistic Indonesian sightings scraped from Instagram, TikTok, YouTube, X, and local news/dive reports, with media archived locally.
   - **Stream 3 — Expert Verification (Pembimbing 2, Dosen FPIK IPB):** Scraped sightings are reviewed by Pembimbing 2 via a structured verification sheet + local media bundle. Only rows marked `status_verifikasi = valid` enter spatial thinning and model calibration:

   | Group | Columns |
   | --- | --- |
   | **Evidence (scraped)** | `sighting_id`, `platform`, `post_url`, `local_media_path`, `caption_raw` |
   | **When (extracted)** | `post_date`, `sighting_date`, `month`, `season` (`NWM`/`TR1`/`SEM`/`TR2`) |
   | **Where (estimated)** | `locality_text`, `lat_est`, `lon_est`, `coord_uncertainty_km` |
   | **Pembimbing 2 Observation** | `status_verifikasi` (`valid` / `repost` / `ragu` / `tolak`), `lat_koreksi`, `lon_koreksi`, `jumlah_individu`, `perilaku_konteks` (feeding, bagan, wisata, melintas), `catatan_dosen` |

3. **Seasonal Temporal Slices (Indonesian Monsoon Cycles):**
   - **NWM (Northwest Monsoon / Musim Barat):** December – February
   - **TR1 (Transition 1 / Peralihan I):** March – May
   - **SEM (Southeast Monsoon / Musim Timur):** June – August
   - **TR2 (Transition 2 / Peralihan II):** September – November
4. **Spatial Thinning & Background Sampling:**
   - **Spatial Thinning:** **`10 km` haversine distance** per domain $\times$ season (matching 1 grid cell of the `1/12°` $\approx 9.2\text{ km}$ environmental raster).
   - **Bias-Corrected Pseudo-Absences:** 10,000 background points per domain sampled via a **2D Gaussian Kernel Density Estimation (KDE) surface (`bandwidth = 25 km`)** built from regional target-group marine megafauna and whale shark sightings.

### B. Environmental Predictors ($X$) (`stages/02_predictors/`)
Common grid: **`1/12°` ($\approx 9.2\text{ km}$)**. Dynamic layers are aggregated by matching monsoon season (`NWM`, `TR1`, `SEM`, `TR2`):
- **Dynamic Surface Physics (CMEMS Global Ocean Physics Reanalysis `GLOBAL_MULTIYEAR_PHY_001_030`):**
  - `thetao_mean`: Sea Surface Temperature (°C, surface 0.5 m)
  - `zos_mean`: Sea Surface Height Above Geoid (m) — geostrophic currents, eddies, and upwelling
- **Dynamic Surface Biogeochemistry (CMEMS `GLOBAL_MULTIYEAR_BGC_001_029`, resampled `1/4°` $\rightarrow$ `1/12°`):**
  - `chl_mean`: Mass concentration of chlorophyll-a ($\text{mg/m}^3$) — phytoplankton proxy
  - `nppv_mean`: Net Primary Production ($\text{mg C/m}^3\text{/day}$) — zooplanktivorous foraging proxy
- **Static Bathymetry & Topography (GEBCO, aggregated to `1/12°`):**
  - `depth`: Seafloor elevation (m)
  - `slope`: Seafloor inclination (°) — shelf-break upwelling proxy
  - `distance_0`: Distance to shoreline (km)
  - `distance_200`, `distance_300`, `distance_500`: Distance to 200 m, 300 m, and 500 m isobaths (km)
- **Collinearity Pruning:** Pairwise Spearman $|r| < 0.75$ and **$\text{VIF} \le 5$** (dropping redundant distance contours if correlated with `depth`/`distance_0`, and dropping `nppv_mean` if collinear with `chl_mean`).
- *Note on `tob_mean` (seafloor bottom temperature):* Omitted for epipelagic filter-feeding *Rhincodon typus* because bottom temperature in deep Indonesian basins (Banda/Weber trenches $>4,000\text{ m}$) reflects abyssal water rather than surface feeding habitat.

### C. Modeling, Domain Adaptation & Validation (`stages/03_modeling/`)
- **Three Algorithms:**
  1. **MaxEnt** (ecological baseline + built-in **MESS** environmental clamping map)
  2. **XGBoost** (gradient-boosted trees Supporting KMM sample weights + SHAP explanations)
  3. **Random Forest** (bagged ensemble baseline supporting KMM sample weights)
- **Three-Way Ablation Design:**
  - *Baseline 1 (ID-Only):* Trained strictly on Indonesian records (`GBIF + OBIS` vs. `GBIF + OBIS + Verified Social Media`).
  - *Baseline 2 (Naive Transfer $\text{AU} \rightarrow \text{ID}$):* Trained on unweighted Australian records and projected onto Indonesia.
  - *Proposed (KMM Domain Adaptation $\text{AU} + \text{ID} \rightarrow \text{ID}$):* Instance-weighted **Kernel Mean Matching (KMM)** aligning Australian source covariate density to the Indonesian target domain, combined with weighted Indonesian target records.
- **Validation Protocol:** **5-Fold Spatial Block Cross-Validation** on Indonesian target folds (`blocksize = 250 km`). Evaluated via **Continuous Boyce Index (CBI)** (primary presence-only metric), **AUC-ROC**, and **True Skill Statistic (TSS)**.

---

## 3. Workspace Navigation
See [AGENTS.md](AGENTS.md) and [CONTEXT.md](CONTEXT.md) for the ICM pipeline structure, stage contracts ([stages/01_occurrences/CONTEXT.md](stages/01_occurrences/CONTEXT.md)), and codebase rules ([_shared/codebase-conventions.md](_shared/codebase-conventions.md)).
