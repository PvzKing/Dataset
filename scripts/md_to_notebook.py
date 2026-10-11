"""Ubah panduan Markdown menjadi notebook Colab, supaya panduan dan notebook selalu sama isinya.

Aturan:
  - blok ```python (tanpa indentasi) menjadi sel kode;
  - teks lain menjadi sel Markdown, dipecah di setiap judul ## dan ###;
  - teks di antara <!-- hanya-md --> dan <!-- /hanya-md --> tidak ikut ke notebook.

Pemakaian:
    python scripts/md_to_notebook.py                     # docs/PROSEDUR_V4.md -> notebooks/v4_pilot_colab.ipynb
    python scripts/md_to_notebook.py PANDUAN.md OUT.ipynb
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BAWAAN = (ROOT / "docs" / "PROSEDUR_V4.md", ROOT / "notebooks" / "v4_pilot_colab.ipynb")


def sel(jenis, baris):
    teks = "\n".join(baris).strip("\n")
    if not teks.strip() or teks.strip() == "---":  # garis pemisah saja tidak perlu jadi sel sendiri
        return None
    sumber = [b + "\n" for b in teks.split("\n")]
    sumber[-1] = sumber[-1].rstrip("\n")
    if jenis == "code":
        return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": sumber}
    return {"cell_type": "markdown", "metadata": {}, "source": sumber}


def ubah(teks):
    teks = re.sub(r"<!-- hanya-md -->.*?<!-- /hanya-md -->\n?", "", teks, flags=re.S)
    cells, md, kode, dalam_kode, dalam_pagar = [], [], [], False, False
    for b in teks.splitlines():
        if dalam_kode:
            if b == "```":
                cells.append(sel("code", kode))
                kode, dalam_kode = [], False
            else:
                kode.append(b)
            continue
        if b == "```python" and not dalam_pagar:
            cells.append(sel("markdown", md))
            md, dalam_kode = [], True
            continue
        if b.lstrip().startswith("```"):
            dalam_pagar = not dalam_pagar  # blok kode lain (contoh output) tetap di Markdown
        if not dalam_pagar and re.match(r"#{2,3} ", b) and any(x.strip() for x in md):
            cells.append(sel("markdown", md))
            md = []
        md.append(b)
    if dalam_kode:
        raise ValueError("blok ```python tidak ditutup")
    cells.append(sel("markdown", md))
    return {
        "cells": [c for c in cells if c],
        "metadata": {"accelerator": "GPU", "colab": {"gpuType": "T4", "provenance": []},
                     "kernelspec": {"display_name": "Python 3", "name": "python3"},
                     "language_info": {"name": "python"}},
        "nbformat": 4, "nbformat_minor": 0,
    }


def main():
    src, out = (Path(sys.argv[1]), Path(sys.argv[2])) if len(sys.argv) == 3 else BAWAAN
    nb = ubah(src.read_text(encoding="utf-8"))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    kode = sum(c["cell_type"] == "code" for c in nb["cells"])
    print(f"ditulis {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}: "
          f"{len(nb['cells'])} sel ({kode} sel kode)")


if __name__ == "__main__":
    main()
