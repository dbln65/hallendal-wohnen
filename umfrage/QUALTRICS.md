# Aufbau der Befragung in Qualtrics

Dokumentation des tatsächlichen Aufbaus (Stand nach Pretest, 2026-10-15). Texte: [FRAGEBOGEN.md](FRAGEBOGEN.md). Dateien zum Einfügen: `qualtrics/`, erzeugt mit `python umfrage/export_qualtrics.py`. Entscheidungen: [README.md](README.md), U-05 bis U-08.

Menünamen wie in der englischen Qualtrics-Oberfläche.

## Überblick

```
Survey Flow
├─ Embedded Data: block (ohne Wert)
├─ Block „Begrüßung“            INTRO
├─ Block „Einwilligung“         EW
├─ Block „Screening“            S4
├─ Branch: S4 „nein“ Is Selected      → Randomizer (1, Evenly Present) → block = 1 … 10
├─ Branch: S4 „nein“ Is Not Selected  → Randomizer (1, Evenly Present) → block = 1 … 10
├─ Block „Instruktion“          INSTR (Instruktion und Ankerbeispiele)
├─ Block „Übung“                UE_TEXT, UE_Q1, UE_Q2_5, UE_Q6, UE_HINWEIS
├─ Branch: block = 1   → Block „Bewertung 1“   (Loop & Merge, 12 Loops, Randomize loop order)
│  …
├─ Branch: block = 10  → Block „Bewertung 10“
├─ Block „Angaben zur Person“   SD_INTRO, S1, S2, S3, S5, FEEDBACK
└─ End of Survey (Survey Complete, eigener Abschlusstext)
```

## 1 Einstellungen

| Einstellung | Wert |
| --- | --- |
| Anonymize responses | an (keine IP-Adresse, kein Standort im Export) |
| Sprache | Deutsch |
| Zurück-Schaltfläche | aus |
| Fortschrittsbalken | an (U-08) |
| HTML | nur `<p>`, `<strong>`, `<br>`; andere Tags lehnt die Lizenz ab (U-07) |

## 2 Blöcke und Fragen

| Block | Element | Typ | Inhalt und Einstellung |
| --- | --- | --- | --- |
| Begrüßung | `INTRO` | Text / Graphic | Seite 1 als HTML |
| Einwilligung | `EW` | Multiple choice, Multiple answer, 1 Option | Einwilligungstext; Force response |
| Screening | `S4` | Multiple choice, Single answer | ja, aktuell / ja, früher / nein; Force response; Recode 1–3 |
| Instruktion | `INSTR` | Text / Graphic | Seite 4 mit beiden Ankerbeispielen in einem Element |
| Übung | `UE_TEXT` | Text / Graphic | Übungsfall P-05 (`qualtrics/uebung.html`) |
| | `UE_Q1` | Multiple choice, Single answer | Q1, 3 Optionen; Force response; Recode 1–3 |
| | `UE_Q2_5` | Matrix table, Likert | Einleitung „Inwieweit treffen die folgenden Aussagen auf die Antwort zu?“, Q2–Q5 als Zeilen, Spalten „1 – trifft überhaupt nicht zu“, „2“, „3“, „4“, „5 – trifft voll und ganz zu“; Force response; Recode 1–5 |
| | `UE_Q6` | Multiple choice, Single answer | Q6, 5 Optionen; Force response; Recode 1–5 |
| | `UE_HINWEIS` | Text / Graphic | „Nach dem Klick auf Weiter beginnen die 12 Antwortentwürfe.“ |
| Bewertung k | `Bk_TEXT` | Text / Graphic | `qualtrics/bewertung_text.html`: Kundenanfrage `${lm://Field/2}`, Antwort `${lm://Field/3}` |
| | `Bk_Q1`, `Bk_Q2_5`, `Bk_Q6` | wie in der Übung | Kopie von „Übung“ bzw. „Bewertung 1“ |
| Angaben zur Person | `SD_INTRO` | Text / Graphic | „Zum Schluss bitten wir Sie um einige Angaben zu Ihrer Person.“ |
| | `S1`, `S2`, `S3`, `S5` | Multiple choice, Single answer | Optionen nach Seite 7; freiwillig; Recode ab 1 |
| | `FEEDBACK` | Text entry, mehrzeilig | „Haben Sie Anmerkungen zur Befragung? (optional, bitte keine persönlichen Angaben)“; freiwillig (U-08) |

Alle Elemente eines Blocks stehen auf einer Seite, ohne Page Break.

## 3 Loop & Merge in den Bewertungsblöcken

1. „Bewertung 1“ entstand als Kopie von „Übung“ (*Block options → Copy*), danach `UE_HINWEIS` gelöscht und das Textelement ersetzt.
2. *Block options → Loop & Merge*: 3 Fields; aus `qualtrics/loop_merge.xlsx`, Blatt „Block k“, die Zellen A1:C12 kopieren und in die erste Zelle einfügen; **Randomize loop order** an, *Present only …* leer.
3. „Bewertung 2“ bis „Bewertung 10“: Kopie von „Bewertung 1“, Loop & Merge mit dem jeweiligen Blatt überschrieben, Fragen umbenannt.

Kontrolle: Im Export steht in der zweiten Kopfzeile jeder Bewertungsspalte die Entwurfs-ID; `import_qualtrics.py` gleicht alle 720 Spalten mit `qualtrics/zuordnung.csv` ab.

## 4 Survey Flow

1. Ganz oben *Embedded Data* `block` ohne Wert („Value will be set from Panel or URL“).
2. Nach „Screening“ zwei Branches auf `S4` = „nein“ (*Is Selected* / *Is Not Selected*), darunter je ein **Randomizer**: *Randomly present* 1, **Evenly Present Elements**, darunter 10 *Embedded Data*-Elemente `block` = 1 bis 10.
3. Nach „Übung“ 10 Branches auf gleicher Ebene: *Embedded Data* `block` *Is Equal to* k, darin nur Block „Bewertung k“.
4. *End of Survey*: *Customize* → *Override Survey Options* → *Custom end of survey message* (Seite 8); Markierung **Survey Complete**.

## 5 Datenexport

*Data & Analysis → Export & Import → Export Data* → CSV:

- Download all fields: an
- Export values: an (Recode-Werte)
- Recode seen but unanswered questions as -99: an
- Use internal IDs in header: aus

Danach `python umfrage/import_qualtrics.py <export.csv>` (ohne `--alle` nur Antworten über den anonymen Link). Spaltenaufbau: `<Loop>_B<Block>_Q1`, `_Q2_5_<1–4>` (in Block 1 `_Q2_<1–4>`), `_Q6`; die Loop-Nummer ist die Zeile der Loop-&-Merge-Tabelle. Die gezeigte Reihenfolge der Loops lässt sich nicht exportieren (U-07).

## 6 Durchgeführte Tests

| Test | Datum | Ergebnis |
| --- | --- | --- |
| Preview-Durchlauf | 2026-10-12 | alle Seiten, Pflichtantworten, Abschlusstext; Block 8 über „nein“ zugeteilt; Export ohne IP und Standort |
| 60 erzeugte Testantworten (*Tools → Generate test responses*) | 2026-10-12 | 62 Elemente je Durchlauf; je S4-Gruppe Blöcke um höchstens 1 verschieden; 720 Bewertungen, je Person 6 RAG und 6 LLM-only |
| Pretest | 2026-10-15 | siehe U-08 |

## 7 Vor dem Feldstart

- [ ] alle Antworten gelöscht (Preview, Test, Pretest)
- [ ] in beiden Randomizern *Edit Count* → **Reset All Counts**
- [ ] *Publish*; anonymer Link für die Einladungstexte
- [ ] QSF (*Tools → Import/Export → Export survey*) und Word-Export als `umfrage/qualtrics/umfrage.qsf` bzw. `.docx` committen, Tag `umfrage-v1.0`

## 8 Während der Feldphase

- Wöchentlich exportieren und `import_qualtrics.py` laufen lassen; `daten/feldstand.txt` zeigt vollständige Antworten je Block und S4-Gruppe.
- Bleibt ein Block durch Abbrüche zurück: *Edit Count* im betroffenen Randomizer anpassen, Änderung mit Datum in README.md (U-05) notieren.
- Feldende nach U-05.
