"""Strang 2: automatisierte Bewertung der Antwortentwürfe (LLM-as-a-Judge, DEMI 2.3 und Tabelle 13).

Je Antwortentwurf bis zu fünf Aufrufe des bewertenden Modells (J-01), jeweils mit strukturierter JSON-Ausgabe (J-07):

  A  Sachaussagen bestimmen und gegen die gesamte KB prüfen      -> KB-Supportedness (beide Bedingungen, H3)
  B  dieselben Aussagen gegen die übergebenen Auszüge prüfen     -> RAG-Faithfulness (nur RAG)
  C  übergebene Auszüge auf Erforderlichkeit prüfen              -> Context Relevance (nur RAG)
  D  drei Kundenanfragen aus dem Entwurf ableiten + Embeddings   -> Answer Relevance (beide)
  E  Vergleich mit der Musterantwort                             -> referenzbasierte Korrektheit (beide, H1)

Der Judge sieht die Entwürfe ohne Belege, bereinigt wie in der Befragung (J-02).

Aufruf (im Repo-Hauptverzeichnis; benötigt ANTHROPIC_API_KEY und OPENAI_API_KEY):
    python judge/judge.py --run pilot-03 --judge-run pilot-03-j1 --dry-run --ids P-02   # Prompts ansehen, ohne API
    python judge/judge.py --run pilot-03 --judge-run pilot-03-j1                        # Pilot (20 Entwürfe)
    python judge/judge.py --run haupt-01 --judge-run haupt-01-j1 --erlaube-haupt        # Hauptlauf (240 Entwürfe)
    python judge/judge.py --run haupt-01 --judge-run haupt-01-j1-wdh --erlaube-haupt --stabilitaet   # J-03

Ergebnis je Judge-Lauf in judge/runs/<judge-run>/:
- judge.jsonl        ein Eintrag je Entwurf: alle Urteile im Wortlaut, Kennzahlen, Tokens, Kosten
- judge_meta.json    Modell, Effort, Prompt-Hashes, KB-Hash, Git-Stand, Zeitraum, Summen
- errors.jsonl       fehlgeschlagene Entwürfe (werden beim nächsten Aufruf erneut versucht)
- uebersicht.md      lesbare Übersicht aller Urteile (nur Pilot- und Testläufe, nicht beim Hauptlauf; K-07)

Ein abgebrochener Lauf wird mit derselben --judge-run fortgesetzt; bewertete Entwürfe werden übersprungen.
Beim Hauptlauf gibt die Konsole keine Bewertungen aus, nur Fortschritt und Kosten (K-07).
"""

import argparse
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path

JUDGE_DIR = Path(__file__).resolve().parent
ROOT = JUDGE_DIR.parent
sys.path.insert(0, str(ROOT / "rag"))
sys.path.insert(0, str(ROOT / "umfrage"))
from common import git_info, kb_hash, load_config, now_iso  # noqa: E402
from prepare_survey import strip_citations  # noqa: E402  (gleiche Bereinigung wie in der Befragung, J-02)

MODELL = "claude-sonnet-5-5"          # J-01
PROMPT_VERSION = "v3"                 # J-11, J-12; bei jeder Änderung an Prompts oder Nachrichtenaufbau erhöhen
EFFORT = "medium"                     # J-06
MAX_TOKENS = 16000
EMBEDDING_MODELL = "text-embedding-3-small"   # wie im Retrieval (rag/config.yaml)
N_FRAGEN = 3                          # J-05
STAB_SEED = "20261020:stabilitaet"    # J-03
STAB_N = {"rag": 12, "llm": 12}
PREISE = {                            # USD je 1 Mio. Tokens, claude-sonnet-5-5 (Stichtag 2026-10-20)
    "stichtag": "2026-10-20", "quelle": "https://platform.claude.com/docs/en/about-claude/pricing",
    "input": 2.00, "cache_write": 2.50, "cache_read": 0.10, "output": 10.00,
}


def obj(props: dict, required: list) -> dict:
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


STR, BOOL, INT = {"type": "string"}, {"type": "boolean"}, {"type": "integer"}
SCHEMAS = {
    "aussagen_kb": obj({"aussagen": {"type": "array", "items": obj(
        {"aussage": STR, "begruendung": STR, "gedeckt": BOOL, "artikel": {"type": "array", "items": STR}},
        ["aussage", "begruendung", "gedeckt", "artikel"])}}, ["aussagen"]),
    "faithfulness": obj({"urteile": {"type": "array", "items": obj(
        {"nr": INT, "begruendung": STR, "ableitbar": BOOL}, ["nr", "begruendung", "ableitbar"])}}, ["urteile"]),
    "context_relevance": obj({"auszuege": {"type": "array", "items": obj(
        {"nr": INT, "begruendung": STR, "erforderlich": BOOL}, ["nr", "begruendung", "erforderlich"])}}, ["auszuege"]),
    "answer_relevance": obj({"fragen": {"type": "array", "items": STR}}, ["fragen"]),
    "korrektheit": obj({"fehlende_kernaussagen": {"type": "array", "items": STR}, "widersprueche": {"type": "array", "items": STR},
                        "begruendung": STR, "urteil": {"type": "string", "enum": ["korrekt", "teilweise", "falsch"]}},
                       ["fehlende_kernaussagen", "widersprueche", "begruendung", "urteil"]),
}


class JudgeFehler(Exception):
    pass


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_prompts() -> dict:
    prompts = {name: (JUDGE_DIR / "prompts" / f"{name}.txt").read_text(encoding="utf-8").strip() for name in SCHEMAS}
    prompts["_hashes"] = {name: sha(prompts[name] + json.dumps(SCHEMAS[name], sort_keys=True)) for name in SCHEMAS}
    return prompts


def kb_block() -> str:
    """KB im selben Format wie bei der Ticketerzeugung (rag/common.kb_hash)."""
    files = sorted((ROOT / "kb").glob("KB-*.md"))
    if len(files) != 40:
        sys.exit(f"FEHLER: {len(files)} KB-Artikel gefunden, erwartet 40.")
    parts = [f'<artikel id="{p.stem}">\n{p.read_text(encoding="utf-8").strip()}\n</artikel>' for p in files]
    return "<wissensdatenbank>\n" + "\n\n".join(parts) + "\n</wissensdatenbank>"


def auszuege(passagen: list) -> str:
    return "\n\n".join(f'<auszug nr="{i}" artikel="{p["artikel_id"]}">\n{p["text"].strip()}\n</auszug>'
                       for i, p in enumerate(passagen, start=1))


def nachrichten(name: str, ctx: dict) -> list:
    """Inhalt der Nutzernachricht je Aufruf; die KB steht vorn und wird gecacht."""
    anfrage = f"<kundenanfrage>\n{ctx['ticket_text']}\n</kundenanfrage>"
    entwurf = f"<antwortentwurf>\n{ctx['antwort']}\n</antwortentwurf>"
    if name == "aussagen_kb":
        return [{"type": "text", "text": ctx["kb"], "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": f"{anfrage}\n\n{entwurf}"}]
    if name == "faithfulness":
        liste = "\n".join(f"{i}. {a['aussage']}" for i, a in enumerate(ctx["aussagen"], start=1))
        return [{"type": "text", "text": f"{anfrage}\n\n<auszuege>\n{auszuege(ctx['passagen'])}\n</auszuege>\n\n<aussagen>\n{liste}\n</aussagen>"}]
    if name == "context_relevance":
        return [{"type": "text", "text": f"{anfrage}\n\n<auszuege>\n{auszuege(ctx['passagen'])}\n</auszuege>"}]
    if name == "answer_relevance":
        return [{"type": "text", "text": entwurf}]
    if name == "korrektheit":
        kern = "\n".join(f"- {k}" for k in ctx["kernaussagen"]) or "- (keine; Rückfrage bzw. Enthaltung erwartet)"
        ref = (f"<referenz>\nAntworttyp: {ctx['antworttyp']}\n\nKernaussagen der Musterantwort:\n{kern}\n\n"
               f"Musterantwort:\n{ctx['musterantwort']}\n</referenz>")
        return [{"type": "text", "text": f"{anfrage}\n\n{ref}\n\n{entwurf}"}]
    raise ValueError(name)


def kosten(u: dict) -> float:
    return round((u["input"] * PREISE["input"] + u["cache_write"] * PREISE["cache_write"]
                  + u["cache_read"] * PREISE["cache_read"] + u["output"] * PREISE["output"]) / 1e6, 8)


def aufruf(client, prompts: dict, name: str, ctx: dict, versuche: int = 2) -> tuple:
    """Ein Aufruf mit strukturierter Ausgabe; bei ungültiger Antwort ein weiterer Versuch."""
    letzter = None
    for _ in range(versuche):
        t0 = time.perf_counter()
        resp = client.messages.create(
            model=MODELL, max_tokens=MAX_TOKENS, system=prompts[name],
            messages=[{"role": "user", "content": nachrichten(name, ctx)}],
            output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMAS[name]}},
        )
        u = resp.usage
        usage = {"input": u.input_tokens, "cache_write": getattr(u, "cache_creation_input_tokens", 0) or 0,
                 "cache_read": getattr(u, "cache_read_input_tokens", 0) or 0, "output": u.output_tokens,
                 "latenz_s": round(time.perf_counter() - t0, 2), "modell_antwort": resp.model, "stop_reason": resp.stop_reason}
        usage["kosten_usd"] = kosten(usage)
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        if resp.stop_reason != "end_turn":
            letzter = f"{name}: stop_reason={resp.stop_reason}"
            continue
        try:
            return json.loads(text), usage
        except json.JSONDecodeError as exc:
            letzter = f"{name}: ungültiges JSON ({exc})"
    raise JudgeFehler(letzter)


def embeddings(oa_client, texte: list) -> tuple:
    resp = oa_client.embeddings.create(model=EMBEDDING_MODELL, input=texte)
    return [d.embedding for d in resp.data], resp.usage.total_tokens


def kosinus(a: list, b: list) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def bewerte(entry: dict, ticket: dict, kb: str, prompts: dict, client, oa_client, emb_preis: float) -> dict:
    rag = entry["bedingung"] == "rag"
    ctx = {"ticket_text": entry["ticket_text"], "antwort": strip_citations(entry["antwort"]), "kb": kb,
           "passagen": ((entry.get("retrieval") or {}).get("passagen") or []) if rag else [],
           "kernaussagen": ticket.get("kernaussagen") or [], "antworttyp": ticket.get("antworttyp", ""),
           "musterantwort": ticket.get("musterantwort", "")}
    if rag and len(ctx["passagen"]) != 3:
        raise JudgeFehler(f"{len(ctx['passagen'])} Auszüge statt 3")
    usage, out = {}, {}

    a, usage["aussagen_kb"] = aufruf(client, prompts, "aussagen_kb", ctx)
    ctx["aussagen"] = a["aussagen"]
    n = len(ctx["aussagen"])
    out.update(aussagen=ctx["aussagen"], n_aussagen=n,
               kb_supportedness=(sum(x["gedeckt"] for x in ctx["aussagen"]) / n) if n else None)

    if rag:
        if n:
            b, usage["faithfulness"] = aufruf(client, prompts, "faithfulness", ctx)
            nr = {u["nr"]: u for u in b["urteile"]}
            if sorted(nr) != list(range(1, n + 1)):
                raise JudgeFehler(f"faithfulness: Nummern {sorted(nr)} statt 1–{n}")
            out["faithfulness_urteile"] = [nr[i] for i in range(1, n + 1)]
            out["faithfulness"] = sum(u["ableitbar"] for u in out["faithfulness_urteile"]) / n
        else:
            out.update(faithfulness_urteile=[], faithfulness=None)
        c, usage["context_relevance"] = aufruf(client, prompts, "context_relevance", ctx)
        nr = {u["nr"]: u for u in c["auszuege"]}
        if sorted(nr) != [1, 2, 3]:
            raise JudgeFehler(f"context_relevance: Nummern {sorted(nr)} statt 1–3")
        out["context_urteile"] = [dict(nr[i], artikel=ctx["passagen"][i - 1]["artikel_id"]) for i in (1, 2, 3)]
        out["context_relevance"] = sum(u["erforderlich"] for u in out["context_urteile"]) / 3

    d, usage["answer_relevance"] = aufruf(client, prompts, "answer_relevance", ctx)
    fragen = [f.strip() for f in d["fragen"] if f.strip()][:N_FRAGEN]
    if not fragen:
        raise JudgeFehler("answer_relevance: keine Fragen")
    vecs, emb_tokens = embeddings(oa_client, [ctx["ticket_text"]] + fragen)
    cos = [kosinus(vecs[0], v) for v in vecs[1:]]
    out.update(fragen=fragen, kosinus=[round(c, 6) for c in cos], answer_relevance=sum(cos) / len(cos))
    usage["embedding"] = {"input": emb_tokens, "kosten_usd": round(emb_tokens * emb_preis / 1e6, 8)}

    e, usage["korrektheit"] = aufruf(client, prompts, "korrektheit", ctx)
    out.update(korrektheit=e["urteil"], korrektheit_detail=e)
    return {"antwort_bewertet": ctx["antwort"], **out, "usage": usage,
            "kosten_usd": round(sum(v["kosten_usd"] for v in usage.values()), 8)}


def uebersicht(rows: list, path: Path) -> None:
    """Lesbare Übersicht für den Pilot; beim Hauptlauf wird sie nicht erzeugt (K-07)."""
    pct = lambda x: "–" if x is None else f"{100 * x:.0f} %"  # noqa: E731
    lines = ["# Judge-Übersicht", ""]
    for r in sorted(rows, key=lambda r: (r["ticket_id"], r["bedingung"])):
        lines += [f"## {r['ticket_id']} · {r['bedingung'].upper()} · {r['kb_abdeckung']}", "",
                  f"Korrektheit: **{r['korrektheit']}** · KB-Supportedness: {pct(r['kb_supportedness'])} · "
                  + (f"Faithfulness: {pct(r.get('faithfulness'))} · Context Relevance: {pct(r.get('context_relevance'))} · "
                     if r["bedingung"] == "rag" else "") + f"Answer Relevance: {r['answer_relevance']:.3f}", "",
                  "**Kundenanfrage**", "", "> " + r["ticket_text"].replace("\n", "\n> "), "",
                  "**Bewerteter Entwurf**", "", "> " + r["antwort_bewertet"].replace("\n", "\n> "), "",
                  "**Sachaussagen**", ""]
        faith = r.get("faithfulness_urteile") or []
        for i, a in enumerate(r["aussagen"], start=1):
            f = f" · Auszüge: {'ja' if faith[i - 1]['ableitbar'] else 'nein'} ({faith[i - 1]['begruendung']})" if faith else ""
            lines.append(f"{i}. {a['aussage']} – KB: {'ja' if a['gedeckt'] else 'nein'} {', '.join(a['artikel'])} "
                         f"({a['begruendung']}){f}")
        if not r["aussagen"]:
            lines.append("– keine –")
        if r.get("context_urteile"):
            lines += ["", "**Auszüge**", ""] + [f"{u['nr']}. {u['artikel']}: {'erforderlich' if u['erforderlich'] else 'nicht erforderlich'} "
                                                 f"({u['begruendung']})" for u in r["context_urteile"]]
        k = r["korrektheit_detail"]
        lines += ["", "**Abgeleitete Anfragen**", ""] + [f"- {q} (Kosinus {c:.3f})" for q, c in zip(r["fragen"], r["kosinus"])]
        lines += ["", f"**Korrektheit:** {k['urteil']} – {k['begruendung']}",
                  f"Fehlend: {'; '.join(k['fehlende_kernaussagen']) or '–'} · Widersprüche: {'; '.join(k['widersprueche']) or '–'}", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="Lauf mit den Antwortentwürfen, z. B. pilot-03 oder haupt-01")
    ap.add_argument("--judge-run", required=True, help="Name des Judge-Laufs, z. B. pilot-03-j1")
    ap.add_argument("--ids", nargs="*", help="nur diese Tickets")
    ap.add_argument("--stabilitaet", action="store_true", help="nur die Stichprobe der Stabilitätsprüfung (J-03)")
    ap.add_argument("--dry-run", action="store_true", help="Prompts des ersten Entwurfs ausgeben, keine API-Aufrufe")
    ap.add_argument("--erlaube-haupt", action="store_true", help="Hauptlauf zulassen (nach Einfrieren, judge-v1.0)")
    args = ap.parse_args()

    haupt = args.run.startswith("haupt")
    if haupt and not args.erlaube_haupt and not args.dry_run:
        sys.exit("Hauptlauf nur mit --erlaube-haupt (erst nach Pilot und Einfrieren, Tag judge-v1.0).")
    with (ROOT / "rag" / "runs" / args.run / "responses.jsonl").open(encoding="utf-8") as f:
        entries = sorted((json.loads(line) for line in f), key=lambda e: (e["ticket_id"], e["bedingung"]))
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}
    if args.stabilitaet:
        rng = random.Random(STAB_SEED)
        wahl = {(e["ticket_id"], e["bedingung"]) for b, n in STAB_N.items()
                for e in rng.sample([x for x in entries if x["bedingung"] == b], n)}
        entries = [e for e in entries if (e["ticket_id"], e["bedingung"]) in wahl]
    if args.ids:
        entries = [e for e in entries if e["ticket_id"] in set(args.ids)]
    prompts, kb = load_prompts(), kb_block()

    if args.dry_run:
        e = entries[0]
        t = tickets[e["ticket_id"]]
        ctx = {"ticket_text": e["ticket_text"], "antwort": strip_citations(e["antwort"]), "kb": "<wissensdatenbank>…</wissensdatenbank>",
               "passagen": (e.get("retrieval") or {}).get("passagen") or [], "kernaussagen": t.get("kernaussagen") or [],
               "antworttyp": t.get("antworttyp", ""), "musterantwort": t.get("musterantwort", ""),
               "aussagen": [{"aussage": "(Beispielaussage aus Aufruf A)"}]}
        namen = ["aussagen_kb", "faithfulness", "context_relevance", "answer_relevance", "korrektheit"]
        for name in namen if e["bedingung"] == "rag" else ["aussagen_kb", "answer_relevance", "korrektheit"]:
            print(f"\n===== {e['ticket_id']} {e['bedingung']} | {name} =====\n[SYSTEM]\n{prompts[name]}\n\n[USER]")
            print("\n\n".join(b["text"] for b in nachrichten(name, ctx)))
        print(f"\nEntwürfe in diesem Lauf: {len(entries)} | KB: {len(kb)} Zeichen")
        return

    import anthropic
    from openai import OpenAI

    client, oa_client = anthropic.Anthropic(max_retries=5), OpenAI(max_retries=5)
    emb_preis = load_config()["preise_usd_pro_1m_tokens"][EMBEDDING_MODELL]["input"]
    out_dir = JUDGE_DIR / "runs" / args.judge_run
    out_dir.mkdir(parents=True, exist_ok=True)
    results, meta_path = out_dir / "judge.jsonl", out_dir / "judge_meta.json"
    config = {"modell": MODELL, "prompt_version": PROMPT_VERSION, "effort": EFFORT, "max_tokens": MAX_TOKENS, "embedding_modell": EMBEDDING_MODELL,
              "n_fragen": N_FRAGEN, "prompt_hashes": prompts["_hashes"], "kb_hash": kb_hash(ROOT / "kb")}
    config_hash = sha(json.dumps(config, sort_keys=True))
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta["config_hash"] != config_hash:
            sys.exit("FEHLER: Prompts, Modell oder KB weichen vom begonnenen Judge-Lauf ab. Neue --judge-run verwenden.")
    else:
        meta = {"judge_run": args.judge_run, "lauf": args.run, "stabilitaet": args.stabilitaet, "config": config,
                "config_hash": config_hash, "preise": PREISE, "embedding_preis_usd_pro_1m": emb_preis,
                "git": git_info(), "start": now_iso(), "responses_sha256": sha((ROOT / "rag" / "runs" / args.run / "responses.jsonl")
                                                                          .read_text(encoding="utf-8"))}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    done = set()
    if results.exists():
        with results.open(encoding="utf-8") as f:
            done = {(r["ticket_id"], r["bedingung"]) for r in map(json.loads, f)}
    todo = [e for e in entries if (e["ticket_id"], e["bedingung"]) not in done]
    print(f"Judge {MODELL} (Effort {EFFORT}) | Lauf {args.run} → {args.judge_run} | {len(todo)} offen, {len(done)} erledigt")

    for i, e in enumerate(todo, start=1):
        key = f"{e['ticket_id']} {e['bedingung']:3}"
        try:
            r = bewerte(e, tickets[e["ticket_id"]], kb, prompts, client, oa_client, emb_preis)
        except Exception as exc:  # protokollieren und mit dem nächsten Entwurf weitermachen
            with (out_dir / "errors.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"timestamp": now_iso(), "ticket_id": e["ticket_id"], "bedingung": e["bedingung"],
                                    "fehler": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False) + "\n")
            print(f"[{i}/{len(todo)}] {key} FEHLER {type(exc).__name__}: {exc}")
            continue
        row = {"judge_run": args.judge_run, "lauf": args.run, "ticket_id": e["ticket_id"], "bedingung": e["bedingung"],
               "kb_abdeckung": e.get("kb_abdeckung"), "kategorie": e.get("kategorie"), "schwierigkeit": e.get("schwierigkeit"),
               "timestamp": now_iso(), "config_hash": config_hash, "ticket_text": e["ticket_text"], **r}
        with results.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        tokens = sum(v.get("output", 0) for v in r["usage"].values())
        info = "" if haupt else (f" | {r['korrektheit']}, KB {r['kb_supportedness'] if r['kb_supportedness'] is None else round(r['kb_supportedness'], 2)}")
        print(f"[{i}/{len(todo)}] {key} ok | {tokens} Output-Tokens | {r['kosten_usd']:.4f} USD{info}")

    with results.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    meta.update(ende=now_iso(), n_bewertet=len(rows), n_erwartet=len(entries),
                summen={"kosten_usd": round(sum(r["kosten_usd"] for r in rows), 4),
                        "output_tokens": sum(v.get("output", 0) for r in rows for v in r["usage"].values()),
                        "cache_read_tokens": sum(v.get("cache_read", 0) for r in rows for v in r["usage"].values())})
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if not haupt:
        uebersicht(rows, out_dir / "uebersicht.md")
    offen = len(entries) - len(rows)
    print(f"\n{len(rows)}/{len(entries)} bewertet, {meta['summen']['kosten_usd']:.4f} USD gesamt"
          + (f" | {offen} offen: erneut aufrufen" if offen else "") + f" | {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
