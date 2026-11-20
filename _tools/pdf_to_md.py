"""Convert each PDF in a folder to Markdown with extracted figures.

Usage: python -I _tools/pdf_to_md.py <pdf_dir> <out_dir> [stem ...]

Writes <out_dir>/<stem>/<stem>.md and <out_dir>/<stem>/images/*.png.
Image links in the Markdown are rewritten to be relative to the .md file.
"""

import re
import shutil
import sys
from pathlib import Path

import pymupdf4llm


def convert(pdf: Path, out_root: Path) -> None:
    out_dir = out_root / pdf.stem
    # pymupdf4llm rewrites spaces and parentheses in the image path, so a
    # name like "Author (2023) - Title" fails. Work in an ASCII-safe folder,
    # then rename it to the real stem when the conversion ends.
    safe = re.sub(r"[^A-Za-z0-9]+", "_", pdf.stem).strip("_")
    work_dir = out_root / f"_work_{safe}"
    img_dir = work_dir / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    md = pymupdf4llm.to_markdown(
        str(pdf),
        write_images=True,
        image_path=str(img_dir),
        image_format="png",
        dpi=200,
        page_separators=True,
    )

    # Rewrite absolute/backslashed image paths to images/<name>.
    def fix(m):
        name = Path(m.group(2).replace("\\", "/")).name
        return f"{m.group(1)}(images/{name})"

    md = re.sub(r"(!\[[^\]]*\])\(([^)]+)\)", fix, md)
    (work_dir / f"{pdf.stem}.md").write_text(md, encoding="utf-8")
    if out_dir.exists():
        shutil.rmtree(out_dir)
    work_dir.rename(out_dir)
    img_dir = out_dir / "images"
    n_links = len(re.findall(r"!\[[^\]]*\]\(images/", md))
    n_files = len(list(img_dir.glob("*.png")))
    print(f"{pdf.name}: {len(md)} chars, {n_links} image links, {n_files} image files")


def main() -> None:
    pdf_dir, out_root = Path(sys.argv[1]), Path(sys.argv[2])
    stems = set(sys.argv[3:])
    for pdf in sorted(pdf_dir.glob("*.pdf")):
        if stems and pdf.stem not in stems:
            continue
        convert(pdf, out_root)


if __name__ == "__main__":
    main()
