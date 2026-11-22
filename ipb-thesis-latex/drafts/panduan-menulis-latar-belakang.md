# Panduan menulis Latar Belakang

Disimpan 2026-11-21 atas permintaan penulis. Pasangan dari [latar-belakang-revisi.md](latar-belakang-revisi.md) (cetak biru klaim dan sumber).

Cara paling cepat: **tulis kerangkanya dulu, baru isinya.** Kerangka Latar Belakang adalah tujuh kalimat topik. Kalau tujuh kalimat itu dibaca berurutan dan sudah terdengar seperti satu argumen, sisanya tinggal mengisi bukti.

## Kebenaran dasarnya (sekali lagi, singkat)

Latar Belakang adalah **argumen yang berakhir di Rumusan Masalah.** RM Anda sudah final. Jadi Anda menulis ke arah tujuan yang sudah jelas, bukan mencari-cari arah.

## Alur kerja 4 langkah

**Langkah 1: Tulis kalimat terakhir dulu (5 menit).**
Kalimat penutup harus mengantar langsung ke kedua RM: data Australia untuk RM1, media sosial terverifikasi untuk RM2. Semua paragraf lain bergerak ke kalimat ini.

**Langkah 2: Tulis 7 kalimat topik (20 menit).**
Satu kalimat per paragraf, belum pakai sitasi. Lalu baca ketujuhnya berurutan. Kalau ada lompatan logika, perbaiki di sini, karena masih murah.

**Langkah 3: Isi tiap paragraf (±20 menit per paragraf).**
Pola tiap paragraf:
1. kalimat topik (klaim);
2. 2–4 kalimat bukti, masing-masing dengan sitasi;
3. satu kalimat penghubung yang memancing paragraf berikutnya, biasanya berupa kekurangan atau "namun".

**Langkah 4: Cek dengan daftar syarat (10 menit).** Daftarnya ada di bawah.

## Peta paragraf

Isi tiap paragraf diambil dari cetak biru. Kolom "harus menyatakan" berisi klaim yang perlu Anda tulis dengan kalimat sendiri.

| P | Tugas | Kalimat topik harus menyatakan | Bukti (kunci `\citep`) | Penghubung ke P berikutnya |
|---|---|---|---|---|
| 1 | Penting | Hiu paus terancam dan butuh peta habitat untuk pengelolaan | `Pierce2025`, `Reynolds2017`, `Putra2026` | Peta habitat dibuat dengan model sebaran |
| 2 | Luar negeri | Model habitat hiu paus sudah dibuat di banyak wilayah, Australia dulu | `Reynolds2017`, `Miller2026`, `Sequeira2014`, `McKinney2012`, `Baez2020`, `Milles2025` | Datanya telemetri, logbook, atau penampakan lokal |
| 3 | Tetangga + Indonesia | Di Indonesia, kajiannya lokal atau berbasis telemetri | `Araujo2019`, `Ranintyari2018`, `Manuhutu2021`, `Herdianti2025`, `Adriani2023`, `Putra2026`, `Setyawan2025` | Data kemunculan Indonesia sedikit dan bias |
| 4 | **Celah** | Data Indonesia tidak cukup; meminjam data Australia masuk akal, tetapi transfer langsung sering gagal | `Setyawan2025`, `Bridges2023`, `Wilson2026`, `Sahri2023`, `Elith2010`, `Sequeira2014` (efek beda antarsamudra) | Ada beberapa cara mengatasi pergeseran itu |
| 5 | Metode | Ada beberapa cara memakai data sumber; tiap cara mengoreksi masalah berbeda | `Pili2025`, `Zhuang2021`, `Kouw2021`, `Saigusa2026`, `Lalou2025`, `Serov2026` (hanya kestabilan bobot) | Data lain bisa menambah titik Indonesia |
| 6 | Media sosial | Media sosial terverifikasi sudah dipakai untuk data kemunculan, tetapi pengaruhnya pada cakupan lingkungan model belum diukur | `Araujo2019`, `Taklis2020`, `Dehm2025`, `Beddoe2026`, `Moore2024` | (langsung ke penutup) |
| 7 | Penutup | Penelitian ini menguji kedua sumber data tersebut | — | → Rumusan Masalah |

**Kalimat celah terkuat di P5:** Saigusa et al. (2026) sendiri menyebut KMM sebagai alternatif yang belum mereka uji. Kutip itu, dan tidak perlu klaim "pertama".

### Catatan P1 (ditambahkan 2026-11-21)

- Status, penurunan 50–79% dalam tiga generasi (120 tahun), panjang 18–20 m, dan sebaran tropis–subtropis hangat sudah dicek langsung di justifikasi asesmen IUCN (`Pierce2025`).
- Bahan sisa P1: penurunan Indo-Pasifik >65% (`Pierce2025`); ancaman tangkapan sampingan jaring dan tabrakan kapal (`Pierce2025`); hiu paus bergerak ke luar kawasan yang dikelola (`Putra2026`, `Reynolds2017`); kalimat penghubung ke P2 (`Putra2026`).
- Jangan menerjemahkan urutan kalimat Putra 2026 secara langsung (risiko plagiarisme terjemahan).
- Status ditulis *Endangered* saja, tanpa padanan "Genting".

## Daftar cek sebelum selesai

- [ ] Urutannya umum ke spesifik, Australia sebelum Indonesia (revisi 1).
- [ ] P2–P3 menjawab "apa bedanya penelitian ini dengan penelitian lain?" (revisi 2).
- [ ] P5 menyebut alternatif metode dan alasan memilih (revisi 4).
- [ ] Setiap RM sudah "dijanjikan" oleh satu celah (revisi 3).
- [ ] Serov **tidak** dikutip sebagai dasar pelatihan berbobot KMM.
- [ ] Tidak ada angka hasil penelitian sendiri. Angka dari paper orang lain boleh, dengan sitasi.
- [ ] Setiap kalimat fakta punya sitasi.
- [ ] Bahasa baku: kalimat aktif, satu gagasan per kalimat.

## Praktis

- Tulis langsung di `src/chapters/chapter-1.tex`, di bawah `\section{Latar Belakang}`. Draf lama bisa dibungkus `\begin{comment}...\end{comment}` supaya tetap ada sebagai cadangan.
- Semua kunci sitasi di tabel sudah ada di `.bib`, jadi langsung jalan begitu dikompilasi.
- Kalau lupa isi sebuah paper, buka `literature/markdown/<paper>/summary.md`, terutama bagian "Use for this project".

Kalau sudah selesai, sebagian atau semuanya, kirim ke asisten. Asisten mengecek terhadap daftar di atas dan memastikan setiap sitasi benar-benar mendukung klaimnya. PDF tidak di-build ulang kecuali diminta. Kalimat tidak diubah tanpa bertanya.
