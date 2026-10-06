"""Prüft die generierten Tickets (tickets/*.json) gegen Plan und Knowledge Base.

FEHLER    Felder/Antworttyp passen nicht zur KB-Abdeckung; Zitat steht nicht wörtlich im
          angegebenen Artikel; unbekannte Artikel-ID; Zahl in der Musterantwort, die in der
          KB nicht vorkommt; Gap-Ticket mit Belegen oder Kernaussagen
WARNUNG   Zielartikel nicht zitiert; Zahl der Musterantwort nicht in den Belegen; Gap-Antwort
          mit Zahlen; Ticket übernimmt Wortfolgen (>= 5 Wörter) oder Fachbegriffe aus der KB;
          Längen außerhalb der Vorgaben; sehr ähnliche Tickets
HINWEIS   weitere Artikel, die denselben Fakt enthalten (Kandidaten für relevante Artikel)

    python validate_tickets.py
    python validate_tickets.py --export     # schreibt tickets.jsonl (nur ohne Fehler und vollständig)
"""

import argparse
import csv
import json
import re
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

from validate_kb import extract_numbers as _extract_numbers  # gleiche Zahlenlogik wie bei der KB


def extract_numbers(text: str) -> set[str]:
    """Wie bei der KB, aber ohne die „3“ aus „3-D-Secure“."""
    return _extract_numbers(re.sub(r"3-D-Secure|B2B", " ", text, flags=re.I))

BASE = Path(__file__).parent
PLAN = BASE / "tickets_plan.csv"
KB_DIR = BASE / "kb"
TICKET_DIR = BASE / "tickets"
REPORT = BASE / "ticket_validation_report.csv"
EXPORT = BASE / "tickets.jsonl"

DEMI_SOLL = {"einfach": 11, "mittel": 8, "komplex": 5, "kb_gap": 6}  # je Kategorie
FACHBEGRIFFE = ["paketware", "speditionsware", "sperrgut", "retourenportal", "aktionscode", "zahlungspartner"]
MAX_NGRAM = 5


def norm(text: str) -> str:
    """Normalisiert Markdown, Anführungszeichen, Striche und Leerraum für den Zitatvergleich."""
    text = re.sub(r"(?m)^\s*(?:[-*]|\d+\.)\s+", "", text)
    text = re.sub(r"[*_`#|]", " ", text)
    text = text.replace("„", '"').replace("“", '"').replace("”", '"').replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().rstrip(".;:,!").strip().casefold()


def words(text: str) -> list[str]:
    return re.findall(r"[a-zäöüß0-9]+", text.casefold())


def ngrams(tokens: list[str], n: int) -> set[tuple]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


def longest_shared(ticket_tokens: list[str], article_tokens: list[str]) -> int:
    best = 0
    for n in range(MAX_NGRAM, 16):
        if ngrams(ticket_tokens, n) & ngrams(article_tokens, n):
            best = n
        else:
            break
    return best


def content_words(text: str) -> set[str]:
    return {w for w in words(text) if len(w) >= 5}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--export", action="store_true")
    args = parser.parse_args()

    with PLAN.open(encoding="utf-8") as f:
        plan = {r["ticket_id"]: r for r in csv.DictReader(f)}
    kb_raw = {p.stem: p.read_text(encoding="utf-8") for p in sorted(KB_DIR.glob("KB-*.md"))}
    kb_norm = {k: norm(v) for k, v in kb_raw.items()}
    kb_tokens = {k: words(v) for k, v in kb_raw.items()}
    kb_numbers = set().union(*(extract_numbers(v) for v in kb_raw.values()))

    tickets, rows = {}, []

    def add(tid, level, check, detail):
        rows.append((tid, level, check, detail))

    for path in sorted(TICKET_DIR.glob("*.json")):
        tid = path.stem
        try:
            t = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add(tid, "FEHLER", "JSON", str(exc))
            continue
        p = plan.get(tid)
        if p is None:
            add(tid, "FEHLER", "Plan", "ID nicht in tickets_plan.csv")
            continue
        missing = [k for k in ("ticket_text", "musterantwort", "antworttyp", "kernaussagen", "belege") if k not in t]
        if missing:
            add(tid, "FEHLER", "Felder", f"fehlen: {', '.join(missing)}")
            continue
        tickets[tid] = t
        gap = p["kb_abdeckung"] == "gap"
        belege, kern = t["belege"], t["kernaussagen"]

        # Antworttyp und Struktur
        soll_typ = "rueckfrage" if gap else "sachantwort"
        if t["antworttyp"].casefold() != soll_typ:
            add(tid, "FEHLER", "Antworttyp", f"{t['antworttyp']} statt {soll_typ}")
        if gap and (belege or kern):
            add(tid, "FEHLER", "Gap", "Gap-Ticket enthält Belege oder Kernaussagen")
        if not gap and not belege:
            add(tid, "FEHLER", "Belege", "keine Belege")
        if not gap and not kern:
            add(tid, "FEHLER", "Kernaussagen", "keine Kernaussagen")
        if len(kern) > 5:
            add(tid, "WARNUNG", "Kernaussagen", f"{len(kern)} Kernaussagen (Soll 1–5)")

        # Belege: wörtlich im angegebenen Artikel?
        zitiert = set()
        for b in belege:
            aid, zitat = b.get("artikel_id", ""), norm(b.get("zitat", ""))
            if aid not in kb_norm:
                add(tid, "FEHLER", "Beleg", f"unbekannte Artikel-ID {aid}")
                continue
            zitiert.add(aid)
            if zitat not in kb_norm[aid]:
                elsewhere = [k for k, v in kb_norm.items() if zitat in v]
                hint = f" (steht in {', '.join(elsewhere)})" if elsewhere else ""
                add(tid, "FEHLER", "Beleg", f"Zitat nicht wörtlich in {aid}{hint}: „{b['zitat'][:70]}…“")
            # Kandidaten: andere Artikel mit denselben Zahlen und weitgehend gleichen Inhaltswörtern
            nums, cw = extract_numbers(b["zitat"]), content_words(b["zitat"])
            if nums and len(cw) >= 3:  # kurze Zitate wie „1 Code pro Bestellung“ sind zu unspezifisch
                for k, v in kb_raw.items():
                    if k == aid or k in zitiert:
                        continue
                    if nums <= extract_numbers(v) and len(cw & content_words(v)) / len(cw) >= 0.8:
                        add(tid, "HINWEIS", "Relevanz", f"Fakt aus {aid} auch in {k}: „{b['zitat'][:60]}…“")

        ziel = {a for a in p["ziel_artikel"].split(";") if a}
        if ziel - zitiert and not gap:
            add(tid, "WARNUNG", "Zielartikel", f"nicht zitiert: {', '.join(sorted(ziel - zitiert))}")

        # Zahlen in der Musterantwort
        antwort_nums = extract_numbers(t["musterantwort"])
        ticket_nums = extract_numbers(t["ticket_text"])  # Angaben der Kundin dürfen aufgegriffen werden
        fremd = sorted(antwort_nums - kb_numbers - ticket_nums, key=float)
        if fremd:
            add(tid, "FEHLER", "Zahlen", f"nicht in der KB: {', '.join(fremd)}")
        beleg_nums = set().union(*(extract_numbers(b["zitat"]) for b in belege)) if belege else set()
        ohne_beleg = sorted((antwort_nums & kb_numbers) - beleg_nums - ticket_nums, key=float)
        if gap and antwort_nums - ticket_nums:
            add(tid, "WARNUNG", "Gap", f"Rückfrage enthält Zahlen: {', '.join(sorted(antwort_nums - ticket_nums, key=float))}")
        elif ohne_beleg:
            add(tid, "WARNUNG", "Zahlen", f"in der Antwort, aber nicht in den Belegen: {', '.join(ohne_beleg)}")

        # Ticket: Übernahme aus der KB
        tt = words(t["ticket_text"])
        overlap = max(((longest_shared(tt, toks), k) for k, toks in kb_tokens.items()), default=(0, ""))
        if overlap[0] >= MAX_NGRAM:
            add(tid, "WARNUNG", "Überlappung", f"{overlap[0]} Wörter in Folge identisch mit {overlap[1]}")
        begriffe = [b for b in FACHBEGRIFFE if b in t["ticket_text"].casefold()]
        if begriffe:
            add(tid, "WARNUNG", "Fachbegriff", f"im Ticket: {', '.join(begriffe)}")

        # Längen
        n_t, n_a = len(tt), len(words(t["musterantwort"]))
        if n_t < 5 or n_t > 150:
            add(tid, "WARNUNG", "Länge", f"Ticket {n_t} Wörter")
        if n_a < 30 or n_a > 200:
            add(tid, "WARNUNG", "Länge", f"Musterantwort {n_a} Wörter (Soll 40–180)")

    # Ähnliche Tickets
    sets = {tid: content_words(t["ticket_text"]) for tid, t in tickets.items()}
    for a, b in combinations(sorted(sets), 2):
        if sets[a] and sets[b] and len(sets[a] & sets[b]) / len(sets[a] | sets[b]) > 0.5:
            add(a, "WARNUNG", "Duplikat", f"sehr ähnlich zu {b}")

    # Vollständigkeit und Verteilung
    fehlend = sorted(set(plan) - set(tickets))
    haupt = Counter((plan[t]["kategorie"], plan[t]["schwierigkeit"]) for t in tickets if plan[t]["set"] == "haupt")
    abweichung = [
        f"{kat}/{sch}: {haupt[(kat, sch)]} von {soll}"
        for kat in sorted({p["kategorie"] for p in plan.values() if p["set"] == "haupt"})
        for sch, soll in DEMI_SOLL.items()
        if haupt[(kat, sch)] != soll
    ]

    with REPORT.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ticket_id", "level", "check", "detail"])
        w.writerows(rows)
        w.writerows((m, "FEHLT", "Datei", "noch nicht generiert") for m in fehlend)

    by_ticket = {}
    for tid, level, check, detail in rows:
        by_ticket.setdefault(tid, []).append((level, check, detail))
    for tid in sorted(by_ticket):
        print(tid)
        for level, check, detail in by_ticket[tid]:
            print(f"    {level:7} {check:12} {detail}")

    n = Counter(r[1] for r in rows)
    print(f"\n{len(tickets)} Tickets geprüft | {n['FEHLER']} Fehler | {n['WARNUNG']} Warnungen | "
          f"{n['HINWEIS']} Hinweise | {len(fehlend)} fehlen")
    if abweichung and not fehlend:
        print("Verteilung weicht von DEMI Tabelle 5 ab: " + "; ".join(abweichung))
    print(f"Bericht: {REPORT.name}")

    if args.export:
        if n["FEHLER"] or fehlend:
            sys.exit("Export abgebrochen: erst alle Fehler beheben und alle Tickets generieren.")
        kandidaten = {}
        for tid, level, check, detail in rows:
            if level == "HINWEIS":
                kandidaten.setdefault(tid, set()).add(re.search(r"auch in (KB-\d{3})", detail).group(1))
        with EXPORT.open("w", encoding="utf-8") as f:
            for tid in sorted(tickets):
                t, p = tickets[tid], plan[tid]
                belegartikel = sorted({b["artikel_id"] for b in t["belege"]} | {a for a in p["ziel_artikel"].split(";") if a})
                f.write(json.dumps({
                    "ticket_id": tid, "set": p["set"], "kategorie": p["kategorie"],
                    "schwierigkeit": p["schwierigkeit"], "kb_abdeckung": p["kb_abdeckung"],
                    "gap_thema": p["gap_thema"], "stil": p["stil"], "human_rating": p["human_rating"],
                    "ticket_text": t["ticket_text"], "musterantwort": t["musterantwort"],
                    "antworttyp": t["antworttyp"], "kernaussagen": t["kernaussagen"], "belege": t["belege"],
                    "belegartikel": belegartikel, "weitere_kandidaten": sorted(kandidaten.get(tid, set()) - set(belegartikel)),
                }, ensure_ascii=False) + "\n")
        print(f"Export: {EXPORT.name} ({len(tickets)} Tickets)")

    sys.exit(1 if n["FEHLER"] else 0)


if __name__ == "__main__":
    main()
