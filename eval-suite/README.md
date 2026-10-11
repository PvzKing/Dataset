# eval-suite: papan skor v4

Alat ukur untuk gerbang penerimaan di [`docs/RENCANA_PYTHON.md`](../docs/RENCANA_PYTHON.md). Prosedur Colab-nya ada di [`docs/PROSEDUR_V4.md`](../docs/PROSEDUR_V4.md).

| File | Isi |
|---|---|
| `indopy_eval.py` | **IndoPy**: soal Python berbahasa Indonesia. Model menjawab bebas, lalu kode yang mendefinisikan fungsi yang diminta dijalankan bersama tes tersembunyi |
| `indopy/dev.jsonl` | 20 soal (6 mudah, 10 sedang, 4 sulit). Boleh dilihat untuk analisis kegagalan |
| `indopy/test.jsonl` | 40 soal (12 mudah, 20 sedang, 8 sulit). **Dikunci**: hanya untuk penilaian akhir, jangan dijadikan dasar menulis sampel |
| `indopy/cek_soal.py` | memeriksa setiap soal: solusi rujukan lolos, semua solusi salah (199 buah) ditolak, nama fungsi unik |
| `web_eval.py` | **Web-eval**: 10 prompt website baru. Website dibuka di Chromium tanpa jaringan, lalu diperiksa: dokumen lengkap, tanpa error JavaScript, tidak ada scroll horizontal di 375 px, dan fitur utama bekerja |
| `web/referensi/` | 10 website rujukan, satu per prompt, ditulis terpisah dari pemeriksaannya |
| `web/uji_pemeriksa.py` | menguji pemeriksaan dari dua arah: website rujukan harus lolos, dan versi yang dirusak dengan satu bug harus ditolak |
| `papan_skor.py` | membaca semua folder hasil dan mencetak status gerbang G1–G3 |

HumanEval+ dan MBPP+ dijalankan dengan `humaneval-bench-script/eval_humaneval.py` (`--dataset mbpp` untuk MBPP+).

## Aturan

- **Jangan melatih model dengan isi folder ini.** Soal IndoPy, prompt Web-eval, dan website rujukan adalah data uji. `scripts/decontaminate.py` memeriksa tumpang tindih 13-gram antara data latihan dan soal uji.
- **Soal uji ditulis terpisah dari penulis sampel latihan**, supaya data latihan tidak tanpa sadar disesuaikan dengan soal.
- **Setelah mengubah soal atau pemeriksaan**, jalankan:
  ```bash
  python eval-suite/indopy/cek_soal.py
  python eval-suite/web/uji_pemeriksa.py      # butuh: pip install playwright && playwright install chromium
  python scripts/decontaminate.py
  ```

## Mencoba alurnya tanpa GPU

Mode `--demo` memakai solusi rujukan dan solusi salah sebagai pengganti jawaban model. Tujuannya menguji alur dari generate sampai papan skor:

```bash
python eval-suite/indopy_eval.py --demo --split dev --results /tmp/uji/eval-indopy-dev
python eval-suite/web_eval.py --demo --results /tmp/uji/eval-web
python eval-suite/papan_skor.py --tag demo --pembanding demo-model-dasar --root /tmp/uji
```

## Catatan penilaian

- **Ekstraksi kode IndoPy** mengambil blok kode terakhir yang mendefinisikan fungsi yang diminta. Kode demo di tingkat atas dibuang: blok `__main__`, `print`, loop, dan `assert`. Import, konstanta, fungsi pembantu, dan kelas dipertahankan. `evalplus.sanitize` sengaja tidak dipakai, karena ia bisa membuang fungsi pembantu yang sebenarnya dipanggil.
- **Web-eval longgar soal cara membangun UI tapi ketat soal hasil.** Misalnya pilihan satuan suhu harus berupa `<select>`, tetapi angkanya boleh tampil di teks, `<input>`, atau `<output>`. Jam dunia harus benar walaupun komputer penguji memakai UTC.
- **10 website terlalu sedikit untuk uji statistik**, jadi G3 dinilai dari jumlah website yang lolos.
- **Soal bertema hukum, pajak, dan ketenagakerjaan sudah diaudit**, karena aturan yang disebut sebagai hukum harus benar. Soal yang ikut diaudit antara lain upah lembur, zakat, PPN, PPh 21, THR, BPJS Kesehatan, pelat nomor, dan tarif PDAM.
  - Aturan yang disederhanakan atau rekaan diberi keterangan di prompt-nya, misalnya bahwa tarif PDAM ditetapkan kepala daerah, bahwa THR yang dihitung adalah besaran minimum menurut Permenaker 6/2016, dan bahwa makanan di restoran dikenai PBJT, bukan PPN.
  - Prompt dan tesnya diperiksa ulang setiap kali soal diubah.
