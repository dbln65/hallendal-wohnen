# Kodierleitfaden: Quellenbezug und Failure Modes (Strang 4)

Grundlage: DEMI 2.5, 3.3 und Tabelle 12. Ergänzende Regeln: K-01 bis K-08 in [README.md](README.md). Der Leitfaden gilt für Erst- und Zweitkodierung gleichermaßen.

## 1 Material

| Material | Inhalt |
| --- | --- |
| `kodierheft.html` | je Entwurf: Kundenanfrage, Antwortentwurf mit hervorgehobenen Belegen, bei RAG die Prüfhilfe und die drei übergebenen Auszüge, die Referenz (Musterantwort, Kernaussagen, Belegzitate); im Anhang alle 40 KB-Artikel, verlinkt |
| `kodiertabelle.xlsx` | eine Zeile je Entwurf in Kodierreihenfolge; Auswahllisten für die Codes; der Link in der Spalte `kodier_id` öffnet den Entwurf im Kodierheft |

**Maßstab für C1 ist die gesamte Knowledge Base**, nicht die Musterantwort und nicht nur die übergebenen Auszüge. Die Referenz im Heft ist ein Hilfsmittel, um Anliegen und Lücken schneller zu erkennen.

## 2 Ablauf je Entwurf

1. Kundenanfrage lesen und die **Anliegen** bestimmen (meist 1–3 Fragen).
2. Antwortentwurf lesen; **Kernaussagen** K1–K3 bestimmen und in die Tabelle eintragen (Abschnitt 3).
3. Je Kernaussage **C1** (Abschnitt 4) und **C2** (Abschnitt 5).
4. Für den Entwurf **C3** (Abschnitt 6).
5. Nur RAG: **Mangel** prüfen und gegebenenfalls **Fehlertypen** zuordnen (Abschnitt 7).
6. Bei Unsicherheit oder Mischfall kurz in `bemerkung` begründen.

Kodiert wird in der vorgegebenen Reihenfolge (K-05). Bereits kodierte Entwürfe werden nicht nachträglich angepasst, außer bei offensichtlichen Eingabefehlern.

## 3 Kernaussagen

**Definition:** Eine Kernaussage ist eine prüfbare Sachaussage über Regeln, Leistungen, Beträge, Fristen, Abläufe oder Möglichkeiten bei Hallendal Wohnen, die sich auf ein Anliegen der Anfrage bezieht. Prüfbar heißt: Die Knowledge Base könnte sie bestätigen oder widerlegen.

**Keine Kernaussagen sind:**

- Anrede, Grußformel, Dank, Entschuldigung, Verständnisäußerungen
- allgemeine Serviceangebote ohne Sachgehalt („Bei weiteren Fragen melden Sie sich gerne.“)
- Ankündigungen eigener Handlungen („Wir prüfen das und melden uns.“), außer sie behaupten eine Regel („Wir antworten innerhalb von 24 Stunden.“)
- Rückfragen, Hinweise auf fehlende Informationen, Weiterleitungen (→ C3)

**Auswahl und Zuschnitt:**

- Höchstens drei Kernaussagen. Enthält der Entwurf mehr, werden die drei gewählt, die die Anliegen am direktesten beantworten; bei Gleichstand gilt die Reihenfolge im Text.
- Ein Sachverhalt, über mehrere Sätze ausgeführt, ist **eine** Kernaussage. Ein Satz mit zwei unabhängigen Sachverhalten (z. B. Kosten und Lieferzeit) sind **zwei** Kernaussagen.
- Auch vage Aussagen zählen, wenn sie prüfbar sind: „Die Versandkosten hängen vom Gewicht ab“ ist prüfbar (die KB nennt Pauschalen) und damit eine Kernaussage.
- Eintrag in die Tabelle als knappe Paraphrase, z. B. „Paketversand DE kostet 4,95 €“.
- Enthält der Entwurf keine Kernaussage (nur Rückfrage, Enthaltung oder Floskeln), bleiben K1–K3 leer; C1 und C2 entfallen.

## 4 C1 Aussagendeckung (je Kernaussage)

| Wert | Regel |
| --- | --- |
| **gedeckt** | Die KB enthält die Aussage inhaltlich vollständig; Werte und Bedingungen stimmen. Umformulierungen sind zulässig, ebenso Schlussfolgerungen, die sich zwingend aus der KB ergeben (Bestellwert 35 € liegt unter der Gratisgrenze von 49 €, also fallen Versandkosten an). |
| **teilweise** | Der Kern stimmt, aber ein Bestandteil ist in der KB nicht enthalten oder weicht ab, ohne die Aussage umzukehren (z. B. richtige Frist, aber eine zusätzliche Bedingung, die nicht in der KB steht). |
| **nicht gedeckt** | Die KB enthält die Aussage nicht oder widerspricht ihr. Das gilt auch für plausible oder allgemein übliche Aussagen ohne Grundlage in der KB, einschließlich rechtlicher Allgemeinaussagen, die nicht in der KB stehen. |

Beispiele (konstruiert):

- „Ab 49 € liefern wir in Deutschland versandkostenfrei.“ → gedeckt (KB-007)
- „Ab 49 € liefern wir versandkostenfrei, auch Speditionsware.“ → nicht gedeckt, weil die Gratisgrenze laut KB nur für Paketware gilt und die Aussage damit in einem wesentlichen Punkt falsch ist
- „Die Lieferung dauert 2–4 Werktage, in Ausnahmefällen auch länger.“ → teilweise (Kern gedeckt, der Zusatz steht nicht in der KB)

## 5 C2 Quellenpassung (je Kernaussage)

| Wert | Regel |
| --- | --- |
| **passend** | Der Satz mit der Kernaussage trägt einen Beleg `[KB-xxx]`, und der zitierte Artikel stützt die Aussage. Bei mehreren Belegen genügt einer. |
| **nicht passend** | Ein Beleg ist angegeben, der zitierte Artikel stützt die Aussage aber nicht, auch wenn ein anderer Artikel sie stützen würde. |
| **kein Beleg** | Der Satz mit der Kernaussage trägt keinen Beleg. |

- Geprüft wird gegen den **zitierten Artikel als Ganzes** (Belege auf Artikelebene, E-13), nicht nur gegen den übergebenen Auszug.
- Eine nicht gedeckte Aussage (C1) kann nicht passend belegt sein; trägt sie einen Beleg, ist C2 = nicht passend.
- LLM-only: C2 ist mit „kein Beleg“ vorbelegt (K-02).

## 6 C3 Rückfrage oder Enthaltung (je Entwurf)

| Wert | Regel |
| --- | --- |
| **ja** | Zu mindestens einem Anliegen gibt der Entwurf **statt** einer Sachaussage eine Rückfrage (z. B. nach der Bestellnummer), einen Hinweis auf fehlende oder unsichere Informationen oder eine Weiterleitung („Wir klären das intern und melden uns.“). |
| **nein** | Alle Anliegen werden mit Sachaussagen beantwortet. |

- Rückfragen, die **zusätzlich** zu einer Sachaussage gestellt werden und zum Ablauf gehören (z. B. „Bitte senden Sie uns Fotos des Schadens.“, wenn die KB das vorsieht), ergeben C3 = nein.
- Floskeln wie „Bei weiteren Fragen melden Sie sich gerne“ zählen nicht.

## 7 Mangel und Fehlertypen (nur RAG)

### 7.1 Mangel

Ein Mangel liegt vor, wenn mindestens einer der Punkte zutrifft (K-01):

| | Mangel |
| --- | --- |
| a | Eine Kernaussage ist bei C1 **teilweise** oder **nicht gedeckt**. |
| b | Ein Anliegen, das die KB beantwortet, bleibt unbeantwortet oder wird durch Rückfrage bzw. Enthaltung ersetzt (Abgleich mit den Kernaussagen der Musterantwort). |
| c | Eine Kernaussage ist bei C2 **nicht passend** oder **ohne Beleg** (Belegpflicht, E-13). |

Bei KB-Gap-Tickets ist eine Rückfrage oder Enthaltung das erwartete Verhalten und **kein** Mangel nach b. Behauptungen ohne KB-Grundlage sind dort Mängel nach a.

Kein Mangel → `mangel` = nein, `F_primaer` = keiner, `F_weitere` leer.

### 7.2 Fehlertypen in fester Prüfreihenfolge

Der **erste zutreffende** Typ ist `F_primaer`; weitere zutreffende Typen kommen in `F_weitere`.

| Reihenfolge | Typ | trifft zu, wenn … |
| --- | --- | --- |
| 1 | **F1 KB-Fail** | das für den Mangel benötigte Wissen nicht in der KB steht. Bei KB-Gap-Tickets mit Mangel immer F1 (Designmerkmal, aus H5 ausgenommen). |
| 2 | **F2 Retrieval-Fail** | das benötigte Wissen in der KB steht, aber in **keinem der drei übergebenen Auszüge** enthalten ist. Prüfen über die Auszüge im Heft; die Zeile „Belegartikel laut Ticket“ hilft, ersetzt aber nicht den Blick in den Auszug, weil ein Artikel übergeben sein kann, ohne dass der passende Abschnitt dabei ist. |
| 3 | **F3 Generation-Fail** | das benötigte Wissen in den übergebenen Auszügen stand, im Entwurf aber nicht, unvollständig oder falsch genutzt wurde. Dazu gehören auch Aussagen ohne Grundlage, obwohl der passende Auszug vorlag. |
| 4 | **F4 Citation-Fail** | eine Kernaussage keinen Beleg trägt oder der Beleg sie nicht stützt (C2 = kein Beleg oder nicht passend). |

### 7.3 Regeln für Mischfälle (K-03)

| Fall | C1 / C2 / C3 | Fehlertypen |
| --- | --- | --- |
| Beleg an einer nicht gedeckten Aussage, passender Auszug lag vor | nicht gedeckt / nicht passend / – | F3, zusätzlich F4 |
| Beleg an einer nicht gedeckten Aussage, passender Auszug fehlte | nicht gedeckt / nicht passend / – | F2, zusätzlich F3 und F4 |
| Enthaltung bei KB-gedecktem Ticket, passender Auszug lag vor | – / – / ja | F3 |
| Enthaltung bei KB-gedecktem Ticket, passender Auszug fehlte | – / – / ja | F2 |
| KB-Gap-Ticket, kategorische Behauptung ohne KB-Grundlage mit Beleg („Inseln beliefern wir nicht [KB-007]“) | nicht gedeckt / nicht passend / nein | F1, zusätzlich F3 und F4 |
| KB-Gap-Ticket, ehrliche Enthaltung ohne Sachaussage | keine Kernaussage / – / ja | kein Mangel → keiner |
| Korrekte Aussage ohne Beleg | gedeckt / kein Beleg / – | F4 |
| Korrekte Aussage, falscher Artikel zitiert | gedeckt / nicht passend / – | F4 |
| Aussage in der KB gedeckt, aber nicht in den Auszügen enthalten (trotzdem richtig) | gedeckt / je nach Beleg / – | nur F4, falls Belegproblem; sonst kein Mangel |
| Teil eines Anliegens fehlt, übrige Aussagen korrekt | gedeckt / passend / nein | F2 oder F3, je nachdem, ob der passende Auszug vorlag |

## 8 Tabelle ausfüllen

| Spalte | Eintrag |
| --- | --- |
| `K1`–`K3` | Kernaussagen als knappe Paraphrase; leer, wenn keine |
| `Kx_C1`, `Kx_C2` | Auswahlliste; nur bei vorhandener Kernaussage |
| `C3` | ja / nein |
| `mangel` | nur RAG: ja / nein |
| `F_primaer` | nur RAG: F1–F4 oder keiner |
| `F_weitere` | nur RAG: weitere Typen, z. B. `F3;F4` |
| `bemerkung` | Begründung bei Mischfall oder Unsicherheit |

Bei LLM-only sind `Kx_C2` mit „kein Beleg“ und `mangel`, `F_primaer`, `F_weitere` mit „n. a.“ vorbelegt (K-02).

## 9 Zweitkodierung

Die zweite Person wird vor Beginn anhand dieses Leitfadens eingewiesen (K-08). Sie erhält 48 Entwürfe (24 RAG, 24 LLM-only) mit den Kernaussagen der Erstkodierung (K-06) und kodiert C1, C2, C3, Mangel und Fehlertypen unabhängig, ohne die Codes der Erstkodierung zu sehen. Abweichungen werden nach der Berechnung von Cohens Kappa im Gespräch geklärt; der Konsenswert geht in die Auswertung ein, die ursprünglichen Codes beider Personen bleiben dokumentiert.
