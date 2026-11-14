# whale-scraper - the pipeline

The flow in one line: fetch and verify whale shark occurrences (`ID` + `AU`), pair them with seasonal CMEMS/GEBCO rasters (`1/12°`), train KMM domain-adapted SDMs (MaxEnt, XGBoost, RF), and compile the IPB thesis manuscript.

| Stage | Folder | Job | Status |
|---|---|---|---|
| `01_occurrences` | [stages/01_occurrences/CONTEXT.md](stages/01_occurrences/CONTEXT.md) | Fetch, verify, clean, and 10 km thin occurrences | Active (Stage 0 `data/cetaceans_id.csv` complete; `taxonKey=2417522` run next) |
| `02_predictors` | *(created when Stage 01 passes)* | Extract seasonal CMEMS & GEBCO rasters (`1/12°`, VIF ≤ 5) | Planned |
| `03_modeling` | *(created when Stage 02 passes)* | Train MaxEnt/XGBoost/RF with KMM (`AU` → `ID`) & Spatial Block CV | Planned |
| Deliverable | [ipb-thesis-latex/CONTEXT.md](ipb-thesis-latex/CONTEXT.md) | Compile PPTA IPB 2026 proposal/thesis PDF | Template ready (`main.pdf` builds cleanly) |

Each implemented stage's own `CONTEXT.md` holds its inputs, process, outputs, and check.

- **Factory (stable, every run):** [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md), [_shared/occurrence-pipeline-spec.md](_shared/occurrence-pipeline-spec.md), [_shared/codebase-conventions.md](_shared/codebase-conventions.md), [literature/markdown/README.md](literature/markdown/README.md)
- **Product (new each run):** each stage's `output/` directory and `ipb-thesis-latex/main.pdf`

Status is whatever exists on disk: a stage is complete when its `output/` holds the target artifacts and `output/check.md` starts with `pass`. A `.gitkeep` placeholder does not count.
