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

Beim ersten Aufruf lädt `tiktoken` einmalig die Tokenizer-Datei herunter.

## Schritt 1: Indexierung

```bash
python rag/chunking.py                  # Übersicht: Chunks und Tokens je Artikel (ohne API)
python rag/chunking.py --show KB-018    # Chunks eines Artikels im Wortlaut
python rag/index_kb.py --dry-run        # Anzahl Chunks und geschätzte Kosten
python rag/index_kb.py                  # Embeddings erzeugen und Qdrant befüllen
python rag/search.py --ticket P-04      # Vektorsuche für ein Pilotticket prüfen
```

`index_kb.py` legt die Collection bei jedem Lauf neu an. Damit entspricht der Index immer genau der aktuellen `config.yaml`.

`search.py` markiert mit ✓ Treffer aus Artikeln, die für das Ticket als relevant gelten (`belegartikel` und bestätigte `weitere_kandidaten`). Haupttickets sind gesperrt, solange die Konfiguration nicht eingefroren ist (E-10).

## Weitere Schritte

| Schritt | Inhalt | Status |
| --- | --- | --- |
| 2 | Reranking mit Cross-Encoder, Retrieval-Test auf den Pilottickets | folgt |
| 3 | Generierung beider Bedingungen, Protokoll nach DEMI 2.2 | folgt |
| 4 | Pilot P-01 bis P-10, Festlegung der Pilot-Parameter, Tag `rag-v1.0` | folgt |
| 5 | Hauptlauf: 120 Tickets × 2 Bedingungen | folgt |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `config.yaml` | alle Parameter; ihr Hash steht in jedem Log-Eintrag |
| `ENTSCHEIDUNGEN.md` | Entscheidungsprotokoll mit Begründung und DEMI-Bezug |
| `docker-compose.yml` | Qdrant mit fester Version, nur lokal erreichbar |
| `common.py` | Pfade, Konfiguration, Hashes, Git-Stand, Kostenberechnung |
| `chunking.py` | Vorverarbeitung und Chunking |
| `index_kb.py` | Schritt 1: Indexierung |
| `search.py` | Kontrolle der Vektorsuche |
| `data/chunks.jsonl` | entsteht bei der Indexierung: alle Chunks im Wortlaut (Anhang der Arbeit) |
| `logs/index_log.jsonl` | entsteht bei der Indexierung: Zeitpunkt, Git-Commit, Config- und KB-Hash, Tokens, Kosten |

## Nachvollziehbarkeit

Jeder Log-Eintrag enthält:

- **Git-Commit** des Code-Stands und ob es nicht committete Änderungen gab (`dirty`). Läufe für die Auswertung erfolgen nur mit `dirty: false`.
- **`config_hash`**: welche Parameter galten.
- **`kb_hash`**: welche KB verwendet wurde. Der Wert muss mit `meta.kb_hash` der Tickets übereinstimmen.
- **Tokens und Kosten** nach der Preisliste zum Stichtag in `config.yaml`.
