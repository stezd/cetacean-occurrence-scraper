#!/usr/bin/env python3
"""Tests for _tools/verify_stages.py against synthetic fixtures and the live Stage 01 output."""

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "_tools"))

import verify_stages as vs

PRESENCE_COLUMNS = [
    "source_stream",
    "source_record_id",
    "domain",
    "latitude",
    "longitude",
    "coordinate_uncertainty_m",
    "year",
    "month",
    "season",
    "event_date",
    "event_date_day",
]
BACKGROUND_COLUMNS = [
    "domain",
    "latitude",
    "longitude",
    "gebco_elevation_m",
    "kde_bandwidth_km",
    "source_stream",
]
BASE = {"id": (-8.0, 110.0), "au": (-25.0, 115.0)}
SPACING_DEG = 0.25  # ~27.8 km, so no synthetic pair ever falls under the 10 km threshold


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def presence_rows(domain: str, per_season: int = 2) -> list[dict[str, str]]:
    lat0, lon0 = BASE[domain]
    rows: list[dict[str, str]] = []
    index = 0
    for season in vs.SEASONS:
        for _ in range(per_season):
            rows.append(
                {
                    "source_stream": "gbif",
                    "source_record_id": f"{domain}-{index:03d}",
                    "domain": domain.upper(),
                    "latitude": f"{lat0 + SPACING_DEG * index:.6f}",
                    "longitude": f"{lon0:.6f}",
                    "coordinate_uncertainty_m": "500.0",
                    "year": "2015",
                    "month": "1",
                    "season": season,
                    "event_date": f"2015-01-{index + 1:02d}T00:00:00Z",
                    "event_date_day": f"2015-01-{index + 1:02d}",
                }
            )
            index += 1
    return rows


def background_rows(domain: str, count: int = vs.BACKGROUND_COUNT_PER_DOMAIN) -> list[dict[str, str]]:
    lat0, lon0 = BASE[domain]
    return [
        {
            "domain": domain.upper(),
            "latitude": f"{lat0 + 0.001 * (index % 100):.6f}",
            "longitude": f"{lon0 + 0.001 * (index // 100):.6f}",
            "gebco_elevation_m": "-100",
            "kde_bandwidth_km": "25.0",
            "source_stream": "background_kde",
        }
        for index in range(count)
    ]


def build_tree(base: Path) -> Path:
    """Write a complete, valid Stage 01 output tree under base and return the output dir."""
    output = base / "stages" / "01_occurrences" / "output"
    output.mkdir(parents=True, exist_ok=True)
    for domain in vs.DOMAINS:
        clean = presence_rows(domain)
        write_csv(output / f"rhincodon_{domain}_clean.csv", PRESENCE_COLUMNS, clean)
        for season in vs.SEASONS:
            partition = [row for row in clean if row["season"] == season]
            write_csv(
                output / f"rhincodon_{domain}_{season.lower()}.csv",
                PRESENCE_COLUMNS,
                partition,
            )
        write_csv(output / f"background_{domain}.csv", BACKGROUND_COLUMNS, background_rows(domain))
    write_csv(
        output / "quarantine.csv",
        ["source_stream", "latitude", "longitude", "quarantine_reason"],
        [{"source_stream": "gbif", "latitude": "", "longitude": "", "quarantine_reason": "missing_coords"}],
    )
    (output / "check.md").write_text("pass\n\nGenerated: 2026-11-14T00:00:00+07:00\n", encoding="utf-8")
    return output


class VerifyStagesCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base = Path(self._tmp.name)
        self.output = build_tree(self.base)
        self.roots = [self.base / "stages", self.base / "_shared", self.base / "_tools"]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def verify(self) -> dict[str, vs.Check]:
        return {check.name: check for check in vs.verify_stage01(self.output, self.roots)}

    def run_cli(self) -> tuple[int, str]:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = vs.main(["--root", str(self.base)])
        return code, buffer.getvalue()

    def assert_only_failures(self, checks: dict[str, vs.Check], *names: str) -> None:
        failing = [name for name, check in checks.items() if not check.ok]
        self.assertEqual(sorted(failing), sorted(names), msg={n: c.detail for n, c in checks.items()})


class TestValidFixtures(VerifyStagesCase):
    def test_valid_fixture_passes(self) -> None:
        checks = self.verify()
        self.assertEqual(len(checks), 8)
        self.assert_only_failures(checks)

    def test_cli_exit_zero_and_deterministic(self) -> None:
        first_code, first_out = self.run_cli()
        second_code, second_out = self.run_cli()
        self.assertEqual(first_code, 0)
        self.assertEqual(first_code, second_code)
        self.assertEqual(first_out, second_out)
        self.assertIn("0 FAIL", first_out)

    def test_live_stage01_output_passes(self) -> None:
        live_output = ROOT / "stages" / "01_occurrences" / "output"
        checks = vs.verify_stage01(
            live_output, [ROOT / "stages", ROOT / "_shared", ROOT / "_tools"]
        )
        failing = {
            check.name: (check.detail, check.examples)
            for check in checks
            if not check.ok
        }
        self.assertEqual(failing, {})
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = vs.main([])
        self.assertEqual(code, 0, msg=buffer.getvalue())
        self.assertIn("0 FAIL", buffer.getvalue())

    def test_allowed_noqa_rule_code_passes_hygiene(self) -> None:
        tools = self.base / "_tools"
        tools.mkdir(exist_ok=True)
        (tools / "clean.py").write_text("# " + "no" + "qa: E501\nvalue = 1\n", encoding="utf-8")
        checks = self.verify()
        self.assertTrue(checks["escape-hatch hygiene"].ok, msg=checks["escape-hatch hygiene"].examples)


class TestCorruptFixtures(VerifyStagesCase):
    def test_nan_coordinate_fails(self) -> None:
        path = self.output / "rhincodon_id_nwm.csv"
        rows = read_csv(path)
        rows[0]["latitude"] = "NaN"
        write_csv(path, PRESENCE_COLUMNS, rows)

        checks = self.verify()
        self.assertFalse(checks["coordinates finite / non-null / non-zero"].ok)
        self.assertTrue(
            any("not finite numeric" in example for example in checks["coordinates finite / non-null / non-zero"].examples),
            msg=checks["coordinates finite / non-null / non-zero"].examples,
        )
        code, output = self.run_cli()
        self.assertEqual(code, 1)
        self.assertIn("1 FAIL" if len([c for c in checks.values() if not c.ok]) == 1 else "FAIL", output)

    def test_null_island_fails(self) -> None:
        for name in ("rhincodon_id_nwm.csv", "rhincodon_id_clean.csv"):
            path = self.output / name
            rows = read_csv(path)
            rows[0]["latitude"] = "0.0"
            rows[0]["longitude"] = "0.0"
            write_csv(path, PRESENCE_COLUMNS, rows)

        checks = self.verify()
        coordinate_check = checks["coordinates finite / non-null / non-zero"]
        self.assertFalse(coordinate_check.ok)
        self.assertTrue(
            any("null island" in example for example in coordinate_check.examples),
            msg=coordinate_check.examples,
        )

    def test_out_of_bounds_coordinate_fails_only_bbox(self) -> None:
        outside_lat = "-45.0"  # south of the 40S edge of the GEBCO subset
        for name in ("rhincodon_id_nwm.csv", "rhincodon_id_clean.csv"):
            path = self.output / name
            rows = read_csv(path)
            rows[0]["latitude"] = outside_lat
            write_csv(path, PRESENCE_COLUMNS, rows)

        checks = self.verify()
        self.assertFalse(checks["study-area bounding box (90-160E, 40S-20N)"].ok)
        self.assertTrue(checks["coordinates finite / non-null / non-zero"].ok)
        self.assertTrue(checks["seasonal partition conservation (ID, AU)"].ok)
        self.assertTrue(checks["spatial thinning >= 10.0 km haversine"].ok)
        self.assert_only_failures(checks, "study-area bounding box (90-160E, 40S-20N)")
        code, _ = self.run_cli()
        self.assertEqual(code, 1)

    def test_missing_seasonal_row_fails_conservation(self) -> None:
        path = self.output / "rhincodon_au_tr2.csv"
        rows = read_csv(path)
        dropped = rows.pop()["source_record_id"]
        write_csv(path, PRESENCE_COLUMNS, rows)

        checks = self.verify()
        conservation = checks["seasonal partition conservation (ID, AU)"]
        self.assertFalse(conservation.ok)
        self.assertTrue(
            any(dropped in example for example in conservation.examples),
            msg=conservation.examples,
        )
        self.assert_only_failures(checks, "seasonal partition conservation (ID, AU)")

    def test_unthinned_duplicate_pair_fails_thinning(self) -> None:
        clean_path = self.output / "rhincodon_id_clean.csv"
        slice_path = self.output / "rhincodon_id_nwm.csv"
        clean = read_csv(clean_path)
        clone = dict(clean[0])
        clone["source_record_id"] = "id-dup"
        clone["latitude"] = f"{float(clone['latitude']) + 0.001:.6f}"  # ~111 m away
        clean.append(clone)
        write_csv(clean_path, PRESENCE_COLUMNS, clean)
        write_csv(slice_path, PRESENCE_COLUMNS, read_csv(slice_path) + [clone])

        checks = self.verify()
        thinning = checks["spatial thinning >= 10.0 km haversine"]
        self.assertFalse(thinning.ok)
        self.assertTrue(any("0.1" in example for example in thinning.examples), msg=thinning.examples)
        self.assertFalse(checks["seasonal partition conservation (ID, AU)"].ok)
        self.assertTrue(checks["coordinates finite / non-null / non-zero"].ok)

    def test_broken_background_count_fails(self) -> None:
        path = self.output / "background_au.csv"
        rows = read_csv(path)
        write_csv(path, BACKGROUND_COLUMNS, rows[:100])
        checks = self.verify()
        self.assertFalse(checks["background integrity (10000 ocean points per domain)"].ok)
        self.assert_only_failures(checks, "background integrity (10000 ocean points per domain)")

    def test_land_background_point_fails(self) -> None:
        path = self.output / "background_id.csv"
        rows = read_csv(path)
        rows[7]["gebco_elevation_m"] = "12"
        write_csv(path, BACKGROUND_COLUMNS, rows)
        checks = self.verify()
        self.assertFalse(checks["background integrity (10000 ocean points per domain)"].ok)

    def test_malformed_check_status_fails(self) -> None:
        (self.output / "check.md").write_text("ok\n", encoding="utf-8")
        checks = self.verify()
        self.assertFalse(checks["check.md status line"].ok)
        self.assert_only_failures(checks, "check.md status line")

    def test_missing_artifact_fails(self) -> None:
        (self.output / "background_au.csv").unlink()
        checks = self.verify()
        self.assertFalse(checks["required artifacts"].ok)
        self.assertFalse(checks["coordinates finite / non-null / non-zero"].ok)
        self.assertFalse(checks["background integrity (10000 ocean points per domain)"].ok)
        self.assertIn("missing background_au.csv", checks["required artifacts"].examples)


class TestHygieneScan(VerifyStagesCase):
    def test_escape_hatches_detected(self) -> None:
        tools = self.base / "_tools"
        tools.mkdir(exist_ok=True)
        markers = [
            "# " + "type:" + " ignore",
            "# " + "no" + "qa",
            "TODO" + ": fix" + " later",
            "value = 1  # " + "HA" + "CK:" + " temporary",
            "# " + "no" + "qa: E501",
        ]
        (tools / "offender.py").write_text("\n".join(markers) + "\n", encoding="utf-8")

        checks = self.verify()
        hygiene = checks["escape-hatch hygiene"]
        self.assertFalse(hygiene.ok)
        self.assertIn("4 escape hatches", hygiene.detail)
        self.assert_only_failures(checks, "escape-hatch hygiene")


if __name__ == "__main__":
    unittest.main()
