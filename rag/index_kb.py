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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="nur chunken, keine API- und Datenbankaufrufe")
    args = parser.parse_args()

    cfg = load_config()
    emb, qd = cfg["embedding"], cfg["qdrant"]
    count = get_token_counter(cfg["chunking"]["tokenizer"])
    chunks = build_chunks(cfg, count)
    n_tok = sum(c["n_tokens"] for c in chunks)
    print(f"{len(chunks)} Chunks, {n_tok} Tokens | geschätzte Embedding-Kosten: "
          f"{cost_usd(cfg, emb['modell'], input_tokens=n_tok):.6f} USD")
    if args.dry_run:
        return

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY ist nicht gesetzt.")
    from openai import OpenAI
    from qdrant_client import QdrantClient, models

    client = OpenAI(max_retries=5)
    qdrant = QdrantClient(url=qd["url"])
    started = time.monotonic()

    # 1. Embeddings erzeugen
    vectors, usage_tokens = [], 0
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        resp = client.embeddings.create(model=emb["modell"], input=[c["text"] for c in batch])
        vectors.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
        usage_tokens += resp.usage.total_tokens
    if any(len(v) != emb["dimensionen"] for v in vectors):
        sys.exit(f"Unerwartete Vektorlänge (erwartet {emb['dimensionen']}).")

    # 2. Collection neu anlegen (ein Lauf ersetzt den vorherigen Index vollständig)
    if qdrant.collection_exists(qd["collection"]):
        qdrant.delete_collection(qd["collection"])
    qdrant.create_collection(
        collection_name=qd["collection"],
        vectors_config=models.VectorParams(size=emb["dimensionen"], distance=getattr(models.Distance, qd["distanz"].upper())),
    )
    qdrant.upsert(
        collection_name=qd["collection"],
        points=[models.PointStruct(id=point_id(c["chunk_id"]), vector=v, payload=c) for c, v in zip(chunks, vectors)],
        wait=True,
    )
    stored = qdrant.count(qd["collection"], exact=True).count
    if stored != len(chunks):
        sys.exit(f"In Qdrant gespeichert: {stored}, erwartet: {len(chunks)}")

    # 3. Chunks und Protokoll schreiben
    DATA_DIR.mkdir(exist_ok=True)
    with (DATA_DIR / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
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
        "n_chunks": len(chunks),
        "embedding_model": emb["modell"],
        "embedding_tokens": usage_tokens,
        "cost_usd": cost_usd(cfg, emb["modell"], input_tokens=usage_tokens),
        "qdrant_collection": qd["collection"],
        "qdrant_version": qdrant_version,
        "duration_s": round(time.monotonic() - started, 2),
    }
    append_jsonl(LOG_DIR / "index_log.jsonl", entry)
    print(f"Index aufgebaut: {stored} Chunks in '{qd['collection']}' | {usage_tokens} Tokens | "
          f"{entry['cost_usd']:.6f} USD | KB-Hash {entry['kb_hash']} | {entry['duration_s']} s")


if __name__ == "__main__":
    main()
