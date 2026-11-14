"""Public RSS / Atom / WP-JSON collector for news and dive-report whale shark sightings."""

from __future__ import annotations

import email.utils
import html
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_DOMAIN,
    DEFAULT_MEDIA_DIR,
    WIB,
    extract_date_parts,
    make_sighting_id,
    match_hotspot,
    matches_whale_shark,
)
from .http_client import RequestBudgetExceeded, RobotsDisallowedError, ThrottledHttpClient

_DOCTYPE_RE = re.compile(r"<!(?:DOCTYPE|ENTITY)\b[^>]*>", re.IGNORECASE)
_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def get_text(self) -> str:
        return " ".join(html.unescape("".join(self._parts)).split())


def strip_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    parser = _TextExtractor()
    parser.feed(raw_html)
    parser.close()
    return parser.get_text()


def _parse_feed_date(raw_date: str | None) -> tuple[int | None, int | None, str]:
    text = (raw_date or "").strip()
    if not text:
        return None, None, ""
    year, month, iso = extract_date_parts(text)
    if iso:
        return year, month, iso
    try:
        dt = email.utils.parsedate_to_datetime(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=WIB)
        iso_str = dt.astimezone(WIB).strftime("%Y-%m-%d")
        return dt.year, dt.month, iso_str
    except (TypeError, ValueError, OverflowError):
        return None, None, ""


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[-1].lower()


def _first_child_text(elem: ET.Element, names: tuple[str, ...]) -> str:
    for child in elem:
        if _local_name(child.tag) in names and child.text:
            return child.text.strip()
    return ""


def _extract_feed_image(elem: ET.Element, raw_html_snippets: list[str]) -> str:
    for child in elem:
        lname = _local_name(child.tag)
        if lname in ("enclosure", "content", "thumbnail"):
            url = (child.attrib.get("url") or "").strip()
            ctype = (child.attrib.get("type") or "").lower()
            medium = (child.attrib.get("medium") or "").lower()
            if url and (not ctype or ctype.startswith("image/") or medium == "image"):
                return url
    for snippet in raw_html_snippets:
        m = _IMG_SRC_RE.search(snippet or "")
        if m:
            return html.unescape(m.group(1).strip())
    return ""


def parse_feed_xml(
    xml_text: str,
    feed_url: str,
    platform: str = "news_rss",
) -> list[dict[str, Any]]:
    """Parse RSS 2.0 or Atom XML safely and return matching whale shark sighting records."""
    if "<!ENTITY" in xml_text.upper():
        raise ValueError("Refusing XML feed containing <!ENTITY declaration")
    cleaned_xml = _DOCTYPE_RE.sub("", xml_text)
    root = ET.fromstring(cleaned_xml)

    entries: list[ET.Element] = []
    root_name = _local_name(root.tag)
    if root_name == "rss":
        entries = [el for el in root.iter() if _local_name(el.tag) == "item"]
    elif root_name == "feed":
        entries = [el for el in root if _local_name(el.tag) == "entry"]
    else:
        entries = [el for el in root.iter() if _local_name(el.tag) in ("item", "entry")]

    records: list[dict[str, Any]] = []
    for entry in entries:
        title = strip_html(_first_child_text(entry, ("title",)))
        raw_desc = _first_child_text(entry, ("encoded", "content", "description", "summary"))
        desc = strip_html(raw_desc)
        caption = f"{title} — {desc}".strip(" —") if desc else title
        if not matches_whale_shark(caption):
            continue

        link = _first_child_text(entry, ("link", "guid"))
        if not link:
            for child in entry:
                if _local_name(child.tag) == "link" and child.attrib.get("href"):
                    rel = (child.attrib.get("rel") or "alternate").lower()
                    if rel in ("alternate", ""):
                        link = child.attrib["href"].strip()
                        break
        if not link:
            continue

        raw_date = _first_child_text(entry, ("pubdate", "published", "updated", "date"))
        year, month, post_date = _parse_feed_date(raw_date)
        hs = match_hotspot(caption)
        media_url = _extract_feed_image(entry, [raw_desc])
        sighting_id = make_sighting_id(platform, link)

        records.append({
            "sighting_id": sighting_id,
            "platform": platform,
            "post_url": link,
            "local_media_path": "",
            "caption_raw": caption,
            "post_date": post_date,
            "sighting_date": "",
            "year": year,
            "month": month,
            "domain": DEFAULT_DOMAIN,
            "locality_text": hs.name if hs else "",
            "lat_est": hs.lat if hs else None,
            "lon_est": hs.lon if hs else None,
            "coord_uncertainty_km": hs.uncertainty_km if hs else None,
            "media_url": media_url,
            "query_term": feed_url,
            "scraped_at": datetime.now(WIB).isoformat(timespec="seconds"),
            "raw_payload": {
                "feed_url": feed_url,
                "title": title,
                "pub_date_raw": raw_date,
            },
        })
    return records


def parse_wp_json_posts(
    posts: list[dict[str, Any]],
    feed_url: str,
    platform: str = "news_rss",
) -> list[dict[str, Any]]:
    """Parse WordPress REST API v2 `/wp-json/wp/v2/posts` items."""
    records: list[dict[str, Any]] = []
    for item in posts:
        if not isinstance(item, dict):
            continue
        title = strip_html(str((item.get("title") or {}).get("rendered") or ""))
        raw_excerpt = str((item.get("excerpt") or {}).get("rendered") or "")
        raw_content = str((item.get("content") or {}).get("rendered") or "")
        desc = strip_html(raw_excerpt or raw_content)
        caption = f"{title} — {desc}".strip(" —") if desc else title
        if not matches_whale_shark(caption):
            continue

        link = str(item.get("link") or "").strip()
        if not link:
            continue
        raw_date = str(item.get("date_gmt") or item.get("date") or "").strip()
        year, month, post_date = _parse_feed_date(raw_date)
        hs = match_hotspot(caption)
        media_url = _extract_feed_image(ET.Element("noop"), [raw_content, raw_excerpt])
        ext_id = str(item.get("id") or "").strip() or None

        records.append({
            "sighting_id": make_sighting_id(platform, link, external_id=ext_id),
            "platform": platform,
            "post_url": link,
            "local_media_path": "",
            "caption_raw": caption,
            "post_date": post_date,
            "sighting_date": "",
            "year": year,
            "month": month,
            "domain": DEFAULT_DOMAIN,
            "locality_text": hs.name if hs else "",
            "lat_est": hs.lat if hs else None,
            "lon_est": hs.lon if hs else None,
            "coord_uncertainty_km": hs.uncertainty_km if hs else None,
            "media_url": media_url,
            "query_term": feed_url,
            "scraped_at": datetime.now(WIB).isoformat(timespec="seconds"),
            "raw_payload": {
                "feed_url": feed_url,
                "wp_post_id": item.get("id"),
                "title": title,
                "date_raw": raw_date,
            },
        })
    return records


def collect_rss_sightings(
    client: ThrottledHttpClient,
    feeds: list[tuple[str, str]],
    download_media: bool = True,
    media_dir: Path = DEFAULT_MEDIA_DIR,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Fetch public RSS/Atom or WP-JSON feeds while respecting robots.txt."""
    collected: list[dict[str, Any]] = []
    warnings: list[str] = []

    for platform, url in feeds:
        try:
            resp = client.get(url, check_robots=True)
        except RobotsDisallowedError as exc:
            warnings.append(f"Skipped {url}: {exc}")
            continue
        except RequestBudgetExceeded:
            warnings.append(f"Stopped at {url}: request budget reached")
            break
        except Exception as exc:
            warnings.append(f"Failed {url}: {exc}")
            continue

        ctype = (resp.headers.get("Content-Type") or "").lower()
        body = resp.text
        try:
            if "json" in ctype or "wp-json" in url:
                data = resp.json()
                items = data if isinstance(data, list) else []
                recs = parse_wp_json_posts(items, feed_url=url, platform=platform)
            else:
                recs = parse_feed_xml(body, feed_url=url, platform=platform)
        except Exception as exc:
            warnings.append(f"Parse error for {url}: {exc}")
            continue

        for rec in recs:
            if download_media and rec["media_url"]:
                try:
                    saved = client.download_media(rec["media_url"], media_dir, rec["sighting_id"])
                    if saved:
                        rec["local_media_path"] = saved
                except (RequestBudgetExceeded, RobotsDisallowedError):
                    pass
                except Exception:
                    pass
            collected.append(rec)

    return collected, warnings
