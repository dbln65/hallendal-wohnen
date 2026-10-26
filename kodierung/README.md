# Manuelle Kodierung (Teilstudie A, Strang 4)

Kodierung von Quellenbezug und Failure Modes für alle 240 Antwortentwürfe des Hauptlaufs `haupt-01` nach DEMI 2.5, 3.3 und Tabelle 12. Regeln für Kodierende: [LEITFADEN.md](LEITFADEN.md) und [AUSLEGUNGEN.md](AUSLEGUNGEN.md).

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/ (benötigt openpyxl)
python kodierung/prepare_coding.py                  # 1. Material für die Erstkodierung
python kodierung/pruefe_kodierung.py                # 3. Konsistenzprüfung der Erstkodierung (muss 0 Fehler melden)
python kodierung/zweitkodierung.py                  # 4. Material für die Zweitkodierung
python kodierung/pruefe_kodierung.py kodierung/zweitkodierung/kodiertabelle_zweit.xlsx   # 5. nach der Zweitkodierung
python kodierung/kappa.py                           # 6. Cohens Kappa und Liste der Abweichungen
python kodierung/konsens.py                         # 7. Konsens übernehmen, endgültiger Kodierdatensatz
```

| # | Schritt | Status |
| --- | --- | --- |
| 1 | Kodierheft, Kodiertabelle und Stichprobe der Zweitkodierung erzeugen; Leitfaden einfrieren, Tag `kodierung-v1.0` | erledigt (2026-10-16) |
| 2 | Erstkodierung aller 240 Entwürfe in `kodierung/kodiertabelle.xlsx` | erledigt (2026-10-19) |
| 3 | Konsistenzprüfung und Korrektur der Erstkodierung (K-08), Tag `kodierung-erst-v1.0` | erledigt (2026-10-19) |
| 4 | Material für die Zweitkodierung erzeugen; Einweisung der Zweitkodierperson anhand von LEITFADEN.md und AUSLEGUNGEN.md | erledigt |
| 5 | Zweitkodierung der 48 Entwürfe in `zweitkodierung/kodiertabelle_zweit.xlsx`, Konsistenzprüfung (K-10) | eingegangen 2026-10-26; Konsistenzprüfung: 10 Fehler in 8 Entwürfen, zur Korrektur an die Zweitkodierperson |
| 6 | Cohens Kappa je Code (K-06) und Liste der Abweichungen mit `kappa.py` | offen |
| 7 | Konsens bei allen Abweichungen (K-11), `konsens.py`, Tag `kodierung-final-v1.0` | offen |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `prepare_coding.py` | erzeugt Kodierheft, Kodiertabelle und Stichprobe der Zweitkodierung |
| `LEITFADEN.md` | Kodierregeln mit Definitionen, Beispielen und Mischfällen (eingefroren mit `kodierung-v1.0`) |
| `AUSLEGUNGEN.md` | Anwendung des Leitfadens auf wiederkehrende Grenzfälle, festgehalten während der Erstkodierung |
| `kodierheft.html` | Lesematerial je Entwurf in Kodierreihenfolge, KB im Anhang |
| `kodiertabelle.xlsx` | Codes der Erstkodierung; Blatt „Korrekturen“ dokumentiert die Änderungen aus der Konsistenzprüfung (K-08) |
| `stichprobe_zweitkodierung.csv` | 48 Kodier-IDs (24 RAG, 24 LLM-only), vor Beginn der Kodierung festgelegt |
| `kodier_meta.json` | Herkunft: Lauf, Hashes, Seed, Git-Stand |
| `pruefe_kodierung.py` | prüft eine Kodiertabelle auf Vollständigkeit und Regelkonsistenz (Fehler und Hinweise) |
| `zweitkodierung.py` | erzeugt `zweitkodierung/` mit Kodierheft und Tabelle für die 48 Entwürfe, Kernaussagen vorgegeben (K-06) |
| `zweitkodierung/` | Material und Codes der Zweitkodierung; enthält keine Codes der Erstkodierung |
| `kappa.py` | Cohens Kappa je Code mit prozentualer Übereinstimmung und Kreuztabellen; schreibt `kappa/` |
| `kappa/bericht.md`, `kappa/kappa.csv` | Übereinstimmung vor dem Konsens |
| `kappa/abweichungen.xlsx` | jede abweichende Codierung; Spalten „konsens“ und „begruendung“ werden im Konsens ausgefüllt |
| `konsens.py` | überträgt den Konsens auf die Erstkodierung und prüft das Ergebnis |
| `kodiertabelle_konsens.xlsx` | endgültiger Kodierdatensatz für die Auswertung von Strang 4; Blatt „Konsens“ protokolliert jede Entscheidung |

## Entscheidungen

Die DEMI legt Codes und Prüfreihenfolge fest (Tabelle 12). Die folgenden Regeln präzisieren sie und wurden vor Beginn der Kodierung festgelegt (2026-10-15; Präzisierungen in LEITFADEN.md, Abschnitte 3–7, am 2026-10-16). K-08 und K-09 betreffen den Abschluss der Erstkodierung (2026-10-19), K-10 und K-11 die Zweitkodierung und den Konsens (2026-10-26).

| Nr. | Entscheidung |
| --- | --- |
| K-01 | Fehlertypen werden nur bei einem **Mangel** vergeben: ungedeckte oder teilweise gedeckte Kernaussage, unbeantwortetes Anliegen trotz KB-Abdeckung oder Belegproblem. Ein vollständiger, korrekter Entwurf erhält keinen Fehlertyp, auch wenn ein Belegartikel nicht abgerufen wurde. Begründung: Failure Modes beschreiben Ursachen von Fehlern, nicht Abweichungen im Abruf ohne Folgen. |
| K-02 | Fehlertypen (F1–F4) und Quellenpassung werden nur für **RAG** kodiert. LLM-only hat weder Abruf noch Belege; dort werden Kernaussagen, C1 und C3 kodiert (für H3 und H4). H5 betrifft laut DEMI nur die RAG-Konfiguration. |
| K-03 | **Mischfälle** werden nach der Tabelle in LEITFADEN.md, Abschnitt 7.3, aufgelöst; die Prüfreihenfolge F1 → F2 → F3 → F4 aus DEMI 3.3 bleibt unverändert. |
| K-04 | **„Teilweise gedeckt“** zählt in der Hauptauswertung des Deckungsanteils je Entwurf als nicht gedeckt (strenge Auslegung); als Robustheitsprüfung wird zusätzlich mit 0,5 gerechnet. Entwürfe ohne Kernaussage gehen nicht in den Deckungsanteil ein (vgl. DEMI 2.3 zur KB-Supportedness). |
| K-05 | Die 240 Entwürfe werden in einer per Seed (20261015) **zufälligen Reihenfolge** kodiert, damit RAG und LLM-only desselben Tickets nicht unmittelbar nacheinander beurteilt werden und Reihenfolgeeffekte sich nicht systematisch auf eine Bedingung auswirken. Eine Verblindung der Bedingung ist nicht möglich, weil RAG-Entwürfe Belege enthalten. |
| K-06 | **Zweitkodierung:** 48 Entwürfe (20 %), je 24 RAG und LLM-only, per Seed gezogen und vor Beginn der Kodierung festgelegt. Die zweite Person erhält die Kernaussagen der Erstkodierung und kodiert C1, C2, C3, Mangel und Fehlertypen unabhängig; nur so ist Kappa für C1 und C2 auf Aussageebene berechenbar. Kappa wird je Code berichtet (C1 und C2 je Kernaussage; C3, Mangel und primärer Fehlertyp je Entwurf). |
| K-07 | Die manuelle Kodierung wird **vor** der Sichtung der automatisierten Bewertung (Strang 2) abgeschlossen, damit deren Ergebnisse die Urteile nicht beeinflussen. Manuelle Codes werden nach Einsicht in die automatisierte Bewertung nicht mehr geändert. Ergebnisse der Online-Befragung werden während der Kodierung ebenfalls nicht ausgewertet. |
| K-08 | **Konsistenzprüfung:** Nach Abschluss der Erstkodierung wird die Tabelle mit `pruefe_kodierung.py` auf fehlende Einträge und Widersprüche zwischen den Codes geprüft (z. B. Belegproblem ohne F4, Mangel ohne Fehlertyp). Korrigiert werden Eingabefehler und Abweichungen von LEITFADEN.md und AUSLEGUNGEN.md, jeweils vor Erzeugung des Materials für die Zweitkodierung und vor Sichtung von Strang 2. Jede Änderung steht im Blatt „Korrekturen“ der Kodiertabelle. Eine inhaltliche Neubewertung bereits kodierter Entwürfe findet nicht statt. |
| K-09 | **Auslegungsregeln:** Wiederkehrende Grenzfälle wurden während der Erstkodierung einheitlich entschieden und in AUSLEGUNGEN.md festgehalten. Sie ändern keine Codes oder Definitionen des Leitfadens. Die Zweitkodierperson erhält sie mit dem Leitfaden in der Einweisung, damit beide Personen dieselben Regeln anwenden. |
| K-10 | **Konsistenzprüfung der Zweitkodierung:** dieselbe Prüfung wie in K-08 mit `pruefe_kodierung.py`. Fehler (fehlende Codes, Widersprüche zwischen den Codes eines Entwurfs) behebt die Zweitkodierperson selbst, ohne Kenntnis der Erstkodierung; die Hinweise prüft sie ebenfalls selbst. Die eingegangene Fassung wird vor der Korrektur unverändert committet, sodass jede Änderung im Git-Verlauf nachvollziehbar ist. Kappa wird auf der korrigierten Fassung berechnet. |
| K-11 | **Konsens:** `kappa.py` listet jede abweichende Codierung in `kappa/abweichungen.xlsx`, einschließlich F_weitere, das nicht in Kappa eingeht. Beide Kodierpersonen besprechen jede Abweichung anhand des Kodierhefts, LEITFADEN.md und AUSLEGUNGEN.md und halten den vereinbarten Code mit Begründung fest. Erfordert ein Konsens Folgeänderungen an anderen Codes desselben Entwurfs, werden sie ebenfalls mit Begründung eingetragen. `konsens.py` überträgt die Entscheidungen auf die Erstkodierung; das Ergebnis muss `pruefe_kodierung.py` ohne Fehler bestehen. Kappa wird für die Codes vor dem Konsens berichtet. Grundlage der Auswertung von Strang 4 ist `kodiertabelle_konsens.xlsx`: Konsenscodes für die 48 doppelt kodierten Entwürfe, Erstkodierung für die übrigen 192. Der Konsens wird vor der Sichtung von Strang 2 und 3 abgeschlossen (K-07). Interpretation von Kappa nach Landis und Koch (1977), Konfidenzintervall nach der Näherung von Cohen (1960); wegen der kleinen Fallzahlen wird die prozentuale Übereinstimmung mit berichtet. |

## Für die Verschriftlichung: Limitationen der Kodierung

- **Fehlurteile der Kodierperson** (übersehene oder falsch beurteilte Kernaussagen) sind möglich. Sie werden durch den festgeschriebenen Leitfaden und die Zweitkodierung mit Cohens Kappa begrenzt, nicht ausgeschlossen.
- **Kappa erfasst nicht die Auswahl der Kernaussagen.** Weil die Zweitkodierperson die Kernaussagen der Erstkodierung erhält (K-06), misst Kappa die Übereinstimmung der Urteile, nicht der Auswahl. Eine übersehene Kernaussage fällt dadurch nicht auf.
- **80 % der Entwürfe sind einfach kodiert.**
- **Keine Verblindung:** Die Erstkodierperson kennt die Hypothesen und erkennt die Bedingung an den Belegen (K-05).
- **Auslegungen entstanden während der Kodierung (K-09):** Entwürfe, die vor einer Auslegung kodiert wurden, können davon abweichen. Die Konsistenzprüfung (K-08) erfasst nur formal erkennbare Abweichungen.
- **Retrieval-Lücken ohne Folgen bleiben in F2 unsichtbar:** Während der Kodierung fiel mehrfach auf, dass ein Belegartikel laut Ticket nicht übergeben wurde, die übrigen Auszüge die Anfrage aber vollständig beantworteten. Nach K-01 ist das kein Mangel. F2 erfasst daher nur Retrieval-Fehler mit Folgen; die Trefferquote des Retrievals (Belegartikel unter den Top-3) wird ergänzend automatisch aus den Protokollen berichtet.
- **Automatisierte Bewertung als unabhängiger zweiter Zugang:** Die Übereinstimmung von C1 und KB-Supportedness wird deskriptiv berichtet (DEMI 2.3). Abweichungen zeigen nicht, welcher Zugang zutrifft, und führen nicht zur nachträglichen Änderung der manuellen Codes (K-07).
