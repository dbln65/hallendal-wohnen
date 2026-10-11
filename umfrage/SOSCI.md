# Aufbau der Befragung in SoSci Survey

Schritt-für-Schritt-Anleitung. Texte: [FRAGEBOGEN.md](FRAGEBOGEN.md). Dateien zum Einfügen: `sosci/`, erzeugt mit `python umfrage/export_sosci.py`. Entscheidungen: [README.md](README.md), U-05 bis U-07.

Die Menünamen folgen der SoSci-Hilfe (englisch: *Special Features*, *List of Questions*, *Compile Questionnaire*). In der deutschen Oberfläche können sie leicht abweichen.

## Überblick

| Seite | Kennung | Inhalt |
| --- | --- | --- |
| 1 | `IN` | Text Begrüßung und Aufklärung |
| 2 | `EW` | Einwilligung `EW01` |
| 3 | `SC` | Screening S4 `SD04` |
| 4 | `IS` | PHP `php_zuteilung.txt`, Text Instruktion, PHP `php_anker.txt` |
| 5 | `UE` | PHP `php_uebung.txt` |
| 6 | `BW` | PHP `php_bewertung.txt` (eine Seite, 12-mal wiederholt) |
| 7 | `SD` | `SD01`, `SD02`, `SD03`, `SD05` |
| 8 | letzte Seite | Text Abschluss |

Die Fragen `BW01`–`BW03` und `IV01`–`IV04` werden **nicht** auf Seiten gezogen. Der PHP-Code ruft sie auf bzw. schreibt in sie.

## 1 Projekt anlegen

1. Konto auf soscisurvey.de anlegen, neues Projekt erstellen. Den Projekttitel neutral halten, z. B. „Antwortentwürfe im Kundenservice“ (er kann für Teilnehmende sichtbar sein).
2. Beim Aktivieren der Befragung die kostenlose wissenschaftliche Nutzung angeben (Bachelorarbeit, ohne Firmenbezug).

## 2 Inhaltsdatenbank importieren

*Special Features → Content Database → Import Data*: `sosci/inhalte.csv` hochladen.

Prüfen: 122 Einträge (`E001`–`E120`, `UEB`, `ANKER`), Umlaute und „€“ korrekt. Die Datei hat keine Kopfzeile, die erste Spalte ist der Schlüssel.

Hinweis aus der SoSci-Hilfe: Die Inhaltsdatenbank wird beim Projektexport nicht mit exportiert und beim Archivieren gelöscht. Maßgeblich ist deshalb `sosci/inhalte.csv` im Repo.

## 3 Urnen anlegen

*Special Features → Randomization using Urns → Create new urn*, zweimal:

| Name | Lose |
| --- | --- |
| `mit_ks` | Inhalt von `sosci/urne.txt` (1 bis 10, je eine Zeile) |
| `ohne_ks` | Inhalt von `sosci/urne.txt` |

## 4 Fragen anlegen

In der Fragenliste die Rubriken mit genau diesen Kennungen anlegen. Fragen **in dieser Reihenfolge** erstellen, damit die Nummern stimmen, und danach jede Kennung prüfen.

### Rubrik `EW` (Einwilligung)

| Frage | Typ | Inhalt |
| --- | --- | --- |
| `EW01` | Mehrfachauswahl | eine Option: Text der Einwilligung aus FRAGEBOGEN.md, Seite 2; *Checking the answers*: Mindestanzahl Auswahlen = 1 |

### Rubrik `SD` (Angaben zur Person)

Antwortoptionen per Direktimport mit festen Codes, z. B. `1=ja, aktuell`.

| Frage | Typ | Fragetext | Optionen (Code=Text) | Pflicht |
| --- | --- | --- | --- | --- |
| `SD01` | Auswahl | Altersgruppe | 1=unter 20, 2=20–29, 3=30–39, 4=40–49, 5=50–59, 6=60 und älter | nein |
| `SD02` | Auswahl | Geschlecht | 1=weiblich, 2=männlich, 3=divers, 4=keine Angabe | nein |
| `SD03` | Auswahl | Höchster Bildungsabschluss | 1=kein Abschluss, 2=Schulabschluss, 3=abgeschlossene Ausbildung, 4=Bachelor, 5=Master oder höher, 6=keine Angabe | nein |
| `SD04` | Auswahl | S4 aus FRAGEBOGEN.md, Seite 3 | 1=ja, aktuell, 2=ja, früher, 3=nein | **ja** |
| `SD05` | Auswahl | S5 aus FRAGEBOGEN.md, Seite 7 | 1=täglich, 2=wöchentlich, 3=monatlich, 4=seltener, 5=nie | nein |

`SD04` muss die Codes 1–3 genau so haben: Der PHP-Code verwendet `value('SD04') == 3` für „nein“.

### Rubrik `IV` (interne Variablen)

| Frage | Typ | Items (Beschreibung) | Zweck |
| --- | --- | --- | --- |
| `IV01` | Interne Variablen | 1 Item: `urne_ohne_ks` | nur für Urne `ohne_ks` |
| `IV02` | Interne Variablen | 1 Item: `urne_mit_ks` | nur für Urne `mit_ks` |
| `IV03` | Interne Variablen | 1 Item: `block` | zugeteilter Block |
| `IV04` | Interne Variablen | 12 Items: `pos01` bis `pos12` | Entwurfs-ID je Position |

`IV01` und `IV02` dürfen laut SoSci-Hilfe nur für die Urne genutzt werden.

### Rubrik `BW` (Bewertung)

Items jeweils per Direktimport aus der Datei einfügen (ein Item je Zeile). Bei allen drei Fragen die Vollständigkeitsprüfung aktivieren (Antwort erzwingen) und keine Ausweichoption („weiß nicht“) anlegen. Fragetext: der jeweilige Itemwortlaut, er wird ausgeblendet (`show-title=no`).

| Frage | Typ | Items | Skalenpunkte und Beschriftung |
| --- | --- | --- | --- |
| `BW01` (Q1) | Skala (Text) | `sosci/items_BW01.txt` (13 Items) | 3 Punkte, alle beschriftet: wirkt falsch / wirkt teilweise korrekt (im Kern richtig, aber mit Ungenauigkeiten) / wirkt korrekt |
| `BW02` (Q2–Q5) | Skala (Text) | `sosci/items_BW02.txt` (52 Items) | 5 Punkte, nur Endpunkte: trifft überhaupt nicht zu / trifft voll und ganz zu |
| `BW03` (Q6) | Skala (Text) | `sosci/items_BW03.txt` (13 Items) | 5 Punkte, alle beschriftet: sehr schlecht / schlecht / mittelmäßig / gut / sehr gut |

Zuordnung: Position p (1–12) belegt `BW01_p`, `BW02` Items 4p−3 bis 4p (Q2, Q3, Q4, Q5) und `BW03_p`. Die Entwurfs-ID der Position steht in `IV04_p`. Item 13 bzw. Items 49–52 sind der Übungsfall und werden nicht ausgewertet.

### Texte

Drei Textelemente mit dem Wortlaut aus FRAGEBOGEN.md anlegen, Platzhalter `[…]` dabei ersetzen:

- **Begrüßung:** Seite 1
- **Instruktion:** Seite 4 von „So funktioniert die Bewertung“ bis zur Liste der sechs Fragen (die Ankerbeispiele erzeugt `php_anker.txt`)
- **Abschluss:** Seite 8

## 5 Fragebogen zusammenstellen

Seiten nach der Tabelle im Überblick anlegen. PHP-Code-Elemente: Inhalt der jeweiligen Datei vollständig einfügen. Auf Seite 4 steht `php_zuteilung.txt` ganz oben, weil die Zuteilung den Wert von S4 von der Vorseite braucht.

## 6 Testen vor dem Pretest

Im Vorschau- bzw. Testmodus mit Debug-Informationen:

- [ ] Zwei Durchläufe, einmal S4 = „nein“, einmal S4 = „ja, aktuell“. In den Debug-Informationen sind `IV01_01` bzw. `IV02_01`, `IV03_01` und `IV04_01`–`IV04_12` belegt.
- [ ] Die angezeigten 12 Entwürfe sind verschieden, und die Reihenfolge entspricht `IV04_01`–`IV04_12`.
- [ ] Ohne Haken bei der Einwilligung geht es nicht weiter.
- [ ] Auf den Bewertungsseiten erscheint bei fehlenden Antworten ein Hinweis.
- [ ] Absätze, Umlaute und „€“ werden korrekt angezeigt, auch auf dem Smartphone.
- [ ] Datensatz herunterladen: `BW01_01`–`BW01_13`, `BW02_01`–`BW02_52`, `BW03_01`–`BW03_13`, `IV03_01`, `IV04_01`–`IV04_12` sind vorhanden und sinnvoll belegt.
- [ ] In der Urnenübersicht prüfen, ob abgeschlossene Testläufe als gezogen zählen und abgebrochene nicht (Option `end`).

## 7 Vor dem Feldstart

- [ ] Pretest mit 2–3 Personen (Dauer, Verständlichkeit); Rückmeldungen in README.md festhalten
- [ ] alle Test- und Pretest-Datensätze löschen
- [ ] beide Urnen zurücksetzen oder neu anlegen, sodass keine Lose als gezogen zählen
- [ ] Befragungszeitraum setzen, Befragung aktivieren
- [ ] Projekt als XML herunterladen (*Project Settings*) und als `umfrage/sosci/projekt.xml` committen; danach Tag `umfrage-v1.0`
