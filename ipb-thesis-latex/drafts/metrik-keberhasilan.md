# Metrik keberhasilan (bahan RM dan Bab III)

Draf 2026-11-21. Bahan untuk penulis, bukan teks skripsi. Arah RM: data Indonesia yang sedikit dan bias diperkuat oleh (1) data Australia lewat empat strategi, dan (2) media sosial terverifikasi. Semua metadata dicek di Crossref.

## Prinsip

1. **"Berhasil" harus diukur pada data Indonesia yang tidak dipakai untuk melatih**, yaitu lipatan uji validasi silang blok spasial. Skor validasi silang acak atau skor pelatihan tidak cukup (Matsui 2026; Miller et al. 2026: AUC latih 0,98, AUC uji blok spasial 0,65–0,69).
2. **Untuk data presence-only, hanya indeks Boyce yang benar-benar cocok.** AUC dan TSS secara teori butuh data absensi sejati (Leroy et al. 2018, dikutip Pili et al. 2025). AUC dan TSS tetap boleh dilaporkan sebagai pelengkap.
3. **Satu ukuran keberhasilan per RM**, ditambah metrik pendukung dan diagnostik.

## RM1: apakah data Australia memperkuat model Indonesia?

| Peran | Metrik | Definisi keberhasilan | Sumber |
|---|---|---|---|
| **Utama** | Indeks Boyce kontinu (CBI) pada lipatan uji blok spasial Indonesia | ΔCBI = CBI(strategi) − CBI(model lokal) > 0, dan konsisten di sebagian besar lipatan | Pili et al. 2025; Leroy et al. 2018 |
| Estimasi CBI | CBI dengan pemulusan statistik | Dipakai karena okurensi Indonesia per lipatan sedikit; CBI cara biasa bias saat titik uji sedikit | Liu et al. 2025 |
| Pelengkap | AUC-ROC dan TSS | Arah perubahan sama dengan CBI | Leroy et al. 2018 (keterbatasannya) |
| Pelengkap | Korelasi prediksi model transfer dengan prediksi model lokal Indonesia (RWIP) | Korelasi tinggi berarti transfer menghasilkan pola yang mirip dengan model yang dikalibrasi di Indonesia | Matsui 2026 |
| Diagnostik KMM | Jumlah sampel efektif bobot (ESS) dan MMD sebelum dan sesudah pembobotan | MMD turun tanpa ESS jatuh terlalu rendah | Kouw & Loog 2021 (varians bobot) |

Catatan:
- Bandingkan semua strategi terhadap **model lokal**, karena pertanyaannya "apakah data Australia membantu", bukan "strategi mana yang tertinggi".
- Uji perbedaan antarstrategi per lipatan secara berpasangan. Metode ujinya belum dipilih dan sumbernya belum dicari.
- Hipotesis dari Lalou et al. 2025: KMM lebih membantu MaxEnt (teregularisasi) daripada XGBoost dan Random Forest (kompleks).

## RM2: apakah media sosial terverifikasi memperkuat data Indonesia?

| Peran | Metrik | Definisi keberhasilan | Sumber |
|---|---|---|---|
| **Utama** | Luas *area of applicability* (AOA) di perairan Indonesia | Persentase luas laut Indonesia di dalam AOA naik setelah media sosial ditambahkan | Meyer & Pebesma 2021 |
| Pendukung | Kepadatan titik latih lokal (LPD) | Jumlah titik latih yang mirip per lokasi prediksi naik di wilayah yang sebelumnya kosong | Schumacher et al. 2025 |
| Pendukung | Luas ekstrapolasi MESS (MESS < 0) | Persentase luas dengan MESS < 0 turun | Elith et al. 2010; alternatif modern: Velazco et al. 2024 (Shape) |
| Pendukung | Sel unik spasial (indeks Sørensen) | Media sosial menyumbang sel grid yang tidak ada di GBIF dan OBIS | Beddoe et al. 2026 |
| **Pengaman** | ΔCBI dengan dan tanpa media sosial, pada lipatan uji GBIF/OBIS yang sama | ΔCBI ≥ 0, atau tidak turun bermakna | Moore et al. 2024 |

**Jebakan yang harus dihindari:** AOA, LPD, dan MESS hampir pasti membaik setiap kali titik baru ditambahkan, valid atau tidak. Jadi cakupan saja tidak membuktikan apa-apa. Metrik pengaman (ΔCBI) memastikan titik tambahan tidak memperburuk model. Moore et al. 2024 juga menemukan bahwa perubahan model lebih ditentukan oleh **lokasi** titik tambahan daripada **jumlahnya**, jadi laporkan juga di mana titik media sosial berada.

## Pustaka metrik (belum masuk `.bib`)

| Kunci usulan | Rujukan |
|---|---|
| `MeyerPebesma2021` | Methods in Ecology and Evolution 12(9): 1620–1633, doi 10.1111/2041-210X.13650 |
| `Schumacher2025` | Geoscientific Model Development 18(24): 10185–10202, doi 10.5194/gmd-18-10185-2025 |
| `Velazco2024` | Ecography 2024(3): e06992, doi 10.1111/ecog.06992 |
| `Liu2025` | Ecography 2025(1): e07218, doi 10.1111/ecog.07218 |
| `Matsui2026` | Ecology and Evolution 16(5): e73534, doi 10.1002/ece3.73534 |
| `Moore2024` | Ecological Informatics 84: 102857, doi 10.1016/j.ecoinf.2024.102857 |
| `Leroy2018` | Journal of Biogeography 45(9): 1994–2002, doi 10.1111/jbi.13402 |

## Dampak ke pipeline (belum dikerjakan)

- AOA dan LPD tersedia di paket R `CAST`. Pipeline sekarang memakai Python, jadi perlu memilih: panggil R, atau implementasikan ulang DI/AOA di Python (rumusnya sederhana: jarak minimum di ruang prediktor yang dibobot kepentingan variabel, dibagi rata-rata jarak antartitik latih).
- CBI dengan pemulusan perlu diimplementasikan atau diambil dari kode Liu et al. 2025.
