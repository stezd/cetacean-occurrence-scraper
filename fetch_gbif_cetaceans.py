"""
GBIF Cetacean Occurrence Fetcher for Indonesia, Australia, and Philippines.
Pulls verified occurrence data with coordinates, date, season, and metadata.
"""

import csv
import json
import os
import sys
import time
from urllib.request import urlopen, Request
from urllib.parse import urlencode

# Taxon Keys
# 733: Order Cetacea (whales, dolphins, porpoises)
# 2440618: Megaptera novaeangliae (Humpback Whale)
# 2440470: Physeter macrocephalus (Sperm Whale)

BASE_URL = "https://api.gbif.org/v1/occurrence/search"

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

def fetch_occurrences(country="ID", taxon_key=733, max_records=1000):
    print(f"[*] Querying GBIF for Country: {country}, Taxon: {taxon_key} (hasCoordinate=true)...")
    records = []
    offset = 0
    limit = 100

    while offset < max_records:
        params = {
            "country": country,
            "taxonKey": taxon_key,
            "hasCoordinate": "true",
            "hasGeospatialIssue": "false",
            "limit": limit,
            "offset": offset,
        }
        url = f"{BASE_URL}?{urlencode(params)}"
        req = Request(url, headers={"User-Agent": "ThesisResearcher/1.0 (cetacean-habitat-modeling)"})
        
        try:
            with urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"[!] Error fetching page at offset {offset}: {e}")
            break

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

        offset += limit
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

if __name__ == "__main__":
    country_code = sys.argv[1] if len(sys.argv) > 1 else "ID"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1500
    
    output_file = f"data/cetaceans_{country_code.lower()}.csv"
    data = fetch_occurrences(country=country_code, max_records=limit)
    save_to_csv(data, output_file)
