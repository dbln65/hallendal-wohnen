"""Kontrolle der Suche: zeigt die Top-k Chunks für ein Ticket oder einen freien Text.

Ein Haken (✓) markiert Chunks aus Artikeln, die für das Ticket als relevant gelten
(belegartikel und bestätigte weitere_kandidaten aus tickets.jsonl).
Mit --rerank zusätzlich die Neuordnung durch den Cross-Encoder und die ausgewählten Top-3.

Haupttickets dürfen nicht zum Abstimmen verwendet werden (ENTSCHEIDUNGEN.md, E-10).
Deshalb sind standardmäßig nur Pilottickets erlaubt.

    python rag/search.py --ticket P-04
    python rag/search.py --ticket P-04 --rerank
    python rag/search.py --text "Wie lange dauert die Lieferung in die Schweiz?"
"""

import argparse
import os
import sys

from common import load_config, load_tickets


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ticket", help="Ticket-ID, z. B. P-04")
    group.add_argument("--text", help="freier Suchtext")
    parser.add_argument("--rerank", action="store_true", help="zusätzlich Reranking mit dem Cross-Encoder")
    parser.add_argument("--erlaube-haupt", action="store_true", help="Haupttickets zulassen (nur nach dem Einfrieren)")
    args = parser.parse_args()

    cfg = load_config()
    relevant = set()
    if args.ticket:
        found = [t for t in load_tickets("alle") if t["ticket_id"] == args.ticket]
        if not found:
            sys.exit(f"Ticket {args.ticket} nicht in tickets.jsonl")
        t = found[0]
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
    mark = lambda aid: "✓" if aid in relevant else " "

    if not args.rerank:
        from openai import OpenAI
        from qdrant_client import QdrantClient

        vector = OpenAI(max_retries=5).embeddings.create(model=cfg["embedding"]["modell"], input=query).data[0].embedding
        hits = QdrantClient(url=cfg["qdrant"]["url"]).query_points(
            collection_name=cfg["qdrant"]["collection"], query=vector, limit=cfg["retrieval"]["top_k"], with_payload=True
        ).points
        for rank, h in enumerate(hits, start=1):
            p = h.payload
            print(f"{rank}. {mark(p['artikel_id'])} {p['chunk_id']:9} {h.score:.4f}  {p['text'].replace(chr(10), ' ')[:110]}…")
        return

    from retrieval import Retriever

    res = Retriever(cfg).retrieve(query)
    print("Vektorsuche (Rang | Chunk | Kosinus | Cross-Encoder-Score):")
    for c in res["candidates"]:
        print(f"{c['rank_vector']}. {mark(c['artikel_id'])} {c['chunk_id']:9} {c['score_vector']:.4f}  {c['score_rerank']:8.4f}")
    print("\nNach Reranking an das Modell übergeben:")
    for p in res["passages"]:
        print(f"{p['rank_rerank']}. {mark(p['artikel_id'])} {p['chunk_id']:9} (vorher Rang {p['rank_vector']})  "
              f"{p['text'].replace(chr(10), ' ')[:100]}…")
    lat = res["latency_ms"]
    print(f"\nLatenz: Embedding {lat['embedding']} ms, Suche {lat['search']} ms, Reranking {lat['rerank']} ms")


if __name__ == "__main__":
    main()
