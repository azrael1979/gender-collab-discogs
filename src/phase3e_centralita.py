"""FASE 3e — centralita' che non si localizzano (DV6).

Perche' questa fase esiste
--------------------------
L'autovettore della Fase 3b, sulla componente gigante di queste reti, si
LOCALIZZA: supera 1e-4 solo per il 2-4% dei nodi ed e' praticamente zero
altrove. Un autovettore localizzato misura l'appartenenza a un unico nucleo
denso, non la centralita' (Martin, Zhang e Newman 2014, Phys. Rev. E 90,
052808). Nel campo nordico la sua regressione dava un effetto donne di +1,49
con tutte le interazioni significative: un artefatto.

Il disegno (registrato in DV6 prima di eseguire)
------------------------------------------------
Stessa componente gigante della Fase 3b (tutti gli artisti, archi pesati),
stesso campione e stesso modello di regressione, con due misure al posto
dell'autovettore:

1. PageRank pesato, smorzamento 0,85 — sostituto principale: il salto casuale
   impedisce la localizzazione. Esito: log(PageRank * n).
2. Centralita' non-backtracking (Martin, Zhang e Newman 2014), non pesata:
   autovettore principale della matrice ridotta 2n x 2n [[A, I-D], [I, 0]];
   le prime n componenti sono la centralita'. Esito: log(1 + x / media(x)).

Per ogni misura, autovettore compreso, si riporta il rapporto di
partecipazione inverso (IPR = somma x^4 su vettore di norma 1): vale circa 1/n
se il peso e' distribuito, e cresce fino a 1/k se si concentra su k nodi.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
import scipy.sparse as sp
from scipy.sparse.linalg import eigs

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import Timer
from phase3b_position import giant

SMORZAMENTO = 0.85


def ipr(x: np.ndarray) -> float:
    x = np.abs(np.asarray(x, dtype=float))
    x = x / np.linalg.norm(x)
    return float((x ** 4).sum())


def non_backtracking(G: nx.Graph, nodi: list) -> np.ndarray:
    A = nx.to_scipy_sparse_array(G, nodelist=nodi, weight=None, format="csr").astype(float)
    A = A - sp.diags(A.diagonal())         # senza anelli
    A.eliminate_zeros()
    n = A.shape[0]
    d = np.asarray(A.sum(axis=1)).ravel()
    I = sp.identity(n, format="csr")
    M = sp.bmat([[A, I - sp.diags(d)], [I, None]], format="csr")
    val, vec = eigs(M, k=1, which="LR", tol=1e-10, maxiter=100000)
    x = np.real(vec[:n, 0])
    x = x if x.sum() >= 0 else -x
    return np.clip(x, 0, None), float(np.real(val[0]))


def regressione(d: pd.DataFrame, esito: str, y: str, log) -> pd.DataFrame:
    """Stesso modello della Fase 3b, con errori HC3."""
    import statsmodels.formula.api as smf
    m = smf.ols(f"{y} ~ C(gender) * C(genere) + log_nrel + C(coorte)", data=d).fit(cov_type="HC3")
    tb = pd.DataFrame({"termine": m.params.index, "coef": m.params.values,
                       "se": m.bse.values, "z": m.tvalues.values, "p": m.pvalues.values,
                       "ci_lo": m.conf_int()[0].values, "ci_hi": m.conf_int()[1].values})
    tb["esito"] = esito
    log.info(f"[{esito}] n={int(m.nobs):,} R2={m.rsquared:.3f}")
    return tb


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase3e_centralita", cfg)
    if common.exists("position_regressions_alt.parquet") and not force:
        log.info("Fase 3e gia' completata, salto")
        return
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    G = nx.Graph()
    G.add_nodes_from(pop.artist_id)
    G.add_weighted_edges_from(edges[["u", "v", "w"]].itertuples(index=False, name=None))
    g = giant(G, log)
    nodi = list(g.nodes())
    n = len(nodi)

    with Timer("PageRank", log):
        pr = nx.pagerank(g, alpha=SMORZAMENTO, weight="weight", tol=1e-10, max_iter=1000)
    with Timer("non-backtracking", log):
        nb, lam = non_backtracking(g, nodi)
    log.info(f"autovalore principale non-backtracking: {lam:.3f}")

    pos = common.load("position.parquet").set_index("artist_id")
    cen = pd.DataFrame({"artist_id": nodi, "pagerank": [pr[a] for a in nodi],
                        "nonbacktracking": nb})
    cen["eigenvector"] = pos.eigenvector.reindex(cen.artist_id).values
    if cen.eigenvector.isna().any():
        log.warning("la componente gigante non coincide con quella della Fase 3b")
    common.save(cen, "centralita_alternative.parquet")

    loc = []
    for c in ["eigenvector", "pagerank", "nonbacktracking"]:
        x = cen[c].fillna(0).values
        v = ipr(x)
        loc.append({"misura": c, "nodi": n, "ipr": v, "ipr_per_n": v * n,
                    "nodi_efficaci": 1 / v, "quota_nodi_efficaci": 1 / v / n,
                    "quota_sopra_1e-4_del_max": float((np.abs(x) > 1e-4 * np.abs(x).max()).mean())})
    loc = pd.DataFrame(loc)
    log.info("\n" + loc.round(5).to_string(index=False))
    common.save(loc, "localizzazione.parquet")

    # stesso campione della Fase 3b
    d = cen.merge(pop, on="artist_id", how="left")
    d = d[d.gender.isin(["M", "F"]) & (d.musical_genre != "Unknown")
          & d.cohort_decade.notna()].copy()
    keep = d.musical_genre.value_counts()
    keep = keep[keep >= 200].index
    d["genere"] = np.where(d.musical_genre.isin(keep), d.musical_genre, "Altro")
    d["log_nrel"] = np.log(d.n_release.clip(lower=1))
    d["coorte"] = d.cohort_decade.astype(int).astype(str)
    d["gender"] = pd.Categorical(d.gender, categories=["M", "F"])
    d["y_pr"] = np.log(d.pagerank * n)
    d["y_nb"] = np.log1p(d.nonbacktracking / cen.nonbacktracking.mean())
    out = pd.concat([regressione(d, "pagerank", "y_pr", log),
                     regressione(d, "nonbacktracking", "y_nb", log)], ignore_index=True)
    common.save(out, "position_regressions_alt.parquet")
    f = out[out.termine == "C(gender)[T.F]"][["esito", "coef", "p"]]
    log.info("effetto principale F:\n" + f.round(4).to_string(index=False))


if __name__ == "__main__":
    main(force="--force" in sys.argv)
