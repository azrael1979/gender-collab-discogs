"""FASE 5 — robustezza dei risultati.

Tre blocchi:

1. Monte Carlo sull'incertezza del genere sessuale. Gli `unknown` non sono
   mancanti a caso: chi ha un solo credito ha meno probabilita' di essere
   risolto. Si delimita allora l'omofilia fra due estremi costruiti apposta
   (assegnazione che la massimizza e assegnazione che la minimizza) e la si
   stima con B estrazioni dalla marginale osservata.

2. Sensibilita' a un parametro per volta rispetto alla configurazione di
   default: numero massimo di crediti per release, peso minimo dell'arco,
   esclusione delle raccolte, soglia di italianita', terna dei pesi di
   specificita', uso o meno dei crediti a livello traccia.

3. Artisti con genere musicale debole (tag top sotto il 40%): metriche
   ricalcolate usando il secondo tag e escludendoli del tutto.
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
from phase2_network import filter_credits, project
from phase3_homophily import edge_attrs, mixing_matrix, assortativity

RAW = ROOT / "data" / "raw"


# ------------------------------------------------- 1. Monte Carlo sul genere
def montecarlo_gender(pop, edges, cfg, log):
    B = cfg["robustness"]["montecarlo_B"]
    rng = np.random.default_rng(cfg["project"]["seed"] + 7)
    known = pop[pop.gender.isin(["M", "F"])]
    p_f = float((known.gender == "F").mean())
    unk = pop.gender.isin(["unknown", "mixed"]).values
    log.info(f"Monte Carlo: {unk.sum():,} nodi da imputare "
             f"({unk.mean():.1%}); marginale osservata P(F)={p_f:.4f}")

    base = pop.gender.where(pop.gender.isin(["M", "F"]), None).values.astype(object)
    ids = pop.artist_id.values
    pos = {a: i for i, a in enumerate(ids)}

    def r_for(labels):
        s = pd.Series(labels, index=ids, name="g")
        tmp = pop[["artist_id"]].copy()
        tmp["gender"] = tmp.artist_id.map(s)
        a, b, w, cats = edge_attrs(edges, tmp, "gender")
        return assortativity(mixing_matrix(a, b, k=len(cats)))

    rows = []
    # --- riferimento: solo i nodi con genere gia' noto
    obs = base.copy()
    rows.append({"scenario": "solo_noti", "replica": 0, "r": r_for(obs)})

    # --- estremi: si guarda il vicinato NOTO e si assegna per massimizzare o
    #     minimizzare l'omofilia. Sono limiti, non stime.
    #     Un nodo ignoto i cui vicini sono tutti a loro volta ignoti non porta
    #     informazione: assegnarlo per maggioranza lo metterebbe sempre nella
    #     stessa categoria, creando un blocco artificiale che gonfia entrambi
    #     gli estremi invece di delimitarli. Quei nodi vengono percio' estratti
    #     dalla marginale, come nello scenario neutro.
    G = nx.Graph()
    G.add_nodes_from(ids)
    G.add_weighted_edges_from(edges[["u", "v", "w"]].itertuples(index=False, name=None))
    nb_major, senza_vicini_noti = {}, 0
    for i, a in enumerate(ids):
        if not unk[i]:
            continue
        cnt = {"M": 0.0, "F": 0.0}
        for v, d in G[a].items():
            gv = base[pos[v]]
            if gv in cnt:
                cnt[gv] += d["weight"]
        if cnt["M"] == 0 and cnt["F"] == 0:
            senza_vicini_noti += 1
            continue
        nb_major[a] = "M" if cnt["M"] > cnt["F"] else "F"
    log.info(f"nodi ignoti con almeno un vicino di genere noto: {len(nb_major):,}; "
             f"senza vicini noti: {senza_vicini_noti:,} "
             f"(estratti dalla marginale anche negli scenari estremi)")
    opp = {"M": "F", "F": "M"}
    for scen, fn in [("peggiore_omofilia_max", lambda a: nb_major[a]),
                     ("migliore_omofilia_min", lambda a: opp[nb_major[a]])]:
        lab = base.copy()
        resto = rng.random(len(ids)) < p_f
        for i, a in enumerate(ids):
            if not unk[i]:
                continue
            lab[i] = fn(a) if a in nb_major else ("F" if resto[i] else "M")
        rows.append({"scenario": scen, "replica": 0, "r": r_for(lab)})

    # --- status quo: estrazioni dalla marginale osservata
    with Timer(f"Monte Carlo status quo (B={B})", log):
        for b in range(B):
            lab = base.copy()
            draw = np.where(rng.random(unk.sum()) < p_f, "F", "M")
            lab[unk] = draw
            rows.append({"scenario": "status_quo", "replica": b, "r": r_for(lab)})
    df = pd.DataFrame(rows)
    summ = df.groupby("scenario").r.agg(["count", "mean", "std", "min", "max"]).reset_index()
    sq = df[df.scenario == "status_quo"].r
    summ.loc[summ.scenario == "status_quo", "ci_lo"] = np.percentile(sq, 2.5)
    summ.loc[summ.scenario == "status_quo", "ci_hi"] = np.percentile(sq, 97.5)
    common.save(df, "mc_gender.parquet")
    common.save_table(summ, "t5_montecarlo_genere",
                      "Assortativita' di genere sotto scenari di imputazione degli "
                      "`unknown`/`mixed`: limiti estremi e distribuzione Monte Carlo")
    log.info("\n" + summ.to_string(index=False))
    return summ


# -------------------------------------------------------- 2. sensibilita'
def key_metrics(edges, pop, label, log) -> dict:
    if edges.empty:
        return {"variante": label, "archi": 0}
    a, b, w, cats = edge_attrs(edges, pop, "gender")
    r_g = assortativity(mixing_matrix(a, b, k=len(cats)))
    # versione PESATA: e' l'unica su cui la terna dei pesi di specificita' puo'
    # mostrarsi, perche' cambiare i pesi non cambia quali archi esistono
    r_gw = assortativity(mixing_matrix(a, b, w, k=len(cats)))
    # versione sui soli nodi con genere determinato (misura di riferimento)
    mf = pop.copy()
    mf.loc[~mf.gender.isin(["M", "F"]), "gender"] = None
    amf, bmf, wmf, cmf = edge_attrs(edges, mf, "gender")
    r_mf = assortativity(mixing_matrix(amf, bmf, k=len(cmf))) if len(amf) > 100 else np.nan
    a2, b2, w2, c2 = edge_attrs(edges, pop, "musical_genre")
    r_m = assortativity(mixing_matrix(a2, b2, k=len(c2)))
    G = nx.Graph()
    G.add_nodes_from(pop.artist_id)
    G.add_weighted_edges_from(edges[["u", "v", "w"]].itertuples(index=False, name=None))
    Gs = G.subgraph([n for n, d in G.degree() if d > 0])
    comps = sorted(nx.connected_components(Gs), key=len, reverse=True)
    known = pop[pop.gender.isin(["M", "F"])]
    return {"variante": label, "nodi": Gs.number_of_nodes(), "archi": len(edges),
            "densita": nx.density(Gs) if Gs.number_of_nodes() > 1 else np.nan,
            "quota_gigante": len(comps[0]) / Gs.number_of_nodes() if comps else np.nan,
            "r_gender": r_g, "r_gender_MF": r_mf, "r_gender_pesato": r_gw,
            "r_genere_musicale": r_m,
            "quota_donne": float((known.gender == "F").mean()),
            "peso_mediano": float(edges.w.median())}


def sensitivity(cfg, log):
    S = cfg["robustness"]["sensitivity"]
    credits = common.load("credits.parquet")
    pop_full = common.load("population_gender.parquet")
    counts = pd.read_csv(RAW / "raw_artist_counts.csv")
    rows = [key_metrics(common.load("edges_all.parquet"), pop_full, "default", log)]

    def variant(label, overrides, pop=None, cr=None):
        c, n = filter_credits(cr if cr is not None else credits, cfg, log, overrides)
        e = project(c, n, log)
        rows.append(key_metrics(e, pop if pop is not None else pop_full, label, log))

    for v in S["max_credits"]:
        if v != cfg["network"]["max_credits"]:
            variant(f"max_credits={v}", {"max_credits": v})
    for v in S["min_edge_weight"]:
        if v != cfg["network"]["min_edge_weight"]:
            variant(f"peso_min_arco={v}", {"min_edge_weight": v})
    for v in S["exclude_compilations"]:
        if v != cfg["network"]["exclude_compilations"]:
            variant(f"raccolte_escluse={v}", {"exclude_compilations": v})
    for v in S["use_track_credits"]:
        if v != cfg["network"]["use_track_credits"]:
            variant(f"crediti_traccia={v}", {"use_track_credits": v})
    for w in S["credit_scope_weight"]:
        if w != cfg["network"]["credit_scope_weight"]:
            variant(f"pesi_specificita={w['track']}/{w['main']}/{w['umbrella']}",
                    {"credit_scope_weight": w})
    for v in S["italian_share"]:
        if v == cfg["population"]["min_italian_share"]:
            continue
        counts2 = counts.copy()
        counts2["share"] = counts2.n_it / counts2.n_all
        keep = set(counts2[(counts2.share >= v) &
                           (counts2.n_all >= cfg["population"]["min_total_releases"])].artist_id)
        pop2 = pop_full[pop_full.artist_id.isin(keep)]
        cr2 = credits[credits.artist_id.isin(keep)]
        log.info(f"soglia italianita' {v}: {len(pop2):,} artisti")
        variant(f"soglia_italianita={v}", {}, pop=pop2, cr=cr2)

    df = pd.DataFrame(rows)
    common.save(df, "sensitivity.parquet")
    common.save_table(df, "t5_sensibilita",
                      "Sensibilita' delle metriche chiave ai parametri di costruzione "
                      "della rete (una variazione per volta rispetto al default)")
    log.info("\n" + df.to_string(index=False))
    return df


# ------------------------------------------------------- 3. genre_weak
def genre_weak_variants(cfg, log):
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    rows = []
    for variant in cfg["robustness"]["genre_weak_variants"]:
        p = pop.copy()
        if variant == "top2":
            m = p.genre_weak & p.musical_genre_2.notna()
            p.loc[m, "musical_genre"] = p.loc[m, "musical_genre_2"]
            e = edges
        elif variant == "exclude":
            keep = set(p[~p.genre_weak].artist_id)
            p = p[p.artist_id.isin(keep)]
            e = edges[edges.u.isin(keep) & edges.v.isin(keep)]
        else:
            e = edges
        m = key_metrics(e, p, f"genre_{variant}", log)
        m["n_artisti"] = len(p)
        m["n_generi"] = p.musical_genre.nunique()
        rows.append(m)
    df = pd.DataFrame(rows)
    common.save(df, "genre_weak_variants.parquet")
    common.save_table(df, "t5_genere_debole",
                      "Metriche chiave per gli artisti con genere musicale debole: "
                      "tag principale, secondo tag, esclusione")
    log.info("\n" + df.to_string(index=False))
    return df


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase5_robustness", cfg)
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    if not common.exists("mc_gender.parquet") or force:
        with Timer("monte carlo genere", log):
            montecarlo_gender(pop, edges, cfg, log)
    if not common.exists("sensitivity.parquet") or force:
        with Timer("sensibilita'", log):
            sensitivity(cfg, log)
    if not common.exists("genre_weak_variants.parquet") or force:
        with Timer("genere debole", log):
            genre_weak_variants(cfg, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
