# KB-Generator – Hallendal Wohnen

Erzeugt die 40 Wissensartikel der Knowledge Base mit Claude und prüft sie automatisch gegen den Firmensteckbrief.

## Dateien

| Datei | Inhalt |
| --- | --- |
| `steckbrief.md` | Einzige Faktenquelle: Profil, Faktenkatalog, bewusste Lücken, Artikelvorlage |
| `plan.csv` | 40 Artikel mit ID, Kategorie, Titel, Kernfakten, Ländern, verwandten Artikeln |
| `prompts/system.txt`, `prompts/user_template.txt` | Prompts (versioniert über Hash im Log) |
| `generate_kb.py` | Generierung, ein API-Aufruf pro Artikel, schreibt `kb/KB-xxx.md` |
| `validate_kb.py` | Automatische Prüfung, schreibt `validation_report.csv` |
| `generation_log.jsonl` | entsteht beim Lauf: Modell, Effort, Tokens, Cache, Dauer, Hashes je Aufruf |

## Einrichtung

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
```

## Ablauf

```bash
# 1. Prompt für einen Artikel ansehen, ohne etwas zu senden
python generate_kb.py --dry-run --ids KB-001

# 2. Probelauf mit 2–3 Artikeln, dann prüfen und lesen
python generate_kb.py --ids KB-001 KB-016 KB-027 --stand 2026-10-01
python validate_kb.py

# 3. Alle fehlenden Artikel generieren
python generate_kb.py --stand 2026-10-01
python validate_kb.py

# 4. Einzelne Artikel nach Korrektur von Steckbrief/Prompt neu erzeugen
python generate_kb.py --ids KB-016 --force --stand 2026-10-01
```

Bereits vorhandene Artikel werden ohne `--force` übersprungen. `--stand` fixiert das Datum im Frontmatter für alle Artikel.

## Modelleinstellungen

Per Umgebungsvariable änderbar:

| Variable | Standard | Hinweis |
| --- | --- | --- |
| `KB_MODEL` | `claude-sonnet-5` | Anderer Anbieter als das Antwortmodell (GPT) |
| `KB_EFFORT` | `medium` | `low`, `medium`, `high`; steuert auch das Nachdenken |
| `KB_MAX_TOKENS` | `16000` | Obergrenze für Thinking + Artikeltext |

Claude Sonnet 5 akzeptiert keine eigenen Werte für `temperature`, `top_p` oder `top_k`; die Anfrage scheitert dann mit einem 400-Fehler. Reproduzierbarkeit entsteht deshalb über fixierte Modell-ID, Effort, Prompt- und Steckbrief-Hash im Log sowie die eingefrorene KB-Version, nicht über Temperatur 0.

Der Steckbrief wird per Prompt-Caching zwischengespeichert. Im Log zeigen `cache_read_input_tokens`, wie viel davon günstiger abgerechnet wurde.

## Validierung

| Stufe | Prüfung |
| --- | --- |
| FEHLER | Frontmatter fehlt oder weicht vom Plan ab; Pflichtabschnitte fehlen; unbekannte Artikel-IDs; Zahlen, die nicht im Steckbrief vorkommen |
| WARNUNG | Länge außerhalb 300–600 Wörter; Begriffe aus den bewussten Lücken; ausgeschriebene Zahlwörter; Verweise weichen vom Plan ab |

Warnungen sind Hinweise für das manuelle Review. Der Zahlencheck erkennt erfundene oder errechnete Werte, aber keine falsch zugeordneten (z. B. 69 € statt 49 € für DE). Das bleibt Aufgabe des manuellen Reviews.

## Nach der Generierung

1. Jeden Artikel mit der Review-Checkliste manuell prüfen.
2. Manuelle Änderungen mit Begründung protokollieren.
3. KB einfrieren (z. B. `git tag kb-v1.0`), erst danach die Tickets generieren.
