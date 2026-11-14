"""Shared constants, hotspot gazetteer, and CSV schema for Stage 01 social media streams."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import timedelta, timezone
from pathlib import Path

SOCIAL_MEDIA_DIR = Path(__file__).resolve().parent
STAGE_DIR = SOCIAL_MEDIA_DIR.parent
REPO_ROOT = STAGE_DIR.parents[1]

DEFAULT_RAW_JSONL = STAGE_DIR / "raw" / "social_media_raw.jsonl"
DEFAULT_UNVERIFIED_CSV = STAGE_DIR / "input" / "social_media_unverified.csv"
DEFAULT_VERIFIED_CSV = STAGE_DIR / "input" / "social_media_verified.csv"
DEFAULT_MEDIA_DIR = STAGE_DIR / "input" / "social_media" / "media"
TEMPLATE_CSV = SOCIAL_MEDIA_DIR / "verification_sheet_template.csv"

TAXON_KEY = 2417522
TARGET_SPECIES = "Rhincodon typus"
DEFAULT_DOMAIN = "ID"
VALID_DOMAINS = ("ID", "AU")
YEAR_MIN = 2010
YEAR_MAX = 2026

WIB = timezone(timedelta(hours=7))

SEARCH_TERMS: tuple[str, ...] = (
    "hiu paus",
    "whale shark",
    "Rhincodon typus",
)


@dataclass(frozen=True)
class Hotspot:
    name: str
    aliases: tuple[str, ...]
    lat: float
    lon: float
    uncertainty_km: float


HOTSPOTS: tuple[Hotspot, ...] = (
    Hotspot(
        name="Teluk Saleh",
        aliases=("teluk saleh", "saleh bay", "labuan jambu", "sumbawa"),
        lat=-8.6333,
        lon=117.9500,
        uncertainty_km=8.0,
    ),
    Hotspot(
        name="Botubarani, Gorontalo",
        aliases=("botubarani", "gorontalo", "kabila bone", "teluk tomini"),
        lat=0.4917,
        lon=123.1067,
        uncertainty_km=5.0,
    ),
    Hotspot(
        name="Derawan / Talisayan",
        aliases=("talisayan", "derawan", "berau", "maratua", "kakaban"),
        lat=1.6500,
        lon=118.2200,
        uncertainty_km=8.0,
    ),
    Hotspot(
        name="Teluk Cenderawasih",
        aliases=("teluk cenderawasih", "cenderawasih", "kwatisore", "nabire"),
        lat=-3.2167,
        lon=134.9600,
        uncertainty_km=9.0,
    ),
    Hotspot(
        name="Probolinggo",
        aliases=("probolinggo", "pantai bentar", "bentar", "kalibuntu"),
        lat=-7.7300,
        lon=113.2800,
        uncertainty_km=8.0,
    ),
)

DEFAULT_RSS_FEEDS: tuple[tuple[str, str], ...] = (
    ("news_rss", "https://www.mongabay.co.id/feed/"),
    ("news_rss", "https://www.antaranews.com/rss/terkini.xml"),
)

# Verification sheet columns matching PROJECT_OVERVIEW.md (Section 2.A) and
# stages/01_occurrences/run_stage01.py:normalize_social_media_row().
SHEET_COLUMNS: list[str] = [
    "sighting_id",
    "platform",
    "post_url",
    "local_media_path",
    "caption_raw",
    "post_date",
    "sighting_date",
    "year",
    "month",
    "season",
    "domain",
    "locality_text",
    "lat_est",
    "lon_est",
    "coord_uncertainty_km",
    "status_verifikasi",
    "lat_koreksi",
    "lon_koreksi",
    "jumlah_individu",
    "perilaku_konteks",
    "catatan_dosen",
]

VALID_STATUS_VERIFIKASI: tuple[str, ...] = ("valid", "repost", "ragu", "tolak")
VALID_PERILAKU_KONTEKS: tuple[str, ...] = ("feeding", "bagan", "wisata", "melintas")
STUBBED_PLATFORMS: tuple[str, ...] = ("instagram", "tiktok", "x")

_WHALE_SHARK_RE = re.compile(r"\b(hiu\s+paus|whale\s+shark|rhincodon\s+typus)\b", re.IGNORECASE)
_ISO_DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?")


def determine_season(month: int | None) -> str:
    """Bucket month (1..12) into Indonesian monsoon season slices."""
    if month in (12, 1, 2):
        return "NWM"
    if month in (3, 4, 5):
        return "TR1"
    if month in (6, 7, 8):
        return "SEM"
    if month in (9, 10, 11):
        return "TR2"
    return "UNKNOWN"


def matches_whale_shark(text: str) -> bool:
    """Return True if text mentions whale shark / hiu paus / Rhincodon typus."""
    return bool(text and _WHALE_SHARK_RE.search(text))


def match_hotspot(text: str) -> Hotspot | None:
    """Match text against known Indonesian whale shark hotspots."""
    if not text:
        return None
    lowered = text.lower()
    for hs in HOTSPOTS:
        for alias in hs.aliases:
            if alias in lowered:
                return hs
    return None


def make_sighting_id(platform: str, canonical_url: str, external_id: str | None = None) -> str:
    """Generate a deterministic, filesystem-safe sighting_id."""
    prefix = re.sub(r"[^a-z0-9]+", "_", platform.lower()).strip("_") or "sm"
    if external_id:
        clean_ext = re.sub(r"[^A-Za-z0-9_-]+", "", external_id)[:40]
        if clean_ext:
            return f"{prefix}_{clean_ext}"
    digest = hashlib.sha256(canonical_url.strip().encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def extract_date_parts(date_str: str | None) -> tuple[int | None, int | None, str]:
    """Parse YYYY[-MM[-DD]] prefix into (year, month, normalized_date)."""
    raw = (date_str or "").strip()
    if not raw or "/" in raw:
        return None, None, ""
    m = _ISO_DATE_RE.match(raw)
    if not m:
        return None, None, ""
    year = int(m.group(1))
    month = int(m.group(2)) if m.group(2) else None
    if month is not None and not (1 <= month <= 12):
        month = None
    if m.group(2) and m.group(3):
        norm = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    elif m.group(2):
        norm = f"{m.group(1)}-{m.group(2)}"
    else:
        norm = m.group(1)
    return year, month, norm


def build_search_queries(include_hotspots: bool = True) -> list[str]:
    """Build search queries combining focal whale shark terms and Indonesian hotspots."""
    queries: list[str] = list(SEARCH_TERMS)
    if include_hotspots:
        for hs in HOTSPOTS:
            short_name = hs.name.split(",")[0].split("/")[0].strip()
            queries.append(f'"hiu paus" "{short_name}"')
            queries.append(f'"whale shark" "{short_name}"')
    return queries
