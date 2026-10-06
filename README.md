# LLM Instruct Dataset

Dataset instruksi untuk fine-tuning Large Language Model (LLM) dalam bahasa Indonesia.

## Format

JSONL (JSON Lines): setiap baris adalah satu contoh training.

```json
{
  "system": "System prompt / persona AI",
  "instruction": "Pertanyaan atau perintah dari user",
  "output": "Jawaban ideal dari AI",
  "category": "Kategori topik",
  "language": "Bahasa (id/en)"
}
```

## Statistik

| Metrik | Nilai |
|--------|-------|
| Total sampel | 42 |
| Bahasa | Indonesia |
| Format | JSONL |

## Kelompok Topik

| Kelompok | Sampel | Kategori (jumlah) |
|----------|--------|-------------------|
| Teknologi & pemrograman | 22 | algorithms (2), database (2), ai, coding, computer_science, creative_writing, critical_thinking, data_structures, design_patterns, devops, distributed_systems, machine_learning, networking, python, security, software_engineering, system_design, testing, version_control, web_development |
| Matematika | 10 | calculus (2), proof (2), probability (2), algebra, linear_algebra, number_theory, statistics |
| Sains | 10 | physics (5), biology (3), chemistry, earth_science |

## Topik Matematika & Sains

- **Kalkulus:** turunan, integral, Teorema Fundamental Kalkulus
- **Pembuktian:** irasionalitas √2, tak hingganya bilangan prima, induksi matematika
- **Probabilitas & statistik:** Monty Hall, Teorema Bayes, standar deviasi dan distribusi normal
- **Aljabar:** persamaan kuadrat dan diskriminan, eigenvalue/eigenvector
- **Fisika:** dilatasi waktu, Hukum Newton, entropi, hamburan Rayleigh, mekanika kuantum
- **Biologi:** fotosintesis, DNA dan dogma sentral, evolusi seleksi alam
- **Kimia:** tabel periodik dan ikatan kimia
- **Ilmu Bumi:** efek rumah kaca dan perubahan iklim

## Cara Pakai

```python
import json

with open("instruct_dataset.jsonl", encoding="utf-8") as f:
    dataset = [json.loads(line) for line in f]

# Contoh format prompt gaya Alpaca
for example in dataset:
    prompt = f"### System:\n{example['system']}\n\n### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}"
```
