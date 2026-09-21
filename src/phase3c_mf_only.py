"""FASE 3 (supplemento) — assortativita' di genere sui SOLI nodi M/F.

Perche' serve una misura separata
---------------------------------
La matrice di mixing calcolata su tutte e quattro le categorie
(M, F, mixed, unknown) produce un'assortativita' piu' alta di quella reale,
perche' la cella unknown-unknown e' fortemente sopra l'atteso. Quello pero' non
e' un fatto sociale: gli artisti su cui non sappiamo il genere condividono le
caratteristiche che li rendono poco documentati (pochi crediti, ruoli minori,
epoche marginali), e quindi collaborano fra loro piu' del caso per ragioni di
copertura dei dati, non di omofilia.

La misura riportata qui restringe il calcolo agli archi in cui ENTRAMBI gli
estremi hanno genere determinato. E' la stima conservativa e va considerata
quella di riferimento; la versione a quattro categorie resta come confronto.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer
from phase3_homophily import (edge_attrs, mixing_matrix, assortativity,
                              null_mixing, bootstrap_r, ci)


def restrict(pop: pd.DataFrame, attributo: str = "gender") -> pd.DataFrame:
    """Azzera la categoria non informativa, cosi' che gli archi che la toccano
    vengano esclusi dal calcolo invece di formare una categoria a se'."""
    p = pop.copy()
    if attributo == "gender":
        p.loc[~p.gender.isin(["M", "F"]), "gender"] = None
    else:
        p.loc[p[attributo] == "Unknown", attributo] = None
    return p


def run(cfg, log):
    B = cfg["homophily"]["bootstrap_B"]
    reps = cfg["homophily"]["null_model_reps"]
    rng = np.random.default_rng(cfg["project"]["seed"] + 11)
    pop = common.load("population_gender.parquet")
    era = pop.set_index("artist_id").era
    # lo stesso confronto si fa su ENTRAMBI gli attributi. Per il genere
    # sessuale escludere gli indeterminati ABBASSA l'assortativita'; per il
    # genere musicale la ALZA. Riportarli insieme evita il sospetto che
    # l'esclusione sia stata scelta perche' conveniva al risultato.
    varianti = {"gender": restrict(pop, "gender"),
                "musical_genre": restrict(pop, "musical_genre")}
    rows = []
    for sub in cfg["network"]["subnetworks"]:
        if not common.exists(f"edges_{sub}.parquet"):
            continue
        E = common.load(f"edges_{sub}.parquet")
        eu, ev = E.u.map(era), E.v.map(era)
        strati = [("tutto", E), ("pre2000", E[(eu == "pre2000") & (ev == "pre2000")]),
                  ("post2000", E[(eu == "post2000") & (ev == "post2000")])]
        for nome, Es in strati:
            if len(Es) < 100:
                continue
            for attributo, ridotta in varianti.items():
                etichette = [("determinati soltanto", ridotta),
                             ("tutte le categorie", pop)]
                for etichetta, popolazione in etichette:
                    a, b, w, cats = edge_attrs(Es, popolazione, attributo)
                    if len(a) < 100:
                        continue
                    k = len(cats)
                    r = assortativity(mixing_matrix(a, b, k=k))
                    bs = bootstrap_r(a, b, k, B, rng)
                    _, rn = null_mixing(a, b, k, reps, rng)
                    lo, hi = ci(bs, cfg["homophily"]["ci_level"])
                    rows.append({"sottorete": sub, "strato": nome,
                                 "attributo": attributo, "categorie": etichetta,
                                 "n_categorie": k, "archi_usati": len(a),
                                 "archi_totali": len(Es),
                                 "quota_archi_usati": len(a) / len(Es),
                                 "r": r, "ci_lo": lo, "ci_hi": hi,
                                 "r_null": float(rn.mean()),
                                 "z": float((r - rn.mean()) / rn.std()) if rn.std() else np.nan})
                    log.info(f"[{sub}/{nome}/{attributo}/{etichetta}] r={r:.4f} "
                             f"IC95 [{lo:.4f},{hi:.4f}] archi={len(a):,} "
                             f"({len(a)/len(Es):.0%} dello strato)")
    df = pd.DataFrame(rows)
    common.save(df, "assortativity_mf.parquet")
    common.save_table(df, "t3_assortativita_MF_vs_tutte",
                      "Assortativita' calcolata sui soli archi fra nodi con "
                      "attributo determinato, a confronto con il calcolo che "
                      "tratta 'indeterminato' come una categoria. Il confronto e' "
                      "fatto sia per il genere sessuale sia per quello musicale")
    return df


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase3c_mf_only", cfg)
    if common.exists("assortativity_mf.parquet") and not force:
        log.info("gia' fatto, salto")
        return
    with Timer("assortativita' solo M/F", log):
        run(cfg, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
