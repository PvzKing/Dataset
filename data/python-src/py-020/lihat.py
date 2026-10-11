import re
from pathlib import Path

html = Path("situs/index.html").read_text(encoding="utf-8")
for judul in re.findall(r"<h3>(.*?)</h3>", html):
    print("judul :", judul)
print("link  :", next(l for l in re.findall(r'href="([^"]+)"', html) if "Kopi" in l))
print("stok habis:", html.count("Stok habis"), "produk")
