"""Schritt 3: Antwortentwürfe für beide Bedingungen erzeugen und nach DEMI 2.2 protokollieren.

Je Ticket werden beide Bedingungen (RAG, LLM-only) in zufälliger, per Seed festgelegter Reihenfolge ausgeführt.
Vor dem ersten protokollierten Aufruf läuft ein Aufwärmaufruf, damit das Laden von Modellen die Latenz nicht verzerrt.

Ergebnis je Lauf im Ordner runs/<run-id>/:
- run_meta.json      Konfiguration, Hashes, Git-Stand, Zeitraum, Summen
- responses.jsonl    ein Eintrag je Ticket und Bedingung (vollständig, inkl. Passagen-Wortlaut)
- responses.csv      dieselben Daten als Tabelle für den Anhang
- errors.jsonl       fehlgeschlagene Aufrufe (falls vorhanden)

    python rag/generate.py --set pilot --run-id pilot-01 --dry-run --ids P-04   # Prompts ansehen, ohne API
    python rag/generate.py --set pilot --run-id pilot-01                        # Pilotlauf (20 Aufrufe)
    python rag/generate.py --set haupt --run-id haupt-01 --erlaube-haupt        # Hauptlauf, erst nach dem Einfrieren

Ein abgebrochener Lauf wird mit derselben --run-id fortgesetzt; vorhandene Einträge werden übersprungen.
"""

import argparse
import csv
import json
import os
import random
import sys

from common import (RAG_DIR, ROOT, append_jsonl, config_hash, git_info, kb_hash, load_config, load_tickets, now_iso,
                    sha256)
from generation import build_messages, generate_one, load_prompts

BEDINGUNGEN = ["rag", "llm"]
CSV_FIELDS = [
    "run_id", "ticket_id", "set", "kategorie", "schwierigkeit", "kb_abdeckung", "bedingung", "position", "timestamp",
    "modell_angefragt", "modell_antwort", "system_fingerprint", "temperatur", "max_output_tokens", "prompt_hash",
    "ticket_text", "kandidaten_ids", "kandidaten_scores_vektor", "passagen_ids", "passagen_scores_rerank",
    "passagen_wortlaut", "antwort", "antwort_ohne_belege", "finish_reason", "zitierte_artikel",
    "zitate_ausserhalb_kontext", "kb_ids_ausserhalb_format", "input_tokens", "cached_tokens", "output_tokens",
    "embedding_tokens", "latenz_ms_retrieval", "latenz_ms_generierung", "latenz_ms_gesamt", "kosten_usd_gesamt",
]


def condition_order(seed: int, ticket_id: str) -> list[str]:
    order = BEDINGUNGEN.copy()
    random.Random(f"{seed}:{ticket_id}").shuffle(order)
    return order


def to_csv_row(e: dict) -> dict:
    r = e.get("retrieval") or {"kandidaten": [], "passagen": []}
    row = {k: e.get(k, "") for k in CSV_FIELDS}
    row.update(
        kandidaten_ids=";".join(c["chunk_id"] for c in r["kandidaten"]),
        kandidaten_scores_vektor=";".join(str(c["score_vector"]) for c in r["kandidaten"]),
        passagen_ids=";".join(p["chunk_id"] for p in r["passagen"]),
        passagen_scores_rerank=";".join(str(p["score_rerank"]) for p in r["passagen"]),
        passagen_wortlaut="\n---\n".join(p["text"] for p in r["passagen"]),
        zitierte_artikel=";".join(e["zitierte_artikel"]),
        zitate_ausserhalb_kontext=";".join(e["zitate_ausserhalb_kontext"]),
        latenz_ms_retrieval=e["latenz_ms"]["retrieval_gesamt"],
        latenz_ms_generierung=e["latenz_ms"]["generierung"],
        latenz_ms_gesamt=e["latenz_ms"]["gesamt"],
        kosten_usd_gesamt=e["kosten_usd"]["gesamt"],
    )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--set", choices=["pilot", "haupt"], required=True)
    parser.add_argument("--run-id", required=True, help="Name des Laufs, z. B. pilot-01")
    parser.add_argument("--ids", nargs="*", help="nur diese Tickets")
    parser.add_argument("--dry-run", action="store_true", help="Prompts ausgeben, keine API-Aufrufe")
    parser.add_argument("--erlaube-haupt", action="store_true", help="Haupttickets zulassen (nur nach dem Einfrieren)")
    args = parser.parse_args()

    cfg = load_config()
    prompts = load_prompts(cfg)
    tickets = load_tickets(args.set)
    if args.ids:
        unknown = set(args.ids) - {t["ticket_id"] for t in tickets}
        if unknown:
            sys.exit(f"Nicht im Set {args.set}: {', '.join(sorted(unknown))}")
        tickets = [t for t in tickets if t["ticket_id"] in set(args.ids)]

    if args.dry_run:
        from retrieval import Retriever

        retriever = Retriever(cfg) if os.getenv("OPENAI_API_KEY") else None
        for t in tickets:
            for bed in condition_order(cfg["generierung"]["reihenfolge_seed"], t["ticket_id"]):
                passages = retriever.retrieve(t["ticket_text"])["passages"] if (bed == "rag" and retriever) else None
                if bed == "rag" and passages is None:
                    passages = [{"artikel_id": "KB-000", "titel": "(Platzhalter ohne API-Key)", "text": "…"}]
                print(f"\n===== {t['ticket_id']} | {bed} =====")
                for m in build_messages(prompts, t["ticket_text"], passages):
                    print(f"[{m['role'].upper()}]\n{m['content']}\n")
        return

    git = git_info()
    if args.set == "haupt":
        if not args.erlaube_haupt:
            sys.exit("Haupttickets erst nach dem Einfrieren (E-10). Dann mit --erlaube-haupt.")
        if git["dirty"]:
            sys.exit("Hauptlauf nur mit sauberem Git-Stand (alles committet).")
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY ist nicht gesetzt.")

    from openai import OpenAI

    from retrieval import Retriever

    run_dir = RAG_DIR / "runs" / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    responses = run_dir / "responses.jsonl"
    done = set()
    if responses.exists():
        with responses.open(encoding="utf-8") as f:
            done = {(e["ticket_id"], e["bedingung"]) for e in map(json.loads, f)}

    client = OpenAI(max_retries=5)
    retriever = Retriever(cfg)

    # Aufwärmaufruf (nicht protokolliert): lädt Modelle und Verbindungen, damit die erste Messung nicht verzerrt ist
    warm = {"ticket_id": "WARMUP", "ticket_text": "Wie lange dauert die Lieferung?"}
    generate_one(client, cfg, prompts, warm, "rag", retriever)

    lock = RAG_DIR / "requirements.lock.txt"
    meta_path = run_dir / "run_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {"run_id": args.run_id, "segmente": []}
    meta.update(
        set=args.set,
        config=cfg,
        config_hash=config_hash(cfg),
        kb_hash=kb_hash(ROOT / cfg["kb"]["verzeichnis"]),
        prompt_hash=prompts["hash"],
        reranker_revision=retriever.reranker_revision,
        requirements_lock_hash=sha256(lock.read_text(encoding="utf-8")) if lock.exists() else None,
    )
    segment = {"start": now_iso(), "git": git, "ids": args.ids or "alle"}
    meta["segmente"].append(segment)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    n_new = 0
    for t in tickets:
        for pos, bed in enumerate(condition_order(cfg["generierung"]["reihenfolge_seed"], t["ticket_id"]), start=1):
            if (t["ticket_id"], bed) in done:
                continue
            base = {"run_id": args.run_id, "ticket_id": t["ticket_id"], "set": t["set"], "kategorie": t["kategorie"],
                    "schwierigkeit": t["schwierigkeit"], "kb_abdeckung": t["kb_abdeckung"], "position": pos,
                    "timestamp": now_iso(), "config_hash": meta["config_hash"], "git_commit": git["commit"]}
            try:
                entry = {**base, **generate_one(client, cfg, prompts, t, bed, retriever if bed == "rag" else None)}
            except Exception as exc:  # Lauf fortsetzen, Fehler protokollieren
                append_jsonl(run_dir / "errors.jsonl", {**base, "bedingung": bed, "error": f"{type(exc).__name__}: {exc}"})
                print(f"{t['ticket_id']} {bed:3}: FEHLER {exc}")
                continue
            append_jsonl(responses, entry)
            n_new += 1
            warn = []
            if entry["finish_reason"] != "stop":
                warn.append(f"finish_reason={entry['finish_reason']}")
            if bed == "rag" and not entry["zitierte_artikel"]:
                warn.append("keine Belege")
            if bed == "llm" and entry["zitierte_artikel"]:
                warn.append("Belege ohne Kontext")
            if entry["zitate_ausserhalb_kontext"]:
                warn.append(f"zitiert nicht übergebene Artikel {entry['zitate_ausserhalb_kontext']}")
            print(f"{t['ticket_id']} {bed:3} (Pos. {pos}): {entry['input_tokens']}+{entry['output_tokens']} Tokens | "
                  f"{entry['latenz_ms']['gesamt']:.0f} ms | {entry['kosten_usd']['gesamt']:.5f} USD"
                  + (f" | ! {', '.join(warn)}" if warn else ""))

    # CSV und Summen aus allen Einträgen des Laufs neu schreiben
    with responses.open(encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    with (run_dir / "responses.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(to_csv_row(e) for e in entries)
    segment["ende"] = now_iso()
    meta["summen"] = {
        "eintraege": len(entries),
        "input_tokens": sum(e["input_tokens"] for e in entries),
        "output_tokens": sum(e["output_tokens"] for e in entries),
        "embedding_tokens": sum(e["embedding_tokens"] for e in entries),
        "kosten_usd": round(sum(e["kosten_usd"]["gesamt"] for e in entries), 6),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{n_new} neue Einträge | Lauf gesamt: {len(entries)} | {meta['summen']['kosten_usd']:.4f} USD | {run_dir}")


if __name__ == "__main__":
    main()
