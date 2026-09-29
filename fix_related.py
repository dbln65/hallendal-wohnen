"""Schreibt den Abschnitt „Verwandte Artikel“ aller KB-Artikel deterministisch aus plan.csv neu.

Hintergrund: Der Generierungsprompt verlangte Verweise mit Titel, übergab die Titel der
verwandten Artikel aber nicht. Das Modell hat einige Titel deshalb falsch geraten.
Dieses Skript ersetzt den Abschnitt ab „## Verwandte Artikel“ bis zum Dateiende durch
die IDs und exakten Titel aus plan.csv. Alles davor bleibt unverändert.

    python fix_related.py --check   # nur anzeigen, was sich ändern würde
    python fix_related.py           # Dateien schreiben
"""

import argparse
import csv
import difflib
import re
import sys
from pathlib import Path

BASE = Path(__file__).parent
PLAN = BASE / "plan.csv"
HEADING = "## Verwandte Artikel"


def build_section(row: dict, titles: dict[str, str]) -> str:
    lines = [HEADING]
    for rid in (r.strip() for r in row["verwandte"].split(",") if r.strip()):
        lines.append(f"- {rid} {titles[rid]}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--kb-dir", default=str(BASE / "kb"))
    parser.add_argument("--check", action="store_true", help="nichts schreiben, nur Unterschiede zeigen")
    args = parser.parse_args()

    with PLAN.open(encoding="utf-8") as f:
        plan = {r["id"]: r for r in csv.DictReader(f)}
    titles = {rid: r["titel"] for rid, r in plan.items()}

    changed, problems = [], []
    for path in sorted(Path(args.kb_dir).glob("KB-*.md")):
        row = plan.get(path.stem)
        if row is None:
            problems.append(f"{path.name}: ID nicht in plan.csv")
            continue
        old = path.read_text(encoding="utf-8")
        match = re.search(rf"(?m)^{re.escape(HEADING)}\s*$", old)
        if not match:
            problems.append(f"{path.name}: Abschnitt „Verwandte Artikel“ fehlt")
            continue
        new = old[: match.start()] + build_section(row, titles)
        if new == old:
            continue
        changed.append(path.name)
        if args.check:
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(), path.name, path.name, lineterm="", n=0)
            print("\n".join(line for line in diff if not line.startswith("@@")))
            print()
        else:
            path.write_text(new, encoding="utf-8")

    verb = "würden geändert" if args.check else "geändert"
    print(f"{len(changed)} Dateien {verb}: {', '.join(changed) if changed else '–'}")
    for p in problems:
        print(f"PROBLEM: {p}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
