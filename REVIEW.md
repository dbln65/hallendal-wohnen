# Review der Knowledge Base

Jeder der 40 Artikel wird manuell gegen `steckbrief.md` geprüft, bevor die KB eingefroren wird. Ergebnisse und Aufwand werden in `review_log.csv` erfasst.

## Ablauf pro Artikel

1. Zeit starten; Artikel und passenden Abschnitt im Steckbrief nebeneinander öffnen.
2. Checkliste unten vollständig durchgehen.
3. Jeden gefundenen Fehler mit Fehlerart und Ursache in `review_log.csv` eintragen.
4. Korrigieren (siehe „Korrekturen“), erneut `python validate_kb.py` ausführen.
5. Zeit stoppen, Minuten eintragen, Artikel als final markieren. Minuten werden kaufmännisch auf ganze Minuten gerundet (4:29 → 4, 4:30 → 5).

## Checkliste

- [ ] Jede Zahl und Frist stimmt mit dem Faktenkatalog überein, auch in der Zuordnung (Land, Paket- vs. Speditionsware, Club-Mitglied).
- [ ] Keine Fakten, Leistungen oder Regeln, die nicht im Faktenkatalog stehen.
- [ ] Alle Fakten aus dem Steckbrief, die zum Thema des Artikels gehören, sind enthalten (Vollständigkeit statt Länge).
- [ ] Kein Thema aus „Bewusste Lücken“, auch nicht indirekt oder als Ausschluss.
- [ ] Keine Fakten der verwandten Artikel wiederholt; Verweise nur per ID.
- [ ] Länderangaben im Frontmatter passen zum Inhalt.
- [ ] Rechtliche Grundlagen plausibel (14 Tage Widerruf, 2 Jahre Gewährleistung).
- [ ] Sie-Form, sachlicher Ton, keine Werbesprache.

Die Längenwarnung des Validators (Soll 150–500 Wörter) ist nur ein Hinweis. Ein kurzer Artikel ist in Ordnung, wenn er vollständig ist.

## Toleranzregel für plausible Ergänzungen

Kleine Ergänzungen, die nicht wörtlich im Steckbrief stehen, werden toleriert und nicht als Fehler erfasst, wenn alle drei Bedingungen erfüllt sind:

Sie widersprechen keinem Fakt im Steckbrief.
Sie enthalten keine Zahl, Frist, Gebühr, Bedingung oder Einschränkung.
Sie beschreiben nur naheliegende Bedienschritte oder allgemeine Selbstverständlichkeiten.

Beispiele für tolerierte Ergänzungen: „Die Benachrichtigung ist kostenlos“ in Abschnitten ohne Kostenangabe im Steckbrief (ausgelöst durch den Pflichtabschnitt „Kosten und Fristen“), „Halten Sie Ihre Bestellnummer bereit“, „Wählen Sie die Option auf der Produktseite“.

Nicht toleriert und als FAKT_ERFUNDEN erfasst: neue Bedingungen oder Einschränkungen (z. B. „nur für Neukunden“), neue Fristen oder Beträge sowie Aussagen, die dem Steckbrief oder dem eigenen Artikel widersprechen.

## Fehlerarten

| Code | Fehlerart | Beispiel |
| --- | --- | --- |
| ZAHL_ERFUNDEN | Zahl oder Frist steht nicht im Steckbrief | „Erstattung in 10 Tagen“ |
| ZAHL_ZUORDNUNG | Zahl existiert, gehört aber zu anderem Fall | 69 € statt 49 € für DE |
| FAKT_ERFUNDEN | Leistung oder Regel steht nicht im Steckbrief | „Umtausch in der Filiale“ |
| FAKT_FEHLT | Relevanter Fakt aus dem Steckbrief fehlt | Packstation-Ausschluss beim Rechnungskauf fehlt |
| LUECKE | Thema aus den bewussten Lücken erwähnt | „Abholung im Lager ist nicht möglich“ |
| VERWEIS | Fakten des verwandten Artikels wiederholt oder Verweis falsch | Retourenkosten im Widerrufsartikel |
| FORM | Frontmatter, Struktur, Formatierung | Titel mit Doppelpunkt ohne Anführungszeichen |
| STIL | Du-Form, Werbesprache, unklare Formulierung | „Super einfach!“ |

## Ursachen

| Code | Bedeutung |
| --- | --- |
| MODELL | Das Modell hat vom Steckbrief oder Prompt abgewichen |
| VORLAGE | Vorlage oder Prompt waren fehlerhaft oder missverständlich |
| STECKBRIEF | Der Steckbrief selbst war lückenhaft oder widersprüchlich |

## Korrekturen

| Code | Vorgehen |
| --- | --- |
| KEINE | Artikel unverändert übernommen |
| MANUELL | Kleine Korrektur direkt in der Datei, einzeln committen |
| NEU | `python generate_kb.py --ids KB-xxx --force --stand <Datum>` |
| STECKBRIEF_NEU | Steckbrief korrigiert, alle betroffenen Artikel neu generiert |

Regeln:
- Fakten werden nie nur im Artikel geändert, wenn der Fehler im Steckbrief liegt.
- Jede manuelle Korrektur als eigener Commit mit Artikel-ID in der Nachricht, z. B. `Review KB-016: Rücktransportkosten AT korrigiert`.
- Mehrere Fehler in einem Artikel: eine Zeile pro Fehler in `review_log.csv`.

## Abschluss

1. Alle 40 Artikel in `review_log.csv` mit `final = ja`.
2. `python validate_kb.py` ohne Fehler.
3. Kosten der Generierung mit dem Console-Dashboard abgleichen und notieren.
4. `git tag kb-v1.0` – erst danach Tickets generieren.
