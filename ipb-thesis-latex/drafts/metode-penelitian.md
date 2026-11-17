# Metode Penelitian (draf esensi)

Draf 2026-11-17. Ringkasan alur kerja, bukan teks Bab III. Sumber: `PROJECT_OVERVIEW.md`, `_shared/occurrence-pipeline-spec.md`, dan keputusan Ruang Lingkup opsi 1.

## 1. Data kemunculan

- **Spesies:** hiu paus (*Rhincodon typus*, GBIF `taxonKey=2417522`).
- **Wilayah:** Indonesia (domain target) dan Australia (domain sumber).
- **Periode:** 2010–2026.
- **Sumber:**
  1. GBIF dan OBIS untuk Indonesia dan Australia.
  2. YouTube dan berita daring untuk Indonesia.
  3. Verifikasi pakar oleh Pembimbing 2 (Dosen FPIK IPB). Hanya baris berstatus `valid` yang dipakai.
- **Pembersihan:** buang spesimen museum dan fosil, ketidakpastian koordinat > 10 km, tahun di luar periode, titik di darat (elevasi GEBCO ≥ 0 m), dan duplikat.
- **Musim:** NWM (Des–Feb), TR1 (Mar–Mei), SEM (Jun–Agu), TR2 (Sep–Nov).
- **Penipisan spasial:** jarak 10 km per domain dan musim.
- **Titik latar:** 10.000 titik per domain dari permukaan KDE (bandwidth 25 km) untuk mengoreksi bias pengambilan sampel.

## 2. Peubah lingkungan

- **Grid:** 1/12° (± 9,2 km). Peubah dinamis dirata-ratakan per musim.
- **Fisika (CMEMS):** suhu permukaan laut (`thetao`) dan tinggi muka laut (`zos`).
- **Biogeokimia (CMEMS):** klorofil-a (`chl`) dan produktivitas primer bersih (`nppv`).
- **Topografi (GEBCO):** kedalaman, kemiringan dasar laut, jarak ke pantai, serta jarak ke isobat 200, 300, dan 500 m.
- **Seleksi peubah:** Spearman |r| < 0,75 dan VIF ≤ 5.

## 3. Pemodelan

- **Algoritma:** MaxEnt, XGBoost, dan Random Forest.
- **Tiga skema pelatihan:**
  1. Lokal: data Indonesia saja.
  2. Transfer langsung: data Australia tanpa pembobotan, diproyeksikan ke Indonesia.
  3. Adaptasi domain: data Australia dibobot dengan KMM agar sebaran peubahnya mendekati Indonesia, lalu digabung dengan data Indonesia.
- **Perbandingan data:** GBIF + OBIS dibandingkan dengan GBIF + OBIS + media sosial terverifikasi.

## 4. Evaluasi

- **Validasi:** validasi silang blok spasial 5 lipatan (blok 250 km) pada data Indonesia.
- **Metrik kinerja (Tujuan 1):** CBI (utama), AUC-ROC, dan TSS.
- **Cakupan relung dan ekstrapolasi (Tujuan 2):** perubahan cakupan relung lingkungan dan peta MESS sebelum dan sesudah penambahan data media sosial.

## Catatan

- `PROJECT_OVERVIEW.md` masih mencantumkan Instagram, TikTok, dan X. Draf ini mengikuti keputusan opsi 1 (YouTube dan berita daring saja).
- Jumlah data belum dicantumkan. Angka hanya boleh diambil dari `check.md` yang berstatus `pass`.
