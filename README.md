# RAG-gestütztes Agent-Assist-System im Kundenservice

Prototyp, Datenbasis und Auswertung einer Bachelorarbeit zur Frage, inwieweit ein RAG-gestütztes Agent-Assist-System im Kundenservice gegenüber einem LLM ohne RAG die Antwortqualität und Belegbarkeit verbessert und unter welchen Bedingungen der Einsatz wirtschaftlich sinnvoll ist (ROI/TCO).

> **Fiktives Szenario.** „Hallendal Wohnen“ ist ein erfundener Online-Möbelhändler. Wissensdatenbank, Kundenanfragen und Musterantworten sind synthetisch erzeugt und manuell geprüft. Das Repository enthält keine echten Kundendaten.

## Untersuchungsdesign

**Teilstudie A** ist ein Experiment mit Messwiederholung: Jede der 120 Kundenanfragen (96 durch die Wissensdatenbank gedeckt, 24 bewusst nicht gedeckt, „KB-Gap“) wird unter zwei Bedingungen beantwortet, mit demselben Sprachmodell:

- **RAG:** Abruf passender Passagen aus der Wissensdatenbank, Antwortentwurf mit Pflicht zur Quellenangabe
- **LLM-only:** Antwortentwurf ohne Zugriff auf die Wissensdatenbank

Die 240 Antwortentwürfe werden in vier Strängen erhoben und bewertet:

| Strang | Methode | Ort |
| --- | --- | --- |
| 1 | automatisierte Protokollierung: Tokens, Kosten, Latenz, Retrieval-Trefferquote | `rag/`, `auswertung/` |
| 2 | automatisierte Bewertung (LLM-as-a-Judge, an RAGAS orientiert): KB-Supportedness, Faithfulness, Context Relevance, Answer Relevance, referenzbasierte Korrektheit | `judge/` |
| 3 | verblindete Online-Befragung zur wahrgenommenen Qualität (Teilstichprobe von 120 Entwürfen) | `umfrage/` |
| 4 | manuelle Inhaltskodierung mit Zweitkodierung: Aussagendeckung, Quellenpassung, Failure Modes, Rückfrageverhalten | `kodierung/` |

**Teilstudie B** ist eine Modellrechnung zur Wirtschaftlichkeit (TCO, modellierter ROI, Break-even, Sensitivitätsanalyse) in drei Szenarien. Einziger Messwert aus Teilstudie A sind die variablen Kosten je Anfrage.

## Ablauf und Verzeichnisse

| # | Schritt | Dateien | Dokumentation |
| --- | --- | --- | --- |
| 1 | Wissensdatenbank: 40 Artikel aus einem Firmensteckbrief erzeugen, automatisch validieren, manuell prüfen | `steckbrief.md`, `plan.csv`, `generate_kb.py`, `validate_kb.py`, `fix_related.py`, `kb/` | [KB.md](KB.md), [REVIEW.md](REVIEW.md), [NACHBEARBEITUNG.md](NACHBEARBEITUNG.md) |
| 2 | Ticketset: 120 Haupt- und 10 Pilotanfragen mit Musterantwort, Kernaussagen und Belegartikeln; Teilstichprobe für die Befragung ziehen | `tickets_plan.csv`, `generate_tickets.py`, `validate_tickets.py`, `draw_rating_sample.py`, `tickets/`, `tickets.jsonl` | [TICKETS.md](TICKETS.md) |
| 3 | Prototyp: Chunking, Embeddings, Vektorsuche (Qdrant), Reranking, Generierung beider Bedingungen; Pilot- und Hauptläufe | `rag/` | [rag/README.md](rag/README.md), [rag/ENTSCHEIDUNGEN.md](rag/ENTSCHEIDUNGEN.md) |
| 4 | Strang 2: automatisierte Bewertung aller Entwürfe, Stabilitätsprüfung | `judge/` | [judge/README.md](judge/README.md) |
| 5 | Strang 3: Verblindung, Fragebogen, Export für das Umfragetool, Import der Antworten | `umfrage/` | [umfrage/README.md](umfrage/README.md) |
| 6 | Strang 4: Kodierleitfaden, Erst- und Zweitkodierung, Konsistenzprüfung | `kodierung/` | [kodierung/README.md](kodierung/README.md) |
| 7 | Auswertung: Strang 1, Teilstudie B und Hypothesentests | `auswertung/` | [auswertung/README.md](auswertung/README.md) |

Jede README eines Unterordners beschreibt Aufrufe, erzeugte Dateien und die dort getroffenen methodischen Entscheidungen mit Datum und Begründung.

## Einrichtung

Voraussetzungen: Python 3.11 oder neuer, Docker, API-Schlüssel für OpenAI und Anthropic.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt              # Wissensdatenbank und Tickets
pip install -r rag/requirements.txt          # Prototyp, Befragung, Kodierung, Judge
pip install -r auswertung/requirements.txt   # Auswertung

export OPENAI_API_KEY=...      # Generierung der Antwortentwürfe, Embeddings
export ANTHROPIC_API_KEY=...   # Wissensdatenbank, Tickets, Judge

cd rag && docker compose up -d && cd ..      # Qdrant, nur lokal erreichbar
```

API-Schlüssel werden ausschließlich als Umgebungsvariablen gesetzt und nie im Repository gespeichert. Alle Skripte werden aus dem Repo-Hauptverzeichnis aufgerufen.

## Eingesetzte Modelle

| Zweck | Modell |
| --- | --- |
| Antwortentwürfe (beide Bedingungen) | `gpt-4.1-mini-2025-04-14` |
| Embeddings | `text-embedding-3-small` |
| Reranking | `BAAI/bge-reranker-v2-m3` (feste Revision, CPU) |
| Wissensdatenbank, Tickets, Musterantworten | `claude-sonnet-5` |
| Automatisierte Bewertung (Judge) | `claude-sonnet-5-5` |

Der Judge ist bewusst ein anderes Modell als der Generator der Antwortentwürfe und ein anderer Modellstand als das Modell, das Wissensdatenbank und Musterantworten erzeugt hat.

## Nachvollziehbarkeit

- **Protokolle:** Jeder Lauf schreibt Modell-ID, Prompt- und Konfigurations-Hashes, Hash der Wissensdatenbank, Tokens, Kosten, Zeitstempel und Git-Stand mit (`*_log.jsonl`, `run_meta.json`, `judge_meta.json`, `meta.json`).
- **Eingefrorene Stände:** Wissensdatenbank, Tickets, Prototyp, Befragung, Kodierleitfaden und Judge wurden vor ihrer Verwendung eingefroren und mit Git-Tags versehen (`kb-v1.0`, `tickets-v1.0`, `rag-v1.0`, `umfrage-v1.0`, `kodierung-v1.0`, `judge-v1.0`).
- **Feste Zufallszahlen:** Reihenfolge der Bedingungen, Blockbildung der Befragung und Stichproben (Zweitkodierung, Stabilitätsprüfung) beruhen auf festen Seeds.
- **Verblindung:** Die Ergebnisse der Stränge 2 bis 4 werden erst ausgewertet, wenn die manuelle Kodierung im Konsens abgeschlossen ist.
- **Sampling:** Die eingesetzten Claude-Modelle erlauben keine Festlegung der Temperatur. Die Schwankung zwischen Läufen wird für den Judge mit einer Stabilitätsprüfung beziffert.

## Nicht im Repository

- API-Schlüssel
- Qdrant-Speicher (`rag/qdrant_storage/`); er wird mit `rag/index_kb.py` aus der Wissensdatenbank neu erzeugt
