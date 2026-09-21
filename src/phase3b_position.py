"""FASE 3.4 — posizione nella rete: centralita', coreness, regressione (RQ3).

La domanda "Smurfette" chiede se le donne, dove ci sono, stiano ai margini o al
centro della struttura collaborativa. Si misura su tre assi complementari:
eigenvector (essere legati a chi conta), betweenness (fare da ponte) e coreness
(appartenere al nucleo ddei collaboratori fitti).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer


def giant(G: nx.Graph, log) -> nx.Graph:
    Gs = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    comps = sorted(nx.connected_components(Gs), key=len, reverse=True)
    g = Gs.subgraph(comps[0]).copy()
    log.info(f"componente gigante: {g.number_of_nodes():,} nodi "
             f"({g.number_of_nodes()/max(Gs.number_of_nodes(),1):.1%} dei nodi connessi, "
             f"{g.number_of_nodes()/G.number_of_nodes():.1%} della popolazione); "
             f"esclusi {Gs.number_of_nodes()-g.number_of_nodes():,} nodi in "
             f"{len(comps)-1:,} componenti minori")
    return g


def centralities(G: nx.Graph, cfg, log) -> pd.DataFrame:
    h = cfg["homophily"]
    out = {}
    with Timer("eigenvector", log):
        try:
            out["eigenvector"] = nx.eigenvector_centrality_numpy(G, weight="weight")
        except Exception as e:
            log.warning(f"eigenvector_numpy fallita ({e}); ripiego su power iteration")
            out["eigenvector"] = nx.eigenvector_centrality(G, weight="weight",
                                                           max_iter=1000, tol=1e-6)
    n = G.number_of_nodes()
    with Timer("betweenness", log):
        if n <= h["betweenness_exact_max_n"]:
            out["betweenness"] = nx.betweenness_centrality(G, normalized=True)
            approx = False
        else:
            k = min(h["betweenness_k_sample"], n)
            out["betweenness"] = nx.betweenness_centrality(
                G, k=k, normalized=True, seed=cfg["project"]["seed"])
            approx = True
            log.info(f"betweenness approssimata su k={k:,} sorgenti campionate "
                     f"(rete da {n:,} nodi): la versione esatta richiederebbe "
                     f"{n:,} sorgenti e non e' praticabile")
    with Timer("coreness e grado", log):
        H = nx.Graph(G)
        H.remove_edges_from(nx.selfloop_edges(H))
        out["coreness"] = nx.core_number(H)
        out["degree"] = dict(G.degree())
        out["strength"] = dict(G.degree(weight="weight"))
        out["clustering"] = nx.clustering(G, weight="weight")
    df = pd.DataFrame(out)
    df.index.name = "artist_id"
    df = df.reset_index()
    df["betweenness_approssimata"] = approx
    return df


def regression(df: pd.DataFrame, cfg, log):
    """log(1+eigenvector) ~ gender * genere musicale + log(n_release) + coorte."""
    import statsmodels.formula.api as smf
    d = df[df.gender.isin(["M", "F"]) & (df.musical_genre != "Unknown")
           & df.cohort_decade.notna()].copy()
    # generi musicali troppo piccoli per stimare un'interazione: accorpati
    keep = d.musical_genre.value_counts()
    keep = keep[keep >= 200].index
    d["genere"] = np.where(d.musical_genre.isin(keep), d.musical_genre, "Altro")
    d["y"] = np.log1p(d.eigenvector * 1e6)      # riscalato: l'eigenvector e' ~1e-6
    d["log_nrel"] = np.log(d.n_release.clip(lower=1))
    d["coorte"] = d.cohort_decade.astype(int).astype(str)
    d["gender"] = pd.Categorical(d.gender, categories=["M", "F"])

    res = {}
    for name, formula in [
        ("eigenvector", "y ~ C(gender) * C(genere) + log_nrel + C(coorte)"),
        ("coreness",    "np.log1p(coreness) ~ C(gender) * C(genere) + log_nrel + C(coorte)"),
        ("betweenness", "np.log1p(betweenness*1e6) ~ C(gender) * C(genere) + log_nrel + C(coorte)"),
    ]:
        with Timer(f"OLS {name}", log):
            m = smf.ols(formula, data=d).fit(cov_type="HC3")
        tb = pd.DataFrame({"termine": m.params.index, "coef": m.params.values,
                           "se": m.bse.values, "z": m.tvalues.values,
                           "p": m.pvalues.values,
                           "ci_lo": m.conf_int()[0].values,
                           "ci_hi": m.conf_int()[1].values})
        tb["esito"] = name
        res[name] = tb
        common.save_table(tb, f"t3_regressione_{name}",
                          f"OLS su {name}: posizione nella rete per genere sessuale "
                          f"e genere musicale, a parita' di attivita' e coorte "
                          f"(errori standard robusti HC3, n={int(m.nobs):,}, "
                          f"R2={m.rsquared:.3f})")
        log.info(f"[{name}] n={int(m.nobs):,} R2={m.rsquared:.3f} | "
                 f"effetto principale F: "
                 f"{m.params.get('C(gender)[T.F]', float('nan')):.3f} "
                 f"(p={m.pvalues.get('C(gender)[T.F]', float('nan')):.2g})")
    allres = pd.concat(res.values(), ignore_index=True)
    common.save(allres, "position_regressions.parquet")
    return allres


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase3b_position", cfg)
    if common.exists("position.parquet") and not force:
        log.info("Fase 3.4 gia' completata, salto")
        return
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    G = nx.Graph()
    G.add_nodes_from(pop.artist_id)
    G.add_weighted_edges_from(edges[["u", "v", "w"]].itertuples(index=False, name=None))
    g = giant(G, log)
    cen = centralities(g, cfg, log)
    df = cen.merge(pop, on="artist_id", how="left")
    common.save(df, "position.parquet")

    # sintesi per genere sessuale: la tabella che risponde a RQ3
    d = df[df.gender.isin(["M", "F", "mixed"])]
    summ = d.groupby("gender").agg(
        n=("artist_id", "size"),
        eigenvector_mediana=("eigenvector", "median"),
        eigenvector_media=("eigenvector", "mean"),
        betweenness_mediana=("betweenness", "median"),
        coreness_mediana=("coreness", "median"),
        coreness_media=("coreness", "mean"),
        grado_mediano=("degree", "median"),
        forza_mediana=("strength", "median"),
        n_release_mediana=("n_release", "median")).reset_index()
    common.save_table(summ, "t3_posizione_per_genere",
                      "Posizione nella componente gigante per genere sessuale (RQ3)")
    log.info("\n" + summ.to_string(index=False))

    bg = d[d.musical_genre != "Unknown"].groupby(["musical_genre", "gender"]).agg(
        n=("artist_id", "size"), coreness_mediana=("coreness", "median"),
        eigenvector_mediana=("eigenvector", "median")).reset_index()
    common.save_table(bg, "t3_posizione_per_genere_musicale",
                      "Posizione nella rete per genere sessuale entro genere musicale (RQ3)")
    regression(df, cfg, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
