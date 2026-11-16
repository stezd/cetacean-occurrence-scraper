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

## Writing rules (locked by the author)
- **Author writes all thesis prose.** The assistant does research (RAG), BibTeX, LaTeX formatting, and consistency checks. Do not draft Latar Belakang, Tujuan, Manfaat, or any other prose unless asked.
- **Scope:** two research questions only (RM1 KMM domain adaptation, RM2 expert-verified social media). RM2 is worded as "memperluas cakupan relung lingkungan dan menurunkan ketidakpastian ekstrapolasi (MESS)", not "meningkatkan akurasi". The seasonal RM3 is out of scope; seasons (NWM/TR1/SEM/TR2) are a method detail only. Do not promise seasonal results in Tujuan.
- **No novelty claims.** Do not write "belum ada penelitian" or "pertama kali". Frame gaps as "masih terbatas" with a cited source.
- **Ruang Lingkup (decided 2026-11-15):** list iNaturalist and Sharkbook as excluded or future work. Platforms (decided 2026-11-16, option 1): YouTube and online news only. Instagram, TikTok and X are out of scope because live scraping is blocked by repo rule (`social_media/platform_stubs.py`); option 2 (manual or official-API export) is kept as a comment in `chapter-1.tex`. An LLM may only pre-screen and extract fields; Pembimbing 2 verifies every row. Name the thin hotspots (Kaimana, Wakatobi, Jembrana, Kei) as a data limit.
- **Numbers** come only from a passing `../stages/*/output/check.md`. Stage 01 is `fail` until Pembimbing 2 supplies `social_media_verified.csv`; any count in the text is provisional until then.
- **Species status:** whale shark is IUCN **Endangered** (uplisted 2016). Some sources still say "Vulnerable" or "critically endangered"; do not copy them. Entry `Pierce2016` in the `.bib` is marked VERIFIKASI.
- **PPTA rules:** Tujuan uses measurable verbs, never "mengetahui" or "memahami"; one Tujuan per RM in the same order. The template section is "Ruang Lingkup" (the author's board calls it "Batasan masalah"). Sistematika Penulisan is not in the PPTA structure; ask the dosen. Scientific names in italics.
- **Bib keys:** `FirstAuthorFamilyNameYear` (for example `Sahri2021`). Metadata comes from `../literature/markdown/*/summary.md`. `Pacheco2021` and `Barthel2025` are missing until their metadata is complete. `src/backmatter/daftar-pustaka.tex` has a temporary `\nocite` list; delete it before the final manuscript.
- **Check after edits:** `./make.bat build` from PowerShell (not bash) exits `0`; also `biber --tool --validate-datamodel src/refs/daftar-pustaka.bib`.

## Outputs
- `main.pdf` (copied to `ipb-thesis-latex/main.pdf` and `output/` by `make.bat`)

## Check
`./make.bat build` exits `0`, produces `main.pdf` with zero undefined citations or LaTeX fatal errors, and every empirical table/figure matches the SHA-256-audited numbers in `stages/*/output/check.md`.
