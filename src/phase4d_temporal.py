"""FASE 4d — come cambia l'omofilia nel tempo, sulla rete integrale.

Datare il legame, non le persone
--------------------------------
Nelle analisi precedenti l'epoca era definita sulla coorte di debutto degli
artisti: un arco era "pre-2000" se entrambi gli estremi avevano debuttato prima
del 2000. E' una definizione scomoda. Un legame nato nel 1975 fra un artista
esordiente e uno in attivita' da vent'anni e' un legame del 1975, non di due
epoche diverse; e la regola che pretende l'accordo di entrambi gli estremi
scarta proprio le collaborazioni intergenerazionali, che sono fra le piu'
interessanti.

Qui ogni arco viene datato con **l'anno della prima pubblicazione condivisa**
dai due artisti: il momento in cui la collaborazione compare per la prima volta
nei dati. E' l'anno di formazione del legame, che e' il concetto giusto per
chiedersi come l'omofilia cambi nel tempo.

Due misure per periodo
----------------------
* **QAP**: si permutano le etichette di genere sui nodi attivi nel periodo,
  tenendo fissa la rete di quel periodo. Poiche' la permutazione avviene dentro
  la composizione realmente osservata in quegli anni, il confronto e'
  automaticamente corretto per il fatto che la quota di donne cambia nel tempo
  — che e' l'insidia principale di qualunque confronto temporale su questo
  tema.
* **Logit diadico**: la stessa stima condizionale della Fase 4c, ripetuta per
  periodo, che dice quanto resta dell'omofilia a parita' di genere musicale,
  coorte e attivita'.

Le due rispondono a domande diverse — se le donne siano aggregate o disperse in
assoluto, e se lo siano a parita' di contesto — e nella Fase 4c danno risposte
di segno opposto. Vedere come ciascuna evolve e' piu' informativo che vederne
una sola.
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

RAW = ROOT / "data" / "raw"
PERMUTAZIONI = 1000
MIN_ARCHI = 2000          # sotto questa soglia il periodo non e' stimabile
CONTROLLI_PER_CASO = 5


def archi_datati(cfg, log) -> pd.DataFrame:
    """Un arco per coppia di artisti, con l'anno della prima collaborazione."""
    credits = common.load("credits.parquet")
    rel = pd.read_parquet(RAW / "raw_releases.parquet")[["release_id", "year"]]
    size = pd.read_parquet(RAW / "raw_relsize.parquet")
    st = RAW / "raw_relsize_track.parquet"
    if st.exists():
        size = pd.concat([size, pd.read_parquet(st)], ignore_index=True) \
                 .drop_duplicates("release_id")
    pop = common.load("population_gender.parquet")
    ids = set(pop[pop.gender.isin(["M", "F", "mixed"])].artist_id)

    c = credits[["artist_id", "release_id"]].drop_duplicates()
    c = c[c.artist_id.isin(ids)]
    c = c.merge(rel, on="release_id").merge(size[["release_id", "n_credited"]],
                                            on="release_id", how="left")
    c = c[c.year.between(cfg["cohort"]["min_year"], cfg["cohort"]["max_year"])]
    # stesso filtro della Fase 2: le raccolte non sono collaborazioni
    c = c[c.n_credited.fillna(1) <= cfg["network"]["max_credits"]]
    log.info(f"coppie (artista, release) datate e filtrate: {len(c):,}")

    # coppie dentro ciascuna release, via self-join
    sz = c.groupby("release_id").artist_id.nunique()
    ok = sz[(sz >= 2) & (sz <= cfg["network"]["max_credits"])].index
    c = c[c.release_id.isin(ok)]
    m = c.merge(c, on=["release_id", "year"], suffixes=("_u", "_v"))
    m = m[m.artist_id_u < m.artist_id_v]
    log.info(f"coppie co-presenti: {len(m):,}")

    # l'anno del legame e' quello della PRIMA pubblicazione condivisa
    e = (m.groupby(["artist_id_u", "artist_id_v"], as_index=False)
           .agg(anno=("year", "min"), n_release=("release_id", "nunique")))
    e.columns = ["u", "v", "anno", "n_release_condivise"]
    e["decennio"] = (e.anno // 10 * 10).astype(int)
    log.info(f"archi datati: {len(e):,} "
             f"({e.anno.min():.0f}-{e.anno.max():.0f})")
    common.save(e, "edges_datati.parquet")
    return e


def qap_periodo(E: pd.DataFrame, gen: pd.Series, seed: int, log) -> dict:
    """Permutazione delle etichette a rete fissa, dentro un periodo."""
    nodi = np.unique(np.concatenate([E.u.values, E.v.values]))
    g = gen.reindex(nodi).values
    pos = {a: i for i, a in enumerate(nodi)}
    u = E.u.map(pos).values
    v = E.v.map(pos).values
    rng = np.random.default_rng(seed)

    def quote(gg):
        gu, gv = gg[u], gg[v]
        return {c: float(((gu == c) & (gv == c)).mean()) for c in ("F", "M")}

    oss = quote(g)
    nulla = {c: np.empty(PERMUTAZIONI) for c in oss}
    for i in range(PERMUTAZIONI):
        q = quote(rng.permutation(g))
        for c in nulla:
            nulla[c][i] = q[c]

    out = {"nodi": len(nodi), "archi": len(E),
           "quota_donne": float((g == "F").mean())}
    for c in ("F", "M"):
        d = nulla[c]
        out[f"oss_{c}"] = oss[c]
        out[f"att_{c}"] = float(d.mean())
        out[f"rapporto_{c}"] = oss[c] / d.mean() if d.mean() else np.nan
        out[f"z_{c}"] = (oss[c] - d.mean()) / d.std() if d.std() else np.nan
    return out


def logit_periodo(E: pd.DataFrame, attrs: pd.DataFrame, seed: int, log) -> dict:
    """Logit diadico caso-controllo dentro un periodo."""
    import statsmodels.api as sm
    nodi = np.unique(np.concatenate([E.u.values, E.v.values]))
    a = attrs.reindex(nodi)
    gen = a.gender.values
    gmu = a.musical_genre.fillna("Unknown").values
    coh = a.cohort_decade.astype("Int64").astype(str).fillna("NA").values
    lnr = np.log(a.n_release.fillna(1).clip(lower=1)).values
    pos = {x: i for i, x in enumerate(nodi)}
    casi = np.column_stack([E.u.map(pos).values, E.v.map(pos).values])

    rng = np.random.default_rng(seed)
    archi = set(map(tuple, np.sort(casi, axis=1)))
    n, n_ctrl = len(nodi), len(casi) * CONTROLLI_PER_CASO
    ctrl = []
    while len(ctrl) < n_ctrl:
        k = (n_ctrl - len(ctrl)) * 2
        i, j = rng.integers(0, n, k), rng.integers(0, n, k)
        cand = np.sort(np.column_stack([i[i != j], j[i != j]]), axis=1)
        for x, y in cand:
            if (x, y) not in archi:
                ctrl.append((x, y))
                if len(ctrl) >= n_ctrl:
                    break
    ctrl = np.array(ctrl)

    tutte = np.vstack([casi, ctrl])
    y = np.concatenate([np.ones(len(casi)), np.zeros(len(ctrl))])
    uu, vv = tutte[:, 0], tutte[:, 1]
    X = pd.DataFrame({
        "same_F": ((gen[uu] == "F") & (gen[vv] == "F")).astype(float),
        "same_M": ((gen[uu] == "M") & (gen[vv] == "M")).astype(float),
        "same_genre": (gmu[uu] == gmu[vv]).astype(float),
        "same_cohort": (coh[uu] == coh[vv]).astype(float),
        "sum_lognrel": lnr[uu] + lnr[vv],
    })
    try:
        m = sm.Logit(y, sm.add_constant(X)).fit(disp=0)
        return {"logit_F": float(m.params["same_F"]),
                "logit_F_se": float(m.bse["same_F"]),
                "logit_M": float(m.params["same_M"]),
                "logit_M_se": float(m.bse["same_M"]),
                "logit_genre": float(m.params["same_genre"])}
    except Exception as e:
        log.warning(f"  logit non stimabile: {e!r}")
        return {}


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4d_temporal", cfg)
    if common.exists("homophily_temporal.parquet") and not force:
        log.info("Fase 4d gia' completata, salto")
        return
    seed = cfg["project"]["seed"]
    pop = common.load("population_gender.parquet")
    attrs = pop.set_index("artist_id")
    gen = attrs.gender

    with Timer("datazione degli archi", log):
        E = archi_datati(cfg, log)

    righe = []
    for dec, g in E.groupby("decennio"):
        if len(g) < MIN_ARCHI:
            log.info(f"  {dec}s: {len(g):,} archi, sotto la soglia — saltato")
            continue
        with Timer(f"periodo {dec}s ({len(g):,} archi)", log):
            r = {"decennio": int(dec)}
            r.update(qap_periodo(g, gen, seed, log))
            r.update(logit_periodo(g, attrs, seed, log))
        righe.append(r)
        log.info(f"  {dec}s: quota donne {r['quota_donne']:.3f} | "
                 f"QAP F {r['rapporto_F']:.2f} (z={r['z_F']:+.1f}) "
                 f"M {r['rapporto_M']:.2f} (z={r['z_M']:+.1f}) | "
                 f"logit F {r.get('logit_F', float('nan')):+.3f} "
                 f"M {r.get('logit_M', float('nan')):+.3f}")

    df = pd.DataFrame(righe)
    common.save(df, "homophily_temporal.parquet")
    common.save_table(df, "t4_omofilia_nel_tempo",
                      "Omofilia di genere per decennio di formazione del legame, "
                      "sulla rete integrale: rapporto osservato/atteso da "
                      "permutazione a rete fissa, e coefficienti del logit "
                      "diadico condizionale")
    log.info("\n" + df.round(4).to_string(index=False))
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
