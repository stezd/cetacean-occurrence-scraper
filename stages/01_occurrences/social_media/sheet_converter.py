#!/usr/bin/env python3
"""Stream 3 converter and validator between raw JSONL and Pembimbing 2 verification CSVs."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    _stage_dir = str(Path(__file__).resolve().parents[1])
    if _stage_dir not in sys.path:
        sys.path.insert(0, _stage_dir)
    __package__ = "social_media"

from .constants import (
    DEFAULT_DOMAIN,
    DEFAULT_RAW_JSONL,
    DEFAULT_UNVERIFIED_CSV,
    DEFAULT_VERIFIED_CSV,
    SHEET_COLUMNS,
    TEMPLATE_CSV,
    VALID_DOMAINS,
    VALID_PERILAKU_KONTEKS,
    VALID_STATUS_VERIFIKASI,
    determine_season,
    extract_date_parts,
)

REQUIRED_VERIFIED_HEADERS = {"sighting_id", "status_verifikasi"}


@dataclass
class RejectedRow:
    row_number: int
    sighting_id: str
    reasons: list[str]
    raw_row: dict[str, str]


@dataclass
class ValidationReport:
    total_rows: int = 0
    accepted_rows: list[dict[str, str]] = field(default_factory=list)
    rejected_rows: list[RejectedRow] = field(default_factory=list)
    status_counts: dict[str, int] = field(default_factory=dict)
    rejection_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def format_summary(self) -> str:
        lines = [
            f"Validation summary: total={self.total_rows}, accepted={len(self.accepted_rows)}, rejected={len(self.rejected_rows)}",
            "  Status counts (accepted): "
            + ", ".join(f"{k}={self.status_counts.get(k, 0)}" for k in VALID_STATUS_VERIFIKASI),
        ]
        if self.rejection_counts:
            lines.append(
                "  Rejection reasons: "
                + ", ".join(f"{k}={v}" for k, v in sorted(self.rejection_counts.items()))
            )
        for w in self.warnings:
            lines.append(f"  [WARN] {w}")
        return "\n".join(lines)


def _clean_cell_text(val: Any) -> str:
    if val is None:
        return ""
    return " ".join(str(val).replace("\r", " ").replace("\n", " ").split())


def _parse_finite_float(val: Any) -> float | None:
    text = str(val or "").strip()
    if not text:
        return None
    num = float(text)
    if math.isnan(num) or math.isinf(num):
        raise ValueError("non-finite float")
    return num


def _parse_int_strict(val: Any) -> int | None:
    text = str(val or "").strip()
    if not text:
        return None
    f = float(text)
    if math.isnan(f) or math.isinf(f) or not f.is_integer():
        raise ValueError("not an integer")
    return int(f)


def generate_template_csv(out_path: Path = TEMPLATE_CSV) -> Path:
    """Write the empty UTF-8-BOM verification sheet template CSV for Excel."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
    return out_path


def raw_record_to_sheet_row(rec: dict[str, Any]) -> dict[str, str]:
    """Map one raw JSONL record to an unverified verification-sheet CSV row."""
    sighting_date = str(rec.get("sighting_date") or "").strip()
    post_date = str(rec.get("post_date") or "").strip()
    ref_date = sighting_date or post_date

    year = rec.get("year")
    month = rec.get("month")
    parsed_y, parsed_m, _ = extract_date_parts(ref_date)
    if year in (None, ""):
        year = parsed_y
    if month in (None, ""):
        month = parsed_m

    try:
        month_int = int(month) if month not in (None, "") else None
    except (TypeError, ValueError):
        month_int = None

    season = str(rec.get("season") or "").strip() or determine_season(month_int)

    def _fmt_num(v: Any) -> str:
        return "" if v is None or v == "" else str(v)

    return {
        "sighting_id": str(rec.get("sighting_id") or "").strip(),
        "platform": str(rec.get("platform") or "").strip(),
        "post_url": str(rec.get("post_url") or "").strip(),
        "local_media_path": str(rec.get("local_media_path") or "").strip(),
        "caption_raw": _clean_cell_text(rec.get("caption_raw") or ""),
        "post_date": post_date,
        "sighting_date": sighting_date,
        "year": _fmt_num(year),
        "month": _fmt_num(month_int),
        "season": season,
        "domain": str(rec.get("domain") or DEFAULT_DOMAIN).strip().upper(),
        "locality_text": _clean_cell_text(rec.get("locality_text") or ""),
        "lat_est": _fmt_num(rec.get("lat_est")),
        "lon_est": _fmt_num(rec.get("lon_est")),
        "coord_uncertainty_km": _fmt_num(rec.get("coord_uncertainty_km")),
        "status_verifikasi": "",
        "lat_koreksi": "",
        "lon_koreksi": "",
        "jumlah_individu": "",
        "perilaku_konteks": "",
        "catatan_dosen": "",
    }


def jsonl_to_unverified_sheet(
    raw_paths: list[Path],
    out_csv: Path = DEFAULT_UNVERIFIED_CSV,
) -> dict[str, int]:
    """Convert append-only raw JSONL capture(s) into an unverified UTF-8-BOM CSV sheet."""
    total_lines = 0
    skipped_duplicates = 0
    seen_ids: set[str] = set()
    rows: list[dict[str, str]] = []

    for raw_path in raw_paths:
        if not raw_path.exists():
            raise FileNotFoundError(f"Raw JSONL file not found: {raw_path}")
        with raw_path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                total_lines += 1
                rec = json.loads(stripped)
                row = raw_record_to_sheet_row(rec)
                sid = row["sighting_id"]
                if sid and sid in seen_ids:
                    skipped_duplicates += 1
                    continue
                if sid:
                    seen_ids.add(sid)
                rows.append(row)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return {
        "raw_lines": total_lines,
        "written_rows": len(rows),
        "skipped_duplicates": skipped_duplicates,
    }


def _validate_coord_pair(
    raw_row: dict[str, str],
    lat_col: str,
    lon_col: str,
    reasons: list[str],
) -> tuple[float | None, float | None]:
    lat_str = (raw_row.get(lat_col) or "").strip()
    lon_str = (raw_row.get(lon_col) or "").strip()
    if bool(lat_str) != bool(lon_str):
        reasons.append(f"incomplete_coord_pair:{lat_col}/{lon_col}")
        return None, None
    if not lat_str and not lon_str:
        return None, None

    try:
        lat = _parse_finite_float(lat_str)
        lon = _parse_finite_float(lon_str)
    except ValueError:
        reasons.append(f"invalid_coord_format:{lat_col}/{lon_col}")
        return None, None

    assert lat is not None and lon is not None
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        reasons.append(f"coord_out_of_range:{lat_col}/{lon_col}")
        return None, None
    if lat == 0.0 and lon == 0.0:
        reasons.append(f"coord_zero_zero:{lat_col}/{lon_col}")
        return None, None
    return lat, lon


def validate_verified_sheet(
    in_csv: Path,
    out_csv: Path | None = DEFAULT_VERIFIED_CSV,
    rejected_csv: Path | None = None,
    strict: bool = False,
) -> ValidationReport:
    """Validate Pembimbing 2's verification CSV and emit `social_media_verified.csv`."""
    if not in_csv.exists():
        raise FileNotFoundError(f"Verification sheet not found: {in_csv}")

    report = ValidationReport()
    seen_ids: set[str] = set()
    status_counter: Counter[str] = Counter()
    reason_counter: Counter[str] = Counter()

    with in_csv.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"Empty CSV or missing header row: {in_csv}")
        field_set = {name.strip() for name in reader.fieldnames if name}
        missing_headers = sorted(REQUIRED_VERIFIED_HEADERS - field_set)
        if missing_headers:
            raise ValueError(f"Missing required column(s) in {in_csv}: {', '.join(missing_headers)}")

        for row_num, raw in enumerate(reader, start=2):
            report.total_rows += 1
            reasons: list[str] = []

            sid = (raw.get("sighting_id") or "").strip()
            if not sid:
                reasons.append("missing_sighting_id")
            elif sid in seen_ids:
                reasons.append("duplicate_sighting_id")

            status = (raw.get("status_verifikasi") or "").strip().lower()
            if not status:
                reasons.append("missing_status_verifikasi")
            elif status not in VALID_STATUS_VERIFIKASI:
                reasons.append("invalid_status_verifikasi")

            _validate_coord_pair(raw, "lat_koreksi", "lon_koreksi", reasons)
            _validate_coord_pair(raw, "lat_est", "lon_est", reasons)

            unc_str = (raw.get("coord_uncertainty_km") or "").strip()
            if unc_str:
                try:
                    unc = _parse_finite_float(unc_str)
                    if unc is not None and unc < 0:
                        reasons.append("negative_coord_uncertainty_km")
                except ValueError:
                    reasons.append("invalid_coord_uncertainty_km")

            cnt_str = (raw.get("jumlah_individu") or "").strip()
            if cnt_str:
                try:
                    cnt = _parse_int_strict(cnt_str)
                    if cnt is not None and cnt < 1:
                        reasons.append("invalid_jumlah_individu")
                except ValueError:
                    reasons.append("invalid_jumlah_individu")

            domain = (raw.get("domain") or DEFAULT_DOMAIN).strip().upper()
            if domain not in VALID_DOMAINS:
                reasons.append("invalid_domain")

            year_str = (raw.get("year") or "").strip()
            parsed_year: int | None = None
            if year_str:
                try:
                    parsed_year = _parse_int_strict(year_str)
                    if parsed_year is not None and not (1900 <= parsed_year <= 2100):
                        reasons.append("invalid_year")
                except ValueError:
                    reasons.append("invalid_year")

            month_str = (raw.get("month") or "").strip()
            parsed_month: int | None = None
            if month_str:
                try:
                    parsed_month = _parse_int_strict(month_str)
                    if parsed_month is not None and not (1 <= parsed_month <= 12):
                        reasons.append("invalid_month")
                except ValueError:
                    reasons.append("invalid_month")

            if reasons:
                if sid:
                    seen_ids.add(sid)
                for r in reasons:
                    reason_counter[r] += 1
                report.rejected_rows.append(
                    RejectedRow(row_number=row_num, sighting_id=sid, reasons=reasons, raw_row=dict(raw))
                )
                continue

            seen_ids.add(sid)
            status_counter[status] += 1

            perilaku = (raw.get("perilaku_konteks") or "").strip().lower()
            if perilaku and perilaku not in VALID_PERILAKU_KONTEKS:
                report.warnings.append(
                    f"Row {row_num} ({sid}): non-standard perilaku_konteks={perilaku!r}"
                )

            sighting_date = (raw.get("sighting_date") or "").strip()
            post_date = (raw.get("post_date") or "").strip()
            dy, dm, _ = extract_date_parts(sighting_date or post_date)
            final_year = parsed_year if parsed_year is not None else dy
            final_month = parsed_month if parsed_month is not None else dm
            season = (raw.get("season") or "").strip().upper() or determine_season(final_month)

            normalized = {col: (raw.get(col) or "").strip() for col in SHEET_COLUMNS}
            normalized["sighting_id"] = sid
            normalized["status_verifikasi"] = status
            normalized["domain"] = domain
            normalized["year"] = str(final_year) if final_year is not None else ""
            normalized["month"] = str(final_month) if final_month is not None else ""
            normalized["season"] = season
            normalized["perilaku_konteks"] = perilaku
            report.accepted_rows.append(normalized)

    report.status_counts = dict(status_counter)
    report.rejection_counts = dict(reason_counter)

    if rejected_csv is not None and report.rejected_rows:
        rejected_csv.parent.mkdir(parents=True, exist_ok=True)
        rej_cols = ["row_number", "rejection_reasons"] + SHEET_COLUMNS
        with rejected_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rej_cols)
            writer.writeheader()
            for rr in report.rejected_rows:
                row_out = {c: rr.raw_row.get(c, "") for c in SHEET_COLUMNS}
                row_out["row_number"] = str(rr.row_number)
                row_out["rejection_reasons"] = ";".join(rr.reasons)
                writer.writerow(row_out)

    if out_csv is not None and not (strict and report.rejected_rows):
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=SHEET_COLUMNS)
            writer.writeheader()
            writer.writerows(report.accepted_rows)

    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert raw social-media JSONL to verification sheet and validate verified CSVs."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_tpl = sub.add_parser("init-template", help="Write the UTF-8-BOM verification sheet template CSV.")
    p_tpl.add_argument("--out", type=Path, default=TEMPLATE_CSV, help=f"Template output path (default: {TEMPLATE_CSV}).")

    p_to_sheet = sub.add_parser("jsonl-to-sheet", help="Convert scraped raw JSONL to an unverified CSV sheet.")
    p_to_sheet.add_argument(
        "--raw",
        nargs="+",
        type=Path,
        default=[DEFAULT_RAW_JSONL],
        help=f"Input raw JSONL file(s) (default: {DEFAULT_RAW_JSONL}).",
    )
    p_to_sheet.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_UNVERIFIED_CSV,
        help=f"Unverified CSV output path (default: {DEFAULT_UNVERIFIED_CSV}).",
    )

    p_val = sub.add_parser("validate", help="Validate Pembimbing 2's CSV and write social_media_verified.csv.")
    p_val.add_argument("--in-csv", type=Path, required=True, help="Reviewed CSV filled in by Pembimbing 2.")
    p_val.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_VERIFIED_CSV,
        help=f"Validated output CSV path (default: {DEFAULT_VERIFIED_CSV}).",
    )
    p_val.add_argument(
        "--rejected-out",
        type=Path,
        default=None,
        help="Optional CSV path to save rejected rows with rejection_reasons.",
    )
    p_val.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 and do not write --out if any row is rejected.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "init-template":
        path = generate_template_csv(args.out)
        print(f"[+] Wrote UTF-8-BOM template CSV -> {path}")
        return 0

    if args.command == "jsonl-to-sheet":
        counts = jsonl_to_unverified_sheet(args.raw, out_csv=args.out)
        print(
            f"[+] Unverified sheet generated: raw_lines={counts['raw_lines']}, "
            f"written={counts['written_rows']}, skipped_duplicates={counts['skipped_duplicates']} -> {args.out}"
        )
        return 0

    if args.command == "validate":
        report = validate_verified_sheet(
            in_csv=args.in_csv,
            out_csv=args.out,
            rejected_csv=args.rejected_out,
            strict=args.strict,
        )
        print(report.format_summary())
        for rr in report.rejected_rows:
            print(f"  [REJECT] row={rr.row_number} sighting_id={rr.sighting_id or '<empty>'}: {', '.join(rr.reasons)}")
        if args.strict and report.rejected_rows:
            print("[!] Strict mode enabled: output file was not written due to rejected rows.")
            return 1
        print(f"[+] Validated verified sheet written -> {args.out}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
