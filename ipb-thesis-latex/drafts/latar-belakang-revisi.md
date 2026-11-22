# Cetak biru revisi Latar Belakang

Draf 2026-11-21. Bahan untuk penulis, bukan teks Bab I. Setiap butir adalah klaim beserta sumbernya. Penulis menulis kalimatnya sendiri.

Dasar: catatan revisi Pembimbing 1 di `src/chapters/chapter-1.tex`, model CARS (Swales 1990), dan pola piramida terbalik.

## 1. Diagnosis draf sekarang

| Paragraf | Isi sekarang | Langkah CARS | Masalah |
|---|---|---|---|
| 1 | Status IUCN, perlindungan, lokasi agregasi Indonesia | Move 1 | Langsung masuk Indonesia. Revisi 1 meminta umum ke spesifik, Australia dulu. `Pierce2016` sudah ada versi 2025. |
| 2 | Kajian habitat di Indonesia, bias GBIF/OBIS | Move 1 + 2 bercampur | Belum ada kajian HSM di luar negeri dan negara tetangga (revisi 2). |
| 3 | Australia, transfer, KMM | Move 2 | **`Serov2026` dikutip untuk KMM sebagai pembobot data latih. Serov memakai KMM untuk estimasi galat, bukan pelatihan.** Belum ada perbandingan metode (revisi 4). |
| 4 | Media sosial | Move 1 + 2 | `Beddoe2026` (preseden terdekat untuk RM2) belum dipakai. |
| 5 | Kalimat penutup | Move 3 | Celah tidak dinyatakan eksplisit sebelum kalimat ini. |

## 2. Struktur yang diusulkan

Urutan mengikuti revisi 1 dan 2: umum, luar negeri (Australia dulu), negara tetangga, Indonesia, celah, metode, penutup.

### P1. Pentingnya topik (Move 1, umum)

- Hiu paus berstatus *Endangered*; populasi turun lebih dari 50% dalam tiga generasi. Sumber: Pierce et al. 2025, IUCN e.T19488A126673248, doi 10.2305/IUCN.UK.2025-2.RLTS.T19488A126673248.en (dikutip Putra 2026). **Ganti `Pierce2016`.**
- Ancaman: interaksi perikanan, tabrakan kapal, wisata tak terkelola (Putra 2026, Reynolds 2017).
- Pengelolaan ruang laut butuh peta habitat (Reynolds 2017: habitat sesuai banyak di luar kawasan konservasi).

### P2. Model habitat hiu paus di luar negeri (Move 1, revisi 2)

| Studi | Wilayah | Data | Metode | Kunci bib |
|---|---|---|---|---|
| Reynolds et al. 2017 | Australia Barat | Telemetri 29 hiu | GAMM | `Reynolds2017` |
| Miller et al. 2026 | Laut Koral, Pasifik barat daya | Telemetri hiu muda | Ensemble SDM, validasi blok spasial + data independen | **baru** |
| Sequeira et al. 2012 | Samudra Hindia | Logbook pukat cincin tuna | GLM, GLMM, MaxEnt | **baru** |
| Sequeira et al. 2014 | Global | Logbook tuna 1980–2010 | GLMM | **baru** |
| McKinney et al. 2012 | Teluk Meksiko utara | Laporan penampakan sukarelawan | MaxEnt, ENFA | **baru** |
| Báez et al. 2020 | Samudra Atlantik | Data pengamat perikanan | Ensemble 19 algoritme | **baru** |
| Petatán-Ramírez et al. 2020 | Teluk California | Basis data internasional + literatur | MaxEnt | **baru** |
| Milles et al. 2025 | Atlantik barat laut | Survei + citizen science oportunistik | SDM musiman | **baru** |

Pola yang terlihat: data berasal dari telemetri, logbook perikanan, atau penampakan lokal. Belum ada yang memindahkan model antarwilayah dengan koreksi pergeseran domain. *(Klaim terakhir ini masih perlu dicek di Google Scholar sebelum ditulis.)*

### P3. Negara tetangga dan Indonesia (Move 1)

- Filipina: Araujo et al. 2019, photo-ID dan telemetri, tanpa model habitat. Ada keterhubungan individu dengan Malaysia dan Kalimantan Timur.
- Indonesia, skala lokal: Ranintyari 2018 (GAM, deviance 6,16%), Manuhutu 2021 (GAM), Herdianti 2025 (regresi, 36 penampakan), Adriani 2023 (populasi dan suhu-salinitas, satu hotspot).
- Indonesia, skala kepulauan: Putra 2026, MaxEnt dari telemetri 70 hiu di 4 lokasi, sekitar 91% jantan muda, 21 dari 73 model berbasis kurang dari 10 titik.
- Data okurensi mengelompok di bagan: 97,8% penampakan di dua wilayah (Setyawan 2025).

### P4. Celah utama dan celah metode (Move 2)

- **Celah utama (terbatas pada):** model habitat Indonesia bersandar pada telemetri dari sedikit lokasi atau satu teluk. Data okurensi terbuka sedikit dan bias.
- **Solusi yang wajar:** pinjam data dari wilayah kaya data. Preseden: Bridges 2023 (transfer Atlantik utara ke selatan, AUC 0,70).
- **Kenapa transfer langsung tidak cukup (kurang memadai):** Wilson 2026 (transfer spasial tanpa adaptasi gagal), Sahri 2023 (transfer antarwilayah Indonesia gagal), Elith 2010 (model mirip menyimpang saat ekstrapolasi).
- **Jawaban yang harus siap:** Reynolds 2017 sudah memproyeksikan ke perairan Indonesia, tetapi tanpa validasi data Indonesia dan tanpa koreksi pergeseran domain.

### P5. Pilihan metode dan alternatifnya (Move 2 ke 3, revisi 4)

| Pendekatan | Yang dikoreksi | Pakai info domain target? | Sumber |
|---|---|---|---|
| Transfer langsung | Tidak ada | Tidak | Bridges 2023, Wilson 2026 |
| Subsampling lingkungan | Bias pengambilan sampel | Tidak | Pili 2025 |
| Pembobotan rasio densitas (KDE) | Pergeseran kovariat | Ya | Saigusa et al. 2026 |
| **KMM** | Pergeseran kovariat | Ya, tanpa mengestimasi densitas | Zhuang et al. 2021, Kouw & Loog 2021 (Huang et al. 2007 hanya sebagai pengusul metode) |
| Integrasi beberapa sumber data | Kurangnya data di target | Ya | Patterson et al. 2025, Gonnerman 2026 |

- Kenapa KMM, bukan KDE: pembobotan KDE meledak pada data yang mengelompok, KMM stabil (Serov 2026). **Ini satu-satunya peran Serov di P5.**
- **Celah dari penulis paper itu sendiri (Saigusa et al. 2026):** pembobotan untuk transfer SDM baru diuji dengan uLSIF; penulisnya menyebut KMM sebagai alternatif yang belum diuji. Manfaat pembobotan lebih besar saat pergeseran kuat dan data kemunculan sedikit, dua kondisi yang cocok dengan kasus hiu paus Australia ke Indonesia. Rata-rata perbaikannya kecil (AUC 0,633 vs 0,635 pada 78 spesies), sejalan dengan Lalou et al. 2025.
- Asumsi KMM: hubungan spesies-lingkungan sama di kedua domain, dan kondisi target berada di dalam jangkauan sumber (Kouw & Loog 2021). MESS menunjukkan di mana asumsi kedua dilanggar (Elith 2010).
- Ekspektasi yang jujur: pada uji realistis, pembobotan (termasuk KMM) sering hanya memberi perbaikan kecil, terutama untuk model kompleks, tetapi jarang memperburuk hasil (Lalou et al. 2025). Pembobotan cocok untuk pergeseran sedang (Zhang & Gao 2024).

### P6. Media sosial (Move 1 + 2, untuk RM2)

- Preseden: Araujo 2019 (36% individu dari publik), Taklis 2020 (22 salah identifikasi), Dehm 2025 (dua peninjau, aturan lokasi tiga tingkat), **Beddoe 2026** (1.124 laporan terverifikasi; lebih banyak sel unik daripada GBIF untuk lima takson).
- **Celah (belum jelas):** penelitian itu mengukur titik atau luas sebaran (EOO), bukan cakupan relung lingkungan atau ekstrapolasi model.

### P7. Penutup (Move 3)

- Satu atau dua kalimat yang menyatakan apa yang dilakukan penelitian ini, dan langsung mengantar ke Rumusan Masalah.

## 3. Kecocokan dengan Rumusan Masalah

| Celah | Rumusan masalah sekarang | Cocok? |
|---|---|---|
| Data Indonesia terbatas | Konteks RM1 dan RM2 | Ya |
| Transfer langsung kurang memadai | RM1 (KMM vs lokal vs transfer langsung) | Ya |
| Kontribusi media sosial ke relung belum jelas | RM2 (cakupan relung dan MESS) | Ya |

Keputusan penulis (2026-11-21):

1. **Subsampling lingkungan (Pili 2025) menjadi pembanding keempat di RM1.** Akibatnya RM1, Tujuan 1, Ruang Lingkup butir 4, `drafts/metode-penelitian.md`, dan `PROJECT_OVERVIEW.md` perlu menyebut empat skema. Kalimat RM dan Tujuan ditulis ulang oleh penulis.
2. **Judul boleh diubah.** Setelah Latar Belakang selesai, cek apakah judul memuat semua inti: hiu paus, Indonesia, adaptasi domain dari Australia, pembanding metode, dan media sosial terverifikasi.

Catatan untuk P5: dengan keputusan 1, tabel metode di P5 bukan lagi sekadar tinjauan. Subsampling lingkungan benar-benar diuji, jadi celah "kenapa bukan Pili?" dijawab oleh hasil, bukan oleh argumen.

## 4. Pustaka yang perlu ditambahkan

| Kunci usulan | Untuk | Status |
|---|---|---|
| `Pierce2025` | P1, ganti `Pierce2016` | Metadata dari daftar pustaka Putra 2026; cek di IUCN |
| `Huang2007` | P5, dasar KMM | Terverifikasi: NIPS 19, MIT Press 2007 |
| `Saigusa2026` | P5 | Ecological Modelling 516: 111534 |
| `Patterson2025` | P5 | Methods Ecol Evol, doi 10.1111/2041-210x.70178 |
| `Miller2026` | P2 | Diversity and Distributions, doi 10.1111/ddi.70186 |
| `Sequeira2012` | P2 | Diversity and Distributions, doi 10.1111/j.1472-4642.2011.00853.x |
| `Sequeira2014` | P2 | Global Change Biology, doi 10.1111/gcb.12343 |
| `McKinney2012` | P2 | MEPS 458: 199–211, doi 10.3354/meps09777 |
| `Baez2020` | P2 | Ecology and Evolution 10(1): 175–184, doi 10.1002/ece3.5884 |
| `PetatanRamirez2020` | P2 | J Fish Biol, doi 10.1111/jfb.14496 |
| `Milles2025` | P2 | MEPS, artikel meps14906 |

Catatan aturan 80%: Huang 2007, Sequeira 2012, McKinney 2012, Sequeira 2014, dan Elith 2010 lebih tua dari 10 tahun. Pakai seperlunya, dan hitung ulang setelah `\nocite` dihapus.
