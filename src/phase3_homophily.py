"""FASE 3 — omofilia, mixing e posizione nella rete.

Null model
----------
"Grado e composizione preservati" e' realizzato con un configuration model a
stub-matching: la sequenza dei gradi viene espansa in stub, gli stub vengono
permutati e riappaiati. I gradi restano esattamente quelli osservati e la
composizione dei nodi per attributo non cambia; cio' che si randomizza e' solo
CHI sta con CHI. Il tutto e' vettorizzato in numpy, quindi le 500 repliche
costano quanto una manciata di secondi.
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

GENDERS = ["F", "M", "mixed", "unknown"]


# --------------------------------------------------------------- utilities
def edge_attrs(edges: pd.DataFrame, pop: pd.DataFrame, col: str):
    """Attributo dei due estremi di ogni arco, come codici interi."""
    m = pop.set_index("artist_id")[col]
    cats = pd.Categorical(m.dropna().astype(str)).categories
    code = {c: i for i, c in enumerate(cats)}
    a = edges.u.map(m).astype(str).map(code)
    b = edges.v.map(m).astype(str).map(code)
    ok = a.notna() & b.notna()
    return a[ok].astype(int).values, b[ok].astype(int).values, \
        edges.w[ok].values, list(cats)


def mixing_matrix(a, b, w=None, k=None) -> np.ndarray:
    """Matrice di mixing simmetrizzata e normalizzata a somma 1.

    Gli indici vengono appiattiti e contati con `np.bincount` invece di
    `np.add.at`: a parita' di risultato e' circa due ordini di grandezza piu'
    veloce, il che rende praticabili le migliaia di repliche bootstrap e di
    null model richieste dal disegno.
    """
    k = int(k or (max(a.max(), b.max()) + 1))
    M = np.bincount(a * k + b, weights=w, minlength=k * k).reshape(k, k)
    M = M + M.T
    tot = M.sum()
    return M / tot if tot else M


def assortativity(M: np.ndarray) -> float:
    """r di Newman per attributi categoriali."""
    a, b = M.sum(1), M.sum(0)
    s = (a * b).sum()
    return float((np.trace(M) - s) / (1 - s)) if s < 1 else np.nan


def null_mixing(a, b, k, reps, rng):
    """Configuration model a stub-matching: permuta gli estremi degli archi
    conservando i gradi (e quindi la composizione) di ciascun nodo."""
    stubs = np.concatenate([a, b])
    out = np.empty((reps, k, k))
    rr = np.empty(reps)
    for i in range(reps):
        s = rng.permutation(stubs)
        half = len(s) // 2
        M = mixing_matrix(s[:half], s[half:2 * half], k=k)
        out[i] = M
        rr[i] = assortativity(M)
    return out, rr


def bootstrap_r(a, b, k, B, rng, w=None):
    n = len(a)
    r = np.empty(B)
    for i in range(B):
        idx = rng.integers(0, n, n)
        r[i] = assortativity(mixing_matrix(a[idx], b[idx],
                                           None if w is None else w[idx], k=k))
    return r


def ci(x, level=0.95):
    lo, hi = (1 - level) / 2 * 100, (1 + level) / 2 * 100
    return float(np.nanpercentile(x, lo)), float(np.nanpercentile(x, hi))


# ------------------------------------------------------- 3.1 mixing matrix
def run_mixing(edges, pop, cfg, log):
    rng = np.random.default_rng(cfg["project"]["seed"])
    reps = cfg["homophily"]["null_model_reps"]
    rows_oe = []
    for col, stem in [("gender", "gender"), ("musical_genre", "genere_musicale")]:
        a, b, w, cats = edge_attrs(edges, pop, col)
        k = len(cats)
        M = mixing_matrix(a, b, k=k)
        Mw = mixing_matrix(a, b, w, k=k)
        with Timer(f"null model {col} ({reps} repliche)", log):
            Mn, rn = null_mixing(a, b, k, reps, rng)
        E = Mn.mean(0)
        OE = np.divide(M, E, out=np.full_like(M, np.nan), where=E > 0)
        z = (M - E) / np.where(Mn.std(0) > 0, Mn.std(0), np.nan)

        common.save_table(pd.DataFrame(M, index=cats, columns=cats).reset_index(names=col),
                          f"t3_mixing_{stem}_osservata", f"Mixing matrix osservata per {col}")
        common.save_table(pd.DataFrame(Mw, index=cats, columns=cats).reset_index(names=col),
                          f"t3_mixing_{stem}_pesata", f"Mixing matrix pesata per {col}")
        common.save_table(pd.DataFrame(OE, index=cats, columns=cats).reset_index(names=col),
                          f"t3_mixing_{stem}_oss_att",
                          f"Rapporto osservato/atteso per {col} (null a grado preservato)")
        common.save_table(pd.DataFrame(z, index=cats, columns=cats).reset_index(names=col),
                          f"t3_mixing_{stem}_z", f"Punteggi z rispetto al null model per {col}")
        np.save(ROOT / "data" / f"oe_{stem}.npy", OE)
        (ROOT / "data" / f"cats_{stem}.txt").write_text("\n".join(cats))
        rows_oe.append({"attributo": col, "r_osservato": assortativity(M),
                        "r_pesato": assortativity(Mw),
                        "r_null_medio": float(rn.mean()), "r_null_sd": float(rn.std()),
                        "z": float((assortativity(M) - rn.mean()) / rn.std())})
        log.info(f"[{col}] r={assortativity(M):.4f} (pesato {assortativity(Mw):.4f}) "
                 f"null {rn.mean():.4f}+-{rn.std():.4f} z={rows_oe[-1]['z']:.1f}")
    df = pd.DataFrame(rows_oe)
    common.save(df, "assortativity_overall.parquet")
    common.save_table(df, "t3_assortativita_globale",
                      "Assortativita' osservata e attesa sotto null model a grado preservato")
    return df


# ---------------------------------------- 3.2 assortativita' per strato
def run_assortativity_strata(cfg, pop, log):
    rng = np.random.default_rng(cfg["project"]["seed"] + 1)
    B = cfg["homophily"]["bootstrap_B"]
    reps = cfg["homophily"]["null_model_reps"]
    rows = []
    for sub in cfg["network"]["subnetworks"]:
        if not common.exists(f"edges_{sub}.parquet"):
            continue
        E = common.load(f"edges_{sub}.parquet")
        strata = [("tutto", E)]
        # epoca: un arco appartiene a un'epoca se entrambi gli artisti vi
        # hanno debuttato (definizione conservativa, dichiarata nel report)
        era = pop.set_index("artist_id").era
        eu, ev = E.u.map(era), E.v.map(era)
        for lab in ["pre2000", "post2000"]:
            strata.append((lab, E[(eu == lab) & (ev == lab)]))
        for name, Es in strata:
            if len(Es) < 100:
                continue
            for col in ["gender", "musical_genre"]:
                a, b, w, cats = edge_attrs(Es, pop, col)
                if len(a) < 100:
                    continue
                k = len(cats)
                r = assortativity(mixing_matrix(a, b, k=k))
                bs = bootstrap_r(a, b, k, B, rng)
                _, rn = null_mixing(a, b, k, reps, rng)
                lo, hi = ci(bs, cfg["homophily"]["ci_level"])
                rows.append({"sottorete": sub, "strato": name, "attributo": col,
                             "archi": len(a), "r": r, "ci_lo": lo, "ci_hi": hi,
                             "r_null": float(rn.mean()),
                             "z": float((r - rn.mean()) / rn.std()) if rn.std() else np.nan})
                log.info(f"[{sub}/{name}/{col}] r={r:.4f} IC95 [{lo:.4f},{hi:.4f}] "
                         f"null={rn.mean():.4f} n={len(a):,}")
    df = pd.DataFrame(rows)
    common.save(df, "assortativity_strata.parquet")
    common.save_table(df, "t3_assortativita_per_strato",
                      "Assortativita' per sottorete di ruolo ed epoca, con IC bootstrap 95%")
    return df


# ------------------------------- 3.2b omofilia per genere musicale (RQ2)
def run_homophily_by_genre(cfg, pop, log, min_edges=500):
    rng = np.random.default_rng(cfg["project"]["seed"] + 2)
    B, reps = cfg["homophily"]["bootstrap_B"], cfg["homophily"]["null_model_reps"]
    E = common.load("edges_all.parquet")
    g = pop.set_index("artist_id").musical_genre
    gu, gv = E.u.map(g), E.v.map(g)
    rows = []
    for genre in pop.musical_genre.value_counts().index:
        if genre == "Unknown":
            continue
        Es = E[(gu == genre) & (gv == genre)]
        if len(Es) < min_edges:
            continue
        a, b, w, cats = edge_attrs(Es, pop, "gender")
        k = len(cats)
        M_ = mixing_matrix(a, b, k=k)
        r = assortativity(M_)
        bs = bootstrap_r(a, b, k, B, rng)
        Mn, rn = null_mixing(a, b, k, reps, rng)
        lo, hi = ci(bs)
        # omofilia separata per M e per F: diagonale osservata su attesa
        Emat = Mn.mean(0)
        oe = {c: (M_[i, i] / Emat[i, i] if Emat[i, i] > 0 else np.nan)
              for i, c in enumerate(cats)}
        rows.append({"genere_musicale": genre, "archi": len(a), "r_gender": r,
                     "ci_lo": lo, "ci_hi": hi, "r_null": float(rn.mean()),
                     "oe_MM": oe.get("M", np.nan), "oe_FF": oe.get("F", np.nan),
                     "n_artisti": int((pop.musical_genre == genre).sum()),
                     "quota_donne": float((pop[pop.musical_genre == genre].gender == "F").mean())})
        log.info(f"[{genre}] r={r:.4f} IC95[{lo:.4f},{hi:.4f}] "
                 f"O/E MM={oe.get('M', float('nan')):.2f} FF={oe.get('F', float('nan')):.2f}")
    df = pd.DataFrame(rows).sort_values("archi", ascending=False)
    common.save(df, "homophily_by_genre.parquet")
    common.save_table(df, "t3_omofilia_per_genere_musicale",
                      "Omofilia di genere sessuale entro ciascun genere musicale (RQ2)")
    return df


# --------------------------------------- 3.3 quota donne x genere x decennio
def run_women_share(pop, cfg, log):
    d = pop[pop.cohort_decade.notna()].copy()
    d["cohort_decade"] = d.cohort_decade.astype(int)
    tot = d.groupby(["musical_genre", "cohort_decade"]).size().rename("n_artisti")
    known = d[d.gender.isin(["M", "F"])]
    kk = known.groupby(["musical_genre", "cohort_decade"]).size().rename("n_noti")
    ff = known[known.gender == "F"].groupby(["musical_genre", "cohort_decade"]).size().rename("n_donne")
    out = pd.concat([tot, kk, ff], axis=1).fillna(0).reset_index()
    out["quota_donne"] = out.n_donne / out.n_noti.replace(0, np.nan)
    # intervallo di Wilson: piu' onesto sulle celle piccole
    z = 1.96
    n, p = out.n_noti, out.quota_donne
    den = 1 + z ** 2 / n
    ctr = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    out["ci_lo"], out["ci_hi"] = (ctr - half).clip(0, 1), (ctr + half).clip(0, 1)
    out["rapporto_uomini_donne"] = (out.n_noti - out.n_donne) / out.n_donne.replace(0, np.nan)
    common.save(out, "women_share.parquet")
    common.save_table(out, "t3_quota_donne_genere_decennio",
                      "Quota di donne per genere musicale e decennio di debutto (RQ1), "
                      "con intervalli di Wilson al 95%")
    log.info("quota donne complessiva per decennio:\n" +
             out.groupby("cohort_decade").apply(
                 lambda g: g.n_donne.sum() / max(g.n_noti.sum(), 1)).round(4).to_string())
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase3_homophily", cfg)
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    with Timer("mixing e assortativita' globale", log):
        run_mixing(edges, pop, cfg, log)
    with Timer("quota donne", log):
        run_women_share(pop, cfg, log)
    with Timer("assortativita' per strato", log):
        run_assortativity_strata(cfg, pop, log)
    with Timer("omofilia per genere musicale", log):
        run_homophily_by_genre(cfg, pop, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
