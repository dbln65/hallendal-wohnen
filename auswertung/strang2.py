"""Strang 2: automatisierte Bewertung – H1 (Korrektheit), H3 (KB-Supportedness), Diagnosemetriken, Stabilität.

Aufruf im Repo-Hauptverzeichnis:
    python auswertung/strang2.py

Eingaben: judge/runs/haupt-01-j1/ (Hauptlauf), judge/runs/haupt-01-j1-wdh/ (Stabilitätsprüfung, J-03), tickets.jsonl

Ausgabe in auswertung/ergebnisse/strang2/:
- bericht.md        Tabellen für das EVI
- entwuerfe.csv     eine Zeile je Entwurf: Korrektheit, KB-Supportedness, Faithfulness, Context/Answer Relevance
- tests.csv         Kennwerte von H1 und H3
- korrektheit.png   Verteilung der Korrektheit je Bedingung, gesamt und nach KB-Abdeckung
- kb_supportedness.png  Anteil gedeckter Sachaussagen je Bedingung
- meta.json         Herkunft: Hashes, Judge-Konfiguration, Git-Stand, Versionen
"""

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

AUSWERTUNG = Path(__file__).resolve().parent
ROOT = AUSWERTUNG.parent
sys.path.insert(0, str(ROOT / "rag"))
sys.path.insert(0, str(AUSWERTUNG))
from common import git_info, now_iso  # noqa: E402
import statistik as st  # noqa: E402
from statistik import KORREKTHEIT, KORREKT_WERT, NAME, de, mdn_iqr, p_text, pct  # noqa: E402

LAUF = ROOT / "judge" / "runs" / "haupt-01-j1"
WDH = ROOT / "judge" / "runs" / "haupt-01-j1-wdh"
OUT = AUSWERTUNG / "ergebnisse" / "strang2"
BED = ("rag", "llm")
GRUPPEN = [("kb_abdeckung", "KB-Abdeckung", ["gedeckt", "gap"]),
           ("schwierigkeit", "Schwierigkeit", ["einfach", "mittel", "komplex", "kb_gap"]),
           ("kategorie", "Kategorie", ["Versand", "Retoure", "Reklamation/Garantie", "Zahlung"])]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def lies(path: Path) -> list:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def main() -> None:
    eintraege = lies(LAUF / "judge.jsonl")
    meta_j = json.loads((LAUF / "judge_meta.json").read_text(encoding="utf-8"))
    wdh = lies(WDH / "judge.jsonl")
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}

    fehler = []
    by = {(e["ticket_id"], e["bedingung"]): e for e in eintraege}
    ids = sorted({e["ticket_id"] for e in eintraege})
    if len(by) != len(eintraege) or len(eintraege) != 240:
        fehler.append(f"erwartet 240 eindeutige Einträge, gefunden {len(eintraege)} ({len(by)} eindeutig)")
    fehler += [f"{t}: Bedingung {b} fehlt" for t in ids for b in BED if (t, b) not in by]
    if {e["config_hash"] for e in eintraege + wdh} != {meta_j["config_hash"]}:
        fehler.append("Konfiguration (config_hash) uneinheitlich zwischen Hauptlauf und Wiederholung")
    if meta_j.get("n_bewertet") != meta_j.get("n_erwartet"):
        fehler.append("judge_meta.json: nicht alle Entwürfe bewertet")
    for e in eintraege:
        t = tickets.get(e["ticket_id"])
        if not t or t["set"] != "haupt" or t["kb_abdeckung"] != e["kb_abdeckung"]:
            fehler.append(f"{e['ticket_id']}: passt nicht zu tickets.jsonl")
    if fehler:
        sys.exit("FEHLER:\n" + "\n".join(fehler))

    def wert(t, b, k):
        return by[(t, b)][k]

    L = ["# Strang 2: Automatisierte Bewertung", "",
         f"Erzeugt mit `auswertung/strang2.py` am {now_iso()[:10]}. Judge-Lauf `{meta_j['judge_run']}` über Lauf "
         f"`{meta_j['lauf']}`: Modell `{meta_j['config']['modell']}`, Prompt-Version {meta_j['config']['prompt_version']}, "
         f"Effort {meta_j['config']['effort']}, Konfiguration `{meta_j['config_hash']}`. 120 Ticketpaare, alle Tests "
         "zweiseitig mit α = 0,05 (DEMI 1.4.5).", ""]

    # ---------------------------------------------------------------- H1 Korrektheit
    vert = {b: Counter(wert(t, b, "korrektheit") for t in ids) for b in BED}
    werte = {b: [KORREKT_WERT[wert(t, b, "korrektheit")] for t in ids] for b in BED}
    h1 = st.wilcoxon(werte["rag"], werte["llm"])
    kreuz = [[sum(1 for t in ids if wert(t, "rag", "korrektheit") == a and wert(t, "llm", "korrektheit") == b)
              for b in KORREKTHEIT] for a in KORREKTHEIT]
    sm = st.stuart_maxwell(kreuz)

    def mdn_kat(v):
        m, q1, q3 = st.quartile(v)
        return f"{KORREKTHEIT[int(round(m))] if m == int(m) else de(m, 1)} ({KORREKTHEIT[int(q1)] if q1 == int(q1) else de(q1, 1)}–{KORREKTHEIT[int(q3)] if q3 == int(q3) else de(q3, 1)})"

    L += ["## H1: Referenzbasierte Korrektheit", "",
          "Tabelle: Verteilung je Bedingung (n = 120 je Bedingung)", "",
          "| Urteil | RAG | LLM-only |", "| --- | --- | --- |"]
    for k in reversed(KORREKTHEIT):
        L.append(f"| {k} | {vert['rag'][k]} ({pct(vert['rag'][k], 120)}) | {vert['llm'][k]} ({pct(vert['llm'][k], 120)}) |")
    L += [f"| Median (IQR) | {mdn_kat(werte['rag'])} | {mdn_kat(werte['llm'])} |", "",
          "Tabelle: Paare (Zeilen RAG, Spalten LLM-only)", "",
          "| RAG \\ LLM-only | " + " | ".join(KORREKTHEIT) + " |", "| --- |" + " --- |" * 3]
    for i, a in enumerate(KORREKTHEIT):
        L.append(f"| {a} | " + " | ".join(str(kreuz[i][j]) for j in range(3)) + " |")
    L += ["", f"- RAG besser: {h1['n_pos']} Paare, gleich: {h1['n_paare'] - h1['n_ungleich']}, LLM-only besser: "
          f"{h1['n_neg']}",
          f"- Exakter Wilcoxon-Vorzeichen-Rang-Test (n = {h1['n_ungleich']} Paare mit Unterschied von {h1['n_paare']}): "
          f"T+ = {de(h1['t_plus'], 1)}, {p_text(h1['p'])}, z = {de(h1['z'])}, r = {de(h1['r'])} ({st.r_stufe(h1['r'])})",
          f"- Robustheitsprüfung, Test auf marginale Homogenität nach Stuart und Maxwell: χ²({sm['df']}) = "
          f"{de(sm['chi2'])}, {p_text(sm['p'])}", ""]

    # ---------------------------------------------------------------- H3 KB-Supportedness
    ks = {b: {t: wert(t, b, "kb_supportedness") for t in ids} for b in BED}
    ohne = {b: sum(v is None for v in ks[b].values()) for b in BED}
    paare3 = [t for t in ids if ks["rag"][t] is not None and ks["llm"][t] is not None]
    h3 = st.wilcoxon([ks["rag"][t] for t in paare3], [ks["llm"][t] for t in paare3])
    na = {b: [e["n_aussagen"] for e in eintraege if e["bedingung"] == b] for b in BED}
    L += ["## H3: KB-Supportedness", "",
          "Anteil der Sachaussagen eines Entwurfs, die laut Judge durch die gesamte KB gedeckt sind. Entwürfe ohne "
          "Sachaussage haben keinen Wert und fallen paarweise aus (DEMI 2.3).", "",
          "| | RAG | LLM-only |", "| --- | --- | --- |",
          f"| Entwürfe ohne Sachaussage | {ohne['rag']} ({pct(ohne['rag'], 120)}) | {ohne['llm']} ({pct(ohne['llm'], 120)}) |",
          f"| Sachaussagen je Entwurf, Median (IQR) | {mdn_iqr(na['rag'], 0)} | {mdn_iqr(na['llm'], 0)} |",
          f"| KB-Supportedness, Median (IQR), Paare n = {len(paare3)} | {mdn_iqr([ks['rag'][t] for t in paare3])} | "
          f"{mdn_iqr([ks['llm'][t] for t in paare3])} |",
          f"| Mittelwert (ergänzend) | {de(sum(ks['rag'][t] for t in paare3) / len(paare3))} | "
          f"{de(sum(ks['llm'][t] for t in paare3) / len(paare3))} |",
          f"| alle Sachaussagen gedeckt | {sum(ks['rag'][t] == 1 for t in paare3)} | {sum(ks['llm'][t] == 1 for t in paare3)} |",
          f"| keine Sachaussage gedeckt | {sum(ks['rag'][t] == 0 for t in paare3)} | {sum(ks['llm'][t] == 0 for t in paare3)} |",
          "",
          f"- RAG höher: {h3['n_pos']} Paare, gleich: {h3['n_paare'] - h3['n_ungleich']}, LLM-only höher: {h3['n_neg']}",
          f"- Wilcoxon-Vorzeichen-Rang-Test, exakt (n = {h3['n_ungleich']} von {h3['n_paare']} Paaren): "
          f"T+ = {de(h3['t_plus'], 1)}, {p_text(h3['p'])}, z = {de(h3['z'])}, r = {de(h3['r'])} ({st.r_stufe(h3['r'])})",
          ""]

    # ---------------------------------------------------------------- Untergruppen (deskriptiv)
    L += ["## Untergruppen (deskriptiv)", "",
          "Anteil korrekter Entwürfe und Paarvergleich der Korrektheit; Median der KB-Supportedness (Paare mit Werten).",
          "", "| Gruppe | Ticketpaare | korrekt RAG | korrekt LLM-only | RAG besser / gleich / schlechter | "
          "KB-Supportedness RAG | LLM-only |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for feld, titel, stufen in GRUPPEN:
        for s in stufen:
            tt = [t for t in ids if by[(t, "rag")][feld] == s]
            if not tt:
                continue
            besser = sum(KORREKT_WERT[wert(t, "rag", "korrektheit")] > KORREKT_WERT[wert(t, "llm", "korrektheit")] for t in tt)
            schlechter = sum(KORREKT_WERT[wert(t, "rag", "korrektheit")] < KORREKT_WERT[wert(t, "llm", "korrektheit")]
                             for t in tt)
            kr = sum(wert(t, "rag", "korrektheit") == "korrekt" for t in tt)
            kl = sum(wert(t, "llm", "korrektheit") == "korrekt" for t in tt)
            p3 = [t for t in tt if t in paare3]
            ks_r = st.quartile([ks["rag"][t] for t in p3])[0] if p3 else None
            ks_l = st.quartile([ks["llm"][t] for t in p3])[0] if p3 else None
            L.append(f"| {titel}: {s} | {len(tt)} | {pct(kr, len(tt), 0)} | {pct(kl, len(tt), 0)} | "
                     f"{besser} / {len(tt) - besser - schlechter} / {schlechter} | {de(ks_r)} | {de(ks_l)} |")
    L.append("")

    # ---------------------------------------------------------------- Diagnose und Answer Relevance
    faith = [wert(t, "rag", "faithfulness") for t in ids if wert(t, "rag", "faithfulness") is not None]
    ctx = [wert(t, "rag", "context_relevance") for t in ids if wert(t, "rag", "context_relevance") is not None]
    ar = {b: [wert(t, b, "answer_relevance") for t in ids] for b in BED}
    L += ["## Diagnosemetriken und Answer Relevance (beschreibend)", "",
          "| Metrik | gilt für | n | Median (IQR) | Mittelwert |", "| --- | --- | --- | --- | --- |",
          f"| RAG-Faithfulness | RAG | {len(faith)} | {mdn_iqr(faith)} | {de(sum(faith) / len(faith))} |",
          f"| Context Relevance | RAG | {len(ctx)} | {mdn_iqr(ctx)} | {de(sum(ctx) / len(ctx))} |",
          f"| Answer Relevance | RAG | 120 | {mdn_iqr(ar['rag'], 3)} | {de(sum(ar['rag']) / 120, 3)} |",
          f"| Answer Relevance | LLM-only | 120 | {mdn_iqr(ar['llm'], 3)} | {de(sum(ar['llm']) / 120, 3)} |", "",
          f"Faithfulness = 1 bei {sum(v == 1 for v in faith)} von {len(faith)} RAG-Entwürfen. Context Relevance: Anteil "
          "der drei übergebenen Auszüge, die zur Beantwortung erforderlich sind.", ""]

    # ---------------------------------------------------------------- Stabilität (J-03)
    w_by = {(e["ticket_id"], e["bedingung"]): e for e in wdh}
    keys = sorted(w_by)
    pk = [(by[k]["korrektheit"], w_by[k]["korrektheit"]) for k in keys]
    kk = st.cohen_kappa(pk, KORREKTHEIT)
    ks_pairs = [(by[k]["kb_supportedness"], w_by[k]["kb_supportedness"]) for k in keys]
    ks_def = [(a, b) for a, b in ks_pairs if a is not None and b is not None]
    rag_k = [k for k in keys if k[1] == "rag"]
    fa = [(by[k]["faithfulness"], w_by[k]["faithfulness"]) for k in rag_k
          if by[k]["faithfulness"] is not None and w_by[k]["faithfulness"] is not None]
    cr = [(by[k]["context_relevance"], w_by[k]["context_relevance"]) for k in rag_k]
    arp = [(by[k]["answer_relevance"], w_by[k]["answer_relevance"]) for k in keys]
    L += ["## Stabilität des Judge (J-03)", "",
          f"{len(keys)} Entwürfe ({len(rag_k)} RAG, {len(keys) - len(rag_k)} LLM-only) in zwei Läufen mit identischer "
          "Konfiguration bewertet.", "",
          "| Metrik | n | identisch | weitere Kennzahl |", "| --- | --- | --- | --- |",
          f"| Korrektheit | {kk['n']} | {pct(sum(a == b for a, b in pk), kk['n'])} | Cohens Kappa {de(kk['kappa'])} |",
          f"| KB-Supportedness | {len(ks_def)} | {pct(sum(abs(a - b) < 1e-9 for a, b in ks_def), len(ks_def))} | "
          f"mittlere absolute Differenz {de(sum(abs(a - b) for a, b in ks_def) / len(ks_def))} |",
          f"| RAG-Faithfulness | {len(fa)} | {pct(sum(abs(a - b) < 1e-9 for a, b in fa), len(fa))} | "
          f"mittlere absolute Differenz {de(sum(abs(a - b) for a, b in fa) / len(fa)) if fa else '–'} |",
          f"| Context Relevance | {len(cr)} | {pct(sum(abs(a - b) < 1e-9 for a, b in cr), len(cr))} | "
          f"mittlere absolute Differenz {de(sum(abs(a - b) for a, b in cr) / len(cr))} |",
          f"| Answer Relevance | {len(arp)} | – | mittlere absolute Differenz {de(sum(abs(a - b) for a, b in arp) / len(arp), 3)} |",
          ""]
    wechsel = [f"{k[0]} {NAME[k[1]]}: {a} → {b}" for k, (a, b) in zip(keys, pk) if a != b]
    if wechsel:
        L += ["Abweichende Korrektheitsurteile: " + "; ".join(wechsel) + ".", ""]

    # ---------------------------------------------------------------- Ausgabe
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "entwuerfe.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticket_id", "bedingung", "kb_abdeckung", "schwierigkeit", "kategorie", "korrektheit",
                    "n_aussagen", "kb_supportedness", "faithfulness", "context_relevance", "answer_relevance"])
        for t in ids:
            for b in BED:
                e = by[(t, b)]
                w.writerow([t, b, e["kb_abdeckung"], e["schwierigkeit"], e["kategorie"], e["korrektheit"],
                            e["n_aussagen"], e["kb_supportedness"], e.get("faithfulness"), e.get("context_relevance"),
                            round(e["answer_relevance"], 6)])
    with (OUT / "tests.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hypothese", "verfahren", "n_paare", "n_ungleich", "rag_hoeher", "llm_hoeher", "statistik", "p", "z", "r"])
        w.writerow(["H1", "Wilcoxon exakt", h1["n_paare"], h1["n_ungleich"], h1["n_pos"], h1["n_neg"],
                    h1["t_plus"], h1["p"], round(h1["z"], 4), round(h1["r"], 4)])
        w.writerow(["H1", f"Stuart-Maxwell (df = {sm['df']})", h1["n_paare"], "", "", "", round(sm["chi2"], 4), sm["p"], "", ""])
        w.writerow(["H3", "Wilcoxon exakt", h3["n_paare"], h3["n_ungleich"], h3["n_pos"], h3["n_neg"],
                    h3["t_plus"], h3["p"], round(h3["z"], 4), round(h3["r"], 4)])

    bilder = abbildungen(by, ids, ks, paare3)
    L += [f"![{b}]({b})" for b in bilder] + [""]
    (OUT / "bericht.md").write_text("\n".join(L), encoding="utf-8")

    meta = {"erzeugt": now_iso(), "skript": "auswertung/strang2.py", "git": git_info(),
            "eingaben": {"judge_hauptlauf": file_hash(LAUF / "judge.jsonl"), "judge_meta": file_hash(LAUF / "judge_meta.json"),
                         "judge_wiederholung": file_hash(WDH / "judge.jsonl"), "tickets_jsonl": file_hash(ROOT / "tickets.jsonl")},
            "judge_config_hash": meta_j["config_hash"], "versionen": versionen()}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("\n".join(l for l in L if l.startswith("- ")))
    print(f"\nGeschrieben: {OUT.relative_to(ROOT)}/ (bericht.md, entwuerfe.csv, tests.csv, {', '.join(bilder)}, meta.json)")


def versionen() -> dict:
    v = {"python": sys.version.split()[0]}
    for mod in ("scipy", "statsmodels", "numpy", "matplotlib"):
        try:
            v[mod] = __import__(mod).__version__
        except ImportError:
            pass
    return v


def abbildungen(by, ids, ks, paare3) -> list:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("Hinweis: matplotlib fehlt, Abbildungen übersprungen")
        return []
    from statistik import GRAU, ORDINAL, ORDINAL4, TEXT, TEXT2
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": TEXT2, "axes.labelcolor": TEXT2,
                         "xtick.color": TEXT2, "ytick.color": TEXT2, "text.color": TEXT})

    def balken(ax, zeilen, stufen, farben, hell):
        """Gestapelte 100-%-Balken; zeilen: Liste (Beschriftung, Counter, n)."""
        y = list(range(len(zeilen)))[::-1]
        for yi, (lab, cnt, n) in zip(y, zeilen):
            links = 0
            for s, farbe in zip(stufen, farben):
                anteil = cnt[s] / n * 100
                if anteil > 0:
                    ax.barh(yi, anteil, left=links, color=farbe, height=0.62, edgecolor="white", linewidth=1.5)
                    if anteil >= 7:
                        ax.text(links + anteil / 2, yi, f"{de(anteil, 0)} %", ha="center", va="center", fontsize=7.5,
                                color="white" if farbe not in hell else TEXT)
                links += anteil
        ax.set_yticks(y, [z[0] for z in zeilen])
        ax.set_xlim(0, 100)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{de(v, 0)} %"))
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.tick_params(axis="y", length=0)

    out = []
    # Korrektheit
    zeilen = []
    for titel, tt in (("gesamt", ids), ("KB-gedeckt", [t for t in ids if by[(t, "rag")]["kb_abdeckung"] == "gedeckt"]),
                      ("KB-Gap", [t for t in ids if by[(t, "rag")]["kb_abdeckung"] == "gap"])):
        for b in BED:
            zeilen.append((f"{titel}: {NAME[b]} (n = {len(tt)})", Counter(by[(t, b)]["korrektheit"] for t in tt), len(tt)))
    fig, ax = plt.subplots(figsize=(6.3, 2.9), dpi=300)
    balken(ax, zeilen, KORREKTHEIT, ORDINAL, hell={ORDINAL[0]})
    handles = [matplotlib.patches.Patch(color=c, label=k) for k, c in zip(KORREKTHEIT, ORDINAL)]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.45, 1.16), ncol=3, frameon=False, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(OUT / "korrektheit.png", facecolor="white")
    plt.close(fig)
    out.append("korrektheit.png")

    # KB-Supportedness (Klassen)
    klassen = ["keine gedeckt", "weniger als die Hälfte", "mindestens die Hälfte", "alle gedeckt", "keine Sachaussage"]

    def klasse(v):
        if v is None:
            return klassen[4]
        return klassen[0] if v == 0 else klassen[3] if v == 1 else klassen[1] if v < 0.5 else klassen[2]

    zeilen = [(f"{NAME[b]} (n = 120)", Counter(klasse(ks[b][t]) for t in ids), 120) for b in BED]
    fig, ax = plt.subplots(figsize=(6.3, 2.3), dpi=300)
    balken(ax, zeilen, klassen, ORDINAL4 + [GRAU], hell={ORDINAL4[0], GRAU})
    handles = [matplotlib.patches.Patch(color=c, label=k) for k, c in zip(klassen, ORDINAL4 + [GRAU])]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.55, 1.0), ncol=3, frameon=False, fontsize=7.5)
    ax.set_xlabel("Anteil der Entwürfe, gruppiert nach dem Anteil KB-gedeckter Sachaussagen")
    fig.tight_layout(rect=(0, 0, 1, 0.8))
    fig.savefig(OUT / "kb_supportedness.png", facecolor="white")
    plt.close(fig)
    out.append("kb_supportedness.png")
    return out


if __name__ == "__main__":
    main()
