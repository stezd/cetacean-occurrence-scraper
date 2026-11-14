#!/usr/bin/env python3
"""Stream 2 CLI: collect public whale shark sightings into append-only raw JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    _stage_dir = str(Path(__file__).resolve().parents[1])
    if _stage_dir not in sys.path:
        sys.path.insert(0, _stage_dir)
    __package__ = "social_media"

from .constants import (
    DEFAULT_MEDIA_DIR,
    DEFAULT_RAW_JSONL,
    DEFAULT_RSS_FEEDS,
    STUBBED_PLATFORMS,
    build_search_queries,
)
from .http_client import ThrottledHttpClient
from .platform_stubs import (
    UnsupportedLiveScrapeError,
    format_stub_notice,
    load_export_file,
    normalize_exported_record,
    scrape_stub,
)
from .rss_news import collect_rss_sightings
from .youtube import MissingApiKeyError, collect_youtube_sightings


def read_existing_sighting_ids(raw_jsonl: Path) -> set[str]:
    """Read sighting_id values already stored in an append-only JSONL file."""
    ids: set[str] = set()
    if not raw_jsonl.exists():
        return ids
    with raw_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            sid = str(obj.get("sighting_id") or "").strip()
            if sid:
                ids.add(sid)
    return ids


def append_raw_records(raw_jsonl: Path, records: list[dict[str, Any]]) -> tuple[int, int]:
    """Append new sighting records to JSONL without modifying existing lines.

    Returns (appended_count, skipped_existing_count).
    """
    raw_jsonl.parent.mkdir(parents=True, exist_ok=True)
    seen = read_existing_sighting_ids(raw_jsonl)
    appended = 0
    skipped = 0
    with raw_jsonl.open("a", encoding="utf-8", newline="\n") as f:
        for rec in records:
            sid = str(rec.get("sighting_id") or "").strip()
            if sid and sid in seen:
                skipped += 1
                continue
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if sid:
                seen.add(sid)
            appended += 1
    return appended, skipped


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect public whale shark (Rhincodon typus) sightings into append-only raw JSONL."
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        default=["rss"],
        help="Sources to query: rss, youtube (requires YOUTUBE_API_KEY), or stubbed platforms (instagram, tiktok, x).",
    )
    parser.add_argument(
        "--rss-url",
        action="append",
        default=[],
        help="Additional public RSS/Atom or WP-JSON feed URL (repeatable).",
    )
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="Custom YouTube search query (repeatable; defaults to whale shark + hotspot combinations).",
    )
    parser.add_argument(
        "--max-queries",
        type=int,
        default=3,
        help="Maximum number of default YouTube queries to run (default: 3).",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Max YouTube search results per query (1..50, default: 10).",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=25,
        help="Hard cap on total HTTP requests in this run (default: 25).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Minimum throttle delay in seconds between requests to the same host (default: 1.5).",
    )
    parser.add_argument(
        "--raw-out",
        type=Path,
        default=DEFAULT_RAW_JSONL,
        help=f"Append-only JSONL output path (default: {DEFAULT_RAW_JSONL}).",
    )
    parser.add_argument(
        "--media-dir",
        type=Path,
        default=DEFAULT_MEDIA_DIR,
        help=f"Local directory for downloaded media (default: {DEFAULT_MEDIA_DIR}).",
    )
    parser.add_argument(
        "--no-media",
        action="store_true",
        help="Do not download thumbnail/image media files.",
    )
    parser.add_argument(
        "--show-stub-spec",
        choices=STUBBED_PLATFORMS,
        default=None,
        help="Print the expected manual/official-API export schema for instagram, tiktok, or x and exit.",
    )
    parser.add_argument(
        "--import-export",
        nargs=2,
        metavar=("PLATFORM", "FILE"),
        default=None,
        help="Ingest a conforming manual or official-API export file for instagram, tiktok, or x.",
    )
    parser.add_argument(
        "--copy-export-media",
        action="store_true",
        help="When used with --import-export, copy referenced local_media_file into --media-dir.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.show_stub_spec:
        print(format_stub_notice(args.show_stub_spec))
        return 0

    if args.import_export:
        platform, file_str = args.import_export
        export_path = Path(file_str)
        raw_items = load_export_file(export_path)
        normalized = [
            normalize_exported_record(
                platform,
                item,
                media_dir=args.media_dir,
                export_base_dir=export_path.parent,
                copy_local_media=args.copy_export_media,
            )
            for item in raw_items
        ]
        appended, skipped = append_raw_records(args.raw_out, normalized)
        print(
            f"[+] Imported {platform} export ({len(normalized)} parsed): "
            f"{appended} appended, {skipped} already present -> {args.raw_out}"
        )
        return 0

    client = ThrottledHttpClient(min_delay_sec=args.delay, max_requests=args.max_requests)
    all_records: list[dict[str, Any]] = []
    warnings: list[str] = []

    sources = [s.strip().lower() for s in args.sources if s.strip()]
    for src in sources:
        if src in STUBBED_PLATFORMS:
            try:
                scrape_stub(src)
            except UnsupportedLiveScrapeError as exc:
                warnings.append(str(exc))
            continue

        if src == "rss":
            feeds: list[tuple[str, str]] = [("news_rss", u) for u in args.rss_url]
            if not feeds:
                feeds = list(DEFAULT_RSS_FEEDS)
            recs, rss_warnings = collect_rss_sightings(
                client,
                feeds=feeds,
                download_media=not args.no_media,
                media_dir=args.media_dir,
            )
            all_records.extend(recs)
            warnings.extend(rss_warnings)
            print(f"[+] RSS/news: collected {len(recs)} matching whale shark items")
            continue

        if src == "youtube":
            queries = list(args.query) if args.query else build_search_queries(include_hotspots=True)[: max(1, args.max_queries)]
            try:
                recs = collect_youtube_sightings(
                    client,
                    queries=queries,
                    max_results_per_query=args.max_results,
                    download_media=not args.no_media,
                    media_dir=args.media_dir,
                )
                all_records.extend(recs)
                print(f"[+] YouTube API v3: collected {len(recs)} matching whale shark items")
            except MissingApiKeyError as exc:
                warnings.append(str(exc))
            continue

        warnings.append(f"Unknown source {src!r}; expected rss, youtube, or {STUBBED_PLATFORMS}")

    appended, skipped = append_raw_records(args.raw_out, all_records)
    print(
        f"[+] Raw capture summary: {len(all_records)} collected, {appended} appended, "
        f"{skipped} skipped (duplicate ID), HTTP requests used={client.requests_made}/{args.max_requests}"
    )
    print(f"    Output: {args.raw_out}")
    for w in warnings:
        print(f"[!] {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
