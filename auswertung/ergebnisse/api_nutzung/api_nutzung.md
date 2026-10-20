# Protokollierte API-Nutzung

Tag in UTC. Input = Eingabetokens ohne Cache-Treffer (bei Anthropic einschließlich Cache-Schreibvorgängen), Cache = Cache-Treffer; Input + Cache ergibt alle Eingabetokens. Kosten nur für OpenAI (Preisliste zum Stichtag); für Anthropic über die Tokenzahlen abgleichen.

## OpenAI

| Tag | Zweck | Modell | Aufrufe | Input | Cache | Output | Kosten (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-10 | Indexierung der KB | text-embedding-3-small | 3 | 46.024 | 0 | 0 | 0,0009 |
| 2026-10-10 | Lauf haupt-01: Embedding der Anfrage | text-embedding-3-small | 120 | 8.814 | 0 | 0 | 0,0002 |
| 2026-10-10 | Lauf haupt-01: Generierung | gpt-4.1-mini-2025-04-14 | 240 | 176.524 | 1.024 | 36.128 | 0,1285 |
| 2026-10-10 | Lauf pilot-01: Embedding der Anfrage | text-embedding-3-small | 10 | 695 | 0 | 0 | 0,0000 |
| 2026-10-10 | Lauf pilot-01: Generierung | gpt-4.1-mini-2025-04-14 | 20 | 12.860 | 0 | 3.081 | 0,0101 |
| 2026-10-10 | Lauf pilot-02: Embedding der Anfrage | text-embedding-3-small | 10 | 695 | 0 | 0 | 0,0000 |
| 2026-10-10 | Lauf pilot-02: Generierung | gpt-4.1-mini-2025-04-14 | 20 | 14.210 | 0 | 3.031 | 0,0105 |
| 2026-10-10 | Lauf pilot-03: Embedding der Anfrage | text-embedding-3-small | 10 | 695 | 0 | 0 | 0,0000 |
| 2026-10-10 | Lauf pilot-03: Generierung | gpt-4.1-mini-2025-04-14 | 20 | 13.436 | 1.024 | 2.944 | 0,0102 |
| **gesamt** | | | 453 | 273.953 | 2.048 | 45.184 | **0,1604** |

## Anthropic

| Tag | Zweck | Modell | Aufrufe | Input | Cache | Output | Kosten (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-28 | KB-Artikel erzeugen | claude-sonnet-5 | 43 | 45.382 | 208.198 | 31.196 | – |
| 2026-10-06 | Tickets erzeugen | claude-sonnet-5 | 134 | 288.768 | 3.928.716 | 122.673 | – |
| 2026-10-06 | Tickets erzeugen (Fehler, ohne Tokens) | claude-sonnet-5 | 8 | 0 | 0 | 0 | – |
| **gesamt** | | | 185 | 334.150 | 4.136.914 | 153.869 | – |

## Nicht protokolliert

- je ein Aufwärmaufruf (Embedding und Generierung) vor jedem Lauf von `rag/generate.py`
- Probeaufrufe mit `--dry-run` und API-Schlüssel (nur Embeddings)
- Embeddings der Tickets beim Retrieval-Vergleich (`rag/eval_retrieval.py`)
- Aufrufe außerhalb der Skripte (z. B. Tests in der Konsole oder Workbench)
