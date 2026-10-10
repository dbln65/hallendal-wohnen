"""Schritt 3: Prompt-Aufbau, Modellaufruf und Belegverarbeitung (ENTSCHEIDUNGEN.md, E-12 bis E-14).

Beide Bedingungen nutzen denselben System-Prompt. Die Nachricht unterscheidet sich nur im Kontextblock mit den
KB-Passagen und in der Belegpflicht (DEMI 1.3.2):

- LLM-only: prompts/user_llm.txt  (nur Tickettext)
- RAG:      prompts/user_rag.txt  (Passagen + Belegpflicht + Tickettext)
"""

import re
import time

from common import RAG_DIR, cost_usd, sha256

CITATION = re.compile(r"\[\s*KB-\d{3}(?:\s*[,;]\s*KB-\d{3})*\s*\]")
KB_ID = re.compile(r"KB-\d{3}")


def load_prompts(cfg: dict) -> dict:
    d = RAG_DIR / cfg["generierung"]["prompt_verzeichnis"]
    prompts = {name: (d / f"{name}.txt").read_text(encoding="utf-8").strip() for name in ("system", "user_llm", "user_rag")}
    prompts["hash"] = sha256(prompts["system"] + "\n" + prompts["user_llm"] + "\n" + prompts["user_rag"])
    return prompts


def format_passages(passages: list[dict]) -> str:
    return "\n\n".join(f'<auszug id="{p["artikel_id"]}" titel="{p["titel"]}">\n{p["text"]}\n</auszug>' for p in passages)


def build_messages(prompts: dict, ticket_text: str, passages: list[dict] | None) -> list[dict]:
    if passages is None:
        user = prompts["user_llm"].format(ticket_text=ticket_text)
    else:
        user = prompts["user_rag"].format(ticket_text=ticket_text, passagen=format_passages(passages))
    return [{"role": "system", "content": prompts["system"]}, {"role": "user", "content": user}]


def parse_citations(text: str) -> dict:
    """Zitierte Artikel im Format [KB-xxx] und KB-IDs, die außerhalb dieses Formats vorkommen."""
    cited = sorted({k for m in CITATION.findall(text) for k in KB_ID.findall(m)})
    outside = KB_ID.findall(CITATION.sub(" ", text))
    return {"zitierte_artikel": cited, "kb_ids_ausserhalb_format": len(outside)}


def strip_citations(text: str) -> str:
    """Entfernt Belege im Format [KB-xxx] (für die verblindete Befragung, DEMI 2.4)."""
    text = CITATION.sub("", text)
    text = re.sub(r"[ \t]+([.,;:!?])", r"\1", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def generate_one(client, cfg: dict, prompts: dict, ticket: dict, bedingung: str, retriever=None) -> dict:
    """Ein Durchlauf für ein Ticket und eine Bedingung; gibt den Protokolleintrag nach DEMI 2.2 zurück."""
    g = cfg["generierung"]
    started = time.perf_counter()
    retrieval = None
    if bedingung == "rag":
        retrieval = retriever.retrieve(ticket["ticket_text"])
    messages = build_messages(prompts, ticket["ticket_text"], retrieval["passages"] if retrieval else None)

    t_gen = time.perf_counter()
    resp = client.chat.completions.create(
        model=g["modell"],
        messages=messages,
        temperature=g["temperatur"],
        max_completion_tokens=g["max_output_tokens"],
        seed=g["seed"],
        store=False,
    )
    finished = time.perf_counter()

    answer = resp.choices[0].message.content or ""
    usage = resp.usage
    cached = (usage.prompt_tokens_details.cached_tokens or 0) if usage.prompt_tokens_details else 0
    cost_gen = cost_usd(cfg, g["modell"], input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens, cached_tokens=cached)
    emb_tokens = retrieval["embedding_tokens"] if retrieval else 0
    cost_emb = cost_usd(cfg, cfg["embedding"]["modell"], input_tokens=emb_tokens)
    cites = parse_citations(answer)
    passage_ids = {p["artikel_id"] for p in retrieval["passages"]} if retrieval else set()

    return {
        "bedingung": bedingung,
        "modell_angefragt": g["modell"],
        "modell_antwort": resp.model,
        "system_fingerprint": resp.system_fingerprint,
        "temperatur": g["temperatur"],
        "max_output_tokens": g["max_output_tokens"],
        "seed": g["seed"],
        "prompt_hash": prompts["hash"],
        "ticket_text": ticket["ticket_text"],
        "retrieval": None if not retrieval else {
            "kandidaten": [{k: c[k] for k in ("chunk_id", "artikel_id", "rank_vector", "score_vector", "score_rerank",
                                              "rerank_input_tokens", "rerank_gekuerzt")} for c in retrieval["candidates"]],
            "passagen": [{k: p[k] for k in ("chunk_id", "artikel_id", "titel", "rank_rerank", "rank_vector",
                                            "score_vector", "score_rerank", "text")} for p in retrieval["passages"]],
        },
        "antwort": answer,
        "antwort_ohne_belege": strip_citations(answer),
        "finish_reason": resp.choices[0].finish_reason,
        **cites,
        "zitate_ausserhalb_kontext": sorted(set(cites["zitierte_artikel"]) - passage_ids) if retrieval else [],
        "input_tokens": usage.prompt_tokens,
        "cached_tokens": cached,
        "output_tokens": usage.completion_tokens,
        "embedding_tokens": emb_tokens,
        "latenz_ms": {
            **(retrieval["latency_ms"] if retrieval else {}),
            "retrieval_gesamt": round((t_gen - started) * 1000, 1),
            "generierung": round((finished - t_gen) * 1000, 1),
            "gesamt": round((finished - started) * 1000, 1),
        },
        "kosten_usd": {"generierung": cost_gen, "embedding": cost_emb, "gesamt": round(cost_gen + cost_emb, 8)},
    }
