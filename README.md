# LLM Instruct Dataset 🔥

Dataset instruksi berkualitas tinggi untuk fine-tuning Large Language Model (LLM) dalam bahasa Indonesia.

## Format

JSONL (JSON Lines) — setiap baris adalah satu contoh training.

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
| Total sampel | 20 |
| Bahasa | Indonesia |
| Format | JSONL |

## Kategori

| Kategori | Jumlah |
|----------|--------|
| computer_science | 1 |
| coding | 1 |
| database | 2 |
| machine_learning | 1 |
| software_engineering | 1 |
| devops | 1 |
| web_development | 1 |
| security | 1 |
| version_control | 1 |
| testing | 1 |
| data_structures | 1 |
| design_patterns | 1 |
| algorithms | 2 |
| python | 1 |
| system_design | 1 |
| distributed_systems | 1 |
| creative_writing | 1 |
| critical_thinking | 1 |
| ai | 1 |
| networking | 1 |

## Cara Pakai

```python
import json

with open("instruct_dataset.jsonl") as f:
    dataset = [json.loads(line) for line in f]

# Format untuk fine-tuning (contoh dengan Alpaca format)
for example in dataset:
    prompt = f"### System:\n{example['system']}\n\n### Instruction:\n{example['instruction']}\n\n### Response:\n{example['output']}"
```

## Topik yang Dicakup

- **Algoritma & Struktur Data** — time complexity, recursion, linked list, sorting
- **Software Engineering** — SOLID, design patterns, testing, clean code
- **Database** — SQL JOIN, indexing, normalization
- **DevOps** — Docker, CI/CD, infrastructure
- **Security** — authentication, HTTPS/TLS, OWASP
- **Distributed Systems** — CAP theorem, microservices, consistency
- **AI/ML** — neural network, prompt engineering
- **Python** — async/await, best practices
- **Creative Writing** — puisi, cerita
- **Critical Thinking** — problem solving, framework berpikir
