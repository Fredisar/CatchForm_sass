"""Rend les pages d'un PDF en planches PNG (plusieurs pages par image) pour relecture visuelle.

Usage : python rendre_pdf.py fichier.pdf [pages_par_planche] [zoom]
"""
import pathlib
import sys

import pymupdf

pdf_path = pathlib.Path(sys.argv[1])
per_sheet = int(sys.argv[2]) if len(sys.argv) > 2 else 4
zoom = float(sys.argv[3]) if len(sys.argv) > 3 else 0.8

out_dir = pdf_path.parent / "apercu_pages"
out_dir.mkdir(exist_ok=True)
for old in out_dir.glob("*.png"):
    old.unlink()

doc = pymupdf.open(pdf_path)
pixmaps = [page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)) for page in doc]
width, height = pixmaps[0].width, pixmaps[0].height
gap = 12

for start in range(0, len(pixmaps), per_sheet):
    group = pixmaps[start:start + per_sheet]
    sheet = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, per_sheet * width + (per_sheet - 1) * gap, height), False)
    sheet.clear_with(200)
    for i, pix in enumerate(group):
        pix.set_origin(i * (width + gap), 0)
        sheet.copy(pix, pix.irect)
    name = out_dir / f"pages_{start + 1:02d}-{start + len(group):02d}.png"
    sheet.save(name)
    print(name)
print(f"{len(pixmaps)} pages")
