# Online-Befragung (Teilstudie A, Strang 3)

Vorbereitung der verblindeten Online-Befragung nach DEMI 1.4.3, 1.4.4, 2.4 und Tabelle 9–11. Grundlage ist der Hauptlauf `haupt-01` (Tag `run-haupt-01`) und die Teilstichprobe der 60 Tickets mit `human_rating = ja` in `tickets_plan.csv`.

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/
python umfrage/prepare_survey.py     # 1. Entwürfe verblinden, Blöcke bilden
python umfrage/export_sosci.py       # 2. Dateien für SoSci erzeugen (umfrage/sosci/)
```

`prepare_survey.py` liest den Hauptlauf, entfernt die Belege, prüft die Texte, bildet die 10 Blöcke und vergibt pseudonyme Entwurfs-IDs. Es bricht mit einer Fehlerliste ab, wenn eine Prüfung scheitert. Bei gleichen Eingaben entstehen immer dieselben Dateien (fester Seed).

`export_sosci.py` erzeugt daraus die Inhaltsdatenbank, den PHP-Code und die Item-Listen für SoSci. Es prüft vorher, dass Ankerbeispiele, Übungsfall und Items wörtlich in `FRAGEBOGEN.md` stehen. Den Aufbau in SoSci beschreibt [SOSCI.md](SOSCI.md).

## Dateien

| Datei | Inhalt | ins Umfragetool? |
| --- | --- | --- |
| `prepare_survey.py` | Export, Prüfungen, Blockbildung | nein |
| `entwuerfe.csv` | `entwurf_id`, `block`, `ticket_text`, `antwort` (ohne Belege) | ja |
| `schluessel.csv` | `entwurf_id` → Ticket, Bedingung, Kategorie, Schwierigkeit, KB-Abdeckung, Wörter | **nein**, nur Auswertung |
| `blockbericht.txt` | Prüfergebnis, Verteilung je Block, Länge, Bereinigung | nein |
| `survey_meta.json` | Herkunft: Lauf, Hashes der Eingaben und Ausgaben, Seed, Git-Stand | nein |
| `FRAGEBOGEN.md` | Wortlaut aller Seiten, Ankerbeispiele, Übungsfall, Einladungstexte | ja (Texte) |
| `export_sosci.py` | erzeugt `sosci/` aus `entwuerfe.csv` und `tickets.jsonl` | nein |
| `SOSCI.md` | Anleitung für den Aufbau in SoSci, Testcheckliste | nein |
| `sosci/inhalte.csv` | Inhaltsdatenbank: 120 Entwürfe, Übungsfall, Anker als HTML | ja |
| `sosci/php_*.txt` | PHP-Code für Zuteilung, Anker, Übung, Bewertung | ja |
| `sosci/items_BW0*.txt`, `sosci/urne.txt` | Items für Q1–Q6, Lose der Urnen | ja |

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
| U-05 | 2026-10-10 | Blockzuteilung geschichtet nach S4, Feldende | fest |
| U-06 | 2026-10-10 | Umfragetool SoSci Survey (löst E-11) | fest |
| U-07 | 2026-10-10 | Technische Umsetzung in SoSci | fest |

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

### U-05 Blockzuteilung nach S4 und Feldende

Zwei Urnen mit den Blöcken 1–10: `mit_ks` für Personen mit Kundenservice-Erfahrung (S4 = „ja, aktuell“ oder „ja, früher“), `ohne_ks` für Personen ohne. Bei 10 bzw. 20 Personen erhält jeder Block eine erfahrene und zwei weitere Bewertende. So ballen sich die Erfahrenen nicht in einzelnen Blöcken, und der Untergruppenvergleich (DEMI Tabelle 15) ist nicht mit den Blöcken vermengt.

- Ein Los gilt erst als gezogen, wenn die Person die letzte Seite erreicht (`urnDraw(…, 'end')`). Abbrüche hinterlassen so keine Lücke in einem Block. Wer gleichzeitig startet, kann denselben Block erhalten; das gleicht sich über die Feldphase aus.
- Ist eine Urne leer, füllt SoSci sie neu (Standardverhalten). Weitere Teilnehmende werden also wieder gleichmäßig verteilt.
- **Feldende:** sobald jeder Block mindestens 3 vollständige Bewertungen hat und mindestens 10 Bewertende mit Kundenservice-Erfahrung teilgenommen haben. Alle vollständigen Datensätze gehen in die Auswertung; das gemischte Modell der ICC-Schätzung (DEMI 2.4) erlaubt ungleich viele Urteile je Entwurf. Andernfalls gilt die Panel-Regel aus DEMI 1.4.3 (nach 4 Wochen).

### U-06 Umfragetool

SoSci Survey. Die Anforderungen aus E-11 sind laut SoSci-Dokumentation erfüllt: Urnen für gleich große Gruppen, zufällige Reihenfolge per PHP mit Speicherung, Pflichtantworten, Server in München, IP-Adressen und Cookies standardmäßig nicht gespeichert, kostenlos für Abschlussarbeiten ohne Firmenbezug (nur anonyme Befragungen). Verworfen wurde MS Forms: keine Zufallszuteilung auf Blöcke, und das Mischen der Fragen ist abgeschaltet, sobald ein Formular Abschnitte enthält.

### U-07 Technische Umsetzung in SoSci

- **Texte der Entwürfe:** in der Inhaltsdatenbank statt 120 einzelner Textelemente, wie im Beispiel der SoSci-Hilfe (Urne, `dbGet()`, `html()`). Zeilenumbrüche sind dort nicht erlaubt, deshalb werden Absätze als HTML gespeichert.
- **Items je Position statt Kopien der Fragen:** `BW01` (Q1) und `BW03` (Q6) haben je 13 Items, `BW02` (Q2–Q5) hat 52 Items; Position p zeigt per `question()` nur ihre Items. So hat jede Position eigene Variablen, ohne 36 Fragen anzulegen. Q1 und Q6 sind dafür als Skala mit vollständig beschrifteten Punkten umgesetzt; Wortlaut und Stufen entsprechen DEMI Tabelle 10.
- **Reihenfolge:** `shuffle()` mischt die 12 Entwürfe des Blocks je Person; `put()` speichert die Entwurfs-ID je Position in `IV04_01`–`IV04_12`, `IV03_01` speichert den Block. Eine Seite wird mit `loopPage(12)` wiederholt. Folge: SoSci erfasst nur die Gesamtzeit dieser Seite, nicht die Zeit je Entwurf.
- **Einwilligung:** Pflichtauswahl; ohne Haken geht es nicht weiter (DEMI Tabelle 9: „ohne Bestätigung kein Zugang“).
- **Pflichtangaben:** S4 und alle Bewertungsitems; S1–S3 und S5 freiwillig.
- **Prüfung:** Der PHP-Code wurde mit nachgebildeten SoSci-Funktionen auf Syntax und Logik getestet (Blockzuteilung, 12 verschiedene Entwürfe, gespeicherte = angezeigte Reihenfolge, Item-Zuordnung). Das Verhalten in SoSci selbst prüft die Checkliste in SOSCI.md.

## Nächste Schritte

1. Aufbau in SoSci nach [SOSCI.md](SOSCI.md), Platzhalter ersetzen, Datenschutzangaben prüfen
2. Testcheckliste (SOSCI.md, Abschnitt 6)
3. Pretest mit 2–3 Personen (Dauer, Verständlichkeit); Pretest-Daten werden nicht ausgewertet
4. Testdaten löschen, Urnen zurücksetzen, Projekt-XML sichern, Tag `umfrage-v1.0`, Feldstart
