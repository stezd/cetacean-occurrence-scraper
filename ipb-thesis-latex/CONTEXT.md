# ipb-thesis-latex - compile PPTA IPB 2026 manuscript

One job: maintain and compile the IPB University undergraduate proposal and thesis manuscript (`main.pdf`) following PPTA IPB Edisi Ke-5 (2026).

## Inputs
- Working (this run): `../stages/01_occurrences/output/check.md`
- Reference (every run): `../PROJECT_OVERVIEW.md`
- Reference (every run): `src/config/information.tex`
- Reference (every run): `src/main.tex`
- Reference (every run): `src/refs/daftar-pustaka.bib`

Do NOT load: `../_archive/`, `src/config/ipb-thesis.sty` (unless debugging macro layout), or `build/` logs unless compilation fails.

## Process
1. Edit metadata in `src/config/information.tex`, chapter prose in `src/chapters/chapter-*.tex`, and BibTeX entries in `src/refs/daftar-pustaka.bib`.
2. Cite real numbers and figures only from verified pipeline outputs (`stages/*/output/`) and literature summaries in [literature/markdown/README.md](../literature/markdown/README.md).
3. Build from `ipb-thesis-latex/` using `./make.bat build` (Windows) or `make build` (LuaLaTeX + Biber).

## Outputs
- `main.pdf` (copied to `ipb-thesis-latex/main.pdf` and `output/` by `make.bat`)

## Check
`./make.bat build` exits `0`, produces `main.pdf` with zero undefined citations or LaTeX fatal errors, and every empirical table/figure matches the SHA-256-audited numbers in `stages/*/output/check.md`.
