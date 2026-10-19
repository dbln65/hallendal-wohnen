"""Prüft eine Kodiertabelle auf Vollständigkeit und Regelkonsistenz (LEITFADEN.md, AUSLEGUNGEN.md, K-08).

Aufruf (im Repo-Hauptverzeichnis):
    python kodierung/pruefe_kodierung.py                                        # Erstkodierung
    python kodierung/pruefe_kodierung.py kodierung/zweitkodierung/kodiertabelle_zweit.xlsx

Ausgabe:
- FEHLER   verletzen eine Regel und müssen behoben werden (Exit-Code 1)
- HINWEISE sind zulässig, sollten aber einmal geprüft werden

Geprüft wird nur die Form und die Konsistenz der Codes untereinander, nicht die inhaltliche Richtigkeit.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("FEHLER: openpyxl fehlt. Installation: pip install openpyxl")

KODIER_DIR = Path(__file__).resolve().parent
C1 = {"gedeckt", "teilweise", "nicht gedeckt"}
C2 = {"passend", "nicht passend", "kein Beleg"}
JA_NEIN = {"ja", "nein"}
FT = ["F1", "F2", "F3", "F4"]
NA = "n. a."
CODE_COLS = ["K1_C1", "K1_C2", "K2_C1", "K2_C2", "K3_C1", "K3_C2", "C3", "mangel", "F_primaer", "F_weitere"]
# Hinweis auf fehlende Information statt Sachaussage (AUSLEGUNGEN A-01); Sätze mit Begründung („da …“) ausgenommen
HINWEIS = re.compile(r"keine (gesicherten |genauen )?Informationen|liegen uns|liegt uns|nicht bekannt|"
                     r"in unseren Informationen|keine verbindliche Auskunft", re.I)
BEGRUENDUNG = re.compile(r"\b(da|weil)\b", re.I)


def s(value) -> str:
    return "" if value is None else str(value).strip()


def split_f(value: str) -> list:
    return [x.strip() for x in re.split(r"[;,]", value) if x.strip()]


def pruefe(path: Path):
    ws = openpyxl.load_workbook(path)["Kodierung"]
    rows = list(ws.iter_rows(values_only=True))
    head = [s(h) for h in rows[0]]
    data = [dict(zip(head, r)) for r in rows[1:] if any(v not in (None, "") for v in r)]
    fehler, hinweise = defaultdict(list), defaultdict(list)

    ids = [s(d["kodier_id"]) for d in data]
    if len(set(ids)) != len(ids) or not all(re.fullmatch(r"K\d{3}", i) for i in ids):
        fehler["Kodier-IDs doppelt oder ungültig"].append(("–", ", ".join(ids[:5]) + " …"))

    for d in data:
        kid, bed, gap = s(d["kodier_id"]), s(d["bedingung"]), s(d["kb_abdeckung"]) == "gap"
        for k in CODE_COLS:
            if isinstance(d[k], str) and d[k] != d[k].strip():
                fehler["Leerzeichen um einen Code"].append((kid, f"{k}={d[k]!r}"))
        ks = [s(d[f"K{i}"]) for i in (1, 2, 3)]
        da = [bool(k) for k in ks]
        if da != sorted(da, reverse=True):
            fehler["Lücke zwischen K1–K3"].append((kid, f"belegt: {da}"))
        c1s, c2s = [], []
        for i in (1, 2, 3):
            k, c1, c2 = ks[i - 1], s(d[f"K{i}_C1"]), s(d[f"K{i}_C2"])
            if not k:
                if c1:
                    fehler["C1 ohne Kernaussage"].append((kid, f"K{i}_C1={c1!r}"))
                if bed == "rag" and c2:
                    fehler["C2 ohne Kernaussage"].append((kid, f"K{i}_C2={c2!r}"))
                continue
            if c1 not in C1:
                fehler["C1 fehlt oder ungültig"].append((kid, f"K{i}_C1={c1!r}"))
            else:
                c1s.append(c1)
            if bed == "rag":
                if c2 not in C2:
                    fehler["C2 fehlt oder ungültig"].append((kid, f"K{i}_C2={c2!r}"))
                else:
                    c2s.append(c2)
            elif c2 != "kein Beleg":
                fehler["LLM-only: C2 muss „kein Beleg“ sein"].append((kid, f"K{i}_C2={c2!r}"))
            if c1 != "gedeckt" and HINWEIS.search(k) and not BEGRUENDUNG.search(k):
                hinweise["Kernaussage klingt nach Hinweis auf fehlende Information (A-01)"].append((kid, f"K{i}: {k[:90]}"))
        c3 = s(d["C3"])
        if c3 not in JA_NEIN:
            fehler["C3 fehlt oder ungültig"].append((kid, f"C3={c3!r}"))
        elif not any(da) and c3 != "ja":
            fehler["keine Kernaussage, aber C3 = nein"].append((kid, ""))

        mangel, fp, fw = s(d["mangel"]), s(d["F_primaer"]), s(d["F_weitere"])
        if bed == "llm":
            if (mangel, fp, fw) != (NA, NA, NA):
                fehler["LLM-only: mangel und F müssen „n. a.“ sein"].append((kid, f"{mangel!r}/{fp!r}/{fw!r}"))
            continue
        weitere = split_f(fw)
        if mangel not in JA_NEIN:
            fehler["mangel fehlt oder ungültig"].append((kid, f"mangel={mangel!r}"))
        if fp not in FT + ["keiner"]:
            fehler["F_primaer fehlt oder ungültig"].append((kid, f"F_primaer={fp!r} (mangel={mangel!r})"))
        if any(x not in FT for x in weitere):
            fehler["F_weitere ungültig"].append((kid, f"F_weitere={fw!r}"))
        if mangel == "nein" and (fp in FT or weitere):
            fehler["mangel = nein, aber Fehlertyp vergeben"].append((kid, f"{fp} {fw}".strip()))
        if mangel == "ja" and fp in ("", "keiner"):
            fehler["mangel = ja, aber kein Fehlertyp"].append((kid, f"F_primaer={fp!r}"))
        if fp in FT:
            if fp in weitere:
                fehler["F_primaer steht auch in F_weitere"].append((kid, f"{fp} / {fw}"))
            if any(x in FT and FT.index(x) < FT.index(fp) for x in weitere):
                fehler["F_weitere liegt in der Prüfreihenfolge vor F_primaer"].append((kid, f"{fp} / {fw}"))
        alle_f = ([fp] if fp in FT else []) + weitere
        c1_problem = any(c != "gedeckt" for c in c1s)
        c2_problem = any(c != "passend" for c in c2s)
        if (c1_problem or c2_problem) and mangel == "nein":
            fehler["C1/C2-Problem, aber mangel = nein"].append((kid, f"C1={c1s} C2={c2s}"))
        if c2_problem and mangel == "ja" and "F4" not in alle_f:
            fehler["Belegproblem in C2, aber kein F4"].append((kid, f"C2={c2s} F={alle_f}"))
        if "F4" in alle_f and not c2_problem:
            fehler["F4 ohne Belegproblem in C2"].append((kid, f"C2={c2s} F={alle_f}"))
        if c1_problem and fp == "F4":
            fehler["Kernaussage nicht (voll) gedeckt, aber F_primaer = F4"].append((kid, f"C1={c1s}"))
        if gap and mangel == "ja" and fp != "F1":
            fehler["KB-Gap mit Mangel, aber F_primaer ≠ F1"].append((kid, f"F_primaer={fp}"))
        if not gap and fp == "F1":
            hinweise["F1 bei KB-gedecktem Ticket"].append((kid, s(d["bemerkung"])[:90]))
        if mangel == "ja" and not c1_problem and not c2_problem and c3 == "nein":
            hinweise["Mangel ohne C1/C2-Problem und ohne Rückfrage (nur offenes Anliegen?)"].append((kid, f"F={alle_f}"))
        if gap and mangel == "nein" and c3 == "nein":
            hinweise["KB-Gap ohne Rückfrage und ohne Mangel"].append((kid, ""))
    return data, fehler, hinweise


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else KODIER_DIR / "kodiertabelle.xlsx"
    data, fehler, hinweise = pruefe(path)
    print(f"{path.name}: {len(data)} Entwürfe geprüft")
    for title, groups in (("FEHLER", fehler), ("HINWEISE", hinweise)):
        n = sum(len(v) for v in groups.values())
        print(f"\n{title}: {n}")
        for cat, items in groups.items():
            print(f"  {cat} ({len(items)})")
            for kid, text in items:
                print(f"    {kid}: {text}" if text else f"    {kid}")
    sys.exit(1 if fehler else 0)


if __name__ == "__main__":
    main()
