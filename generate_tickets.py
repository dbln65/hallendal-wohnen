"""Generiert Tickets, Musterantworten, Kernaussagen und Belege mit der Claude API.

Grundlage ist ausschließlich die eingefrorene Knowledge Base (kb/), nicht der Steckbrief.
Pro Ticket ein API-Aufruf mit strukturierter JSON-Ausgabe. Ergebnis: tickets/<ID>.json.
Jeder Aufruf wird in ticket_generation_log.jsonl protokolliert.

Beispiele:
    python generate_tickets.py --dry-run --ids T-001
    python generate_tickets.py --ids T-001 T-045 T-073 T-120      # Probelauf
    python generate_tickets.py                                    # alle fehlenden (haupt + pilot)
    python generate_tickets.py --set pilot
    python generate_tickets.py --ids T-045 --force                # neu generieren
"""

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).parent
PLAN = BASE / "tickets_plan.csv"
KB_DIR = BASE / "kb"
OUT_DIR = BASE / "tickets"
SYSTEM_PROMPT = BASE / "prompts" / "ticket_system.txt"
USER_TEMPLATE = BASE / "prompts" / "ticket_user_template.txt"
LOG_FILE = BASE / "ticket_generation_log.jsonl"

MODEL = os.getenv("TICKET_MODEL", "claude-sonnet-5")
EFFORT = os.getenv("TICKET_EFFORT", "medium")
MAX_TOKENS = int(os.getenv("TICKET_MAX_TOKENS", "16000"))

SCHWIERIGKEIT_DEF = {  # DEMI 1.4.1
    "einfach": "eine eindeutige Sachfrage, vollständig durch einen KB-Artikel beantwortbar",
    "mittel": "Zusammenführung von Informationen aus mehreren KB-Artikeln erforderlich",
    "komplex": "mehrteilige Anfrage mit Bedingungen, Fristen oder Sonderfällen",
    "kb_gap": "die Knowledge Base enthält bewusst keine hinreichende Antwort",
}
STIL_DEF = {
    "sachlich": "vollständige, höfliche Anfrage",
    "umgangssprachlich": "Alltagssprache, einzelne Tippfehler, lockere Zeichensetzung",
    "unvollstaendig": "vage, ohne Nebenangaben wie Bestellnummer; entscheidende Information bleibt erkennbar",
    "veraergert": "verärgerter Ton, Beschwerde, aber ohne Beleidigungen",
}

SCHEMA = {
    "type": "object",
    "properties": {
        "ticket_text": {"type": "string"},
        "musterantwort": {"type": "string"},
        "antworttyp": {"type": "string", "enum": ["sachantwort", "rueckfrage"]},
        "kernaussagen": {"type": "array", "items": {"type": "string"}},
        "belege": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"artikel_id": {"type": "string"}, "zitat": {"type": "string"}},
                "required": ["artikel_id", "zitat"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["ticket_text", "musterantwort", "antworttyp", "kernaussagen", "belege"],
    "additionalProperties": False,
}


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_kb() -> str:
    files = sorted(KB_DIR.glob("KB-*.md"))
    if len(files) != 40:
        sys.exit(f"Erwartet 40 Artikel in {KB_DIR}, gefunden: {len(files)}")
    parts = [f'<artikel id="{p.stem}">\n{p.read_text(encoding="utf-8").strip()}\n</artikel>' for p in files]
    return "\n\n".join(parts)


def build_user_text(row: dict, template: str) -> str:
    return template.format(
        ticket_id=row["ticket_id"],
        kategorie=row["kategorie"],
        schwierigkeit=row["schwierigkeit"],
        schwierigkeit_def=SCHWIERIGKEIT_DEF[row["schwierigkeit"]],
        kb_abdeckung=row["kb_abdeckung"],
        ziel_artikel=", ".join(a for a in row["ziel_artikel"].split(";") if a) or "–",
        gap_thema=row["gap_thema"] or "–",
        stil=row["stil"],
        stil_def=STIL_DEF[row["stil"]],
        szenario=row["szenario"],
    )


def count_attempts(ticket_id: str) -> int:
    if not LOG_FILE.exists():
        return 0
    with LOG_FILE.open(encoding="utf-8") as f:
        return sum(1 for line in f if json.loads(line).get("ticket_id") == ticket_id)


def append_log(entry: dict) -> None:
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ids", nargs="*", help="nur diese Ticket-IDs")
    parser.add_argument("--set", choices=["haupt", "pilot", "alle"], default="alle")
    parser.add_argument("--force", action="store_true", help="vorhandene Tickets überschreiben")
    parser.add_argument("--dry-run", action="store_true", help="Prompt ausgeben statt API aufrufen")
    args = parser.parse_args()

    kb_text = load_kb()
    system_prompt = SYSTEM_PROMPT.read_text(encoding="utf-8").strip()
    template = USER_TEMPLATE.read_text(encoding="utf-8")
    prompt_hash = sha256(system_prompt + "\n" + template + json.dumps(SCHEMA, sort_keys=True))
    kb_hash = sha256(kb_text)

    with PLAN.open(encoding="utf-8") as f:
        plan = list(csv.DictReader(f))
    if args.set != "alle":
        plan = [r for r in plan if r["set"] == args.set]
    if args.ids:
        unknown = set(args.ids) - {r["ticket_id"] for r in plan}
        if unknown:
            sys.exit(f"Unbekannte IDs: {', '.join(sorted(unknown))}")
        plan = [r for r in plan if r["ticket_id"] in set(args.ids)]

    OUT_DIR.mkdir(exist_ok=True)
    if not args.dry_run:
        import anthropic

        client = anthropic.Anthropic(max_retries=5)  # liest ANTHROPIC_API_KEY

    print(f"Modell: {MODEL} | Effort: {EFFORT} | Prompt {prompt_hash} | KB {kb_hash}")

    for row in plan:
        tid = row["ticket_id"]
        out_path = OUT_DIR / f"{tid}.json"
        if out_path.exists() and not args.force:
            print(f"{tid}: vorhanden, übersprungen (--force zum Überschreiben)")
            continue

        user_text = build_user_text(row, template)
        if args.dry_run:
            print(f"\n===== {tid} =====\n[SYSTEM]\n{system_prompt}\n\n[USER]\n<knowledge_base>…{len(kb_text)} Zeichen…</knowledge_base>\n\n{user_text}")
            continue

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ticket_id": tid,
            "attempt": count_attempts(tid) + 1,
            "model_requested": MODEL,
            "effort": EFFORT,
            "max_tokens": MAX_TOKENS,
            "prompt_hash": prompt_hash,
            "kb_hash": kb_hash,
        }
        started = time.monotonic()
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=[
                    {
                        "role": "user",
                        "content": [
                            # KB ist in allen Aufrufen gleich -> Prompt-Caching
                            {
                                "type": "text",
                                "text": f"<knowledge_base>\n{kb_text}\n</knowledge_base>",
                                "cache_control": {"type": "ephemeral"},
                            },
                            {"type": "text", "text": user_text},
                        ],
                    }
                ],
            )
        except Exception as exc:
            entry.update(status="error", error=f"{type(exc).__name__}: {exc}")
            append_log(entry)
            print(f"{tid}: FEHLER {exc}")
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

        try:
            if response.stop_reason != "end_turn":
                raise ValueError(f"stop_reason={response.stop_reason}")
            data = json.loads(text)
        except (ValueError, json.JSONDecodeError) as exc:
            entry.update(status="incomplete", error=str(exc))
            append_log(entry)
            print(f"{tid}: UNVOLLSTÄNDIG ({exc}), nicht gespeichert")
            continue

        record = {
            "ticket_id": tid,
            "plan": {k: row[k] for k in row if k != "ticket_id"},
            **data,
            "meta": {
                "model": response.model,
                "effort": EFFORT,
                "prompt_hash": prompt_hash,
                "kb_hash": kb_hash,
                "generated_at": entry["timestamp"],
            },
        }
        out_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        entry.update(status="ok", output_file=str(out_path.relative_to(BASE)))
        append_log(entry)
        print(
            f"{tid}: ok | in {usage.input_tokens} + cache {entry['cache_read_input_tokens']} "
            f"| out {usage.output_tokens} | {entry['duration_s']} s"
        )


if __name__ == "__main__":
    main()
