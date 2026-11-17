#!/usr/bin/env python3
"""Verify whale-scraper stage outputs for silent data corruption. Exit 1 on any violation.

Standard library only. Run from anywhere:

    python -I _tools/verify_stages.py
    python -I _tools/verify_stages.py --output-dir stages/01_occurrences/output
    python -I _tools/verify_stages.py --root <repo> --scan-root stages --scan-root _tools

Stage 01 invariants (contract: stages/01_occurrences/CONTEXT.md "Check"):

1. Required artifacts exist, and output/check.md starts with `pass` or `fail: <why>`.
2. Coordinates: clean, seasonal, and background rows carry finite numeric latitude and
   longitude - never empty, `NaN`, `Inf`, out of range, or the (0, 0) null island.
3. Study area: every seasonal and background row lies inside the GEBCO subset the land mask
   covers - 90E-160E, 40S-20N (`data/gebco/SOURCE.md`). A row outside it is invisible to the
   mask, so `on_land` filtering silently skips it.
4. Seasonal partition conservation: every clean row is accounted for exactly once - either
   tagged `UNKNOWN` (excluded from seasonal slices by design) or inside exactly one season's
   pre-thinning partition - and every seasonal output row belongs to its own season's
   partition and is reproduced by the deterministic 10 km greedy thinning of that partition.
   Post-thinning file sizes are smaller than the clean row count by design, so the files are
   compared against the recomputed thinning, not against `rhincodon_<domain>_clean.csv`.
5. Spatial thinning: every pair inside a seasonal file is at least 10 km apart (haversine).
6. Background: 10,000 points per domain, 25 km KDE bandwidth, ocean cells only (GEBCO
   elevation < 0 m) - a truncated or land-contaminated background file corrupts the model
   without any error.
7. Escape-hatch hygiene: no `type: ignore`, bare `noqa` without a rule code, deferred-fix
   markers, or hack markers in the Python sources under stages/, _shared/, _tools/.
"""

from __future__ import annotations

import csv
import math
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOMAINS = ("id", "au")
SEASONS = ("NWM", "TR1", "SEM", "TR2")
THIN_DISTANCE_KM = 10.0
EARTH_RADIUS_KM = 6371.0088
KDE_BANDWIDTH_KM = 25.0
BACKGROUND_COUNT_PER_DOMAIN = 10000
STREAM_PRIORITY = {"social_media_verified": 0, "gbif": 1, "obis": 2}

# GEBCO_2026 subset 90E-160E, 40S-20N (data/gebco/SOURCE.md) - the only area the land mask sees.
STUDY_AREA = {"lat_min": -40.0, "lat_max": 20.0, "lon_min": 90.0, "lon_max": 160.0}
BBOX_EPS_DEG = 1e-9
DIST_EPS_KM = 1e-9
MAX_EXAMPLES = 5

CLEAN_FILES = tuple(f"rhincodon_{domain}_clean.csv" for domain in DOMAINS)
SEASONAL_FILES = {
    f"rhincodon_{domain}_{season.lower()}.csv": (domain.upper(), season)
    for domain in DOMAINS
    for season in SEASONS
}
BACKGROUND_FILES = {f"background_{domain}.csv": domain.upper() for domain in DOMAINS}
REQUIRED_FILES = (
    *CLEAN_FILES,
    *SEASONAL_FILES,
    *BACKGROUND_FILES,
    "quarantine.csv",
    "check.md",
)
COORDINATE_FILES = (*CLEAN_FILES, *SEASONAL_FILES, *BACKGROUND_FILES)
# The task's `*_id_*.csv` / `*_au_*.csv` glob covers the clean files too: a clean row outside
# the mask extent never reaches the land mask, so it must be caught here.
BBOX_FILES = (*CLEAN_FILES, *SEASONAL_FILES, *BACKGROUND_FILES)

ESCAPE_PATTERNS = (
    (re.compile(r"#\s*type:\s*ignore"), "type: ignore"),
    (re.compile(r"#\s*noqa(?!\s*:\s*[A-Z]+\d+)"), "bare noqa without a rule code"),
    (re.compile(r"TODO\s*:\s*fix\s+later"), "deferred-fix marker"),
    (re.compile(r"HACK\s*:"), "hack marker"),
)
SKIP_PARTS = {"__pycache__", ".venv", ".git", "raw"}


class Check:
    __slots__ = ("name", "ok", "detail", "examples")

    def __init__(self, name: str, ok: bool, detail: str, examples=()) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.examples = list(examples)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def parse_coord(text: str | None) -> float | None:
    """Return the coordinate, or None when empty, non-numeric, NaN, or infinite."""
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    try:
        value = float(stripped)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    a = (
        math.sin((phi2 - phi1) / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin((lam2 - lam1) / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def coordinate_problem(lat_text: str | None, lon_text: str | None) -> str | None:
    lat = parse_coord(lat_text)
    lon = parse_coord(lon_text)
    if lat is None or lon is None:
        return f"coordinate not finite numeric (lat={lat_text!r}, lon={lon_text!r})"
    if not -90.0 <= lat <= 90.0:
        return f"latitude {lat} outside [-90, 90]"
    if not -180.0 <= lon <= 180.0:
        return f"longitude {lon} outside [-180, 180]"
    if lat == 0.0 and lon == 0.0:
        return "null island (0, 0)"
    return None


def bbox_problem(lat: float, lon: float) -> str | None:
    if not STUDY_AREA["lat_min"] - BBOX_EPS_DEG <= lat <= STUDY_AREA["lat_max"] + BBOX_EPS_DEG:
        return f"latitude {lat} outside [{STUDY_AREA['lat_min']}, {STUDY_AREA['lat_max']}]"
    if not STUDY_AREA["lon_min"] - BBOX_EPS_DEG <= lon <= STUDY_AREA["lon_max"] + BBOX_EPS_DEG:
        return f"longitude {lon} outside [{STUDY_AREA['lon_min']}, {STUDY_AREA['lon_max']}]"
    return None


def status_line(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "check.md missing"
    text = path.read_text(encoding="utf-8", errors="replace")
    first = text.splitlines()[0].strip() if text.splitlines() else ""
    if first == "pass":
        return True, "stage status: pass"
    if first.startswith("fail:"):
        return True, f"stage status: {first}"
    return False, f"first line is not a pass/fail status: {first[:80]!r}"


# --- Stage 01 invariant 2: coordinates ------------------------------------------------


def check_coordinates(rows_by_file: dict[str, list[dict[str, str]] | None]) -> Check:
    total = 0
    violations = 0
    examples: list[str] = []
    missing: list[str] = []
    for name in COORDINATE_FILES:
        rows = rows_by_file.get(name)
        if rows is None:
            missing.append(name)
            continue
        for line_no, row in enumerate(rows, start=2):
            total += 1
            problem = coordinate_problem(row.get("latitude"), row.get("longitude"))
            if problem:
                violations += 1
                if len(examples) < MAX_EXAMPLES:
                    examples.append(f"{name}:{line_no} {problem}")
    ok = not violations and not missing
    detail = f"{total} rows checked, {violations} bad coordinates"
    if missing:
        detail += f", missing {', '.join(missing)}"
    return Check("coordinates finite / non-null / non-zero", ok, detail, examples)


# --- Stage 01 invariant 3: study area bounding box ------------------------------------


def check_study_area(rows_by_file: dict[str, list[dict[str, str]] | None]) -> Check:
    total = 0
    violations = 0
    examples: list[str] = []
    missing: list[str] = []
    for name in BBOX_FILES:
        rows = rows_by_file.get(name)
        if rows is None:
            missing.append(name)
            continue
        for line_no, row in enumerate(rows, start=2):
            lat = parse_coord(row.get("latitude"))
            lon = parse_coord(row.get("longitude"))
            if lat is None or lon is None:
                continue  # already reported by the coordinate invariant
            total += 1
            problem = bbox_problem(lat, lon)
            if problem:
                violations += 1
                if len(examples) < MAX_EXAMPLES:
                    examples.append(f"{name}:{line_no} {problem}")
    ok = not violations and not missing
    detail = (
        f"{total} rows inside "
        f"{STUDY_AREA['lat_min']}..{STUDY_AREA['lat_max']} lat / "
        f"{STUDY_AREA['lon_min']}..{STUDY_AREA['lon_max']} lon, {violations} outside"
    )
    if missing:
        detail += f", missing {', '.join(missing)}"
    return Check("study-area bounding box (90-160E, 40S-20N)", ok, detail, examples)


# --- Stage 01 invariant 4: seasonal partition conservation ----------------------------


def thinning_order_key(row: dict) -> tuple:
    uncertainty = row["coordinate_uncertainty_m"]
    return (
        uncertainty if uncertainty is not None else 1e9,
        STREAM_PRIORITY.get(row["source_stream"], 9),
        row["event_date_day"] or row["event_date"] or "9999-99-99",
        row["latitude"],
        row["longitude"],
        row["source_record_id"],
    )


def greedy_thin(rows: list[dict], min_km: float = THIN_DISTANCE_KM) -> list[dict]:
    """Same greedy rule as stages/01_occurrences/run_stage01.py::greedy_thin."""
    kept: list[dict] = []
    for candidate in sorted(rows, key=thinning_order_key):
        if all(
            haversine_km(
                candidate["latitude"],
                candidate["longitude"],
                previous["latitude"],
                previous["longitude"],
            )
            >= min_km
            for previous in kept
        ):
            kept.append(candidate)
    return kept


def parse_presence_rows(
    name: str, rows: list[dict[str, str]]
) -> tuple[list[dict], list[str]]:
    parsed: list[dict] = []
    problems: list[str] = []
    for line_no, row in enumerate(rows, start=2):
        lat = parse_coord(row.get("latitude"))
        lon = parse_coord(row.get("longitude"))
        if lat is None or lon is None:
            problems.append(f"{name}:{line_no} carries no usable coordinate")
            continue
        parsed.append(
            {
                "source_stream": (row.get("source_stream") or "").strip(),
                "source_record_id": (row.get("source_record_id") or "").strip(),
                "season": (row.get("season") or "").strip(),
                "event_date": (row.get("event_date") or "").strip(),
                "event_date_day": (row.get("event_date_day") or "").strip(),
                "coordinate_uncertainty_m": parse_coord(row.get("coordinate_uncertainty_m")),
                "latitude": lat,
                "longitude": lon,
            }
        )
    return parsed, problems


def check_conservation(rows_by_file: dict[str, list[dict[str, str]] | None]) -> Check:
    ok = True
    details: list[str] = []
    examples: list[str] = []
    for domain in DOMAINS:
        clean_name = f"rhincodon_{domain}_clean.csv"
        clean_rows = rows_by_file.get(clean_name)
        if clean_rows is None:
            ok = False
            details.append(f"{domain.upper()}: clean file missing")
            continue

        clean, problems = parse_presence_rows(clean_name, clean_rows)
        if problems:
            ok = False
            examples.extend(problems[:MAX_EXAMPLES])

        partition: dict[str, list[dict]] = {season: [] for season in SEASONS}
        unknown = 0
        for row in clean:
            if row["season"] in partition:
                partition[row["season"]].append(row)
            elif row["season"] == "UNKNOWN":
                unknown += 1
            else:
                ok = False
                if len(examples) < MAX_EXAMPLES:
                    examples.append(
                        f"{clean_name} unreadable season tag {row['season']!r} for "
                        f"{row['source_stream']}/{row['source_record_id']}"
                    )

        pre_thin = sum(len(partition[season]) for season in SEASONS)
        if pre_thin + unknown != len(clean):
            ok = False
            examples.append(
                f"{domain.upper()}: partition holds {pre_thin} + {unknown} UNKNOWN "
                f"rows but {len(clean)} clean rows parsed"
            )

        kept_total = 0
        file_total = 0
        for season in SEASONS:
            file_name = f"rhincodon_{domain}_{season.lower()}.csv"
            file_rows = rows_by_file.get(file_name)
            if file_rows is None:
                ok = False
                details.append(f"{file_name} missing")
                continue
            expected = greedy_thin(partition[season], THIN_DISTANCE_KM)
            kept_total += len(expected)

            actual, file_problems = parse_presence_rows(file_name, file_rows)
            if file_problems:
                ok = False
                examples.extend(file_problems[:MAX_EXAMPLES])
            file_total += len(actual)

            partition_ids = {
                (row["source_stream"], row["source_record_id"]) for row in partition[season]
            }
            expected_ids = [(row["source_stream"], row["source_record_id"]) for row in expected]
            actual_ids = [(row["source_stream"], row["source_record_id"]) for row in actual]

            if len(set(actual_ids)) != len(actual_ids):
                ok = False
                examples.append(f"{file_name} contains duplicate rows")
            foreign = [
                f"{stream}/{record}"
                for stream, record in actual_ids
                if (stream, record) not in partition_ids
            ]
            if foreign:
                ok = False
                if len(examples) < MAX_EXAMPLES:
                    examples.append(
                        f"{file_name} holds rows absent from the {season} partition: "
                        f"{', '.join(foreign[:3])}"
                    )
            if actual_ids != expected_ids:
                ok = False
                missing = [f"{s}/{r}" for s, r in expected_ids if (s, r) not in set(actual_ids)]
                extra = [f"{s}/{r}" for s, r in actual_ids if (s, r) not in set(expected_ids)]
                examples.append(
                    f"{file_name}: expected {len(expected_ids)} thinned rows, found "
                    f"{len(actual_ids)}"
                    + (f"; dropped {', '.join(missing[:3])}" if missing else "")
                    + (f"; unexpected {', '.join(extra[:3])}" if extra else "")
                    + ("" if missing or extra else "; row order differs (sort-key drift)")
                )
            for row in actual:
                if row["season"] != season:
                    ok = False
                    if len(examples) < MAX_EXAMPLES:
                        examples.append(
                            f"{file_name} holds season={row['season']!r} row "
                            f"{row['source_stream']}/{row['source_record_id']}"
                        )
                    break

        details.append(
            f"{domain.upper()}: clean={len(clean)} unknown={unknown} pre-thin={pre_thin} "
            f"thinned={file_total} (recomputed {kept_total}, removed {pre_thin - kept_total})"
        )
        if file_total != kept_total:
            ok = False

    return Check(
        "seasonal partition conservation (ID, AU)",
        ok,
        "; ".join(details),
        examples,
    )


# --- Stage 01 invariant 5: minimum haversine distance inside thinned slices -----------


def check_thinning(rows_by_file: dict[str, list[dict[str, str]] | None]) -> Check:
    ok = True
    worst = math.inf
    violating_files = 0
    violating_points = 0
    examples: list[str] = []
    missing: list[str] = []
    threshold = THIN_DISTANCE_KM - DIST_EPS_KM
    for name in SEASONAL_FILES:
        rows = rows_by_file.get(name)
        if rows is None:
            missing.append(name)
            continue
        points = []
        for line_no, row in enumerate(rows, start=2):
            lat = parse_coord(row.get("latitude"))
            lon = parse_coord(row.get("longitude"))
            if lat is None or lon is None:
                continue  # already reported by the coordinate invariant
            points.append((lat, lon))
        file_violations = 0
        for i in range(len(points)):
            lat1, lon1 = points[i]
            for j in range(i + 1, len(points)):
                distance = haversine_km(lat1, lon1, points[j][0], points[j][1])
                if distance < worst:
                    worst = distance
                if distance < threshold:
                    file_violations += 1
                    if len(examples) < MAX_EXAMPLES:
                        examples.append(
                            f"{name}: pair ({lat1}, {lon1}) <-> ({points[j][0]}, {points[j][1]}) "
                            f"is {distance:.3f} km"
                        )
                    break
        if file_violations:
            ok = False
            violating_files += 1
            violating_points += file_violations
    if missing:
        ok = False
    worst_text = f"{worst:.2f}" if math.isfinite(worst) else "n/a"
    detail = (
        f"{len(SEASONAL_FILES) - len(missing)} slices, minimum pair distance {worst_text} km "
        f"(threshold {THIN_DISTANCE_KM} km), "
        f"{violating_files} slices and {violating_points} points violate"
    )
    if missing:
        detail += f", missing {', '.join(missing)}"
    return Check(f"spatial thinning >= {THIN_DISTANCE_KM} km haversine", ok, detail, examples)


# --- Stage 01 invariant 6: background point integrity ---------------------------------


def check_background(rows_by_file: dict[str, list[dict[str, str]] | None]) -> Check:
    ok = True
    details: list[str] = []
    examples: list[str] = []
    for name, domain in BACKGROUND_FILES.items():
        rows = rows_by_file.get(name)
        if rows is None:
            ok = False
            details.append(f"{domain}: missing")
            continue
        land = 0
        wrong_domain = 0
        wrong_bandwidth = 0
        wrong_stream = 0
        max_elev = None
        for line_no, row in enumerate(rows, start=2):
            elevation = parse_coord(row.get("gebco_elevation_m"))
            if elevation is None or elevation >= 0.0:
                land += 1
                if len(examples) < MAX_EXAMPLES:
                    examples.append(f"{name}:{line_no} elevation {row.get('gebco_elevation_m')!r}")
            elif max_elev is None or elevation > max_elev:
                max_elev = elevation
            if (row.get("domain") or "").strip() != domain:
                wrong_domain += 1
            bandwidth = parse_coord(row.get("kde_bandwidth_km"))
            if bandwidth is None or abs(bandwidth - KDE_BANDWIDTH_KM) > 1e-9:
                wrong_bandwidth += 1
            if (row.get("source_stream") or "").strip() != "background_kde":
                wrong_stream += 1
        count_ok = len(rows) == BACKGROUND_COUNT_PER_DOMAIN
        if not count_ok:
            ok = False
            examples.append(
                f"{name} holds {len(rows)} points, expected {BACKGROUND_COUNT_PER_DOMAIN}"
            )
        if land or wrong_domain or wrong_bandwidth or wrong_stream:
            ok = False
            if wrong_domain:
                examples.append(f"{name} has {wrong_domain} rows with domain != {domain}")
            if wrong_bandwidth:
                examples.append(f"{name} has {wrong_bandwidth} rows with bandwidth != {KDE_BANDWIDTH_KM}")
            if wrong_stream:
                examples.append(f"{name} has {wrong_stream} rows with another source_stream")
        details.append(
            f"{domain}={len(rows)} pts, {land} on land, max elevation "
            f"{max_elev if max_elev is not None else 'n/a'} m"
        )
    detail = "; ".join(details) + f"; bandwidth {KDE_BANDWIDTH_KM} km"
    return Check(
        f"background integrity ({BACKGROUND_COUNT_PER_DOMAIN} ocean points per domain)",
        ok,
        detail,
        examples,
    )


# --- Invariant 7: escape-hatch hygiene ------------------------------------------------


def python_sources(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            found.append(root)
        elif root.is_dir():
            found.extend(
                path
                for path in sorted(root.rglob("*.py"))
                if not SKIP_PARTS.intersection(path.parts)
            )
    return sorted(found, key=lambda path: path.as_posix())


def check_hygiene(roots: list[Path]) -> Check:
    files = python_sources(roots)
    violations = 0
    examples: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern, label in ESCAPE_PATTERNS:
                if pattern.search(line):
                    violations += 1
                    if len(examples) < MAX_EXAMPLES:
                        examples.append(f"{path}:{line_no} {label}: {line.strip()[:100]}")
                    break
    detail = f"{len(files)} Python files scanned, {violations} escape hatches"
    if not files:
        detail = "0 Python files scanned (no roots matched)"
    return Check("escape-hatch hygiene", not violations, detail, examples)


# --- driver ---------------------------------------------------------------------------


def verify_stage01(output_dir: Path, scan_roots: list[Path]) -> list[Check]:
    rows_by_file: dict[str, list[dict[str, str]] | None] = {}
    for name in COORDINATE_FILES:
        path = output_dir / name
        rows_by_file[name] = read_rows(path) if path.is_file() else None

    missing = [name for name in REQUIRED_FILES if not (output_dir / name).is_file()]
    files_check = Check(
        "required artifacts",
        not missing,
        f"{len(REQUIRED_FILES) - len(missing)}/{len(REQUIRED_FILES)} present",
        [f"missing {name}" for name in missing],
    )

    status_ok, status_detail = status_line(output_dir / "check.md")
    checks = [
        files_check,
        Check("check.md status line", status_ok, status_detail),
        check_coordinates(rows_by_file),
        check_study_area(rows_by_file),
        check_conservation(rows_by_file),
        check_thinning(rows_by_file),
        check_background(rows_by_file),
        check_hygiene(scan_roots),
    ]
    return checks


def render(checks: list[Check], output_dir: Path, scan_roots: list[Path]) -> None:
    width = max(len(check.name) for check in checks)
    roots = ", ".join(root.name for root in scan_roots)
    print("whale-scraper stage verification")
    print(f"  output: {output_dir}")
    print(f"  hygiene roots: {roots}")
    print()
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}  {check.name:<{width}}  {check.detail}")
        for example in check.examples:
            print(f"      {example}")
    failed = [check for check in checks if not check.ok]
    print()
    print(f"summary: {len(checks) - len(failed)} PASS, {len(failed)} FAIL")
    if failed:
        print("failed invariants: " + "; ".join(check.name for check in failed))


def parse_args(argv: list[str] | None):
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify whale-scraper stage outputs for silent data corruption."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="repository root (default: the folder that holds _tools/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="stage 01 output directory (default: <root>/stages/01_occurrences/output)",
    )
    parser.add_argument(
        "--scan-root",
        type=Path,
        action="append",
        default=None,
        help="folder or file to scan for escape hatches (repeatable)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    output_dir = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else root / "stages" / "01_occurrences" / "output"
    )
    scan_roots = (
        [path.resolve() for path in args.scan_root]
        if args.scan_root
        else [root / "stages", root / "_shared", root / "_tools"]
    )
    checks = verify_stage01(output_dir, scan_roots)
    render(checks, output_dir, scan_roots)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
