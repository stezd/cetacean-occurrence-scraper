# Log penggunaan AI

Dibuat 2026-11-22 untuk memenuhi *Panduan Penggunaan AI IPB*:
- C.4 butir 2: dokumentasikan cara AI digunakan.
- C.5 butir 1: catat alat, versi, tanggal, dan prompt.
- C.5 butir 2: nyatakan peran AI secara eksplisit.

Pernyataan resmi ada di `src/config/information.tex` (`\NamaAlatAI`, `\TujuanPenggunaanAI`).

## Cara mengisi

- Tambahkan satu baris untuk setiap pemakaian AI yang menghasilkan isi naskah, kode, atau data.
- Kolom **Bukti** menunjuk ke tempat yang bisa diperiksa: hash commit, komentar `% DRAF` di naskah, atau thread/sesi.
- Kolom **Verifikasi** menjelaskan apa yang dicek manusia.
- Baris bertanda **(isi)** belum diketahui asisten. Penulis harus melengkapinya.

## Sumber dokumentasi

| Sumber | Isi |
|---|---|
| Komentar `% DRAF` di `src/chapters/*.tex` | Paragraf yang drafnya dibuat AI, beserta alat dan tanggalnya |
| Riwayat git (`git log --date=short`) | Perubahan naskah dan kode per tanggal |
| Transkrip sesi Claude Code | Prompt dan keluaran, disimpan lokal di `~/.claude/projects/` |
| Thread delegasi T3 Code | Prompt dan keluaran Gemini Neon |

## Log

| Tanggal | Alat (versi) | Bagian | Peran AI | Verifikasi oleh penulis | Bukti |
|---|---|---|---|---|---|
| 2026-10-03 s.d. 2026-11-17 | (isi) | Kode pipeline `stages/01_occurrences/`, `_tools/` | Rekayasa perangkat lunak | (isi) | commit `3e1576b` s.d. `264ab86` |
| 2026-11-14 s.d. 2026-11-21 | (isi) | `literature/markdown/*/summary.md` (55 paper) | Konversi PDF dan peringkasan pustaka | Klaim yang dikutip di naskah dicek ke teks paper | `_tools/pdf_to_md.py`, folder `literature/` |
| 2026-11-14 s.d. 2026-11-21 | (isi) | `src/refs/daftar-pustaka.bib` | Penyusunan entri BibTeX | Metadata dicek ke halaman penerbit | commit `fc39d63`, `52c662c`, `98ae593` |
| 2026-11-21 | Claude Opus 5.5 | Bab I Latar Belakang P1 | Saran perbaikan kalimat dan penempatan sitasi pada draf penulis | Angka IUCN dicek langsung ke justifikasi asesmen | komentar di atas P1 |
| 2026-11-21 | Claude Opus 5.5 | Bab I P2, dari kalimat Miller sampai akhir | Draf awal atas permintaan penulis | Sitasi dicek ke ringkasan dan teks paper | `% DRAF ASISTEN 2026-11-21` |
| 2026-11-21 | Gemini 4 Neon; dirapikan Claude Opus 5.5 | Bab I P3–P6 | Draf awal, lalu perbaikan fakta dan sitasi | Klaim utama dicek ke teks paper | `% DRAF P3`–`% DRAF P6`, commit `5e53a24` |
| 2026-11-22 | Claude Opus 5.5 (3 reviewer) dan Gemini 4 Neon (1 reviewer) | Bab I P7, Rumusan Masalah, Tujuan 2, Hipotesis | Tinjauan naskah dan usulan rumusan; usulan gabungan disetujui penulis | Penulis memilih dan menyetujui rumusan | `% DRAF P7`, commit `4aa1eb8` |
| 2026-11-22 | Claude Opus 5.5 | Halaman awal (`information.tex`) dan tiga suntingan kata di P2 | Menerapkan catatan penulis dari PDF beranotasi | Penulis menulis isinya di anotasi PDF | commit `697c804` |
| (isi) | Gemini 4 Hydrogen | (isi) | (isi) | (isi) | (isi) |
| (isi) | GLM 5.3 | (isi) | (isi) | (isi) | (isi) |
| (isi) | DeepSeek 4.1 Flash | (isi) | (isi) | (isi) | (isi) |

## Kewajiban yang masih terbuka

- [ ] Sunting semua paragraf bertanda `% DRAF` ke gaya sendiri sebelum naskah diserahkan. Dasarnya: Panduan hlm. 25, butir b, "tidak boleh menggunakan hasil keluaran dari AI begitu saja".
- [ ] Setelah menyunting, ubah komentar `% DRAF` menjadi catatan riwayat, misalnya `% Draf awal: Gemini Neon 2026-11-21; ditulis ulang penulis <tanggal>`. Jangan hapus jejaknya.
- [ ] Tambahkan paragraf "Penggunaan AI" di Bab III dengan format terstruktur dari Panduan C.5 butir 4.
