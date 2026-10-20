# Auswertung (EVI)

Skripte für die Auswertung der Untersuchung nach DEMI 3.6 und Tabelle 15. Jedes Skript liest die eingefrorenen Daten aus `rag/`, `umfrage/` und `kodierung/`, schreibt seine Ergebnisse nach `ergebnisse/<teil>/` und hält die Herkunft in `meta.json` fest (Hashes, Git-Stand, Bibliotheksversionen).

## Einrichtung

```bash
pip install -r auswertung/requirements.txt
```

Die Versionen sind nicht fest vorgegeben; jedes Skript schreibt die tatsächlich verwendeten Versionen in seine `meta.json`.

## Stand

| Teil | Skript | Liefert | Status |
| --- | --- | --- | --- |
| Strang 1 Protokollierung | `strang1.py` | Tokens, Kosten, Latenz je Bedingung; Retrieval-Trefferquote; variable Kosten je Ticket für Teilstudie B | Skript fertig |
| API-Nutzung | `api_nutzung.py` | alle protokollierten OpenAI- und Anthropic-Aufrufe je Tag und Modell, zum Abgleich mit den Nutzungsseiten | Skript fertig |
| Strang 2 automatisierte Bewertung | offen | H1, H3, H6 | offen |
| Strang 3 Online-Befragung | offen | H2, ICC, Untergruppen | nach Konsens der Kodierung (K-07) |
| Strang 4 Kodierung | offen (`kappa.py` in `kodierung/`) | H4, H5, Cohens Kappa | nach Zweitkodierung |
| Teilstudie B | offen | Szenarien, Break-even, Sensitivität | nach Teilstudie A |

## Strang 1

```bash
python auswertung/strang1.py --usd-eur <EZB-Kurs>
```

Beschreibende Auswertung des Hauptlaufs `haupt-01`; DEMI Tabelle 15 sieht für Strang 1 keine Tests vor. Ausgabe: `ergebnisse/strang1/bericht.md` (Tabellen für das EVI), `strang1.png`, `kennzahlen.csv`, `paare.csv`, `retrieval.csv`, `meta.json`.

## Entscheidungen

| Nr. | Datum | Entscheidung |
| --- | --- | --- |
| AW-01 | 2026-10-19 | **Währung:** Die Protokolle enthalten Kosten in US-Dollar (Preisliste zum Stichtag 2026-10-10, E-08). DEMI Tabelle 13 verlangt Euro. Umgerechnet wird mit dem EZB-Referenzkurs; da der Stichtag ein Samstag ist, gilt der Kurs vom Freitag, 2026-10-09. |
| AW-02 | 2026-10-19 | **Lage- und Streuungsmaße in Strang 1:** Median und Interquartilsbereich wie in DEMI 3.6, ergänzt um das 90. Perzentil der Latenz. Für die Kosten wird zusätzlich der Mittelwert berichtet, weil er als variable Kosten je Ticket in Teilstudie B eingeht und sich Kosten über das Ticketvolumen aufsummieren. |
| AW-03 | 2026-10-19 | **Retrieval-Trefferquote:** Anteil der KB-gedeckten Tickets (n = 96), bei denen mindestens ein bzw. alle Belegartikel der Musterantwort unter den übergebenen Top-3 (und den Top-5-Kandidaten) waren. Ergänzt F2, das nur Retrieval-Fehler mit Folgen erfasst (kodierung/README.md, Limitationen). |
