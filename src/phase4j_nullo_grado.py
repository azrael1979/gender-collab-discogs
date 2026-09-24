"""FASE 4j — il nullo della Fase 4e ignora quanti legami ha ciascuno.

Perche' questa fase esiste
--------------------------
La permutazione della Fase 4e assegna le etichette di genere ai nodi in modo
UNIFORME: ogni nodo ha la stessa probabilita' di ricevere l'etichetta F,
qualunque sia il suo grado. Tiene fissa la rete, ma non tiene fisso CHI ha
molti legami. Se le donne hanno in media meno legami degli uomini — e ne hanno:
fra 0,65 e 0,70 volte la media nei decenni 1950-1970 — il nullo uniforme si
aspetta piu' legami donna-donna di quanti ne produrrebbe il caso fra persone
con la loro attivita'. Un rapporto osservato/atteso sotto 1 puo' allora dire
soltanto "le donne hanno meno legami", non "le donne evitano le donne".

La matrice di mixing della Fase 3 usa invece un nullo a grado preservato, e
sulla rete intera da' un rapporto donna-donna di 1,54 dove la permutazione
uniforme da' 0,82: stesso dato, segno opposto. Serve sapere quale dei due
nulli risponde alla domanda dell'articolo, decennio per decennio.

Il disegno
----------
Stesso insieme di nodi e di archi della Fase 4e, decennio per decennio e sulla
rete intera. Le etichette si permutano **all'interno di strati di grado**:
artisti con lo stesso numero di legami (strati fusi fino ad almeno
`MIN_STRATO` nodi) si scambiano l'etichetta solo fra loro. Cosi' ogni genere
conserva esattamente la sua distribuzione dei gradi a meno della grana degli
strati, e la rete resta fissa come nella 4e. La media e la deviazione della
distribuzione nulla vengono da `REPLICHE` permutazioni: con gli strati la forma
chiusa della 4e non vale piu'.

Accanto si riportano, per controllo:

* il rapporto sotto nullo uniforme, che deve coincidere con la Fase 4e;
* il rapporto di Newman sul modello di configurazione, `oss / (m * a_c^2)`
  con `a_c` la quota di estremita' d'arco della categoria c.

Previsione dichiarata prima di eseguire
---------------------------------------
Se il deficit dei primi decenni e' un effetto di attivita', sotto il nullo per
strati di grado i rapporti F dei decenni 1950-1970 salgono attorno a 1 o
sopra; se e' segregazione, restano sotto 1.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import Timer
from phase4e_esatto import carica

REPLICHE = 2000
MIN_STRATO = 30
CATEGORIE = ("F", "M")


def strati_di_grado(gradi: np.ndarray, minimo: int = MIN_STRATO) -> np.ndarray:
    """Strato per ogni nodo: gradi uguali insieme, strati contigui fusi finche'
    ciascuno ha almeno `minimo` nodi (l'ultimo si fonde col precedente)."""
    valori, conte = np.unique(gradi, return_counts=True)
    etichetta = np.empty(len(valori), dtype=np.int32)
    s, acc = 0, 0
    for i, c in enumerate(conte):
        etichetta[i] = s
        acc += c
        if acc >= minimo:
            s, acc = s + 1, 0
    if acc and s > 0:                       # coda troppo piccola: al precedente
        etichetta[etichetta == s] = s - 1
    return etichetta[np.searchsorted(valori, gradi)]


def permuta_negli_strati(etichette: np.ndarray, strati: np.ndarray,
                         rng: np.random.Generator) -> np.ndarray:
    """Una permutazione delle etichette che non esce dagli strati."""
    ordine = np.lexsort((rng.random(len(strati)), strati))
    base = np.argsort(strati, kind="stable")
    out = np.empty_like(etichette)
    out[base] = etichette[ordine]
    return out


def confronta(gender: np.ndarray, ii: np.ndarray, jj: np.ndarray,
              rng: np.random.Generator, repliche: int = REPLICHE) -> list[dict]:
    n, m = len(gender), len(ii)
    gradi = np.bincount(np.concatenate([ii, jj]), minlength=n)
    strati = strati_di_grado(gradi)
    righe = []
    for c in CATEGORIE:
        lab = gender == c
        oss = int((lab[ii] & lab[jj]).sum())
        nc = int(lab.sum())
        att_unif = m * nc * (nc - 1) / (n * (n - 1))
        a_c = gradi[lab].sum() / (2 * m)
        sim = np.empty(repliche)
        for r in range(repliche):
            p = permuta_negli_strati(lab, strati, rng)
            sim[r] = (p[ii] & p[jj]).sum()
        mu, sd = sim.mean(), sim.std(ddof=1)
        righe.append({
            "categoria": c, "nodi": n, "archi": m, "n_categoria": nc,
            "strati": int(strati.max() + 1),
            "grado_medio_relativo": float(gradi[lab].mean() / gradi.mean()),
            "osservati": oss,
            "attesi_uniforme": att_unif,
            "rapporto_uniforme": oss / att_unif,
            "attesi_grado": mu, "sd_grado": sd,
            "rapporto_grado": oss / mu, "z_grado": (oss - mu) / sd,
            "rapporto_configurazione": oss / (m * a_c ** 2),
        })
    return righe


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4j_nullo_grado", cfg)
    if common.exists("nullo_grado.parquet") and not force:
        log.info("Fase 4j gia' completata, salto")
        return
    rng = np.random.default_rng(cfg["project"]["seed"])
    righe = []

    # --- decennio per decennio: stessa selezione della Fase 4e ------------
    E = common.load("edges_datati.parquet")
    pop = common.load("population_gender.parquet").set_index("artist_id")
    for dec, g in E.groupby("decennio"):
        nodi = np.unique(np.concatenate([g.u.values, g.v.values]))
        nodi = nodi[pd.Index(nodi).isin(pop.index)]
        a = pop.reindex(nodi)
        a = a[a.gender.isin(["M", "F", "mixed"])]
        nodi = a.index.values
        pos = {x: i for i, x in enumerate(nodi)}
        gg = g[g.u.isin(pos) & g.v.isin(pos)]
        if len(nodi) < 100 or len(gg) < 200:
            continue
        ii = gg.u.map(pos).values.astype(np.int32)
        jj = gg.v.map(pos).values.astype(np.int32)
        with Timer(f"{dec}s ({len(nodi):,} nodi, {len(gg):,} archi)", log):
            for r in confronta(a.gender.values.astype(str), ii, jj, rng):
                righe.append({"insieme": f"{int(dec)}s", "decennio": int(dec), **r})

    # --- rete intera: stessa rete della permutazione esatta ---------------
    n, attrs, A, ii, jj, gradi = carica(cfg, log)
    with Timer("rete intera", log):
        for r in confronta(attrs["gender"], ii, jj, rng, repliche=REPLICHE // 2):
            righe.append({"insieme": "rete intera", "decennio": None, **r})

    out = pd.DataFrame(righe)
    log.info("\n" + out[["insieme", "categoria", "grado_medio_relativo",
                         "rapporto_uniforme", "rapporto_grado", "z_grado",
                         "rapporto_configurazione"]].round(3).to_string(index=False))

    # controllo di coerenza con la Fase 4e: il nullo uniforme deve coincidere
    te = common.load("temporale_esatto.parquet").set_index("decennio")
    f = out[(out.categoria == "F") & out.decennio.notna()].set_index("decennio")
    scarto = (f.rapporto_uniforme - te.rapporto_F.reindex(f.index)).abs().max()
    log.info(f"scarto massimo dal rapporto uniforme della Fase 4e: {scarto:.2e}")

    common.save(out, "nullo_grado.parquet")
    common.save_table(out, "t5_nullo_grado",
                      "Legami entro-genere osservati su attesi sotto due nulli: "
                      "permutazione uniforme (Fase 4e) e permutazione entro strati "
                      "di grado")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
