Saya guru dan bikin script Python untuk rekap nilai rapor. Aturan sekolah: nilai akhir dibulatkan ke bilangan bulat, ,5 dibulatkan ke atas, KKM 75. Tapi ada siswa yang nilainya 74,5 malah tidak tuntas, padahal harusnya jadi 75. Ini kodenya:

```python
{{file bug/rapor.py}}
```

Hasilnya:

```
{{output python rapor.py}}
```

Ayu harusnya 75 (0,3×80 + 0,3×75 + 0,4×70 = 74,5) dan Bima harusnya 85.
