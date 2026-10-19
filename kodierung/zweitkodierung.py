"""Erzeugt das Material für die Zweitkodierung (K-06): 48 Entwürfe mit vorgegebenen Kernaussagen der Erstkodierung.

Voraussetzungen:
- kodierung/kodiertabelle.xlsx ist vollständig und besteht pruefe_kodierung.py ohne Fehler
- kodierung/stichprobe_zweitkodierung.csv und kodierung/kodier_meta.json aus prepare_coding.py

Aufruf (im Repo-Hauptverzeichnis):
    python kodierung/zweitkodierung.py

Ausgabe in kodierung/zweitkodierung/ (nur diesen Ordner an die Zweitkodierperson geben, dazu LEITFADEN.md und AUSLEGUNGEN.md):
- kodierheft.html            die 48 Entwürfe in Kodierreihenfolge, KB im Anhang (gleiches Material wie in der Erstkodierung)
- kodiertabelle_zweit.xlsx   K1–K3 vorgegeben; C1, C2, C3, mangel und Fehlertypen leer
- zweit_meta.json            Herkunft: Hashes von Erstkodierung, Stichprobe und Lauf, Git-Stand
Die Codes der Erstkodierung enthält keine dieser Dateien.
"""

import csv
import json
import random
import sys
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, PatternFill

from prepare_coding import (KODIER_DIR, N_ZWEIT, ROOT, SEED, build_html, build_xlsx, file_hash,  # noqa: E402
                            git_info, load_kb, now_iso)
from pruefe_kodierung import pruefe  # noqa: E402

RUN = "haupt-01"
OUT = KODIER_DIR / "zweitkodierung"
GIVEN = PatternFill("solid", fgColor="DDEBF7")


def main() -> None:
    erst = KODIER_DIR / "kodiertabelle.xlsx"
    git_state = git_info()
    data, fehler, _ = pruefe(erst)
    if fehler:
        sys.exit(f"FEHLER: {erst.name} hat {sum(len(v) for v in fehler.values())} Fehler. "
                 "Erst python kodierung/pruefe_kodierung.py ausführen und beheben.")
    erst_rows = {str(d["kodier_id"]).strip(): d for d in data}

    meta_erst = json.loads((KODIER_DIR / "kodier_meta.json").read_text(encoding="utf-8"))
    responses = ROOT / "rag" / "runs" / RUN / "responses.jsonl"
    errors = []
    if meta_erst.get("lauf") != RUN:
        errors.append(f"kodier_meta.json gehört zu Lauf {meta_erst.get('lauf')}, erwartet {RUN}")
    if file_hash(responses) != meta_erst.get("responses_sha256"):
        errors.append("responses.jsonl hat sich seit prepare_coding.py geändert")
    if file_hash(ROOT / "tickets.jsonl") != meta_erst.get("tickets_jsonl_sha256"):
        errors.append("tickets.jsonl hat sich seit prepare_coding.py geändert")

    with responses.open(encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}
    kb = load_kb()

    # Kodierreihenfolge wie in prepare_coding.py rekonstruieren und gegen die Erstkodierung prüfen
    order = sorted(entries, key=lambda e: (e["ticket_id"], e["bedingung"]))
    random.Random(SEED).shuffle(order)
    items = [{"kodier_id": f"K{n:03d}", "ticket_id": e["ticket_id"], "bedingung": e["bedingung"],
              "kb_abdeckung": e["kb_abdeckung"], "schwierigkeit": e["schwierigkeit"], "entry": e}
             for n, e in enumerate(order, start=1)]
    for it in items:
        d = erst_rows.get(it["kodier_id"])
        if not d or (str(d["ticket_id"]).strip(), str(d["bedingung"]).strip()) != (it["ticket_id"], it["bedingung"]):
            errors.append(f"{it['kodier_id']}: Ticket/Bedingung weichen von der Erstkodierung ab")

    with (KODIER_DIR / "stichprobe_zweitkodierung.csv").open(encoding="utf-8") as f:
        stichprobe = list(csv.DictReader(f))
    rng = random.Random(f"{SEED}:zweitkodierung")
    neu = sorted(it["kodier_id"] for bed, n in N_ZWEIT.items()
                 for it in rng.sample([x for x in items if x["bedingung"] == bed], n))
    if sorted(r["kodier_id"] for r in stichprobe) != neu:
        errors.append("stichprobe_zweitkodierung.csv entspricht nicht der Ziehung mit Seed (K-06)")
    if errors:
        sys.exit("FEHLER:\n" + "\n".join(errors))

    ids = {r["kodier_id"] for r in stichprobe}
    subset = [it for it in items if it["kodier_id"] in ids]
    OUT.mkdir(exist_ok=True)

    html = build_html(subset, tickets, kb, RUN)
    replacements = {
        f"<title>Kodierheft {RUN}</title>": "<title>Kodierheft Zweitkodierung</title>",
        f"<h1 id='top'>Kodierheft – Lauf {RUN}</h1>": "<h1 id='top'>Kodierheft Zweitkodierung</h1>",
        "Reihenfolge = Kodierreihenfolge (K-05).": f"{len(subset)} Entwürfe der Zweitkodierung (K-06) in Kodierreihenfolge. "
                                                   "Die Kernaussagen sind in kodiertabelle_zweit.xlsx vorgegeben.",
        "Regeln: LEITFADEN.md. Codes in kodiertabelle.xlsx eintragen.": "Regeln: LEITFADEN.md und AUSLEGUNGEN.md. "
                                                                         "Codes in kodiertabelle_zweit.xlsx eintragen.",
    }
    for old, new in replacements.items():
        if old not in html:
            sys.exit(f"FEHLER: Textbaustein im Kodierheft nicht gefunden: {old}")
        html = html.replace(old, new)
    (OUT / "kodierheft.html").write_text(html, encoding="utf-8")

    table = OUT / "kodiertabelle_zweit.xlsx"
    build_xlsx(subset, table)
    wb = openpyxl.load_workbook(table)
    ws = wb["Kodierung"]
    col = {c.value: c.column for c in ws[1]}
    n_k = 0
    for r in range(2, ws.max_row + 1):
        d = erst_rows[ws.cell(r, col["kodier_id"]).value]
        for i in (1, 2, 3):
            k = str(d[f"K{i}"]).strip() if d[f"K{i}"] else ""
            cell = ws.cell(r, col[f"K{i}"], k or None)
            cell.fill = GIVEN
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            n_k += bool(k)
            if not k and ws.cell(r, col["bedingung"]).value == "llm":
                ws.cell(r, col[f"K{i}_C2"]).value = None   # nur bei vorhandener Kernaussage vorbelegt
    codes = wb["Codes"]
    codes.cell(2, 3).value = ("vorgegeben aus der Erstkodierung (K-06), blau hinterlegt, nicht ändern; "
                              "leer, wenn die Erstkodierung keine Kernaussage festgestellt hat")
    wb.save(table)

    meta = {"erzeugt": now_iso(), "skript": "kodierung/zweitkodierung.py", "git": git_state, "lauf": RUN,
            "erstkodierung_sha256": file_hash(erst),
            "stichprobe_sha256": file_hash(KODIER_DIR / "stichprobe_zweitkodierung.csv"),
            "responses_sha256": file_hash(responses),
            "anzahl": {"entwuerfe": len(subset), "rag": sum(it["bedingung"] == "rag" for it in subset),
                       "kernaussagen_vorgegeben": n_k},
            "ausgaben": {n: file_hash(OUT / n) for n in ("kodierheft.html", "kodiertabelle_zweit.xlsx")}}
    (OUT / "zweit_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rel = OUT.relative_to(ROOT)
    print(f"{len(subset)} Entwürfe ({meta['anzahl']['rag']} RAG), {n_k} Kernaussagen aus der Erstkodierung vorgegeben")
    print(f"Geschrieben: {rel}/kodierheft.html, {rel}/kodiertabelle_zweit.xlsx, {rel}/zweit_meta.json")
    print("Weitergeben: nur den Ordner zweitkodierung/ sowie LEITFADEN.md und AUSLEGUNGEN.md, nicht kodiertabelle.xlsx.")


if __name__ == "__main__":
    main()
