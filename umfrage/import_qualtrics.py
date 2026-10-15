"""Liest den Qualtrics-Export und erzeugt eine Tabelle mit einer Bewertung je Zeile (U-07).

Export in Qualtrics: Data & Analysis → Export & Import → Export Data → CSV, „Download all fields“,
„Export values“, „Recode seen but unanswered questions as -99“.

Aufruf (im Repo-Hauptverzeichnis):
    python umfrage/import_qualtrics.py <export.csv>           # nur echte Antworten (anonymer Link)
    python umfrage/import_qualtrics.py <export.csv> --alle    # auch Preview- und Testantworten (zum Testen)

Ausgabe in umfrage/daten/:
- bewertungen.csv    eine Zeile je Bewertung: Person, Block, S4, Entwurf, Ticket, Bedingung, Merkmale, Q1–Q6
- teilnehmende.csv   eine Zeile je Person: Kanal, Block, S4, Kundenservice-Erfahrung, S1–S3, S5, Dauer, Anmerkungen
- feldstand.txt      vollständige Antworten je Block und S4-Gruppe, Urteile je Entwurf, Prüfergebnisse, Feldende (U-05)

Die Entwurfs-ID jeder Bewertung steht in der zweiten Kopfzeile des Exports (Loop & Merge, Field 1). Sie wird mit
qualtrics/zuordnung.csv abgeglichen; Bedingung und Ticket kommen aus schluessel.csv.
"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

UMFRAGE_DIR = Path(__file__).resolve().parent
OUT = UMFRAGE_DIR / "daten"

LOOP_COL = re.compile(r"^(\d+)_B(\d+)_(Q1|Q6|Q2(?:_5)?_([1-4]))$")
DRAFT_IN_LABEL = re.compile(r"(?<![A-Za-z0-9])(E\d{3}) - ")
SKALA = {"q1": range(1, 4), **{f"q{n}": range(1, 6) for n in range(2, 7)}}
ZIEL_JE_BLOCK = 3      # U-05
ZIEL_ERFAHREN = 10     # DEMI 1.4.3


def item_name(match: re.Match) -> str:
    q = match.group(3)
    return "q1" if q == "Q1" else "q6" if q == "Q6" else f"q{int(match.group(4)) + 1}"


def to_int(value: str):
    try:
        return int(value)
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", type=Path)
    ap.add_argument("--alle", action="store_true", help="auch Preview- und Testantworten einbeziehen")
    args = ap.parse_args()

    with args.export.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    header, labels = rows[0], rows[1]
    data = rows[3:] if rows[2] and rows[2][0].startswith("{") else rows[2:]
    col = {name: i for i, name in enumerate(header)}

    with (UMFRAGE_DIR / "qualtrics" / "zuordnung.csv").open(encoding="utf-8") as f:
        zuordnung = {(int(r["block"]), int(r["loop"])): r["entwurf_id"] for r in csv.DictReader(f)}
    with (UMFRAGE_DIR / "schluessel.csv").open(encoding="utf-8") as f:
        schluessel = {r["entwurf_id"]: r for r in csv.DictReader(f)}

    # Spalten der Bewertungsblöcke: (Block, Loop, Item) -> Spaltenindex; Entwurfs-ID aus der Kopfzeile prüfen
    errors, loop_cols = [], {}
    for i, name in enumerate(header):
        m = LOOP_COL.match(name)
        if not m:
            continue
        loop, block, item = int(m.group(1)), int(m.group(2)), item_name(m)
        found = DRAFT_IN_LABEL.search(labels[i])
        expected = zuordnung.get((block, loop))
        if not found or found.group(1) != expected:
            errors.append(f"Spalte {name}: Entwurf laut Export {found.group(1) if found else '?'}, laut zuordnung.csv {expected}")
        loop_cols[(block, loop, item)] = i
    if len(loop_cols) != 10 * 12 * 6:
        errors.append(f"{len(loop_cols)} Bewertungsspalten gefunden, erwartet 720")
    if errors:
        sys.exit("FEHLER:\n" + "\n".join(errors))

    people, ratings, skipped, warnings = [], [], Counter(), []
    for r in data:
        kanal = r[col["DistributionChannel"]]
        if not args.alle and kanal != "anonymous":
            skipped[f"Kanal {kanal}"] += 1
            continue
        if r[col["Finished"]] != "1":
            skipped["nicht abgeschlossen"] += 1
            continue
        rid, block, s4 = r[col["ResponseId"]], to_int(r[col["block"]]), to_int(r[col["S4"]])
        if block not in range(1, 11):
            warnings.append(f"{rid}: kein gültiger Block ({r[col['block']]!r})")
            continue
        others = [header[i] for (b, _, _), i in loop_cols.items() if b != block and r[i] not in ("", "-99")]
        if others:
            warnings.append(f"{rid}: Werte in fremden Blöcken, z. B. {others[0]}")
        person_ratings = []
        for loop in range(1, 13):
            values = {item: to_int(r[loop_cols[(block, loop, item)]]) for item in SKALA}
            bad = [k for k, v in values.items() if v not in SKALA[k]]
            if bad:
                warnings.append(f"{rid}: Block {block}, Loop {loop}: ungültig/fehlend {bad}")
                continue
            e = zuordnung[(block, loop)]
            k = schluessel[e]
            person_ratings.append({"response_id": rid, "block": block, "s4": s4, "entwurf_id": e,
                                   "ticket_id": k["ticket_id"], "bedingung": k["bedingung"], "kategorie": k["kategorie"],
                                   "schwierigkeit": k["schwierigkeit"], "kb_abdeckung": k["kb_abdeckung"], **values})
        if len(person_ratings) != 12:
            skipped["unvollständige Bewertungen"] += 1
            continue
        ratings += person_ratings
        people.append({"response_id": rid, "kanal": kanal, "block": block, "s4": s4,
                       "ks_erfahrung": "ja" if s4 in (1, 2) else "nein",
                       **{s.lower(): r[col[s]] for s in ("S1", "S2", "S3", "S5")},
                       "dauer_s": r[col["Duration (in seconds)"]],
                       "feedback": r[col["FEEDBACK"]].strip() if "FEEDBACK" in col else ""})

    OUT.mkdir(exist_ok=True)
    for name, rows_out, fields in (
        ("bewertungen.csv", ratings, ["response_id", "block", "s4", "entwurf_id", "ticket_id", "bedingung", "kategorie",
                                      "schwierigkeit", "kb_abdeckung", *SKALA]),
        ("teilnehmende.csv", people, ["response_id", "kanal", "block", "s4", "ks_erfahrung", "s1", "s2", "s3", "s5",
                                      "dauer_s", "feedback"]),
    ):
        with (OUT / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows_out)

    # Feldstand (U-05)
    per_block = defaultdict(Counter)
    for p in people:
        per_block[p["block"]][p["ks_erfahrung"]] += 1
    per_draft = Counter(x["entwurf_id"] for x in ratings)
    erfahren = sum(1 for p in people if p["ks_erfahrung"] == "ja")
    zu_wenig = [b for b in range(1, 11) if sum(per_block[b].values()) < ZIEL_JE_BLOCK]
    lines = [
        f"Feldstand – Export: {args.export.name}" + (" (inkl. Preview/Test)" if args.alle else ""),
        f"Vollständige Antworten: {len(people)} | ausgeschlossen: "
        + (", ".join(f"{k}: {v}" for k, v in skipped.items()) or "keine"),
        "",
        "Block | gesamt | mit KS-Erfahrung | ohne",
    ] + [f"{b:>5} | {sum(per_block[b].values()):>6} | {per_block[b]['ja']:>16} | {per_block[b]['nein']:>4}"
         for b in range(1, 11)] + [
        "",
        f"Urteile je Entwurf: min {min((per_draft.get(e, 0) for e in schluessel), default=0)}, "
        f"max {max(per_draft.values(), default=0)} (Ziel: mindestens {ZIEL_JE_BLOCK})",
        f"Bewertende mit Kundenservice-Erfahrung: {erfahren} (Ziel: mindestens {ZIEL_ERFAHREN})",
        f"Blöcke unter {ZIEL_JE_BLOCK}: {zu_wenig or 'keine'}",
        f"Feldende nach U-05 erreicht: {'ja' if not zu_wenig and erfahren >= ZIEL_ERFAHREN else 'nein'}",
    ]
    if warnings:
        lines += ["", "Hinweise:"] + [f"  {w}" for w in warnings]
    report = "\n".join(lines) + "\n"
    (OUT / "feldstand.txt").write_text(report, encoding="utf-8")
    print(report)
    print(f"Geschrieben: {OUT.name}/bewertungen.csv ({len(ratings)} Bewertungen), {OUT.name}/teilnehmende.csv, "
          f"{OUT.name}/feldstand.txt")


if __name__ == "__main__":
    main()
