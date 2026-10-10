# Entscheidungsprotokoll RAG-Prototyp

Jede Designentscheidung mit Datum, Begründung und Bezug zur DEMI. Status „fest“ heißt: vorgegeben oder entschieden. „Pilot“ heißt: Startwert, die endgültige Festlegung erfolgt mit P-01 bis P-10 und wird hier nachgetragen.

| ID | Datum | Entscheidung | Status |
| --- | --- | --- | --- |
| E-01 | 2026-10-10 | Prototyp im selben Repo unter `rag/` | fest |
| E-02 | 2026-10-10 | Qdrant v1.19.2 lokal per Docker | fest |
| E-03 | 2026-10-10 | Embedding `text-embedding-3-small`, 1536 Dimensionen, Kosinus | fest |
| E-04 | 2026-10-10 | Vorverarbeitung: Frontmatter, H1 und „Verwandte Artikel“ entfernen | fest |
| E-05 | 2026-10-10 | Chunking: 300 Tokens, 60 Tokens Überlappung, ohne Titel (im Pilot festgelegt) | fest |
| E-06 | 2026-10-10 | Reranker: lokaler Cross-Encoder `BAAI/bge-reranker-v2-m3` | fest |
| E-07 | 2026-10-10 | Generierung: `gpt-4.1-mini-2025-04-14`, Temperatur 0,2 | fest |
| E-08 | 2026-10-10 | Preise in USD zum Stichtag 2026-10-10 | fest |
| E-09 | 2026-10-10 | Suchanfrage ist der unveränderte Tickettext | fest |
| E-10 | 2026-10-10 | Abstimmung nur mit Pilottickets | fest |
| E-11 | 2026-10-10 | Umfragetool: SoSci Survey oder vergleichbares Online-Tool | offen |
| E-12 | 2026-10-10 | Prompt-Gerüst: identisch, Unterschied nur Kontextblock und Belegpflicht | Pilot |
| E-13 | 2026-10-10 | Belege auf Artikelebene `[KB-xxx]`, automatisch entfernbar | fest |
| E-14 | 2026-10-10 | Durchführung: Reihenfolge je Ticket zufällig, Aufwärmaufruf, Latenzdefinition | fest |

## E-01 Repo-Struktur

Der Prototyp liegt im selben Repository wie Knowledge Base und Ticketset, im Ordner `rag/`. KB (`kb/`, Tag `kb-v1.0`) und Tickets (`tickets.jsonl`, Tag `tickets-v1.0`) werden unverändert gelesen. Der `kb_hash` im Indexierungsprotokoll wird mit derselben Formel berechnet wie in `generate_tickets.py`. Stimmt er mit `meta.kb_hash` der Tickets überein, ist belegt, dass Tickets und Index auf derselben KB beruhen.

## E-02 Vektordatenbank

Qdrant in der festen Version v1.19.2, lokal als Docker-Container, nur über `127.0.0.1` erreichbar. Gründe: reproduzierbar durch die feste Version, keine Kosten während des Experiments, keine Daten bei Dritten. Für die Wirtschaftlichkeitsanalyse wird die Annahme einer kostenfreien Vektordatenbank laut DEMI 3.5 durch die Betriebskosten einer gehosteten Variante nach Preisliste ersetzt.

## E-03 Embedding

`text-embedding-3-small` mit 1536 Dimensionen und Kosinus-Ähnlichkeit, wie in DEMI Tabelle 4 festgelegt.

## E-04 Vorverarbeitung

- Das YAML-Frontmatter (ID, Kategorie, Titel, Länder, Stand) wird als Metadaten gespeichert und nicht eingebettet.
- Die H1-Überschrift entfällt. Der Titel steht in den Metadaten jedes Chunks; ob er zusätzlich dem Chunk-Text vorangestellt wird, regelt E-05.
- Der Abschnitt „Verwandte Artikel“ wird entfernt. Er enthält nur Verweise auf andere Artikel, keine Fakten, und erzeugt Scheintreffer. Ein Beispiel aus der Relevanz-Review: Bei T-067 fanden sich „5-Jahres-Garantie“-Treffer in KB-023 und KB-025 nur in der Verweisliste.

Die KB-Dateien selbst bleiben unverändert. Die Vorverarbeitung betrifft nur den Index.

## E-05 Chunking

- **Feste Chunk-Größe in Tokens mit Überlappung**, wie in DEMI Tabelle 4 festgelegt. Gezählt wird mit dem Tokenizer von `text-embedding-3-small` (`cl100k_base`).
- **Grenzen auf Wortgrenzen**, damit kein Wort zerteilt wird. Die Größe ist daher eine Obergrenze und bezieht sich auf den Text ohne vorangestellten Titel.
- **Titel voranstellen (ja/nein)** wurde im Pilot geprüft. Die Überlegung dafür: Auch spätere Chunks eines Artikels behalten so ihren thematischen Bezug. Die Überlegung dagegen: Alle Chunks eines Artikels werden einander ähnlicher und verdrängen in der Vektorsuche andere Artikel.
- **Startwerte: 200 Tokens, 40 Tokens Überlappung.** Die Artikel haben rund 120–280 Wörter, das ergibt meist 2–3 Chunks je Artikel.

**Festlegung im Pilot (vorab definiert, 2026-10-10).** Mit `eval_retrieval.py` werden sechs Varianten auf den 8 KB-gedeckten Pilottickets (26 Beleg-Zitate) verglichen. Format: Chunk-Tokens/Überlappung/Titel.

- `150/30/ja`, `200/40/ja`, `300/60/ja`, `400/80/ja` (Überlappung jeweils 20 %)
- `200/40/nein`, `300/60/nein` (Wirkung des vorangestellten Titels)

Entscheidungsregel, festgelegt vor dem ersten Vergleich:

1. höchste Beleg-Abdeckung@3 nach Reranking, also der Anteil der Beleg-Zitate, die wörtlich in den drei an das Modell übergebenen Passagen stehen;
2. bei Gleichstand (Unterschied von höchstens einem Zitat) höherer Artikel-Treffer@3 nach Reranking;
3. danach der kürzere Kontext (geringere Kosten).

Einschränkung: Bei 8 Tickets ist der Vergleich grob. Er dient der begründeten Wahl eines Parameters, nicht dem Nachweis eines Unterschieds.

Einschränkung der Kennzahl (festgestellt beim ersten Testlauf am 2026-10-10, vor dem Variantenvergleich): Die Beleg-Abdeckung zählt nur wörtliche Zitate. Steht derselbe Fakt in einem anderen Artikel anders formuliert, gilt er als nicht abgedeckt. Beispiel P-03: Die abgerufenen Chunks aus KB-015 und KB-017 enthalten beide Kernaussagen („ungebraucht“, „Originalverpackung erwünscht, aber nicht Pflicht“), die Belege stammen aber aus KB-014. Die Kennzahl unterschätzt die tatsächliche Abdeckung daher. Für den Vergleich der Varianten ist das unkritisch, weil alle Varianten dieselben Artikeltexte enthalten und nur die Chunk-Grenzen sich unterscheiden. Für die F2-Kodierung im Hauptlauf gilt: Maßgeblich ist, ob der Fakt inhaltlich in einer abgerufenen Passage steht, nicht nur die Artikel-ID.

**Ergebnis des Variantenvergleichs (2026-10-10, `logs/retrieval_eval.jsonl`)**

| Variante | Chunks | Artikel-Treffer R@3 | Beleg-Abdeckung V@5 | V@3 | R@3 | Kontext (Zeichen) |
| --- | --- | --- | --- | --- | --- | --- |
| 150/30/ja | 113 | 0,88 | 0,81 | 0,61 | 0,58 | 1525 |
| 200/40/ja | 89 | 0,88 | 0,65 | 0,61 | 0,61 | 1881 |
| 300/60/ja | 63 | 0,88 | 0,85 | 0,81 | **0,81** | 2679 |
| 400/80/ja | 44 | 0,88 | 0,92 | 0,85 | 0,73 | 3258 |
| 200/40/nein | 89 | 1,00 | 0,65 | 0,58 | 0,58 | 1804 |
| 300/60/nein | 63 | 0,88 | 0,85 | 0,69 | **0,81** | 2441 |

Anwendung der Entscheidungsregel:

1. Die höchste Beleg-Abdeckung@3 nach Reranking erreichen `300/60/ja` und `300/60/nein` mit je 0,81 (21 von 26 Zitaten). `400/80/ja` liegt mit 0,73 zwei Zitate darunter und scheidet damit aus.
2. Artikel-Treffer@3: beide 0,88, also Gleichstand.
3. Kürzerer Kontext: `300/60/nein` mit 2441 statt 2679 Zeichen.

**Festlegung: 300 Tokens, 60 Tokens Überlappung, ohne vorangestellten Titel.** Der Titel steht weiterhin in den Metadaten und kann im Kontextblock des Prompts angezeigt werden (Schritt 3).

Beobachtungen:
- Kleine Chunks (150, 200) zerteilen Fakten häufiger und senken die Abdeckung.
- Bei 400 Tokens senkt das Reranking die Abdeckung gegenüber der reinen Vektorsuche (0,85 auf 0,73). Eine mögliche Ursache: Ticket und Chunk überschreiten zusammen die maximale Eingabelänge des Cross-Encoders (512 Tokens), und das Ende des Chunks wird abgeschnitten. Das wird in Schritt 3 geprüft.

Korrektur 2026-10-10: Die erste Fassung von `chunking.py` zählte die Tokens jedes Wortes einzeln und addierte sie. Weil der Tokenizer ein Leerzeichen mit dem folgenden Wort zu einem Token zusammenfasst, überschätzte das die Länge um rund 50 %. Die Chunks hatten deshalb nur etwa 120–140 statt 200 Tokens (139 statt erwartet rund 90–100 Chunks). Seit der Korrektur wird immer der zusammengesetzte Text gezählt. Der erste Indexlauf steht weiterhin in `logs/index_log.jsonl`, sein Git-Commit verweist auf die alte Fassung.

## E-06 Reranker

Lokaler Cross-Encoder `BAAI/bge-reranker-v2-m3`: mehrsprachig (auch Deutsch), feste Modellgewichte und damit reproduzierbar, keine API-Kosten, keine Daten bei Dritten. Er ordnet die Top-5 der Vektorsuche neu und behält die besten 3 (DEMI Tabelle 4). Die Scores werden auf der CPU berechnet (`reranker_device: cpu`), damit sie auf jedem Rechner gleich ausfallen. Die maximale Eingabelänge beträgt 512 Tokens; Ticket und Chunk liegen deutlich darunter.

Die Modellrevision (Commit auf Hugging Face) ermittelt `eval_retrieval.py` beim ersten Lauf. Sie wird danach in `config.yaml` als `reranker_revision` eingetragen, damit alle weiteren Läufe genau diese Gewichte verwenden. Revision: `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (ermittelt am 2026-10-10).

Änderung 2026-10-10, vor dem ersten Generierungslauf: `reranker_max_length` von 512 auf 1024 erhöht. Gründe: Bei der Variante 400/80 verschlechterte das Reranking die Abdeckung, was auf abgeschnittene Eingaben hindeutet, und Haupttickets sind teils länger als Pilottickets. Seitdem protokolliert `retrieval.py` je Paar die Eingabelänge in Tokens des Cross-Encoders und ob gekürzt wurde. Voraussetzung ist, dass das Modell Eingaben dieser Länge verarbeitet: `max_position_embeddings` = 8194 (geprüft am 2026-10-10 in der fixierten Revision). Kontrolle mit `eval_retrieval.py` (2026-10-10): Die Pilotwerte sind mit 1024 unverändert (Beleg-Abdeckung R@3 0,81). Die längste Eingabe hat 333 Tokens, gekürzt wurden 0 von 40 Paaren.

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

## E-12 Prompt-Gerüst

Beide Bedingungen erhalten denselben System-Prompt (`prompts/system.txt`) mit Rolle, Aufgabe und Format. Die Nachricht unterscheidet sich nur im Kontextblock mit den drei KB-Passagen und in der Belegpflicht (`prompts/user_rag.txt` statt `prompts/user_llm.txt`), wie in DEMI 1.3.2 und Tabelle 4 festgelegt.

- **Unternehmenskontext:** nur Name und Branche („Online-Shop für Möbel und Wohnaccessoires“), keine Regeln, Preise oder Fristen. Die LLM-only-Bedingung erhält damit kein Wissen über die KB.
- **Umgang mit Unsicherheit in beiden Bedingungen:** „Mache keine Angaben, die du nicht sicher weißt … sage das offen und biete an, den Punkt zu klären.“ Eine solche Anweisung ist in einem Agent-Assist-System üblich. Sie steht in beiden Bedingungen, damit ein Unterschied im Rückfrageverhalten (H4) auf den Kontext zurückgeht und nicht auf eine abweichende Anweisung.
- **Format wie die Musterantworten:** Sie-Form, „Guten Tag,“ … „Viele Grüße, Ihr Hallendal-Wohnen-Team“, höchstens 180 Wörter, Fließtext. Das macht die Entwürfe mit den Musterantworten vergleichbar, und in der Befragung sind beide Bedingungen äußerlich nicht zu unterscheiden.
- **Belegpflicht (nur RAG):** Jede sachliche Aussage stützt sich ausschließlich auf die Auszüge und erhält direkt dahinter die Artikel-ID. Was die Auszüge nicht abdecken, wird nicht behauptet.

Status „Pilot“: Der Wortlaut wird mit P-01 bis P-10 geprüft. Änderungen werden hier mit Begründung eingetragen, danach wird eingefroren.

**Änderungen nach Pilotlauf `pilot-01` (2026-10-10).** Grundsatz: Korrigiert werden nur Verstöße gegen die vorgegebene Form. Das inhaltliche Antwortverhalten (Ausführlichkeit, Zusatzinformationen, Rückfragen) wird nicht nachgesteuert, damit die Ergebnisse nicht durch Abstimmung auf die Pilottickets geprägt sind.

| Befund in `pilot-01` | Bedingung | Änderung |
| --- | --- | --- |
| Anrede mit Vorname („Guten Tag, Herr Tobias“) in 5 von 10 Tickets | beide | „Beginne genau mit „Guten Tag,“ ohne Namen und ohne „Herr“ oder „Frau“.“ |
| Kein Absatz, alles in einem Block | beide | „Gliedere in Absätze, getrennt durch eine Leerzeile: Anrede, Antwort, Gruß.“ |
| Belege gesammelt am Ende, teils nach der Grußformel (z. B. P-01, P-07) | RAG | Beleg am Ende jedes Satzes mit sachlicher Aussage, mit Beispiel; „Sammle die Belege nicht am Ende“; Grußformel als letzter Text |

Nicht geändert wurden unter anderem: Zusatzinformationen über die Frage hinaus (z. B. Kosten in P-01), die vorsichtige, häufig nachfragende Art der LLM-only-Bedingung und Aussagen ohne Deckung durch die Passagen (z. B. P-08, P-10). Diese Befunde gehören zum zu messenden Systemverhalten.

`show_run.py` prüft seitdem automatisch: Anrede, Grußformel am Ende, Absätze, Belege nach der Grußformel und Sätze mit Zahlen ohne Beleg.

## E-13 Belegformat

Belege stehen auf Artikelebene im Format `[KB-017]`, mehrere als `[KB-017, KB-018]`. Die Passagen sind im Prompt mit ihrer Artikel-ID gekennzeichnet. Artikelebene genügt für die Kodierung von C2 (Quellenpassung), weil die übergebenen Passagen je Antwort protokolliert sind.

Für die verblindete Befragung entfernt `generation.strip_citations()` die Belege automatisch (DEMI 2.4). Gespeichert werden beide Fassungen (`antwort`, `antwort_ohne_belege`). Zusätzlich werden protokolliert:

- `zitierte_artikel`: alle zitierten IDs
- `zitate_ausserhalb_kontext`: zitierte Artikel, die nicht übergeben wurden (Hinweis auf Citation-Fail, F4)
- `kb_ids_ausserhalb_format`: KB-IDs außerhalb des Belegformats; diese würden beim Entfernen übersehen und müssen vor der Befragung geprüft werden

## E-14 Durchführung

- **Ein Durchlauf je Ticket und Bedingung** (DEMI Tabelle 4).
- **Reihenfolge der Bedingungen je Ticket zufällig**, festgelegt über `reihenfolge_seed` (DEMI 1.3.1). Sie ist dadurch wiederholbar.
- **Aufwärmaufruf vor dem ersten protokollierten Aufruf**, nicht protokolliert, damit das Laden des Cross-Encoders und der Verbindungsaufbau die erste Latenzmessung nicht verzerren.
- **Latenz** (DEMI Tabelle 13, Zeit bis zur vollständigen Antwort): RAG = Embedding + Vektorsuche + Reranking + Generierung; LLM-only = Generierung. Die Teilzeiten werden einzeln protokolliert. Das Reranking läuft lokal auf der CPU, seine Dauer hängt daher von der Hardware ab; der verwendete Rechner wird in der Arbeit angegeben.
- **Seed und Fingerprint:** Der OpenAI-Parameter `seed` verringert die Zufallsvarianz, garantiert aber keine identischen Antworten. `system_fingerprint` wird protokolliert und zeigt Änderungen auf Anbieterseite an.
- **`store=False`:** Anfragen werden bei OpenAI nicht als gespeicherte Completions abgelegt.
- **Fehler und Fortsetzung:** Fehlgeschlagene Aufrufe stehen in `errors.jsonl`. Ein Lauf wird mit derselben `--run-id` fortgesetzt; vorhandene Einträge werden übersprungen.
- **Hauptlauf** nur mit `--erlaube-haupt` und sauberem Git-Stand (alles committet).
