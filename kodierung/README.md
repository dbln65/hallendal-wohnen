# Manuelle Kodierung (Teilstudie A, Strang 4)

Kodierung von Quellenbezug und Failure Modes für alle 240 Antwortentwürfe des Hauptlaufs `haupt-01` nach DEMI 2.5, 3.3 und Tabelle 12. Regeln für Kodierende: [LEITFADEN.md](LEITFADEN.md).

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/ (benötigt openpyxl)
python kodierung/prepare_coding.py
```

| # | Schritt | Status |
| --- | --- | --- |
| 1 | Kodierheft, Kodiertabelle und Stichprobe der Zweitkodierung erzeugen; Leitfaden einfrieren, Tag `kodierung-v1.0` | offen |
| 2 | Erstkodierung aller 240 Entwürfe in `kodierung/kodiertabelle.xlsx` | offen |
| 3 | Einweisung der Zweitkodierperson anhand des Leitfadens, danach Zweitkodierung der 48 Entwürfe aus `stichprobe_zweitkodierung.csv` | offen |
| 4 | Cohens Kappa, Konsens bei Abweichungen | offen |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `prepare_coding.py` | erzeugt Kodierheft, Kodiertabelle und Stichprobe der Zweitkodierung |
| `LEITFADEN.md` | Kodierregeln mit Definitionen, Beispielen und Mischfällen |
| `kodierheft.html` | Lesematerial je Entwurf in Kodierreihenfolge, KB im Anhang |
| `kodiertabelle.xlsx` | Eingabe der Codes (Erstkodierung) |
| `stichprobe_zweitkodierung.csv` | 48 Kodier-IDs (24 RAG, 24 LLM-only), vor Beginn der Kodierung festgelegt |
| `kodier_meta.json` | Herkunft: Lauf, Hashes, Seed, Git-Stand |

## Entscheidungen

Die DEMI legt Codes und Prüfreihenfolge fest (Tabelle 12). Die folgenden Regeln präzisieren sie und wurden vor Beginn der Kodierung festgelegt (2026-10-15; Präzisierungen in LEITFADEN.md, Abschnitte 3–7, am 2026-10-16).

| Nr. | Entscheidung |
| --- | --- |
| K-01 | Fehlertypen werden nur bei einem **Mangel** vergeben: ungedeckte oder teilweise gedeckte Kernaussage, unbeantwortetes Anliegen trotz KB-Abdeckung oder Belegproblem. Ein vollständiger, korrekter Entwurf erhält keinen Fehlertyp, auch wenn ein Belegartikel nicht abgerufen wurde. Begründung: Failure Modes beschreiben Ursachen von Fehlern, nicht Abweichungen im Abruf ohne Folgen. |
| K-02 | Fehlertypen (F1–F4) und Quellenpassung werden nur für **RAG** kodiert. LLM-only hat weder Abruf noch Belege; dort werden Kernaussagen, C1 und C3 kodiert (für H3 und H4). H5 betrifft laut DEMI nur die RAG-Konfiguration. |
| K-03 | **Mischfälle** werden nach der Tabelle in LEITFADEN.md, Abschnitt 7.3, aufgelöst; die Prüfreihenfolge F1 → F2 → F3 → F4 aus DEMI 3.3 bleibt unverändert. |
| K-04 | **„Teilweise gedeckt“** zählt in der Hauptauswertung des Deckungsanteils je Entwurf als nicht gedeckt (strenge Auslegung); als Robustheitsprüfung wird zusätzlich mit 0,5 gerechnet. Entwürfe ohne Kernaussage gehen nicht in den Deckungsanteil ein (vgl. DEMI 2.3 zur KB-Supportedness). |
| K-05 | Die 240 Entwürfe werden in einer per Seed (20261015) **zufälligen Reihenfolge** kodiert, damit RAG und LLM-only desselben Tickets nicht unmittelbar nacheinander beurteilt werden und Reihenfolgeeffekte sich nicht systematisch auf eine Bedingung auswirken. Eine Verblindung der Bedingung ist nicht möglich, weil RAG-Entwürfe Belege enthalten. |
| K-06 | **Zweitkodierung:** 48 Entwürfe (20 %), je 24 RAG und LLM-only, per Seed gezogen und vor Beginn der Kodierung festgelegt. Die zweite Person erhält die Kernaussagen der Erstkodierung und kodiert C1, C2, C3, Mangel und Fehlertypen unabhängig; nur so ist Kappa für C1 und C2 auf Aussageebene berechenbar. Kappa wird je Code berichtet (C1 und C2 je Kernaussage; C3, Mangel und primärer Fehlertyp je Entwurf). |
| K-07 | Die manuelle Kodierung wird **vor** der Sichtung der automatisierten Bewertung (Strang 2) abgeschlossen, damit deren Ergebnisse die Urteile nicht beeinflussen. Manuelle Codes werden nach Einsicht in die automatisierte Bewertung nicht mehr geändert. Ergebnisse der Online-Befragung werden während der Kodierung ebenfalls nicht ausgewertet. |

## Für die Verschriftlichung: Limitationen der Kodierung

- **Fehlurteile der Kodierperson** (übersehene oder falsch beurteilte Kernaussagen) sind möglich. Sie werden durch den festgeschriebenen Leitfaden und die Zweitkodierung mit Cohens Kappa begrenzt, nicht ausgeschlossen.
- **Kappa erfasst nicht die Auswahl der Kernaussagen.** Weil die Zweitkodierperson die Kernaussagen der Erstkodierung erhält (K-06), misst Kappa die Übereinstimmung der Urteile, nicht der Auswahl. Eine übersehene Kernaussage fällt dadurch nicht auf.
- **80 % der Entwürfe sind einfach kodiert.**
- **Keine Verblindung:** Die Erstkodierperson kennt die Hypothesen und erkennt die Bedingung an den Belegen (K-05).
- **Automatisierte Bewertung als unabhängiger zweiter Zugang:** Die Übereinstimmung von C1 und KB-Supportedness wird deskriptiv berichtet (DEMI 2.3). Abweichungen zeigen nicht, welcher Zugang zutrifft, und führen nicht zur nachträglichen Änderung der manuellen Codes (K-07).
