"""Strang 1: Auswertung der automatisierten Protokollierung (DEMI 2.2 und Tabelle 13).

Beschreibt den Hauptlauf je Bedingung: Tokenverbrauch, Kosten je Anfrage und Latenz, dazu die Trefferquote
des Retrievals (Belegartikel unter den übergebenen Top-3) und die Prüfung der Datenqualität. Es gibt hier keine
Hypothesentests; die Werte sind beschreibend und liefern die variablen Kosten je Ticket für Teilstudie B.

Aufruf (im Repo-Hauptverzeichnis):
    python auswertung/strang1.py --usd-eur 1.0950        # Beispielwert; EZB-Referenzkurs zum Stichtag eintragen

--usd-eur ist der EZB-Referenzkurs in US-Dollar je Euro zum Preisstichtag (config.yaml, E-08). Fällt der Stichtag
auf ein Wochenende, gilt der letzte veröffentlichte Kurs davor (--kurs-datum).

Ausgabe in auswertung/ergebnisse/strang1/:
- bericht.md        Tabellen und Kennzahlen für das EVI
- kennzahlen.csv    je Bedingung und Größe: n, Median, Quartile, Mittelwert, P90, Summe
- paare.csv         je Ticket: Differenz RAG minus LLM-only (Tokens, Kosten, Latenz)
- retrieval.csv     je KB-gedecktem Ticket: Belegartikel, übergeben (Top-3), unter den Kandidaten (Top-5)
- strang1.png       Abbildung: Latenz und Kosten je Anfrage nach Bedingung
- meta.json         Herkunft: Lauf, Hashes, Wechselkurs, Git-Stand, Bibliotheksversionen
"""

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

AUSWERTUNG = Path(__file__).resolve().parent
ROOT = AUSWERTUNG.parent
sys.path.insert(0, str(ROOT / "rag"))
from common import git_info, now_iso  # noqa: E402

FARBE = {"rag": "#2a78d6", "llm": "#eb6834"}          # Kategorialpalette, Slots 1 und 2
NAME = {"rag": "RAG", "llm": "LLM-only"}
TEXT, TEXT2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def de(x, nd=1) -> str:
    """Zahl im deutschen Format (Tausenderpunkt, Dezimalkomma)."""
    return f"{x:,.{nd}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def kennwerte(values: list) -> dict:
    v = sorted(values)
    q = statistics.quantiles(v, n=4, method="inclusive") if len(v) > 1 else [v[0]] * 3
    p90 = statistics.quantiles(v, n=10, method="inclusive")[8] if len(v) > 1 else v[0]
    return {"n": len(v), "median": q[1], "q1": q[0], "q3": q[2], "iqr": q[2] - q[0],
            "mittel": statistics.fmean(v), "p90": p90, "min": v[0], "max": v[-1], "summe": sum(v)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", default="haupt-01")
    ap.add_argument("--usd-eur", type=float, required=True, help="EZB-Referenzkurs: US-Dollar je 1 Euro")
    ap.add_argument("--kurs-datum", default="2026-10-09", help="Datum des verwendeten EZB-Referenzkurses")
    args = ap.parse_args()

    run_dir = ROOT / "rag" / "runs" / args.run
    responses = run_dir / "responses.jsonl"
    out = AUSWERTUNG / "ergebnisse" / "strang1"
    git_state = git_info()
    with responses.open(encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}

    # Datenqualität
    by_key = {(e["ticket_id"], e["bedingung"]): e for e in entries}
    ids = sorted({e["ticket_id"] for e in entries})
    errors = []
    if len(by_key) != len(entries):
        errors.append("doppelte Einträge (Ticket, Bedingung)")
    errors += [f"{t}: Bedingung fehlt" for t in ids for b in ("rag", "llm") if (t, b) not in by_key]
    if errors:
        sys.exit("FEHLER:\n" + "\n".join(errors))
    err_file = run_dir / "errors.jsonl"
    n_fehlversuche = sum(1 for _ in err_file.open(encoding="utf-8")) if err_file.exists() else 0
    finish = Counter((e["bedingung"], e.get("finish_reason")) for e in entries)
    modelle = Counter(e.get("modell_antwort") for e in entries)
    fingerprints = Counter(e.get("system_fingerprint") for e in entries)

    # Größen je Eintrag
    def werte(e: dict) -> dict:
        lat = e["latenz_ms"]
        return {
            "input_tokens": e["input_tokens"],
            "output_tokens": e["output_tokens"],
            "cached_tokens": e.get("cached_tokens", 0),
            "embedding_tokens": e.get("embedding_tokens", 0),
            "kosten_usd": e["kosten_usd"]["gesamt"],
            "kosten_generierung_usd": e["kosten_usd"].get("generierung", e["kosten_usd"]["gesamt"]),
            "kosten_embedding_usd": e["kosten_usd"].get("embedding", 0),
            "kosten_eur": e["kosten_usd"]["gesamt"] / args.usd_eur,
            "latenz_s": lat["gesamt"] / 1000,
            "latenz_generierung_s": lat["generierung"] / 1000,
            "latenz_retrieval_s": lat.get("retrieval_gesamt", 0) / 1000,
            "latenz_embedding_s": lat.get("embedding", 0) / 1000,
            "latenz_suche_s": lat.get("search", 0) / 1000,
            "latenz_rerank_s": lat.get("rerank", 0) / 1000,
        }

    rows = {k: werte(e) for k, e in by_key.items()}
    groessen = list(next(iter(rows.values())).keys())
    stats = {b: {g: kennwerte([rows[(t, b)][g] for t in ids]) for g in groessen} for b in ("rag", "llm")}
    diff = {g: kennwerte([rows[(t, "rag")][g] - rows[(t, "llm")][g] for t in ids]) for g in groessen}

    # Retrieval-Trefferquote (nur KB-gedeckte Tickets mit Belegartikeln)
    ret_rows = []
    for t in ids:
        tk, e = tickets[t], by_key[(t, "rag")]
        beleg = tk.get("belegartikel") or []
        if tk.get("kb_abdeckung") != "gedeckt" or not beleg:
            continue
        r = e.get("retrieval") or {}
        top3 = {p["artikel_id"] for p in r.get("passagen", [])}
        top5 = {c["artikel_id"] for c in r.get("kandidaten", [])}
        ret_rows.append({"ticket_id": t, "kategorie": tk.get("kategorie", ""), "schwierigkeit": tk.get("schwierigkeit", ""),
                         "belegartikel": ";".join(beleg), "uebergeben_top3": ";".join(sorted(top3)),
                         "kandidaten_top5": ";".join(sorted(top5)),
                         "treffer_min1_top3": int(bool(top3 & set(beleg))), "treffer_alle_top3": int(set(beleg) <= top3),
                         "treffer_min1_top5": int(bool(top5 & set(beleg))), "treffer_alle_top5": int(set(beleg) <= top5)})
    n_ret = len(ret_rows)

    def quote(key, rows_=None):
        rows_ = ret_rows if rows_ is None else rows_
        return sum(r[key] for r in rows_), len(rows_)

    out.mkdir(parents=True, exist_ok=True)
    with (out / "kennzahlen.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bedingung", "groesse", "n", "median", "q1", "q3", "iqr", "mittel", "p90", "min", "max", "summe"])
        for b in ("rag", "llm"):
            for g in groessen:
                s = stats[b][g]
                w.writerow([b, g] + [round(s[k], 8) for k in ("n", "median", "q1", "q3", "iqr", "mittel", "p90", "min", "max", "summe")])
        for g in groessen:
            s = diff[g]
            w.writerow(["differenz_rag_minus_llm", g] + [round(s[k], 8) for k in ("n", "median", "q1", "q3", "iqr", "mittel", "p90", "min", "max", "summe")])
    with (out / "paare.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        keys = ["input_tokens", "output_tokens", "kosten_eur", "latenz_s"]
        w.writerow(["ticket_id", "kb_abdeckung"] + [f"{k}_{b}" for k in keys for b in ("rag", "llm")] + [f"diff_{k}" for k in keys])
        for t in ids:
            w.writerow([t, tickets[t].get("kb_abdeckung", "")]
                       + [round(rows[(t, b)][k], 8) for k in keys for b in ("rag", "llm")]
                       + [round(rows[(t, "rag")][k] - rows[(t, "llm")][k], 8) for k in keys])
    with (out / "retrieval.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(ret_rows[0].keys()) if ret_rows else ["ticket_id"])
        w.writeheader()
        w.writerows(ret_rows)

    # Abbildung
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None
        print("Hinweis: matplotlib fehlt, Abbildung übersprungen (pip install matplotlib)")
    if plt:
        plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": TEXT2, "axes.labelcolor": TEXT2,
                             "xtick.color": TEXT2, "ytick.color": TEXT2, "text.color": TEXT})
        fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.7), dpi=300)
        panels = [("latenz_s", "Latenz je Anfrage (s)", 1),
                  ("kosten_eur", "Kosten je 1.000 Anfragen (€)", 1000)]
        for ax, (g, titel, faktor) in zip(axes, panels):
            data = [[rows[(t, b)][g] * faktor for t in ids] for b in ("rag", "llm")]
            bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=True,
                            medianprops={"color": TEXT, "linewidth": 1.4},
                            whiskerprops={"color": TEXT2, "linewidth": 1}, capprops={"color": TEXT2, "linewidth": 1},
                            flierprops={"marker": "o", "markersize": 3, "markerfacecolor": "none", "markeredgecolor": TEXT2})
            for patch, b in zip(bp["boxes"], ("rag", "llm")):
                patch.set_facecolor(FARBE[b])
                patch.set_alpha(0.35)
                patch.set_edgecolor(FARBE[b])
                patch.set_linewidth(1.2)
            ax.set_xticks([1, 2], [f"{NAME['rag']}\n(n = {len(ids)})", f"{NAME['llm']}\n(n = {len(ids)})"])
            ax.set_title(titel, fontsize=9, color=TEXT, loc="left")
            ax.yaxis.grid(True, color=GRID, linewidth=0.6)
            ax.set_axisbelow(True)
            ax.set_ylim(bottom=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
            ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: de(v, 1 if v < 10 else 0)))
        fig.tight_layout()
        fig.savefig(out / "strang1.png", facecolor="white")
        plt.close(fig)

    # Bericht
    s_r, s_l, d = stats["rag"], stats["llm"], diff
    k_rag_eur = s_r["kosten_eur"]["mittel"]

    def zeile(label, g, nd=0, faktor=1):
        a, b = s_r[g], s_l[g]
        return (f"| {label} | {de(a['median'] * faktor, nd)} ({de(a['q1'] * faktor, nd)}–{de(a['q3'] * faktor, nd)}) | "
                f"{de(b['median'] * faktor, nd)} ({de(b['q1'] * faktor, nd)}–{de(b['q3'] * faktor, nd)}) | "
                f"{de(d[g]['median'] * faktor, nd)} |")

    m1, n1 = quote("treffer_min1_top3")
    m2, _ = quote("treffer_alle_top3")
    m3, _ = quote("treffer_min1_top5")
    m4, _ = quote("treffer_alle_top5")
    pct = lambda a, b: de(100 * a / b, 1) if b else "–"  # noqa: E731
    lines = [
        f"# Strang 1: Protokollierung – Lauf {args.run}",
        "",
        f"Erzeugt mit `auswertung/strang1.py` am {now_iso()[:10]}. Kosten in Euro umgerechnet mit dem EZB-Referenzkurs "
        f"{de(args.usd_eur, 4)} USD je Euro vom {args.kurs_datum}.",
        "",
        "## Datenqualität",
        "",
        f"- Einträge: {len(entries)} ({len(ids)} Tickets × 2 Bedingungen), fehlgeschlagene Aufrufe laut errors.jsonl: {n_fehlversuche}",
        "- Abbruchgrund der Generierung: " + ", ".join(f"{NAME[b]} {r}: {n}" for (b, r), n in sorted(finish.items(), key=str)),
        "- Modellversion laut Antwort: " + ", ".join(f"{m} ({n})" for m, n in modelle.items()),
        f"- verschiedene system_fingerprint-Werte: {len(fingerprints)}",
        "",
        "## Tabelle: Tokenverbrauch, Kosten und Latenz je Anfrage",
        "",
        "Median (Interquartilsbereich Q1–Q3); letzte Spalte: Median der Differenz RAG minus LLM-only je Ticket.",
        "",
        "| Größe | RAG | LLM-only | Differenz (Median) |",
        "| --- | --- | --- | --- |",
        zeile("Input-Tokens", "input_tokens"),
        zeile("Output-Tokens", "output_tokens"),
        zeile("Embedding-Tokens", "embedding_tokens"),
        zeile("Kosten je 1.000 Anfragen (€)", "kosten_eur", 3, 1000),
        zeile("Latenz gesamt (s)", "latenz_s", 2),
        zeile("davon Generierung (s)", "latenz_generierung_s", 2),
        zeile("davon Retrieval (s)", "latenz_retrieval_s", 2),
        "",
        "## Kosten",
        "",
        f"- Mittlere Kosten je Anfrage: RAG {de(s_r['kosten_eur']['mittel'] * 1000, 3)} € je 1.000 Anfragen, "
        f"LLM-only {de(s_l['kosten_eur']['mittel'] * 1000, 3)} € je 1.000 Anfragen "
        f"(Faktor {de(s_r['kosten_eur']['mittel'] / s_l['kosten_eur']['mittel'], 2)}).",
        f"- **Variable Kosten je Ticket für Teilstudie B (RAG, Mittelwert): {de(k_rag_eur, 6)} €** "
        f"({de(k_rag_eur * 1000, 3)} € je 1.000 Tickets). Der Mittelwert ist hier die passende Größe, weil sich Kosten "
        "über das Ticketvolumen aufsummieren.",
        "",
        f"Gesamtkosten des Laufs {args.run} (Summe über alle {len(entries)} protokollierten Aufrufe, Preisliste zum Stichtag):",
        "",
        "| | RAG | LLM-only | gesamt |",
        "| --- | --- | --- | --- |",
        *[f"| {label} (USD) | {de(s_r[g]['summe'], 4)} | {de(s_l[g]['summe'], 4)} | {de(s_r[g]['summe'] + s_l[g]['summe'], 4)} |"
          for label, g in (("Generierung", "kosten_generierung_usd"), ("Embedding der Anfrage", "kosten_embedding_usd"),
                           ("**gesamt**", "kosten_usd"))],
        f"| **gesamt (€)** | {de(s_r['kosten_eur']['summe'], 4)} | {de(s_l['kosten_eur']['summe'], 4)} | "
        f"{de(s_r['kosten_eur']['summe'] + s_l['kosten_eur']['summe'], 4)} |",
        "",
        "Nicht enthalten: Aufwärmaufruf vor dem Lauf, Pilotläufe, Indexierung der KB und Erzeugung von KB und Tickets "
        "(siehe `auswertung/api_nutzung.py`).",
        "",
        "## Latenz der RAG-Bedingung nach Teilschritt (Median, s)",
        "",
        "| Embedding | Vektorsuche | Reranking | Generierung | gesamt |",
        "| --- | --- | --- | --- | --- |",
        f"| {de(s_r['latenz_embedding_s']['median'], 2)} | {de(s_r['latenz_suche_s']['median'], 2)} | "
        f"{de(s_r['latenz_rerank_s']['median'], 2)} | {de(s_r['latenz_generierung_s']['median'], 2)} | "
        f"{de(s_r['latenz_s']['median'], 2)} |",
        "",
        f"90 % der RAG-Anfragen waren nach {de(s_r['latenz_s']['p90'], 2)} s beantwortet, "
        f"90 % der LLM-only-Anfragen nach {de(s_l['latenz_s']['p90'], 2)} s.",
        "",
        f"## Retrieval-Trefferquote (KB-gedeckte Tickets, n = {n_ret})",
        "",
        "Anteil der Tickets, deren Belegartikel (laut Musterantwort) unter den abgerufenen Artikeln waren. "
        "Ein Treffer heißt nicht, dass der passende Abschnitt übergeben wurde (vgl. F2 in der Kodierung).",
        "",
        "| | mindestens ein Belegartikel | alle Belegartikel |",
        "| --- | --- | --- |",
        f"| übergeben (Top-3 nach Reranking) | {m1}/{n1} ({pct(m1, n1)} %) | {m2}/{n1} ({pct(m2, n1)} %) |",
        f"| unter den Kandidaten (Top-5 der Vektorsuche) | {m3}/{n1} ({pct(m3, n1)} %) | {m4}/{n1} ({pct(m4, n1)} %) |",
        "",
        "Nach Schwierigkeitsgrad (mindestens ein Belegartikel übergeben):",
        "",
        "| Schwierigkeit | Treffer |",
        "| --- | --- |",
    ]
    stufen = ["einfach", "mittel", "komplex"]
    for level in sorted({r["schwierigkeit"] for r in ret_rows}, key=lambda x: stufen.index(x) if x in stufen else 99):
        a, b = quote("treffer_min1_top3", [r for r in ret_rows if r["schwierigkeit"] == level])
        lines.append(f"| {level} | {a}/{b} ({pct(a, b)} %) |")
    lines += ["", "![Latenz und Kosten je Anfrage](strang1.png)", ""]
    (out / "bericht.md").write_text("\n".join(lines), encoding="utf-8")

    versionen = {"python": sys.version.split()[0]}
    try:
        import matplotlib as _m
        versionen["matplotlib"] = _m.__version__
    except ImportError:
        pass
    meta = {"erzeugt": now_iso(), "skript": "auswertung/strang1.py", "git": git_state, "lauf": args.run,
            "responses_sha256": file_hash(responses), "tickets_jsonl_sha256": file_hash(ROOT / "tickets.jsonl"),
            "wechselkurs": {"usd_je_eur": args.usd_eur, "datum": args.kurs_datum, "quelle": "EZB-Referenzkurs"},
            "teilstudie_b": {"variable_kosten_je_ticket_eur": round(k_rag_eur, 8), "basis": "Mittelwert RAG, haupt-01"},
            "versionen": versionen}
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("\n".join(lines[:4] + lines[11:22]))
    print(f"\nGeschrieben: {out.relative_to(ROOT)}/ (bericht.md, kennzahlen.csv, paare.csv, retrieval.csv, strang1.png, meta.json)")


if __name__ == "__main__":
    main()
