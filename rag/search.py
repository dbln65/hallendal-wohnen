"""Kontrolle der Vektorsuche: zeigt die Top-k Chunks für ein Ticket oder einen freien Text.

Ein Haken (✓) markiert Chunks aus Artikeln, die für das Ticket als relevant gelten
(belegartikel und bestätigte weitere_kandidaten aus tickets.jsonl).

Haupttickets dürfen nicht zum Abstimmen verwendet werden (ENTSCHEIDUNGEN.md, E-10).
Deshalb sind standardmäßig nur Pilottickets erlaubt.

    python rag/search.py --ticket P-04
    python rag/search.py --text "Wie lange dauert die Lieferung in die Schweiz?"
"""

import argparse
import json
import os
import sys

from common import ROOT, load_config


def load_ticket(tid: str) -> dict:
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            if t["ticket_id"] == tid:
                return t
    sys.exit(f"Ticket {tid} nicht in tickets.jsonl")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", help="Ticket-ID, z. B. P-04")
    group.add_argument("--text", help="freier Suchtext")
    parser.add_argument("--k", type=int, help="Anzahl Treffer (Standard: retrieval.top_k)")
    parser.add_argument("--erlaube-haupt", action="store_true", help="Haupttickets zulassen (nur nach dem Einfrieren)")
    args = parser.parse_args()

    cfg = load_config()
    relevant = set()
    if args.ticket:
        t = load_ticket(args.ticket)
        if t["set"] != "pilot" and not args.erlaube_haupt:
            sys.exit("Haupttickets nicht zum Abstimmen verwenden (E-10). Nur nach dem Einfrieren mit --erlaube-haupt.")
        query = t["ticket_text"]
        relevant = set(t["belegartikel"]) | set(t["weitere_kandidaten"])
        print(f"{t['ticket_id']} | {t['kategorie']} | {t['schwierigkeit']} | relevant: {', '.join(sorted(relevant)) or '–'}")
        print(f"Ticket: {query}\n")
    else:
        query = args.text

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY ist nicht gesetzt.")
    from openai import OpenAI
    from qdrant_client import QdrantClient

    vector = OpenAI(max_retries=5).embeddings.create(model=cfg["embedding"]["modell"], input=query).data[0].embedding
    hits = QdrantClient(url=cfg["qdrant"]["url"]).query_points(
        collection_name=cfg["qdrant"]["collection"], query=vector,
        limit=args.k or cfg["retrieval"]["top_k"], with_payload=True,
    ).points
    for rank, h in enumerate(hits, start=1):
        p = h.payload
        mark = "✓" if p["artikel_id"] in relevant else " "
        preview = p["text"].replace("\n", " ")[:110]
        print(f"{rank}. {mark} {p['chunk_id']:9} {h.score:.4f}  {preview}…")


if __name__ == "__main__":
    main()
