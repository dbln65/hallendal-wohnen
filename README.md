# Automatisierte Bewertung (Teilstudie A, Strang 2)

LLM-as-a-Judge nach DEMI 2.3 und Tabelle 13, orientiert an RAGAS (Es et al., 2024). Ein anderes Modell als der Generator bewertet jeden Antwortentwurf des Hauptlaufs `haupt-01`.

| Metrik | gilt für | Aufruf | Kennzahl | Hypothese |
| --- | --- | --- | --- | --- |
| KB-Supportedness | beide | A: Sachaussagen bestimmen und gegen die gesamte KB prüfen | Anteil gedeckter Sachaussagen | H3 |
| RAG-Faithfulness | nur RAG | B: dieselben Sachaussagen gegen die drei übergebenen Auszüge prüfen | Anteil ableitbarer Sachaussagen | Diagnose |
| Context Relevance | nur RAG | C: übergebene Auszüge auf Erforderlichkeit prüfen | Anteil erforderlicher Auszüge | Diagnose |
| Answer Relevance | beide | D: drei Kundenanfragen aus dem Entwurf ableiten, Kosinus-Ähnlichkeit zur Originalanfrage | Mittelwert der Kosinus-Ähnlichkeit | beschreibend |
| Referenzbasierte Korrektheit | beide | E: Vergleich mit Musterantwort, Kernaussagen und Antworttyp | korrekt / teilweise / falsch | H1, H6 |

## Ablauf

```bash
# im Repo-Hauptverzeichnis; benötigt ANTHROPIC_API_KEY und OPENAI_API_KEY (Umgebungsvariablen, nie ins Repo)
python judge/judge.py --run pilot-03 --judge-run pilot-03-j1 --dry-run --ids P-02   # 1. Prompts ansehen
python judge/judge.py --run pilot-03 --judge-run pilot-03-j1                        # 2. Pilot
python judge/judge.py --run haupt-01 --judge-run haupt-01-j1 --erlaube-haupt        # 4. Hauptlauf
python judge/judge.py --run haupt-01 --judge-run haupt-01-j1-wdh --erlaube-haupt --stabilitaet   # 5. Stabilitätsprüfung
```

| # | Schritt | Status |
| --- | --- | --- |
| 1 | Prompts im Trockenlauf prüfen | erledigt (2026-10-20) |
| 2 | Pilot an den 20 Entwürfen aus `pilot-03`; `uebersicht.md` durchsehen, Prompts bei Bedarf überarbeiten (neuer Judge-Lauf `pilot-03-j2` usw.) | `pilot-03-j1` erledigt (0,62 USD), Prompts überarbeitet (J-11); `pilot-03-j2` offen |
| 3 | Prompts und Skript einfrieren, Tag `judge-v1.0` | offen |
| 4 | Hauptlauf über 240 Entwürfe; Ergebnisse erst nach dem Konsens der Kodierung ansehen (K-07) | offen |
| 5 | Stabilitätsprüfung: 24 Entwürfe erneut bewerten (J-03) | offen |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `judge.py` | Bewertung, Protokollierung, Übersicht für den Pilot |
| `prompts/*.txt` | Systemprompts der fünf Aufrufe; Hash je Prompt samt JSON-Schema in `judge_meta.json` |
| `runs/<judge-run>/judge.jsonl` | ein Eintrag je Entwurf: Urteile im Wortlaut mit Begründung, Kennzahlen, Tokens, Kosten |
| `runs/<judge-run>/judge_meta.json` | Modell, Effort, Prompt-Hashes, KB-Hash, Preise, Git-Stand, Zeitraum, Summen |
| `runs/<judge-run>/uebersicht.md` | lesbare Übersicht (nur Pilot- und Testläufe) |
| `runs/<judge-run>/errors.jsonl` | fehlgeschlagene Entwürfe; ein erneuter Aufruf versucht sie noch einmal |

## Entscheidungen

| Nr. | Datum | Entscheidung |
| --- | --- | --- |
| J-01 | 2026-10-20 | **Judge-Modell `claude-sonnet-5-5`.** Anderes Modell als der Generator `gpt-4.1-mini` (DEMI 2.3) und anderer Modellstand als `claude-sonnet-5`, mit dem KB, Tickets und Musterantworten erzeugt wurden. Das verringert das Risiko, dass der Judge Texte bevorzugt, die seinem eigenen Stil ähneln; RAG-Entwürfe übernehmen Formulierungen aus der KB. Datumslose Modell-IDs bezeichnen einen festen Modellstand. Preise laut Preisliste vom 2026-10-20: 2 USD (Input), 2,50 USD (Cache-Schreiben), 0,10 USD (Cache-Lesen), 10 USD (Output) je 1 Mio. Tokens. |
| J-02 | 2026-10-20 | **Entwürfe ohne Belege.** Der Judge erhält alle Entwürfe mit derselben Bereinigung wie die Befragung (`strip_citations` aus `umfrage/prepare_survey.py`). Er erkennt die Bedingung damit nicht an den Belegen, und beide Bedingungen werden mit identischen Prompts bewertet. Zugleich beurteilen Judge und Befragte denselben Text (H6). |
| J-03 | 2026-10-20 | **Stabilitätsprüfung.** Bei Claude-Modellen ab 4.7 lassen sich Temperatur und andere Sampling-Parameter nicht verändern; identische Anfragen können unterschiedliche Urteile ergeben. 24 Entwürfe (12 RAG, 12 LLM-only, Seed `20261020:stabilitaet`) werden in einem zweiten Judge-Lauf erneut bewertet; berichtet wird die Übereinstimmung beider Läufe. |
| J-04 | 2026-10-20 | **Sachaussagen wie im Kodierleitfaden.** Definition und Ausschlüsse nach LEITFADEN.md, Abschnitt 3, und AUSLEGUNGEN.md (A-01, A-07), jedoch ohne Obergrenze von drei. Eine Sachaussage gilt nur als gedeckt, wenn die KB sie vollständig stützt (strenge Auslegung wie K-04). Entwürfe ohne Sachaussage haben keine KB-Supportedness und gehen nicht in H3 ein (DEMI 2.3). |
| J-05 | 2026-10-20 | **Answer Relevance ohne „noncommittal“-Abschlag.** RAGAS setzt den Wert ausweichender Antworten auf 0. Das würde korrekte Rückfragen bei KB-Gap-Tickets bestrafen; das Rückfrageverhalten erfasst H4. Drei abgeleitete Anfragen, Embeddings mit `text-embedding-3-small` wie im Retrieval. |
| J-06 | 2026-10-20 | **Effort `medium`, adaptives Denken.** Bei `claude-sonnet-5-5` lässt sich das Denken nicht abschalten; `medium` entspricht der Einstellung bei der KB-Erzeugung. Denk-Tokens werden als Output-Tokens abgerechnet und sind in den Kosten enthalten. |
| J-07 | 2026-10-20 | **Strukturierte Ausgabe** über `output_config.format` (JSON-Schema). Jede Antwort ist gültiges JSON in festem Aufbau; die Begründung steht im Schema vor dem Urteil. Ungültige oder abgebrochene Antworten werden einmal wiederholt, sonst als Fehler protokolliert. |
| J-08 | 2026-10-20 | **Eine Aussagenmenge für KB-Supportedness und Faithfulness.** Die Sachaussagen werden einmal bestimmt (Aufruf A) und für Aufruf B übernommen, damit sich beide Anteile auf dieselben Aussagen beziehen. |
| J-09 | 2026-10-20 | **Korrektheit referenzbasiert ohne KB.** Referenz sind Musterantwort, Kernaussagen und Antworttyp; die KB wird nicht übergeben, damit H1 unabhängig von der KB-Supportedness (H3) gemessen wird. Für den Antworttyp „rueckfrage“ (KB-Gap) gilt eine eigene Stufendefinition. |
| J-10 | 2026-10-20 | **Pilot, Einfrieren, Verblindung.** Die Prompts werden an `pilot-03` erprobt und danach eingefroren (`judge-v1.0`). Beim Hauptlauf zeigt die Konsole nur Fortschritt und Kosten, und es entsteht keine Übersicht; die Ergebnisse werden erst nach dem Konsens der Kodierung ausgewertet (K-07). |
| J-11 | 2026-10-20 | **Änderungen nach dem Pilot `pilot-03-j1` (Prompts v2).** (a) Aufruf A: Ankündigungen eigener Handlungen gelten auch dann nicht als Sachaussage, wenn sie ein mögliches Ergebnis nennen (P-06: „Wir kümmern uns um einen Austausch …“, „So können wir den Schaden dokumentieren …“); entspricht A-07. (b) Aufruf A: Eine weggelassene Bedingung macht eine Aussage nicht ungedeckt, solange sie für den Fall der Anfrage zutrifft (P-07: Ratenkauf über 24 Monate ohne Hinweis auf Deutschland); entspricht A-08. (c) Aufruf E: Ein Widerspruch ist eine mit der Referenz unvereinbare Aussage; Angaben, die in der Referenz fehlen, sind keiner (P-07: „Bonitätsprüfung“ war als Widerspruch gewertet). (d) Aufruf E, Antworttyp „rueckfrage“: Beantwortet der Entwurf den offenen Punkt inhaltlich mit unbelegten Sachangaben, ist er falsch, auch bei zusätzlicher Rückfrage (P-09: erfundene FSC-Zertifizierung war als teilweise gewertet); der Verweis auf die allgemeinen Kontaktwege zur Weiterleitung ist keine Sachangabe (P-10). Die Änderungen folgen aus Leitfaden und Auslegungen der manuellen Kodierung und wurden ausschließlich an den Pilotdaten erprobt. |
