"""Schritt 2: Retrieval-Test auf den Pilottickets (ENTSCHEIDUNGEN.md, E-05 und E-10).

Kennzahlen (nur KB-gedeckte Tickets; Gap-Tickets haben keine Belege):
- Artikel-Treffer@k: Anteil der Tickets mit mindestens einem relevanten Artikel unter den Top-k
  (relevant = belegartikel und bestätigte weitere_kandidaten aus tickets.jsonl)
- Beleg-Abdeckung@k: Anteil aller Beleg-Zitate, die wörtlich in einer der Top-k-Passagen stehen
Beides jeweils für die Vektorsuche (Top-5, Top-3) und nach dem Reranking (Top-3).

    python rag/eval_retrieval.py                                   # aktuelle Konfiguration und Collection
    python rag/eval_retrieval.py --varianten 150/30/ja 200/40/ja 300/60/ja 200/40/nein
        # Variante = Chunk-Tokens/Überlappung/Titel; jede wird in einer temporären Collection indexiert

Jeder Lauf wird in logs/retrieval_eval.jsonl protokolliert.
"""

import argparse
import copy
import os
import sys

from common import LOG_DIR, append_jsonl, config_hash, git_info, load_config, load_tickets, norm, now_iso
from retrieval import Retriever, load_reranker


def parse_variant(spec: str) -> dict:
    try:
        size, overlap, titel = spec.split("/")
        return {"chunk_tokens": int(size), "overlap_tokens": int(overlap), "titel_voranstellen": titel == "ja"}
    except ValueError:
        sys.exit(f"Ungültige Variante '{spec}', erwartet z. B. 200/40/ja")


def evaluate(retriever: Retriever, tickets: list[dict]) -> dict:
    rows = []
    for t in tickets:
        res = retriever.retrieve(t["ticket_text"])
        relevant = set(t["belegartikel"]) | set(t["weitere_kandidaten"])
        vec = res["candidates"]
        lists = {"vec5": vec, "vec3": vec[:3], "rr3": res["passages"]}
        zitate = [norm(b["zitat"]) for b in t["belege"]]
        row = {"ticket_id": t["ticket_id"], "relevant": sorted(relevant), "n_belege": len(zitate)}
        for name, items in lists.items():
            texts = [norm(p["text"]) for p in items]
            row[f"{name}_chunks"] = [p["chunk_id"] for p in items]
            row[f"{name}_hit"] = any(p["artikel_id"] in relevant for p in items)
            row[f"{name}_belege"] = sum(any(z in tx for tx in texts) for z in zitate)
        row["rr3_zeichen"] = sum(len(p["text"]) for p in res["passages"])  # grobes Maß der Kontextlänge
        row["rerank_input_tokens_max"] = max((c["rerank_input_tokens"] for c in vec), default=0)
        row["rerank_gekuerzt"] = sum(c["rerank_gekuerzt"] for c in vec)
        rows.append(row)

    n_t, n_b = len(rows), sum(r["n_belege"] for r in rows)
    summary = {}
    for name in ("vec5", "vec3", "rr3"):
        summary[f"artikel_treffer_{name}"] = round(sum(r[f"{name}_hit"] for r in rows) / n_t, 3)
        summary[f"beleg_abdeckung_{name}"] = round(sum(r[f"{name}_belege"] for r in rows) / n_b, 3)
    summary["kontext_zeichen_rr3_mittel"] = round(sum(r["rr3_zeichen"] for r in rows) / n_t)
    summary["rerank_input_tokens_max"] = max(r["rerank_input_tokens_max"] for r in rows)
    summary["rerank_paare_gekuerzt"] = sum(r["rerank_gekuerzt"] for r in rows)
    summary["rerank_paare"] = sum(len(r["vec5_chunks"]) for r in rows)
    return {"summary": summary, "tickets": rows, "n_tickets": n_t, "n_belege": n_b}


def print_details(result: dict) -> None:
    for r in result["tickets"]:
        rel = set(r["relevant"])
        mark = lambda ids: " ".join(f"{c}{'✓' if c.split('#')[0] in rel else ''}" for c in ids)
        print(f"{r['ticket_id']}  relevant: {', '.join(r['relevant'])}")
        print(f"    Vektor Top-5:  {mark(r['vec5_chunks'])}")
        print(f"    Rerank Top-3:  {mark(r['rr3_chunks'])}   Belege {r['rr3_belege']}/{r['n_belege']}")


def print_summary_table(results: list[tuple[str, dict]]) -> None:
    head = f"{'Variante':<22}{'Treffer V@5':>12}{'V@3':>6}{'R@3':>6}{'Belege V@5':>12}{'V@3':>6}{'R@3':>6}{'Kontext':>9}"
    print("\n" + head + "\n" + "-" * len(head))
    for label, res in results:
        s = res["summary"]
        print(f"{label:<22}{s['artikel_treffer_vec5']:>12.2f}{s['artikel_treffer_vec3']:>6.2f}{s['artikel_treffer_rr3']:>6.2f}"
              f"{s['beleg_abdeckung_vec5']:>12.2f}{s['beleg_abdeckung_vec3']:>6.2f}{s['beleg_abdeckung_rr3']:>6.2f}"
              f"{s['kontext_zeichen_rr3_mittel']:>9}")
    print("Treffer = Artikel-Treffer, Belege = Beleg-Abdeckung, V = Vektorsuche, R = nach Reranking, "
          "Kontext = mittlere Zeichenzahl der Top-3-Passagen")
    for label, res in results:
        s = res["summary"]
        print(f"Cross-Encoder {label}: längste Eingabe {s['rerank_input_tokens_max']} Tokens, "
              f"gekürzt {s['rerank_paare_gekuerzt']} von {s['rerank_paare']} Paaren")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--varianten", nargs="*", help="Chunk-Tokens/Überlappung/Titel, z. B. 200/40/ja")
    parser.add_argument("--set", choices=["pilot", "haupt"], default="pilot")
    parser.add_argument("--erlaube-haupt", action="store_true", help="Haupttickets zulassen (nur nach dem Einfrieren)")
    args = parser.parse_args()

    if args.set == "haupt" and not args.erlaube_haupt:
        sys.exit("Haupttickets nicht zum Abstimmen verwenden (E-10). Nur nach dem Einfrieren mit --erlaube-haupt.")
    if args.set == "haupt" and args.varianten:
        sys.exit("Variantenvergleich nur mit Pilottickets (E-10).")
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY ist nicht gesetzt.")

    cfg = load_config()
    all_tickets = load_tickets(args.set)
    tickets = [t for t in all_tickets if t["kb_abdeckung"] == "gedeckt"]
    print(f"{len(tickets)} KB-gedeckte Tickets ({args.set}); {len(all_tickets) - len(tickets)} Gap-Tickets ohne Belege ausgelassen")

    reranker = load_reranker(cfg)
    print(f"Reranker {cfg['retrieval']['reranker']} @ {reranker['revision']} | max_length {cfg['retrieval']['reranker_max_length']}")
    if not cfg["retrieval"].get("reranker_revision"):
        print(f"Hinweis: Revision in config.yaml fixieren -> reranker_revision: {reranker['revision']}")

    results = []
    if not args.varianten:
        res = evaluate(Retriever(cfg, reranker=reranker), tickets)
        c = cfg["chunking"]
        label = f"{c['chunk_tokens']}/{c['overlap_tokens']}/{'ja' if c['titel_voranstellen'] else 'nein'} (aktuell)"
        print_details(res)
        results.append((label, res, cfg, cfg["qdrant"]["collection"]))
    else:
        from openai import OpenAI
        from qdrant_client import QdrantClient

        from index_kb import build_index

        tune = cfg["qdrant"]["collection"] + "_tune"
        openai_client, qdrant = OpenAI(max_retries=5), QdrantClient(url=cfg["qdrant"]["url"])
        for spec in args.varianten:
            cfg_v = copy.deepcopy(cfg)
            cfg_v["chunking"].update(parse_variant(spec))
            idx = build_index(cfg_v, tune, openai_client, qdrant)
            res = evaluate(Retriever(cfg_v, collection=tune, reranker=reranker), tickets)
            res["n_chunks"] = len(idx["chunks"])
            print(f"Variante {spec}: {res['n_chunks']} Chunks indexiert und ausgewertet")
            results.append((spec, res, cfg_v, tune))
        qdrant.delete_collection(tune)

    print_summary_table([(label, res) for label, res, _, _ in results])
    for label, res, cfg_used, collection in results:
        append_jsonl(LOG_DIR / "retrieval_eval.jsonl", {
            "timestamp": now_iso(),
            "git": git_info(),
            "config_hash": config_hash(cfg_used),
            "variante": label,
            "chunking": cfg_used["chunking"],
            "collection": collection,
            "set": args.set,
            "reranker": cfg["retrieval"]["reranker"],
            "reranker_revision": reranker["revision"],
            "reranker_max_length": cfg["retrieval"]["reranker_max_length"],
            **res,
        })
    print("\nProtokolliert in logs/retrieval_eval.jsonl")


if __name__ == "__main__":
    main()
