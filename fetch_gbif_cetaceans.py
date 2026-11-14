"""
GBIF Occurrence Fetcher for Indonesia, Australia, and Philippines.
Defaults to legacy Stage 0 Cetacea (taxonKey=733), and supports Rhincodon typus (taxonKey=2417522)
via --taxon-key, --year, and --output flags.
"""

import argparse
import csv
import json
import os
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# Taxon Keys
# 733: Order Cetacea (whales, dolphins, porpoises)
# 2417522: Rhincodon typus (Whale Shark / Hiu Paus)
# 2440618: Megaptera novaeangliae (Humpback Whale)
# 2440470: Physeter macrocephalus (Sperm Whale)

BASE_URL = "https://api.gbif.org/v1/occurrence/search"
MAX_GBIF_LIMIT = 300
MAX_GBIF_OFFSET = 100000
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

def determine_season(month):
    """
    Monsoon seasons in Indonesian waters:
    - NWM: Northwest Monsoon (December - February)
    - TR1: Transition 1 (March - May)
    - SEM: Southeast Monsoon (June - August)
    - TR2: Transition 2 (September - November)
    """
    if month in (12, 1, 2):
        return "NWM"
    elif month in (3, 4, 5):
        return "TR1"
    elif month in (6, 7, 8):
        return "SEM"
    elif month in (9, 10, 11):
        return "TR2"
    return "UNKNOWN"

def _fetch_json_with_retry(url, headers, max_retries=4, base_delay=1.5, timeout=30):
    last_error = None
    for attempt in range(max_retries + 1):
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            last_error = e
            if e.code not in RETRYABLE_STATUS_CODES or attempt == max_retries:
                raise RuntimeError(f"GBIF HTTP {e.code} for {url}: {e}") from e
            retry_after = e.headers.get("Retry-After") if e.headers else None
            delay = float(retry_after) if retry_after and retry_after.isdigit() else base_delay * (2 ** attempt)
        except URLError as e:
            last_error = e
            if attempt == max_retries:
                raise RuntimeError(f"GBIF network error for {url}: {e}") from e
            delay = base_delay * (2 ** attempt)
        print(f"[!] Transient error ({last_error}); retrying in {delay:.1f}s...")
        time.sleep(delay)
    raise RuntimeError(f"GBIF request failed for {url}: {last_error}")


def fetch_occurrences(country="ID", taxon_key=733, max_records=1000, year=None, page_limit=MAX_GBIF_LIMIT):
    print(f"[*] Querying GBIF for Country: {country}, Taxon: {taxon_key}, Year: {year or 'all'} (hasCoordinate=true)...")
    records = []
    offset = 0
    limit = min(int(page_limit), MAX_GBIF_LIMIT)
    headers = {"User-Agent": "WhaleScraperResearch/1.0 (rhincodon-typus-sdm)"}

    while len(records) < max_records:
        if offset + limit > MAX_GBIF_OFFSET:
            print(f"[!] Stopping before GBIF hard offset+limit ceiling ({MAX_GBIF_OFFSET}).")
            break
        remaining = max_records - len(records)
        page_size = min(limit, remaining)
        params = {
            "country": country,
            "taxonKey": taxon_key,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": page_size,
            "offset": offset,
        }
        if year:
            params["year"] = year
        url = f"{BASE_URL}?{urlencode(params)}"
        data = _fetch_json_with_retry(url, headers=headers)

        results = data.get("results", [])
        if not results:
            break

        for item in results:
            month = item.get("month")
            season = determine_season(month) if month else "UNKNOWN"
            records.append({
                "gbif_id": item.get("gbifID"),
                "scientific_name": item.get("scientificName"),
                "species": item.get("species"),
                "family": item.get("family"),
                "country": item.get("countryCode"),
                "latitude": item.get("decimalLatitude"),
                "longitude": item.get("decimalLongitude"),
                "coordinate_uncertainty_m": item.get("coordinateUncertaintyInMeters"),
                "year": item.get("year"),
                "month": month,
                "season": season,
                "event_date": item.get("eventDate"),
                "locality": item.get("verbatimLocality"),
                "basis_of_record": item.get("basisOfRecord"),
                "dataset_name": item.get("datasetName"),
                "occurrence_url": item.get("occurrenceID") or item.get("references"),
            })

        print(f"    Fetched {len(records)} / {data.get('count', '?')} total records...")
        if data.get("endOfRecords", False):
            break

        offset += len(results)
        time.sleep(0.2)  # courteous API rate limit

    return records

def save_to_csv(records, filename):
    if not records:
        print(f"[!] No records to save for {filename}")
        return

    os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
    fieldnames = list(records[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"[+] Saved {len(records)} records to {filename}")


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Fetch GBIF occurrences for whale-scraper.")
    parser.add_argument("country_code", nargs="?", default="ID", help="ISO2 country code (default: ID)")
    parser.add_argument("max_records", nargs="?", type=int, default=1500, help="Max records to fetch (default: 1500)")
    parser.add_argument("--taxon-key", type=int, default=733, help="GBIF taxonKey (default: 733; Rhincodon typus: 2417522)")
    parser.add_argument("--year", default=None, help="Year or year range, e.g. 2010,2026")
    parser.add_argument("--limit", type=int, default=MAX_GBIF_LIMIT, help="Page size up to 300 (default: 300)")
    parser.add_argument("--output", default=None, help="Output CSV path")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    if args.output:
        output_file = args.output
    elif args.taxon_key == 733:
        output_file = f"data/cetaceans_{args.country_code.lower()}.csv"
    else:
        output_file = f"data/gbif_{args.taxon_key}_{args.country_code.lower()}.csv"

    data = fetch_occurrences(
        country=args.country_code,
        taxon_key=args.taxon_key,
        max_records=args.max_records,
        year=args.year,
        page_limit=args.limit,
    )
    save_to_csv(data, output_file)
