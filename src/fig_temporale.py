"""Figura centrale: l'inversione dell'omofilia femminile, calcolata esattamente.

Tre pannelli impilati, una sola scala per pannello — le tre grandezze hanno
unita' incompatibili e sovrapporle su assi gemelli renderebbe il confronto
illeggibile proprio dove conta.

Il pannello della quota femminile viene PER PRIMO di proposito: e' il controllo
che rende interpretabili gli altri due. Se la quota crescesse, l'aumento
dell'omofilia sarebbe un banale effetto di composizione. Non cresce — scende
dal 15,5% al 9,6% e risale appena — quindi non lo e'.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import viz
from common import ROOT

FIG = ROOT / "report" / "figures"


def main():
    cfg = common.load_config()
    log = common.setup_logging("fig_temporale", cfg)
    viz.setup()
    d = common.load("temporale_esatto.parquet").sort_values("decennio")
    # i primi decenni hanno troppo poche donne perche' il logit sia risolvibile
    d = d[d.decennio >= 1950].copy()
    x = np.arange(len(d))
    et = [f"{int(v)}" for v in d.decennio]
    cF, cM = viz.GENDER_COLOR["F"], viz.GENDER_COLOR["M"]

    fig, axes = plt.subplots(3, 1, figsize=(7.0, 7.8), sharex=True,
                             gridspec_kw={"height_ratios": [0.85, 1.2, 1.2],
                                          "hspace": 0.12})

    # --- 1. la quota femminile, il controllo di composizione ---------------
    a = axes[0]
    a.plot(x, 100 * d.quota_donne, color=cF, lw=2, marker="o", ms=5.5,
           zorder=3, clip_on=False)
    for xi, v in zip(x, 100 * d.quota_donne):
        a.annotate(f"{v:.1f}", (xi, v), textcoords="offset points",
                   xytext=(0, 8), ha="center", fontsize=7.6, color=viz.INK2)
    a.set_ylim(0, 21)
    a.set_ylabel("quota di donne\nfra gli artisti attivi (%)")
    a.set_title("Le donne non sono diventate più numerose",
                loc="left", color=viz.INK)
    viz.tidy(a)

    # --- 2. permutazione a rete fissa: osservato / atteso ------------------
    a = axes[1]
    a.axhline(1.0, color=viz.MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    a.annotate("atteso dal caso", (len(d) - 0.08, 1.0),
               textcoords="offset points", xytext=(0, 5), ha="right",
               fontsize=7.4, color=viz.MUTED)
    for col, c, lab in (("rapporto_F", cF, "fra donne"),
                        ("rapporto_M", cM, "fra uomini")):
        a.plot(x, d[col], color=c, lw=2, marker="o", ms=5.5, label=lab,
               zorder=3, clip_on=False)
    # il segno della z: pieno dove e' significativa, vuoto dove non lo e'
    sig = d.z_F.abs() >= 1.96
    a.scatter(x[~sig.values], d.rapporto_F[~sig.values], s=34, zorder=4,
              facecolor=viz.SURFACE, edgecolor=cF, linewidth=1.6)
    # margine sotto il minimo: senza, i punti del 1950-60 toccano il bordo
    lo = min(d.rapporto_F.min(), d.rapporto_M.min())
    hi = max(d.rapporto_F.max(), d.rapporto_M.max())
    a.set_ylim(lo - 0.10 * (hi - lo), hi + 0.16 * (hi - lo))
    a.set_ylabel("legami interni al genere\nosservati / attesi")
    a.set_title("…ma dagli anni Novanta collaborano fra loro più del caso",
                loc="left", color=viz.INK)
    a.legend(loc="upper left", ncol=2)
    viz.tidy(a)

    # --- 3. logit esatto su tutte le diadi del periodo ---------------------
    a = axes[2]
    a.axhline(0.0, color=viz.MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    for col, se, c, lab in (("coef_same_F", "se_same_F", cF, "fra donne"),
                            ("coef_same_M", "se_same_M", cM, "fra uomini")):
        y, s = d[col].values, d[se].values
        a.fill_between(x, y - 1.96 * s, y + 1.96 * s, color=c, alpha=0.16,
                       lw=0, zorder=2)
        a.plot(x, y, color=c, lw=2, marker="o", ms=5.5, label=lab, zorder=3,
               clip_on=False)
    lo = min((d.coef_same_F - 2 * d.se_same_F).min(),
             (d.coef_same_M - 2 * d.se_same_M).min())
    hi = max((d.coef_same_F + 2 * d.se_same_F).max(),
             (d.coef_same_M + 2 * d.se_same_M).max())
    a.set_ylim(lo - 0.06 * (hi - lo), hi + 0.14 * (hi - lo))
    a.set_ylabel("coefficiente di omofilia\n(logit, a parità di contesto)")
    a.set_title("E l'effetto resta a parità di genere musicale, coorte e attività",
                loc="left", color=viz.INK)
    a.legend(loc="upper left", ncol=2)
    a.set_xticks(x)
    a.set_xticklabels(et)
    a.set_xlabel("decennio di formazione del legame")
    viz.tidy(a)

    viz.caption(fig,
        "Omofilia di genere per decennio di formazione del legame, su tutta la rete. "
        "I legami sono datati con l'anno della prima pubblicazione condivisa. "
        "Pannello centrale: rapporto fra legami interni al genere osservati e attesi "
        "sotto permutazione delle etichette a rete fissa — media e varianza in forma "
        "chiusa, non stimate per simulazione; i cerchi vuoti segnalano gli scarti non "
        "significativi (|z| < 1,96). Pannello inferiore: coefficiente di un logit "
        "diadico calcolato su tutte le diadi del periodo, senza campionamento, con "
        "banda al 95% dall'informazione osservata. Le donne passano da collegarsi fra "
        "loro meno del caso (z = −3,6 negli anni Settanta) a molto più del caso "
        "(z = +8,6 negli anni Venti) mentre la loro quota non cresce: l'aumento non è "
        "un effetto di composizione. Gli uomini non mostrano alcuna tendenza.")

    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "f_omofilia_nel_tempo_esatta.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info(f"prodotta {out}")
    print(out)


if __name__ == "__main__":
    main()
