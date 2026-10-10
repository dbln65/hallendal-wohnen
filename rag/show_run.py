"""Zeigt die Ergebnisse eines Laufs zur Durchsicht: beide Antworten je Ticket nebeneinander.

Die Musterantwort-Kernaussagen werden nur zur eigenen Kontrolle angezeigt; das Modell hat sie nie gesehen.

    python rag/show_run.py pilot-01                 # Übersicht: Tokens, Latenz, Kosten, Auffälligkeiten
    python rag/show_run.py pilot-01 --ticket P-04   # beide Antworten eines Tickets im Wortlaut
    python rag/show_run.py pilot-01 --alle          # alle Tickets im Wortlaut
"""

import argparse
import json
import statistics
import sys

from common import RAG_DIR, load_tickets


def show_ticket(tid: str, entries: dict, gold: dict) -> None:
    g = gold[tid]
    print(f"\n{'=' * 100}\n{tid} | {g['kategorie']} | {g['schwierigkeit']} | {g['kb_abdeckung']}")
    print(f"Ticket: {g['ticket_text']}")
    print("Kernaussagen (Musterantwort): " + (" || ".join(g["kernaussagen"]) or "– (Rückfrage erwartet)"))
    for bed in ("rag", "llm"):
        e = entries.get((tid, bed))
        if not e:
            print(f"\n--- {bed.upper()}: fehlt")
            continue
        print(f"\n--- {bed.upper()} (Position {e['position']}, {e['output_tokens']} Tokens, {e['latenz_ms']['gesamt']:.0f} ms)")
        if e["retrieval"]:
            print("Passagen: " + ", ".join(f"{p['chunk_id']} ({p['score_rerank']:.2f})" for p in e["retrieval"]["passagen"]))
        print(e["antwort"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("run_id")
    parser.add_argument("--ticket")
    parser.add_argument("--alle", action="store_true")
    args = parser.parse_args()

    path = RAG_DIR / "runs" / args.run_id / "responses.jsonl"
    if not path.exists():
        sys.exit(f"Lauf nicht gefunden: {path}")
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    entries = {(e["ticket_id"], e["bedingung"]): e for e in rows}
    gold = {t["ticket_id"]: t for t in load_tickets("alle")}

    if args.ticket or args.alle:
        for tid in ([args.ticket] if args.ticket else sorted({e["ticket_id"] for e in rows})):
            show_ticket(tid, entries, gold)
        return

    print(f"Lauf {args.run_id}: {len(rows)} Einträge, {len({e['ticket_id'] for e in rows})} Tickets\n")
    print(f"{'Bedingung':<10}{'n':>4}{'Input Ø':>9}{'Output Ø':>10}{'Latenz Median ms':>18}{'Kosten USD':>12}")
    for bed in ("rag", "llm"):
        es = [e for e in rows if e["bedingung"] == bed]
        if not es:
            continue
        print(f"{bed:<10}{len(es):>4}{statistics.mean(e['input_tokens'] for e in es):>9.0f}"
              f"{statistics.mean(e['output_tokens'] for e in es):>10.0f}"
              f"{statistics.median(e['latenz_ms']['gesamt'] for e in es):>18.0f}"
              f"{sum(e['kosten_usd']['gesamt'] for e in es):>12.5f}")

    print("\nAuffälligkeiten:")
    found = False
    for e in rows:
        notes = []
        if e["finish_reason"] != "stop":
            notes.append(f"abgebrochen ({e['finish_reason']})")
        if e["bedingung"] == "rag" and not e["zitierte_artikel"]:
            notes.append("RAG ohne Beleg")
        if e["bedingung"] == "llm" and e["zitierte_artikel"]:
            notes.append("LLM-only mit Beleg")
        if e["zitate_ausserhalb_kontext"]:
            notes.append(f"zitiert nicht übergebene Artikel {e['zitate_ausserhalb_kontext']}")
        if e["kb_ids_ausserhalb_format"]:
            notes.append("KB-ID außerhalb des Belegformats")
        if e["retrieval"] and any(c["rerank_gekuerzt"] for c in e["retrieval"]["kandidaten"]):
            notes.append("Cross-Encoder-Eingabe gekürzt")
        n_words = len(e["antwort_ohne_belege"].split())
        if n_words > 200:
            notes.append(f"{n_words} Wörter")
        if notes:
            found = True
            print(f"  {e['ticket_id']} {e['bedingung']}: {'; '.join(notes)}")
    if not found:
        print("  keine")


if __name__ == "__main__":
    main()
