# Spesifikasi Data Pipeline — Occurrence Hiu Paus (*Rhincodon typus*)

Dokumen kerja untuk Bab III (`taxonKey=2417522`, diperbarui dari eksplorasi awal *Cetacea* `taxonKey=733`). Nama lapisan sengaja polos (`mentah` → `bersih` → `siap-model`).

## Ringkasan lapisan

| Lapisan | Isi | Format | Siapa yang baca |
|---|---|---|---|
| Mentah | respons GBIF/OBIS (`ID`, `AU`, `2010–2026`) + tangkapan media sosial apa adanya, append-only | JSONL / CSV mentah + bundel media lokal | pipeline & Pembimbing 2 |
| Bersih | baris tervalidasi (GBIF/OBIS + media sosial berstatus `valid` dari Pembimbing 2), terdedupe, bertag musim | CSV + `quarantine.csv` | audit, peneliti |
| Siap-model | thinning 10 km per musim (`NWM`, `TR1`, `SEM`, `TR2`) + background KDE 25 km | CSV di `stages/01_occurrences/output/` | model MaxEnt / XGBoost / RF |

---

## Tahap 1 — Ambil (ingest)

**Masukan:** daftar negara (`ID` target, `AU` source domain), rentang tahun (`2010–2026`), filter takson (`taxonKey=2417522`), serta hasil scraping media sosial.
**Keluaran:** berkas mentah + `manifest.json` + lembar verifikasi Pembimbing 2 (untuk media sosial).

Aturan teknis (dari dokumentasi GBIF):

- `limit` maksimum **300** per halaman; nilai lebih besar dipotong ke 300 ([GBIF occurrence API](https://www.gbif.org/developer/occurrence)).
- Batas keras **offset + limit ≤ 100.000** per query.
- Retry dengan backoff eksponensial untuk 429/5xx.
- Simpan **query JSON** dan hash-nya di manifest, supaya hasil bisa direproduksi.

Manifest minimal:

```json
{
  "query": {"taxonKey": 2417522, "country": "ID", "year": "2010,2026", "hasCoordinate": true},
  "query_hash": "sha256:...",
  "fetched_at": "2026-11-05T19:45:00+07:00",
  "pages": 2, "rows": 120, "sha256_file": "..."
}
```

---

## Tahap 2 — Skema dan penyaringan isu

**Masukan:** data mentah GBIF/OBIS + baris media sosial yang telah diverifikasi `status_verifikasi = valid` oleh **Pembimbing 2 (Dosen FPIK IPB)**.
**Keluaran:** baris valid + `quarantine.csv`.

Aturan tolak (masuk karantina, **bukan** dibuang):

| Kondisi | Alasan karantina |
|---|---|
| latitude/longitude kosong | `missing_coords` |
| tidak ada tanggal sama sekali | `missing_date` |
| `eventDate` berupa rentang (`"1785/1913"`) | `date_range_not_date` |
| `occurrenceStatus = absent` | `not_presence` |
| `basisOfRecord` = PRESERVED_SPECIMEN / MATERIAL_SAMPLE / FOSSIL_SPECIMEN | `not_observation` |
| `coordinateUncertaintyInMeters > 10000` (> 10 km, melebihi grid 1/12°) | `high_uncertainty` |
| tahun di luar `2010–2026` | `out_of_temporal_window` |
| media sosial `status_verifikasi != valid` (`repost`/`ragu`/`tolak`) | `unverified_social_media` |

Flag isu GBIF yang dipakai sebagai penanda:
`ZERO_COORDINATE`, `COORDINATE_OUT_OF_RANGE`, `COUNTRY_COORDINATE_MISMATCH`, `COORDINATE_ROUNDED`, `RECORDED_DATE_INVALID`, `RECORDED_DATE_UNLIKELY`, `BASIS_OF_RECORD_INVALID` ([Occurrence issues and flags](https://techdocs.gbif.org/en/data-use/occurrence-issues-and-flags)).

---

## Tahap 3 — Validasi koordinat

Mengikuti tes [CoordinateCleaner](https://cran.r-project.org/web/packages/CoordinateCleaner/readme/) + mask batimetri GEBCO:

| Tes | Aksi di pipeline |
|---|---|
| validitas koordinat (rentang, bukan 0/0) | tolak → `invalid_coord` |
| centroid negara/provinsi | tolak → `near_centroid` |
| koordinat ibu kota / institusi | tolak → `institution_coord` |
| titik di darat (`depth >= 0` m pada GEBCO) | tolak → `on_land` |
| duplikat koordinat per tanggal | tahap dedupe |

Nilai ketidakpastian palsu dari geocoder — **301, 3036, 999, 9999** — diperlakukan sebagai kosong, bukan angka nyata ([GBIF course](https://docs.gbif.org/course-data-use/)).

---

## Tahap 4 — Normalisasi taksonomi

- Cocokkan ke GBIF backbone: *Rhincodon typus* Smith, 1828 (`taxonKey=2417522`).

---

## Tahap 5 — Penandaan bukti & musim

| Kolom | Aturan |
|---|---|
| `source_stream` | `gbif`, `obis`, `social_media_verified` |
| `domain` | `ID` (target) atau `AU` (source) |
| `season` | `NWM` (Des–Feb), `TR1` (Mar–Mei), `SEM` (Jun–Agu), `TR2` (Sep–Nov), `UNKNOWN` bila bulan kosong |
| `basis_of_record` | disalin apa adanya untuk audit |

---

## Tahap 6 — Dedupe lintas sumber

- Kunci utama: `gbif_id` / `obis_id` / `sighting_id`.
- Kunci sekunder lintas repositori (GBIF vs OBIS vs medsos): `(round(lat, 4), round(lon, 4), event_date)`.
- Kalau bentrok, pertahankan baris dengan ketidakpastian koordinat terkecil.

---

## Tahap 7 — Spatial Thinning (10 km) & Background Bias (25 km KDE)

- **Thinning:** greedy spatial thinning dengan jarak **10 km** (haversine, setara ~1 sel grid CMEMS `1/12°` ≈ 9.2 km), dihitung **per domain (`ID`, `AU`) dan per musim (`NWM`, `TR1`, `SEM`, `TR2`)**.
- **Split musim:** baris `UNKNOWN` hanya masuk model statis tahunan, bukan musiman.
- **Background / Pseudo-Absence:** 10.000 titik background per domain yang disampel menggunakan **2D Gaussian Kernel Density Estimation (KDE, bandwidth = 25 km)** untuk mengoreksi bias observasi pesisir/wisata (Sahri et al., 2023; Pili et al., 2025).
- Keluaran: `stages/01_occurrences/output/rhincodon_<domain>_<musim>.csv` + `stages/01_occurrences/output/check.md`.

---

## Tahap 8 — Audit

- `stages/01_occurrences/output/check.md` mencatat status (`pass` / `fail: <alasan>`), jumlah titik sebelum dan sesudah penyaringan per tahap, per domain (`ID` vs `AU`), per `source_stream`, dan per musim (`NWM`, `TR1`, `SEM`, `TR2`), beserta checksum SHA-256 tiap berkas keluaran.
