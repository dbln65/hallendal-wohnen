# RAG-Prototyp – Agent-Assist für Hallendal Wohnen

Prototyp für Teilstudie A der Bachelorarbeit (DEMI, Abschnitt 1.3). Er erzeugt für jedes Ticket zwei Antwortentwürfe:

- **RAG:** Antwort aus Tickettext und abgerufenen KB-Passagen, mit Belegpflicht
- **LLM-only:** Antwort allein aus dem Tickettext

Grundlage sind die eingefrorene Knowledge Base (`kb/`, Tag `kb-v1.0`) und das Ticketset (`tickets.jsonl`, Tag `tickets-v1.0`). Beide werden hier nur gelesen. Alle Designentscheidungen mit Begründung stehen in [ENTSCHEIDUNGEN.md](ENTSCHEIDUNGEN.md).

## Architektur

```
EINMALIG: Indexierung (Schritt 1)
40 KB-Artikel ──► Chunking ──► Embeddings (OpenAI) ──► Qdrant

PRO TICKET, Bedingung RAG
Tickettext ──► Embedding ──► Qdrant: Top-5 ──► Cross-Encoder: Top-3
           ──► gpt-4.1-mini (Ticket + Passagen + Belegpflicht) ──► Entwurf mit [KB-xxx] ──► Protokoll

PRO TICKET, Bedingung LLM-only
Tickettext ──► gpt-4.1-mini (gleicher Prompt, ohne Passagen) ──► Entwurf ──► Protokoll
```

| Baustein | Aufgabe |
| --- | --- |
| Chunking | zerlegt Artikel in Textstücke fester Größe mit Überlappung |
| `text-embedding-3-small` | wandelt Text in einen Vektor um; ähnliche Bedeutung ergibt nahe Vektoren |
| Qdrant | speichert Vektoren, Text und Chunk-ID; liefert die ähnlichsten Chunks |
| Cross-Encoder `bge-reranker-v2-m3` | bewertet Ticket und Chunk gemeinsam und wählt aus den Top-5 die besten 3 |
| `gpt-4.1-mini` | schreibt den Antwortentwurf |

## Einrichtung

Voraussetzungen: Python 3.11 oder neuer, Docker, OpenAI-API-Key.

```bash
# im Repo-Hauptverzeichnis
python -m venv .venv && source .venv/bin/activate
pip install -r rag/requirements.txt
export OPENAI_API_KEY=sk-...        # nie ins Repo schreiben

# Qdrant starten
cd rag && docker compose up -d && cd ..
```

Beim ersten Aufruf lädt `tiktoken` einmalig die Tokenizer-Datei herunter. Ab Schritt 2 installiert `sentence-transformers` auch PyTorch, und der Cross-Encoder wird einmalig von Hugging Face geladen (rund 2 GB). Unter Linux genügt die CPU-Version von PyTorch: vor dem `pip install` einmal `pip install torch --index-url https://download.pytorch.org/whl/cpu` ausführen.

Den genauen Paketstand für den Anhang hältst du nach der Installation fest:

```bash
pip freeze > rag/requirements.lock.txt
```

## Schritt 1: Indexierung

```bash
python rag/chunking.py                  # Übersicht: Chunks und Tokens je Artikel (ohne API)
python rag/chunking.py --show KB-018    # Chunks eines Artikels im Wortlaut
python rag/index_kb.py --dry-run        # Anzahl Chunks und geschätzte Kosten
python rag/index_kb.py                  # Embeddings erzeugen und Qdrant befüllen
python rag/search.py --ticket P-04      # Vektorsuche für ein Pilotticket prüfen
```

`index_kb.py` legt die Collection bei jedem Lauf neu an. Damit entspricht der Index immer genau der aktuellen `config.yaml`.

`search.py` markiert mit ✓ Treffer aus Artikeln, die für das Ticket als relevant gelten (`belegartikel` und bestätigte `weitere_kandidaten`). Haupttickets sind nur mit `--erlaube-haupt` freigegeben (E-10).

## Schritt 2: Reranking und Retrieval-Test

```bash
python rag/search.py --ticket P-04 --rerank      # Vektorsuche, Cross-Encoder-Scores, ausgewählte Top-3
python rag/eval_retrieval.py                     # alle Pilottickets mit der aktuellen Konfiguration
python rag/eval_retrieval.py --varianten 150/30/ja 200/40/ja 300/60/ja 400/80/ja 200/40/nein 300/60/nein
```

`eval_retrieval.py` misst auf den KB-gedeckten Pilottickets:

- **Artikel-Treffer@k:** Anteil der Tickets mit mindestens einem relevanten Artikel unter den Top-k
- **Beleg-Abdeckung@k:** Anteil der Beleg-Zitate, die wörtlich in den Top-k-Passagen stehen

Beides jeweils für die Vektorsuche (Top-5, Top-3) und nach dem Reranking (Top-3). Mit `--varianten` wird jede Variante in einer temporären Collection indexiert und ausgewertet; die Haupt-Collection bleibt unverändert. Die Varianten und die Entscheidungsregel sind vorab in E-05 festgelegt. Jeder Lauf wird in `logs/retrieval_eval.jsonl` protokolliert.

Beim ersten Lauf zeigt das Skript die Revision des Cross-Encoders an. Sie wird in `config.yaml` als `reranker_revision` eingetragen (E-06).

## Schritt 3: Generierung

```bash
python rag/generate.py --set pilot --run-id pilot-01 --dry-run --ids P-04   # Prompts beider Bedingungen ansehen
python rag/generate.py --set pilot --run-id pilot-01                        # 10 Pilottickets × 2 Bedingungen
python rag/show_run.py pilot-01                                             # Übersicht und Auffälligkeiten
python rag/show_run.py pilot-01 --ticket P-04                               # beide Antworten im Wortlaut
```

Je Ticket laufen beide Bedingungen in zufälliger, per Seed festgelegter Reihenfolge. Vor dem ersten protokollierten Aufruf erfolgt ein Aufwärmaufruf. Ergebnis je Lauf in `runs/<run-id>/`:

| Datei | Inhalt |
| --- | --- |
| `run_meta.json` | Konfiguration, Config-, KB- und Prompt-Hash, Reranker-Revision, Git-Stand, Zeitraum, Summen |
| `responses.jsonl` | ein Eintrag je Ticket und Bedingung nach DEMI 2.2, inkl. Wortlaut der Passagen |
| `responses.csv` | dieselben Daten als Tabelle für den Anhang |
| `errors.jsonl` | fehlgeschlagene Aufrufe, falls vorhanden |

Prompts: `prompts/system.txt` (beide Bedingungen), `prompts/user_llm.txt`, `prompts/user_rag.txt`. Begründung in E-12 bis E-14.

## Schritt 4: Pilot und Einfrieren

```bash
python rag/generate.py --set pilot --run-id pilot-03                          # neuer Lauf nach jeder Prompt-Anpassung
python rag/show_run.py pilot-03 --alle > rag/runs/pilot-03/durchsicht.txt
git tag rag-v1.0 && git push origin rag-v1.0                                  # nach dem letzten Pilotlauf
```

Die Pilotläufe `pilot-01` bis `pilot-03` dienen nur der Abstimmung des Formats. Nach `pilot-01` und `pilot-02` wurden die Prompts angepasst, nur in der Form, nicht im Inhalt (E-12). Nach `pilot-03` wurde die Konfiguration eingefroren und als `rag-v1.0` getaggt (E-15). Die Pilotläufe gehen in keine Auswertung ein.

## Schritt 5: Hauptlauf

```bash
git status                                                       # muss sauber sein
python rag/generate.py --set haupt --run-id haupt-01 --erlaube-haupt
python rag/show_run.py haupt-01
python rag/show_run.py haupt-01 --alle > rag/runs/haupt-01/durchsicht.txt
```

`generate.py` bricht ab, wenn der Git-Stand nicht sauber ist oder der Index nicht zur Konfiguration passt.

## Stand

| Schritt | Inhalt | Status |
| --- | --- | --- |
| 1 | Indexierung | erledigt |
| 2 | Reranking und Retrieval-Test, Festlegung des Chunkings | erledigt (E-05, E-06) |
| 3 | Generierung | erledigt |
| 4 | Pilot P-01 bis P-10, Tag `rag-v1.0` | erledigt (E-15) |
| 5 | Hauptlauf: 120 Tickets × 2 Bedingungen | erledigt (`haupt-01`) |
| 6 | Online-Befragung vorbereiten | siehe [`../umfrage/README.md`](../umfrage/README.md) |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `config.yaml` | alle Parameter; ihr Hash steht in jedem Log-Eintrag |
| `ENTSCHEIDUNGEN.md` | Entscheidungsprotokoll mit Begründung und DEMI-Bezug |
| `docker-compose.yml` | Qdrant mit fester Version, nur lokal erreichbar |
| `common.py` | Pfade, Konfiguration, Hashes, Git-Stand, Kostenberechnung |
| `chunking.py` | Vorverarbeitung und Chunking |
| `index_kb.py` | Schritt 1: Indexierung |
| `search.py` | Kontrolle der Suche, mit `--rerank` inklusive Cross-Encoder |
| `retrieval.py` | Schritt 2: Vektorsuche und Reranking, wird auch von der Generierung genutzt |
| `eval_retrieval.py` | Schritt 2: Retrieval-Test und Variantenvergleich auf den Pilottickets |
| `generation.py` | Schritt 3: Prompt-Aufbau, Modellaufruf, Belege erkennen und entfernen |
| `generate.py` | Schritt 3: Lauf über ein Ticketset, Protokoll nach DEMI 2.2 |
| `show_run.py` | Durchsicht eines Laufs |
| `prompts/` | System-Prompt und Nachrichtenvorlagen beider Bedingungen |
| `runs/<run-id>/` | Ergebnisse je Lauf, dazu `durchsicht.txt` aus `show_run.py --alle` |
| `data/chunks.jsonl` | entsteht bei der Indexierung: alle Chunks im Wortlaut (Anhang der Arbeit) |
| `logs/index_log.jsonl` | entsteht bei der Indexierung: Zeitpunkt, Git-Commit, Config- und KB-Hash, Tokens, Kosten |
| `logs/retrieval_eval.jsonl` | entsteht beim Retrieval-Test: Kennzahlen je Variante und Ticket |
| `requirements.lock.txt` | von dir erzeugt: exakter Paketstand der Umgebung |

## Nachvollziehbarkeit

Jeder Log-Eintrag enthält:

- **Git-Commit** des Code-Stands und ob es nicht committete Änderungen gab (`dirty`). Läufe für die Auswertung erfolgen nur mit `dirty: false`.
- **`config_hash`**: welche Parameter galten.
- **`kb_hash`**: welche KB verwendet wurde. Der Wert muss mit `meta.kb_hash` der Tickets übereinstimmen.
- **Tokens und Kosten** nach der Preisliste zum Stichtag in `config.yaml`.
