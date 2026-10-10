"""Bereitet die verblindete Online-Befragung vor (DEMI 1.4.4, 2.4, Tabelle 9; Entscheidungen U-01 bis U-05 in README.md).

Eingabe:
- rag/runs/<run-id>/responses.jsonl  Hauptlauf (Standard: haupt-01)
- rag/runs/<run-id>/run_meta.json    Herkunft des Laufs
- tickets_plan.csv                   Spalte human_rating = ja (60 Tickets, gezogen mit draw_rating_sample.py)
- tickets.jsonl                      Abgleich der Tickettexte

Ausgabe in umfrage/:
- entwuerfe.csv     verblindet: Entwurfs-ID, Block, Tickettext, Antwort ohne Belege (Grundlage für das Umfragetool)
- schluessel.csv    Entwurfs-ID -> Ticket und Bedingung (nur für die Auswertung, nie ins Umfragetool)
- blockbericht.txt  Prüfungen, Bereinigung und Verteilung je Block
- survey_meta.json  Herkunft: Lauf, Hashes, Seed, Git-Stand

Aufruf (im Repo-Hauptverzeichnis):
    python umfrage/prepare_survey.py
"""

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

UMFRAGE_DIR = Path(__file__).resolve().parent
ROOT = UMFRAGE_DIR.parent
sys.path.insert(0, str(ROOT / "rag"))
from common import git_info, now_iso  # noqa: E402

SEED = 20261010          # einmalig festgelegt, keine Neuziehung (U-02, U-03)
N_BLOECKE = 10
BEDINGUNGEN = ("rag", "llm")
SCHWIERIGKEIT = {"einfach": 0, "mittel": 1, "komplex": 2, "kb_gap": 3}
ANREDE = "Guten Tag,"
GRUSS = "Viele Grüße, Ihr Hallendal-Wohnen-Team"

CIT = r"\[\s*KB-\d{3}(?:\s*[,;]\s*KB-\d{3})*\s*\]"
CITATION = re.compile(CIT)
# Ein Beleg oder eine Folge von Belegen wie "[KB-012], [KB-025]" samt Leerzeichen davor (U-01)
CITATION_GROUP = re.compile(rf"[ \t]*{CIT}(?:[ \t]*[,;]?[ \t]*{CIT})*")
# Wörter, die auf die Wissensdatenbank und damit auf die RAG-Bedingung hinweisen könnten (nur Bericht)
HINWEISWOERTER = re.compile(r"Auszug|Auszüge|Wissensdatenbank|Datenbank|Quelle|KB", re.IGNORECASE)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def strip_citations(text: str) -> str:
    """Entfernt alle Belege; im Unterschied zu rag/generation.py auch Belegfolgen und Leerzeichen am Zeilenende."""
    text = CITATION_GROUP.sub("", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def check_text(original: str, clean: str) -> list[str]:
    """Prüft, dass nur Belege entfernt wurden und keine Spuren bleiben."""
    problems = []
    if re.search(r"KB-\d|\[|\]", clean):
        problems.append("Belegreste")
    if re.search(r"[ \t][.,;:!?]|[,;:]\.|\.\.", clean):
        problems.append("Satzzeichenfehler")
    if re.search(r"[ \t]\n|[ \t]{2,}", clean):
        problems.append("Leerzeichenfehler")
    if not clean.startswith(ANREDE) or not clean.endswith(GRUSS):
        problems.append("Rahmen (Anrede/Gruß)")
    skeleton = lambda t: re.sub(r"[\s.,;]", "", t)  # noqa: E731
    if skeleton(clean) != skeleton(CITATION.sub("", original)):
        problems.append("Inhalt verändert")
    return problems


def load_rating_plan() -> dict:
    with (ROOT / "tickets_plan.csv").open(encoding="utf-8") as f:
        plan = {r["ticket_id"]: r for r in csv.DictReader(f) if r["human_rating"] == "ja"}
    if len(plan) != 60:
        sys.exit(f"FEHLER: {len(plan)} Tickets mit human_rating = ja, erwartet 60 (DEMI 1.4.4).")
    return plan


def load_responses(run_dir: Path, plan: dict) -> dict:
    entries = {}
    with (run_dir / "responses.jsonl").open(encoding="utf-8") as f:
        for e in map(json.loads, f):
            key = (e["ticket_id"], e["bedingung"])
            if key in entries:
                sys.exit(f"FEHLER: doppelter Eintrag {key} in responses.jsonl.")
            entries[key] = e
    missing = [(t, b) for t in plan for b in BEDINGUNGEN if (t, b) not in entries]
    if missing:
        sys.exit(f"FEHLER: Entwürfe fehlen im Lauf: {missing}")
    return {(t, b): entries[(t, b)] for t in plan for b in BEDINGUNGEN}


def assign_blocks(plan: dict) -> dict:
    """U-02: Tickets nach Schwierigkeit und Kategorie ordnen (innerhalb zufällig), dann reihum verteilen.

    RAG-Entwurf von Ticket i -> Block i mod 10, LLM-Entwurf -> Block (i + 5) mod 10. Damit enthält jeder Block
    6 RAG- und 6 LLM-Entwürfe aus 12 verschiedenen Tickets, und die Strata verteilen sich gleichmäßig.
    """
    rng = random.Random(SEED)
    tiebreak = {t: rng.random() for t in sorted(plan)}
    ordered = sorted(plan, key=lambda t: (SCHWIERIGKEIT[plan[t]["schwierigkeit"]], plan[t]["kategorie"], tiebreak[t]))
    blocks = {}
    for i, t in enumerate(ordered):
        blocks[(t, "rag")] = i % N_BLOECKE + 1
        blocks[(t, "llm")] = (i + N_BLOECKE // 2) % N_BLOECKE + 1
    return blocks


def assign_ids(keys: list) -> dict:
    """U-03: Pseudonyme Entwurfs-IDs in Zufallsreihenfolge; die ID verrät weder Ticket noch Bedingung."""
    perm = sorted(keys)
    random.Random(f"{SEED}:entwurf_ids").shuffle(perm)
    return {k: f"E{n:03d}" for n, k in enumerate(perm, start=1)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-id", default="haupt-01")
    args = ap.parse_args()
    git_state = git_info()  # vor dem Schreiben der Ausgaben, sonst zählen sie selbst als Änderung

    run_dir = ROOT / "rag" / "runs" / args.run_id
    run_meta = json.loads((run_dir / "run_meta.json").read_text(encoding="utf-8"))
    run_gits = [s["git"] for s in run_meta.get("segmente", [])]
    if not run_gits or any(g.get("dirty") is not False for g in run_gits):
        sys.exit(f"FEHLER: Lauf {args.run_id} hat keinen sauberen Git-Stand (run_meta.json, segmente[].git.dirty).")

    plan = load_rating_plan()
    responses = load_responses(run_dir, plan)
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        ticket_texts = {t["ticket_id"]: t["ticket_text"] for t in map(json.loads, f)}

    blocks = assign_blocks(plan)
    ids = assign_ids(list(responses))

    errors, rows, key_rows, changed, hinweise = [], [], [], [], Counter()
    for (t, b), e in responses.items():
        if e["ticket_text"] != ticket_texts.get(t):
            errors.append(f"{t}: Tickettext weicht von tickets.jsonl ab")
        if e.get("finish_reason") != "stop":
            errors.append(f"{t} {b}: finish_reason = {e.get('finish_reason')}")
        clean = strip_citations(e["antwort"])
        errors += [f"{t} {b}: {p}" for p in check_text(e["antwort"], clean)]
        old = e["antwort_ohne_belege"]
        if clean != old:
            if re.sub(r"[ \t]+\n", "\n", old) == clean:
                changed.append(f"{t} {b}: nur Leerzeichen am Zeilenende")
            else:
                i = next(n for n, (x, y) in enumerate(zip(old + "\0", clean + "\0")) if x != y)
                changed.append(f"{t} {b}: {old[max(0, i - 30):i + 10]!r} -> {clean[max(0, i - 30):i + 10]!r}")
        hinweise[b] += len(HINWEISWOERTER.findall(clean))
        rows.append({"entwurf_id": ids[(t, b)], "block": blocks[(t, b)], "ticket_text": e["ticket_text"], "antwort": clean})
        key_rows.append({"entwurf_id": ids[(t, b)], "block": blocks[(t, b)], "ticket_id": t, "bedingung": b,
                         "kategorie": plan[t]["kategorie"], "schwierigkeit": plan[t]["schwierigkeit"],
                         "kb_abdeckung": plan[t]["kb_abdeckung"], "woerter": len(clean.split())})

    # Blockregeln nach DEMI 1.4.4
    per_block = {n: [k for k in key_rows if k["block"] == n] for n in range(1, N_BLOECKE + 1)}
    for n, items in per_block.items():
        cond = Counter(k["bedingung"] for k in items)
        if len(items) != 12 or cond["rag"] != 6 or cond["llm"] != 6:
            errors.append(f"Block {n}: {len(items)} Entwürfe, {dict(cond)}")
        if len({k["ticket_id"] for k in items}) != len(items):
            errors.append(f"Block {n}: ein Ticket kommt doppelt vor")

    if errors:
        print("\n".join(["FEHLER:"] + errors))
        sys.exit(1)

    rows.sort(key=lambda r: (r["block"], r["entwurf_id"]))
    key_rows.sort(key=lambda r: (r["block"], r["entwurf_id"]))
    for name, data in (("entwuerfe.csv", rows), ("schluessel.csv", key_rows)):
        with (UMFRAGE_DIR / name).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]))
            w.writeheader()
            w.writerows(data)

    # Bericht
    diffs = list(SCHWIERIGKEIT)
    cats = sorted({k["kategorie"] for k in key_rows})
    lines = [
        f"Blockbericht Online-Befragung – erzeugt {now_iso()} mit umfrage/prepare_survey.py",
        f"Lauf: {args.run_id} | Seed: {SEED} | {len(rows)} Entwürfe aus {len(plan)} Tickets | {N_BLOECKE} Blöcke",
        "",
        "Prüfungen: alle bestanden (Tickettexte, finish_reason, Belege entfernt, Rahmen, Inhalt unverändert,",
        "           je Block 12 Entwürfe, 6 RAG + 6 LLM, kein Ticket doppelt)",
        "",
        "Verteilung je Block",
        f"{'Block':>5} | {'RAG':>3} {'LLM':>3} | " + " ".join(f"{d[:7]:>7}" for d in diffs) + " | "
        + " ".join(f"{c[:8]:>8}" for c in cats) + " | Wörter RAG/LLM",
    ]
    for n, items in per_block.items():
        cond = Counter(k["bedingung"] for k in items)
        dc = Counter(k["schwierigkeit"] for k in items)
        cc = Counter(k["kategorie"] for k in items)
        w = {b: round(sum(k["woerter"] for k in items if k["bedingung"] == b) / cond[b]) for b in BEDINGUNGEN}
        lines.append(f"{n:>5} | {cond['rag']:>3} {cond['llm']:>3} | " + " ".join(f"{dc[d]:>7}" for d in diffs) + " | "
                     + " ".join(f"{cc[c]:>8}" for c in cats) + f" | {w['rag']}/{w['llm']}")
    partner = {n: n + N_BLOECKE // 2 for n in range(1, N_BLOECKE // 2 + 1)}
    lines += ["", "Blockpaare mit denselben 12 Tickets in getauschter Bedingung: "
              + ", ".join(f"{a}/{b}" for a, b in partner.items())]
    for a, b in partner.items():
        ta = {k["ticket_id"]: k["bedingung"] for k in per_block[a]}
        tb = {k["ticket_id"]: k["bedingung"] for k in per_block[b]}
        assert ta.keys() == tb.keys() and all(ta[t] != tb[t] for t in ta)
    w_all = {b: [k["woerter"] for k in key_rows if k["bedingung"] == b] for b in BEDINGUNGEN}
    lines += [
        "",
        "Länge (Wörter, gesamt): " + " | ".join(f"{b}: Mittel {sum(v) / len(v):.0f}, Min {min(v)}, Max {max(v)}"
                                                for b, v in w_all.items()),
        f"Hinweiswörter (Auszug, Wissensdatenbank, Datenbank, Quelle, KB): rag {hinweise['rag']}, llm {hinweise['llm']}",
        "",
        f"Bereinigung: {len(changed)} Entwürfe weichen von antwort_ohne_belege im Lauf ab (U-01)",
    ] + [f"  {c}" for c in changed]
    report = "\n".join(lines) + "\n"
    (UMFRAGE_DIR / "blockbericht.txt").write_text(report, encoding="utf-8")

    meta = {
        "erzeugt": now_iso(),
        "skript": "umfrage/prepare_survey.py",
        "git": git_state,
        "seed": SEED,
        "lauf": {"run_id": args.run_id, "responses_sha256": file_hash(run_dir / "responses.jsonl"),
                 "git": run_gits, "config_hash": run_meta.get("config_hash"),
                 "prompt_hash": run_meta.get("prompt_hash"), "kb_hash": run_meta.get("kb_hash")},
        "tickets_plan_sha256": file_hash(ROOT / "tickets_plan.csv"),
        "tickets_jsonl_sha256": file_hash(ROOT / "tickets.jsonl"),
        "anzahl": {"tickets": len(plan), "entwuerfe": len(rows), "bloecke": N_BLOECKE},
        "ausgaben": {n: file_hash(UMFRAGE_DIR / n) for n in ("entwuerfe.csv", "schluessel.csv")},
    }
    (UMFRAGE_DIR / "survey_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(report)
    print("Geschrieben: umfrage/entwuerfe.csv, umfrage/schluessel.csv, umfrage/blockbericht.txt, umfrage/survey_meta.json")


if __name__ == "__main__":
    main()
