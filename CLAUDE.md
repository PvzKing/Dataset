# Catatan untuk Claude

Repo ini berisi dataset instruct berbahasa Indonesia dan perangkat fine-tuning. Lihat README untuk detailnya.

- **Berjalan di Google Colab:** notebook menyalin `docs/RUNBOOK_CLAUDE.md` ke `/content/CLAUDE.md`. Ikuti runbook itu saat diminta melatih atau memantau training.
- **Mengubah `scripts/train_unsloth.py` atau `docs/RUNBOOK_CLAUDE.md`:** jalankan `python scripts/build_notebook.py` supaya notebook ikut diperbarui.
- **Mengubah `data/train.jsonl`:** jalankan `python scripts/validate.py`.
- **Mengubah sampel Python:** edit sumbernya di `data/python-src/<id>/`, bukan `train.jsonl`, lalu jalankan `python scripts/build_python_samples.py` dan `python scripts/decontaminate.py`.
- **Mengubah `eval-suite/`:** jalankan `python eval-suite/indopy/cek_soal.py` dan `python eval-suite/web/uji_pemeriksa.py`. Isi `eval-suite/` adalah data uji: jangan dijadikan sampel latihan.
- **Mengubah website di `examples/web/`:** jalankan juga tes browser di `tests/`.
