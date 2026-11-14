"""Official YouTube Data API v3 collector for public whale shark sightings."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .constants import (
    DEFAULT_DOMAIN,
    DEFAULT_MEDIA_DIR,
    WIB,
    YEAR_MAX,
    YEAR_MIN,
    extract_date_parts,
    make_sighting_id,
    match_hotspot,
    matches_whale_shark,
)
from .http_client import RequestBudgetExceeded, RobotsDisallowedError, ThrottledHttpClient

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


class MissingApiKeyError(RuntimeError):
    """Raised when YOUTUBE_API_KEY is not configured."""


def _redact_secret(msg: str, secret: str) -> str:
    if secret and secret in msg:
        msg = msg.replace(secret, "[REDACTED]")
    return re.sub(r"(key=)[^&\s]+", r"\1[REDACTED]", msg)


def get_youtube_api_key(load_env: bool = True) -> str:
    if load_env:
        load_dotenv(override=False)
    key = (os.environ.get("YOUTUBE_API_KEY") or "").strip()
    if not key:
        raise MissingApiKeyError(
            "YOUTUBE_API_KEY is not set. Export YOUTUBE_API_KEY in your environment or .env to use YouTube API v3."
        )
    return key


def _best_thumbnail_url(snippet: dict[str, Any]) -> str:
    thumbs = snippet.get("thumbnails") or {}
    for tier in ("high", "medium", "default"):
        entry = thumbs.get(tier) or {}
        url = str(entry.get("url") or "").strip()
        if url:
            return url
    return ""


def parse_youtube_item(
    search_item: dict[str, Any],
    video_detail: dict[str, Any] | None = None,
    query_term: str = "",
) -> dict[str, Any] | None:
    """Convert a YouTube Data API v3 search/video payload into a raw sighting record."""
    vid = ""
    raw_id = search_item.get("id")
    if isinstance(raw_id, dict):
        vid = str(raw_id.get("videoId") or "").strip()
    elif isinstance(raw_id, str):
        vid = raw_id.strip()
    if not vid and video_detail:
        vid = str(video_detail.get("id") or "").strip()
    if not vid:
        return None

    snippet = (video_detail or {}).get("snippet") or search_item.get("snippet") or {}
    title = str(snippet.get("title") or "").strip()
    description = str(snippet.get("description") or "").strip()
    caption = f"{title} — {description}".strip(" —") if description else title
    if not matches_whale_shark(caption):
        return None

    post_url = f"https://www.youtube.com/watch?v={vid}"
    sighting_id = make_sighting_id("youtube", post_url, external_id=vid)

    published_at = str(snippet.get("publishedAt") or "").strip()
    year, month, post_date = extract_date_parts(published_at)

    rec_details = (video_detail or {}).get("recordingDetails") or {}
    rec_loc = rec_details.get("location") or {}
    rec_date_raw = str(rec_details.get("recordingDate") or "").strip()
    _, _, sighting_date = extract_date_parts(rec_date_raw)
    if sighting_date:
        s_year, s_month, _ = extract_date_parts(sighting_date)
        year = s_year or year
        month = s_month or month

    loc_desc = str(rec_details.get("locationDescription") or "").strip()
    hs = match_hotspot(f"{loc_desc} {caption}")
    locality = loc_desc or (hs.name if hs else "")

    lat_est = rec_loc.get("latitude")
    lon_est = rec_loc.get("longitude")
    unc_km: float | None = None
    if lat_est is not None and lon_est is not None:
        unc_km = 5.0
    elif hs is not None:
        lat_est = hs.lat
        lon_est = hs.lon
        unc_km = hs.uncertainty_km

    media_url = _best_thumbnail_url(snippet)
    return {
        "sighting_id": sighting_id,
        "platform": "youtube",
        "post_url": post_url,
        "local_media_path": "",
        "caption_raw": caption,
        "post_date": post_date,
        "sighting_date": sighting_date,
        "year": year,
        "month": month,
        "domain": DEFAULT_DOMAIN,
        "locality_text": locality,
        "lat_est": lat_est,
        "lon_est": lon_est,
        "coord_uncertainty_km": unc_km,
        "media_url": media_url,
        "query_term": query_term,
        "scraped_at": datetime.now(WIB).isoformat(timespec="seconds"),
        "raw_payload": {
            "video_id": vid,
            "channel_title": snippet.get("channelTitle"),
            "published_at": published_at,
            "recording_details": rec_details or None,
        },
    }


def collect_youtube_sightings(
    client: ThrottledHttpClient,
    queries: list[str],
    api_key: str | None = None,
    max_results_per_query: int = 10,
    download_media: bool = True,
    media_dir: Path = DEFAULT_MEDIA_DIR,
) -> list[dict[str, Any]]:
    """Query YouTube Data API v3 for public Indonesian whale shark sighting videos."""
    key = api_key if api_key is not None else get_youtube_api_key()
    headers = {"X-goog-api-key": key}
    search_items_by_vid: dict[str, tuple[dict[str, Any], str]] = {}

    for q in queries:
        params = {
            "part": "snippet",
            "q": q,
            "type": "video",
            "maxResults": max(1, min(50, int(max_results_per_query))),
            "publishedAfter": f"{YEAR_MIN}-01-01T00:00:00Z",
            "publishedBefore": f"{YEAR_MAX}-12-31T23:59:59Z",
            "regionCode": "ID",
        }
        try:
            # Official authenticated REST API endpoint: pass key via header, skip robots.txt on googleapis.com
            client.session.headers.update(headers)
            resp = client.get(YOUTUBE_SEARCH_URL, params=params, check_robots=False)
            payload = resp.json()
        except RequestBudgetExceeded:
            break
        except Exception as exc:
            raise RuntimeError(_redact_secret(f"YouTube search failed for {q!r}: {exc}", key)) from exc
        finally:
            client.session.headers.pop("X-goog-api-key", None)

        for item in payload.get("items") or []:
            vid = str((item.get("id") or {}).get("videoId") or "").strip()
            if vid and vid not in search_items_by_vid:
                search_items_by_vid[vid] = (item, q)

    if not search_items_by_vid:
        return []

    # Enrich in batches of up to 50 to retrieve full descriptions and recordingDetails.
    details_by_vid: dict[str, dict[str, Any]] = {}
    vids = list(search_items_by_vid.keys())
    for i in range(0, len(vids), 50):
        batch = vids[i : i + 50]
        try:
            client.session.headers.update(headers)
            resp = client.get(
                YOUTUBE_VIDEOS_URL,
                params={"part": "snippet,recordingDetails", "id": ",".join(batch)},
                check_robots=False,
            )
            for item in resp.json().get("items") or []:
                vid = str(item.get("id") or "").strip()
                if vid:
                    details_by_vid[vid] = item
        except RequestBudgetExceeded:
            break
        except Exception as exc:
            raise RuntimeError(_redact_secret(f"YouTube videos lookup failed: {exc}", key)) from exc
        finally:
            client.session.headers.pop("X-goog-api-key", None)

    records: list[dict[str, Any]] = []
    for vid, (s_item, q) in search_items_by_vid.items():
        rec = parse_youtube_item(s_item, details_by_vid.get(vid), query_term=q)
        if not rec:
            continue
        if download_media and rec["media_url"]:
            try:
                saved = client.download_media(rec["media_url"], media_dir, rec["sighting_id"])
                if saved:
                    rec["local_media_path"] = saved
            except (RequestBudgetExceeded, RobotsDisallowedError):
                pass
            except Exception:
                pass
        records.append(rec)
    return records
