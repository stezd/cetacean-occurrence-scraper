"""Documented stubs and manual/official-API export importers for Instagram, TikTok, and X.

Live unauthenticated scraping of Instagram, TikTok, and X is intentionally NOT
implemented. Bypassing login walls, using shared/stolen session cookies, or
circumventing anti-bot protections violates platform Terms of Service and repo rules.

Instead, researchers may obtain records via:
1. Official platform APIs (Meta Graph API, TikTok Research API, X API v2), or
2. Manual export spreadsheets/JSON collected during literature/social-media review.

Use `import_platform_export()` (or `scraper.py --import-export <platform> <file>`)
to ingest conforming JSON / JSONL exports into `social_media_raw.jsonl`.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_DOMAIN,
    STUBBED_PLATFORMS,
    WIB,
    extract_date_parts,
    make_sighting_id,
    match_hotspot,
)
from .http_client import _to_repo_relative_posix


class UnsupportedLiveScrapeError(NotImplementedError):
    """Raised when live scraping is requested for login-walled / stubbed platforms."""


PLATFORM_EXPORT_SPECS: dict[str, dict[str, Any]] = {
    "instagram": {
        "official_api": "Meta Graph API (Instagram Business Discovery / Hashtag Search) or manual researcher log",
        "required_fields": ["post_url (or permalink)", "caption (or caption_raw)", "timestamp (or post_date)"],
        "optional_fields": ["id", "sighting_date", "locality_text", "lat_est", "lon_est", "coord_uncertainty_km", "media_url", "local_media_file"],
        "example_record": {
            "id": "17895695668004550",
            "permalink": "https://www.instagram.com/p/EXAMPLE_SHORTCODE/",
            "caption": "Penampakan hiu paus di sekitar bagan Labuan Jambu, Teluk Saleh pagi ini.",
            "timestamp": "2025-08-14T07:30:00+0700",
            "sighting_date": "2025-08-14",
            "locality_text": "Labuan Jambu, Teluk Saleh",
            "local_media_file": "ig_17895695668004550.jpg",
        },
    },
    "tiktok": {
        "official_api": "TikTok Research API (/v2/research/video/query/) or manual researcher log",
        "required_fields": ["share_url (or post_url)", "video_description (or caption)", "create_time (ISO date or Unix seconds)"],
        "optional_fields": ["id", "sighting_date", "locality_text", "lat_est", "lon_est", "coord_uncertainty_km", "region_code", "local_media_file"],
        "example_record": {
            "id": "7381920451234567890",
            "share_url": "https://www.tiktok.com/@example_user/video/7381920451234567890",
            "video_description": "Hiu paus muncul di Pantai Botubarani Gorontalo #hiupaus #gorontalo",
            "create_time": "2025-06-21T09:15:00+07:00",
            "region_code": "ID",
            "local_media_file": "tiktok_7381920451234567890.jpg",
        },
    },
    "x": {
        "official_api": "X API v2 (/2/tweets/search/recent or full-archive search) or manual researcher log",
        "required_fields": ["url (or post_url, or id)", "text (or caption)", "created_at (or post_date)"],
        "optional_fields": ["id", "sighting_date", "locality_text", "lat_est", "lon_est", "coord_uncertainty_km", "place_full_name", "local_media_file"],
        "example_record": {
            "id": "1890123456789012345",
            "url": "https://x.com/example_user/status/1890123456789012345",
            "text": "Tiga ekor hiu paus terlihat di perairan Talisayan, Berau hari ini.",
            "created_at": "2025-10-03T11:20:00Z",
            "place_full_name": "Talisayan, Berau, Kalimantan Timur",
            "local_media_file": "x_1890123456789012345.jpg",
        },
    },
}


def format_stub_notice(platform: str) -> str:
    key = platform.lower().strip()
    if key not in PLATFORM_EXPORT_SPECS:
        raise ValueError(f"Unknown stubbed platform {platform!r}. Expected one of {STUBBED_PLATFORMS}.")
    spec = PLATFORM_EXPORT_SPECS[key]
    return (
        f"[{key.upper()} STUB] Live scraping is disabled to respect ToS, login walls, and anti-bot controls.\n"
        f"  Official / manual source: {spec['official_api']}\n"
        f"  Required export fields : {', '.join(spec['required_fields'])}\n"
        f"  Optional export fields : {', '.join(spec['optional_fields'])}\n"
        f"  Example JSON record    : {json.dumps(spec['example_record'], ensure_ascii=False)}"
    )


def scrape_stub(platform: str, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
    """Explicitly refuse live scraping for login-walled platforms."""
    raise UnsupportedLiveScrapeError(format_stub_notice(platform))


def _coerce_post_date(raw_val: Any) -> str:
    if raw_val is None or raw_val == "":
        return ""
    if isinstance(raw_val, (int, float)):
        dt = datetime.fromtimestamp(float(raw_val), tz=WIB)
        return dt.strftime("%Y-%m-%d")
    text = str(raw_val).strip()
    if text.isdigit() and len(text) >= 9:
        dt = datetime.fromtimestamp(float(text), tz=WIB)
        return dt.strftime("%Y-%m-%d")
    _, _, iso = extract_date_parts(text)
    return iso


def normalize_exported_record(
    platform: str,
    item: dict[str, Any],
    media_dir: Path | None = None,
    export_base_dir: Path | None = None,
    copy_local_media: bool = False,
) -> dict[str, Any]:
    """Normalize a manual or official-API export item from Instagram, TikTok, or X."""
    plat = platform.lower().strip()
    if plat not in STUBBED_PLATFORMS:
        raise ValueError(f"Unsupported export platform {platform!r}; expected one of {STUBBED_PLATFORMS}")

    ext_id = str(item.get("id") or "").strip() or None
    post_url = str(
        item.get("post_url")
        or item.get("permalink")
        or item.get("share_url")
        or item.get("video_url")
        or item.get("url")
        or ""
    ).strip()
    if not post_url and plat == "x" and ext_id:
        post_url = f"https://x.com/i/web/status/{ext_id}"
    if not post_url:
        raise ValueError(f"{plat} export record missing post_url/permalink/share_url/url")

    caption = str(
        item.get("caption_raw")
        or item.get("caption")
        or item.get("video_description")
        or item.get("text")
        or ""
    ).strip()

    post_date = _coerce_post_date(
        item.get("post_date") or item.get("timestamp") or item.get("create_time") or item.get("created_at")
    )
    sighting_date = _coerce_post_date(item.get("sighting_date"))
    ref_date = sighting_date or post_date
    year, month, _ = extract_date_parts(ref_date)

    locality = str(item.get("locality_text") or item.get("place_full_name") or "").strip()
    hs = match_hotspot(f"{locality} {caption}")
    if not locality and hs:
        locality = hs.name

    lat_est = item.get("lat_est")
    lon_est = item.get("lon_est")
    unc_km = item.get("coord_uncertainty_km")
    if (lat_est is None or lat_est == "") and (lon_est is None or lon_est == "") and hs:
        lat_est = hs.lat
        lon_est = hs.lon
        unc_km = unc_km if unc_km not in (None, "") else hs.uncertainty_km

    sighting_id = str(item.get("sighting_id") or "").strip() or make_sighting_id(plat, post_url, ext_id)

    local_media_path = str(item.get("local_media_path") or "").strip()
    src_media = str(item.get("local_media_file") or "").strip()
    if copy_local_media and src_media and media_dir is not None:
        src_path = Path(src_media)
        if not src_path.is_absolute() and export_base_dir is not None:
            src_path = export_base_dir / src_path
        if src_path.exists() and src_path.is_file():
            media_dir.mkdir(parents=True, exist_ok=True)
            dest = media_dir / f"{sighting_id}{src_path.suffix.lower() or '.jpg'}"
            if src_path.resolve() != dest.resolve():
                shutil.copy2(src_path, dest)
            local_media_path = _to_repo_relative_posix(dest)

    return {
        "sighting_id": sighting_id,
        "platform": plat,
        "post_url": post_url,
        "local_media_path": local_media_path,
        "caption_raw": caption,
        "post_date": post_date,
        "sighting_date": sighting_date,
        "year": year,
        "month": month,
        "domain": str(item.get("domain") or DEFAULT_DOMAIN).upper(),
        "locality_text": locality,
        "lat_est": lat_est,
        "lon_est": lon_est,
        "coord_uncertainty_km": unc_km,
        "media_url": str(item.get("media_url") or "").strip(),
        "query_term": "manual_or_api_export",
        "scraped_at": datetime.now(WIB).isoformat(timespec="seconds"),
        "raw_payload": item,
    }


def load_export_file(path: Path) -> list[dict[str, Any]]:
    """Load a JSON list, {'data': [...]} envelope, or JSONL file."""
    text = path.read_text(encoding="utf-8-sig").strip()
    if not text:
        return []
    if text[0] in "[{":
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                return [x for x in parsed if isinstance(x, dict)]
            if isinstance(parsed, dict):
                if isinstance(parsed.get("data"), list):
                    return [x for x in parsed["data"] if isinstance(x, dict)]
                return [parsed]
        except json.JSONDecodeError:
            pass
    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            obj = json.loads(line)
            if isinstance(obj, dict):
                records.append(obj)
    return records
