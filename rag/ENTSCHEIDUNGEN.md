# Entscheidungsprotokoll RAG-Prototyp

Jede Designentscheidung mit Datum, Begründung und Bezug zur DEMI. Status „fest“ heißt: vorgegeben oder entschieden. „Pilot“ heißt: Startwert, die endgültige Festlegung erfolgt mit P-01 bis P-10 und wird hier nachgetragen.

| ID | Datum | Entscheidung | Status |
| --- | --- | --- | --- |
| E-01 | 2026-10-10 | Prototyp im selben Repo unter `rag/` | fest |
| E-02 | 2026-10-10 | Qdrant v1.19.2 lokal per Docker | fest |
| E-03 | 2026-10-10 | Embedding `text-embedding-3-small`, 1536 Dimensionen, Kosinus | fest |
| E-04 | 2026-10-10 | Vorverarbeitung: Frontmatter, H1 und „Verwandte Artikel“ entfernen | fest |
| E-05 | 2026-10-10 | Chunking: feste Token-Größe mit Überlappung, Titel vorangestellt | Pilot |
| E-06 | 2026-10-10 | Reranker: lokaler Cross-Encoder `BAAI/bge-reranker-v2-m3` | fest |
| E-07 | 2026-10-10 | Generierung: `gpt-4.1-mini-2025-04-14`, Temperatur 0,2 | fest |
| E-08 | 2026-10-10 | Preise in USD zum Stichtag 2026-10-10 | fest |
| E-09 | 2026-10-10 | Suchanfrage ist der unveränderte Tickettext | fest |
| E-10 | 2026-10-10 | Abstimmung nur mit Pilottickets | fest |
| E-11 | 2026-10-10 | Umfragetool: SoSci Survey oder vergleichbares Online-Tool | offen |

## E-01 Repo-Struktur

Der Prototyp liegt im selben Repository wie Knowledge Base und Ticketset, im Ordner `rag/`. KB (`kb/`, Tag `kb-v1.0`) und Tickets (`tickets.jsonl`, Tag `tickets-v1.0`) werden unverändert gelesen. Der `kb_hash` im Indexierungsprotokoll wird mit derselben Formel berechnet wie in `generate_tickets.py`. Stimmt er mit `meta.kb_hash` der Tickets überein, ist belegt, dass Tickets und Index auf derselben KB beruhen.

## E-02 Vektordatenbank

Qdrant in der festen Version v1.19.2, lokal als Docker-Container, nur über `127.0.0.1` erreichbar. Gründe: reproduzierbar durch die feste Version, keine Kosten während des Experiments, keine Daten bei Dritten. Für die Wirtschaftlichkeitsanalyse wird die Annahme einer kostenfreien Vektordatenbank laut DEMI 3.5 durch die Betriebskosten einer gehosteten Variante nach Preisliste ersetzt.

## E-03 Embedding

`text-embedding-3-small` mit 1536 Dimensionen und Kosinus-Ähnlichkeit, wie in DEMI Tabelle 4 festgelegt.

## E-04 Vorverarbeitung

- Das YAML-Frontmatter (ID, Kategorie, Titel, Länder, Stand) wird als Metadaten gespeichert und nicht eingebettet.
- Die H1-Überschrift entfällt, weil der Titel jedem Chunk vorangestellt wird (E-05).
- Der Abschnitt „Verwandte Artikel“ wird entfernt. Er enthält nur Verweise auf andere Artikel, keine Fakten, und erzeugt Scheintreffer. Ein Beispiel aus der Relevanz-Review: Bei T-067 fanden sich „5-Jahres-Garantie“-Treffer in KB-023 und KB-025 nur in der Verweisliste.

Die KB-Dateien selbst bleiben unverändert. Die Vorverarbeitung betrifft nur den Index.

## E-05 Chunking

- **Feste Chunk-Größe in Tokens mit Überlappung**, wie in DEMI Tabelle 4 festgelegt. Gezählt wird mit dem Tokenizer von `text-embedding-3-small` (`cl100k_base`).
- **Grenzen auf Wortgrenzen**, damit kein Wort zerteilt wird. Die Größe ist daher eine Obergrenze und bezieht sich auf den Text ohne vorangestellten Titel.
- **Titel jedem Chunk vorangestellt**, damit auch spätere Chunks eines Artikels ihren thematischen Bezug behalten.
- **Startwerte: 200 Tokens, 40 Tokens Überlappung.** Die Artikel haben rund 120–280 Wörter, das ergibt meist 2–3 Chunks je Artikel.

Endgültige Werte: werden nach dem Pilot eingetragen.

Korrektur 2026-10-10: Die erste Fassung von `chunking.py` zählte die Tokens jedes Wortes einzeln und addierte sie. Weil der Tokenizer ein Leerzeichen mit dem folgenden Wort zu einem Token zusammenfasst, überschätzte das die Länge um rund 50 %. Die Chunks hatten deshalb nur etwa 120–140 statt 200 Tokens (139 statt erwartet rund 90–100 Chunks). Seit der Korrektur wird immer der zusammengesetzte Text gezählt. Der erste Indexlauf steht weiterhin in `logs/index_log.jsonl`, sein Git-Commit verweist auf die alte Fassung.

## E-06 Reranker

Lokaler Cross-Encoder `BAAI/bge-reranker-v2-m3`: mehrsprachig (auch Deutsch), feste Modellgewichte und damit reproduzierbar, keine API-Kosten, keine Daten bei Dritten. Er ordnet die Top-5 der Vektorsuche neu und behält die besten 3 (DEMI Tabelle 4). Die Modellrevision wird beim ersten Download fixiert und hier nachgetragen.

## E-07 Generierungsmodell

`gpt-4.1-mini` im datierten Snapshot `gpt-4.1-mini-2025-04-14`, Temperatur 0,2, gleiche maximale Antwortlänge in beiden Bedingungen (DEMI Tabelle 4). Laut OpenAI-Deprecations-Seite ist für gpt-4.1-mini derzeit keine Abschaltung angekündigt (Abruf 2026-10-10). Der Hauptlauf muss trotzdem zeitnah erfolgen, weil sich das ändern kann.

## E-08 Preise

Preise in USD je 1 Mio. Tokens, Stichtag 2026-10-10:

| Modell | Input | Cached Input | Output |
| --- | --- | --- | --- |
| `gpt-4.1-mini-2025-04-14` | 0,40 | 0,10 | 1,60 |
| `text-embedding-3-small` | 0,02 | – | – |

Quellen: OpenAI-Modellseiten zu gpt-4.1-mini und text-embedding-3-small (Abruf 2026-10-10). Die Umrechnung in Euro erfolgt erst in Teilstudie B, mit dem Wechselkurs zum Stichtag.

## E-09 Suchanfrage

Als Suchanfrage dient der unveränderte Tickettext, ohne Umformulierung oder Zusammenfassung durch ein Modell. So unterscheiden sich die Bedingungen nur im Kontextblock und in der Belegpflicht (DEMI 1.3.2), und das Retrieval bleibt ohne zusätzlichen Modellaufruf nachvollziehbar.

## E-10 Abstimmung nur mit Pilottickets

Chunk-Größe, Überlappung, Prompt und maximale Antwortlänge werden ausschließlich mit P-01 bis P-10 abgestimmt. Danach wird die Konfiguration eingefroren (Tag `rag-v1.0`). Die Haupttickets werden erst im Hauptlauf verwendet. `search.py` sperrt sie, solange nicht ausdrücklich `--erlaube-haupt` gesetzt wird.

## E-11 Umfragetool

SoSci Survey oder ein vergleichbares Online-Tool. Anforderungen: ausgewogene Zuteilung auf 10 Blöcke (z. B. SoSci-Urnen), Randomisierung der Reihenfolge je Person, Screening-Item S4, Einwilligung, Server in der EU.
