#!/usr/bin/env python3
"""Unit tests for Stage 01 occurrence cleaning, deduplication, thinning, and fetcher CLI."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
from scipy.io import netcdf_file

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_gbif_cetaceans as fetcher
import run_stage01 as s1


class TestStage01(unittest.TestCase):
    def test_seasons(self):
        self.assertEqual(s1.determine_season(12), "NWM")
        self.assertEqual(s1.determine_season(2), "NWM")
        self.assertEqual(s1.determine_season(3), "TR1")
        self.assertEqual(s1.determine_season(5), "TR1")
        self.assertEqual(s1.determine_season(6), "SEM")
        self.assertEqual(s1.determine_season(8), "SEM")
        self.assertEqual(s1.determine_season(9), "TR2")
        self.assertEqual(s1.determine_season(11), "TR2")
        self.assertEqual(s1.determine_season(None), "UNKNOWN")

    def test_bogus_uncertainty_treated_as_empty(self):
        for bogus in (301, 3036, 999, 9999):
            self.assertIsNone(s1.clean_uncertainty(bogus))
        self.assertEqual(s1.clean_uncertainty(5000), 5000.0)

    def test_quarantine_rules(self):
        gbif_valid = s1.normalize_gbif_row({
            "gbifID": 1,
            "taxonKey": 2417522,
            "species": "Rhincodon typus",
            "decimalLatitude": -8.5,
            "decimalLongitude": 118.0,
            "coordinateUncertaintyInMeters": 9999,
            "year": 2022,
            "month": 10,
            "eventDate": "2022-10-15",
            "basisOfRecord": "HUMAN_OBSERVATION",
            "occurrenceStatus": "PRESENT",
        }, "ID")
        self.assertIsNone(s1.evaluate_row(gbif_valid))
        self.assertIsNone(gbif_valid["coordinate_uncertainty_m"])

        sm_ragu = s1.normalize_social_media_row({
            "sighting_id": "sm1",
            "status_verifikasi": "ragu",
            "lat_est": "-8.5",
            "lon_est": "118.0",
            "sighting_date": "2024-01-10",
        })
        self.assertEqual(s1.evaluate_row(sm_ragu), "unverified_social_media")

        obis_land = s1.normalize_obis_row({
            "id": "ob1",
            "species": "Rhincodon typus",
            "decimalLatitude": -8.5,
            "decimalLongitude": 118.1,
            "date_year": 2020,
            "eventDate": "2020-07-01",
            "bathymetry": -13,
            "flags": ["ON_LAND"],
        }, "ID")
        self.assertEqual(s1.evaluate_row(obis_land), "on_land")

        obis_sea = s1.normalize_obis_row({
            "id": "ob2",
            "species": "Rhincodon typus",
            "decimalLatitude": -8.5,
            "decimalLongitude": 118.0,
            "date_year": 2020,
            "eventDate": "2020-07-01",
            "bathymetry": 112,
            "flags": ["NO_DEPTH"],
        }, "ID")
        self.assertIsNone(s1.evaluate_row(obis_sea))

    def test_cross_source_dedupe_keeps_smaller_uncertainty(self):
        r1 = s1.normalize_gbif_row({
            "gbifID": 10,
            "taxonKey": 2417522,
            "species": "Rhincodon typus",
            "decimalLatitude": -8.50001,
            "decimalLongitude": 118.00001,
            "coordinateUncertaintyInMeters": 5000,
            "year": 2021,
            "month": 7,
            "eventDate": "2021-07-12T10:00:00Z",
            "basisOfRecord": "HUMAN_OBSERVATION",
        }, "ID")
        r2 = s1.normalize_obis_row({
            "id": "ob-10",
            "species": "Rhincodon typus",
            "decimalLatitude": -8.50002,
            "decimalLongitude": 118.00002,
            "coordinateUncertaintyInMeters": 250,
            "date_year": 2021,
            "eventDate": "2021-07-12",
            "bathymetry": 150,
        }, "ID")
        clean, dup_q = s1.dedupe_rows([r1, r2])
        self.assertEqual(len(clean), 1)
        self.assertEqual(clean[0]["source_stream"], "obis")
        self.assertEqual(len(dup_q), 1)
        self.assertEqual(dup_q[0]["quarantine_reason"], "duplicate_cross_source")

    def test_greedy_thin_enforces_10km(self):
        rows = [
            s1.normalize_gbif_row({
                "gbifID": i,
                "taxonKey": 2417522,
                "species": "Rhincodon typus",
                "decimalLatitude": -8.5 + i * 0.02,
                "decimalLongitude": 118.0,
                "year": 2022,
                "month": 7,
                "eventDate": "2022-07-01",
            }, "ID")
            for i in range(10)
        ]
        thinned = s1.greedy_thin(rows, 10.0)
        self.assertGreater(len(thinned), 1)
        self.assertGreaterEqual(s1.min_pairwise_km(thinned), 10.0)

    def test_fetcher_cli_backwards_compat(self):
        legacy = fetcher.parse_args(["AU", "5000"])
        self.assertEqual(legacy.country_code, "AU")
        self.assertEqual(legacy.max_records, 5000)
        self.assertEqual(legacy.taxon_key, 733)

        ws = fetcher.parse_args(["ID", "2000", "--taxon-key", "2417522", "--year", "2010,2026"])
        self.assertEqual(ws.taxon_key, 2417522)
        self.assertEqual(ws.year, "2010,2026")

    def test_gebco_land_mask_and_sign_convention(self):
        lats = np.array([-9.0, -8.5, -8.0])
        lons = np.array([117.5, 118.0, 118.5])
        # Negative = ocean, 0 or positive = land
        elev = np.array([
            [-120, -45, 0],
            [-10, 15, 250],
            [5, 80, -30],
        ], dtype=np.int16)
        raster = s1.GebcoRaster.from_arrays(lats, lons, elev)

        def make_gbif(gid, lat, lon):
            return s1.normalize_gbif_row({
                "gbifID": gid,
                "taxonKey": 2417522,
                "species": "Rhincodon typus",
                "decimalLatitude": lat,
                "decimalLongitude": lon,
                "year": 2022,
                "month": 7,
                "eventDate": "2022-07-01",
                "basisOfRecord": "HUMAN_OBSERVATION",
            }, "ID")

        # Ocean cell (-9.0, 118.0 -> -45 m) passes
        ocean_row = make_gbif(101, -9.0, 118.0)
        self.assertIsNone(s1.evaluate_row(ocean_row, gebco_sampler=raster))
        self.assertEqual(ocean_row["gebco_elevation_m"], -45)

        # Sea-level boundary (-9.0, 118.5 -> 0 m) is quarantined as on_land
        zero_row = make_gbif(102, -9.0, 118.5)
        self.assertEqual(s1.evaluate_row(zero_row, gebco_sampler=raster), "on_land")
        self.assertEqual(zero_row["gebco_elevation_m"], 0)
        self.assertEqual(zero_row["_on_land_source"], "gebco")

        # Positive elevation (-8.5, 118.0 -> +15 m) is quarantined as on_land
        land_row = make_gbif(103, -8.5, 118.0)
        self.assertEqual(s1.evaluate_row(land_row, gebco_sampler=raster), "on_land")
        self.assertEqual(land_row["gebco_elevation_m"], 15)

        # Sign trap: OBIS positive bathymetry (+50 m depth) + GEBCO negative (-45 m) passes
        obis_ok = s1.normalize_obis_row({
            "id": "ob-ok",
            "species": "Rhincodon typus",
            "decimalLatitude": -9.0,
            "decimalLongitude": 118.0,
            "date_year": 2022,
            "eventDate": "2022-07-01",
            "bathymetry": 50,
        }, "ID")
        self.assertIsNone(s1.evaluate_row(obis_ok, gebco_sampler=raster))

        # Out-of-bounds query returns None cleanly without marking on_land
        oob_row = make_gbif(104, -5.0, 118.0)
        self.assertIsNone(s1.evaluate_row(oob_row, gebco_sampler=raster))
        self.assertIsNone(oob_row["gebco_elevation_m"])

    def test_kde_background_reproducible_and_ocean_only(self):
        # Coastal split grid: lat < 0.0 is ocean (-80 m), lat >= 0.0 is land (+40 m)
        lats = np.linspace(-2.0, 2.0, 41)
        lons = np.linspace(116.0, 120.0, 41)
        elev = np.where(lats[:, None] < 0.0, -80, 40).astype(np.int16)
        elev = np.broadcast_to(elev, (lats.size, lons.size)).copy()
        raster = s1.GebcoRaster.from_arrays(lats, lons, elev)

        pres = [
            s1.normalize_gbif_row({
                "gbifID": 1,
                "taxonKey": 2417522,
                "species": "Rhincodon typus",
                "decimalLatitude": -0.05,
                "decimalLongitude": 118.0,
                "year": 2023,
                "month": 4,
                "eventDate": "2023-04-10",
            }, "ID"),
            s1.normalize_gbif_row({
                "gbifID": 2,
                "taxonKey": 2417522,
                "species": "Rhincodon typus",
                "decimalLatitude": -0.20,
                "decimalLongitude": 118.3,
                "year": 2023,
                "month": 5,
                "eventDate": "2023-05-12",
            }, "ID"),
        ]

        bg1 = s1.sample_kde_background(pres, raster.elevations_at, domain="ID", n_points=300, bandwidth_km=25.0, seed=12345)
        bg2 = s1.sample_kde_background(pres, raster.elevations_at, domain="ID", n_points=300, bandwidth_km=25.0, seed=12345)
        bg3 = s1.sample_kde_background(pres, raster.elevations_at, domain="ID", n_points=300, bandwidth_km=25.0, seed=99999)

        self.assertEqual(len(bg1), 300)
        self.assertEqual(bg1, bg2)
        self.assertNotEqual(bg1, bg3)
        self.assertTrue(all(r["gebco_elevation_m"] < 0 for r in bg1))
        self.assertTrue(all(r["latitude"] < 0.0 for r in bg1))

        # All-land raster fails fast instead of hanging
        land_only = s1.GebcoRaster.from_arrays(lats, lons, np.full_like(elev, 10))
        with self.assertRaises(RuntimeError):
            s1.sample_kde_background(pres, land_only.elevations_at, domain="ID", n_points=10, max_batches=3)

    def test_synthetic_netcdf_end_to_end_pipeline(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raw_dir = tmp / "raw"
            in_dir = tmp / "input"
            out_dir = tmp / "output"
            raw_dir.mkdir()
            in_dir.mkdir()
            nc_path = tmp / "tiny_gebco.nc"

            lats = np.linspace(-25.0, -5.0, 21)
            lons = np.linspace(110.0, 130.0, 21)
            elev = np.full((lats.size, lons.size), -100, dtype=np.int16)
            # Mark northern cells (lat >= -8.0) as land (+20 m)
            elev[lats >= -8.0, :] = 20

            with netcdf_file(nc_path, "w") as nc:
                nc.createDimension("lat", lats.size)
                nc.createDimension("lon", lons.size)
                vlat = nc.createVariable("lat", "d", ("lat",))
                vlon = nc.createVariable("lon", "d", ("lon",))
                velev = nc.createVariable("elevation", "h", ("lat", "lon"))
                vlat[:] = lats
                vlon[:] = lons
                velev[:] = elev

            (raw_dir / "gbif_id.jsonl").write_text("\n".join([
                json.dumps({
                    "gbifID": 1, "taxonKey": 2417522, "species": "Rhincodon typus",
                    "decimalLatitude": -10.0, "decimalLongitude": 118.0,
                    "year": 2022, "month": 7, "eventDate": "2022-07-01",
                }),
                json.dumps({
                    "gbifID": 2, "taxonKey": 2417522, "species": "Rhincodon typus",
                    "decimalLatitude": -7.0, "decimalLongitude": 118.0,
                    "year": 2022, "month": 7, "eventDate": "2022-07-02",
                }),
            ]) + "\n", encoding="utf-8")
            (raw_dir / "gbif_au.jsonl").write_text(json.dumps({
                "gbifID": 3, "taxonKey": 2417522, "species": "Rhincodon typus",
                "decimalLatitude": -20.0, "decimalLongitude": 114.0,
                "year": 2023, "month": 1, "eventDate": "2023-01-15",
            }) + "\n", encoding="utf-8")
            (raw_dir / "obis_id.jsonl").write_text("", encoding="utf-8")
            (raw_dir / "obis_au.jsonl").write_text("", encoding="utf-8")

            with (
                mock.patch.object(s1, "RAW_DIR", raw_dir),
                mock.patch.object(s1, "INPUT_DIR", in_dir),
                mock.patch.object(s1, "OUTPUT_DIR", out_dir),
            ):
                s1.run_pipeline(from_raw=True, gebco_path=nc_path, background_count=25, background_seed=77)

            check_text = (out_dir / "check.md").read_text(encoding="utf-8")
            first_line = check_text.splitlines()[0]
            self.assertTrue(first_line.startswith("fail:"), first_line)
            self.assertIn("GEBCO raster land mask: APPLIED", check_text)
            self.assertIn("25 km Gaussian KDE ocean background: APPLIED (ID=25, AU=25; 0 on land", check_text)
            self.assertTrue((out_dir / "background_id.csv").exists())
            self.assertTrue((out_dir / "background_au.csv").exists())
            id_clean = (out_dir / "rhincodon_id_clean.csv").read_text(encoding="utf-8")
            self.assertIn("1,", id_clean)
            self.assertNotIn(",2,", id_clean)


if __name__ == "__main__":
    unittest.main()
