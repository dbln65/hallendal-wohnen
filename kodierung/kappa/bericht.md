# Übereinstimmung der Zweitkodierung

Erzeugt mit `kodierung/kappa.py` am 2026-10-26. 48 Entwürfe (24 RAG), Codes vor dem Konsens (K-06, K-11).

## Tabelle: Cohens Kappa je Code

| Code | Einheit | n | Übereinstimmung | Kappa | 95-%-KI | Stufe |
| --- | --- | --- | --- | --- | --- | --- |
| C1 Aussagendeckung | Kernaussagen (beide Bedingungen) | 91 | 83,5 % | 0,57 | 0,37 bis 0,77 | moderate |
| C2 Quellenpassung | Kernaussagen (RAG) | 57 | 96,5 % | 0,49 | −0,21 bis 1,00 | moderate |
| C3 Rückfrage/Enthaltung | Entwürfe (beide Bedingungen) | 48 | 87,5 % | 0,75 | 0,56 bis 0,94 | substantial |
| Mangel | Entwürfe (RAG) | 24 | 91,7 % | 0,45 | −0,27 bis 1,00 | moderate |
| Primärer Fehlertyp | Entwürfe (RAG) | 24 | 91,7 % | 0,47 | −0,23 bis 1,00 | moderate |
| C1, linear gewichtet (ergänzend) | Kernaussagen (beide Bedingungen) | 91 | – | 0,65 | – | substantial |

Stufen nach Landis und Koch (1977). Konfidenzintervall nach der Näherung von Cohen (1960), auf −1 bis 1 begrenzt; bei kleinen Fallzahlen nur grob. Bei sehr ungleich verteilten Kategorien kann Kappa trotz hoher Übereinstimmung niedrig ausfallen; deshalb wird die prozentuale Übereinstimmung mit berichtet. Die gewichtete Variante wertet „teilweise“ gegenüber „gedeckt“ oder „nicht gedeckt“ als halbe Übereinstimmung.

¹ Kappa ist nicht definiert, wenn beide Kodierenden durchgehend dieselbe Kategorie vergeben.

## Kreuztabellen

Zeilen: Erstkodierung, Spalten: Zweitkodierung.

**C1 Aussagendeckung** (n = 91)

| Erst \ Zweit | gedeckt | teilweise | nicht gedeckt |
| --- | --- | --- | --- |
| gedeckt | 66 | 0 | 0 |
| teilweise | 5 | 4 | 3 |
| nicht gedeckt | 3 | 4 | 6 |

**C2 Quellenpassung** (n = 57)

| Erst \ Zweit | passend | nicht passend | kein Beleg |
| --- | --- | --- | --- |
| passend | 54 | 0 | 0 |
| nicht passend | 0 | 0 | 0 |
| kein Beleg | 2 | 0 | 1 |

**C3 Rückfrage/Enthaltung** (n = 48)

| Erst \ Zweit | ja | nein |
| --- | --- | --- |
| ja | 21 | 4 |
| nein | 2 | 21 |

**Mangel** (n = 24)

| Erst \ Zweit | ja | nein |
| --- | --- | --- |
| ja | 1 | 1 |
| nein | 1 | 21 |

**Primärer Fehlertyp** (n = 24)

| Erst \ Zweit | keiner | F1 | F2 | F3 | F4 |
| --- | --- | --- | --- | --- | --- |
| keiner | 21 | 0 | 0 | 1 | 0 |
| F1 | 0 | 1 | 0 | 0 | 0 |
| F2 | 0 | 0 | 0 | 0 | 0 |
| F3 | 0 | 0 | 0 | 0 | 0 |
| F4 | 1 | 0 | 0 | 0 | 0 |

## Abweichungen für den Konsens

27 abweichende Codierungen in 19 Entwürfen (davon F_weitere: 0; nicht Teil der Kappa-Berechnung). Liste: `abweichungen.xlsx`.
