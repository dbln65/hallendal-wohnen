"""Übersicht über alle protokollierten API-Aufrufe des Projekts, zum Abgleich mit den Nutzungsseiten von OpenAI und Anthropic.

Gelesen werden:
- OpenAI:    rag/runs/*/responses.jsonl (Generierung und Embedding je Antwortentwurf), rag/logs/index_log.jsonl (Indexierung)
- Anthropic: generation_log.jsonl (KB-Artikel), ticket_generation_log.jsonl (Tickets und Musterantworten)

Gruppiert wird nach Anbieter, Zweck, Modell und Kalendertag (UTC, wie auf den Nutzungsseiten). Für OpenAI stehen die
Kosten im Protokoll (Preisliste zum Stichtag, E-08). Für Anthropic enthält das Protokoll nur Tokens; der Abgleich
erfolgt deshalb über die Tokenzahlen.

Aufruf (im Repo-Hauptverzeichnis):
    python auswertung/api_nutzung.py

Ausgabe: auswertung/ergebnisse/api_nutzung/api_nutzung.md und api_nutzung.csv
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

AUSWERTUNG = Path(__file__).resolve().parent
ROOT = AUSWERTUNG.parent
OUT = AUSWERTUNG / "ergebnisse" / "api_nutzung"
FIELDS = ["anbieter", "zweck", "modell", "tag_utc", "aufrufe", "input_tokens", "cache_tokens", "output_tokens", "kosten_usd"]


def read_jsonl(path: Path) -> list:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def de(x, nd=0) -> str:
    return f"{x:,.{nd}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def main() -> None:
    rows = defaultdict(lambda: {"aufrufe": 0, "input_tokens": 0, "cache_tokens": 0, "output_tokens": 0, "kosten_usd": 0.0})

    def add(anbieter, zweck, modell, ts, n=1, inp=0, cache=0, out=0, usd=None):
        r = rows[(anbieter, zweck, modell, (ts or "")[:10])]
        r["aufrufe"] += n
        r["input_tokens"] += inp
        r["cache_tokens"] += cache
        r["output_tokens"] += out
        if usd is None:
            r["kosten_usd"] = None
        elif r["kosten_usd"] is not None:
            r["kosten_usd"] += usd

    # OpenAI: Antwortentwürfe aller Läufe
    for resp in sorted((ROOT / "rag" / "runs").glob("*/responses.jsonl")):
        run = resp.parent.name
        for e in read_jsonl(resp):
            k = e.get("kosten_usd") or {}
            add("OpenAI", f"Lauf {run}: Generierung", e.get("modell_antwort") or e.get("modell_angefragt", "?"), e.get("timestamp"),
                inp=e.get("input_tokens", 0) - e.get("cached_tokens", 0), cache=e.get("cached_tokens", 0),
                out=e.get("output_tokens", 0),
                usd=k.get("generierung", k.get("gesamt", 0)))
            if e.get("embedding_tokens"):
                add("OpenAI", f"Lauf {run}: Embedding der Anfrage", "text-embedding-3-small", e.get("timestamp"),
                    inp=e["embedding_tokens"], usd=k.get("embedding", 0))
    # OpenAI: Indexierung
    for e in read_jsonl(ROOT / "rag" / "logs" / "index_log.jsonl"):
        add("OpenAI", "Indexierung der KB", e.get("embedding_model", "?"), e.get("timestamp"),
            inp=e.get("embedding_tokens", 0), usd=e.get("cost_usd", 0))
    # Anthropic: KB- und Ticketgenerierung (nur erfolgreiche oder unvollständige Antworten haben Tokens)
    for name, zweck in (("generation_log.jsonl", "KB-Artikel erzeugen"), ("ticket_generation_log.jsonl", "Tickets erzeugen")):
        for e in read_jsonl(ROOT / name):
            if "input_tokens" not in e:
                add("Anthropic", zweck + " (Fehler, ohne Tokens)", e.get("model_requested", "?"), e.get("timestamp"), usd=None)
                continue
            add("Anthropic", zweck, e.get("model_response") or e.get("model_requested", "?"), e.get("timestamp"),
                inp=e["input_tokens"] + e.get("cache_creation_input_tokens", 0), cache=e.get("cache_read_input_tokens", 0),
                out=e["output_tokens"], usd=None)

    data = [dict(zip(FIELDS[:4], k), **v) for k, v in sorted(rows.items())]
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "api_nutzung.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in data:
            w.writerow({**r, "kosten_usd": "" if r["kosten_usd"] is None else round(r["kosten_usd"], 6)})

    lines = ["# Protokollierte API-Nutzung", "",
             "Tag in UTC. Input = Eingabetokens ohne Cache-Treffer (bei Anthropic einschließlich Cache-Schreibvorgängen), "
             "Cache = Cache-Treffer; Input + Cache ergibt alle Eingabetokens. "
             "Kosten nur für OpenAI (Preisliste zum Stichtag); für Anthropic über die Tokenzahlen abgleichen.", ""]
    for anbieter in ("OpenAI", "Anthropic"):
        part = [r for r in data if r["anbieter"] == anbieter]
        if not part:
            continue
        lines += [f"## {anbieter}", "", "| Tag | Zweck | Modell | Aufrufe | Input | Cache | Output | Kosten (USD) |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in sorted(part, key=lambda r: (r["tag_utc"], r["zweck"])):
            usd = "–" if r["kosten_usd"] is None else de(r["kosten_usd"], 4)
            lines.append(f"| {r['tag_utc']} | {r['zweck']} | {r['modell']} | {r['aufrufe']} | {de(r['input_tokens'])} | "
                         f"{de(r['cache_tokens'])} | {de(r['output_tokens'])} | {usd} |")
        total = {k: sum(r[k] for r in part) for k in ("aufrufe", "input_tokens", "cache_tokens", "output_tokens")}
        usd_total = sum(r["kosten_usd"] or 0 for r in part) if anbieter == "OpenAI" else None
        lines.append(f"| **gesamt** | | | {total['aufrufe']} | {de(total['input_tokens'])} | {de(total['cache_tokens'])} | "
                     f"{de(total['output_tokens'])} | {'–' if usd_total is None else '**' + de(usd_total, 4) + '**'} |")
        lines.append("")
    lines += ["## Nicht protokolliert", "",
              "- je ein Aufwärmaufruf (Embedding und Generierung) vor jedem Lauf von `rag/generate.py`",
              "- Probeaufrufe mit `--dry-run` und API-Schlüssel (nur Embeddings)",
              "- Embeddings der Tickets beim Retrieval-Vergleich (`rag/eval_retrieval.py`)",
              "- Aufrufe außerhalb der Skripte (z. B. Tests in der Konsole oder Workbench)", ""]
    (OUT / "api_nutzung.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"Geschrieben: {OUT.relative_to(ROOT)}/api_nutzung.md, api_nutzung.csv")


if __name__ == "__main__":
    main()
