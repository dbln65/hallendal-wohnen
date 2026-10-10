"""Schritt 1: Indexierung der Knowledge Base in Qdrant.

Ablauf: KB-Artikel chunken -> Embeddings bei OpenAI erzeugen -> Collection in Qdrant neu anlegen und befüllen.
Schreibt data/chunks.jsonl (alle Chunks im Wortlaut, ohne Vektoren) und einen Eintrag in logs/index_log.jsonl.

Voraussetzungen: Qdrant läuft (docker compose up -d im Ordner rag/), OPENAI_API_KEY ist gesetzt.

    python rag/index_kb.py --dry-run    # nur chunken und Kosten schätzen, kein API-Aufruf
    python rag/index_kb.py              # Index (neu) aufbauen
"""

import argparse
import json
import os
import sys
import time
import uuid

from chunking import build_chunks, get_token_counter
from common import DATA_DIR, LOG_DIR, ROOT, append_jsonl, config_hash, cost_usd, git_info, kb_hash, load_config, now_iso

BATCH = 100


def point_id(chunk_id: str) -> str:
    """Qdrant verlangt UUID oder Ganzzahl; UUID5 aus der Chunk-ID ist bei jedem Lauf identisch."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hallendal-kb/{chunk_id}"))


def build_index(cfg: dict, collection: str, openai_client, qdrant) -> dict:
    """Chunkt die KB nach cfg, erzeugt Embeddings und legt `collection` neu an. Gibt Chunks und Verbrauch zurück."""
    from qdrant_client import models

    emb = cfg["embedding"]
    chunks = build_chunks(cfg, get_token_counter(cfg["chunking"]["tokenizer"]))

    # 1. Embeddings erzeugen
    vectors, usage_tokens = [], 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        resp = openai_client.embeddings.create(model=emb["modell"], input=[c["text"] for c in batch])
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        usage_tokens += resp.usage.total_tokens
    if any(len(v) != emb["dimensionen"] for v in vectors):
        sys.exit(f"Unerwartete Vektorlänge (erwartet {emb['dimensionen']}).")

    # 2. Collection neu anlegen (ein Lauf ersetzt den vorherigen Index vollständig)
    if qdrant.collection_exists(collection):
        qdrant.delete_collection(collection)
    qdrant.create_collection(
        collection_name=collection,
        vectors_config=models.VectorParams(
            size=emb["dimensionen"], distance=getattr(models.Distance, cfg["qdrant"]["distanz"].upper())
        ),
    )
    qdrant.upsert(
        collection_name=collection,
        points=[models.PointStruct(id=point_id(c["chunk_id"]), vector=v, payload=c) for c, v in zip(chunks, vectors)],
        wait=True,
    )
    stored = qdrant.count(collection, exact=True).count
    if stored != len(chunks):
        sys.exit(f"In Qdrant gespeichert: {stored}, erwartet: {len(chunks)}")
    return {
        "chunks": chunks,
        "embedding_tokens": usage_tokens,
        "cost_usd": cost_usd(cfg, emb["modell"], input_tokens=usage_tokens),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="nur chunken, keine API- und Datenbankaufrufe")
    args = parser.parse_args()

    cfg = load_config()
    emb, qd = cfg["embedding"], cfg["qdrant"]
    chunks = build_chunks(cfg, get_token_counter(cfg["chunking"]["tokenizer"]))
    n_tok = sum(c["n_tokens"] for c in chunks)
    print(f"{len(chunks)} Chunks, {n_tok} Tokens | geschätzte Embedding-Kosten: "
          f"{cost_usd(cfg, emb['modell'], input_tokens=n_tok):.6f} USD")
    if args.dry_run:
        return

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY ist nicht gesetzt.")
    from openai import OpenAI
    from qdrant_client import QdrantClient

    qdrant = QdrantClient(url=qd["url"])
    started = time.monotonic()
    result = build_index(cfg, qd["collection"], OpenAI(max_retries=5), qdrant)

    DATA_DIR.mkdir(exist_ok=True)
    with (DATA_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in result["chunks"]:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    try:
        qdrant_version = qdrant.info().version
    except Exception:  # ältere Server liefern keine Versionsinfo
        qdrant_version = None
    entry = {
        "timestamp": now_iso(),
        "git": git_info(),
        "config_hash": config_hash(cfg),
        "kb_hash": kb_hash(ROOT / cfg["kb"]["verzeichnis"]),
        "chunking": cfg["chunking"],
        "n_chunks": len(result["chunks"]),
        "embedding_model": emb["modell"],
        "embedding_tokens": result["embedding_tokens"],
        "cost_usd": result["cost_usd"],
        "qdrant_collection": qd["collection"],
        "qdrant_version": qdrant_version,
        "duration_s": round(time.monotonic() - started, 2),
    }
    append_jsonl(LOG_DIR / "index_log.jsonl", entry)
    print(f"Index aufgebaut: {entry['n_chunks']} Chunks in '{qd['collection']}' | {entry['embedding_tokens']} Tokens | "
          f"{entry['cost_usd']:.6f} USD | KB-Hash {entry['kb_hash']} | {entry['duration_s']} s")


if __name__ == "__main__":
    main()
