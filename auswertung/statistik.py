"""Gemeinsame statistische Verfahren und Formatierung für die Auswertung (DEMI 3.6, Tabelle 15).

Alle Tests zweiseitig mit α = 0,05 (DEMI 1.4.5). Entscheidungen zu den Verfahren: auswertung/README.md (AW-04 ff.).
"""

import math
import random
from collections import Counter

FARBE = {"rag": "#2a78d6", "llm": "#eb6834"}          # wie Strang 1 (Kategorialpalette, Slots 1 und 2)
NAME = {"rag": "RAG", "llm": "LLM-only"}
TEXT, TEXT2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
ORDINAL = ["#86b6ef", "#3987e5", "#1c5cab"]           # Sequenzrampe Blau, Stufen 250/400/550 (niedrig → hoch)
ORDINAL4 = ["#86b6ef", "#3987e5", "#1c5cab", "#0d366b"]  # Stufen 250/400/550/700
GRAU = "#c3c2b7"
KORREKTHEIT = ["falsch", "teilweise", "korrekt"]
KORREKT_WERT = {k: i for i, k in enumerate(KORREKTHEIT)}


# --------------------------------------------------------------------------- Formatierung

def de(x, nd=2) -> str:
    """Zahl im deutschen Format mit typografischem Minus."""
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "–"
    return f"{x:,.{nd}f}".replace(",", "§").replace(".", ",").replace("§", ".").replace("-", "−")


def p_fmt(p: float) -> str:
    """p-Wert nach üblicher Konvention: drei Nachkommastellen, kleine Werte als < 0,001."""
    return "< 0,001" if p < 0.001 else de(p, 3)


def p_text(p: float) -> str:
    """„p < 0,001“ oder „p = 0,023“."""
    return "p < 0,001" if p < 0.001 else f"p = {de(p, 3)}"


def pct(a: int, b: int, nd=1) -> str:
    return f"{de(100 * a / b, nd)} %" if b else "–"


def quartile(werte: list) -> tuple:
    """Median, Q1, Q3 (Methode „inclusive“, wie in strang1.py)."""
    import statistics
    v = sorted(werte)
    if len(v) == 1:
        return v[0], v[0], v[0]
    q = statistics.quantiles(v, n=4, method="inclusive")
    return q[1], q[0], q[2]


def mdn_iqr(werte: list, nd=2) -> str:
    if not werte:
        return "–"
    m, q1, q3 = quartile(werte)
    return f"{de(m, nd)} ({de(q1, nd)}–{de(q3, nd)})"


# --------------------------------------------------------------------------- Wilcoxon-Vorzeichen-Rang-Test

def _raenge(werte: list) -> list:
    """Mittlere Ränge (1-basiert) bei Bindungen."""
    order = sorted(range(len(werte)), key=lambda i: werte[i])
    r = [0.0] * len(werte)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and werte[order[j + 1]] == werte[order[i]]:
            j += 1
        mittel = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = mittel
        i = j + 1
    return r


def wilcoxon(x: list, y: list) -> dict:
    """Wilcoxon-Vorzeichen-Rang-Test für Paare (x − y), exakt auch bei Bindungen.

    Nulldifferenzen werden ausgeschlossen (Wilcoxon-Verfahren). Die exakte Verteilung von T+ unter H0 wird bedingt auf
    die beobachteten (mittleren) Ränge über alle 2^n Vorzeichenkombinationen berechnet (dynamische Programmierung über
    die verdoppelten Ränge). p zweiseitig: P(|T+ − E| ≥ |t − E|).
    z: Normalapproximation mit Bindungskorrektur, ohne Stetigkeitskorrektur; r = |z| / √N mit N = Anzahl aller Paare.
    """
    d = [a - b for a, b in zip(x, y)]
    nz = [v for v in d if abs(v) > 1e-12]
    n_paare, n = len(d), len(nz)
    res = {"n_paare": n_paare, "n_ungleich": n, "n_pos": sum(v > 0 for v in nz), "n_neg": sum(v < 0 for v in nz),
           "median_diff": quartile(d)[0] if d else None}
    if n == 0:
        res.update({"t_plus": 0.0, "p": 1.0, "z": 0.0, "r": 0.0})
        return res
    r = _raenge([abs(v) for v in nz])
    t_plus = sum(rk for rk, v in zip(r, nz) if v > 0)
    gewichte = [int(round(2 * rk)) for rk in r]
    total = sum(gewichte)
    verteilung = [0] * (total + 1)            # Anzahl der Vorzeichenkombinationen je Summe (verdoppelt)
    verteilung[0] = 1
    for w in gewichte:
        for s in range(total, w - 1, -1):
            verteilung[s] += verteilung[s - w]
    gesamt = 2 ** n
    erwartung2 = total / 2                    # E(2·T+)
    beob = abs(2 * t_plus - erwartung2)
    p = sum(c for s, c in enumerate(verteilung) if abs(s - erwartung2) >= beob - 1e-9) / gesamt
    bind = sum(t ** 3 - t for t in Counter(r).values())
    var = n * (n + 1) * (2 * n + 1) / 24 - bind / 48
    z = (t_plus - n * (n + 1) / 4) / math.sqrt(var) if var > 0 else 0.0
    res.update({"t_plus": t_plus, "t_minus": n * (n + 1) / 2 - t_plus, "p": min(1.0, p), "z": z,
                "r": abs(z) / math.sqrt(n_paare)})
    return res


def r_stufe(r: float) -> str:
    """Einordnung nach Cohen (1988): 0,1 klein, 0,3 mittel, 0,5 groß."""
    r = abs(r)
    return "groß" if r >= 0.5 else "mittel" if r >= 0.3 else "klein" if r >= 0.1 else "unter klein"


# --------------------------------------------------------------------------- weitere Tests

def stuart_maxwell(tabelle: list) -> dict:
    """Test auf marginale Homogenität nach Stuart und Maxwell (statsmodels)."""
    import numpy as np
    from statsmodels.stats.contingency_tables import SquareTable
    res = SquareTable(np.array(tabelle, dtype=float), shift_zeros=False).homogeneity(method="stuart_maxwell")
    return {"chi2": float(res.statistic), "df": int(res.df), "p": float(res.pvalue)}


def mcnemar_exakt(b: int, c: int) -> dict:
    """Exakter McNemar-Test (Binomialtest auf die diskordanten Paare) und Odds Ratio b/c für gepaarte Daten.

    b: Bedingung 1 ja, Bedingung 2 nein; c: umgekehrt. KI exakt über das Clopper-Pearson-Intervall für b/(b+c).
    """
    from scipy.stats import beta, binomtest
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p": 1.0, "or": None, "ci": (None, None)}
    p = binomtest(b, n, 0.5).pvalue
    lo = beta.ppf(0.025, b, c + 1) if b > 0 else 0.0
    hi = beta.ppf(0.975, b + 1, c) if c > 0 else 1.0
    odds = (b / c) if c > 0 else math.inf
    lo, hi = float(lo), float(hi)
    return {"b": b, "c": c, "p": float(p), "or": odds,
            "ci": (lo / (1 - lo) if lo < 1 else math.inf, hi / (1 - hi) if hi < 1 else math.inf)}


def gleichverteilung(counts: list) -> dict:
    """Chi-Quadrat-Anpassungstest gegen Gleichverteilung und exakter Multinomialtest (Summe der Wahrscheinlichkeiten
    aller Ergebnisse, die höchstens so wahrscheinlich sind wie das beobachtete)."""
    from scipy.stats import chisquare
    k, n = len(counts), sum(counts)
    chi = chisquare(counts)
    erwartet = n / k

    def kompositionen(rest, teile):
        if teile == 1:
            yield (rest,)
            return
        for i in range(rest + 1):
            for t in kompositionen(rest - i, teile - 1):
                yield (i,) + t

    def prob(c):
        return math.factorial(n) / math.prod(math.factorial(x) for x in c) / k ** n

    p_obs = prob(counts)
    p_exakt = sum(prob(c) for c in kompositionen(n, k) if prob(c) <= p_obs * (1 + 1e-9))
    return {"n": n, "chi2": float(chi.statistic), "df": k - 1, "p_chi2": float(chi.pvalue), "erwartet": erwartet,
            "p_exakt": min(1.0, p_exakt)}


def spearman(x: list, y: list, seed: str, b: int = 10000) -> dict:
    """Spearmans ρ mit p-Wert (scipy) und 95-%-Bootstrap-Perzentilintervall (Paare gezogen, fester Seed)."""
    from scipy.stats import spearmanr
    res = spearmanr(x, y)
    rng = random.Random(seed)
    n, werte = len(x), []
    for _ in range(b):
        idx = [rng.randrange(n) for _ in range(n)]
        xs, ys = [x[i] for i in idx], [y[i] for i in idx]
        if len(set(xs)) > 1 and len(set(ys)) > 1:
            werte.append(spearmanr(xs, ys).statistic)
    werte.sort()
    return {"n": n, "rho": float(res.statistic), "p": float(res.pvalue),
            "ci": (werte[int(0.025 * len(werte))], werte[int(0.975 * len(werte)) - 1])}


def mann_whitney(x: list, y: list) -> dict:
    """Mann-Whitney-U-Test (zweiseitig, scipy) mit z (Bindungskorrektur) und r = |z| / √N."""
    from scipy.stats import mannwhitneyu
    res = mannwhitneyu(x, y, alternative="two-sided")
    n1, n2 = len(x), len(y)
    big_n = n1 + n2
    raenge = _raenge(list(x) + list(y))
    u1 = sum(raenge[:n1]) - n1 * (n1 + 1) / 2
    bind = sum(t ** 3 - t for t in Counter(raenge).values())
    sigma = math.sqrt(n1 * n2 / 12 * ((big_n + 1) - bind / (big_n * (big_n - 1))))
    z = (u1 - n1 * n2 / 2) / sigma if sigma > 0 else 0.0
    return {"n1": n1, "n2": n2, "u": float(u1), "p": float(res.pvalue), "z": z, "r": abs(z) / math.sqrt(big_n)}


def cohen_kappa(paare: list, kategorien: list) -> dict:
    n = len(paare)
    po = sum(a == b for a, b in paare) / n
    ca, cb = Counter(a for a, _ in paare), Counter(b for _, b in paare)
    pe = sum(ca[k] * cb[k] for k in kategorien) / n ** 2
    return {"n": n, "po": po, "kappa": (po - pe) / (1 - pe) if pe < 1 else None}


def icc_gemischt(daten: list, wert: str, ziel: str, person: str) -> dict:
    """ICC(2,1) und ICC(2,3) nach dem Zwei-Weg-Zufallsmodell mit absoluter Übereinstimmung (McGraw & Wong, 1996).

    Varianzkomponenten aus einem linearen gemischten Modell mit gekreuzten Zufallseffekten für Antwortentwurf und
    bewertende Person (REML, statsmodels), weil das Blockdesign nicht vollständig gekreuzt ist (DEMI 2.4):
    ICC(2,1) = σ²_Entwurf / (σ²_Entwurf + σ²_Person + σ²_Rest); ICC(2,k) = σ²_Entwurf / (σ²_Entwurf + (σ²_Person + σ²_Rest) / k).
    """
    import warnings

    import pandas as pd
    import statsmodels.formula.api as smf
    df = pd.DataFrame(daten)
    df["_g"] = 1
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = smf.mixedlm(f"{wert} ~ 1", df, groups="_g", re_formula="0",
                            vc_formula={"ziel": f"0 + C({ziel})", "person": f"0 + C({person})"})
        fit = model.fit(reml=True, method=["lbfgs", "powell"])
    vc = dict(zip(model.exog_vc.names, fit.vcomp))
    s_z, s_p, s_e = vc["ziel"], vc["person"], fit.scale
    icc1 = s_z / (s_z + s_p + s_e)
    icc3 = s_z / (s_z + (s_p + s_e) / 3)
    return {"var_entwurf": float(s_z), "var_person": float(s_p), "var_rest": float(s_e), "icc_2_1": float(icc1),
            "icc_2_3": float(icc3),
            "konvergiert": bool(fit.converged)}


def icc_stufe(icc: float) -> str:
    """Einordnung nach Koo und Li (2016): < 0,5 gering, 0,5–0,75 mäßig, 0,75–0,9 gut, > 0,9 sehr gut."""
    return "sehr gut" if icc > 0.9 else "gut" if icc >= 0.75 else "mäßig" if icc >= 0.5 else "gering"
