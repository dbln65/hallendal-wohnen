"""Strang 3: Online-Befragung – Stichprobe, H2 (Gesamtqualität), ICC, Erfahrung im Kundenservice, H6.

Aufruf im Repo-Hauptverzeichnis (nach strang2.py nicht erforderlich; H6 liest den Judge-Lauf direkt):
    python auswertung/strang3.py

Eingaben: umfrage/daten/bewertungen.csv, umfrage/daten/teilnehmende.csv, judge/runs/haupt-01-j1/judge.jsonl

Ausgabe in auswertung/ergebnisse/strang3/:
- bericht.md        Tabellen für das EVI
- entwuerfe.csv     eine Zeile je bewertetem Entwurf: Anzahl Urteile, Mittelwerte Q1–Q6, Judge-Korrektheit
- tests.csv         Kennwerte von H2 und H6, jeweils alle Bewertenden und Sensitivitätsanalyse (AW-07)
- q6.png            Gesamtqualität je Entwurf und Bedingung, alle Bewertenden
- q6_sensitivitaet.png  dasselbe neben der Sensitivitätsanalyse (AW-07)
- h6.png            wahrgenommene Korrektheit (Q1) nach referenzbasierter Korrektheit des Judge
- meta.json         Herkunft: Hashes, Git-Stand, Versionen

Die Urteile werden je Entwurf gemittelt; Analyseeinheit für H2 ist das Ticketpaar (DEMI 3.6).
"""

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

AUSWERTUNG = Path(__file__).resolve().parent
ROOT = AUSWERTUNG.parent
sys.path.insert(0, str(ROOT / "rag"))
sys.path.insert(0, str(AUSWERTUNG))
from common import git_info, now_iso  # noqa: E402
import statistik as st  # noqa: E402
from statistik import KORREKTHEIT, KORREKT_WERT, NAME, de, mdn_iqr, p_text  # noqa: E402

DATEN = ROOT / "umfrage" / "daten"
JUDGE = ROOT / "judge" / "runs" / "haupt-01-j1" / "judge.jsonl"
OUT = AUSWERTUNG / "ergebnisse" / "strang3"
BED = ("rag", "llm")
ITEMS = ["q1", "q2", "q3", "q4", "q5", "q6"]
ITEM_NAME = {"q1": "Q1 Korrektheit (wahrgenommen, 1–3)", "q2": "Q2 Vollständigkeit", "q3": "Q3 Verständlichkeit",
             "q4": "Q4 Ton", "q5": "Q5 ohne Änderung sendbar", "q6": "Q6 Gesamtqualität"}
SPANNE = {"q1": (1, 3), **{q: (1, 5) for q in ITEMS[1:]}}
MIN_DAUER_S = 300          # Sensitivitätsanalyse (AW-07): Bearbeitungszeit unter 5 Minuten
LABELS = {  # Antwortoptionen in der Reihenfolge von FRAGEBOGEN.md (Qualtrics: Export values 1 … n)
    "s1": ["unter 20", "20–29", "30–39", "40–49", "50–59", "60 und älter"],
    "s2": ["weiblich", "männlich", "divers", "keine Angabe"],
    "s3": ["kein Abschluss", "Schulabschluss", "abgeschlossene Ausbildung", "Bachelor", "Master oder höher",
           "keine Angabe"],
    "s4": ["ja, aktuell", "ja, früher", "nein"],
    "s5": ["täglich", "wöchentlich", "monatlich", "seltener", "nie"],
}
S_NAME = {"s1": "S1 Altersgruppe", "s2": "S2 Geschlecht", "s3": "S3 Bildungsabschluss",
          "s4": "S4 Erfahrung im Kundenservice", "s5": "S5 Nutzung von KI-Chatbots"}
GRUPPEN = [("kb_abdeckung", "KB-Abdeckung", ["gedeckt", "gap"]),
           ("schwierigkeit", "Schwierigkeit", ["einfach", "mittel", "komplex", "kb_gap"]),
           ("kategorie", "Kategorie", ["Versand", "Retoure", "Reklamation/Garantie", "Zahlung"])]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def lies_csv(path: Path) -> list:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def mittel(werte):
    return sum(werte) / len(werte)


def je_entwurf(bew: list) -> dict:
    """Mittelwerte Q1–Q6 je (Ticket, Bedingung) über alle vorhandenen Urteile."""
    d = defaultdict(list)
    for r in bew:
        d[(r["ticket_id"], r["bedingung"])].append(r)
    return {k: {"n": len(v), **{q: mittel([int(r[q]) for r in v]) for q in ITEMS},
                **{f: v[0][f] for f in ("entwurf_id", "kb_abdeckung", "schwierigkeit", "kategorie")}}
            for k, v in d.items()}


def h2_test(ent: dict) -> tuple:
    tickets = sorted({t for t, b in ent if (t, "rag") in ent and (t, "llm") in ent})
    x = [ent[(t, "rag")]["q6"] for t in tickets]
    y = [ent[(t, "llm")]["q6"] for t in tickets]
    return tickets, x, y, st.wilcoxon(x, y)


def main() -> None:
    bew = lies_csv(DATEN / "bewertungen.csv")
    pers = {p["response_id"]: p for p in lies_csv(DATEN / "teilnehmende.csv")}
    with JUDGE.open(encoding="utf-8") as f:
        judge = {(e["ticket_id"], e["bedingung"]): e for e in map(json.loads, f)}

    fehler = []
    je_person = Counter(r["response_id"] for r in bew)
    if set(je_person) != set(pers):
        fehler.append("Personen in bewertungen.csv und teilnehmende.csv stimmen nicht überein")
    fehler += [f"{p}: {n} statt 12 Bewertungen" for p, n in je_person.items() if n != 12]
    for r in bew:
        for q in ITEMS:
            lo, hi = SPANNE[q]
            if not r[q].isdigit() or not lo <= int(r[q]) <= hi:
                fehler.append(f"{r['response_id']} {r['entwurf_id']}: {q} = {r[q]!r} außerhalb {lo}–{hi}")
        if (r["ticket_id"], r["bedingung"]) not in judge:
            fehler.append(f"{r['entwurf_id']}: Ticket/Bedingung nicht im Judge-Lauf")
    if fehler:
        sys.exit("FEHLER:\n" + "\n".join(fehler[:30]))

    ent = je_entwurf(bew)
    schnell = {p for p, v in pers.items() if int(v["dauer_s"]) < MIN_DAUER_S}
    bew_s = [r for r in bew if r["response_id"] not in schnell]
    ent_s = je_entwurf(bew_s)
    ks = {p: v["ks_erfahrung"] for p, v in pers.items()}
    dauer = sorted(int(v["dauer_s"]) / 60 for v in pers.values())

    L = ["# Strang 3: Online-Befragung", "",
         f"Erzeugt mit `auswertung/strang3.py` am {now_iso()[:10]}. {len(pers)} vollständige Teilnahmen, "
         f"{len(bew)} Bewertungen von {len(ent)} Entwürfen ({len({t for t, _ in ent})} Ticketpaare). Urteile je Entwurf "
         "gemittelt, alle Tests zweiseitig mit α = 0,05.", ""]

    # ---------------------------------------------------------------- Stichprobe
    n_urteile = Counter(e["n"] for e in ent.values())
    L += ["## Stichprobe", "",
          "- Urteile je Entwurf: " + ", ".join(f"{k} Urteile bei {v} Entwürfen" for k, v in sorted(n_urteile.items())),
          f"- Erfahrung im Kundenservice: {sum(v == 'ja' for v in ks.values())} ja, {sum(v == 'nein' for v in ks.values())} nein",
          f"- Bearbeitungszeit: Median {de(st.quartile(dauer)[0], 1)} min (IQR {de(st.quartile(dauer)[1], 1)}–"
          f"{de(st.quartile(dauer)[2], 1)}), Minimum {de(dauer[0], 1)} min, Maximum {de(dauer[-1], 1)} min",
          f"- Bearbeitungszeit unter {MIN_DAUER_S // 60} Minuten: {len(schnell)} Personen "
          f"({sum(ks[p] == 'ja' for p in schnell)} mit, {sum(ks[p] == 'nein' for p in schnell)} ohne Erfahrung im "
          "Kundenservice); Sensitivitätsanalyse ohne diese Personen (AW-07)", "",
          "| Merkmal | Ausprägung | n |", "| --- | --- | --- |"]
    for s, labels in LABELS.items():
        cnt = Counter(v[s] for v in pers.values())
        for i, lab in enumerate(labels, start=1):
            if cnt.get(str(i)):
                L.append(f"| {S_NAME[s]} | {lab} | {cnt[str(i)]} |")
        if cnt.get(""):
            L.append(f"| {S_NAME[s]} | ohne Angabe | {cnt['']} |")
    L += ["", "Zuordnung der Codes zu den Antwortoptionen nach der Reihenfolge in FRAGEBOGEN.md (Qualtrics, Export values).",
          ""]

    # ---------------------------------------------------------------- H2
    tickets, x, y, h2 = h2_test(ent)
    tickets_s, xs, ys, h2s = h2_test(ent_s)
    L += ["## H2: Gesamtqualität (Q6)", "",
          "| | alle Bewertenden | ohne Bearbeitungszeit < 5 min |", "| --- | --- | --- |",
          f"| Personen | {len(pers)} | {len(pers) - len(schnell)} |",
          f"| Ticketpaare | {len(tickets)} | {len(tickets_s)} |",
          f"| Q6 RAG, Median (IQR) | {mdn_iqr(x)} | {mdn_iqr(xs)} |",
          f"| Q6 LLM-only, Median (IQR) | {mdn_iqr(y)} | {mdn_iqr(ys)} |",
          f"| RAG höher / gleich / LLM-only höher | {h2['n_pos']} / {h2['n_paare'] - h2['n_ungleich']} / {h2['n_neg']} | "
          f"{h2s['n_pos']} / {h2s['n_paare'] - h2s['n_ungleich']} / {h2s['n_neg']} |",
          f"| Wilcoxon (exakt) | T+ = {de(h2['t_plus'], 1)}, {p_text(h2['p'])} | T+ = {de(h2s['t_plus'], 1)}, "
          f"{p_text(h2s['p'])} |",
          f"| z, Effektstärke r | z = {de(h2['z'])}, r = {de(h2['r'])} ({st.r_stufe(h2['r'])}) | z = {de(h2s['z'])}, "
          f"r = {de(h2s['r'])} ({st.r_stufe(h2s['r'])}) |", ""]
    weg = len(tickets) - len(tickets_s)
    if weg:
        L += [f"In der Sensitivitätsanalyse entfallen {weg} Ticketpaare, weil alle Bewertenden ihres Blocks unter "
              f"{MIN_DAUER_S // 60} Minuten lagen.", ""]

    # ---------------------------------------------------------------- Q1–Q6 beschreibend
    L += ["## Items Q1–Q6 je Bedingung (beschreibend)", "",
          "Mittelwerte der Urteile je Entwurf; Median (IQR) über die 60 Entwürfe je Bedingung.", "",
          "| Item | RAG | LLM-only | Differenz der Mediane |", "| --- | --- | --- | --- |"]
    for q in ITEMS:
        vr = [ent[(t, "rag")][q] for t in tickets]
        vl = [ent[(t, "llm")][q] for t in tickets]
        L.append(f"| {ITEM_NAME[q]} | {mdn_iqr(vr)} | {mdn_iqr(vl)} | {de(st.quartile(vr)[0] - st.quartile(vl)[0])} |")
    L.append("")

    # ---------------------------------------------------------------- ICC
    daten = [{"wert": int(r[q]), "item": q, "entwurf": r["entwurf_id"], "person": r["response_id"]} for r in bew for q in ITEMS]
    L += ["## Übereinstimmung der Bewertenden (ICC)", "",
          "Zwei-Weg-Zufallsmodell, absolute Übereinstimmung; Varianzkomponenten aus einem linearen gemischten Modell "
          "mit gekreuzten Zufallseffekten für Entwurf und Person (DEMI 2.4). Einordnung nach Koo und Li (2016).", "",
          "| Item | ICC(2,1) | ICC(2,3) | Einordnung ICC(2,3) | σ² Entwurf | σ² Person | σ² Rest |",
          "| --- | --- | --- | --- | --- | --- | --- |"]
    iccs = {}
    for q in ITEMS:
        ic = st.icc_gemischt([d for d in daten if d["item"] == q], "wert", "entwurf", "person")
        iccs[q] = ic
        L.append(f"| {ITEM_NAME[q]} | {de(ic['icc_2_1'])} | {de(ic['icc_2_3'])} | {st.icc_stufe(ic['icc_2_3'])} | "
                 f"{de(ic['var_entwurf'], 3)} | {de(ic['var_person'], 3)} | {de(ic['var_rest'], 3)} |"
                 + ("" if ic["konvergiert"] else " (nicht konvergiert)"))
    ic_s = st.icc_gemischt([{"wert": int(r["q6"]), "entwurf": r["entwurf_id"], "person": r["response_id"]} for r in bew_s],
                           "wert", "entwurf", "person")
    L += ["", f"Sensitivitätsanalyse Q6 ohne Bearbeitungszeit < {MIN_DAUER_S // 60} min: ICC(2,1) = {de(ic_s['icc_2_1'])}, "
          f"ICC(2,3) = {de(ic_s['icc_2_3'])}.", ""]

    # ---------------------------------------------------------------- Erfahrung im Kundenservice
    pr = defaultdict(lambda: {"rag": [], "llm": []})
    for r in bew:
        pr[r["response_id"]][r["bedingung"]].append(int(r["q6"]))
    niveau = {p: mittel(v["rag"] + v["llm"]) for p, v in pr.items()}
    vorteil = {p: mittel(v["rag"]) - mittel(v["llm"]) for p, v in pr.items()}
    ja = [p for p in pr if ks[p] == "ja"]
    nein = [p for p in pr if ks[p] == "nein"]
    mw_n = st.mann_whitney([niveau[p] for p in ja], [niveau[p] for p in nein])
    mw_v = st.mann_whitney([vorteil[p] for p in ja], [vorteil[p] for p in nein])
    L += ["## Bewertende mit und ohne Erfahrung im Kundenservice", "",
          "Analyseeinheit ist die Person (AW-08): mittlere Gesamtqualität (Q6) über ihre zwölf Entwürfe und ihr "
          "wahrgenommener RAG-Vorteil (Mittel Q6 RAG minus Mittel Q6 LLM-only, je sechs Entwürfe).", "",
          f"| Kennzahl | mit Erfahrung (n = {len(ja)}) | ohne Erfahrung (n = {len(nein)}) | Mann-Whitney-U |",
          "| --- | --- | --- | --- |",
          f"| Q6 gesamt, Median (IQR) | {mdn_iqr([niveau[p] for p in ja])} | {mdn_iqr([niveau[p] for p in nein])} | "
          f"U = {de(mw_n['u'], 1)}, {p_text(mw_n['p'])}, r = {de(mw_n['r'])} |",
          f"| RAG-Vorteil in Q6, Median (IQR) | {mdn_iqr([vorteil[p] for p in ja])} | {mdn_iqr([vorteil[p] for p in nein])} | "
          f"U = {de(mw_v['u'], 1)}, {p_text(mw_v['p'])}, r = {de(mw_v['r'])} |",
          ""]
    ja_s, nein_s = [p for p in ja if p not in schnell], [p for p in nein if p not in schnell]
    mw_vs = st.mann_whitney([vorteil[p] for p in ja_s], [vorteil[p] for p in nein_s])
    L += [f"Unter den {len(schnell)} Personen mit Bearbeitungszeit unter {MIN_DAUER_S // 60} Minuten haben "
          f"{sum(ks[p] == 'nein' for p in schnell)} keine Erfahrung im Kundenservice; der Gruppenvergleich ist damit "
          f"mit der Bearbeitungszeit vermengt. Ohne diese Personen: RAG-Vorteil mit Erfahrung (n = {len(ja_s)}) "
          f"{mdn_iqr([vorteil[p] for p in ja_s])}, ohne Erfahrung (n = {len(nein_s)}) {mdn_iqr([vorteil[p] for p in nein_s])}; "
          f"U = {de(mw_vs['u'], 1)}, {p_text(mw_vs['p'])}, r = {de(mw_vs['r'])}.", ""]

    # ---------------------------------------------------------------- H6
    def korr(k):
        return KORREKT_WERT[judge[k]["korrektheit"]]

    keys = sorted(ent)
    keys_s = sorted(ent_s)
    sp = st.spearman([ent[k]["q1"] for k in keys], [korr(k) for k in keys], seed="20261026:h6")
    sp_s = st.spearman([ent_s[k]["q1"] for k in keys_s], [korr(k) for k in keys_s], seed="20261026:h6s")
    erg = [("Q6 Gesamtqualität – Korrektheit (Judge)", [ent[k]["q6"] for k in keys], [korr(k) for k in keys])]
    kk = [k for k in keys if judge[k]["kb_supportedness"] is not None]
    erg.append(("Q6 Gesamtqualität – KB-Supportedness", [ent[k]["q6"] for k in kk], [judge[k]["kb_supportedness"] for k in kk]))
    erg.append(("Q2 Vollständigkeit – Answer Relevance", [ent[k]["q2"] for k in keys], [judge[k]["answer_relevance"] for k in keys]))
    L += ["## H6: Zusammenhang von menschlicher und automatisierter Bewertung", "",
          "Spearmans ρ über die bewerteten Entwürfe (beide Bedingungen); 95-%-Konfidenzintervall per Bootstrap "
          "(10.000 Ziehungen, fester Seed).", "",
          "| Zusammenhang | n | ρ | 95-%-KI | p |", "| --- | --- | --- | --- | --- |",
          f"| **Q1 wahrgenommene Korrektheit – Korrektheit (Judge)** | {sp['n']} | {de(sp['rho'])} | {de(sp['ci'][0])} bis "
          f"{de(sp['ci'][1])} | {p_text(sp['p'])} |",
          f"| dasselbe ohne Bearbeitungszeit < {MIN_DAUER_S // 60} min | {sp_s['n']} | {de(sp_s['rho'])} | "
          f"{de(sp_s['ci'][0])} bis {de(sp_s['ci'][1])} | {p_text(sp_s['p'])} |"]
    weitere = []
    for name, a, b in erg:
        r = st.spearman(a, b, seed=f"20261026:{name}")
        weitere.append((name, r))
        L.append(f"| {name} (ergänzend) | {r['n']} | {de(r['rho'])} | {de(r['ci'][0])} bis {de(r['ci'][1])} | {p_text(r['p'])} |")
    rho_in = {}
    for b in BED:
        kb = [k for k in keys if k[1] == b]
        if len({korr(k) for k in kb}) > 1:
            rho_in[b] = st.spearman([ent[k]["q1"] for k in kb], [korr(k) for k in kb], seed=f"20261026:h6:{b}")
    L += ["", "Innerhalb der Bedingungen (ergänzend; zeigt, ob der Zusammenhang nur aus dem Bedingungsunterschied "
          "entsteht): " + "; ".join(f"{NAME[b]} ρ = {de(r['rho'])} ({p_text(r['p'])}, n = {r['n']})"
                                     for b, r in rho_in.items()) + ".", "",
          "Mittelwert Q1 je Korrektheitsurteil des Judge:", "",
          "| Judge | n | Q1, Median (IQR) |", "| --- | --- | --- |"]
    for kat in reversed(KORREKTHEIT):
        v = [ent[k]["q1"] for k in keys if judge[k]["korrektheit"] == kat]
        L.append(f"| {kat} | {len(v)} | {mdn_iqr(v)} |")
    L.append("")

    # ---------------------------------------------------------------- Untergruppen
    L += ["## Untergruppen (deskriptiv)", "", "Q6 je Entwurf, Median nach Bedingung; Paarvergleich der Mittelwerte.", "",
          "| Gruppe | Ticketpaare | Q6 RAG | Q6 LLM-only | RAG höher / gleich / niedriger |", "| --- | --- | --- | --- | --- |"]
    for feld, titel, stufen in GRUPPEN:
        for s in stufen:
            tt = [t for t in tickets if ent[(t, "rag")][feld] == s]
            if not tt:
                continue
            hoeher = sum(ent[(t, "rag")]["q6"] > ent[(t, "llm")]["q6"] + 1e-9 for t in tt)
            niedriger = sum(ent[(t, "rag")]["q6"] < ent[(t, "llm")]["q6"] - 1e-9 for t in tt)
            L.append(f"| {titel}: {s} | {len(tt)} | {de(st.quartile([ent[(t, 'rag')]['q6'] for t in tt])[0])} | "
                     f"{de(st.quartile([ent[(t, 'llm')]['q6'] for t in tt])[0])} | {hoeher} / {len(tt) - hoeher - niedriger} / {niedriger} |")
    L.append("")

    # ---------------------------------------------------------------- Ausgabe
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / "entwuerfe.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["entwurf_id", "ticket_id", "bedingung", "kb_abdeckung", "schwierigkeit", "kategorie", "n_urteile"]
                   + [f"{q}_mittel" for q in ITEMS] + ["n_urteile_ohne_schnelle", "q6_mittel_ohne_schnelle",
                                                       "korrektheit_judge"])
        for k in keys:
            e, es = ent[k], ent_s.get(k)
            w.writerow([e["entwurf_id"], k[0], k[1], e["kb_abdeckung"], e["schwierigkeit"], e["kategorie"], e["n"]]
                       + [round(e[q], 4) for q in ITEMS] + [es["n"] if es else 0, round(es["q6"], 4) if es else "",
                                                           judge[k]["korrektheit"]])
    with (OUT / "tests.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["analyse", "stichprobe", "n", "statistik", "p", "effekt"])
        w.writerow(["H2 Wilcoxon exakt", "alle", h2["n_paare"], h2["t_plus"], h2["p"], round(h2["r"], 4)])
        w.writerow(["H2 Wilcoxon exakt", f"ohne < {MIN_DAUER_S} s", h2s["n_paare"], h2s["t_plus"], h2s["p"], round(h2s["r"], 4)])
        w.writerow(["H6 Spearman Q1-Korrektheit", "alle", sp["n"], round(sp["rho"], 4), sp["p"], ""])
        w.writerow(["H6 Spearman Q1-Korrektheit", f"ohne < {MIN_DAUER_S} s", sp_s["n"], round(sp_s["rho"], 4), sp_s["p"], ""])
        for name, r in weitere:
            w.writerow([f"ergänzend {name}", "alle", r["n"], round(r["rho"], 4), r["p"], ""])
        for q, ic in iccs.items():
            w.writerow([f"ICC {q}", "alle", len(ent), "", "", f"ICC(2,1)={ic['icc_2_1']:.4f}; ICC(2,3)={ic['icc_2_3']:.4f}"])
        w.writerow(["Mann-Whitney Q6 gesamt", "Personen", f"{len(ja)}/{len(nein)}", mw_n["u"], mw_n["p"], round(mw_n["r"], 4)])
        w.writerow(["Mann-Whitney RAG-Vorteil", "Personen", f"{len(ja)}/{len(nein)}", mw_v["u"], mw_v["p"], round(mw_v["r"], 4)])
        w.writerow(["Mann-Whitney RAG-Vorteil", f"Personen ohne < {MIN_DAUER_S} s", f"{len(ja_s)}/{len(nein_s)}", mw_vs["u"],
                    mw_vs["p"], round(mw_vs["r"], 4)])

    bilder = abbildungen(ent, ent_s, tickets, tickets_s, judge, len(pers), len(pers) - len(schnell))
    L += [f"![{b}]({b})" for b in bilder] + [""]
    (OUT / "bericht.md").write_text("\n".join(L), encoding="utf-8")
    meta = {"erzeugt": now_iso(), "skript": "auswertung/strang3.py", "git": git_info(),
            "eingaben": {"bewertungen_csv": file_hash(DATEN / "bewertungen.csv"),
                         "teilnehmende_csv": file_hash(DATEN / "teilnehmende.csv"), "judge_jsonl": file_hash(JUDGE)},
            "sensitivitaet_min_dauer_s": MIN_DAUER_S, "ausgeschlossen_sensitivitaet": len(schnell),
            "versionen": {"python": sys.version.split()[0],
                          **{m: __import__(m).__version__ for m in ("scipy", "statsmodels", "pandas", "matplotlib")}}}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"H2 alle: {p_text(h2['p'])}, r = {de(h2['r'])} | ohne schnelle: {p_text(h2s['p'])}, r = {de(h2s['r'])}")
    print(f"H6 ρ = {de(sp['rho'])} ({p_text(sp['p'])}) | ICC(2,3) Q6 = {de(iccs['q6']['icc_2_3'])}")
    print(f"Geschrieben: {OUT.relative_to(ROOT)}/ (bericht.md, entwuerfe.csv, tests.csv, {', '.join(bilder)}, meta.json)")


def abbildungen(ent, ent_s, tickets, tickets_s, judge, n_alle, n_ohne) -> list:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    import random
    from statistik import FARBE, GRID, TEXT, TEXT2
    plt.rcParams.update({"font.size": 8.5, "axes.edgecolor": TEXT2, "axes.labelcolor": TEXT2,
                         "xtick.color": TEXT2, "ytick.color": TEXT2, "text.color": TEXT})
    rng = random.Random(1)

    def stil(ax):
        ax.yaxis.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

    def q6_panel(ax, e, tt, titel):
        daten = [[e[(t, b)]["q6"] for t in tt] for b in BED]
        bp = ax.boxplot(daten, widths=0.5, patch_artist=True, showfliers=False,
                        medianprops={"color": TEXT, "linewidth": 1.4},
                        whiskerprops={"color": TEXT2, "linewidth": 1}, capprops={"color": TEXT2, "linewidth": 1})
        for patch, b in zip(bp["boxes"], BED):
            patch.set_facecolor(FARBE[b])
            patch.set_alpha(0.3)
            patch.set_edgecolor(FARBE[b])
        for i, (b, vals) in enumerate(zip(BED, daten), start=1):
            ax.scatter([i + rng.uniform(-0.16, 0.16) for _ in vals], vals, s=9, color=FARBE[b], alpha=0.75, linewidths=0)
        ax.set_xticks([1, 2], [f"{NAME[b]}\n({len(tt)} Entwürfe)" for b in BED])
        if titel:
            ax.set_title(titel, fontsize=9, color=TEXT, loc="left")
        ax.set_ylim(0.8, 5.2)
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: de(v, 1)))
        stil(ax)

    fig, ax = plt.subplots(figsize=(4.2, 2.8), dpi=300)
    q6_panel(ax, ent, tickets, "")
    ax.set_ylabel("Q6 Gesamtqualität,\nMittel je Entwurf")
    fig.tight_layout()
    fig.savefig(OUT / "q6.png", facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.8), dpi=300, sharey=True)
    q6_panel(axes[0], ent, tickets, f"alle Bewertenden (n = {n_alle})")
    q6_panel(axes[1], ent_s, tickets_s, f"ohne Bearbeitungszeit < 5 min (n = {n_ohne})")
    axes[0].set_ylabel("Q6 Gesamtqualität, Mittel je Entwurf")
    fig.tight_layout()
    fig.savefig(OUT / "q6_sensitivitaet.png", facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.3, 2.8), dpi=300)
    keys = sorted(ent)
    for b in BED:
        kb = [k for k in keys if k[1] == b]
        xs = [KORREKT_WERT[judge[k]["korrektheit"]] + (-0.12 if b == "rag" else 0.12) + rng.uniform(-0.08, 0.08) for k in kb]
        ax.scatter(xs, [ent[k]["q1"] for k in kb], s=12, color=FARBE[b], alpha=0.8, linewidths=0, label=NAME[b])
    for i, kat in enumerate(KORREKTHEIT):
        v = [ent[k]["q1"] for k in keys if judge[k]["korrektheit"] == kat]
        if v:
            m = st.quartile(v)[0]
            ax.plot([i - 0.3, i + 0.3], [m, m], color=TEXT, linewidth=1.6)
    ax.set_xticks(range(3), [f"{k}\n(Judge)" for k in KORREKTHEIT])
    ax.set_ylabel("Q1 wahrgenommene Korrektheit\n(Mittel je Entwurf, 1–3)")
    ax.set_ylim(0.9, 3.1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: de(v, 2)))
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    stil(ax)
    fig.tight_layout()
    fig.savefig(OUT / "h6.png", facecolor="white")
    plt.close(fig)
    return ["q6.png", "q6_sensitivitaet.png", "h6.png"]


if __name__ == "__main__":
    main()
