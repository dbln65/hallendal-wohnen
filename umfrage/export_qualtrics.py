"""Erzeugt die Dateien für den Aufbau der Befragung in Qualtrics (Anleitung: QUALTRICS.md, Entscheidungen U-05 bis U-07).

Eingabe:
- umfrage/entwuerfe.csv    verblindete Entwürfe mit Block (aus prepare_survey.py)
- tickets.jsonl            Pilottickets P-05 (Übungsfall) und P-07 (Ankerbeispiele)
- umfrage/FRAGEBOGEN.md    Abgleich: Anker, Übungsfall und Items müssen dort wörtlich stehen

Ausgabe in umfrage/qualtrics/ (wird bei jedem Lauf überschrieben):
- loop_merge.xlsx       10 Blätter „Block 1“ bis „Block 10“, je 12 Zeilen: Field 1 Entwurfs-ID, Field 2 Kundenanfrage,
                        Field 3 Antwortentwurf (HTML, ohne Zeilenumbrüche); zum Einfügen in Loop & Merge
- zuordnung.csv         Block, Loop-Nummer (Zeile 1–12), Entwurfs-ID; für die Auswertung der exportierten Daten
- bewertung_text.html   Text der Bewertungsseite mit Loop-&-Merge-Feldern
- anker.html            Ankerbeispiele für die Instruktion
- uebung.html           Übungsfall

Aufruf (im Repo-Hauptverzeichnis; benötigt openpyxl: pip install openpyxl):
    python umfrage/export_qualtrics.py
"""

import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

try:
    from openpyxl import Workbook
except ImportError:
    sys.exit("FEHLER: openpyxl fehlt. Installation: pip install openpyxl")

UMFRAGE_DIR = Path(__file__).resolve().parent
ROOT = UMFRAGE_DIR.parent
OUT = UMFRAGE_DIR / "qualtrics"

N_POS = 12
UEBUNG = "P-05"
ANKER = "P-07"
ANKER_B = ("Guten Tag,\n\nbei Unzufriedenheit mit der Zahlung können Sie Ihre Bestellung jederzeit stornieren. "
           "Einschränkungen gibt es bei Zahlungsarten immer, das ist in jedem Online-Shop so. Bitte lesen Sie sich die "
           "Informationen vor dem Kauf selbst durch, dann erübrigen sich solche Nachfragen.\n\n"
           "Viele Grüße, Ihr Hallendal-Wohnen-Team")
KOMMENTAR_A = ("Die Antwort beantwortet die Frage direkt und nennt die Bedingungen. Sie ist klar gegliedert, geht auf den "
               "Ärger ein und könnte ohne Änderung versendet werden. Eine solche Antwort liegt bei den meisten Fragen im "
               "oberen Bereich der Skala.")
KOMMENTAR_B = ("Die Frage nach der Ratenzahlung über 24 Monate bleibt unbeantwortet, der Hinweis auf eine Stornierung geht "
               "am Anliegen vorbei. Der Ton ist belehrend und abweisend. So könnte die Antwort nicht versendet werden. Eine "
               "solche Antwort liegt bei den meisten Fragen im unteren Bereich der Skala.")
ITEMS = [  # Wortlaut DEMI Tabelle 10
    "Wie fachlich korrekt wirkt die Antwort auf Sie?",
    "Die Antwort geht auf alle Anliegen der Anfrage ein.",
    "Die Antwort ist klar und verständlich formuliert.",
    "Der Ton der Antwort ist für den Kundenservice angemessen.",
    "Die Antwort könnte ohne inhaltliche Änderung an die Kundin bzw. den Kunden gesendet werden.",
    "Wie bewerten Sie die Gesamtqualität dieser Antwort?",
]
BOX = "border:1px solid #c8c8c8; border-radius:6px; padding:12px 16px; margin:0 0 16px 0; background:#f7f7f7;"


def to_html(text: str) -> str:
    """Absätze als <p>, einfache Zeilenumbrüche als <br>; Loop-&-Merge-Felder vertragen keine Zeilenumbrüche.
    Anführungszeichen werden als HTML-Entität geschrieben, damit Excel sie beim Kopieren nicht maskiert."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    out = "".join("<p>" + "<br>".join(html.escape(line.strip()) for line in p.split("\n")) + "</p>"
                  for p in paras)
    assert "\n" not in out and "\r" not in out and "\t" not in out
    return out


def norm(text: str) -> str:
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = text.replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


def box(title: str, content: str) -> str:
    return f'<p><strong>{title}</strong></p>\n<div style="{BOX}">{content}</div>\n'


def main() -> None:
    with (UMFRAGE_DIR / "entwuerfe.csv").open(encoding="utf-8") as f:
        drafts = list(csv.DictReader(f))
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}
    fragebogen = norm((UMFRAGE_DIR / "FRAGEBOGEN.md").read_text(encoding="utf-8"))

    # Abgleich mit FRAGEBOGEN.md: Was in Qualtrics erscheint, muss dort dokumentiert sein
    texts = {
        "Übung Anfrage": tickets[UEBUNG]["ticket_text"], "Übung Antwort": tickets[UEBUNG]["musterantwort"],
        "Anker Anfrage": tickets[ANKER]["ticket_text"], "Anker A": tickets[ANKER]["musterantwort"],
        "Anker B": ANKER_B, "Kommentar A": KOMMENTAR_A, "Kommentar B": KOMMENTAR_B,
        **{f"Q{n}": q for n, q in enumerate(ITEMS, start=1)},
    }
    missing = [name for name, t in texts.items() if norm(t) not in fragebogen]
    if missing:
        sys.exit(f"FEHLER: nicht wörtlich in FRAGEBOGEN.md: {missing}")

    blocks = defaultdict(list)
    for d in sorted(drafts, key=lambda d: d["entwurf_id"]):
        blocks[int(d["block"])].append(d)
    if sorted(blocks) != list(range(1, 11)) or any(len(v) != N_POS for v in blocks.values()):
        sys.exit("FEHLER: entwuerfe.csv enthält nicht 10 Blöcke zu 12 Entwürfen.")

    OUT.mkdir(exist_ok=True)

    # Loop & Merge: je Block ein Blatt, Zeile = Loop, Spalte = Field (ohne Kopfzeile, damit A1:C12 direkt einfügbar ist)
    wb = Workbook()
    wb.remove(wb.active)
    rows_map = []
    for n in range(1, 11):
        ws = wb.create_sheet(f"Block {n}")
        for loop, d in enumerate(blocks[n], start=1):
            ws.append([d["entwurf_id"], to_html(d["ticket_text"]), to_html(d["antwort"])])
            rows_map.append({"block": n, "loop": loop, "entwurf_id": d["entwurf_id"]})
        ws.column_dimensions["A"].width = 10
        ws.column_dimensions["B"].width = 60
        ws.column_dimensions["C"].width = 100
    wb.save(OUT / "loop_merge.xlsx")

    with (OUT / "zuordnung.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["block", "loop", "entwurf_id"])
        w.writeheader()
        w.writerows(rows_map)

    (OUT / "bewertung_text.html").write_text(
        box("Kundenanfrage", "${lm://Field/2}") + box("Antwortentwurf", "${lm://Field/3}"),
        encoding="utf-8")
    (OUT / "anker.html").write_text(
        "<p>Zur Orientierung folgen zwei Antworten auf dieselbe Anfrage.</p>\n"
        + box("Beispielanfrage", to_html(tickets[ANKER]["ticket_text"]))
        + box("Beispiel A: eine eher hoch bewertete Antwort", to_html(tickets[ANKER]["musterantwort"]))
        + f"<p><em>Kommentar:</em> {html.escape(KOMMENTAR_A)}</p>\n"
        + box("Beispiel B: eine eher niedrig bewertete Antwort", to_html(ANKER_B))
        + f"<p><em>Kommentar:</em> {html.escape(KOMMENTAR_B)}</p>\n",
        encoding="utf-8")
    (OUT / "uebung.html").write_text(
        "<p><strong>Übungsbeispiel:</strong> Diese Bewertung dient nur zum Kennenlernen und wird nicht ausgewertet.</p>\n"
        + box("Kundenanfrage", to_html(tickets[UEBUNG]["ticket_text"]))
        + box("Antwortentwurf", to_html(tickets[UEBUNG]["musterantwort"])),
        encoding="utf-8")

    print(f"Abgleich mit FRAGEBOGEN.md: {len(texts)} Texte wörtlich enthalten")
    print("loop_merge.xlsx: " + ", ".join(f"Block {n}: {len(blocks[n])}" for n in range(1, 11)))
    print(f"Geschrieben nach {OUT.relative_to(ROOT)}/: " + ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
