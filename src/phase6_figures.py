"""FASE 6 — figure del report (PNG 300 dpi)."""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common, viz
from common import ROOT, Timer
from viz import CAT, GENDER_COLOR, GENDER_LABEL

FIGS = []


def fig(name):
    def deco(fn):
        FIGS.append((name, fn))
        return fn
    return deco


def _oe(stem):
    p = ROOT / "data" / f"oe_{stem}.npy"
    c = ROOT / "data" / f"cats_{stem}.txt"
    if not p.exists():
        return None, None
    return np.load(p), c.read_text().splitlines()


# ---------------------------------------------------------------- F1 mixing
@fig("f1_mixing_gender_oss_att")
def f_mixing_gender(cfg, log):
    M, cats = _oe("gender")
    if M is None:
        return None
    lab = [GENDER_LABEL.get(c, c) for c in cats]
    fig_, ax = plt.subplots(figsize=(5.6, 4.6))
    L, norm, ticks, ticklab = viz.ratio_scale(M)
    im = ax.imshow(L, cmap=viz.cmap_div, norm=norm)
    ax.set_xticks(range(len(lab)), lab, rotation=30, ha="right")
    ax.set_yticks(range(len(lab)), lab)
    for i in range(len(lab)):
        for j in range(len(lab)):
            if np.isfinite(M[i, j]):
                ax.text(j, i, f"{M[i, j]:.2f}", ha="center", va="center", fontsize=8.5,
                        color="white" if abs(L[i, j]) > 0.62 * norm.vmax else viz.INK)
    cb = fig_.colorbar(im, ax=ax, shrink=0.82, ticks=ticks)
    cb.ax.set_yticklabels(ticklab, fontsize=8)
    cb.set_label("osservato / atteso (scala log)", fontsize=8.5)
    ax.set_title("Chi collabora con chi, rispetto al caso")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return fig_


@fig("f2_mixing_genere_musicale_oss_att")
def f_mixing_genre(cfg, log):
    M, cats = _oe("genere_musicale")
    if M is None:
        return None
    ordv = np.argsort(-np.nan_to_num(M.diagonal()))
    keep = [i for i in ordv if cats[i] != "Unknown"][:12]
    Ms, lab = M[np.ix_(keep, keep)], [cats[i] for i in keep]
    fig_, ax = plt.subplots(figsize=(7.6, 6.2))
    L, norm, ticks, ticklab = viz.ratio_scale(Ms, cap_pct=97.0)
    im = ax.imshow(L, cmap=viz.cmap_div, norm=norm)
    ax.set_xticks(range(len(lab)), lab, rotation=40, ha="right")
    ax.set_yticks(range(len(lab)), lab)
    for i in range(len(lab)):
        for j in range(len(lab)):
            if np.isfinite(Ms[i, j]) and Ms[i, j] >= 1.5:
                ax.text(j, i, f"{Ms[i, j]:.0f}", ha="center", va="center", fontsize=7,
                        color="white" if abs(L[i, j]) > 0.62 * norm.vmax else viz.INK)
    cb = fig_.colorbar(im, ax=ax, shrink=0.82, ticks=ticks)
    cb.ax.set_yticklabels(ticklab, fontsize=8)
    cb.set_label("osservato / atteso (scala log)", fontsize=8.5)
    ax.set_title("Omofilia per genere musicale")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return fig_


# ------------------------------------------------------- F3 quota donne
@fig("f3_quota_donne_per_decennio")
def f_women_decade(cfg, log):
    d = common.load("women_share.parquet")
    tot = d.groupby("cohort_decade").agg(n_donne=("n_donne", "sum"),
                                         n_noti=("n_noti", "sum")).reset_index()
    tot["q"] = tot.n_donne / tot.n_noti
    z = 1.96
    n, p = tot.n_noti, tot.q
    den = 1 + z ** 2 / n
    ctr = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    fig_, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.fill_between(tot.cohort_decade, (ctr - half).clip(0), (ctr + half).clip(0),
                    color=CAT[0], alpha=0.15, lw=0)
    ax.plot(tot.cohort_decade, tot.q, color=CAT[0], marker="o")
    for x, y in zip(tot.cohort_decade, tot.q):
        ax.annotate(f"{y:.1%}", (x, y), textcoords="offset points", xytext=(0, 8),
                    ha="center", fontsize=8, color=viz.INK2)
    ax.axhline(0.5, color=viz.MUTED, ls=":", lw=1)
    ax.annotate("parità", (tot.cohort_decade.max(), 0.5), xytext=(4, 2),
                textcoords="offset points", fontsize=8, color=viz.MUTED, va="bottom")
    ax.set_ylim(0, max(0.55, tot.q.max() * 1.35))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("decennio di debutto")
    ax.set_ylabel("quota di donne")
    ax.set_title("Quota di donne fra gli artisti italiani, per decennio di debutto")
    viz.tidy(ax)
    viz.decade_axis(ax, cfg["cohort"]["decade_floor"])
    return fig_


@fig("f4_quota_donne_genere_x_decennio")
def f_women_facets(cfg, log):
    d = common.load("women_share.parquet")
    big = d.groupby("musical_genre").n_noti.sum().sort_values(ascending=False)
    gens = [g for g in big.index if g != "Unknown"][:8]
    ncol, nrow = 4, 2
    fig_, axes = plt.subplots(nrow, ncol, figsize=(10.5, 5.2), sharex=True, sharey=True)
    for ax, g in zip(axes.ravel(), gens):
        s = d[(d.musical_genre == g) & (d.n_noti >= 15)].sort_values("cohort_decade")
        ax.fill_between(s.cohort_decade, s.ci_lo, s.ci_hi, color=CAT[0], alpha=0.15, lw=0)
        ax.plot(s.cohort_decade, s.quota_donne, color=CAT[0], marker="o", ms=4)
        ax.axhline(0.5, color=viz.MUTED, ls=":", lw=0.8)
        ax.set_title(g, fontsize=9.5)
        viz.tidy(ax)
    for ax in axes.ravel()[len(gens):]:
        ax.set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("decennio")
        viz.decade_axis(ax, cfg["cohort"]["decade_floor"])
    for ax in axes[:, 0]:
        ax.set_ylabel("quota di donne")
    axes[0, 0].yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    axes[0, 0].set_ylim(0, 0.62)
    fig_.suptitle("Quota di donne per genere musicale e decennio di debutto",
                  fontsize=11, fontweight="semibold")
    return fig_


# ------------------------------------------------------- F5 gradi log-log
@fig("f5_distribuzione_gradi")
def f_degree(cfg, log):
    if not common.exists("position.parquet"):
        return None
    d = common.load("position.parquet")
    fig_, axes = plt.subplots(1, 2, figsize=(9.0, 3.6))
    for ax, col, lab in [(axes[0], "degree", "grado (numero di collaboratori)"),
                         (axes[1], "strength", "forza (peso totale dei legami)")]:
        v = d[col][d[col] > 0]
        vals, cnt = np.unique(np.round(v, 3), return_counts=True)
        ax.scatter(vals, cnt / cnt.sum(), s=7, color=CAT[0], alpha=0.55,
                   edgecolors="none")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel(lab)
        ax.set_ylabel("frequenza relativa")
        viz.tidy(ax, "both")
    fig_.suptitle("Distribuzione di grado e forza nella componente gigante "
                  "(scala doppio-logaritmica)", fontsize=11, fontweight="semibold")
    return fig_


# ----------------------------------------------- F6 assortativita' per strato
@fig("f6_assortativita_per_strato")
def f_assort(cfg, log):
    """Mostra la misura di riferimento (soli nodi M/F) accanto a quella a
    quattro categorie: la distanza fra le due e' il peso dell'artefatto di
    copertura dei dati, ed e' il punto metodologico della sezione 5.1."""
    if not common.exists("assortativity_mf.parquet"):
        return None
    d = common.load("assortativity_mf.parquet").copy()
    if "attributo" in d.columns:
        d = d[d.attributo == "gender"]
    if d.empty:
        return None
    d["etichetta"] = d.sottorete + " · " + d.strato
    ordine = [f"{s} · {e}" for s in ["all", "creative", "performance"]
              for e in ["tutto", "pre2000", "post2000"]]
    ordine = [o for o in ordine if o in set(d.etichetta)]
    pos = {o: i for i, o in enumerate(ordine)}
    serie = [("determinati soltanto", CAT[0], "soli nodi con genere determinato"),
             ("tutte le categorie", viz.MUTED, "tutte e quattro le categorie")]
    fig_, ax = plt.subplots(figsize=(7.2, 0.46 * len(ordine) + 2.0))
    off = 0.19
    for k, (cat, col, lab) in enumerate(serie):
        sd = d[d.categorie == cat]
        y = sd.etichetta.map(pos) + (k - 0.5) * 2 * off
        ax.hlines(y, sd.ci_lo, sd.ci_hi, color=col, lw=2.4, alpha=0.8)
        ax.scatter(sd.r, y, color=col, s=38, zorder=3, label=lab)
    nul = d[d.categorie == "determinati soltanto"]
    ax.scatter(nul.r_null, nul.etichetta.map(pos) - off, color=viz.INK,
               s=22, marker="|", zorder=4, label="modello nullo")
    ax.axvline(0, color=viz.MUTED, ls=":", lw=1)
    ax.set_yticks(range(len(ordine)), ordine)
    ax.set_xlabel("assortatività di genere (r di Newman)")
    ax.set_title("Omofilia di genere per sottorete di ruolo ed epoca\n"
                 "punto = osservato, barra = IC 95% bootstrap", fontsize=10)
    ax.legend(loc="upper right", ncol=1, framealpha=0.92, frameon=True,
              edgecolor="none", facecolor=viz.SURFACE)
    viz.tidy(ax, "x")
    ax.invert_yaxis()
    return fig_


@fig("f7_omofilia_per_genere_musicale")
def f_hom_genre(cfg, log):
    if not common.exists("homophily_by_genre.parquet"):
        return None
    d = common.load("homophily_by_genre.parquet").sort_values("r_gender")
    if d.empty:
        return None
    y = np.arange(len(d))
    fig_, axes = plt.subplots(1, 2, figsize=(9.6, 0.42 * len(d) + 1.8),
                              gridspec_kw={"width_ratios": [1.25, 1]})
    ax = axes[0]
    ax.hlines(y, d.ci_lo, d.ci_hi, color=CAT[0], lw=2.4, alpha=0.7)
    ax.scatter(d.r_gender, y, color=CAT[0], s=36, zorder=3)
    ax.scatter(d.r_null, y, color=viz.INK2, s=18, marker="|", zorder=3)
    ax.axvline(0, color=viz.MUTED, ls=":", lw=1)
    ax.set_yticks(y, d.genere_musicale)
    ax.set_xlabel("assortatività di genere (r)")
    ax.set_title("Omofilia entro genere musicale", fontsize=10)
    viz.tidy(ax, "x")
    ax2 = axes[1]
    ax2.scatter(d.oe_MM, y, color=CAT[1], s=36, label="uomo–uomo")
    ax2.scatter(d.oe_FF, y, color=CAT[0], s=36, label="donna–donna")
    ax2.axvline(1, color=viz.MUTED, ls=":", lw=1)
    ax2.set_yticks(y, [""] * len(d))
    ax2.set_xlabel("osservato / atteso sulla diagonale")
    ax2.set_title("Chiusura entro genere sessuale", fontsize=10)
    ax2.legend(loc="upper left", framealpha=0.9, frameon=True,
                edgecolor="none", facecolor=viz.SURFACE)
    viz.tidy(ax2, "x")
    for a in axes:
        a.invert_yaxis()
    return fig_


# ------------------------------------------------------------- F8 posizione
@fig("f8_posizione_per_genere")
def f_position(cfg, log):
    if not common.exists("position.parquet"):
        return None
    d = common.load("position.parquet")
    d = d[d.gender.isin(["F", "M", "mixed"])]
    big = d.musical_genre.value_counts()
    gens = [g for g in big.index if g != "Unknown"][:8]
    s = d[d.musical_genre.isin(gens)]
    agg = s.groupby(["musical_genre", "gender"]).coreness.median().unstack()
    agg = agg.loc[[g for g in gens if g in agg.index]]
    x = np.arange(len(agg))
    wbar = 0.26
    fig_, ax = plt.subplots(figsize=(8.4, 3.8))
    for i, g in enumerate([c for c in ["F", "M", "mixed"] if c in agg.columns]):
        ax.bar(x + (i - 1) * wbar, agg[g], wbar * 0.92, label=GENDER_LABEL[g],
               color=GENDER_COLOR[g], edgecolor=viz.SURFACE, linewidth=1.2)
    ax.set_xticks(x, agg.index, rotation=25, ha="right")
    ax.set_ylabel("coreness mediana")
    ax.set_title("Quanto al centro della rete stanno donne e uomini, per genere musicale",
                 pad=26)
    ax.legend(ncol=3, loc="lower center", bbox_to_anchor=(0.5, 1.005))
    ax.set_ylim(0, agg.max().max() * 1.08)
    viz.tidy(ax)
    return fig_


# ---------------------------------------------------------------- F9 ERGM
@fig("f9_ergm_forest_gender")
def f_ergm(cfg, log):
    if not common.exists("ergm_coef.parquet"):
        return None
    c = common.load("ergm_coef.parquet")
    pref = [m for m in ["M1_con_gwesp", "M0_senza_gwesp"] if m in set(c.model)]
    d = c[c.model.isin(pref[:1]) & c.term.str.contains("nodematch.gender")]
    d = d[d.rete.str.startswith("genere_")].copy()
    if d.empty:
        return None
    d["categoria"] = d.term.str.extract(r"\.([A-Za-z]+)$")[0]
    d["rete_lab"] = d.rete.str.replace("genere_", "", regex=False).str.replace("_", " ")
    d = d[d.categoria.isin(["M", "F"])].sort_values(["rete_lab", "categoria"])
    y = np.arange(len(d))
    fig_, ax = plt.subplots(figsize=(7.0, 0.40 * len(d) + 1.8))
    col = [GENDER_COLOR.get(k, viz.MUTED) for k in d.categoria]
    ax.hlines(y, d.ci_lo, d.ci_hi, color=col, lw=2.4, alpha=0.75)
    ax.scatter(d.estimate, y, color=col, s=36, zorder=3)
    ax.axvline(0, color=viz.MUTED, ls=":", lw=1)
    ax.set_yticks(y, [f"{r} · {GENDER_LABEL.get(k, k)}"
                      for r, k in zip(d.rete_lab, d.categoria)])
    ax.set_xlabel("coefficiente ERGM di omofilia (log-odds)")
    ax.set_title("Omofilia di genere a parità di attività, coorte e chiusura triadica\n"
                 "nei cinque generi musicali più popolosi", fontsize=10)
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([], [], color=GENDER_COLOR[g], marker="o", lw=2.4,
                              ms=7, label=f"omofilia fra {GENDER_LABEL[g]}")
                       for g in ["F", "M"]],
              loc="lower right", framealpha=0.92, frameon=True,
              edgecolor="none", facecolor=viz.SURFACE)
    viz.tidy(ax, "x")
    ax.invert_yaxis()
    return fig_


# --------------------------------------------------------- F10 robustezza
@fig("f10_montecarlo_genere")
def f_mc(cfg, log):
    if not common.exists("mc_gender.parquet"):
        return None
    d = common.load("mc_gender.parquet")
    sq = d[d.scenario == "status_quo"].r
    if sq.empty:
        return None
    fig_, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.hist(sq, bins=30, color=CAT[0], alpha=0.8, edgecolor=viz.SURFACE, lw=0.6,
            label=f"imputazione casuale dalla marginale ({len(sq)} repliche)")
    righe = [("solo_noti", viz.INK, "-", "solo artisti con genere noto"),
             ("migliore_omofilia_min", CAT[2], "--", "limite inferiore (omofilia minima)"),
             ("peggiore_omofilia_max", CAT[7], "--", "limite superiore (omofilia massima)")]
    for scen, c, ls, lab in righe:
        v = d[d.scenario == scen].r
        if len(v):
            ax.axvline(v.iloc[0], color=c, lw=2.0, ls=ls,
                       label=f"{lab} — r = {v.iloc[0]:.4f}".replace(".", ","))
    ax.set_xlabel("assortatività di genere (r)")
    ax.set_ylabel("repliche Monte Carlo")
    ax.set_title("Quanto l'omofilia dipende da ciò che non sappiamo")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=1,
              fontsize=8, handlelength=1.8)
    viz.tidy(ax)
    return fig_


@fig("f11_sensibilita")
def f_sens(cfg, log):
    if not common.exists("sensitivity.parquet"):
        return None
    d = common.load("sensitivity.parquet").copy()
    coppie = [("r_gender_MF", "non pesata, soli nodi M/F\n(misura di riferimento)"),
              ("r_gender_pesato", "pesata per specificità del credito")]
    coppie = [(c, t) for c, t in coppie if c in d.columns]
    if not coppie:
        return None
    base = d[d.variante == "default"]
    d = d[d.variante != "default"].sort_values(coppie[0][0])
    y = np.arange(len(d))
    fig_, axes = plt.subplots(1, len(coppie), figsize=(4.9 * len(coppie), 0.40 * len(d) + 2.2),
                              sharey=True)
    axes = np.atleast_1d(axes)
    for ax, (col, titolo) in zip(axes, coppie):
        b = float(base[col].iloc[0])
        ax.scatter(d[col], y, color=CAT[0], s=40, zorder=3)
        ax.axvline(b, color=CAT[1], lw=1.8, ls="--", zorder=2)
        ax.annotate(f"default {b:.3f}".replace(".", ","), (b, -0.9),
                    ha="center", va="top", fontsize=8, color=CAT[1],
                    annotation_clip=False)
        ax.set_title(titolo, fontsize=9.5)
        ax.set_xlabel("assortatività di genere (r)")
        viz.tidy(ax, "x")
    axes[0].set_yticks(y, d.variante)
    axes[0].set_ylim(-1.8, len(d) - 0.4)
    fig_.suptitle("Sensibilità dell'omofilia ai parametri di costruzione della rete",
                  fontsize=11, fontweight="semibold")
    return fig_


@fig("f12_ergm_gof")
def f_gof(cfg, log):
    """Bontà di adattamento: statistiche osservate contro quelle simulate dal
    modello. Le tabelle di `gof` elencano tutti i valori possibili fino al
    numero di nodi, ma la massa sta nei primi: la coda di zeri va troncata,
    altrimenti il grafico e' una riga verticale."""
    import glob
    files = sorted(glob.glob(str(ROOT / "data" / "ergm" / "*" / "gof.csv")))
    if not files:
        return None
    reti = []
    for f in files[:3]:
        d = pd.read_csv(f)
        if not d.empty:
            reti.append((Path(f).parent.name.replace("genere_", "")
                         .replace("epoca_", "").replace("_", " "), d))
    if not reti:
        return None
    stats = [("grado", "distribuzione dei gradi", "numero di collaboratori"),
             ("esp", "partner condivisi (ESP)", "partner in comune"),
             ("distanza", "distanze geodetiche", "distanza")]
    fig_, axes = plt.subplots(len(reti), len(stats),
                              figsize=(3.7 * len(stats), 2.8 * len(reti)),
                              squeeze=False)
    for i, (nome, d) in enumerate(reti):
        for j, (st, titolo, xlab) in enumerate(stats):
            ax = axes[i][j]
            sd = d[d.statistica == st].copy()
            if sd.empty:
                ax.set_visible(False)
                continue
            # la riga "inf" delle distanze (coppie non connesse) ha una massa
            # enorme e schiaccerebbe l'asse: si toglie e si annota a parte
            n_inf = None
            if st == "distanza":
                m_inf = sd.valore.astype(str).str.lower().str.contains("inf")
                if m_inf.any():
                    n_inf = int(sd.loc[m_inf, "obs"].iloc[0])
                    sd = sd[~m_inf]
            # si tiene fino all'ultimo valore con massa, piu' un margine
            vivo = sd[(sd.obs > 0) | (sd["mean"] > 0.5)]
            ultimo = int(vivo.index.max() - sd.index.min()) if len(vivo) else 10
            sd = sd.iloc[:min(ultimo + 3, len(sd))]
            x = np.arange(len(sd))
            ax.fill_between(x, sd["min"], sd["max"], color=CAT[0], alpha=0.20,
                            lw=0, label="simulato (min–max)")
            ax.plot(x, sd["mean"], color=CAT[0], lw=1.6, label="simulato (media)")
            fuori = (sd.obs < sd["min"]) | (sd.obs > sd["max"])
            ax.plot(x, sd.obs, color=viz.INK, lw=0, marker="o", ms=4,
                    label="osservato")
            if fuori.any():
                ax.plot(x[fuori.values], sd.obs[fuori.values], lw=0, marker="o",
                        ms=6, mfc="none", mec=CAT[7], mew=1.4,
                        label="fuori dalla banda")
            ax.set_xticks(x[::max(1, len(x) // 6)],
                          sd.valore.astype(str).values[::max(1, len(x) // 6)],
                          fontsize=7.5)
            if i == 0:
                ax.set_title(titolo, fontsize=9.5)
            if i == len(reti) - 1:
                ax.set_xlabel(xlab, fontsize=8.5)
            if j == 0:
                ax.set_ylabel(nome, fontsize=9)
            if n_inf:
                ax.annotate(f"coppie non connesse: {n_inf:,}".replace(",", "."),
                            (0.98, 0.94), xycoords="axes fraction", ha="right",
                            fontsize=7, color=viz.MUTED)
            viz.tidy(ax)
    axes[0][-1].legend(fontsize=7, loc="upper right")
    fig_.suptitle("Bontà di adattamento degli ERGM", fontsize=11,
                  fontweight="semibold")
    return fig_


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase6_figures", cfg)
    viz.setup()
    made = []
    for name, fn in FIGS:
        try:
            with Timer(f"figura {name}", log):
                f = fn(cfg, log)
            if f is None:
                log.warning(f"{name}: dati assenti, saltata")
                continue
            p = common.savefig(f, name, cfg)
            made.append(name)
            log.info(f"  -> {p}")
        except Exception as e:
            log.error(f"{name}: errore {e!r}")
    common.write_json({"figure": made}, "figures_made.json")
    log.info(f"figure prodotte: {len(made)}/{len(FIGS)}")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
