Ini masalah **urutan topologis**. Saya pakai algoritma Kahn: paket tanpa dependensi dipasang lebih dulu, lalu setiap paket yang semua dependensinya sudah terpasang menyusul. Beberapa hal yang perlu ditangani:

- **Paket yang hanya muncul sebagai dependensi**, seperti `util` di contohmu, tetap harus masuk urutan walaupun bukan kunci dict.
- **Hasil harus sama setiap kali dijalankan.** Paket yang siap disimpan di heap, jadi di antara paket yang sama-sama siap dipilih urutan alfabetis. Tanpa ini, urutan bisa berubah-ubah mengikuti urutan set.
- **Dependensi ganda** seperti `["a", "a"]` dihitung sekali.
- **Dependensi melingkar** terdeteksi kalau ada paket yang tidak pernah siap. Pesan "ada siklus" saja tidak membantu, jadi saya telusuri dependensi yang tersisa sampai kembali ke paket yang sudah dilewati, lalu tampilkan siklusnya. Paket yang hanya bergantung pada siklus (seperti `d` di contoh) tidak ikut ditampilkan sebagai bagian siklus.

```python
{{file urutan.py}}
```

```
{{run python urutan.py}}
```

Error dibuat sebagai kelas sendiri, turunan `ValueError`, dengan atribut `siklus`. Pemanggil bisa menangkapnya secara spesifik dan menampilkan siklusnya ke pengguna. Kompleksitasnya O((P + D) log P) untuk P paket dan D relasi dependensi.
