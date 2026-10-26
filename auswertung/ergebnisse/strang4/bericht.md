# Strang 4: Manuelle Kodierung

Erzeugt mit `auswertung/strang4.py` am 2026-10-26. Grundlage: `kodierung/kodiertabelle_konsens.xlsx` (Erstkodierung, für die 48 doppelt kodierten Entwürfe Konsenscodes; K-11). 120 Ticketpaare, davon 96 KB-gedeckt und 24 KB-Gap. Alle Tests zweiseitig mit α = 0,05.

## Übereinstimmung der Zweitkodierung (vor dem Konsens)

| Code | Einheit | n | Übereinstimmung | Cohens Kappa | Stufe nach Landis und Koch (1977) |
| --- | --- | --- | --- | --- | --- |
| C1 Aussagendeckung | Kernaussagen (beide Bedingungen) | 91 | 83,5 % | 0,57 | moderate |
| C2 Quellenpassung | Kernaussagen (RAG) | 57 | 96,5 % | 0,49 | moderate |
| C3 Rückfrage/Enthaltung | Entwürfe (beide Bedingungen) | 48 | 87,5 % | 0,75 | substantial |
| Mangel | Entwürfe (RAG) | 24 | 91,7 % | 0,45 | moderate |
| Primärer Fehlertyp | Entwürfe (RAG) | 24 | 91,7 % | 0,47 | moderate |
| C1, linear gewichtet | Kernaussagen (beide Bedingungen) | 91 | – | 0,65 | substantial |

Details und Kreuztabellen: `kodierung/kappa/bericht.md`.

## C1 Aussagendeckung

Bis zu drei Kernaussagen je Entwurf, je Kernaussage gegen die gesamte KB geprüft (LEITFADEN.md, Abschnitte 3 und 4). Deckungsanteil je Entwurf streng (teilweise = 0, K-04) und als Robustheitsprüfung mit teilweise = 0,5.

| | RAG | LLM-only |
| --- | --- | --- |
| Kernaussagen gedeckt | 266 (93,3 %) | 53 (33,3 %) |
| Kernaussagen teilweise | 1 (0,4 %) | 46 (28,9 %) |
| Kernaussagen nicht gedeckt | 18 (6,3 %) | 60 (37,7 %) |
| Entwürfe ohne Kernaussage | 0 | 10 |
| Deckungsanteil streng, alle: Median (IQR), Mittel | 1,00 (1,00–1,00), 0,93 (n = 120) | 0,00 (0,00–0,50), 0,31 (n = 110) |
| Deckungsanteil streng, KB-gedeckt: Median (IQR), Mittel | 1,00 (1,00–1,00), 0,99 (n = 96) | 0,00 (0,00–0,67), 0,35 (n = 89) |
| Deckungsanteil streng, KB-Gap: Median (IQR), Mittel | 0,67 (0,50–1,00), 0,70 (n = 24) | 0,00 (0,00–0,00), 0,12 (n = 21) |
| Deckungsanteil teilweise = 0,5, alle: Median (IQR), Mittel | 1,00 (1,00–1,00), 0,93 (n = 120) | 0,50 (0,00–0,75), 0,45 (n = 110) |
| Deckungsanteil teilweise = 0,5, KB-gedeckt: Median (IQR), Mittel | 1,00 (1,00–1,00), 0,99 (n = 96) | 0,50 (0,25–0,83), 0,52 (n = 89) |
| Deckungsanteil teilweise = 0,5, KB-Gap: Median (IQR), Mittel | 0,67 (0,50–1,00), 0,71 (n = 24) | 0,00 (0,00–0,00), 0,13 (n = 21) |

Paare mit Kernaussagen in beiden Bedingungen: 110; Deckungsanteil (streng) RAG höher: 84, gleich: 25, LLM-only höher: 1. Beschreibend; maßgeblich für H3 ist die KB-Supportedness des Judge (DEMI 2.3).

## Manuelle Aussagendeckung und KB-Supportedness (DEMI 2.3)

Beide Zugänge erfassen dasselbe Konstrukt, beziehen sich aber auf unterschiedliche Aussagenmengen: C1 auf bis zu drei Kernaussagen, die KB-Supportedness auf alle Sachaussagen eines Entwurfs. Beschreibend.

| | n | C1 streng, Mittel | KB-Supportedness, Mittel | beide 1 | beide 0 |
| --- | --- | --- | --- | --- | --- |
| RAG | 120 | 0,93 | 0,89 | 73 | 0 |
| LLM-only | 108 | 0,31 | 0,37 | 6 | 35 |

Rangkorrelation über alle Entwürfe mit beiden Werten: ρ = 0,62 (95-%-KI 0,52 bis 0,72, p < 0,001, n = 228).

## C2 Quellenpassung (RAG)

| Code | Kernaussagen |
| --- | --- |
| passend | 259 (90,9 %) |
| nicht passend | 5 (1,8 %) |
| kein Beleg | 21 (7,4 %) |

## C3 Rückfrage oder Enthaltung

| Tickets | RAG | LLM-only |
| --- | --- | --- |
| alle (n = 120) | 20 (16,7 %) | 109 (90,8 %) |
| KB-gedeckt (n = 96) | 9 (9,4 %) | 88 (91,7 %) |
| KB-Gap (n = 24) | 11 (45,8 %) | 21 (87,5 %) |

### H4 (explorativ): Rückfrage oder Enthaltung bei KB-Gap-Tickets

| RAG \ LLM-only | Rückfrage ja | Rückfrage nein |
| --- | --- | --- |
| Rückfrage ja | 9 | 2 |
| Rückfrage nein | 12 | 1 |

- Rückfragequote: RAG 45,8 %, LLM-only 87,5 %
- Exakter McNemar-Test auf die 14 diskordanten Paare: p = 0,013
- Odds Ratio (gepaart, b/c; > 1 = RAG häufiger): 0,17, 95-%-KI 0,02 bis 0,75
- Nach DEMI 1.4.5 nur sehr deutliche Unterschiede nachweisbar; ein nicht signifikantes Ergebnis belegt keine Gleichheit.

## Mangel und Fehlertypen (RAG)

KB-gedeckte Tickets: Mangel bei 7 von 96 RAG-Entwürfen (7,3 %). KB-Gap-Tickets: Mangel bei 15 von 24 (F1 als primärer Typ: 15; laut DEMI Designmerkmal, nicht Teil von H5).

| Fehlertyp | primär (KB-gedeckt, n = 96) | primär oder weiterer (KB-gedeckt) |
| --- | --- | --- |
| F1 KB-Fail | 0 | 0 |
| F2 Retrieval-Fail | 3 | 3 |
| F3 Generation-Fail | 1 | 3 |
| F4 Citation-Fail | 3 | 6 |
| kein Fehlertyp | 89 | – |

### H5: Verteilung der primären Fehlertypen F2–F4 (KB-gedeckte Tickets)

- Beobachtet: F2 = 3, F3 = 1, F4 = 3 (n = 7); erwartet je Typ 2,33
- Chi-Quadrat-Anpassungstest gegen Gleichverteilung: χ²(2) = 1,14, p = 0,565
- Exakter Multinomialtest (AW-09): p = 0,712; die erwarteten Häufigkeiten liegen unter 5, deshalb ist der exakte Test maßgeblich.
