# whale-scraper

Seasonal habitat suitability modeling pipeline for whale shark (*Rhincodon typus* / hiu paus, `taxonKey=2417522`) in Indonesian waters using Australian source-domain adaptation and expert-verified social-media sightings.

## Where things live

| Folder / File | What it holds |
|---|---|
| [CONTEXT.md](CONTEXT.md) | L1 pipeline overview: stages, factory vs product, completion rules |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Locked Phase 1 research specification, variables, models, and RQ1/RQ2 |
| `stages/` | Pipeline stages in execution order (`01_occurrences/`, then `02_predictors/`, `03_modeling/`) |
| `_shared/` | Factory rules and contracts ([occurrence-pipeline-spec.md](_shared/occurrence-pipeline-spec.md), [codebase-conventions.md](_shared/codebase-conventions.md)) |
| `literature/` | Converted reference papers ([literature/markdown/README.md](literature/markdown/README.md)); mounted in Obsidian as `Domains/` |
| `ipb-thesis-latex/` | PPTA IPB 2026 LaTeX thesis/proposal deliverable ([ipb-thesis-latex/CONTEXT.md](ipb-thesis-latex/CONTEXT.md)) |
| `_tools/` | Workspace utilities (`links.py` link/contract checker, `pdf_to_md.py` PDF converter) |
| `_archive/` | Superseded templates (`proposal-aldi/`, `inbox/`) and past presentation runs (`progress-bimbingan/`) |

## Route by what just happened

| If | Go to | Then stop at |
|---|---|---|
| starting or resuming the pipeline | [CONTEXT.md](CONTEXT.md) → [01_occurrences](stages/01_occurrences/CONTEXT.md) | the stage's `output/check.md` |
| modifying code or running the GBIF fetcher | [codebase-conventions.md](_shared/codebase-conventions.md) | `stages/01_occurrences/output/check.md` |
| checking research scope, predictors, or models | [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | the spec section needed |
| looking up a paper or citation | [literature/markdown/README.md](literature/markdown/README.md) | the paper's `summary.md` |
| drafting or compiling the IPB thesis/proposal (the author writes the prose; you research, format, cite) | [ipb-thesis-latex/CONTEXT.md](ipb-thesis-latex/CONTEXT.md) "Writing rules" | `ipb-thesis-latex/main.pdf` build check |
| asked for status or link health | scan `stages/*/output/check.md` and run `python -I _tools/links.py` | report what exists |

## Companion Obsidian vault (external)

Working notes live outside git at `C:\Users\Fjontoldesk\Documents\Obsidian Vault\Π Projects\whale-scraper\` (`Thoughts/Research Design.md`, `advise-notes/`, and `Domains/` which junctions into `literature/markdown/`).

## The one rule

Nothing moves to the next stage until the current stage's `output/check.md` passes.
