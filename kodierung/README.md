# Manuelle Kodierung (Teilstudie A, Strang 4)

Kodierung von Quellenbezug und Failure Modes für alle 240 Antwortentwürfe des Hauptlaufs `haupt-01` nach DEMI 2.5, 3.3 und Tabelle 12. Regeln für Kodierende: [LEITFADEN.md](LEITFADEN.md).

## Ablauf

```bash
# im Repo-Hauptverzeichnis, gleiche Umgebung wie rag/ (benötigt openpyxl)
python kodierung/prepare_coding.py --run pilot-03 --out kodierung/probe   # 1. Probekodierung (20 Entwürfe)
python kodierung/prepare_coding.py                                        # 2. Hauptkodierung (240 Entwürfe)
```

| # | Schritt | Status |
| --- | --- | --- |
| 1 | Probekodierung der 20 Entwürfe aus `pilot-03` durch die Erstkodierperson; geht nicht in die Auswertung ein (K-08) | offen |
| 2 | Leitfaden bei Bedarf nachschärfen und einfrieren, Tag `kodierung-v1.0` | offen |
| 3 | Erstkodierung aller 240 Entwürfe in `kodierung/kodiertabelle.xlsx` | offen |
| 4 | Einweisung der Zweitkodierperson anhand des Leitfadens, danach Zweitkodierung der 48 Entwürfe aus `stichprobe_zweitkodierung.csv` | offen |
| 5 | Cohens Kappa, Konsens bei Abweichungen | offen |

## Dateien

| Datei | Inhalt |
| --- | --- |
| `prepare_coding.py` | erzeugt Kodierheft, Kodiertabelle und Stichprobe der Zweitkodierung |
| `LEITFADEN.md` | Kodierregeln mit Definitionen, Beispielen und Mischfällen |
| `kodierheft.html` | Lesematerial je Entwurf in Kodierreihenfolge, KB im Anhang |
| `kodiertabelle.xlsx` | Eingabe der Codes (Erstkodierung) |
| `stichprobe_zweitkodierung.csv` | 48 Kodier-IDs (24 RAG, 24 LLM-only), vor Beginn der Kodierung festgelegt |
| `kodier_meta.json` | Herkunft: Lauf, Hashes, Seed, Git-Stand |
| `probe/` | dieselben Dateien für die Probekodierung (`pilot-03`, K-08) |

## Entscheidungen

Die DEMI legt Codes und Prüfreihenfolge fest (Tabelle 12). Die folgenden Regeln präzisieren sie und wurden vor Beginn der Kodierung festgelegt (2026-10-15, K-08 am 2026-10-16).

| Nr. | Entscheidung |
| --- | --- |
| K-01 | Fehlertypen werden nur bei einem **Mangel** vergeben: ungedeckte oder teilweise gedeckte Kernaussage, unbeantwortetes Anliegen trotz KB-Abdeckung oder Belegproblem. Ein vollständiger, korrekter Entwurf erhält keinen Fehlertyp, auch wenn ein Belegartikel nicht abgerufen wurde. Begründung: Failure Modes beschreiben Ursachen von Fehlern, nicht Abweichungen im Abruf ohne Folgen. |
| K-02 | Fehlertypen (F1–F4) und Quellenpassung werden nur für **RAG** kodiert. LLM-only hat weder Abruf noch Belege; dort werden Kernaussagen, C1 und C3 kodiert (für H3 und H4). H5 betrifft laut DEMI nur die RAG-Konfiguration. |
| K-03 | **Mischfälle** werden nach der Tabelle in LEITFADEN.md, Abschnitt 7.3, aufgelöst; die Prüfreihenfolge F1 → F2 → F3 → F4 aus DEMI 3.3 bleibt unverändert. |
| K-04 | **„Teilweise gedeckt“** zählt in der Hauptauswertung des Deckungsanteils je Entwurf als nicht gedeckt (strenge Auslegung); als Robustheitsprüfung wird zusätzlich mit 0,5 gerechnet. Entwürfe ohne Kernaussage gehen nicht in den Deckungsanteil ein (vgl. DEMI 2.3 zur KB-Supportedness). |
| K-05 | Die 240 Entwürfe werden in einer per Seed (20261015) **zufälligen Reihenfolge** kodiert, damit RAG und LLM-only desselben Tickets nicht unmittelbar nacheinander beurteilt werden und Reihenfolgeeffekte sich nicht systematisch auf eine Bedingung auswirken. Eine Verblindung der Bedingung ist nicht möglich, weil RAG-Entwürfe Belege enthalten. |
| K-06 | **Zweitkodierung:** 48 Entwürfe (20 %), je 24 RAG und LLM-only, per Seed gezogen und vor Beginn der Kodierung festgelegt. Die zweite Person erhält die Kernaussagen der Erstkodierung und kodiert C1, C2, C3, Mangel und Fehlertypen unabhängig; nur so ist Kappa für C1 und C2 auf Aussageebene berechenbar. Kappa wird je Code berichtet (C1 und C2 je Kernaussage; C3, Mangel und primärer Fehlertyp je Entwurf). |
| K-07 | Die manuelle Kodierung wird **vor** der Sichtung der automatisierten Bewertung (Strang 2) abgeschlossen, damit deren Ergebnisse die Urteile nicht beeinflussen. Ergebnisse der Online-Befragung werden während der Kodierung ebenfalls nicht ausgewertet. |
| K-08 | **Probekodierung:** Die DEMI sieht keine Probekodierung vor. Ergänzend kodiert die Erstkodierperson vor der Hauptkodierung die 20 Entwürfe des Pilotlaufs `pilot-03` (Pilottickets, nicht Teil des Hauptsets), um Leitfaden, Kodierheft und Kodiertabelle zu erproben. Die Ergebnisse gehen nicht in die Auswertung ein; Änderungen am Leitfaden erfolgen vor dem Tag `kodierung-v1.0` und sind im Git-Verlauf nachvollziehbar. Die Zweitkodierperson nimmt an der Probekodierung nicht teil; sie wird vor der Zweitkodierung anhand des Leitfadens eingewiesen. |
