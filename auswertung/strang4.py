"""Strang 4: manuelle Kodierung – Aussagendeckung (C1), Quellenpassung (C2), H4 (Rückfragen), H5 (Fehlertypen).

Aufruf im Repo-Hauptverzeichnis:
    python auswertung/strang4.py

Eingaben: kodierung/kodiertabelle_konsens.xlsx (Konsens, K-11), kodierung/kappa/kappa.csv (falls vorhanden),
judge/runs/haupt-01-j1/judge.jsonl (Vergleich C1 mit KB-Supportedness, DEMI 2.3)

Ausgabe in auswertung/ergebnisse/strang4/:
- bericht.md     Tabellen für das EVI
- entwuerfe.csv  eine Zeile je Entwurf: Deckungsanteile (streng und mit 0,5), C3, Mangel, Fehlertypen, KB-Supportedness
- tests.csv      Kennwerte von H4 und H5
- meta.json      Herkunft: Hashes, Git-Stand, Versionen
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
sys.path.insert(0, str(ROOT / "kodierung"))
sys.path.insert(0, str(AUSWERTUNG))
from common import git_info, now_iso  # noqa: E402
from pruefe_kodierung import pruefe, s, split_f  # noqa: E402
import statistik as st  # noqa: E402
from statistik import NAME, de, mdn_iqr, p_text, pct  # noqa: E402

KODIERUNG = ROOT / "kodierung" / "kodiertabelle_konsens.xlsx"
KAPPA = ROOT / "kodierung" / "kappa" / "kappa.csv"
JUDGE = ROOT / "judge" / "runs" / "haupt-01-j1" / "judge.jsonl"
OUT = AUSWERTUNG / "ergebnisse" / "strang4"
BED = ("rag", "llm")
FT = ["F1", "F2", "F3", "F4"]
F_NAME = {"F1": "KB-Fail", "F2": "Retrieval-Fail", "F3": "Generation-Fail", "F4": "Citation-Fail"}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def deckung(d: dict, teil: float) -> float | None:
    """Anteil gedeckter Kernaussagen; „teilweise“ zählt als teil (K-04: 0 streng, 0,5 Robustheit)."""
    c1 = [s(d[f"K{i}_C1"]) for i in (1, 2, 3) if s(d[f"K{i}"])]
    if not c1:
        return None
    return sum(1.0 if c == "gedeckt" else teil if c == "teilweise" else 0.0 for c in c1) / len(c1)


def main() -> None:
    data, fehler, _ = pruefe(KODIERUNG)
    if fehler:
        sys.exit(f"FEHLER: {KODIERUNG.relative_to(ROOT)} besteht pruefe_kodierung.py nicht "
                 f"({sum(len(v) for v in fehler.values())} Fehler)")
    with JUDGE.open(encoding="utf-8") as f:
        judge = {(e["ticket_id"], e["bedingung"]): e for e in map(json.loads, f)}
    by = {(s(d["ticket_id"]), s(d["bedingung"])): d for d in data}
    ids = sorted({t for t, _ in by})
    probleme = [f"{t}: Bedingung {b} fehlt" for t in ids for b in BED if (t, b) not in by]
    if len(by) != 240 or probleme:
        sys.exit("FEHLER:\n" + "\n".join(probleme or [f"{len(by)} statt 240 Entwürfe"]))

    def gap(t):
        return s(by[(t, "rag")]["kb_abdeckung"]) == "gap"

    L = ["# Strang 4: Manuelle Kodierung", "",
         f"Erzeugt mit `auswertung/strang4.py` am {now_iso()[:10]}. Grundlage: `kodierung/kodiertabelle_konsens.xlsx` "
         "(Erstkodierung, für die 48 doppelt kodierten Entwürfe Konsenscodes; K-11). 120 Ticketpaare, davon 96 "
         "KB-gedeckt und 24 KB-Gap. Alle Tests zweiseitig mit α = 0,05.", ""]

    # ---------------------------------------------------------------- Übereinstimmung
    if KAPPA.exists():
        with KAPPA.open(encoding="utf-8") as f:
            kap = list(csv.DictReader(f))
        L += ["## Übereinstimmung der Zweitkodierung (vor dem Konsens)", "",
              "| Code | Einheit | n | Übereinstimmung | Cohens Kappa | Stufe nach Landis und Koch (1977) |",
              "| --- | --- | --- | --- | --- | --- |"]
        namen = {"C1": "C1 Aussagendeckung", "C2": "C2 Quellenpassung", "C3": "C3 Rückfrage/Enthaltung",
                 "mangel": "Mangel", "F_primaer": "Primärer Fehlertyp", "C1_linear_gewichtet": "C1, linear gewichtet"}
        for r in kap:
            k = r["kappa"]
            gewichtet = "gewichtet" in r["code"]
            uebereinstimmung = "–" if gewichtet else f"{de(float(r['uebereinstimmung']) * 100, 1)} %"
            L.append(f"| {namen.get(r['code'], r['code'])} | {r['einheit']} | {r['n']} | {uebereinstimmung} | "
                     f"{de(float(k)) if k else 'nicht definiert'} | {r['stufe'] or '–'} |")
        L += ["", "Details und Kreuztabellen: `kodierung/kappa/bericht.md`.", ""]

    # ---------------------------------------------------------------- C1 Aussagendeckung
    deck = {(t, b): (deckung(by[(t, b)], 0.0), deckung(by[(t, b)], 0.5)) for t in ids for b in BED}
    stat_c1 = Counter((b, s(by[(t, b)][f"K{i}_C1"])) for t in ids for b in BED for i in (1, 2, 3) if s(by[(t, b)][f"K{i}"]))
    L += ["## C1 Aussagendeckung", "",
          "Bis zu drei Kernaussagen je Entwurf, je Kernaussage gegen die gesamte KB geprüft (LEITFADEN.md, Abschnitte 3 "
          "und 4). Deckungsanteil je Entwurf streng (teilweise = 0, K-04) und als Robustheitsprüfung mit teilweise = 0,5.",
          "", "| | RAG | LLM-only |", "| --- | --- | --- |"]
    for c in ("gedeckt", "teilweise", "nicht gedeckt"):
        n_r = sum(v for (b, k), v in stat_c1.items() if b == "rag")
        n_l = sum(v for (b, k), v in stat_c1.items() if b == "llm")
        L.append(f"| Kernaussagen {c} | {stat_c1[('rag', c)]} ({pct(stat_c1[('rag', c)], n_r)}) | "
                 f"{stat_c1[('llm', c)]} ({pct(stat_c1[('llm', c)], n_l)}) |")
    ohne = {b: sum(deck[(t, b)][0] is None for t in ids) for b in BED}
    L.append(f"| Entwürfe ohne Kernaussage | {ohne['rag']} | {ohne['llm']} |")
    for teil, lab in ((0, "streng"), (1, "teilweise = 0,5")):
        for gruppe, tt in (("alle", ids), ("KB-gedeckt", [t for t in ids if not gap(t)]), ("KB-Gap", [t for t in ids if gap(t)])):
            vr = [deck[(t, "rag")][teil] for t in tt if deck[(t, "rag")][teil] is not None]
            vl = [deck[(t, "llm")][teil] for t in tt if deck[(t, "llm")][teil] is not None]
            L.append(f"| Deckungsanteil {lab}, {gruppe}: Median (IQR), Mittel | {mdn_iqr(vr)}, {de(sum(vr) / len(vr)) if vr else '–'}"
                     f" (n = {len(vr)}) | {mdn_iqr(vl)}, {de(sum(vl) / len(vl)) if vl else '–'} (n = {len(vl)}) |")
    paare = [t for t in ids if deck[(t, "rag")][0] is not None and deck[(t, "llm")][0] is not None]
    hoeher = sum(deck[(t, "rag")][0] > deck[(t, "llm")][0] for t in paare)
    niedriger = sum(deck[(t, "rag")][0] < deck[(t, "llm")][0] for t in paare)
    L += ["", f"Paare mit Kernaussagen in beiden Bedingungen: {len(paare)}; Deckungsanteil (streng) RAG höher: {hoeher}, "
          f"gleich: {len(paare) - hoeher - niedriger}, LLM-only höher: {niedriger}. Beschreibend; maßgeblich für H3 ist "
          "die KB-Supportedness des Judge (DEMI 2.3).", ""]

    # ---------------------------------------------------------------- C1 vs. KB-Supportedness
    vergleich = [(deck[k][0], judge[k]["kb_supportedness"], k[1]) for k in deck
                 if deck[k][0] is not None and judge[k]["kb_supportedness"] is not None]
    sp = st.spearman([a for a, _, _ in vergleich], [b for _, b, _ in vergleich], seed="20261026:c1kb")
    L += ["## Manuelle Aussagendeckung und KB-Supportedness (DEMI 2.3)", "",
          "Beide Zugänge erfassen dasselbe Konstrukt, beziehen sich aber auf unterschiedliche Aussagenmengen: C1 auf bis "
          "zu drei Kernaussagen, die KB-Supportedness auf alle Sachaussagen eines Entwurfs. Beschreibend.", "",
          "| | n | C1 streng, Mittel | KB-Supportedness, Mittel | beide 1 | beide 0 |", "| --- | --- | --- | --- | --- | --- |"]
    for b in BED:
        v = [(a, c) for a, c, bb in vergleich if bb == b]
        L.append(f"| {NAME[b]} | {len(v)} | {de(sum(a for a, _ in v) / len(v))} | {de(sum(c for _, c in v) / len(v))} | "
                 f"{sum(a == 1 and c == 1 for a, c in v)} | {sum(a == 0 and c == 0 for a, c in v)} |")
    L += ["", f"Rangkorrelation über alle Entwürfe mit beiden Werten: ρ = {de(sp['rho'])} (95-%-KI {de(sp['ci'][0])} bis "
          f"{de(sp['ci'][1])}, {p_text(sp['p'])}, n = {sp['n']}).", ""]

    # ---------------------------------------------------------------- C2 Quellenpassung
    c2 = Counter(s(by[(t, "rag")][f"K{i}_C2"]) for t in ids for i in (1, 2, 3) if s(by[(t, "rag")][f"K{i}"]))
    n_c2 = sum(c2.values())
    L += ["## C2 Quellenpassung (RAG)", "", "| Code | Kernaussagen |", "| --- | --- |"]
    for c in ("passend", "nicht passend", "kein Beleg"):
        L.append(f"| {c} | {c2[c]} ({pct(c2[c], n_c2)}) |")
    L.append("")

    # ---------------------------------------------------------------- C3 und H4
    def c3(t, b):
        return s(by[(t, b)]["C3"]) == "ja"

    L += ["## C3 Rückfrage oder Enthaltung", "", "| Tickets | RAG | LLM-only |", "| --- | --- | --- |"]
    for gruppe, tt in (("alle (n = 120)", ids), ("KB-gedeckt (n = 96)", [t for t in ids if not gap(t)]),
                       ("KB-Gap (n = 24)", [t for t in ids if gap(t)])):
        L.append(f"| {gruppe} | {sum(c3(t, 'rag') for t in tt)} ({pct(sum(c3(t, 'rag') for t in tt), len(tt))}) | "
                 f"{sum(c3(t, 'llm') for t in tt)} ({pct(sum(c3(t, 'llm') for t in tt), len(tt))}) |")
    gt = [t for t in ids if gap(t)]
    a = sum(c3(t, "rag") and c3(t, "llm") for t in gt)
    b_ = sum(c3(t, "rag") and not c3(t, "llm") for t in gt)
    c_ = sum(not c3(t, "rag") and c3(t, "llm") for t in gt)
    d_ = sum(not c3(t, "rag") and not c3(t, "llm") for t in gt)
    mc = st.mcnemar_exakt(b_, c_)
    or_txt = "nicht schätzbar (c = 0)" if mc["or"] in (None, float("inf")) else de(mc["or"])
    L += ["", "### H4 (explorativ): Rückfrage oder Enthaltung bei KB-Gap-Tickets", "",
          "| RAG \\ LLM-only | Rückfrage ja | Rückfrage nein |", "| --- | --- | --- |",
          f"| Rückfrage ja | {a} | {b_} |", f"| Rückfrage nein | {c_} | {d_} |", "",
          f"- Rückfragequote: RAG {pct(a + b_, len(gt))}, LLM-only {pct(a + c_, len(gt))}",
          f"- Exakter McNemar-Test auf die {b_ + c_} diskordanten Paare: {p_text(mc['p'])}",
          f"- Odds Ratio (gepaart, b/c; > 1 = RAG häufiger): {or_txt}, 95-%-KI {de(mc['ci'][0])} bis {de(mc['ci'][1])}",
          "- Nach DEMI 1.4.5 nur sehr deutliche Unterschiede nachweisbar; ein nicht signifikantes Ergebnis belegt "
          "keine Gleichheit.", ""]

    # ---------------------------------------------------------------- H5 und Mangel
    rag_ged = [t for t in ids if not gap(t)]
    fp = Counter(s(by[(t, "rag")]["F_primaer"]) for t in rag_ged)
    mangel_ged = sum(s(by[(t, "rag")]["mangel"]) == "ja" for t in rag_ged)
    alle_f = Counter(f for t in rag_ged for f in ([s(by[(t, "rag")]["F_primaer"])] + split_f(s(by[(t, "rag")]["F_weitere"])))
                     if f in FT)
    counts = [fp["F2"], fp["F3"], fp["F4"]]
    gv = st.gleichverteilung(counts) if sum(counts) else None
    fp_gap = Counter(s(by[(t, "rag")]["F_primaer"]) for t in gt)
    L += ["## Mangel und Fehlertypen (RAG)", "",
          f"KB-gedeckte Tickets: Mangel bei {mangel_ged} von {len(rag_ged)} RAG-Entwürfen ({pct(mangel_ged, len(rag_ged))}). "
          f"KB-Gap-Tickets: Mangel bei {sum(s(by[(t, 'rag')]['mangel']) == 'ja' for t in gt)} von {len(gt)} "
          f"(F1 als primärer Typ: {fp_gap['F1']}; laut DEMI Designmerkmal, nicht Teil von H5).", "",
          "| Fehlertyp | primär (KB-gedeckt, n = 96) | primär oder weiterer (KB-gedeckt) |", "| --- | --- | --- |"]
    for f in FT:
        L.append(f"| {f} {F_NAME[f]} | {fp[f]} | {alle_f[f]} |")
    L.append(f"| kein Fehlertyp | {fp['keiner']} | – |")
    L += ["", "### H5: Verteilung der primären Fehlertypen F2–F4 (KB-gedeckte Tickets)", ""]
    if gv:
        L += [f"- Beobachtet: F2 = {counts[0]}, F3 = {counts[1]}, F4 = {counts[2]} (n = {gv['n']}); erwartet je Typ "
              f"{de(gv['erwartet'], 2)}",
              f"- Chi-Quadrat-Anpassungstest gegen Gleichverteilung: χ²({gv['df']}) = {de(gv['chi2'])}, "
              f"{p_text(gv['p_chi2'])}",
              f"- Exakter Multinomialtest (AW-09): {p_text(gv['p_exakt'])}"
              + ("; die erwarteten Häufigkeiten liegen unter 5, deshalb ist der exakte Test maßgeblich."
                 if gv["erwartet"] < 5 else ""), ""]
    else:
        L += ["Keine Fehler der Typen F2–F4; H5 nicht prüfbar.", ""]

    # ---------------------------------------------------------------- Ausgabe
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "entwuerfe.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["kodier_id", "ticket_id", "bedingung", "kb_abdeckung", "n_kernaussagen", "deckung_streng",
                    "deckung_halb", "c3", "mangel", "f_primaer", "f_weitere", "kb_supportedness_judge"])
        for t in ids:
            for b in BED:
                d = by[(t, b)]
                w.writerow([s(d["kodier_id"]), t, b, s(d["kb_abdeckung"]), sum(bool(s(d[f"K{i}"])) for i in (1, 2, 3)),
                            deck[(t, b)][0], deck[(t, b)][1], s(d["C3"]), s(d["mangel"]), s(d["F_primaer"]),
                            ";".join(split_f(s(d["F_weitere"]))), judge[(t, b)]["kb_supportedness"]])
    with (OUT / "tests.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hypothese", "verfahren", "n", "kennwerte", "p"])
        w.writerow(["H4", "McNemar exakt", len(gt), f"a={a}; b={b_}; c={c_}; d={d_}; OR={mc['or']}; "
                    f"KI={mc['ci'][0]:.4f}-{mc['ci'][1]:.4f}", mc["p"]])
        if gv:
            w.writerow(["H5", f"Chi-Quadrat (df = {gv['df']})", gv["n"], f"F2={counts[0]}; F3={counts[1]}; F4={counts[2]}; "
                        f"chi2={gv['chi2']:.4f}", gv["p_chi2"]])
            w.writerow(["H5", "Multinomial exakt", gv["n"], f"F2={counts[0]}; F3={counts[1]}; F4={counts[2]}", gv["p_exakt"]])
        w.writerow(["C1-KB", "Spearman", sp["n"], f"rho={sp['rho']:.4f}", sp["p"]])
    (OUT / "bericht.md").write_text("\n".join(L), encoding="utf-8")
    meta = {"erzeugt": now_iso(), "skript": "auswertung/strang4.py", "git": git_info(),
            "eingaben": {"kodiertabelle_konsens": file_hash(KODIERUNG), "judge_jsonl": file_hash(JUDGE),
                         "kappa_csv": file_hash(KAPPA) if KAPPA.exists() else None},
            "versionen": {"python": sys.version.split()[0], **{m: __import__(m).__version__ for m in ("scipy", "openpyxl")}}}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"H4: RAG {a + b_}/{len(gt)}, LLM-only {a + c_}/{len(gt)}, {p_text(mc['p'])}")
    if gv:
        print(f"H5: F2/F3/F4 = {counts}, exakt {p_text(gv['p_exakt'])}")
    print(f"Geschrieben: {OUT.relative_to(ROOT)}/ (bericht.md, entwuerfe.csv, tests.csv, meta.json)")


if __name__ == "__main__":
    main()
