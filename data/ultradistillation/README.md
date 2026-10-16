# Kelompok ultradistillation

Jawaban dari AI lain untuk pertanyaan di `pertanyaan.jsonl`. Jawabannya dikirim pemilik repo, diperiksa otomatis, lalu dibangun menjadi `ultradistillation.jsonl` dengan format yang sama dengan `data/train.jsonl`. Kelompok ini **terpisah** dan tidak otomatis ikut training.

| Berkas | Isi |
|---|---|
| `pertanyaan.jsonl` | pertanyaan: `id`, `kategori`, `prompt`; soal Python juga punya `entry` dan `tes` tersembunyi, soal website punya `simpan` |
| `instruksi-awal.md` | format jawaban yang diminta ke AI. Ditempel saat menyalin, tetapi tidak disimpan di dataset |
| `SALIN.md` | pertanyaan yang belum dijawab, sudah digabung dengan instruksi awal (dibuat oleh `salin`) |
| `jawaban/<id>.md` | jawaban apa adanya, dengan `sumber`, `tanggal`, dan untuk hukum `diperiksa` di bagian depan berkas |
| `ultradistillation.jsonl` | hasil `bangun`: hanya jawaban yang lolos pemeriksaan |

```bash
python scripts/ultradistillation.py salin                 # tulis SALIN.md
python scripts/ultradistillation.py simpan ud-001 --sumber "Nama AI versi X" < jawaban.md
python scripts/ultradistillation.py periksa ud-012         # jawaban hukum sudah diperiksa pemilik
python scripts/ultradistillation.py bangun                 # cek semua jawaban lalu tulis ultradistillation.jsonl
```

## Pemeriksaan

| Kategori | Lolos jika |
|---|---|
| `python`, `python_debug` | kode di blok ```python lulus tes tersembunyi di `pertanyaan.jsonl`, dengan pengambil kode yang sama dengan IndoPy |
| `web` | lolos pemeriksaan Chromium yang sama dengan sulingan V7: tanpa error saat dibuka dan dipakai, halaman berubah setelah tombol diklik, responsif di 375 px, localStorage jika diminta, dan ada **Cek kebutuhan** |
| `hukum` | pemilik sudah memeriksa pasal, ayat, dan nomor peraturannya, lalu menandainya dengan `periksa`. Ini tidak bisa diperiksa otomatis, dan AI sering salah menyebut nomor pasal |
| semua | sumber tercatat, tanpa tag `<think>`, tanpa basa-basi "sebagai AI", dan tidak punya 13-gram yang sama dengan IndoPy, Web-eval, HumanEval+, atau MBPP+ |

Pertanyaan baru tidak boleh sama tugasnya dengan soal Web-eval, IndoPy, prompt uji `train_unsloth.py` (bengkel, absensi), prompt uji antrean puskesmas, atau prompt sulingan V7.

## Sumber jawaban dan syarat layanan

Baca bagian ini sebelum mengisi jawaban. Hak cipta atas jawaban AI di Indonesia belum jelas, tetapi **syarat layanan** penyedia AI mengikat sebagai perjanjian (Pasal 1338 KUHPerdata), dan melanggarnya adalah wanprestasi (Pasal 1238 dan 1243). Beberapa penyedia besar melarang outputnya dipakai untuk melatih model:

| Sumber | Status (periksa lagi versi terbaru syaratnya) |
|---|---|
| ChatGPT / API OpenAI | Terms of Use melarang memakai output untuk mengembangkan model yang bersaing dengan OpenAI |
| Claude / API Anthropic | Ketentuan Anthropic melarang memakai layanan atau outputnya untuk mengembangkan atau melatih model AI, termasuk produk pesaing |
| Gemini / Google AI Studio | Syarat Gemini API melarang memakai layanan untuk mengembangkan model yang bersaing |
| Model bobot terbuka yang lisensinya mengizinkan (misalnya keluarga Qwen dengan Apache 2.0, DeepSeek dengan lisensi MIT), dijalankan sendiri | lisensi bobot mengatur, dan umumnya tidak membatasi pemakaian output. Situs chat resmi penyedianya punya syarat layanan sendiri yang tetap harus dibaca |
| Ditulis atau disunting sendiri oleh pemilik repo | paling aman |

Karena itu setiap jawaban **wajib** mencatat `sumber`, supaya sampel dari sumber tertentu bisa dibuang belakangan jika ternyata tidak boleh dipakai. Jangan mendistribusikan `ultradistillation.jsonl` atau model yang dilatih dengannya sebelum status sumbernya jelas.

Data pribadi: semua pertanyaan memakai data fiktif. Jangan mengganti contoh dengan data klien atau perkara sungguhan (UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi, dan kewajiban kerahasiaan advokat menurut Pasal 19 UU No. 18 Tahun 2003 tentang Advokat).
