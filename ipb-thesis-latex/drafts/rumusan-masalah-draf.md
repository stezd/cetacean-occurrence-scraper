# Draf Rumusan Masalah, Tujuan, dan Hipotesis

Draf 2026-11-21, disusun asisten atas permintaan penulis. Arah B: masalah data, dengan perbandingan empat strategi di dalam RM1. Penulis meninjau dan menyunting sebelum dipindahkan ke `src/chapters/chapter-1.tex`. Dasar: `drafts/latar-belakang-revisi.md` dan `drafts/metrik-keberhasilan.md`.

## Rumusan Masalah

Berdasarkan latar belakang tersebut, rumusan masalah dalam penelitian ini adalah sebagai berikut:

1. Bagaimana pengaruh pemanfaatan data kemunculan hiu paus (*Rhincodon typus*) dari perairan Australia terhadap kinerja model kesesuaian habitat di perairan Indonesia apabila data tersebut digunakan melalui transfer langsung, adaptasi domain *Kernel Mean Matching* (KMM), dan *subsampling* lingkungan, dibandingkan dengan model yang hanya dilatih dengan data Indonesia?
2. Sejauh mana penambahan data kemunculan dari media sosial dan berita daring yang telah diverifikasi pakar memperluas cakupan lingkungan model kesesuaian habitat hiu paus di perairan Indonesia tanpa menurunkan kinerja model?

## Tujuan

Berdasarkan rumusan masalah yang telah diuraikan, penelitian ini bertujuan untuk:

1. Membandingkan kinerja model kesesuaian habitat hiu paus di perairan Indonesia pada empat skema pelatihan, yaitu model lokal Indonesia, transfer langsung dari Australia, adaptasi domain KMM, dan *subsampling* lingkungan, menggunakan algoritme MaxEnt, XGBoost, dan *Random Forest*. Kinerja diukur dengan indeks Boyce kontinu sebagai ukuran utama serta AUC-ROC dan TSS sebagai ukuran pelengkap, melalui validasi silang blok spasial lima lipatan.
2. Mengukur perubahan luas *area of applicability* (AOA), luas wilayah ekstrapolasi MESS, dan indeks Boyce kontinu model di perairan Indonesia akibat penambahan data media sosial terverifikasi pada data GBIF dan OBIS.

## Hipotesis (opsional)

1. Pemanfaatan data Australia meningkatkan indeks Boyce kontinu model di perairan Indonesia dibandingkan model lokal, dan peningkatan dari KMM lebih besar pada MaxEnt daripada pada XGBoost dan *Random Forest* (dasar: Lalou et al. 2025).
2. Penambahan data media sosial terverifikasi memperluas AOA dan mempersempit wilayah ekstrapolasi MESS tanpa menurunkan indeks Boyce kontinu.

## Catatan untuk penulis

**Apa yang berubah dari versi lama:**

| Bagian | Lama | Draf ini | Alasan |
|---|---|---|---|
| Fokus RM1 | Kinerja KMM | Pengaruh data Australia, KMM salah satu dari tiga cara | Hasil tetap bermakna walau KMM tidak unggul (Lalou et al. 2025) |
| Skema | 3 | 4 (tambah *subsampling* lingkungan) | Keputusan penulis 2026-11-21; revisi 4 Pembimbing 1 |
| Pembanding | Tidak eksplisit | Model lokal Indonesia | Pertanyaannya "apakah data Australia membantu" |
| Metrik utama RM1 | CBI, AUC, TSS setara | CBI utama, AUC dan TSS pelengkap | Hanya indeks Boyce cocok untuk *presence-only* (Leroy et al. 2018) |
| Fokus RM2 | Cakupan relung dan MESS | Cakupan lingkungan **tanpa menurunkan kinerja** | AOA dan MESS pasti membaik saat titik ditambah; perlu metrik pengaman |
| Metrik RM2 | Cakupan relung, MESS | AOA (utama), MESS, CBI | AOA mengukur di mana skor validasi berlaku (Meyer & Pebesma 2021) |

**Bagian lain yang ikut berubah bila draf ini dipakai:**

1. Ruang Lingkup butir 4: sebut empat skema.
2. Ruang Lingkup butir 6: MESS sekarang pendukung; AOA menjadi metrik utama RM2.
3. `drafts/metode-penelitian.md`: bagian Evaluasi perlu menyebut AOA, LPD, dan metrik pengaman.
4. Judul: pertimbangkan judul yang menonjolkan masalah data, misalnya dengan kata kunci "data Australia" dan "media sosial terverifikasi". Judul PPTA maksimal 15 kata bermakna.

**Hal yang belum diputuskan:**

- Metode *subsampling* lingkungan: pengelompokan lingkungan atau penipisan jarak lingkungan (Pili et al. 2025).
- Uji statistik untuk membandingkan skema per lipatan.
- Apakah Hipotesis ditulis eksplisit. PPTA membolehkan eksplisit atau tersirat.
