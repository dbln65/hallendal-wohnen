# Ticketset – Plan und Vorgehen

`tickets_plan.csv` legt alle Tickets vor der Generierung fest: 120 Haupttickets gemäß DEMI, Tabelle 5, und 10 Pilottickets außerhalb der Stichprobe.

## Verteilung der Haupttickets (DEMI, Tabelle 5)

| Schicht | Versand | Retoure | Reklamation/Garantie | Zahlung | Summe |
| --- | --- | --- | --- | --- | --- |
| einfach, KB-gedeckt | 11 | 11 | 11 | 11 | 44 |
| mittel, KB-gedeckt | 8 | 8 | 8 | 8 | 32 |
| komplex, KB-gedeckt | 5 | 5 | 5 | 5 | 20 |
| KB-Gap | 6 | 6 | 6 | 6 | 24 |
| Summe | 30 | 30 | 30 | 30 | 120 |

Die Kategorie „Garantie“ der DEMI umfasst die KB-Kategorie „Reklamation & Garantie“ (Transportschaden, Falschlieferung, Gewährleistung, Garantie, Montage/Ersatzteile).

## Verhältnis von KB- und Ticketkategorien

Die Knowledge Base deckt sechs Themenfelder ab, die Ticketstichprobe ist über vier davon stratifiziert. Die Artikel zu Bestellung, Kundenkonto sowie Gutscheine & Service verbleiben in der KB. Sie erhöhen die Zahl konkurrierender Passagen im Retrieval und dienen in mittleren und komplexen Tickets teilweise als ergänzende Quelle.

## Spalten

| Spalte | Inhalt |
| --- | --- |
| `ticket_id` | T-001 bis T-120 (Hauptstichprobe), P-01 bis P-10 (Pilot) |
| `set` | `haupt` oder `pilot` |
| `kategorie` | Versand, Retoure, Reklamation/Garantie, Zahlung |
| `schwierigkeit` | `einfach`, `mittel`, `komplex`, `kb_gap` (Definitionen: DEMI 1.4.1) |
| `kb_abdeckung` | `gedeckt` oder `gap` |
| `ziel_artikel` | Artikel, auf denen das Ticket konstruiert wird (Mindestmenge). Weitere Artikel mit denselben Fakten werden bei der Validierung ergänzt. |
| `gap_thema` | nur bei KB-Gap-Tickets |
| `stil` | sprachliche Variante (siehe unten) |
| `szenario` | Anliegen des Kunden in Stichworten; Vorgabe für die Generierung |
| `human_rating` | `ja` = Teil der Rating-Teilstichprobe (DEMI 1.4.4) |

## Stilvarianten (DEMI 1.4.2)

| Stil | Beschreibung |
| --- | --- |
| `sachlich` | vollständige, höfliche Anfrage |
| `umgangssprachlich` | Alltagssprache, Tippfehler, fehlende Satzzeichen |
| `unvollstaendig` | vage, ohne Bestellnummer oder Details; die für die Antwort entscheidende Information bleibt erkennbar |
| `veraergert` | verärgerter Ton, Beschwerde |

Die Stile rotieren je Kategorie (7–8 Tickets je Stil und Kategorie).

## KB-Gap-Themen

Je Kategorie zwei Themen mit je drei Tickets. Die beiden neu ergänzten Themen wurden per Volltextsuche in der KB (kb-v1.0) geprüft und kommen dort nicht vor.

| Kategorie | Gap-Thema 1 | Gap-Thema 2 |
| --- | --- | --- |
| Versand | Lieferung auf Nordsee- und Ostseeinseln | Lieferung am Wochenende oder zu Wunschterminen |
| Retoure | Showroom oder Abholung/Rückgabe im Lager | Kein Drucker für das Retourenlabel (neu) |
| Reklamation/Garantie | Ersatzteile für Fremdmarken | Garantieverlängerung (neu) |
| Zahlung | B2B-Konditionen und Mengenrabatte | Nachträgliche Preiserstattung bei Preissenkung |

Die Pilottickets nutzen die übrigen Lückenthemen (Nachhaltigkeit, Kooperationsanfragen), damit kein Gap-Thema der Hauptstichprobe beim Tuning bekannt ist.

## Pilotset

P-01 bis P-10 dienen ausschließlich der Abstimmung von Prompt, Chunking und Retrieval. Sie gehen in keine Auswertung ein.

## Generierung und Prüfung

| Datei | Inhalt |
| --- | --- |
| `generate_tickets.py` | Claude Sonnet 5, ein Aufruf pro Ticket, strukturierte JSON-Ausgabe; Grundlage ist ausschließlich `kb/` (nicht der Steckbrief) |
| `prompts/ticket_system.txt`, `prompts/ticket_user_template.txt` | Prompts (Hash im Log) |
| `tickets/<ID>.json` | Ticket, Musterantwort, Antworttyp, Kernaussagen, Belege (wörtliche Zitate) und Metadaten |
| `ticket_generation_log.jsonl` | Modell, Effort, Tokens, Cache, Dauer, Prompt- und KB-Hash je Aufruf |
| `validate_tickets.py` | Prüfung gegen Plan und KB, Bericht `ticket_validation_report.csv`; `--export` schreibt `tickets.jsonl` |
| `relevanz_review.csv` | Entscheidung je Relevanz-Hinweis (`bestaetigt`/`verworfen`) mit Begründung |

Ablauf:

```bash
python generate_tickets.py --dry-run --ids T-073
python generate_tickets.py --ids T-001 T-051 T-073 T-115     # Probelauf
python validate_tickets.py
python generate_tickets.py                                   # alle fehlenden (haupt + pilot)
python validate_tickets.py
python validate_tickets.py --export                          # nach dem Review
```

Kurze Musterantworten bei Gap-Tickets und Längenwarnungen sind Hinweise für das Review. Hinweise vom Typ „Relevanz“ nennen weitere Artikel mit demselben Fakt. Sie werden im Review in `relevanz_review.csv` bestätigt oder verworfen (eine Zeile pro Ticket und Artikel). Bestätigt wird ein Artikel nur, wenn er denselben Fakt unter denselben Bedingungen (Land, Warenart) enthält und dieser Fakt zu einer Kernaussage des Tickets gehört. Nur bestätigte Artikel erscheinen im Export als `weitere_kandidaten`; der Export bricht ab, solange ein Hinweis ohne Entscheidung ist.

## Teilstichprobe Human-Rating

`python draw_rating_sample.py` zieht je Kategorie 5 einfache, 4 mittlere, 3 komplexe und 3 KB-Gap-Tickets (insgesamt 60). Seed: 20261006.

## Review der Tickets

Ergebnisse und Aufwand werden in `ticket_review_log.csv` erfasst (eine Zeile pro Fehler; mehrere Fehler im selben Ticket = mehrere Zeilen mit derselben ID). Ursachen- und Korrekturcodes wie in `REVIEW.md`. Fehlerarten:

| Code | Fehlerart |
| --- | --- |
| BELEG | Zitat nicht wörtlich, falscher Artikel oder Beleg fehlt |
| FAKT_ERFUNDEN / ZAHL_ERFUNDEN / ZAHL_ZUORDNUNG | Musterantwort weicht von der KB ab |
| FAKT_FEHLT | Musterantwort beantwortet ein Teilanliegen nicht |
| KERNAUSSAGE | Kernaussage ungefragt, fehlend oder nicht prüfbar |
| GAP | Gap-Ticket mit Fakten/Zusagen in der Rückfrage oder doch durch die KB beantwortbar |
| TICKET | Tickettext unnatürlich, KB-Fachbegriff oder entscheidende Information fehlt |
| SCHWIERIGKEIT | Ticket passt nicht zum Schwierigkeitsgrad der DEMI |
| STIL | Anrede, Ton, Formulierung der Musterantwort |
