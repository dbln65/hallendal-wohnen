"""Generiert die KB-Artikel für Hallendal Wohnen mit der Claude API.

Pro Artikel ein API-Aufruf. Jeder Aufruf wird in generation_log.jsonl
protokolliert (Modell, Einstellungen, Tokens, Hashes von Prompt und Steckbrief).

Beispiele:
    python generate_kb.py                    # alle fehlenden Artikel
    python generate_kb.py --ids KB-001 KB-016  # nur diese
    python generate_kb.py --ids KB-016 --force # neu generieren
    python generate_kb.py --dry-run --ids KB-001  # Prompt anzeigen, nichts senden
"""

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
STECKBRIEF = BASE / "steckbrief.md"
PLAN = BASE / "plan.csv"
SYSTEM_PROMPT = BASE / "prompts" / "system.txt"
USER_TEMPLATE = BASE / "prompts" / "user_template.txt"
KB_DIR = BASE / "kb"
LOG_FILE = BASE / "generation_log.jsonl"

# Standardwerte; per Umgebungsvariable überschreibbar.
MODEL = os.getenv("KB_MODEL", "claude-sonnet-5")
EFFORT = os.getenv("KB_EFFORT", "medium")  # low | medium | high
MAX_TOKENS = int(os.getenv("KB_MAX_TOKENS", "16000"))  # Obergrenze inkl. Thinking


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_plan() -> list[dict]:
    with PLAN.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_user_text(row: dict, template: str, stand: str) -> str:
    return template.format(
        id=row["id"],
        kategorie=row["kategorie"],
        titel=row["titel"],
        kernfakten=row["kernfakten"],
        laender="[" + ", ".join(row["laender"].split(",")) + "]",
        verwandte=", ".join(row["verwandte"].split(",")),
        stand=stand,
    )


def clean_output(text: str) -> str:
    """Entfernt eine eventuelle Code-Umrandung und Text vor dem Frontmatter."""
    text = text.strip()
    text = re.sub(r"^```(?:markdown|md)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    start = text.find("---")
    return text[start:].strip() + "\n" if start >= 0 else text + "\n"


def count_attempts(article_id: str) -> int:
    if not LOG_FILE.exists():
        return 0
    with LOG_FILE.open(encoding="utf-8") as f:
        return sum(1 for line in f if json.loads(line).get("id") == article_id)


def append_log(entry: dict) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", nargs="*", help="nur diese Artikel-IDs generieren")
    parser.add_argument("--force", action="store_true", help="vorhandene Artikel überschreiben")
    parser.add_argument("--dry-run", action="store_true", help="Prompt ausgeben statt API aufrufen")
    parser.add_argument("--stand", default=date.today().isoformat(), help="Stand-Datum im Frontmatter")
    args = parser.parse_args()

    steckbrief = STECKBRIEF.read_text(encoding="utf-8")
    system_prompt = SYSTEM_PROMPT.read_text(encoding="utf-8").strip()
    template = USER_TEMPLATE.read_text(encoding="utf-8")
    prompt_hash = sha256(system_prompt + "\n" + template)
    steckbrief_hash = sha256(steckbrief)

    plan = load_plan()
    if args.ids:
        wanted = set(args.ids)
        unknown = wanted - {r["id"] for r in plan}
        if unknown:
            sys.exit(f"Unbekannte IDs: {', '.join(sorted(unknown))}")
        plan = [r for r in plan if r["id"] in wanted]

    KB_DIR.mkdir(exist_ok=True)

    if not args.dry_run:
        import anthropic

        client = anthropic.Anthropic(max_retries=5)  # liest ANTHROPIC_API_KEY

    print(f"Modell: {MODEL} | Effort: {EFFORT} | Prompt {prompt_hash} | Steckbrief {steckbrief_hash}")

    for row in plan:
        out_path = KB_DIR / f"{row['id']}.md"
        if out_path.exists() and not args.force:
            print(f"{row['id']}: vorhanden, übersprungen (--force zum Überschreiben)")
            continue

        user_text = build_user_text(row, template, args.stand)
        if args.dry_run:
            print(f"\n===== {row['id']} =====\n[SYSTEM]\n{system_prompt}\n\n[USER]\n<steckbrief>…{len(steckbrief)} Zeichen…</steckbrief>\n\n{user_text}")
            continue

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "id": row["id"],
            "attempt": count_attempts(row["id"]) + 1,
            "model_requested": MODEL,
            "effort": EFFORT,
            "max_tokens": MAX_TOKENS,
            "prompt_hash": prompt_hash,
            "steckbrief_hash": steckbrief_hash,
        }
        started = time.monotonic()
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                output_config={"effort": EFFORT},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            # Steckbrief ist in allen 40 Aufrufen gleich -> Prompt-Caching
                            {
                                "type": "text",
                                "text": f"<steckbrief>\n{steckbrief}\n</steckbrief>",
                                "cache_control": {"type": "ephemeral"},
                            },
                            {"type": "text", "text": user_text},
                        ],
                    }
                ],
            )
        except Exception as exc:  # Fehler protokollieren und mit nächstem Artikel weitermachen
            entry.update(status="error", error=f"{type(exc).__name__}: {exc}")
            append_log(entry)
            print(f"{row['id']}: FEHLER {exc}")
            continue

        text = "".join(b.text for b in response.content if b.type == "text")
        usage = response.usage
        entry.update(
            model_response=response.model,
            stop_reason=response.stop_reason,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", None) or 0,
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None) or 0,
            duration_s=round(time.monotonic() - started, 2),
        )

        if response.stop_reason != "end_turn" or not text.strip():
            entry.update(status="incomplete")
            append_log(entry)
            print(f"{row['id']}: UNVOLLSTÄNDIG (stop_reason={response.stop_reason}), nicht gespeichert")
            continue

        article = clean_output(text)
        out_path.write_text(article, encoding="utf-8")
        entry.update(status="ok", output_file=str(out_path.relative_to(BASE)), output_hash=sha256(article))
        append_log(entry)
        print(
            f"{row['id']}: ok | in {usage.input_tokens} + cache {entry['cache_read_input_tokens']} "
            f"| out {usage.output_tokens} | {entry['duration_s']} s"
        )


if __name__ == "__main__":
    main()
