# Cetacean Habitat Suitability Modeling (Whale & Dolphin Sightings)

## 1. Project Background ("About" / Latar Belakang)

### The Problem
- **Data Deficiency in Indonesia:** Indonesian waters (notably the Savu Sea, Alor, Flores, and the Wallacea region) host vital migration corridors and habitats for cetaceans (whales, dolphins, and porpoises). However, occurrence records within Indonesian territorial waters are historically fragmented and poorly documented compared to data-rich neighbors like Australia (~950 records in ID vs 11,000+ in AU).
- **Conservation & Maritime Urgency:** Without clear habitat suitability maps and migration corridor models, marine spatial planning, maritime vessel strike mitigation, and traditional whaling monitoring (e.g., Lamalera in NTT) lack robust scientific baselines.
- **The Research Hypothesis:** By coupling open occurrence data (GBIF / OBIS / opportunistic sightings) with high-resolution oceanographic and bathymetric environmental predictors, we can model and predict cetacean habitat suitability across Indonesian waters, using cross-regional correlation from neighboring Australian populations across seasonal monsoon cycles.

---

## 2. Research Architecture & Methodology

### A. Occurrence Data (Presence Points)
1. **Target Taxa:** Order *Cetacea* (TaxonKey: `733`).
   - High-occurrence species in Indonesia:
     - *Physeter macrocephalus* (Sperm Whale / Paus Sperma) — **483 verified records**
     - *Stenella longirostris* (Spinner Dolphin) — **173 verified records**
     - *Tursiops aduncus* (Bottlenose Dolphin) — **34 verified records**
     - *Peponocephala electra* (Melon-headed Whale) — **34 verified records**
     - *Globicephala macrorhynchus* (Short-finned Pilot Whale) — **32 verified records**
     - *Balaenoptera musculus* (Blue Whale) — **25 verified records**
     - *Balaenoptera omurai* (Omura's Whale) — **12 verified records**
     - *Megaptera novaeangliae* (Humpback Whale) — **11 verified records**
2. **Seasonal Temporal Slices (Monsoon Cycles):**
   - **NWM (Northwest Monsoon):** December – February
   - **TR1 (Transition 1):** March – May
   - **SEM (Southeast Monsoon):** June – August
   - **TR2 (Transition 2):** September – November

### B. Environmental Predictors (Oceanographic & Bathymetric)
- `thetao_mean`: Sea Surface Temperature (°C)
- `tob_mean`: Average temperature at seafloor bottom (°C)
- `chl_mean`: Total Chlorophyll concentration (mg/m³) — primary food chain indicator
- `zos_mean`: Sea Surface Height Above Geoid (m) — ocean currents and upwelling
- `nppy_mean`: Net Primary Production / carbon capture through photosynthesis
- `distance_0`: Distance to shoreline (km)
- `distance_200`, `distance_300`, `distance_500`: Distance to 200m, 300m, and 500m bathymetric isobaths
- `slope`: Seafloor inclination / topographic gradient

### C. Machine Learning & Modeling Techniques
- **Presence-Only / Pseudo-Absence Modeling:** Because marine animals are underwater, lack of sighting does not prove absence ("pseudo-absence").
- **MaxEnt (Maximum Entropy Modeling):** Industry standard for presence-only ecological niche modeling.
- **Tree-Based Ensembles:** XGBoost and Random Forest trained with pseudo-absence background generation (accounting for spatial sampling bias using Gaussian Kernel Density weighting).

---

## 3. Data Files in this Repository

- `fetch_gbif_cetaceans.py`: Automated extractor querying the GBIF REST API for georeferenced cetaceans.
- `data/cetaceans_id.csv`: **951 verified cetacean occurrence records** in Indonesia with exact coordinates, species taxonomy, dates, and season tags.

### To Fetch Neighboring Data (Australia / Philippines):
```bash
# Fetch Australia records (e.g. for cross-regional model training)
python fetch_gbif_cetaceans.py AU 5000

# Fetch Philippines records
python fetch_gbif_cetaceans.py PH 1000
```
