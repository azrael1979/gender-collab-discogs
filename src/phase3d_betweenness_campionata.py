"""FASE 3d — che cosa costerebbe approssimare la betweenness, su questa rete.

La Fase 3b calcola la betweenness ESATTA, da tutte le sorgenti. L'articolo
mostra che cosa si perderebbe con l'approssimazione usuale — k sorgenti
campionate — e il confronto ha senso solo sulla STESSA rete. La prima volta il
valore campionato era rimasto quello della rete con i gruppi, e dopo la loro
esclusione (D16) non era piu' confrontabile.

Qui si ricalcola la betweenness su `homophily.betweenness_k_sample` sorgenti
(networkx, seme del progetto) sulla componente gigante della Fase 3b, e si
stima la stessa OLS della 3b per il solo esito betweenness. Non si tocca nulla
della 3b: il risultato va in `betweenness_campionata.parquet`.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import Timer


def main(force: bool = False):
    import statsmodels.formula.api as smf
    cfg = common.load_config()
    log = common.setup_logging("phase3d_betweenness_campionata", cfg)
    if common.exists("betweenness_campionata.parquet") and not force:
        log.info("Fase 3d gia' completata, salto")
        return
    pos = common.load("position.parquet")
    edges = common.load("edges_all.parquet")
    nodi = set(pos.artist_id)
    e = edges[edges.u.isin(nodi) & edges.v.isin(nodi)]
    G = nx.Graph()
    G.add_nodes_from(nodi)
    G.add_edges_from(e[["u", "v"]].itertuples(index=False, name=None))
    k = int(cfg["homophily"]["betweenness_k_sample"])
    log.info(f"componente gigante: {G.number_of_nodes():,} nodi, "
             f"{G.number_of_edges():,} archi; sorgenti campionate: {k}")
    with Timer(f"betweenness su {k} sorgenti", log):
        b = nx.betweenness_centrality(G, k=k, normalized=True,
                                      seed=cfg["project"]["seed"])
    pos = pos.copy()
    pos["betweenness"] = pos.artist_id.map(b)

    # stessa preparazione e stessa formula della Fase 3b
    d = pos[pos.gender.isin(["M", "F"]) & (pos.musical_genre != "Unknown")
            & pos.cohort_decade.notna()].copy()
    keep = d.musical_genre.value_counts()
    keep = keep[keep >= 200].index
    d["genere"] = np.where(d.musical_genre.isin(keep), d.musical_genre, "Altro")
    d["log_nrel"] = np.log(d.n_release.clip(lower=1))
    d["coorte"] = d.cohort_decade.astype(int).astype(str)
    d["gender"] = pd.Categorical(d.gender, categories=["M", "F"])
    m = smf.ols("np.log1p(betweenness*1e6) ~ C(gender) * C(genere) + log_nrel "
                "+ C(coorte)", data=d).fit(cov_type="HC3")
    t = "C(gender)[T.F]"
    out = pd.DataFrame([{"sorgenti": k, "coef": float(m.params[t]),
                         "se": float(m.bse[t]), "p": float(m.pvalues[t]),
                         "n": int(m.nobs)}])
    log.info("\n" + out.round(4).to_string(index=False))
    esatta = common.load("position_regressions.parquet")
    esatta = esatta[(esatta.esito == "betweenness") & (esatta.termine == t)].iloc[0]
    log.info(f"esatta: {esatta.coef:.4f} (p={esatta.p:.3f})")
    common.save(out, "betweenness_campionata.parquet")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
