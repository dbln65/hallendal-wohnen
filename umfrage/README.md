# Online-Befragung (Teilstudie A, Strang 3)

Vorbereitung der verblindeten Online-Befragung nach DEMI 1.4.3, 1.4.4, 2.4 und Tabelle 9–11. Grundlage ist der Hauptlauf `haupt-01` (Tag `run-haupt-01`) und die Teilstichprobe der 60 Tickets mit `human_rating = ja` in `tickets_plan.csv`.

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/
python umfrage/prepare_survey.py
```

Das Skript liest den Hauptlauf, entfernt die Belege, prüft die Texte, bildet die 10 Blöcke und vergibt pseudonyme Entwurfs-IDs. Es bricht mit einer Fehlerliste ab, wenn eine Prüfung scheitert. Bei gleichen Eingaben entstehen immer dieselben Dateien (fester Seed).

## Dateien

| Datei | Inhalt | ins Umfragetool? |
| --- | --- | --- |
| `prepare_survey.py` | Export, Prüfungen, Blockbildung | nein |
| `entwuerfe.csv` | `entwurf_id`, `block`, `ticket_text`, `antwort` (ohne Belege) | ja |
| `schluessel.csv` | `entwurf_id` → Ticket, Bedingung, Kategorie, Schwierigkeit, KB-Abdeckung, Wörter | **nein**, nur Auswertung |
| `blockbericht.txt` | Prüfergebnis, Verteilung je Block, Länge, Bereinigung | nein |
| `survey_meta.json` | Herkunft: Lauf, Hashes der Eingaben und Ausgaben, Seed, Git-Stand | nein |
| `FRAGEBOGEN.md` | Wortlaut aller Seiten, Ankerbeispiele, Übungsfall, Einladungstexte | ja (Texte) |

## Prüfungen im Skript

- 60 Tickets mit `human_rating = ja`, beide Bedingungen je Ticket im Lauf, keine doppelten Einträge
- Lauf mit sauberem Git-Stand (`dirty: false` in allen Segmenten von `run_meta.json`)
- Tickettext identisch mit `tickets.jsonl`, `finish_reason = stop`
- nach der Bereinigung keine Belegreste, keine Satzzeichen- oder Leerzeichenfehler, Anrede und Gruß unverändert
- Inhalt unverändert: Bereinigter Text und Original ohne Belege stimmen bis auf Leerzeichen und Satzzeichen (`. , ;`) überein
- je Block 12 Entwürfe, davon 6 RAG und 6 LLM-only, kein Ticket doppelt (DEMI 1.4.4)

## Entscheidungen

| Nr. | Datum | Entscheidung | Status |
| --- | --- | --- | --- |
| U-01 | 2026-10-10 | Belege für die Befragung mit verbesserter Bereinigung entfernen | fest |
| U-02 | 2026-10-10 | Blockbildung: geschichtet, reihum, Blockpaare mit getauschter Bedingung | fest |
| U-03 | 2026-10-10 | Pseudonyme Entwurfs-IDs, Schlüssel getrennt vom Umfragematerial | fest |
| U-04 | 2026-10-10 | Anker und Übungsfall aus Pilottickets, niedriger Anker konstruiert | fest |
| U-05 | 2026-10-10 | Blockzuteilung geschichtet nach S4 | geplant |
| U-06 | 2026-10-10 | Umfragetool SoSci Survey (löst E-11) | geplant |

### U-01 Bereinigung der Belege

`strip_citations()` in `rag/generation.py` hinterlässt bei Belegfolgen wie `[KB-012], [KB-025].` ein „,.“ (z. B. T-094) und lässt Leerzeichen am Zeilenende stehen. Der eingefrorene Code (`rag-v1.0`) und das Protokoll des Hauptlaufs bleiben unverändert. Für die Befragung entfernt `prepare_survey.py` Belege und Belegfolgen mit einer verbesserten Funktion. Eine Prüfung stellt sicher, dass sich bereinigter Text und Original ohne Belege nur in Leerzeichen und Satzzeichen unterscheiden. Alle Abweichungen von `antwort_ohne_belege` stehen in `blockbericht.txt`.

### U-02 Blockbildung

DEMI 1.4.4 verlangt 10 Blöcke zu 12 Entwürfen, je Block 6 Entwürfe je Bedingung und höchstens eine Bedingung je Ticket. Umsetzung:

1. Die 60 Tickets werden nach Schwierigkeit (einfach, mittel, komplex, KB-Gap) und Kategorie geordnet, innerhalb gleicher Merkmale in Zufallsreihenfolge (Seed 20261010).
2. Der RAG-Entwurf des Tickets an Position i kommt in Block (i mod 10) + 1, der LLM-only-Entwurf in Block ((i + 5) mod 10) + 1.

Folgen:

- Jeder Block enthält 6 RAG- und 6 LLM-only-Entwürfe aus 12 verschiedenen Tickets.
- Schwierigkeit und Kategorie verteilen sich gleichmäßig: je Block 4 einfache, 3–4 mittlere, 2–3 komplexe und 2–3 KB-Gap-Entwürfe.
- Die Blöcke 1/6, 2/7, 3/8, 4/9 und 5/10 enthalten dieselben 12 Tickets mit getauschter Bedingung. Jede Bedingung eines Tickets wird damit von einer anderen Gruppe von Bewertenden beurteilt.

Der Seed wurde einmalig festgelegt. Die Zuteilung wird nicht neu gezogen.

### U-03 Verblindung

Die Entwurfs-IDs E001–E120 werden in Zufallsreihenfolge vergeben und verraten weder Ticket noch Bedingung. Ins Umfragetool gelangen nur `entwuerfe.csv` und die Texte aus `FRAGEBOGEN.md`. `schluessel.csv` wird erst bei der Auswertung verwendet. `blockbericht.txt` zählt zusätzlich Wörter, die auf die Wissensdatenbank hinweisen könnten.

### U-04 Ankerbeispiele und Übungsfall

DEMI Tabelle 9 sieht je ein kommentiertes Beispiel für hohe und niedrige Ausprägung sowie einen nicht ausgewerteten Übungsfall vor.

- **Quelle:** Pilottickets. Sie gehören nicht zur Bewertungsstichprobe, daher sieht niemand ein Bewertungsticket vorab.
- **Hoher Anker:** Musterantwort von P-07, unverändert.
- **Niedriger Anker:** für dieselbe Anfrage konstruiert, mit gleicher Anrede und Grußformel. Die Mängel sind ein verfehltes Anliegen und ein abweisender Ton. Bewusst nicht verwendet werden Rückfragen oder Hinweise auf fehlende Informationen. Beides ist typisches Verhalten einer Bedingung (LLM-only fragt in `haupt-01` häufig nach der Bestellnummer, RAG enthält sich bei Gap-Tickets), und ein solcher Anker würde die Bewertenden gegen diese Bedingung einstimmen.
- **Kommentare:** nennen den oberen bzw. unteren Bereich der Skala, keine konkreten Werte.
- **Übungsfall:** Musterantwort von P-05, unverändert.

### U-05 Blockzuteilung nach S4 (geplant)

Zwei Urnen mit den Blöcken 1–10: eine für Personen mit Kundenservice-Erfahrung (S4 = „ja, aktuell“ oder „ja, früher“), eine für Personen ohne. Bei 10 bzw. 20 Personen erhält jeder Block eine erfahrene und zwei weitere Bewertende. So ballen sich die Erfahrenen nicht in einzelnen Blöcken, und der Untergruppenvergleich (DEMI Tabelle 15) ist nicht mit den Blöcken vermengt. Die technische Umsetzung, die Zählung nur vollständiger Fragebögen und der Umgang mit mehr als 30 Teilnehmenden werden mit der SoSci-Umsetzung festgelegt.

### U-06 Umfragetool (geplant)

SoSci Survey. Anforderungen aus E-11: ausgewogene Zuteilung auf 10 Blöcke, Randomisierung je Person, Screening-Item S4, Einwilligung, Server in der EU. Die Erfüllung wird bei der Umsetzung anhand der SoSci-Dokumentation geprüft.

## Nächste Schritte

1. SoSci-Umsetzung: Seiten nach `FRAGEBOGEN.md`, Entwürfe aus `entwuerfe.csv`, Urnen (U-05), Randomisierung, Speicherung der Entwurfs-ID je Position
2. Platzhalter in `FRAGEBOGEN.md` ersetzen und Datenschutzangaben prüfen
3. Pretest mit 2–3 Personen (Dauer, Verständlichkeit); Pretest-Daten werden nicht ausgewertet
4. Fragebogen einfrieren (Tag `umfrage-v1.0`), dann Feldstart
