# Aufbau der Befragung in Qualtrics

Schritt-für-Schritt-Anleitung. Texte: [FRAGEBOGEN.md](FRAGEBOGEN.md). Dateien zum Einfügen: `qualtrics/`, erzeugt mit `python umfrage/export_qualtrics.py`. Entscheidungen: [README.md](README.md), U-05 bis U-07.

Menünamen wie in der englischen Qualtrics-Hilfe. Funktionen, deren Verhalten die Hilfe nicht eindeutig beschreibt, sind mit **Test** markiert und werden in Abschnitt 6 geprüft.

## Überblick

```
Survey Flow
├─ Embedded Data: block
├─ Block „Begrüßung“
├─ Block „Einwilligung“
├─ Block „Screening“ (S4)
├─ Branch: S4 = „nein“        → Randomizer (1 von 10, gleichmäßig) → block = 1 … 10
├─ Branch: S4 ≠ „nein“        → Randomizer (1 von 10, gleichmäßig) → block = 1 … 10
├─ Block „Instruktion“ (mit Ankerbeispielen)
├─ Block „Übung“
├─ Branch: block = 1          → Block „Bewertung 1“  (Loop & Merge, 12 Entwürfe, Reihenfolge zufällig)
│  …
├─ Branch: block = 10         → Block „Bewertung 10“
├─ Block „Angaben zur Person“
└─ End of Survey (Abschlusstext)
```

## 0 Vorbereitung

1. Zugang über die Hochschullizenz prüfen. Die Umfrage braucht **Randomizer** im Survey Flow und **Loop & Merge**. Fehlt eine der Funktionen, bei der BHT nachfragen.
2. Bei der BHT erfragen, in welchem Rechenzentrum die Daten der Lizenz liegen (für den Datenschutztext auf Seite 1).
3. Dateien erzeugen:
   ```bash
   pip install openpyxl
   python umfrage/export_qualtrics.py
   ```

## 1 Projekt und Einstellungen

1. Neues Projekt vom Typ *Survey* anlegen, Titel neutral, z. B. „Antwortentwürfe im Kundenservice“.
2. *Survey options*:
   - **Anonymize responses** aktivieren (entfernt IP-Adresse und Standortdaten). Vor dem ersten echten Datensatz einschalten; frühere Antworten bleiben laut Hilfe unverändert.
   - Sprache der Umfrage auf Deutsch stellen, damit Schaltflächen und Hinweise deutsch sind (**Test**).
   - Zurück-Schaltfläche aus lassen (wichtig wegen der Zuteilung nach S4).

## 2 Blöcke und Fragen

Fragen nach dem Anlegen umbenennen (Klick auf die Fragenummer). Die Namen erscheinen im Datenexport.

### Block „Begrüßung“

| Name | Typ | Inhalt |
| --- | --- | --- |
| `INTRO` | Text / Graphic | FRAGEBOGEN.md, Seite 1 (Platzhalter ersetzen) |

### Block „Einwilligung“

| Name | Typ | Inhalt | Einstellung |
| --- | --- | --- | --- |
| `EW` | Multiple choice, *Multiple answer* | Frage: leer oder „Einwilligung“; eine Antwortoption: Einwilligungstext aus Seite 2; darunter der Hinweis zum Schließen des Fensters | **Force Response** |

### Block „Screening“

| Name | Typ | Inhalt | Einstellung |
| --- | --- | --- | --- |
| `S4` | Multiple choice, *Single answer* | Frage S4 aus Seite 3; Optionen: ja, aktuell / ja, früher / nein | **Force Response**; *Recode values* 1, 2, 3 |

### Block „Instruktion“

| Name | Typ | Inhalt |
| --- | --- | --- |
| `INSTR` | Text / Graphic | Seite 4 von „So funktioniert die Bewertung“ bis zur Liste der sechs Fragen |
| `ANKER` | Text / Graphic | Inhalt von `qualtrics/anker.html` im HTML-Modus des Editors einfügen |

### Block „Übung“

| Name | Typ | Inhalt | Einstellung |
| --- | --- | --- | --- |
| `UE_TEXT` | Text / Graphic | `qualtrics/uebung.html` im HTML-Modus | – |
| `UE_Q1` | Multiple choice, *Single answer*, horizontal | Q1; Optionen: wirkt falsch / wirkt teilweise korrekt (im Kern richtig, aber mit Ungenauigkeiten) / wirkt korrekt | Force Response; Recode 1–3 |
| `UE_Q2_5` | Matrix table, Likert, *Single answer* | Aussagen Q2, Q3, Q4, Q5; Spalten: „1 – trifft überhaupt nicht zu“, „2“, „3“, „4“, „5 – trifft voll und ganz zu“ | Force Response; Recode 1–5 |
| `UE_Q6` | Multiple choice, *Single answer*, horizontal | Q6; Optionen: sehr schlecht / schlecht / mittelmäßig / gut / sehr gut | Force Response; Recode 1–5 |
| `UE_HINWEIS` | Text / Graphic | „Nach dem Klick auf Weiter beginnen die 12 Antwortentwürfe.“ | – |

Wortlaut von Q1–Q6 exakt aus FRAGEBOGEN.md, Seite 6. Alle fünf Elemente in dieser Reihenfolge auf einer Seite, ohne Seitenumbruch.

### Block „Bewertung 1“

1. Gleicher Aufbau wie „Übung“, aber mit eigenem Textelement und ohne `UE_HINWEIS`:

   | Name | Typ | Inhalt |
   | --- | --- | --- |
   | `B1_TEXT` | Text / Graphic | `qualtrics/bewertung_text.html` im HTML-Modus |
   | `B1_Q1`, `B1_Q2_5`, `B1_Q6` | wie `UE_Q1`, `UE_Q2_5`, `UE_Q6` | – |

2. *Block options* → **Loop & Merge** einschalten. Felder hinzufügen, bis es **3 Fields** sind.
3. `qualtrics/loop_merge.xlsx` öffnen, Blatt „Block 1“, Zellen **A1:C12** markieren und kopieren. In Loop & Merge in die erste Zelle (Zeile 1, Field 1) klicken und einfügen.
4. Prüfen: genau 12 Zeilen; Field 1 enthält die Entwurfs-IDs aus dem Blatt (z. B. E005); Field 2 und 3 enthalten HTML-Text.
5. **Randomize loop order** anhaken. *Present only … of total loops* **nicht** setzen. Speichern.
6. Piped Text prüfen: In `B1_TEXT` über *Piped Text → Loop & Merge → Loop & Merge Fields* Field 2 einfügen. Der erzeugte Code muss `${lm://Field/2}` lauten wie in der eingefügten HTML-Datei, sonst beide Platzhalter durch den erzeugten Code ersetzen.

### Blöcke „Bewertung 2“ bis „Bewertung 10“

Für k = 2 bis 10:

1. *Block options* → **Copy** an „Bewertung 1“, Kopie in „Bewertung k“ umbenennen.
2. Fragen umbenennen: `Bk_TEXT`, `Bk_Q1`, `Bk_Q2_5`, `Bk_Q6`.
3. Loop & Merge öffnen (die Hilfe sagt nicht, ob die Einstellungen mitkopiert werden: **Test**). Daten aus Blatt „Block k“ (A1:C12) einfügen, sodass genau diese 12 Zeilen drinstehen. **Randomize loop order** anhaken.
4. Field 1 mit dem Blatt vergleichen.

### Block „Angaben zur Person“

| Name | Typ | Optionen | Einstellung |
| --- | --- | --- | --- |
| `S1` | Multiple choice, Single answer | unter 20 / 20–29 / 30–39 / 40–49 / 50–59 / 60 und älter | freiwillig; Recode 1–6 |
| `S2` | Multiple choice, Single answer | weiblich / männlich / divers / keine Angabe | freiwillig; Recode 1–4 |
| `S3` | Multiple choice, Single answer | kein Abschluss / Schulabschluss / abgeschlossene Ausbildung / Bachelor / Master oder höher / keine Angabe | freiwillig; Recode 1–6 |
| `S5` | Multiple choice, Single answer | täglich / wöchentlich / monatlich / seltener / nie | freiwillig; Recode 1–5 |

Fragetexte aus Seite 7.

## 3 Survey Flow

*Survey flow* öffnen und den Aufbau aus dem Überblick herstellen:

1. Ganz oben *Add a New Element Here* → **Embedded Data**, Feld `block` anlegen, ohne Wert.
2. Blöcke „Begrüßung“, „Einwilligung“, „Screening“ in dieser Reihenfolge.
3. **Branch** → *Add a Condition*: Frage `S4`, Option „nein“, *Is Selected*. Darunter **Randomizer**:
   - *Randomly Present* = **1**, **Evenly Present Elements** anhaken.
   - Unter dem Randomizer 10 **Embedded Data**-Elemente: `block` = 1, `block` = 2, … `block` = 10.
4. Zweiter **Branch**: Frage `S4`, Option „nein“, *Is Not Selected*. Darunter ein zweiter Randomizer mit denselben Einstellungen und denselben 10 Embedded-Data-Elementen.
5. Blöcke „Instruktion“ und „Übung“.
6. 10 **Branches**: Bedingung *Embedded Data* `block` *Is Equal to* k, darunter Block „Bewertung k“.
7. Block „Angaben zur Person“.
8. **End of Survey** → *Customize* → *Override Survey Options* → *Custom end of survey message*: Text aus Seite 8.

Jeder Block darf im Flow nur einmal vorkommen. Neu angelegte Blöcke hängt Qualtrics unten an den Flow an; die Bewertungsblöcke müssen unter ihre Branches verschoben werden.

## 4 Optional: Zeit je Entwurf

In jeden Bewertungsblock eine Frage vom Typ **Timing** aufnehmen. Sie misst die Bearbeitungszeit je Loop und erlaubt, extrem schnelle Bearbeitungen zu erkennen. Die DEMI verlangt das nicht; die Entscheidung in README.md festhalten.

## 5 Datenexport (Aufbau)

- Jeder Loop hat eigene Spalten, z. B. `1_B3_Q1` für Loop 1 in Block 3. Die Loop-Nummer ist die **Zeile in der Loop-&-Merge-Tabelle**, nicht die angezeigte Position. Welche Entwurfs-ID zu Block und Loop gehört, steht in `qualtrics/zuordnung.csv`.
- Die Reihenfolge, in der die Loops gezeigt wurden, lässt sich laut Qualtrics-Hilfe nicht exportieren (U-07).
- Export als CSV mit numerischen Werten (Recode values).

## 6 Testen vor dem Pretest

- [ ] Vorschau zweimal durchlaufen, einmal S4 = „nein“, einmal S4 = „ja, aktuell“: Nach der Übung erscheinen 12 Entwürfe, keiner doppelt.
- [ ] Mehrere Vorschauläufe: Wird derselbe Block zugeteilt (erkennbar an den Texten), unterscheidet sich die Reihenfolge der Entwürfe.
- [ ] Ohne Haken bei der Einwilligung geht es nicht weiter; bei fehlenden Bewertungen erscheint ein Hinweis, auf Deutsch.
- [ ] Absätze, Umlaute und „€“ korrekt, auch in der Mobilansicht der Vorschau.
- [ ] *Tools → Generate test responses* mit z. B. 40 Testantworten; danach im Datenexport prüfen: `block` ist in beiden S4-Gruppen gleichmäßig verteilt, die Spalten `1_Bk_Q1` usw. sind belegt, IP-Adresse und Standort fehlen.
- [ ] Loop & Merge in allen 10 Blöcken: 12 Zeilen, richtige IDs, Randomize loop order aktiv.

## 7 Vor dem Feldstart

- [ ] Pretest mit 2–3 Personen (Dauer, Verständlichkeit); Rückmeldungen in README.md festhalten
- [ ] alle Test- und Pretest-Antworten löschen
- [ ] in beiden Randomizern *Edit Count* → **Reset All Counts**
- [ ] Umfrage veröffentlichen (*Publish*), anonymen Link für die Einladung verwenden
- [ ] Umfrage als QSF exportieren (*Tools → Import/Export → Export survey*) und als `umfrage/qualtrics/umfrage.qsf` committen, zusätzlich *Export survey to Word* als lesbare Dokumentation; danach Tag `umfrage-v1.0`

## 8 Während der Feldphase

- Einmal pro Woche vollständige Antworten je Block und S4-Gruppe zählen. Die Hilfe sagt nicht, ob abgebrochene Antworten bei *Evenly Present Elements* mitzählen. Bleibt ein Block durch Abbrüche zurück, über *Edit Count* gegensteuern (laut Hilfe dafür vorgesehen) und die Änderung mit Datum in README.md notieren.
- Feldende nach U-05.
