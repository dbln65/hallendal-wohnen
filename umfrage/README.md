# Online-Befragung (Teilstudie A, Strang 3)

Vorbereitung der verblindeten Online-Befragung nach DEMI 1.4.3, 1.4.4, 2.4 und Tabelle 9–11. Grundlage ist der Hauptlauf `haupt-01` (Tag `run-haupt-01`) und die Teilstichprobe der 60 Tickets mit `human_rating = ja` in `tickets_plan.csv`.

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/
python umfrage/prepare_survey.py     # 1. Entwürfe verblinden, Blöcke bilden
python umfrage/export_qualtrics.py   # 2. Dateien für Qualtrics erzeugen (umfrage/qualtrics/), benötigt openpyxl
python umfrage/import_qualtrics.py <export.csv>   # 3. Qualtrics-Export einlesen, Feldstand prüfen (umfrage/daten/)
```

`prepare_survey.py` liest den Hauptlauf, entfernt die Belege, prüft die Texte, bildet die 10 Blöcke und vergibt pseudonyme Entwurfs-IDs. Es bricht mit einer Fehlerliste ab, wenn eine Prüfung scheitert. Bei gleichen Eingaben entstehen immer dieselben Dateien (fester Seed).

`export_qualtrics.py` erzeugt daraus die Tabellen für Loop & Merge, die Zuordnung Block/Loop → Entwurfs-ID und die HTML-Texte für Qualtrics. Es prüft vorher, dass Ankerbeispiele, Übungsfall und Items wörtlich in `FRAGEBOGEN.md` stehen. Den Aufbau in Qualtrics beschreibt [QUALTRICS.md](QUALTRICS.md).

`import_qualtrics.py` liest den Qualtrics-Export (CSV, *Export values*) und schreibt eine Zeile je Bewertung mit Entwurf, Ticket und Bedingung. Die Entwurfs-ID jeder Spalte steht im Export selbst (Loop & Merge, Field 1) und wird mit `qualtrics/zuordnung.csv` abgeglichen. Preview- und Testantworten werden ohne `--alle` ausgeschlossen. `feldstand.txt` zeigt vollständige Antworten je Block und S4-Gruppe und ob das Feldende nach U-05 erreicht ist; das Skript dient deshalb auch der wöchentlichen Kontrolle während der Feldphase.

## Dateien

| Datei | Inhalt | ins Umfragetool? |
| --- | --- | --- |
| `prepare_survey.py` | Export, Prüfungen, Blockbildung | nein |
| `entwuerfe.csv` | `entwurf_id`, `block`, `ticket_text`, `antwort` (ohne Belege) | ja |
| `schluessel.csv` | `entwurf_id` → Ticket, Bedingung, Kategorie, Schwierigkeit, KB-Abdeckung, Wörter | **nein**, nur Auswertung |
| `blockbericht.txt` | Prüfergebnis, Verteilung je Block, Länge, Bereinigung | nein |
| `survey_meta.json` | Herkunft: Lauf, Hashes der Eingaben und Ausgaben, Seed, Git-Stand | nein |
| `FRAGEBOGEN.md` | Wortlaut aller Seiten, Ankerbeispiele, Übungsfall, Einladungstexte | ja (Texte) |
| `export_qualtrics.py` | erzeugt `qualtrics/` aus `entwuerfe.csv` und `tickets.jsonl` | nein |
| `QUALTRICS.md` | Anleitung für den Aufbau in Qualtrics, Tests, Feldphase | nein |
| `qualtrics/loop_merge.xlsx` | je Block ein Blatt mit 12 Zeilen: Entwurfs-ID, Kundenanfrage, Antwort (HTML) | ja |
| `qualtrics/bewertung_text.html`, `anker.html`, `uebung.html` | HTML-Texte für Bewertungsseite, Ankerbeispiele, Übungsfall | ja |
| `qualtrics/zuordnung.csv` | Block und Loop-Nummer → Entwurfs-ID | nein, nur Auswertung |
| `import_qualtrics.py` | liest den Qualtrics-Export, prüft ihn und erzeugt `daten/` | nein |
| `daten/bewertungen.csv` | eine Zeile je Bewertung: Person, Block, S4, Entwurf, Ticket, Bedingung, Q1–Q6 | nein, Auswertung |
| `daten/teilnehmende.csv`, `daten/feldstand.txt` | eine Zeile je Person (S1–S5, Dauer); Feldstand je Block | nein, Auswertung |

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
| U-06 | 2026-10-11 | Umfragetool Qualtrics (löst E-11; SoSci verworfen) | fest |
| U-07 | 2026-10-11 | Technische Umsetzung in Qualtrics | fest |

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

Zwei getrennte Zuteilungen auf die Blöcke 1–10: eine für Personen mit Kundenservice-Erfahrung (S4 = „ja, aktuell“ oder „ja, früher“), eine für Personen ohne. Bei 10 bzw. 20 Personen erhält jeder Block eine erfahrene und zwei weitere Bewertende. So ballen sich die Erfahrenen nicht in einzelnen Blöcken, und der Untergruppenvergleich (DEMI Tabelle 15) ist nicht mit den Blöcken vermengt.

- Umsetzung in Qualtrics: je S4-Gruppe ein Randomizer mit *Evenly Present Elements*, der die Variable `block` setzt (U-07).
- Die Qualtrics-Hilfe sagt nicht, ob abgebrochene Antworten mitzählen. Deshalb werden die vollständigen Antworten je Block wöchentlich gezählt; bleibt ein Block zurück, werden die Zähler über *Edit Count* angepasst und die Änderung mit Datum hier notiert.
- **Feldende:** sobald jeder Block mindestens 3 vollständige Bewertungen hat und mindestens 10 Bewertende mit Kundenservice-Erfahrung teilgenommen haben. Alle vollständigen Datensätze gehen in die Auswertung; das gemischte Modell der ICC-Schätzung (DEMI 2.4) erlaubt ungleich viele Urteile je Entwurf. Andernfalls gilt die Panel-Regel aus DEMI 1.4.3 (nach 4 Wochen).

### U-06 Umfragetool

Qualtrics über die Hochschullizenz. Erfüllt die Anforderungen aus E-11 laut Qualtrics-Hilfe: Randomizer mit gleichmäßiger Verteilung und zurücksetzbaren Zählern, Loop & Merge mit zufälliger Reihenfolge, Pflichtantworten, *Anonymize responses* (entfernt IP-Adresse und Standort). Rechenzentrum der Lizenz: [bei der BHT erfragen und eintragen].

Verlauf: Am 2026-10-10 war SoSci Survey vorgesehen und umgesetzt (`export_sosci.py`, `SOSCI.md`, `sosci/`). Am 2026-10-11 wurde auf Qualtrics gewechselt. Begründung: Die Bedienoberfläche von SoSci erwies sich beim Aufbau als unübersichtlich und aufwendig. Die SoSci-Dateien wurden entfernt und sind im Git-Verlauf erhalten. Verworfen wurde außerdem MS Forms: keine Zufallszuteilung auf Blöcke, und das Mischen der Fragen ist abgeschaltet, sobald ein Formular Abschnitte enthält.

### U-07 Technische Umsetzung in Qualtrics

- **Ein Bewertungsblock je Block:** 10 Qualtrics-Blöcke „Bewertung 1“ bis „Bewertung 10“; der Survey Flow zeigt per Branch nur den Block, der in `block` steht.
- **Loop & Merge:** je Block 12 Loops mit 3 Feldern (Entwurfs-ID, Kundenanfrage, Antwort). Die Texte stehen als HTML in den Feldern, weil Loop-&-Merge-Felder keine Zeilenumbrüche aufnehmen. *Randomize loop order* mischt die Reihenfolge je Person (DEMI 1.4.4).
- **Einschränkung:** Laut Qualtrics-Hilfe lässt sich die Reihenfolge, in der die Loops gezeigt wurden, nicht exportieren. Die Randomisierung findet statt, aber die Position eines Entwurfs wird nicht gespeichert. Positionseffekte sind in der DEMI nicht als Auswertung vorgesehen; die Einschränkung wird in der Arbeit genannt.
- **Datenexport:** Jeder Loop hat eigene Spalten; die Loop-Nummer entspricht der Zeile der Loop-&-Merge-Tabelle. `qualtrics/zuordnung.csv` ordnet Block und Loop der Entwurfs-ID zu.
- **Items:** Q1 und Q6 als Einfachauswahl, Q2–Q5 als Matrix mit 5 Spalten, beschriftete Endpunkte. Wortlaut und Stufen nach DEMI Tabelle 10.
- **Einwilligung:** Pflichtauswahl; ohne Haken geht es nicht weiter (DEMI Tabelle 9: „ohne Bestätigung kein Zugang“).
- **Pflichtangaben:** S4 und alle Bewertungsitems; S1–S3 und S5 freiwillig.
- **Prüfung:** Verhalten in Qualtrics nach der Checkliste in QUALTRICS.md, Abschnitt 6.

## Nächste Schritte

1. Aufbau in Qualtrics nach [QUALTRICS.md](QUALTRICS.md), Platzhalter ersetzen, Datenschutzangaben prüfen
2. Testcheckliste (QUALTRICS.md, Abschnitt 6)
3. Pretest mit 2–3 Personen (Dauer, Verständlichkeit); Pretest-Daten werden nicht ausgewertet
4. Testantworten löschen, Randomizer-Zähler zurücksetzen, QSF sichern, Tag `umfrage-v1.0`, Feldstart
