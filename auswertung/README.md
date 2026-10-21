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
| Strang 1 Protokollierung | `strang1.py` | Tokens, Kosten, Latenz je Bedingung; Retrieval-Trefferquote; variable Kosten je Ticket für Teilstudie B | erledigt (2026-10-20) |
| API-Nutzung | `api_nutzung.py` | alle protokollierten OpenAI- und Anthropic-Aufrufe je Tag und Modell, zum Abgleich mit den Nutzungsseiten | Skript fertig |
| Strang 2 automatisierte Bewertung | Erhebung: `judge/judge.py`; Auswertung offen | H1, H3, H6, Stabilität des Judge | Erhebung abgeschlossen (`haupt-01-j1`, `haupt-01-j1-wdh`); Auswertung nach Konsens der Kodierung (K-07) |
| Strang 3 Online-Befragung | offen | H2, ICC, Untergruppen | nach Konsens der Kodierung (K-07) |
| Strang 4 Kodierung | offen (`kappa.py` in `kodierung/`) | H4, H5, Cohens Kappa | nach Zweitkodierung |
| Teilstudie B | `teilstudie_b.py` | Szenarien, Break-even, Sensitivität, Amortisationssicht, Schwelle RAG gegenüber LLM-only | Skript fertig |

## Strang 1

```bash
python auswertung/strang1.py --usd-eur <EZB-Kurs>
```

Beschreibende Auswertung des Hauptlaufs `haupt-01`; DEMI Tabelle 15 sieht für Strang 1 keine Tests vor. Ausgabe: `ergebnisse/strang1/bericht.md` (Tabellen für das EVI), `strang1.png`, `kennzahlen.csv`, `paare.csv`, `retrieval.csv`, `meta.json`.

## Teilstudie B

```bash
python auswertung/teilstudie_b.py        # nach strang1.py
```

Modellrechnung nach DEMI 1.5, 3.5 und Tabelle 14. **Alle Ergebnisse sind Modellergebnisse und keine empirischen Messwerte.** Gemessen sind nur die variablen Kosten je Ticket (RAG, für die Schwelle auch LLM-only) und die Latenzdifferenz; das Skript liest sie aus `ergebnisse/strang1/kennzahlen.csv`. Alle übrigen Eingangsgrößen stehen mit Typ und Quelle in `teilstudie_b.py` (Liste `PARAMETER`) und im Blatt „Parameter“ der Tabellenkalkulation.

Ausgabe in `ergebnisse/teilstudie_b/`: `roi_modell.xlsx` (Formeln, nachrechenbar; Blätter Hinweise, Parameter, Szenarien, Sensitivität), `bericht.md`, `szenarien.csv`, `sensitivitaet.csv`, `break_even.png`, `tornado.png`, `meta.json`.

Modell je Monat (Zeitangaben in Minuten, daher ÷ 60):

- Nutzen = Ticketvolumen × Adoptionsrate × (Zeitersparnis + Reduktion der Eskalationsquote × Zusatzzeit je Eskalation) ÷ 60 × Personalkostensatz
- Kosten (TCO) = Hosting + (Aufwand KB-Pflege + Aufwand Monitoring) × Personalkostensatz + Ticketvolumen × Adoptionsrate × variable Kosten je Ticket
- ROI = (Nutzen − Kosten) ÷ Kosten; Break-even = Ticketvolumen mit Nutzen = Kosten

Quellen der Sekundärdaten (abgerufen am 2026-10-20):

- Destatis (2026, 29. April): *Eine Arbeitsstunde kostete im Jahr 2025 durchschnittlich 45,00 Euro* (Pressemitteilung Nr. 148). https://www.destatis.de/DE/Presse/Pressemitteilungen/2026/04/PD26_148_624.html
- Destatis: *Durchschnittliche Bruttoverdienste und Arbeitszeiten April 2025* (Stand 09.01.2026; Kontrollwert B-03). https://www.destatis.de/DE/Themen/Arbeit/Verdienste/Verdienste-Branche-Berufe/Tabellen/bruttomonats-verdienste-stichmonat.html
- Destatis: *Lohnnebenkosten in Deutschland* (Kontrollwert B-03). https://www.destatis.de/DE/Themen/Arbeit/Arbeitskosten-Lohnnebenkosten/Tabellen/lohnkosten-deutschland.html
- Hetzner Online: *Hetzner Price Adjustment 15 June 2026* (zuletzt geändert 08.07.2026). https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Hetzner Online: *IPv4 pricing*. https://docs.hetzner.com/general/infrastructure-and-availability/ipv4-pricing
- Hetzner Online: *Cloud Billing FAQ* (Backups). https://docs.hetzner.com/cloud/billing/faq/

## Entscheidungen

| Nr. | Datum | Entscheidung |
| --- | --- | --- |
| AW-01 | 2026-10-19 | **Währung:** Die Protokolle enthalten Kosten in US-Dollar (Preisliste zum Stichtag 2026-10-10, E-08). DEMI Tabelle 13 verlangt Euro. Umgerechnet wird mit dem EZB-Referenzkurs; da der Stichtag ein Samstag ist, gilt der Kurs vom Freitag, 2026-10-09. |
| AW-02 | 2026-10-19 | **Lage- und Streuungsmaße in Strang 1:** Median und Interquartilsbereich wie in DEMI 3.6, ergänzt um das 90. Perzentil der Latenz. Für die Kosten wird zusätzlich der Mittelwert berichtet, weil er als variable Kosten je Ticket in Teilstudie B eingeht und sich Kosten über das Ticketvolumen aufsummieren. |
| AW-03 | 2026-10-19 | **Retrieval-Trefferquote:** Anteil der KB-gedeckten Tickets (n = 96), bei denen mindestens ein bzw. alle Belegartikel der Musterantwort unter den übergebenen Top-3 (und den Top-5-Kandidaten) waren. Ergänzt F2, das nur Retrieval-Fehler mit Folgen erfasst (kodierung/README.md, Limitationen). |
| B-01 | 2026-10-20 | **Annahmen vor der Entblindung festgelegt.** Alle Szenariowerte stehen fest, bevor Ergebnisse der Stränge 2 bis 4 angesehen werden (K-07). Die Qualitätsdifferenz aus Teilstudie A geht nicht als Parameter ein; einziger Messwert des Modells sind nach DEMI 3.5 die variablen Kosten je Ticket. Sie dient in der Diskussion dazu, einzuordnen, welches Szenario plausibel ist. |
| B-02 | 2026-10-20 | **Richtung der Pflegeannahmen.** DEMI Tabelle 14 nennt für KB-Pflege 2/5/10 h und für Monitoring 1/2/4 h je Monat ohne Zuordnung zu den Szenarien. Da „konservativ“ für ungünstige Annahmen steht, erhält das konservative Szenario den höchsten Aufwand (10 h, 4 h) und das optimistische den niedrigsten (2 h, 1 h). |
| B-03 | 2026-10-20 | **Personalkostensatz 33,20 € je Stunde:** Arbeitskosten je geleistete Stunde 2025 im Abschnitt N „Sonstige wirtschaftliche Dienstleistungen“, dem die Call Center (WZ 82.2) angehören (Destatis, Pressemitteilung Nr. 148 vom 29.04.2026; Jahresschätzung auf Basis der Arbeitskostenerhebung 2020). Abweichung von DEMI Tabelle 14 (Verdiensterhebung): Gesucht ist der Wert einer eingesparten Arbeitsstunde für den Arbeitgeber, also Bruttoverdienst einschließlich Lohnnebenkosten je tatsächlich geleistete Stunde. Die Verdiensterhebung weist nur Bruttoverdienste je bezahlte Stunde aus, eine Gliederung nach Call Centern ist nur über GENESIS-Online abrufbar. Kontrollwerte: Bruttostundenverdienst im Abschnitt N (Vollzeit, April 2025) 22,70 €, mit 29 € Lohnnebenkosten je 100 € Bruttoverdienst (2025) rund 29,28 €; Arbeitskosten im Abschnitt G „Handel“ (Serviceteam beim Händler selbst) 37,20 €. Beide liegen in der Sensitivitätsspanne von ±20 % (26,56 bis 39,84 €). Der Satz gilt in allen Szenarien und auch für die Stunden der KB-Pflege und des Monitorings. |
| B-04 | 2026-10-20 | **Hosting 10,69 € je Monat:** ein Cloud-Server für Qdrant, Anwendung und Reranker wie im Prototyp (`rag/docker-compose.yml`), Hetzner CX33 (4 vCPU, 8 GB RAM, 80 GB) für 8,49 € nach der Preisanpassung vom 15.06.2026, zuzüglich primärer IPv4-Adresse (0,50 €) und Backups (20 % des Serverpreises, 1,70 €); Standort Deutschland, Nettopreise, da ein Unternehmen die Vorsteuer abzieht. Ersetzt die Annahme einer kostenfreien Vektordatenbank (DEMI 3.5, E-02). Grenzen: Die Servergröße ist eine Annahme; Speicherbedarf und Latenz des Rerankers auf diesem Server wurden nicht gemessen; keine Hochverfügbarkeit; die Produktseite zeigte beim Abruf den Hinweis „currently unavailable“. Der Wert gilt in allen Szenarien. |
| B-05 | 2026-10-20 | **Variable Kosten je Ticket:** Mittelwert der Kosten je Anfrage der RAG-Bedingung aus Strang 1 (AW-02), automatisch aus `ergebnisse/strang1/kennzahlen.csv` gelesen; wie in DEMI 3.5 nur für unterstützte Tickets (Ticketvolumen × Adoptionsrate). Die Latenz wird im Vergleich mit einem Betrieb ohne System nicht von der Zeitersparnis abgezogen, weil die Annahmen zur Zeitersparnis aus Einsatzstudien abgeleitet sind, die Gesamteffekte im Betrieb messen. |
| B-06 | 2026-10-20 | **Break-even geschlossen berechnet:** Ticketvolumen = Fixkosten ÷ (Adoptionsrate × Deckungsbeitrag je unterstütztem Ticket), mit Deckungsbeitrag = (Zeitersparnis + Reduktion der Eskalationsquote × Zusatzzeit) ÷ 60 × Personalkostensatz − variable Kosten je Ticket. Da das Modell im Ticketvolumen linear ist, entspricht das Ergebnis der Zielwertsuche aus DEMI 3.5. Die Tabellenkalkulation enthält eine Kontrollzeile (Nettonutzen beim Break-even = 0) und eine Anleitung zur Zielwertsuche. |
| B-07 | 2026-10-20 | **Sensitivität:** One-at-a-time-Variation um ±20 % (DEMI 1.5) für zehn Parameter in jedem Szenario; Zielgröße ist der ROI, Rangfolge nach der Spannweite zwischen −20 % und +20 %, gleiche Spannweite ergibt denselben Rang. Die Fixkosten aus DEMI Tabelle 14 werden in Hosting, KB-Pflege und Monitoring aufgeteilt. Der Personalkostensatz wirkt zugleich auf den Nutzen und auf die Pflegekosten; Ticketvolumen und Adoptionsrate wirken nur als Produkt und daher gleich stark. |
| B-08 | 2026-10-20 | **Amortisationssicht (Ergänzung zur DEMI):** Das Modell enthält nur laufende Kosten; einmalige Kosten für Einführung, Integration und Schulung fehlen, und belastbare Beträge liegen nicht vor. Statt einen Betrag anzunehmen, wird die höchste Einmalinvestition ausgewiesen, die der monatliche Nettonutzen in 12, 24 bzw. 36 Monaten zurückverdient (Nettonutzen × Monate, ohne Abzinsung). |
| B-09 | 2026-10-20 | **Schwelle RAG gegenüber LLM-only (Ergänzung zur DEMI):** zusätzliche Zeitersparnis je unterstütztem Ticket, die RAG gegenüber LLM-only erbringen muss, damit sich die Mehrkosten tragen. Mehrkosten = Hosting + KB-Pflege + unterstützte Tickets × (Kosten je Anfrage RAG − LLM-only). Monitoring fällt bei beiden Varianten an. Hosting wird vollständig RAG zugerechnet, obwohl auch LLM-only einen kleinen Anwendungsserver bräuchte. Hinzu kommt die gemessene Latenzdifferenz (Mittelwert der Differenzen je Ticket) als Wartezeit. Beide Festlegungen gehen zulasten von RAG. Die Schwelle wird in der Diskussion der Qualitätsdifferenz aus Teilstudie A gegenübergestellt. |
