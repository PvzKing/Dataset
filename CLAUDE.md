# Catatan untuk Claude

Repo ini berisi dataset instruct berbahasa Indonesia dan perangkat fine-tuning. Lihat README untuk detailnya.

- **Berjalan di Google Colab:** notebook menyalin `docs/RUNBOOK_CLAUDE.md` ke `/content/CLAUDE.md`. Ikuti runbook itu saat diminta melatih atau memantau training.
- **Mengubah `scripts/train_unsloth.py` atau `docs/RUNBOOK_CLAUDE.md`:** jalankan `python scripts/build_notebook.py` supaya notebook ikut diperbarui.
- **Mengubah `data/train.jsonl`:** jalankan `python scripts/validate.py`.
- **Mengubah website di `examples/web/`:** jalankan juga tes browser di `tests/`.
