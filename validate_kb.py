"""Prüft die generierten KB-Artikel automatisch gegen Steckbrief und Plan.

Prüfungen:
  FEHLER   Frontmatter, Pflichtabschnitte, Artikel-IDs, Zahlen, die nicht im Steckbrief stehen
  WARNUNG  Länge außerhalb 300–600 Wörter, Begriffe aus den bewussten Lücken,
           ausgeschriebene Zahlwörter, abweichende verwandte Artikel

Warnungen sind Hinweise für das manuelle Review, keine automatischen Ablehnungen.
Das Ergebnis wird zusätzlich in validation_report.csv geschrieben.

    python validate_kb.py
    python validate_kb.py --kb-dir kb
"""

import argparse
import csv
import re
import sys
from pathlib import Path

import yaml

BASE = Path(__file__).parent
STECKBRIEF = BASE / "steckbrief.md"
PLAN = BASE / "plan.csv"
REPORT = BASE / "validation_report.csv"

SECTIONS = [
    "Kurzantwort",
    "So gehen Sie vor",
    "Kosten und Fristen",
    "Ausnahmen und Sonderfälle",
    "Verwandte Artikel",
]
MIN_WORDS, MAX_WORDS = 300, 600

# Begriffe zu den bewussten Lücken (Kleinschreibung, Regex).
GAP_PATTERNS = {
    "Inseln": r"\binsel|nordsee|ostsee",
    "B2B/Mengenrabatt": r"\bb2b\b|mengenrabatt|großkunde",
    "Preisgarantie": r"preisgarantie|preissenkung|preiserstattung|preisdifferenz",
    "Wochenende/Wunschtermin": r"wochenende|sonntag|samstagslieferung|wunschtermin",
    "Fremdmarken": r"fremdmarke",
    "Nachhaltigkeit": r"nachhaltig|co2|co₂|klima|herkunft",
    "Showroom/Abholung": r"showroom|ausstellung|selbstabholung|abholung im lager|im lager abhol",
    "Bewerbung/Kooperation": r"bewerbung|karriere|stellenangebot|kooperation",
}

NUMBER_WORDS = (
    r"\b(zwei|drei|vier|fünf|sechs|sieben|acht|neun|zehn|elf|zwölf|vierzehn|"
    r"zwanzig|dreißig|vierzig|fünfzig|hundert)\b"
)
NUMBER_RE = re.compile(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:,\d+)?")
KB_ID_RE = re.compile(r"KB-\d{3}")


def normalize(num: str) -> str:
    """'1.500' -> '1500', '4,95' -> '4.95', '5,00' -> '5'."""
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", num):
        num = num.replace(".", "")
    return f"{float(num.replace(',', '.')):g}"


def extract_numbers(text: str) -> set[str]:
    text = KB_ID_RE.sub(" ", text)
    text = re.sub(r"(?m)^\s*\d+\.\s", " ", text)  # Nummerierung von Listen
    return {normalize(n) for n in NUMBER_RE.findall(text)}


def split_frontmatter(text: str) -> tuple[dict | None, str]:
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.S)
    if not match:
        return None, text
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None, match.group(2)
    return (meta if isinstance(meta, dict) else None), match.group(2)


def word_count(body: str) -> int:
    return len(re.findall(r"[\wÄÖÜäöüß€%-]+", body))


def check_article(path: Path, plan: dict, allowed_numbers: set[str]) -> list[tuple[str, str, str]]:
    issues = []

    def add(level, check, detail):
        issues.append((level, check, detail))

    text = path.read_text(encoding="utf-8")
    meta, body = split_frontmatter(text)
    article_id = path.stem

    # Frontmatter
    if meta is None:
        add("FEHLER", "Frontmatter", "fehlt oder ist kein gültiges YAML")
        meta = {}
    else:
        for key in ("id", "kategorie", "titel", "laender", "stand"):
            if key not in meta:
                add("FEHLER", "Frontmatter", f"Feld '{key}' fehlt")
        if meta.get("id") != article_id:
            add("FEHLER", "Frontmatter", f"id '{meta.get('id')}' passt nicht zum Dateinamen")

    row = plan.get(article_id)
    if row is None:
        add("FEHLER", "Plan", "ID steht nicht im Kategorienplan")
    elif meta:
        if meta.get("titel") != row["titel"]:
            add("FEHLER", "Frontmatter", f"titel weicht vom Plan ab: '{meta.get('titel')}'")
        if meta.get("kategorie") != row["kategorie"]:
            add("FEHLER", "Frontmatter", f"kategorie weicht vom Plan ab: '{meta.get('kategorie')}'")
        laender = meta.get("laender") or []
        if set(map(str, laender)) != set(row["laender"].split(",")):
            add("FEHLER", "Frontmatter", f"laender {laender} ≠ Plan {row['laender']}")

    # Struktur
    if not re.search(r"(?m)^# \S", body):
        add("FEHLER", "Struktur", "H1-Überschrift fehlt")
    headings = re.findall(r"(?m)^## (.+?)\s*$", body)
    missing = [s for s in SECTIONS if s not in headings]
    if missing:
        add("FEHLER", "Struktur", f"Abschnitte fehlen: {', '.join(missing)}")
    elif [h for h in headings if h in SECTIONS] != SECTIONS:
        add("FEHLER", "Struktur", "Abschnitte in falscher Reihenfolge")

    # Länge
    words = word_count(body)
    if not MIN_WORDS <= words <= MAX_WORDS:
        add("WARNUNG", "Länge", f"{words} Wörter (Soll {MIN_WORDS}–{MAX_WORDS})")

    # Verweise auf andere Artikel
    referenced = set(KB_ID_RE.findall(body)) - {article_id}
    unknown = referenced - set(plan)
    if unknown:
        add("FEHLER", "Verweise", f"unbekannte IDs: {', '.join(sorted(unknown))}")
    if row is not None:
        expected = set(row["verwandte"].split(","))
        if referenced != expected:
            add("WARNUNG", "Verweise", f"verweist auf {sorted(referenced)}, Plan: {sorted(expected)}")

    # Zahlen, die nicht im Steckbrief stehen
    foreign = sorted(extract_numbers(body) - allowed_numbers, key=float)
    if foreign:
        add("FEHLER", "Zahlen", f"nicht im Steckbrief: {', '.join(foreign)}")

    # Bewusste Lücken
    lowered = body.lower()
    for topic, pattern in GAP_PATTERNS.items():
        hits = sorted({m.group(0) for m in re.finditer(pattern, lowered)})
        if hits:
            add("WARNUNG", "Lücke", f"{topic}: {', '.join(hits)} – manuell prüfen")

    # Zahlwörter
    words_found = sorted({m.group(0) for m in re.finditer(NUMBER_WORDS, lowered)})
    if words_found:
        add("WARNUNG", "Zahlwort", f"ausgeschrieben: {', '.join(words_found)} – Ziffern verwenden?")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kb-dir", default=str(BASE / "kb"))
    args = parser.parse_args()
    kb_dir = Path(args.kb_dir)

    with PLAN.open(encoding="utf-8") as f:
        plan = {r["id"]: r for r in csv.DictReader(f)}
    allowed_numbers = extract_numbers(STECKBRIEF.read_text(encoding="utf-8"))

    files = sorted(kb_dir.glob("KB-*.md"))
    rows, n_err, n_warn = [], 0, 0
    for path in files:
        issues = check_article(path, plan, allowed_numbers)
        status = "FEHLER" if any(i[0] == "FEHLER" for i in issues) else "WARNUNG" if issues else "OK"
        print(f"{path.stem}: {status}")
        for level, check, detail in issues:
            print(f"    {level:7} {check:12} {detail}")
            rows.append((path.stem, level, check, detail))
        n_err += sum(i[0] == "FEHLER" for i in issues)
        n_warn += sum(i[0] == "WARNUNG" for i in issues)

    missing = sorted(set(plan) - {p.stem for p in files})
    with REPORT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "level", "check", "detail"])
        writer.writerows(rows)
        writer.writerows((m, "FEHLT", "Datei", "noch nicht generiert") for m in missing)

    print(f"\n{len(files)} Artikel geprüft | {n_err} Fehler | {n_warn} Warnungen | {len(missing)} fehlen")
    print(f"Bericht: {REPORT.name}")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
