"""Zieht die stratifizierte Teilstichprobe für das Human-Rating (DEMI, Abschnitt 1.4.4).

Je Kategorie: 5 einfach, 4 mittel, 3 komplex, 3 KB-Gap = 15 Tickets, insgesamt 60.
Die Ziehung ist mit festem Seed reproduzierbar und schreibt die Spalte
`human_rating` (ja/nein) in tickets_plan.csv. Pilot-Tickets sind ausgeschlossen.

    python draw_rating_sample.py
"""

import csv
import random
from collections import defaultdict
from pathlib import Path

SEED = 20261006
QUOTE = {"einfach": 5, "mittel": 4, "komplex": 3, "kb_gap": 3}
PLAN = Path(__file__).parent / "tickets_plan.csv"

with PLAN.open(encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
    fields = list(rows[0])

zellen = defaultdict(list)
for r in rows:
    if r["set"] == "haupt":
        zellen[(r["kategorie"], r["schwierigkeit"])].append(r["ticket_id"])

rng = random.Random(SEED)
gezogen = set()
for key in sorted(zellen):  # feste Reihenfolge -> reproduzierbar
    gezogen.update(rng.sample(sorted(zellen[key]), QUOTE[key[1]]))

for r in rows:
    r["human_rating"] = "ja" if r["ticket_id"] in gezogen else "nein"

with PLAN.open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

print(f"Seed {SEED}: {len(gezogen)} Tickets für das Human-Rating gezogen")
