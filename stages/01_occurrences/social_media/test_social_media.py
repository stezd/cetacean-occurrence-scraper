#!/usr/bin/env python3
"""Offline unit tests and run_stage01 round-trip tests for Stream 2 & Stream 3."""

from __future__ import annotations

import csv
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

STAGE_DIR = Path(__file__).resolve().parents[1]
if str(STAGE_DIR) not in sys.path:
    sys.path.insert(0, str(STAGE_DIR))

import run_stage01 as s1
from social_media import constants as c
from social_media import http_client as hc
from social_media import platform_stubs as stubs
from social_media import rss_news as rss
from social_media import scraper
from social_media import sheet_converter as sc
from social_media import youtube as yt


def _fake_response(status_code: int = 200, text: str = "", content: bytes = b"", headers: dict[str, str] | None = None, json_data=None):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content
    resp.headers = headers or {}
    if json_data is not None:
        resp.json.return_value = json_data
    elif text:
        resp.json.side_effect = lambda: json.loads(text)
    resp.iter_content.return_value = [content] if content else []
    if status_code >= 400:
        import requests
        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status_code}", response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestConstantsAndTemplate(unittest.TestCase):
    def test_template_csv_has_utf8_bom_and_expected_headers(self):
        self.assertTrue(c.TEMPLATE_CSV.exists(), f"Missing template: {c.TEMPLATE_CSV}")
        raw_bytes = c.TEMPLATE_CSV.read_bytes()
        self.assertTrue(raw_bytes.startswith(b"\xef\xbb\xbf"), "Template CSV must have UTF-8 BOM")
        with c.TEMPLATE_CSV.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            headers = next(reader)
        self.assertEqual(headers, c.SHEET_COLUMNS)
        for required_by_loader in (
            "sighting_id",
            "platform",
            "post_url",
            "locality_text",
            "lat_koreksi",
            "lon_koreksi",
            "lat_est",
            "lon_est",
            "coord_uncertainty_km",
            "sighting_date",
            "post_date",
            "status_verifikasi",
            "domain",
            "year",
            "month",
        ):
            self.assertIn(required_by_loader, headers)

    def test_hotspot_matching(self):
        self.assertEqual(c.match_hotspot("Hiu paus di Teluk Saleh NTB").name, "Teluk Saleh")
        self.assertEqual(c.match_hotspot("Pantai Botubarani Gorontalo").name, "Botubarani, Gorontalo")
        self.assertEqual(c.match_hotspot("Perairan Talisayan Berau").name, "Derawan / Talisayan")
        self.assertEqual(c.match_hotspot("Kwatisore Teluk Cenderawasih").name, "Teluk Cenderawasih")
        self.assertEqual(c.match_hotspot("Wisata hiu paus Probolinggo").name, "Probolinggo")
        self.assertIsNone(c.match_hotspot("Samudra Pasifik"))


class TestHttpClientAndRobots(unittest.TestCase):
    def test_robots_disallow_and_budget_cap(self):
        session = MagicMock()
        session.headers = {}

        def fake_get(url, params=None, timeout=20.0, stream=False):
            if url.endswith("/robots.txt"):
                return _fake_response(200, text="User-agent: *\nDisallow: /private/\nAllow: /feed/\n")
            return _fake_response(200, text="<rss/>")

        session.get.side_effect = fake_get
        client = hc.ThrottledHttpClient(min_delay_sec=0.0, max_requests=3, session=session)

        with self.assertRaises(hc.RobotsDisallowedError):
            client.get("https://example.org/private/secret.xml")

        # robots.txt took 1 request; /feed/ takes request #2
        resp = client.get("https://example.org/feed/news.xml")
        self.assertEqual(resp.status_code, 200)

        # Request #3 succeeds, #4 hits max_requests=3
        client.get("https://example.org/feed/more.xml")
        with self.assertRaises(hc.RequestBudgetExceeded):
            client.get("https://example.org/feed/overflow.xml")

    def test_download_media_writes_image_and_dedupes(self):
        session = MagicMock()
        session.headers = {}

        def fake_get(url, params=None, timeout=20.0, stream=False):
            if url.endswith("/robots.txt"):
                return _fake_response(404)
            return _fake_response(200, content=b"\xff\xd8\xff\xe0JPEGDATA", headers={"Content-Type": "image/jpeg"})

        session.get.side_effect = fake_get
        client = hc.ThrottledHttpClient(min_delay_sec=0.0, max_requests=10, session=session)

        with tempfile.TemporaryDirectory() as tmp:
            media_dir = Path(tmp) / "media"
            saved1 = client.download_media("https://cdn.example.org/img/ws.jpg", media_dir, "yt_abc123")
            self.assertIsNotNone(saved1)
            self.assertTrue((media_dir / "yt_abc123.jpg").exists())
            reqs_after_first = client.requests_made

            # Second download for same sighting_id skips HTTP call
            saved2 = client.download_media("https://cdn.example.org/img/ws.jpg", media_dir, "yt_abc123")
            self.assertEqual(saved1, saved2)
            self.assertEqual(client.requests_made, reqs_after_first)


class TestSourcesAndStubs(unittest.TestCase):
    def test_parse_rss_and_atom_and_reject_entity(self):
        rss_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
          <channel>
            <title>Berita Kelautan</title>
            <item>
              <title>Kemunculan Hiu Paus di Teluk Saleh</title>
              <link>https://news.example.id/hiu-paus-saleh</link>
              <pubDate>Tue, 15 Jul 2025 08:00:00 +0700</pubDate>
              <description>&lt;p&gt;Nelayan melihat dua &lt;b&gt;hiu paus&lt;/b&gt; di bagan.&lt;/p&gt;</description>
              <enclosure url="https://news.example.id/img/saleh.jpg" type="image/jpeg" />
            </item>
            <item>
              <title>Harga Ikan Tuna Naik</title>
              <link>https://news.example.id/tuna</link>
              <description>Berita pasar ikan biasa.</description>
            </item>
          </channel>
        </rss>"""
        recs = rss.parse_feed_xml(rss_xml, feed_url="https://news.example.id/feed")
        self.assertEqual(len(recs), 1)
        r = recs[0]
        self.assertEqual(r["platform"], "news_rss")
        self.assertEqual(r["post_date"], "2025-07-15")
        self.assertEqual(r["year"], 2025)
        self.assertEqual(r["month"], 7)
        self.assertEqual(r["locality_text"], "Teluk Saleh")
        self.assertAlmostEqual(r["lat_est"], -8.6333)
        self.assertEqual(r["media_url"], "https://news.example.id/img/saleh.jpg")

        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Whale shark spotted in Botubarani</title>
            <link rel="alternate" href="https://dive.example.id/botubarani" />
            <published>2024-04-10T02:00:00Z</published>
            <summary>Snorkelers saw Rhincodon typus near Gorontalo.</summary>
          </entry>
        </feed>"""
        atom_recs = rss.parse_feed_xml(atom_xml, feed_url="https://dive.example.id/atom", platform="dive_report")
        self.assertEqual(len(atom_recs), 1)
        self.assertEqual(atom_recs[0]["locality_text"], "Botubarani, Gorontalo")
        self.assertEqual(atom_recs[0]["post_date"], "2024-04-10")

        wp_posts = [
            {
                "id": 42,
                "link": "https://dive.example.id/posts/42",
                "date_gmt": "2025-02-01T10:00:00",
                "title": {"rendered": "Hiu Paus di Teluk Cenderawasih"},
                "excerpt": {"rendered": "<p>Penampakan <b>hiu paus</b> dekat bagan Kwatisore.</p>"},
                "content": {"rendered": '<p><img src="https://dive.example.id/pic.png" /></p>'},
            }
        ]
        wp_recs = rss.parse_wp_json_posts(wp_posts, feed_url="https://dive.example.id/wp-json/wp/v2/posts")
        self.assertEqual(len(wp_recs), 1)
        self.assertEqual(wp_recs[0]["sighting_id"], "news_rss_42")
        self.assertEqual(wp_recs[0]["locality_text"], "Teluk Cenderawasih")
        self.assertEqual(wp_recs[0]["media_url"], "https://dive.example.id/pic.png")

        with self.assertRaises(ValueError):
            rss.parse_feed_xml("<!DOCTYPE foo [<!ENTITY xxe 'bad'>]><rss/>", feed_url="https://bad.invalid")

    def test_youtube_parser_and_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(yt.MissingApiKeyError):
                yt.get_youtube_api_key(load_env=False)

        search_item = {
            "id": {"videoId": "vid12345"},
            "snippet": {
                "title": "Hiu Paus Talisayan Berau",
                "description": "Menyelam bersama whale shark",
                "publishedAt": "2023-10-05T04:00:00Z",
                "channelTitle": "Dive Indo",
                "thumbnails": {"high": {"url": "https://i.ytimg.com/vi/vid12345/hqdefault.jpg"}},
            },
        }
        detail_item = {
            "id": "vid12345",
            "snippet": search_item["snippet"],
            "recordingDetails": {
                "recordingDate": "2023-10-02T00:00:00Z",
                "locationDescription": "Talisayan, Berau",
                "location": {"latitude": 1.6512, "longitude": 118.2195},
            },
        }
        rec = yt.parse_youtube_item(search_item, detail_item, query_term='"hiu paus" "Talisayan"')
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec["sighting_id"], "youtube_vid12345")
        self.assertEqual(rec["post_date"], "2023-10-05")
        self.assertEqual(rec["sighting_date"], "2023-10-02")
        self.assertEqual(rec["month"], 10)
        self.assertAlmostEqual(rec["lat_est"], 1.6512)
        self.assertEqual(rec["coord_uncertainty_km"], 5.0)
        self.assertIn("[REDACTED]", yt._redact_secret("Error with secretXYZ and ?key=secretXYZ", "secretXYZ"))

        # Also test collect_youtube_sightings with mocked HTTP client
        yt_session = MagicMock()
        yt_session.headers = {}

        def fake_yt_get(url, params=None, timeout=20.0, stream=False):
            if url == yt.YOUTUBE_SEARCH_URL:
                return _fake_response(200, json_data={"items": [search_item]})
            if url == yt.YOUTUBE_VIDEOS_URL:
                return _fake_response(200, json_data={"items": [detail_item]})
            if url.endswith("/robots.txt"):
                return _fake_response(404)
            return _fake_response(200, content=b"\xff\xd8\xff\xe0THUMB", headers={"Content-Type": "image/jpeg"})

        yt_session.get.side_effect = fake_yt_get
        yt_client = hc.ThrottledHttpClient(min_delay_sec=0.0, max_requests=10, session=yt_session)
        with tempfile.TemporaryDirectory() as tmp:
            recs = yt.collect_youtube_sightings(
                yt_client,
                queries=['"hiu paus" "Talisayan"'],
                api_key="dummy-key-never-logged",
                download_media=True,
                media_dir=Path(tmp) / "media",
            )
            self.assertEqual(len(recs), 1)
            self.assertEqual(recs[0]["sighting_id"], "youtube_vid12345")
            self.assertTrue((Path(tmp) / "media" / "youtube_vid12345.jpg").exists())

    def test_platform_stubs_refuse_live_and_import_exports(self):
        for plat in ("instagram", "tiktok", "x"):
            with self.assertRaises(stubs.UnsupportedLiveScrapeError):
                stubs.scrape_stub(plat)

        ig_item = stubs.PLATFORM_EXPORT_SPECS["instagram"]["example_record"]
        rec = stubs.normalize_exported_record("instagram", ig_item)
        self.assertEqual(rec["platform"], "instagram")
        self.assertEqual(rec["sighting_id"], "instagram_17895695668004550")
        self.assertEqual(rec["sighting_date"], "2025-08-14")
        self.assertEqual(rec["locality_text"], "Labuan Jambu, Teluk Saleh")
        self.assertAlmostEqual(rec["lat_est"], -8.6333)

        with tempfile.TemporaryDirectory() as tmp:
            raw_jsonl = Path(tmp) / "raw.jsonl"
            app1, skip1 = scraper.append_raw_records(raw_jsonl, [rec])
            app2, skip2 = scraper.append_raw_records(raw_jsonl, [rec])
            self.assertEqual((app1, skip1), (1, 0))
            self.assertEqual((app2, skip2), (0, 1))


class TestConverterValidatorAndStage01RoundTrip(unittest.TestCase):
    def test_validator_rejects_bad_rows_and_reports_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            in_csv = tmp_dir / "reviewed.csv"
            out_csv = tmp_dir / "social_media_verified.csv"
            rej_csv = tmp_dir / "rejected.csv"

            rows = [
                # Accepted: valid
                {
                    "sighting_id": "yt_ok1",
                    "platform": "youtube",
                    "post_url": "https://youtube.com/watch?v=ok1",
                    "post_date": "2024-07-15",
                    "sighting_date": "2024-07-12",
                    "locality_text": "Teluk Saleh",
                    "lat_est": "-8.6333",
                    "lon_est": "117.9500",
                    "coord_uncertainty_km": "8.0",
                    "status_verifikasi": "valid",
                    "lat_koreksi": "-8.6100",
                    "lon_koreksi": "117.9600",
                    "jumlah_individu": "2",
                    "perilaku_konteks": "bagan",
                },
                # Accepted: repost (no coords needed)
                {
                    "sighting_id": "news_repost",
                    "platform": "news_rss",
                    "post_url": "https://news.example.id/1",
                    "post_date": "2024-08-01",
                    "status_verifikasi": "repost",
                },
                # Rejected: missing sighting_id
                {
                    "sighting_id": "",
                    "platform": "youtube",
                    "status_verifikasi": "valid",
                    "lat_est": "-8.5",
                    "lon_est": "118.0",
                },
                # Rejected: bad status_verifikasi
                {
                    "sighting_id": "yt_bad_status",
                    "platform": "youtube",
                    "status_verifikasi": "maybe",
                    "lat_est": "-8.5",
                    "lon_est": "118.0",
                },
                # Rejected: out-of-range latitude
                {
                    "sighting_id": "yt_bad_lat",
                    "platform": "youtube",
                    "status_verifikasi": "valid",
                    "lat_koreksi": "-95.5",
                    "lon_koreksi": "118.0",
                },
                # Rejected: incomplete coordinate pair
                {
                    "sighting_id": "yt_half_coord",
                    "platform": "youtube",
                    "status_verifikasi": "valid",
                    "lat_est": "-8.5",
                    "lon_est": "",
                },
                # Rejected: duplicate sighting_id
                {
                    "sighting_id": "yt_ok1",
                    "platform": "youtube",
                    "status_verifikasi": "tolak",
                },
            ]

            with in_csv.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=c.SHEET_COLUMNS)
                writer.writeheader()
                for r in rows:
                    full = {col: r.get(col, "") for col in c.SHEET_COLUMNS}
                    writer.writerow(full)

            report = sc.validate_verified_sheet(in_csv, out_csv=out_csv, rejected_csv=rej_csv, strict=False)
            self.assertEqual(report.total_rows, 7)
            self.assertEqual(len(report.accepted_rows), 2)
            self.assertEqual(len(report.rejected_rows), 5)
            self.assertEqual(report.status_counts, {"valid": 1, "repost": 1})
            self.assertEqual(report.rejection_counts["missing_sighting_id"], 1)
            self.assertEqual(report.rejection_counts["invalid_status_verifikasi"], 1)
            self.assertEqual(report.rejection_counts["coord_out_of_range:lat_koreksi/lon_koreksi"], 1)
            self.assertEqual(report.rejection_counts["incomplete_coord_pair:lat_est/lon_est"], 1)
            self.assertEqual(report.rejection_counts["duplicate_sighting_id"], 1)
            self.assertTrue(out_csv.exists())
            self.assertTrue(rej_csv.exists())

            # Strict mode must not overwrite/write output when rejected rows exist
            strict_out = tmp_dir / "strict_out.csv"
            strict_report = sc.validate_verified_sheet(in_csv, out_csv=strict_out, strict=True)
            self.assertEqual(len(strict_report.rejected_rows), 5)
            self.assertFalse(strict_out.exists())

    def test_end_to_end_round_trip_with_run_stage01(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            raw_jsonl = tmp_dir / "social_media_raw.jsonl"
            unverified_csv = tmp_dir / "social_media_unverified.csv"
            reviewed_csv = tmp_dir / "social_media_reviewed.csv"
            verified_csv = tmp_dir / "social_media_verified.csv"

            # 1. Produce raw JSONL records from RSS + Instagram export stub
            raw_records = [
                {
                    "sighting_id": "yt_saleh_ok",
                    "platform": "youtube",
                    "post_url": "https://www.youtube.com/watch?v=saleh_ok",
                    "local_media_path": "stages/01_occurrences/input/social_media/media/yt_saleh_ok.jpg",
                    "caption_raw": "Hiu paus muncul di Teluk Saleh",
                    "post_date": "2024-07-15",
                    "sighting_date": "2024-07-12",
                    "year": 2024,
                    "month": 7,
                    "domain": "ID",
                    "locality_text": "Teluk Saleh",
                    "lat_est": -8.6333,
                    "lon_est": 117.95,
                    "coord_uncertainty_km": 8.0,
                },
                {
                    "sighting_id": "news_high_unc",
                    "platform": "news_rss",
                    "post_url": "https://news.example.id/unc",
                    "local_media_path": "",
                    "caption_raw": "Hiu paus di perairan Indonesia timur",
                    "post_date": "2023-01-20",
                    "sighting_date": "",
                    "year": 2023,
                    "month": 1,
                    "domain": "ID",
                    "locality_text": "Maluku",
                    "lat_est": -3.5,
                    "lon_est": 128.0,
                    "coord_uncertainty_km": 25.0,
                },
                {
                    "sighting_id": "ig_old_year",
                    "platform": "instagram",
                    "post_url": "https://www.instagram.com/p/OLD2008/",
                    "local_media_path": "",
                    "caption_raw": "Foto lama hiu paus tahun 2008 di Probolinggo",
                    "post_date": "2022-05-01",
                    "sighting_date": "2008-05-01",
                    "year": 2008,
                    "month": 5,
                    "domain": "ID",
                    "locality_text": "Probolinggo",
                    "lat_est": -7.73,
                    "lon_est": 113.28,
                    "coord_uncertainty_km": 8.0,
                },
                {
                    "sighting_id": "tiktok_missing_coords",
                    "platform": "tiktok",
                    "post_url": "https://www.tiktok.com/@u/video/1",
                    "local_media_path": "",
                    "caption_raw": "Hiu paus di tengah laut",
                    "post_date": "2025-04-11",
                    "sighting_date": "2025-04-11",
                    "year": 2025,
                    "month": 4,
                    "domain": "ID",
                    "locality_text": "",
                    "lat_est": None,
                    "lon_est": None,
                    "coord_uncertainty_km": None,
                },
                {
                    "sighting_id": "x_repost",
                    "platform": "x",
                    "post_url": "https://x.com/u/status/99",
                    "local_media_path": "",
                    "caption_raw": "Repost video hiu paus Gorontalo",
                    "post_date": "2024-06-05",
                    "sighting_date": "2024-06-01",
                    "year": 2024,
                    "month": 6,
                    "domain": "ID",
                    "locality_text": "Botubarani, Gorontalo",
                    "lat_est": 0.4917,
                    "lon_est": 123.1067,
                    "coord_uncertainty_km": 5.0,
                },
                {
                    "sighting_id": "news_ragu",
                    "platform": "news_rss",
                    "post_url": "https://news.example.id/ragu",
                    "local_media_path": "",
                    "caption_raw": "Ikan besar mirip hiu paus",
                    "post_date": "2024-10-03",
                    "sighting_date": "",
                    "year": 2024,
                    "month": 10,
                    "domain": "ID",
                    "locality_text": "Derawan / Talisayan",
                    "lat_est": 1.65,
                    "lon_est": 118.22,
                    "coord_uncertainty_km": 8.0,
                },
                {
                    "sighting_id": "yt_tolak",
                    "platform": "youtube",
                    "post_url": "https://www.youtube.com/watch?v=tolak1",
                    "local_media_path": "",
                    "caption_raw": "Ternyata paus sperma bukan hiu paus",
                    "post_date": "2024-03-18",
                    "sighting_date": "",
                    "year": 2024,
                    "month": 3,
                    "domain": "ID",
                    "locality_text": "Teluk Cenderawasih",
                    "lat_est": -3.2167,
                    "lon_est": 134.96,
                    "coord_uncertainty_km": 9.0,
                },
            ]
            appended, _ = scraper.append_raw_records(raw_jsonl, raw_records)
            self.assertEqual(appended, len(raw_records))

            # 2. Convert JSONL -> unverified CSV (status_verifikasi empty)
            conv_counts = sc.jsonl_to_unverified_sheet([raw_jsonl], out_csv=unverified_csv)
            self.assertEqual(conv_counts["written_rows"], len(raw_records))

            with unverified_csv.open("r", encoding="utf-8-sig", newline="") as f:
                unv_rows = list(csv.DictReader(f))
            self.assertTrue(all(r["status_verifikasi"] == "" for r in unv_rows))

            # 3. Simulate Pembimbing 2 filling in statuses + corrections (+ one invalid row to test rejection)
            statuses = {
                "yt_saleh_ok": ("valid", "-8.6120", "117.9650", "2", "bagan", "Terverifikasi valid"),
                "news_high_unc": ("valid", "", "", "", "", "Lokasi terlalu umum"),
                "ig_old_year": ("valid", "", "", "", "wisata", "Dokumentasi arsip 2008"),
                "tiktok_missing_coords": ("valid", "", "", "", "melintas", "Tidak ada koordinat"),
                "x_repost": ("repost", "", "", "", "", "Unggahan ulang"),
                "news_ragu": ("ragu", "", "", "", "", "Foto buram"),
                "yt_tolak": ("tolak", "", "", "", "", "Bukan Rhincodon typus"),
            }
            for r in unv_rows:
                st, lk, lnk, ji, pk, cat = statuses[r["sighting_id"]]
                r["status_verifikasi"] = st
                r["lat_koreksi"] = lk
                r["lon_koreksi"] = lnk
                r["jumlah_individu"] = ji
                r["perilaku_konteks"] = pk
                r["catatan_dosen"] = cat

            # Add an invalid row (bad coordinates) that must be rejected before Stage 01
            bad_row = {col: "" for col in c.SHEET_COLUMNS}
            bad_row["sighting_id"] = "bad_coord_row"
            bad_row["status_verifikasi"] = "valid"
            bad_row["lat_koreksi"] = "120.0"
            bad_row["lon_koreksi"] = "118.0"
            unv_rows.append(bad_row)

            with reviewed_csv.open("w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=c.SHEET_COLUMNS)
                writer.writeheader()
                writer.writerows(unv_rows)

            # 4. Validate reviewed CSV -> social_media_verified.csv
            report = sc.validate_verified_sheet(reviewed_csv, out_csv=verified_csv)
            self.assertEqual(len(report.accepted_rows), 7)
            self.assertEqual(len(report.rejected_rows), 1)

            # 5. Round-trip through run_stage01.normalize_social_media_row() & evaluate_row()
            reasons_by_id: dict[str, str | None] = {}
            normalized_by_id: dict[str, dict] = {}
            with verified_csv.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    nr = s1.normalize_social_media_row(row)
                    normalized_by_id[nr["source_record_id"]] = nr
                    reasons_by_id[nr["source_record_id"]] = s1.evaluate_row(nr)

            self.assertNotIn("bad_coord_row", reasons_by_id)
            self.assertIsNone(reasons_by_id["yt_saleh_ok"])
            self.assertAlmostEqual(normalized_by_id["yt_saleh_ok"]["latitude"], -8.6120)
            self.assertAlmostEqual(normalized_by_id["yt_saleh_ok"]["longitude"], 117.9650)
            self.assertEqual(normalized_by_id["yt_saleh_ok"]["season"], "SEM")

            self.assertEqual(reasons_by_id["news_high_unc"], "high_uncertainty")
            self.assertEqual(reasons_by_id["ig_old_year"], "out_of_temporal_window")
            self.assertEqual(reasons_by_id["tiktok_missing_coords"], "missing_coords")
            self.assertEqual(reasons_by_id["x_repost"], "unverified_social_media")
            self.assertEqual(reasons_by_id["news_ragu"], "unverified_social_media")
            self.assertEqual(reasons_by_id["yt_tolak"], "unverified_social_media")


if __name__ == "__main__":
    unittest.main()
