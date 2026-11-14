# Panduan Verifikasi Penampakan Hiu Paus (*Rhincodon typus*) untuk Pembimbing 2

Dokumen ini memandu Pembimbing 2 (Dosen FPIK IPB) dalam memverifikasi data penampakan hiu paus (*Rhincodon typus*) dari media sosial dan berita (Stream 3).

## Berkas yang Digunakan

1. Templat lembar kosong: [verification_sheet_template.csv](verification_sheet_template.csv) (format UTF-8 dengan BOM agar Microsoft Excel membukanya tanpa merusak karakter).
2. Lembar kerja hasil unduhan otomatis: `stages/01_occurrences/input/social_media_unverified.csv`.
3. Bundel media lokal (foto/cuplikan): `stages/01_occurrences/input/social_media/media/`.

## Cara Membuka Lembar di Microsoft Excel

1. Klik ganda berkas CSV di Windows Explorer atau buka melalui menu **Data > From Text/CSV** di Excel dengan pengodean **65001: Unicode (UTF-8)**.
2. Periksa bukti visual melalui tautan pada kolom `post_url` atau berkas gambar pada kolom `local_media_path`.
3. Isi enam kolom observasi Pembimbing 2 pada bagian kanan tabel.

## Arti Nilai `status_verifikasi`

Isi kolom `status_verifikasi` dengan tepat satu nilai berikut (huruf kecil):

| Nilai | Arti | Dampak pada Pipeline |
|---|---|---|
| `valid` | Penampakan hiu paus (*Rhincodon typus*) asli di perairan Indonesia dalam rentang tahun 2010–2026 dengan waktu dan lokasi yang dapat dipastikan. | Masuk ke data bersih dan pemodelan spasial. |
| `repost` | Unggahan ulang dari kejadian atau dokumentasi yang sudah ada sebelumnya. | Masuk ke karantina (`unverified_social_media`) agar tidak terjadi penghitungan ganda. |
| `ragu` | Bukti visual atau keterangan tidak cukup jelas untuk memastikan spesies, lokasi, atau tanggal penampakan. | Masuk ke karantina (`unverified_social_media`). |
| `tolak` | Bukan hiu paus (*Rhincodon typus*), berita palsu, lokasi di luar cakupan, atau di luar periode 2010–2026. | Masuk ke karantina (`unverified_social_media`). |

> **Catatan penting:** Hanya baris dengan `status_verifikasi = valid` yang masuk ke tahap *spatial thinning* (10 km) dan kalibrasi model.

## Penjelasan Kolom Observasi Pembimbing 2

| Kolom | Cara Pengisian |
|---|---|
| `status_verifikasi` | Wajib diisi: `valid`, `repost`, `ragu`, atau `tolak`. |
| `lat_koreksi` | Lintang koreksi dalam derajat desimal WGS84 (contoh: `-8.6333`). Biarkan kosong apabila `lat_est` sudah sesuai. |
| `lon_koreksi` | Bujur koreksi dalam derajat desimal WGS84 (contoh: `117.9500`). Biarkan kosong apabila `lon_est` sudah sesuai. |
| `jumlah_individu` | Bilangan bulat positif untuk jumlah individu yang tampak (contoh: `2`). Boleh kosong bila tidak dapat dihitung. |
| `perilaku_konteks` | Pilih salah satu: `feeding`, `bagan`, `wisata`, atau `melintas`. Boleh kosong bila konteks tidak terlihat. |
| `catatan_dosen` | Catatan singkat hasil telaah pakar (opsional). |

### Catatan Koordinat dan Ketidakpastian Lokasi

- Jika `lat_koreksi` diisi, isi juga `lon_koreksi` sebagai pasangan koordinat.
- Rentang nilai koordinat yang sah adalah `-90` hingga `90` untuk lintang dan `-180` hingga `180` untuk bujur.
- Nilai pada `coord_uncertainty_km` memakai satuan kilometer. Pipeline menolak baris dengan ketidakpastian lebih dari `10` km (melebihi resolusi grid `1/12°` ≈ 9,2 km) ke dalam karantina.

## Contoh Baris Terisi

| sighting_id | platform | post_date | sighting_date | locality_text | lat_est | lon_est | coord_uncertainty_km | status_verifikasi | lat_koreksi | lon_koreksi | jumlah_individu | perilaku_konteks | catatan_dosen |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `yt_abc123` | `youtube` | `2024-07-15` | `2024-07-12` | `Teluk Saleh` | `-8.6333` | `117.9500` | `8.0` | `valid` | `-8.6120` | `117.9650` | `2` | `bagan` | `Terlihat dua individu di sekitar bagan apung.` |

## Langkah Setelah Verifikasi Selesai

1. Simpan lembar sebagai berkas CSV UTF-8.
2. Serahkan berkas kepada peneliti untuk divalidasi melalui `sheet_converter.py validate` menjadi `stages/01_occurrences/input/social_media_verified.csv` sebelum menjalankan [run_stage01.py](../run_stage01.py).
