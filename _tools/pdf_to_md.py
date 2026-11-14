"""Convert each PDF in a folder to Markdown with extracted figures.

Usage: python -I _tools/pdf_to_md.py <pdf_dir> <out_dir> [stem ...]

Writes <out_dir>/<stem>/<stem>.md and <out_dir>/<stem>/images/*.png.
Image links in the Markdown are rewritten to be relative to the .md file.
"""

import re
import sys
from pathlib import Path

import pymupdf4llm


def convert(pdf: Path, out_root: Path) -> None:
    out_dir = out_root / pdf.stem
    img_dir = out_dir / "images"
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
    (out_dir / f"{pdf.stem}.md").write_text(md, encoding="utf-8")
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
