# Whale Scraper

Seasonal habitat suitability modeling pipeline for whale shark (*Rhincodon typus* / hiu paus, GBIF `taxonKey=2417522`) in Indonesian waters.

- **Agent router:** [AGENTS.md](AGENTS.md)
- **Pipeline overview:** [CONTEXT.md](CONTEXT.md)
- **Research specification (Phase 1 locked):** [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md)
- **Code & CLI conventions:** [_shared/codebase-conventions.md](_shared/codebase-conventions.md)
- **Occurrence cleaning spec:** [_shared/occurrence-pipeline-spec.md](_shared/occurrence-pipeline-spec.md)

## Quick Start

```bash
python -m venv .venv && .venv/Scripts/activate   # Windows; source .venv/bin/activate elsewhere
pip install -r requirements.txt

# Fetch GBIF occurrences
python fetch_gbif_cetaceans.py            # Indonesia (default), 1500 records
python fetch_gbif_cetaceans.py AU 5000    # Australia, 5000 records
python fetch_gbif_cetaceans.py PH 1000    # Philippines, 1000 records

# Check workspace links and stage contracts
python -I _tools/links.py
```

See [_shared/codebase-conventions.md](_shared/codebase-conventions.md) for the 16-column CSV contract, monsoon season tags (`NWM`, `TR1`, `SEM`, `TR2`), pagination behavior, and `.env` credentials.
