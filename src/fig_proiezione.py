"""Figura metodologica: perche' un ERGM con gwesp non puo' adattarsi a questa rete.

Due pannelli, due affermazioni distinte che insieme fanno una dimostrazione.

A sinistra il SINTOMO: in ogni decennio in cui l'ERGM converge, la
distribuzione simulata dei partner condivisi sbaglia nello stesso modo — a U.
Il modello sovrastima il centro e sottostima entrambe le code. E' cio' che
accade adattando una distribuzione unimodale, quale gwesp puo' produrre avendo
un solo parametro, a una bimodale.

A destra la CAUSA, misurata arco per arco su tutta la rete: la quota di partner
condivisi che una singola release basta a spiegare. Con max_credits = 8, una
pubblicazione puo' imporne al massimo 8-2 = 6, e fino a quel punto la quota
resta piatta all'80%. Oltre, crolla. La riga verticale non e' una scelta
grafica: e' il tetto aritmetico del meccanismo.

Le due scale sono diverse e restano su pannelli diversi. Quella di sinistra e'
logaritmica perche' rappresenta rapporti, dove 1/5 e 5 sono scarti di pari
entita' in direzioni opposte e una scala lineare darebbe al secondo cinque
volte lo spazio del primo.
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
MODELS = ROOT / "data" / "ergm_decenni"
N_ESP = 13


def main():
    cfg = common.load_config()
    log = common.setup_logging("fig_proiezione", cfg)
    viz.setup()
    maxc = cfg["network"]["max_credits"]
    tetto = maxc - 2

    fig, (a1, a2, a3) = plt.subplots(1, 3, figsize=(13.8, 4.3),
                                     gridspec_kw={"wspace": 0.30})

    # --- A. il sintomo: la U della bonta' di adattamento -------------------
    a1.axhline(1.0, color=viz.MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    decenni = sorted(p.name for p in MODELS.glob("dec*") if (p / "gof.csv").exists())
    for i, d in enumerate(decenni):
        g = pd.read_csv(MODELS / d / "gof.csv")
        g = g[(g.statistica == "esp") & (g.valore <= N_ESP)]
        r = g.obs / g["mean"].replace(0, np.nan)
        a1.plot(g.valore, r, color=viz.CAT[i], lw=2, marker="o", ms=5,
                label=f"{d.replace('dec','')}s", zorder=3)
    a1.set_yscale("log")
    a1.set_yticks([0.25, 0.5, 1, 2, 4, 8, 16, 32, 64])
    a1.set_yticklabels(["¼×", "½×", "1× (atteso)", "2×", "4×", "8×", "16×",
                        "32×", "64×"])
    a1.set_xlabel("partner condivisi dall'arco")
    a1.set_ylabel("archi osservati / archi simulati dal modello")
    a1.set_title("Il sintomo: l'ERGM sbaglia a U", loc="left", color=viz.INK)
    a1.legend(loc="upper left", title="decennio")
    viz.tidy(a1)

    # --- B. la causa: il tetto della proiezione ----------------------------
    d = common.load("proiezione_distribuzione.parquet")
    d = d[(d.esp >= 1) & (d.esp <= 20)]
    colori = [viz.CAT[0] if v <= tetto else viz.MUTED for v in d.esp]
    a2.bar(d.esp, d.quota_spiegata, color=colori, width=0.78,
           edgecolor=viz.SURFACE, linewidth=1.2, zorder=3)
    a2.axvline(tetto + 0.5, color=viz.CAT[3], lw=1.6, zorder=4)
    a2.annotate(f"tetto di una singola release:\n{maxc} accreditati → {tetto} partner",
                (tetto + 0.62, 0.95), fontsize=8, color=viz.INK2,
                va="top", ha="left")
    a2.set_ylim(0, 1.0)
    a2.set_xticks(range(2, 21, 2))
    a2.set_xlabel("partner condivisi dall'arco")
    a2.set_ylabel("quota imposta dalla proiezione bipartita")
    a2.set_title("La causa: sotto il tetto sono meccanici", loc="left",
                 color=viz.INK)
    viz.tidy(a2)

    # --- C. la conferma: il meccanismo da solo riproduce la forma ---------
    n = common.load("proiezione_nulla.parquet")
    a3.axhline(1.0, color=viz.MUTED, lw=1, ls=(0, (4, 3)), zorder=1)
    # l'ERGM, per confronto: e' la curva a U
    ge = pd.read_csv(MODELS / "dec1940" / "gof.csv")
    ge = ge[(ge.statistica == "esp") & (ge.valore <= N_ESP)]
    qo = ge.obs / ge.obs.sum()
    qs = ge["mean"] / ge["mean"].sum()
    a3.plot(ge.valore, qs / qo, color=viz.CAT[7], lw=2.4, marker="s", ms=5,
            label="ERGM stimato (1940s)", zorder=4)
    stili = {"1940s": 0, "1950s": 1, "rete intera": 2}
    for et, i in stili.items():
        g = n[(n.insieme == et) & (n.esp <= N_ESP)]
        if not len(g):
            continue
        tot_o = n[n.insieme == et].osservati.sum()
        tot_b = n[n.insieme == et].randomizzati.sum()
        a3.plot(g.esp, (g.randomizzati / tot_b) / (g.osservati / tot_o),
                color=viz.CAT[i], lw=2 if et == "rete intera" else 1.5,
                marker="o", ms=4.5, label=f"proiezione randomizzata — {et}",
                zorder=3)
    a3.set_yscale("log")
    # spazio in alto per la legenda: sotto, la curva dell'ERGM ci passa dentro
    a3.set_ylim(0.09, 14)
    a3.set_yticks([0.125, 0.25, 0.5, 1, 2, 4])
    a3.set_yticklabels(["⅛×", "¼×", "½×", "1× (osservato)", "2×", "4×"])
    a3.set_xlabel("partner condivisi dall'arco")
    a3.set_ylabel("quota simulata / quota osservata")
    a3.set_title("La conferma: senza parametri, nessuna U", loc="left",
                 color=viz.INK)
    a3.legend(loc="upper left", fontsize=7.4)
    viz.tidy(a3)

    t = common.load("proiezione_tetto.parquet").set_index("gruppo")
    viz.caption(fig,
        "Perché un termine di chiusura triadica è mal posto su una rete ottenuta per "
        "proiezione bipartita. A sinistra: per ogni decennio in cui l'ERGM converge, "
        "rapporto fra il numero di archi con un dato numero di partner condivisi "
        "osservato e quello prodotto da 100 reti simulate dal modello stimato. Lo "
        "scarto ha la stessa forma a U nei due decenni — centro sovrastimato, code "
        "sottostimate — che è ciò che si ottiene adattando una distribuzione "
        "unimodale a una bimodale. A destra: quota dei partner condivisi attribuibile "
        "alla co-presenza in una stessa release, calcolata arco per arco su tutta la "
        "rete (702.613 archi, nessun campionamento). Una release con 8 artisti "
        f"accreditati impone a ogni coppia al suo interno esattamente 6 partner "
        f"condivisi: fino a 6 la quota resta all'80%, oltre crolla. Separando gli archi "
        f"secondo il tetto imposto dalla loro release condivisa più grande, quelli che "
        f"vi rientrano hanno il {t.loc['entro il tetto','quota_spiegata']:.1%} dei "
        f"partner spiegato dalla proiezione, quelli che lo superano il "
        f"{t.loc['oltre il tetto','quota_spiegata']:.1%}. "
        "A destra la verifica del meccanismo: la struttura bipartita viene randomizzata "
        "conservando esattamente entrambe le distribuzioni di grado — quante release per "
        "artista, quanti artisti per release — e riproiettata, cento volte. Nessuna "
        "preferenza sociale vi entra. Il confronto è di forma, ciascun modello contro il "
        "proprio osservato e normalizzato a quote, perché gli insiemi differiscono per "
        "costruzione. Lo scarto medio in log₂ è 1,80 per l'ERGM stimato e 0,30 per la "
        "proiezione randomizzata, che non ha parametri: la U è una proprietà del modello, "
        "non dei dati.")

    FIG.mkdir(parents=True, exist_ok=True)
    out = FIG / "f_proiezione_bipartita.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    log.info(f"prodotta {out}")
    print(out)


if __name__ == "__main__":
    main()
