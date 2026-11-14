#!/usr/bin/env python3
"""
Stage 01: Fetch, verify, clean, deduplicate, and 10 km spatially thin
Rhincodon typus (taxonKey=2417522, 2010-2026) occurrences for ID and AU.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import requests
from scipy.io import netcdf_file

STAGE_DIR = Path(__file__).resolve().parent
REPO_ROOT = STAGE_DIR.parents[1]
RAW_DIR = STAGE_DIR / "raw"
INPUT_DIR = STAGE_DIR / "input"
OUTPUT_DIR = STAGE_DIR / "output"
DEFAULT_GEBCO_PATH = REPO_ROOT / "data" / "gebco" / "gebco_2026_indopacific_90E_160E_40S_20N.nc"

TAXON_KEY = 2417522
TARGET_SPECIES = "Rhincodon typus"
YEAR_MIN = 2010
YEAR_MAX = 2026
MAX_UNCERTAINTY_M = 10000.0
THIN_DISTANCE_KM = 10.0
KDE_BANDWIDTH_KM = 25.0
BACKGROUND_COUNT_PER_DOMAIN = 10000
BACKGROUND_SEED = 20261114
EARTH_RADIUS_KM = 6371.0088

GBIF_URL = "https://api.gbif.org/v1/occurrence/search"
GBIF_PAGE_LIMIT = 300
GBIF_MAX_OFFSET = 100000

OBIS_URL = "https://api.obis.org/v3/occurrence"
OBIS_PAGE_SIZE = 1000
OBIS_AREA_IDS = {"ID": 115, "AU": 8}

BOGUS_UNCERTAINTY_VALUES = {301.0, 3036.0, 999.0, 9999.0}
REJECTED_BASIS_OF_RECORD = {
    "PRESERVED_SPECIMEN",
    "MATERIAL_SAMPLE",
    "FOSSIL_SPECIMEN",
}
REJECTED_GBIF_ISSUES = {
    "ZERO_COORDINATE",
    "COORDINATE_OUT_OF_RANGE",
    "COUNTRY_COORDINATE_MISMATCH",
    "RECORDED_DATE_INVALID",
    "RECORDED_DATE_UNLIKELY",
    "BASIS_OF_RECORD_INVALID",
}

# Country / capital centroids (lat, lon) to catch unflagged geocoded centroids within 1.0 km
KNOWN_CENTROIDS = [
    (-2.5489, 118.0149),   # Indonesia centroid
    (-6.2088, 106.8456),   # Jakarta centroid (inland)
    (-25.2744, 133.7751),  # Australia centroid
    (-35.2809, 149.1300),  # Canberra centroid (inland)
]
CENTROID_RADIUS_KM = 1.0

SEASONS = ("NWM", "TR1", "SEM", "TR2")
STREAM_PRIORITY = {"social_media_verified": 0, "gbif": 1, "obis": 2}
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
WIB = timezone(timedelta(hours=7))

CLEAN_COLUMNS = [
    "source_stream",
    "source_record_id",
    "domain",
    "taxon_key",
    "scientific_name",
    "species",
    "latitude",
    "longitude",
    "coordinate_uncertainty_m",
    "year",
    "month",
    "season",
    "event_date",
    "event_date_day",
    "basis_of_record",
    "occurrence_status",
    "locality",
    "dataset_name",
    "occurrence_url",
    "issues",
    "obis_bathymetry_m",
    "gebco_elevation_m",
    "status_verifikasi",
]

QUARANTINE_COLUMNS = CLEAN_COLUMNS + ["quarantine_reason"]

BACKGROUND_COLUMNS = [
    "domain",
    "latitude",
    "longitude",
    "gebco_elevation_m",
    "kde_bandwidth_km",
    "source_stream",
]


class GebcoRaster:
    """Nearest-cell lookup on a rectilinear GEBCO elevation grid (meters relative to sea level)."""

    def __init__(
        self,
        lat_axis: np.ndarray,
        lon_axis: np.ndarray,
        elevation: Any,
        nc_handle: Any = None,
        source_name: str = "synthetic",
    ) -> None:
        self.lat_axis = np.asarray(lat_axis, dtype=np.float64)
        self.lon_axis = np.asarray(lon_axis, dtype=np.float64)
        if self.lat_axis.ndim != 1 or self.lon_axis.ndim != 1:
            raise ValueError("GEBCO lat_axis and lon_axis must be 1D")
        if self.lat_axis.size == 0 or self.lon_axis.size == 0:
            raise ValueError("GEBCO grid axes cannot be empty")
        if np.any(np.diff(self.lat_axis) <= 0) or np.any(np.diff(self.lon_axis) <= 0):
            raise ValueError("GEBCO lat_axis and lon_axis must be strictly increasing")
        self._elevation = elevation
        self._nc_handle = nc_handle
        self.source_name = source_name

        self._lat_min = float(self.lat_axis[0]) - self._half_step_low(self.lat_axis)
        self._lat_max = float(self.lat_axis[-1]) + self._half_step_high(self.lat_axis)
        self._lon_min = float(self.lon_axis[0]) - self._half_step_low(self.lon_axis)
        self._lon_max = float(self.lon_axis[-1]) + self._half_step_high(self.lon_axis)

    @staticmethod
    def _half_step_low(axis: np.ndarray) -> float:
        return 0.5 * float(axis[1] - axis[0]) if axis.size >= 2 else 0.0025

    @staticmethod
    def _half_step_high(axis: np.ndarray) -> float:
        return 0.5 * float(axis[-1] - axis[-2]) if axis.size >= 2 else 0.0025

    @classmethod
    def from_arrays(
        cls,
        lat_axis: np.ndarray,
        lon_axis: np.ndarray,
        elevation: np.ndarray,
        source_name: str = "synthetic",
    ) -> "GebcoRaster":
        arr = np.asarray(elevation, dtype=np.float64)
        if arr.shape != (len(lat_axis), len(lon_axis)):
            raise ValueError(f"Elevation shape {arr.shape} does not match ({len(lat_axis)}, {len(lon_axis)})")
        return cls(lat_axis=lat_axis, lon_axis=lon_axis, elevation=arr, source_name=source_name)

    @classmethod
    def from_netcdf(cls, path: Path) -> "GebcoRaster":
        nc = netcdf_file(path, "r", mmap=True)
        try:
            lat_axis = np.array(nc.variables["lat"][:], dtype=np.float64, copy=True)
            lon_axis = np.array(nc.variables["lon"][:], dtype=np.float64, copy=True)
            elev = nc.variables["elevation"].data
        except Exception:
            nc.close()
            raise
        return cls(lat_axis=lat_axis, lon_axis=lon_axis, elevation=elev, nc_handle=nc, source_name=path.name)

    def close(self) -> None:
        self._elevation = None
        if self._nc_handle is not None:
            self._nc_handle.close()
            self._nc_handle = None

    def __enter__(self) -> "GebcoRaster":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    @staticmethod
    def _nearest_indices(axis: np.ndarray, values: np.ndarray) -> np.ndarray:
        n = axis.size
        if n == 1:
            return np.zeros(values.shape, dtype=np.intp)
        idx = np.searchsorted(axis, values, side="left")
        hi = np.clip(idx, 1, n - 1)
        lo = hi - 1
        pick_lo = np.abs(values - axis[lo]) <= np.abs(axis[hi] - values)
        return np.where(pick_lo, lo, hi)

    def elevations_at(self, lats: np.ndarray, lons: np.ndarray) -> np.ndarray:
        lat_q = np.asarray(lats, dtype=np.float64)
        lon_q = np.asarray(lons, dtype=np.float64)
        out = np.full(lat_q.shape, np.nan, dtype=np.float64)
        in_bounds = (
            np.isfinite(lat_q)
            & np.isfinite(lon_q)
            & (lat_q >= self._lat_min)
            & (lat_q <= self._lat_max)
            & (lon_q >= self._lon_min)
            & (lon_q <= self._lon_max)
        )
        if not np.any(in_bounds):
            return out
        iy = self._nearest_indices(self.lat_axis, lat_q[in_bounds])
        ix = self._nearest_indices(self.lon_axis, lon_q[in_bounds])
        out[in_bounds] = np.asarray(self._elevation[iy, ix], dtype=np.float64)
        return out

    def elevation_at(self, lat: float, lon: float) -> float | None:
        vals = self.elevations_at(np.array([lat], dtype=np.float64), np.array([lon], dtype=np.float64))
        val = float(vals[0])
        return None if math.isnan(val) else val


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def determine_season(month: int | None) -> str:
    if month in (12, 1, 2):
        return "NWM"
    if month in (3, 4, 5):
        return "TR1"
    if month in (6, 7, 8):
        return "SEM"
    if month in (9, 10, 11):
        return "TR2"
    return "UNKNOWN"


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, lam1 = math.radians(lat1), math.radians(lon1)
    phi2, lam2 = math.radians(lat2), math.radians(lon2)
    dphi = phi2 - phi1
    dlam = lam2 - lam1
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    return 2.0 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def request_json_with_retry(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    max_retries: int = 4,
    base_delay: float = 1.5,
) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = session.get(url, params=params, timeout=30)
            if resp.status_code in RETRYABLE_STATUS:
                raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
            if attempt == max_retries:
                break
            delay = base_delay * (2 ** attempt)
            print(f"[!] Transient fetch error ({exc}); retrying in {delay:.1f}s...")
            time.sleep(delay)
    raise RuntimeError(f"Request failed after {max_retries + 1} attempts for {url} {params}: {last_err}")


def fetch_gbif_raw(session: requests.Session, domain: str, out_path: Path) -> dict[str, Any]:
    query = {
        "taxonKey": TAXON_KEY,
        "country": domain,
        "year": f"{YEAR_MIN},{YEAR_MAX}",
        "hasCoordinate": "true",
        "hasGeospatialIssue": "false",
        "limit": GBIF_PAGE_LIMIT,
    }
    rows = 0
    pages = 0
    offset = 0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        while True:
            if offset + GBIF_PAGE_LIMIT > GBIF_MAX_OFFSET:
                raise RuntimeError(f"GBIF offset+limit exceeded {GBIF_MAX_OFFSET} for {domain}")
            page_params = {**query, "offset": offset}
            data = request_json_with_retry(session, GBIF_URL, page_params)
            results = data.get("results", [])
            pages += 1
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                rows += 1
            if data.get("endOfRecords", False) or not results:
                break
            offset += len(results)
            time.sleep(0.15)
    print(f"[+] GBIF {domain}: fetched {rows} rows across {pages} page(s) -> {out_path.name}")
    return {
        "source": "gbif",
        "domain": domain,
        "query": query,
        "query_hash": sha256_json(query),
        "fetched_at": datetime.now(WIB).isoformat(timespec="seconds"),
        "pages": pages,
        "rows": rows,
        "file": out_path.name,
        "sha256_file": sha256_file(out_path),
    }


def fetch_obis_raw(session: requests.Session, domain: str, out_path: Path) -> dict[str, Any]:
    area_id = OBIS_AREA_IDS[domain]
    query = {
        "scientificname": TARGET_SPECIES,
        "areaid": area_id,
        "startdate": f"{YEAR_MIN}-01-01",
        "enddate": f"{YEAR_MAX}-12-31",
        "size": OBIS_PAGE_SIZE,
    }
    rows = 0
    pages = 0
    after: str | None = None
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        while True:
            page_params = dict(query)
            if after:
                page_params["after"] = after
            data = request_json_with_retry(session, OBIS_URL, page_params)
            results = data.get("results", [])
            pages += 1
            if not results:
                break
            for item in results:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                rows += 1
            after = str(results[-1].get("id") or "")
            if len(results) < OBIS_PAGE_SIZE or not after:
                break
            time.sleep(0.15)
    print(f"[+] OBIS {domain} (areaid={area_id}): fetched {rows} rows across {pages} page(s) -> {out_path.name}")
    return {
        "source": "obis",
        "domain": domain,
        "query": query,
        "query_hash": sha256_json(query),
        "fetched_at": datetime.now(WIB).isoformat(timespec="seconds"),
        "pages": pages,
        "rows": rows,
        "file": out_path.name,
        "sha256_file": sha256_file(out_path),
    }


def parse_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        num = float(val)
        return None if math.isnan(num) or math.isinf(num) else num
    except (TypeError, ValueError):
        return None


def parse_int(val: Any) -> int | None:
    if val is None or val == "":
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def clean_uncertainty(val: Any) -> float | None:
    num = parse_float(val)
    if num is None or num in BOGUS_UNCERTAINTY_VALUES or num < 0:
        return None
    return num


def parse_date_parts(year_val: Any, month_val: Any, event_date_val: Any) -> tuple[int | None, int | None, str]:
    ev = "" if event_date_val is None else str(event_date_val).strip()
    year = parse_int(year_val)
    month = parse_int(month_val)
    day_str = ""
    if ev and "/" not in ev:
        m = re.match(r"^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?", ev)
        if m:
            if year is None:
                year = int(m.group(1))
            if month is None and m.group(2):
                month = int(m.group(2))
            if m.group(2) and m.group(3):
                day_str = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
            elif m.group(2):
                day_str = f"{m.group(1)}-{m.group(2)}"
            else:
                day_str = m.group(1)
    if month is not None and not (1 <= month <= 12):
        month = None
    return year, month, day_str


def normalize_gbif_row(item: dict[str, Any], domain: str) -> dict[str, Any]:
    year, month, day_str = parse_date_parts(item.get("year"), item.get("month"), item.get("eventDate"))
    unc = clean_uncertainty(item.get("coordinateUncertaintyInMeters"))
    issues = ";".join(item.get("issues") or [])
    return {
        "source_stream": "gbif",
        "source_record_id": str(item.get("gbifID") or ""),
        "domain": domain,
        "taxon_key": parse_int(item.get("taxonKey")) or parse_int(item.get("acceptedTaxonKey")),
        "scientific_name": item.get("scientificName") or "",
        "species": item.get("species") or "",
        "latitude": parse_float(item.get("decimalLatitude")),
        "longitude": parse_float(item.get("decimalLongitude")),
        "coordinate_uncertainty_m": unc,
        "year": year,
        "month": month,
        "season": determine_season(month),
        "event_date": str(item.get("eventDate") or ""),
        "event_date_day": day_str,
        "basis_of_record": str(item.get("basisOfRecord") or "").upper(),
        "occurrence_status": str(item.get("occurrenceStatus") or "PRESENT").upper(),
        "locality": str(item.get("verbatimLocality") or item.get("locality") or ""),
        "dataset_name": str(item.get("datasetName") or item.get("datasetKey") or ""),
        "occurrence_url": str(item.get("occurrenceID") or item.get("references") or f"https://www.gbif.org/occurrence/{item.get('gbifID')}"),
        "issues": issues,
        "obis_bathymetry_m": None,
        "gebco_elevation_m": None,
        "status_verifikasi": "not_applicable",
        "_raw_absence": False,
        "_obis_flags": set(),
        "_obis_marine": None,
        "_on_land_source": None,
    }


def normalize_obis_row(item: dict[str, Any], domain: str) -> dict[str, Any]:
    event_date = item.get("eventDate") or ""
    if not event_date and item.get("date_mid") is not None:
        try:
            dt = datetime.fromtimestamp(float(item["date_mid"]) / 1000.0, tz=timezone.utc)
            event_date = dt.strftime("%Y-%m-%d")
        except (TypeError, ValueError, OSError):
            pass
    year, month, day_str = parse_date_parts(item.get("date_year"), None, event_date)
    unc = clean_uncertainty(item.get("coordinateUncertaintyInMeters"))
    flags = set(item.get("flags") or [])
    return {
        "source_stream": "obis",
        "source_record_id": str(item.get("id") or ""),
        "domain": domain,
        "taxon_key": TAXON_KEY if (item.get("species") == TARGET_SPECIES or str(item.get("scientificName", "")).startswith(TARGET_SPECIES)) else None,
        "scientific_name": item.get("scientificName") or "",
        "species": item.get("species") or "",
        "latitude": parse_float(item.get("decimalLatitude")),
        "longitude": parse_float(item.get("decimalLongitude")),
        "coordinate_uncertainty_m": unc,
        "year": year,
        "month": month,
        "season": determine_season(month),
        "event_date": str(event_date),
        "event_date_day": day_str,
        "basis_of_record": str(item.get("basisOfRecord") or "").upper(),
        "occurrence_status": str(item.get("occurrenceStatus") or ("ABSENT" if item.get("absence") else "PRESENT")).upper(),
        "locality": str(item.get("locality") or ""),
        "dataset_name": str(item.get("dataset_id") or ""),
        "occurrence_url": str(item.get("occurrenceID") or f"https://obis.org/occurrence/{item.get('id')}"),
        "issues": ";".join(sorted(flags)),
        "obis_bathymetry_m": parse_float(item.get("bathymetry")),
        "gebco_elevation_m": None,
        "status_verifikasi": "not_applicable",
        "_raw_absence": bool(item.get("absence")),
        "_obis_flags": flags,
        "_obis_marine": item.get("marine"),
        "_on_land_source": None,
    }


def normalize_social_media_row(row: dict[str, str]) -> dict[str, Any]:
    def first_float(*keys: str) -> float | None:
        # Explicit None check: a corrected coordinate of exactly 0.0 is valid.
        for key in keys:
            val = parse_float(row.get(key))
            if val is not None:
                return val
        return None

    lat = first_float("lat_koreksi", "lat_est", "latitude")
    lon = first_float("lon_koreksi", "lon_est", "longitude")
    unc_km = parse_float(row.get("coord_uncertainty_km"))
    unc_m = clean_uncertainty(unc_km * 1000.0 if unc_km is not None else row.get("coordinate_uncertainty_m"))
    ev = str(row.get("sighting_date") or row.get("post_date") or row.get("event_date") or "")
    year, month, day_str = parse_date_parts(row.get("year"), row.get("month"), ev)
    status = str(row.get("status_verifikasi") or "").strip().lower()
    return {
        "source_stream": "social_media_verified",
        "source_record_id": str(row.get("sighting_id") or ""),
        "domain": str(row.get("domain") or "ID").upper(),
        "taxon_key": TAXON_KEY,
        "scientific_name": TARGET_SPECIES,
        "species": TARGET_SPECIES,
        "latitude": lat,
        "longitude": lon,
        "coordinate_uncertainty_m": unc_m,
        "year": year,
        "month": month,
        "season": determine_season(month),
        "event_date": ev,
        "event_date_day": day_str,
        "basis_of_record": "HUMAN_OBSERVATION",
        "occurrence_status": "PRESENT",
        "locality": str(row.get("locality_text") or ""),
        "dataset_name": str(row.get("platform") or "social_media"),
        "occurrence_url": str(row.get("post_url") or ""),
        "issues": "",
        "obis_bathymetry_m": None,
        "gebco_elevation_m": None,
        "status_verifikasi": status,
        "_raw_absence": False,
        "_obis_flags": set(),
        "_obis_marine": None,
        "_on_land_source": None,
    }


def evaluate_row(
    row: dict[str, Any],
    gebco_sampler: GebcoRaster | Callable[[float, float], float | None] | None = None,
) -> str | None:
    if row["source_stream"] == "social_media_verified" and row["status_verifikasi"] != "valid":
        return "unverified_social_media"
    if row["taxon_key"] != TAXON_KEY and row["species"] != TARGET_SPECIES:
        return "wrong_taxon"
    lat, lon = row["latitude"], row["longitude"]
    if lat is None or lon is None:
        return "missing_coords"
    if abs(lat) > 90.0 or abs(lon) > 180.0 or (lat == 0.0 and lon == 0.0):
        return "invalid_coord"
    ev = row["event_date"]
    if "/" in ev:
        return "date_range_not_date"
    if row["year"] is None and not ev:
        return "missing_date"
    if row["year"] is None or row["year"] < YEAR_MIN or row["year"] > YEAR_MAX:
        return "out_of_temporal_window"
    if row["occurrence_status"] == "ABSENT" or row["_raw_absence"]:
        return "not_presence"
    if row["basis_of_record"] in REJECTED_BASIS_OF_RECORD:
        return "not_observation"
    unc = row["coordinate_uncertainty_m"]
    if unc is not None and unc > MAX_UNCERTAINTY_M:
        return "high_uncertainty"
    issues = set(filter(None, row["issues"].split(";")))
    if issues & REJECTED_GBIF_ISSUES:
        return "gbif_issue_flag"
    for clat, clon in KNOWN_CENTROIDS:
        if haversine_km(lat, lon, clat, clon) <= CENTROID_RADIUS_KM:
            return "near_centroid"

    # Populate GEBCO elevation (negative below sea level; >= 0 is land/sea-level)
    gebco_elev: float | None = None
    if gebco_sampler is not None:
        if isinstance(gebco_sampler, GebcoRaster):
            gebco_elev = gebco_sampler.elevation_at(lat, lon)
        else:
            gebco_elev = gebco_sampler(lat, lon)
        if gebco_elev is not None:
            row["gebco_elevation_m"] = int(round(gebco_elev)) if float(gebco_elev).is_integer() else round(float(gebco_elev), 2)

    # Secondary OBIS flags (note: OBIS bathymetry is positive depth below sea level)
    obis_land = (
        ("ON_LAND" in row["_obis_flags"])
        or (row["obis_bathymetry_m"] is not None and row["obis_bathymetry_m"] <= 0)
        or (row["_obis_marine"] is False)
    )
    gebco_land = gebco_elev is not None and gebco_elev >= 0.0
    if obis_land or gebco_land:
        if obis_land and gebco_land:
            row["_on_land_source"] = "both"
        elif obis_land:
            row["_on_land_source"] = "obis"
        else:
            row["_on_land_source"] = "gebco"
        return "on_land"
    return None


def dedupe_rows(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def quality_key(r: dict[str, Any]) -> tuple[float, int, str]:
        unc = r["coordinate_uncertainty_m"]
        unc_score = unc if unc is not None else 1e9
        prio = STREAM_PRIORITY.get(r["source_stream"], 9)
        return (unc_score, prio, r["source_record_id"])

    quarantined: list[dict[str, Any]] = []
    primary_seen: dict[tuple[str, str, str], dict[str, Any]] = {}
    after_primary: list[dict[str, Any]] = []

    for r in sorted(rows, key=quality_key):
        pkey = (r["domain"], r["source_stream"], r["source_record_id"])
        if r["source_record_id"] and pkey in primary_seen:
            q = dict(r)
            q["quarantine_reason"] = "duplicate_primary"
            quarantined.append(q)
        else:
            if r["source_record_id"]:
                primary_seen[pkey] = r
            after_primary.append(r)

    secondary_seen: dict[tuple[str, float, float, str], dict[str, Any]] = {}
    clean: list[dict[str, Any]] = []
    for r in sorted(after_primary, key=quality_key):
        skey = (
            r["domain"],
            round(r["latitude"], 4),
            round(r["longitude"], 4),
            r["event_date_day"] or r["event_date"],
        )
        if skey in secondary_seen:
            q = dict(r)
            q["quarantine_reason"] = "duplicate_cross_source"
            quarantined.append(q)
        else:
            secondary_seen[skey] = r
            clean.append(r)

    clean.sort(key=lambda r: (r["domain"], r["season"], r["event_date_day"] or r["event_date"], r["latitude"], r["longitude"], r["source_record_id"]))
    return clean, quarantined


def greedy_thin(rows: list[dict[str, Any]], min_km: float = THIN_DISTANCE_KM) -> list[dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda r: (
            r["coordinate_uncertainty_m"] if r["coordinate_uncertainty_m"] is not None else 1e9,
            STREAM_PRIORITY.get(r["source_stream"], 9),
            r["event_date_day"] or r["event_date"] or "9999-99-99",
            r["latitude"],
            r["longitude"],
            r["source_record_id"],
        ),
    )
    kept: list[dict[str, Any]] = []
    for cand in ordered:
        too_close = False
        for prev in kept:
            if haversine_km(cand["latitude"], cand["longitude"], prev["latitude"], prev["longitude"]) < min_km:
                too_close = True
                break
        if not too_close:
            kept.append(cand)
    return kept


def min_pairwise_km(rows: list[dict[str, Any]]) -> float | None:
    if len(rows) < 2:
        return None
    min_d = float("inf")
    for i in range(len(rows)):
        lat1, lon1 = rows[i]["latitude"], rows[i]["longitude"]
        for j in range(i + 1, len(rows)):
            d = haversine_km(lat1, lon1, rows[j]["latitude"], rows[j]["longitude"])
            if d < min_d:
                min_d = d
    return min_d


def write_csv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({c: r.get(c, "") for c in columns})
    return sha256_file(path)


def sample_kde_background(
    presence_rows: list[dict[str, Any]],
    ocean_elevation_fn: Callable[[np.ndarray, np.ndarray], np.ndarray],
    domain: str,
    n_points: int = BACKGROUND_COUNT_PER_DOMAIN,
    bandwidth_km: float = KDE_BANDWIDTH_KM,
    seed: int = BACKGROUND_SEED,
    max_batches: int = 500,
) -> list[dict[str, Any]]:
    """Sample n_points ocean-only pseudo-absences from an isotropic 2D Gaussian KDE (bandwidth_km)."""
    if n_points <= 0:
        return []
    if not presence_rows:
        raise ValueError(f"Cannot build KDE background for {domain}: 0 clean presence rows")

    lats_rad = np.radians([float(r["latitude"]) for r in presence_rows])
    lons_rad = np.radians([float(r["longitude"]) for r in presence_rows])
    n_pres = lats_rad.size
    rng = np.random.default_rng(seed)

    accepted_lats: list[np.ndarray] = []
    accepted_lons: list[np.ndarray] = []
    accepted_elevs: list[np.ndarray] = []
    collected = 0

    for _ in range(max_batches):
        remaining = n_points - collected
        if remaining <= 0:
            break
        batch_size = min(max(remaining * 3, 512), 100000)
        idx = rng.integers(0, n_pres, size=batch_size)
        dn = rng.normal(0.0, bandwidth_km, size=batch_size)
        de = rng.normal(0.0, bandwidth_km, size=batch_size)
        delta = np.hypot(dn, de) / EARTH_RADIUS_KM
        theta = np.arctan2(de, dn)

        lat0 = lats_rad[idx]
        lon0 = lons_rad[idx]
        sin_lat0 = np.sin(lat0)
        cos_lat0 = np.cos(lat0)
        sin_d = np.sin(delta)
        cos_d = np.cos(delta)

        lat_new = np.arcsin(np.clip(sin_lat0 * cos_d + cos_lat0 * sin_d * np.cos(theta), -1.0, 1.0))
        lon_new = lon0 + np.arctan2(np.sin(theta) * sin_d * cos_lat0, cos_d - sin_lat0 * np.sin(lat_new))

        lat_deg = np.round(np.degrees(lat_new), 6)
        lon_deg = np.round(((np.degrees(lon_new) + 180.0) % 360.0) - 180.0, 6)

        elevs = np.asarray(ocean_elevation_fn(lat_deg, lon_deg), dtype=np.float64)
        mask = np.isfinite(elevs) & (elevs < 0.0)
        if np.any(mask):
            take = min(remaining, int(np.count_nonzero(mask)))
            accepted_lats.append(lat_deg[mask][:take])
            accepted_lons.append(lon_deg[mask][:take])
            accepted_elevs.append(elevs[mask][:take])
            collected += take

    if collected < n_points:
        raise RuntimeError(
            f"KDE background sampling for {domain} yielded only {collected}/{n_points} ocean points after {max_batches} batches"
        )

    all_lats = np.concatenate(accepted_lats)[:n_points]
    all_lons = np.concatenate(accepted_lons)[:n_points]
    all_elevs = np.concatenate(accepted_elevs)[:n_points]
    return [
        {
            "domain": domain,
            "latitude": float(lat),
            "longitude": float(lon),
            "gebco_elevation_m": int(round(float(elev))),
            "kde_bandwidth_km": bandwidth_km,
            "source_stream": "background_kde",
        }
        for lat, lon, elev in zip(all_lats, all_lons, all_elevs)
    ]


def run_pipeline(
    from_raw: bool = False,
    social_media_csv: Path | None = None,
    gebco_path: Path | None = None,
    background_count: int = BACKGROUND_COUNT_PER_DOMAIN,
    background_seed: int = BACKGROUND_SEED,
) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest_path = RAW_DIR / "manifest.json"
    if not from_raw:
        session = requests.Session()
        session.headers.update({"User-Agent": "WhaleScraperResearch/1.0 (rhincodon-typus-sdm)"})
        entries = [
            fetch_gbif_raw(session, "ID", RAW_DIR / "gbif_id.jsonl"),
            fetch_gbif_raw(session, "AU", RAW_DIR / "gbif_au.jsonl"),
            fetch_obis_raw(session, "ID", RAW_DIR / "obis_id.jsonl"),
            fetch_obis_raw(session, "AU", RAW_DIR / "obis_au.jsonl"),
        ]
        manifest = {
            "generated_at": datetime.now(WIB).isoformat(timespec="seconds"),
            "taxon_key": TAXON_KEY,
            "species": TARGET_SPECIES,
            "temporal_window": f"{YEAR_MIN}-{YEAR_MAX}",
            "sources": entries,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    raw_rows: list[dict[str, Any]] = []
    raw_counts: dict[tuple[str, str], int] = {}

    for domain in ("ID", "AU"):
        gbif_file = RAW_DIR / f"gbif_{domain.lower()}.jsonl"
        cnt = 0
        if gbif_file.exists():
            with gbif_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        raw_rows.append(normalize_gbif_row(json.loads(line), domain))
                        cnt += 1
        raw_counts[(domain, "gbif")] = cnt

        obis_file = RAW_DIR / f"obis_{domain.lower()}.jsonl"
        cnt = 0
        if obis_file.exists():
            with obis_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        raw_rows.append(normalize_obis_row(json.loads(line), domain))
                        cnt += 1
        raw_counts[(domain, "obis")] = cnt

    sm_path = social_media_csv or (INPUT_DIR / "social_media_verified.csv")
    sm_loaded = False
    if sm_path and sm_path.exists():
        sm_loaded = True
        with sm_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                nr = normalize_social_media_row(r)
                raw_rows.append(nr)
                key = (nr["domain"], "social_media_verified")
                raw_counts[key] = raw_counts.get(key, 0) + 1

    resolved_gebco = gebco_path or DEFAULT_GEBCO_PATH
    gebco_raster: GebcoRaster | None = None
    gebco_applied = False
    if resolved_gebco and resolved_gebco.exists():
        gebco_raster = GebcoRaster.from_netcdf(resolved_gebco)
        gebco_applied = True

    try:
        valid_rows: list[dict[str, Any]] = []
        quarantine_rows: list[dict[str, Any]] = []
        reason_counts: dict[str, int] = {}
        on_land_by_source = {"obis": 0, "gebco": 0, "both": 0}
        on_land_by_domain = {
            "ID": {"obis": 0, "gebco": 0, "both": 0},
            "AU": {"obis": 0, "gebco": 0, "both": 0},
        }

        for r in raw_rows:
            reason = evaluate_row(r, gebco_sampler=gebco_raster)
            if reason:
                q = dict(r)
                q["quarantine_reason"] = reason
                quarantine_rows.append(q)
                reason_counts[reason] = reason_counts.get(reason, 0) + 1
                if reason == "on_land" and r["_on_land_source"] in on_land_by_source:
                    src_tag = r["_on_land_source"]
                    on_land_by_source[src_tag] += 1
                    if r["domain"] in on_land_by_domain:
                        on_land_by_domain[r["domain"]][src_tag] += 1
            else:
                valid_rows.append(r)

        clean_rows, dup_quarantine = dedupe_rows(valid_rows)
        for dq in dup_quarantine:
            reason = dq["quarantine_reason"]
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        quarantine_rows.extend(dup_quarantine)

        checksums: dict[str, str] = {}
        clean_by_domain: dict[str, list[dict[str, Any]]] = {"ID": [], "AU": []}
        for r in clean_rows:
            if r["domain"] in clean_by_domain:
                clean_by_domain[r["domain"]].append(r)

        for domain in ("ID", "AU"):
            fname = f"rhincodon_{domain.lower()}_clean.csv"
            checksums[fname] = write_csv(OUTPUT_DIR / fname, CLEAN_COLUMNS, clean_by_domain[domain])

        checksums["quarantine.csv"] = write_csv(OUTPUT_DIR / "quarantine.csv", QUARANTINE_COLUMNS, quarantine_rows)

        thin_stats: list[dict[str, Any]] = []
        min_dist_violations = 0
        for domain in ("ID", "AU"):
            for season in SEASONS:
                slice_rows = [r for r in clean_by_domain[domain] if r["season"] == season]
                thinned = greedy_thin(slice_rows, THIN_DISTANCE_KM)
                min_d = min_pairwise_km(thinned)
                if min_d is not None and min_d < THIN_DISTANCE_KM:
                    min_dist_violations += 1
                fname = f"rhincodon_{domain.lower()}_{season.lower()}.csv"
                sha = write_csv(OUTPUT_DIR / fname, CLEAN_COLUMNS, thinned)
                checksums[fname] = sha
                thin_stats.append({
                    "domain": domain,
                    "season": season,
                    "pre_thin": len(slice_rows),
                    "post_thin": len(thinned),
                    "min_km": min_d,
                    "file": fname,
                })

        bg_stats: list[dict[str, Any]] = []
        bg_by_domain: dict[str, list[dict[str, Any]]] = {"ID": [], "AU": []}
        kde_applied = False
        bg_count_violations = 0
        bg_on_land_violations = 0
        clean_on_land_violations = 0

        if gebco_raster is not None:
            if clean_rows:
                clean_lats = np.array([float(r["latitude"]) for r in clean_rows], dtype=np.float64)
                clean_lons = np.array([float(r["longitude"]) for r in clean_rows], dtype=np.float64)
                clean_elevs = gebco_raster.elevations_at(clean_lats, clean_lons)
                clean_on_land_violations = int(np.count_nonzero(np.isfinite(clean_elevs) & (clean_elevs >= 0.0)))

            kde_ready = True
            for dom_idx, domain in enumerate(("ID", "AU")):
                pres = clean_by_domain[domain]
                if not pres:
                    kde_ready = False
                    continue
                bg_rows = sample_kde_background(
                    pres,
                    gebco_raster.elevations_at,
                    domain=domain,
                    n_points=background_count,
                    bandwidth_km=KDE_BANDWIDTH_KM,
                    seed=background_seed + dom_idx,
                )
                bg_by_domain[domain] = bg_rows
                fname = f"background_{domain.lower()}.csv"
                checksums[fname] = write_csv(OUTPUT_DIR / fname, BACKGROUND_COLUMNS, bg_rows)
                bg_lats = np.array([r["latitude"] for r in bg_rows], dtype=np.float64)
                bg_lons = np.array([r["longitude"] for r in bg_rows], dtype=np.float64)
                bg_elevs = gebco_raster.elevations_at(bg_lats, bg_lons)
                on_land_cnt = int(np.count_nonzero(~np.isfinite(bg_elevs) | (bg_elevs >= 0.0)))
                if len(bg_rows) != background_count:
                    bg_count_violations += 1
                bg_on_land_violations += on_land_cnt
                bg_stats.append({
                    "domain": domain,
                    "pres_count": len(pres),
                    "bg_count": len(bg_rows),
                    "on_land": on_land_cnt,
                    "min_elev": int(np.min(bg_elevs)) if bg_elevs.size else 0,
                    "max_elev": int(np.max(bg_elevs)) if bg_elevs.size else 0,
                    "seed": background_seed + dom_idx,
                    "file": fname,
                })
            kde_applied = kde_ready and len(bg_stats) == 2

        # Audit checks
        bad_taxon = sum(1 for r in clean_rows if r["taxon_key"] != TAXON_KEY)
        bad_coords = sum(1 for r in clean_rows if r["latitude"] is None or r["longitude"] is None)
        bad_year = sum(1 for r in clean_rows if r["year"] is None or r["year"] < YEAR_MIN)
        bad_sm = sum(1 for r in clean_rows if r["source_stream"] == "social_media_verified" and r["status_verifikasi"] != "valid")

        missing_gates: list[str] = []
        if not sm_loaded:
            missing_gates.append("Pembimbing 2 verified social_media_verified CSV not yet supplied")
        if not gebco_applied:
            missing_gates.append("GEBCO bathymetry raster land mask (elevation >= 0 m) not applied (raster missing)")
        if not kde_applied:
            missing_gates.append("25 km KDE ocean background points not generated")

        hard_fail = bool(
            bad_taxon
            or bad_coords
            or bad_year
            or bad_sm
            or min_dist_violations
            or clean_on_land_violations
            or bg_count_violations
            or bg_on_land_violations
        )
        if hard_fail:
            status_line = "fail: hard occurrence, GEBCO mask, thinning, or KDE background validation failed"
        elif missing_gates:
            status_line = (
                "fail: open-repo GBIF+OBIS fetch/clean/GEBCO-mask/10km-thinning/25km-KDE-background passed, but "
                + "; ".join(missing_gates)
            )
        else:
            status_line = "pass"

        obis_land_total = on_land_by_source["obis"] + on_land_by_source["both"]
        gebco_extra_total = on_land_by_source["gebco"]
        if gebco_applied:
            gebco_line = (
                f"APPLIED (`{resolved_gebco.name}`; elevation >= 0 m quarantined as `on_land`; "
                f"OBIS-flagged={obis_land_total}, GEBCO-extra={gebco_extra_total}, total={obis_land_total + gebco_extra_total})"
            )
        else:
            gebco_line = f"NOT APPLIED (missing `{resolved_gebco}` — OBIS ON_LAND/bathymetry/marine flags only)"

        if kde_applied:
            bg_summary = ", ".join(f"{st['domain']}={st['bg_count']}" for st in bg_stats)
            kde_line = f"APPLIED ({bg_summary}; {bg_on_land_violations} on land; bandwidth={KDE_BANDWIDTH_KM} km; seed={background_seed})"
        else:
            kde_line = "NOT APPLIED (0 background points generated)"

        lines = [
            status_line,
            "",
            f"Generated: {datetime.now(WIB).isoformat(timespec='seconds')}",
            "",
            "## Integrity Checks",
            f"- Rows with taxonKey != {TAXON_KEY}: {bad_taxon}",
            f"- Rows with missing coordinates: {bad_coords}",
            f"- Rows with year < {YEAR_MIN}: {bad_year}",
            f"- Unverified social-media rows in clean output: {bad_sm}",
            f"- Thinned slices with min pairwise distance < {THIN_DISTANCE_KM} km: {min_dist_violations}",
            f"- Clean rows with GEBCO elevation >= 0 m: {clean_on_land_violations}",
            f"- GEBCO raster land mask: {gebco_line}",
            f"- 25 km Gaussian KDE ocean background: {kde_line}",
            f"- Social-media verified stream loaded: {'YES' if sm_loaded else 'NO (0 rows)'}",
            "",
            "## Counts by Domain & Source Stream (Raw -> Clean Post-Dedupe)",
            "| Domain | Stream | Raw | Clean (Post-Dedupe) |",
            "|---|---|---:|---:|",
        ]
        for domain in ("ID", "AU"):
            for stream in ("gbif", "obis", "social_media_verified"):
                rc = raw_counts.get((domain, stream), 0)
                cc = sum(1 for r in clean_by_domain[domain] if r["source_stream"] == stream)
                lines.append(f"| {domain} | {stream} | {rc} | {cc} |")

        if gebco_applied:
            lines.extend([
                "",
                "## Land Mask Breakdown (Pre-Dedupe)",
                "| Domain | OBIS Only | Both OBIS & GEBCO | GEBCO Extra | Total `on_land` |",
                "|---|---:|---:|---:|---:|",
            ])
            for domain in ("ID", "AU"):
                d = on_land_by_domain[domain]
                tot = d["obis"] + d["both"] + d["gebco"]
                lines.append(f"| {domain} | {d['obis']} | {d['both']} | {d['gebco']} | {tot} |")

        lines.extend([
            "",
            "## Seasonal Thinning (10 km Haversine)",
            "| Domain | Season | Pre-Thin | Post-Thin (10 km) | Min Pairwise km | Output File |",
            "|---|---|---:|---:|---:|---|",
        ])
        for st in thin_stats:
            md_str = f"{st['min_km']:.2f}" if st["min_km"] is not None else "n/a (<2 pts)"
            lines.append(f"| {st['domain']} | {st['season']} | {st['pre_thin']} | {st['post_thin']} | {md_str} | `{st['file']}` |")

        for domain in ("ID", "AU"):
            unk = sum(1 for r in clean_by_domain[domain] if r["season"] == "UNKNOWN")
            lines.append(f"- `{domain}` `UNKNOWN`-season clean rows (excluded from seasonal slices): {unk}")

        if bg_stats:
            lines.extend([
                "",
                "## Bias-Corrected Background Points (25 km Gaussian KDE, Ocean Cells Only)",
                "| Domain | Clean Presences (KDE Input) | Background Points | On-Land Points | Min Elev (m) | Max Elev (m) | Seed | Output File |",
                "|---|---:|---:|---:|---:|---:|---:|---|",
            ])
            for st in bg_stats:
                lines.append(
                    f"| {st['domain']} | {st['pres_count']} | {st['bg_count']} | {st['on_land']} | "
                    f"{st['min_elev']} | {st['max_elev']} | {st['seed']} | `{st['file']}` |"
                )

        lines.extend([
            "",
            "## Quarantine Breakdown",
            f"- Total quarantined rows: {len(quarantine_rows)}",
            "| Reason | Count |",
            "|---|---:|",
        ])
        for reason, cnt in sorted(reason_counts.items(), key=lambda kv: (-kv[1], kv[0])):
            lines.append(f"| `{reason}` | {cnt} |")

        lines.extend([
            "",
            "## Output SHA-256 Checksums",
            "| File | SHA-256 |",
            "|---|---|",
        ])
        for fname, sha in sorted(checksums.items()):
            lines.append(f"| `{fname}` | `{sha}` |")

        (OUTPUT_DIR / "check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"[+] Stage 01 complete. Audit written to {OUTPUT_DIR / 'check.md'}")
        print(f"    Status: {status_line}")
    finally:
        if gebco_raster is not None:
            gebco_raster.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Stage 01 occurrence pipeline for Rhincodon typus.")
    parser.add_argument("--from-raw", action="store_true", help="Skip API fetch and rebuild from raw/*.jsonl")
    parser.add_argument("--social-media-csv", type=Path, default=None, help="Path to Pembimbing 2 verified social media CSV")
    parser.add_argument("--gebco-path", type=Path, default=None, help="Path to GEBCO bathymetry NetCDF raster")
    parser.add_argument("--background-count", type=int, default=BACKGROUND_COUNT_PER_DOMAIN, help="KDE background points per domain")
    parser.add_argument("--background-seed", type=int, default=BACKGROUND_SEED, help="RNG seed for KDE background sampling")
    args = parser.parse_args()
    run_pipeline(
        from_raw=args.from_raw,
        social_media_csv=args.social_media_csv,
        gebco_path=args.gebco_path,
        background_count=args.background_count,
        background_seed=args.background_seed,
    )


if __name__ == "__main__":
    main()
