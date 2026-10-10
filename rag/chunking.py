"""Vorverarbeitung und Chunking der KB-Artikel (ENTSCHEIDUNGEN.md, E-04 und E-05).

1. Frontmatter wird als Metadaten gelesen und aus dem Text entfernt.
2. Die H1-Überschrift entfällt, weil der Titel jedem Chunk vorangestellt wird.
3. Abschnitte aus config.kb.entferne_abschnitte (z. B. „Verwandte Artikel“) werden entfernt.
4. Der Text wird in Stücke fester Größe (in Tokens) mit Überlappung zerlegt; Grenzen liegen auf Wortgrenzen.

Aufruf zur Kontrolle ohne API und Datenbank:
    python rag/chunking.py                 # Übersicht je Artikel
    python rag/chunking.py --show KB-018   # alle Chunks eines Artikels im Wortlaut
"""

import argparse
import re
from pathlib import Path

import yaml

from common import ROOT, load_config


def get_token_counter(name: str):
    import tiktoken

    enc = tiktoken.get_encoding(name)
    return lambda text: len(enc.encode(text))


def parse_article(path: Path, remove_sections: list[str]) -> dict:
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", raw, flags=re.S)
    if not m:
        raise ValueError(f"{path.name}: kein Frontmatter gefunden")
    meta, body = yaml.safe_load(m.group(1)), m.group(2)
    body = re.sub(r"^\s*# .*\n", "", body, count=1)          # H1 = Titel
    for name in remove_sections:                             # Abschnitt bis zur nächsten ##-Überschrift
        body = re.sub(rf"(?ms)^## {re.escape(name)}\s*\n.*?(?=^## |\Z)", "", body)
    return {
        "artikel_id": meta["id"],
        "titel": meta["titel"],
        "kategorie": meta["kategorie"],
        "laender": meta.get("laender", []),
        "body": body.strip(),
    }


def split_spans(n_tokens: list[int], size: int, overlap: int) -> list[tuple[int, int]]:
    """Greedy: Wörter auffüllen bis `size` Tokens; der nächste Chunk beginnt `overlap` Tokens vor dem Ende."""
    spans, start, n = [], 0, len(n_tokens)
    while start < n:
        end, total = start, 0
        while end < n and (total + n_tokens[end] <= size or end == start):
            total += n_tokens[end]
            end += 1
        spans.append((start, end))
        if end >= n:
            break
        back, ov = end, 0
        while back > start + 1 and ov < overlap:              # mindestens ein Wort Fortschritt
            back -= 1
            ov += n_tokens[back]
        start = back
    return spans


def chunk_article(article: dict, cfg: dict, count) -> list[dict]:
    c = cfg["chunking"]
    words = re.findall(r"\S+\s*", article["body"])           # Wort inkl. folgendem Leerraum/Zeilenumbruch
    spans = split_spans([count(w) for w in words], c["chunk_tokens"], c["overlap_tokens"])
    chunks = []
    for i, (s, e) in enumerate(spans, start=1):
        body = "".join(words[s:e]).strip()
        text = f"{article['titel']}\n\n{body}" if c["titel_voranstellen"] else body
        chunks.append({
            "chunk_id": f"{article['artikel_id']}#{i}",
            "artikel_id": article["artikel_id"],
            "titel": article["titel"],
            "kategorie": article["kategorie"],
            "laender": article["laender"],
            "chunk_index": i,
            "text": text,                                   # wird eingebettet, gerankt und dem Modell übergeben
            "n_tokens": count(text),
        })
    return chunks


def build_chunks(cfg: dict, count) -> list[dict]:
    kb_dir = ROOT / cfg["kb"]["verzeichnis"]
    files = sorted(kb_dir.glob("KB-*.md"))
    if len(files) != 40:
        raise SystemExit(f"Erwartet 40 Artikel in {kb_dir}, gefunden: {len(files)}")
    chunks = []
    for path in files:
        chunks.extend(chunk_article(parse_article(path, cfg["kb"]["entferne_abschnitte"]), cfg, count))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--show", metavar="KB-ID", help="Chunks eines Artikels vollständig ausgeben")
    args = parser.parse_args()

    cfg = load_config()
    count = get_token_counter(cfg["chunking"]["tokenizer"])
    chunks = build_chunks(cfg, count)

    if args.show:
        for ch in (c for c in chunks if c["artikel_id"] == args.show):
            print(f"===== {ch['chunk_id']} ({ch['n_tokens']} Tokens) =====\n{ch['text']}\n")
        return

    c = cfg["chunking"]
    print(f"Chunk-Größe {c['chunk_tokens']} Tokens, Überlappung {c['overlap_tokens']}, Titel voranstellen: {c['titel_voranstellen']}\n")
    per_article = {}
    for ch in chunks:
        per_article.setdefault(ch["artikel_id"], []).append(ch["n_tokens"])
    for aid, toks in per_article.items():
        print(f"{aid}: {len(toks)} Chunks, Tokens {toks}")
    sizes = [ch["n_tokens"] for ch in chunks]
    print(f"\n{len(chunks)} Chunks aus {len(per_article)} Artikeln | Tokens je Chunk min {min(sizes)}, "
          f"Median {sorted(sizes)[len(sizes) // 2]}, max {max(sizes)} | gesamt {sum(sizes)}")


if __name__ == "__main__":
    main()
