"""FASE 3f — l'effetto medio dell'essere donna sulla posizione nella rete.

Perche' questa fase esiste
--------------------------
Le regressioni delle Fasi 3b, 3d e 3e stimano
`y ~ C(gender) * C(genere) + log_nrel + C(coorte)`. Con l'interazione, il
coefficiente `C(gender)[T.F]` NON e' un effetto medio: e' l'effetto
dell'essere donna nella categoria di riferimento del genere musicale, che qui
e' "Altro" (i generi musicali minori accorpati, poche centinaia di artisti).
Riportarlo come "effetto dell'essere donna" era un errore.

Il disegno
----------
Per ogni misura di posizione, sullo stesso campione della Fase 3b:
* modello ADDITIVO `y ~ C(gender) + C(genere) + log_nrel + C(coorte)`: il
  coefficiente F e' l'effetto medio entro genere musicale, a parita' di
  attivita' e coorte (errori HC3);
* modello con INTERAZIONI, come prima, solo per il test congiunto di Wald che
  tutte le interazioni F x genere musicale siano nulle: dice se l'effetto
  varia fra generi musicali;
* test di PERMUTAZIONE del coefficiente additivo: gli errori HC3 trattano gli
  artisti come indipendenti, e in una rete non lo sono. Le etichette di genere
  si permutano entro strati di genere musicale x coorte x quintile di
  attivita', con la rete fissa (PERMUTAZIONI repliche, seme del progetto); il
  coefficiente si ricalcola per Frisch-Waugh-Lovell sulle altre covariate.

Misure: coreness, betweenness esatta (Fase 3b), betweenness su 400 sorgenti
(Fase 3d, se sono stati salvati i valori), PageRank e non-backtracking
(Fase 3e), e l'autovettore, riportato solo per documentarne il problema
(localizzato: vedi Fase 3e).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common

PERMUTAZIONI = 2000
ESITI = {
    "coreness": "np.log1p(coreness)",
    "betweenness": "np.log1p(betweenness*1e6)",
    "betweenness_campionata": "np.log1p(betweenness_campionata*1e6)",
    "pagerank": "np.log(pagerank * n_nodi)",
    "nonbacktracking": "np.log1p(nonbacktracking / nb_medio)",
    "eigenvector": "np.log1p(eigenvector*1e6)",
}


def campione(df: pd.DataFrame) -> pd.DataFrame:
    """Stessa selezione e stesse variabili della Fase 3b."""
    d = df[df.gender.isin(["M", "F"]) & (df.musical_genre != "Unknown")
           & df.cohort_decade.notna()].copy()
    keep = d.musical_genre.value_counts()
    keep = keep[keep >= 200].index
    d["genere"] = np.where(d.musical_genre.isin(keep), d.musical_genre, "Altro")
    d["log_nrel"] = np.log(d.n_release.clip(lower=1))
    d["coorte"] = d.cohort_decade.astype(int).astype(str)
    d["gender"] = pd.Categorical(d.gender, categories=["M", "F"])
    return d


def permutazione(d: pd.DataFrame, y: np.ndarray, rng) -> tuple[float, float]:
    """p bilaterale del coefficiente F del modello additivo, permutando F entro strati."""
    import patsy
    Z = patsy.dmatrix("C(genere) + log_nrel + C(coorte)", d, return_type="matrix")
    Q, _ = np.linalg.qr(np.asarray(Z))
    ry = y - Q @ (Q.T @ y)
    f = (d.gender == "F").to_numpy(dtype=float)
    strati = pd.factorize(d.genere.astype(str) + "|" + d.coorte.astype(str) + "|"
                          + pd.qcut(d.log_nrel.rank(method="first"), 5, labels=False).astype(str))[0]
    ordine = np.argsort(strati, kind="stable")

    def coef(fv):
        rf = fv - Q @ (Q.T @ fv)
        return float(rf @ ry / (rf @ rf))

    oss = coef(f)
    sim = np.empty(PERMUTAZIONI)
    for i in range(PERMUTAZIONI):
        perm = np.lexsort((rng.random(len(f)), strati))
        fp = np.empty_like(f)
        fp[ordine] = f[perm]
        sim[i] = coef(fp)
    p = (1 + np.sum(np.abs(sim - sim.mean()) >= abs(oss - sim.mean()))) / (PERMUTAZIONI + 1)
    return oss, float(p)


def main(force: bool = False):
    import statsmodels.formula.api as smf
    cfg = common.load_config()
    log = common.setup_logging("phase3f_posizione_additiva", cfg)
    if common.exists("position_regressions_additiva.parquet") and not force:
        log.info("Fase 3f gia' completata, salto")
        return
    pos = common.load("position.parquet")
    n_nodi = len(pos)
    if common.exists("centralita_alternative.parquet"):
        alt = common.load("centralita_alternative.parquet")[["artist_id", "pagerank", "nonbacktracking"]]
        pos = pos.merge(alt, on="artist_id", how="left")
    if common.exists("betweenness_campionata_valori.parquet"):
        pos = pos.merge(common.load("betweenness_campionata_valori.parquet"), on="artist_id", how="left")
    d = campione(pos)
    d["n_nodi"] = n_nodi
    if "nonbacktracking" in d:
        d["nb_medio"] = pos.nonbacktracking.mean()

    righe = []
    rng = np.random.default_rng(cfg["project"]["seed"])
    t = "C(gender)[T.F]"
    for esito, y in ESITI.items():
        col = esito if esito in d else None
        if col is None or d[col].isna().any():
            log.info(f"{esito}: non disponibile, salto")
            continue
        add = smf.ols(f"{y} ~ C(gender) + C(genere) + log_nrel + C(coorte)", data=d).fit(cov_type="HC3")
        inter = smf.ols(f"{y} ~ C(gender) * C(genere) + log_nrel + C(coorte)", data=d).fit(cov_type="HC3")
        termini = [x for x in inter.params.index if x.startswith(f"{t}:")]
        R = np.zeros((len(termini), len(inter.params)))
        for i, x in enumerate(termini):
            R[i, list(inter.params.index).index(x)] = 1
        w = inter.wald_test(R, scalar=True)
        righe.append({"esito": esito, "n": int(add.nobs), "coef_F": float(add.params[t]),
                      "se": float(add.bse[t]), "ci_lo": float(add.conf_int().loc[t, 0]),
                      "ci_hi": float(add.conf_int().loc[t, 1]), "p": float(add.pvalues[t]),
                      "r2": float(add.rsquared), "interazioni": len(termini),
                      "wald_interazioni_stat": float(w.statistic), "wald_interazioni_p": float(w.pvalue),
                      "coef_F_categoria_riferimento": float(inter.params[t]),
                      "p_categoria_riferimento": float(inter.pvalues[t]),
                      "categoria_riferimento": sorted(d.genere.unique())[0]})
        if esito != "eigenvector":
            yv = np.asarray(add.model.endog, dtype=float)
            _, p_perm = permutazione(d, yv, rng)
            righe[-1]["p_permutazione"] = p_perm
            righe[-1]["permutazioni"] = PERMUTAZIONI
    out = pd.DataFrame(righe)
    log.info("\n" + out[["esito", "coef_F", "ci_lo", "ci_hi", "p", "p_permutazione", "wald_interazioni_p",
                         "coef_F_categoria_riferimento"]].round(4).to_string(index=False))
    common.save(out, "position_regressions_additiva.parquet")
    common.save_table(out, "t3_regressione_additiva",
                      "Effetto medio dell'essere donna sulla posizione nella rete (modello "
                      "additivo, HC3) e test congiunto delle interazioni con il genere musicale")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
