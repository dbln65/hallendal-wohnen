"""Schritt 2: Retrieval mit Reranking (ENTSCHEIDUNGEN.md, E-06 und E-09).

Ablauf je Anfrage:
1. Tickettext unverändert einbetten (text-embedding-3-small)
2. Qdrant liefert die top_k ähnlichsten Chunks (Vektorsuche, Kosinus)
3. Der Cross-Encoder bewertet jedes Paar (Tickettext, Chunk) und behält die rerank_top_n besten

Wird von eval_retrieval.py (Pilot) und vom Generierungsskript (Schritt 3) verwendet.
"""

import time


def resolve_revision(model_name: str) -> str:
    """Aktueller Commit des Modells auf Hugging Face; wird nach dem ersten Lauf in config.yaml fixiert."""
    from huggingface_hub import HfApi

    return HfApi().model_info(model_name).sha


def load_reranker(cfg: dict):
    """Lädt den Cross-Encoder in der fixierten Revision. Gibt (Modell, Revision) zurück."""
    from sentence_transformers import CrossEncoder

    r = cfg["retrieval"]
    revision = r.get("reranker_revision") or resolve_revision(r["reranker"])
    model = CrossEncoder(r["reranker"], revision=revision, device=r["reranker_device"], max_length=r["reranker_max_length"])
    return model, revision


class Retriever:
    def __init__(self, cfg: dict, collection: str | None = None, reranker=None):
        from openai import OpenAI
        from qdrant_client import QdrantClient

        self.cfg = cfg
        self.collection = collection or cfg["qdrant"]["collection"]
        self.openai = OpenAI(max_retries=5)
        self.qdrant = QdrantClient(url=cfg["qdrant"]["url"])
        self.reranker, self.reranker_revision = reranker or load_reranker(cfg)

    def retrieve(self, query: str) -> dict:
        r = self.cfg["retrieval"]
        t0 = time.perf_counter()
        emb = self.openai.embeddings.create(model=self.cfg["embedding"]["modell"], input=query)
        t1 = time.perf_counter()
        hits = self.qdrant.query_points(
            collection_name=self.collection, query=emb.data[0].embedding, limit=r["top_k"], with_payload=True
        ).points
        t2 = time.perf_counter()
        scores = self.reranker.predict([(query, h.payload["text"]) for h in hits]) if hits else []
        t3 = time.perf_counter()

        candidates = [
            {
                "chunk_id": h.payload["chunk_id"],
                "artikel_id": h.payload["artikel_id"],
                "rank_vector": i,
                "score_vector": round(float(h.score), 6),
                "score_rerank": round(float(s), 6),
                "text": h.payload["text"],
            }
            for i, (h, s) in enumerate(zip(hits, scores), start=1)
        ]
        # Reranking: höchster Cross-Encoder-Score zuerst; bei Gleichstand entscheidet der Vektorrang
        ranked = sorted(candidates, key=lambda c: (-c["score_rerank"], c["rank_vector"]))
        passages = [dict(c, rank_rerank=i) for i, c in enumerate(ranked[: r["rerank_top_n"]], start=1)]
        return {
            "candidates": candidates,                 # Top-k der Vektorsuche (für F2 und Context Relevance)
            "passages": passages,                     # an das Modell übergebene Passagen
            "embedding_tokens": emb.usage.total_tokens,
            "latency_ms": {
                "embedding": round((t1 - t0) * 1000, 1),
                "search": round((t2 - t1) * 1000, 1),
                "rerank": round((t3 - t2) * 1000, 1),
            },
        }
