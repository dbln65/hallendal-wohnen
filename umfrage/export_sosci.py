"""Erzeugt die Dateien für den Aufbau der Befragung in SoSci Survey (Anleitung: SOSCI.md, Entscheidungen U-05 bis U-07).

Eingabe:
- umfrage/entwuerfe.csv    verblindete Entwürfe mit Block (aus prepare_survey.py)
- tickets.jsonl            Pilottickets P-05 (Übungsfall) und P-07 (Ankerbeispiele)
- umfrage/FRAGEBOGEN.md    Abgleich: Anker und Übungsfall müssen dort wörtlich stehen

Ausgabe in umfrage/sosci/ (wird bei jedem Lauf überschrieben):
- inhalte.csv          Import in die Inhaltsdatenbank: 120 Entwürfe, Übungsfall, Ankerbeispiele (ohne Kopfzeile)
- php_zuteilung.txt    PHP-Code Seite „IS“: Blockzuteilung per Urne, zufällige Reihenfolge, Speicherung
- php_anker.txt        PHP-Code Seite „IS“: Ankerbeispiele
- php_uebung.txt       PHP-Code Seite „UE“: Übungsfall
- php_bewertung.txt    PHP-Code Seite „BW“: 12 Entwürfe per loopPage()
- items_BW01.txt       Items für Q1 (12 Positionen + Übung), Direktimport
- items_BW02.txt       Items für Q2–Q5 (je Position 4 Items + Übung), Direktimport
- items_BW03.txt       Items für Q6 (12 Positionen + Übung), Direktimport
- urne.txt             Lose 1–10 für beide Urnen

Aufruf (im Repo-Hauptverzeichnis):
    python umfrage/export_sosci.py
"""

import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

UMFRAGE_DIR = Path(__file__).resolve().parent
ROOT = UMFRAGE_DIR.parent
OUT = UMFRAGE_DIR / "sosci"

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

# Wortlaut DEMI Tabelle 10
Q1 = "Wie fachlich korrekt wirkt die Antwort auf Sie?"
Q2_5 = [
    "Die Antwort geht auf alle Anliegen der Anfrage ein.",
    "Die Antwort ist klar und verständlich formuliert.",
    "Der Ton der Antwort ist für den Kundenservice angemessen.",
    "Die Antwort könnte ohne inhaltliche Änderung an die Kundin bzw. den Kunden gesendet werden.",
]
Q6 = "Wie bewerten Sie die Gesamtqualität dieser Antwort?"

BOX = "border:1px solid #c8c8c8; border-radius:6px; padding:12px 16px; margin:0 0 16px 0; background:#f7f7f7;"


def to_html(text: str) -> str:
    """Absätze als <p>, einfache Zeilenumbrüche als <br>; die Inhaltsdatenbank erlaubt keine Zeilenumbrüche."""
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    out = "".join("<p>" + "<br>".join(html.escape(line.strip(), quote=False) for line in p.split("\n")) + "</p>"
                  for p in paras)
    assert "\n" not in out and "\r" not in out
    return out


def norm(text: str) -> str:
    text = re.sub(r"(?m)^\s*>\s?", "", text)
    text = text.replace("*", "")
    return re.sub(r"\s+", " ", text).strip()


def php_str(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main() -> None:
    with (UMFRAGE_DIR / "entwuerfe.csv").open(encoding="utf-8") as f:
        drafts = list(csv.DictReader(f))
    with (ROOT / "tickets.jsonl").open(encoding="utf-8") as f:
        tickets = {t["ticket_id"]: t for t in map(json.loads, f)}
    fragebogen = norm((UMFRAGE_DIR / "FRAGEBOGEN.md").read_text(encoding="utf-8"))

    # Abgleich mit FRAGEBOGEN.md: Was in SoSci erscheint, muss dort dokumentiert sein
    texts = {
        "Übung Anfrage": tickets[UEBUNG]["ticket_text"], "Übung Antwort": tickets[UEBUNG]["musterantwort"],
        "Anker Anfrage": tickets[ANKER]["ticket_text"], "Anker A": tickets[ANKER]["musterantwort"],
        "Anker B": ANKER_B, "Kommentar A": KOMMENTAR_A, "Kommentar B": KOMMENTAR_B,
        **{f"Q{n}": q for n, q in zip(range(1, 7), [Q1, *Q2_5, Q6])},
    }
    missing = [name for name, t in texts.items() if norm(t) not in fragebogen]
    if missing:
        sys.exit(f"FEHLER: nicht wörtlich in FRAGEBOGEN.md: {missing}")

    blocks = defaultdict(list)
    for d in drafts:
        blocks[int(d["block"])].append(d["entwurf_id"])
    if sorted(blocks) != list(range(1, 11)) or any(len(v) != N_POS for v in blocks.values()):
        sys.exit("FEHLER: entwuerfe.csv enthält nicht 10 Blöcke zu 12 Entwürfen.")

    OUT.mkdir(exist_ok=True)

    # Inhaltsdatenbank: erste Spalte Schlüssel, keine Kopfzeile (SoSci-Hilfe „Content Database“)
    rows = [[d["entwurf_id"], to_html(d["ticket_text"]), to_html(d["antwort"])] for d in drafts]
    rows.append(["UEB", to_html(tickets[UEBUNG]["ticket_text"]), to_html(tickets[UEBUNG]["musterantwort"])])
    rows.append(["ANKER", to_html(tickets[ANKER]["ticket_text"]), to_html(tickets[ANKER]["musterantwort"]),
                 html.escape(KOMMENTAR_A, quote=False), to_html(ANKER_B), html.escape(KOMMENTAR_B, quote=False)])
    with (OUT / "inhalte.csv").open("w", encoding="utf-8", newline="") as f:
        csv.writer(f, quoting=csv.QUOTE_ALL).writerows(rows)

    # Items (Direktimport: ein Item je Zeile). Position p belegt BW01/BW03 Item p und BW02 Items 4p-3 bis 4p;
    # das letzte Item bzw. die letzten 4 Items gehören zum Übungsfall.
    (OUT / "items_BW01.txt").write_text("\n".join([Q1] * (N_POS + 1)) + "\n", encoding="utf-8")
    (OUT / "items_BW02.txt").write_text("\n".join(Q2_5 * (N_POS + 1)) + "\n", encoding="utf-8")
    (OUT / "items_BW03.txt").write_text("\n".join([Q6] * (N_POS + 1)) + "\n", encoding="utf-8")
    (OUT / "urne.txt").write_text("\n".join(str(n) for n in range(1, 11)) + "\n", encoding="utf-8")

    block_lines = ",\n".join(f"    {n} => array(" + ", ".join(php_str(e) for e in sorted(blocks[n])) + ")"
                             for n in range(1, 11))
    zuteilung = f"""// Blockzuteilung (U-05) und zufällige Reihenfolge der 12 Entwürfe (DEMI 1.4.4)
// Erzeugt mit umfrage/export_sosci.py aus umfrage/entwuerfe.csv – nicht von Hand ändern
if (!isset($entwuerfe)) {{
  if (value('SD04') == 3) {{
    urnDraw('ohne_ks', 'IV01', 'end');
    $block = (int)value('IV01_01');
  }} else {{
    urnDraw('mit_ks', 'IV02', 'end');
    $block = (int)value('IV02_01');
  }}
  $bloecke = array(
{block_lines}
  );
  if (!isset($bloecke[$block])) {{
    html('<p style="color:#b00000">Fehler bei der Blockzuteilung (Block: '.$block.').</p>');
  }} else {{
    $entwuerfe = $bloecke[$block];
    shuffle($entwuerfe);
    put('IV03_01', $block);
    for ($i = 0; $i < 12; $i++) {{
      put('IV04_'.($i < 9 ? '0' : '').($i + 1), $entwuerfe[$i]);
    }}
    registerVariable($entwuerfe);
  }}
}}
"""
    box = php_str(BOX)
    anker = f"""// Ankerbeispiele (U-04); Texte aus der Inhaltsdatenbank, Schlüssel ANKER
$box = {box};
$a = dbGet('ANKER');
html(
  '<p style="margin-top:24px">Zur Orientierung folgen zwei Antworten auf dieselbe Anfrage.</p>'.
  '<p><b>Beispielanfrage</b></p><div style="'.$box.'">'.$a[0].'</div>'.
  '<p><b>Beispiel A: eine eher hoch bewertete Antwort</b></p><div style="'.$box.'">'.$a[1].'</div>'.
  '<p><i>Kommentar:</i> '.$a[2].'</p>'.
  '<p style="margin-top:24px"><b>Beispiel B: eine eher niedrig bewertete Antwort</b></p><div style="'.$box.'">'.$a[3].'</div>'.
  '<p><i>Kommentar:</i> '.$a[4].'</p>'
);
"""
    uebung = f"""// Übungsfall (DEMI Tabelle 9, Nr. 5); wird nicht ausgewertet. Texte aus der Inhaltsdatenbank, Schlüssel UEB
$box = {box};
$e = dbGet('UEB');
html(
  '<p><b>Übungsbeispiel:</b> Diese Bewertung dient nur zum Kennenlernen und wird nicht ausgewertet.</p>'.
  '<p><b>Kundenanfrage</b></p><div style="'.$box.'">'.$e[0].'</div>'.
  '<p><b>Antwortentwurf</b></p><div style="'.$box.'">'.$e[1].'</div>'
);
question('BW01', array(13), 'show-title=no');
question('BW02', array(49, 50, 51, 52), 'show-title=no');
question('BW03', array(13), 'show-title=no');
"""
    bewertung = f"""// Bewertungsblock: 12 Entwürfe in zufälliger Reihenfolge (DEMI Tabelle 9, Nr. 6)
// Position p (1–12): BW01 Item p, BW02 Items 4p-3 bis 4p, BW03 Item p; Entwurfs-ID in IV04_p
$box = {box};
$i = loopPage(12);
$e = dbGet($entwuerfe[$i]);
if ($i == 0) {{
  html('<p><b>Jetzt beginnen die 12 Antwortentwürfe.</b></p>');
}}
html(
  '<p style="color:#555555">Antwortentwurf '.($i + 1).' von 12</p>'.
  '<p><b>Kundenanfrage</b></p><div style="'.$box.'">'.$e[0].'</div>'.
  '<p><b>Antwortentwurf</b></p><div style="'.$box.'">'.$e[1].'</div>'
);
question('BW01', array($i + 1), 'show-title=no');
question('BW02', array(4 * $i + 1, 4 * $i + 2, 4 * $i + 3, 4 * $i + 4), 'show-title=no');
question('BW03', array($i + 1), 'show-title=no');
"""
    for name, code in (("php_zuteilung.txt", zuteilung), ("php_anker.txt", anker), ("php_uebung.txt", uebung),
                       ("php_bewertung.txt", bewertung)):
        (OUT / name).write_text(code, encoding="utf-8")

    print(f"Abgleich mit FRAGEBOGEN.md: {len(texts)} Texte wörtlich enthalten")
    print(f"inhalte.csv: {len(rows)} Einträge ({len(drafts)} Entwürfe, UEB, ANKER)")
    print("Blöcke: " + ", ".join(f"{n}: {len(blocks[n])}" for n in range(1, 11)))
    print(f"Geschrieben nach {OUT.relative_to(ROOT)}/: " + ", ".join(sorted(p.name for p in OUT.iterdir())))


if __name__ == "__main__":
    main()
