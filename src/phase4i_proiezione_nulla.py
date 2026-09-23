"""FASE 4i — la bimodalita' viene davvero dalla proiezione? Il test senza ERGM.

Perche' questa fase esiste
--------------------------
La Fase 4h doveva confermare per via causale che lo scarto a U della bonta' di
adattamento nasce dalla bimodalita' dei partner condivisi. Ha fallito per
intero: tutte e tre le specifiche alternative, CONTROLLO NEGATIVO COMPRESO, non
convergono su un decennio dove `gwesp(0.25)` converge in cinquantadue minuti.
Senza la GOF del controllo non si puo' nemmeno escludere l'ipotesi alternativa
banale, cioe' che sia questione di decay.

Cercare la conferma dentro l'ERGM era l'errore. L'affermazione da verificare
non riguarda un modello: riguarda il MECCANISMO che genera la rete. E un
meccanismo si verifica facendolo girare.

Il disegno
----------
La rete e' la proiezione di un grafo bipartito artisti-release. Si prende
quella struttura bipartita, la si randomizza conservandone esattamente le due
distribuzioni di grado — quante release per artista, quanti artisti per
release — e la si riproietta. Poi si confronta la distribuzione dei partner
condivisi cosi' ottenuta con quella osservata, e con quella che l'ERGM stimato
produce.

Tre distribuzioni, una domanda:

* **O** — osservata.
* **E** — simulata dall'ERGM stimato (gia' disponibile in `gof.csv`). Sbaglia
  a U: sovrastima il centro, sottostima entrambe le code.
* **B** — proiezione bipartita randomizzata. Non contiene NESSUNA preferenza
  sociale: gli artisti sono assegnati alle release a caso. Contiene solo il
  meccanismo.

Se **B somiglia a O piu' di quanto le somigli E**, allora la forma che l'ERGM
non riesce a riprodurre e' prodotta dal meccanismo di proiezione, non da un
processo di chiusura triadica. E' la conferma che la Fase 4h non ha potuto
dare.

Se invece B e' unimodale quanto E, l'interpretazione e' sbagliata e va
abbandonata.

Sulla natura di questo calcolo
------------------------------
Si simula, ma si simula un processo NOTO, non si stima un parametro ignoto. La
randomizzazione serve a rispondere a "che forma produce questo meccanismo da
solo", non a inferire alcunche' dai dati. E' la stessa differenza che passa fra
un modello nullo e una stima: qui le due distribuzioni di grado sono tenute
esattamente ai valori osservati, e l'unica cosa che varia e' l'appaiamento.
"""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

RAW = ROOT / "data" / "raw"
REPLICHE = 100
# scambi per arco bipartito: dieci bastano a decorrelare l'appaiamento
SCAMBI_PER_ARCO = 10
ESP_MAX = 25


def bipartito(cfg, log, decennio=None):
    """Crediti (artista, release) filtrati come nella costruzione della rete."""
    cr = common.load("credits.parquet")[["artist_id", "release_id"]].drop_duplicates()
    dim = cr.groupby("release_id").artist_id.size()
    maxc = cfg["network"]["max_credits"]
    ok = dim[(dim >= 2) & (dim <= maxc)].index
    cr = cr[cr.release_id.isin(ok)]
    if decennio is not None:
        rel = pd.read_parquet(RAW / "raw_releases.parquet")[["release_id", "year"]]
        cr = cr.merge(rel, on="release_id")
        cr = cr[(cr.year // 10 * 10) == decennio][["artist_id", "release_id"]]
    a = pd.factorize(cr.artist_id)[0].astype(np.int32)
    r = pd.factorize(cr.release_id)[0].astype(np.int32)
    log.info(f"bipartito: {a.max()+1:,} artisti, {r.max()+1:,} release, "
             f"{len(a):,} crediti")
    return a, r, int(a.max()) + 1, int(r.max()) + 1


def scambia(a, r, rng, n_scambi):
    """Doppi scambi sul grafo bipartito: conserva ESATTAMENTE entrambe le
    distribuzioni di grado.

    Si prendono due crediti (a1,r1) e (a2,r2) e si scambiano le release. Il
    grado di ogni artista e di ogni release resta identico; cambia solo chi sta
    con chi. Lo scambio viene rifiutato se creerebbe un doppione, cioe' se a1
    fosse gia' accreditato su r2 o a2 su r1 — altrimenti la release perderebbe
    un artista e il conto dei gradi si romperebbe.
    """
    a = a.copy()
    r = r.copy()
    presenti = set(zip(a.tolist(), r.tolist()))
    m = len(a)
    i1 = rng.integers(0, m, n_scambi)
    i2 = rng.integers(0, m, n_scambi)
    riusciti = 0
    for k in range(n_scambi):
        x, y = int(i1[k]), int(i2[k])
        if x == y:
            continue
        a1, r1, a2, r2 = a[x], r[x], a[y], r[y]
        if r1 == r2 or a1 == a2:
            continue
        if (a1, r2) in presenti or (a2, r1) in presenti:
            continue
        presenti.discard((a1, r1)); presenti.discard((a2, r2))
        presenti.add((a1, r2)); presenti.add((a2, r1))
        r[x], r[y] = r2, r1
        riusciti += 1
    return a, r, riusciti


def esp_da_bipartito(a, r, n_art):
    """Proietta e restituisce la distribuzione dei partner condivisi per arco."""
    cast = defaultdict(list)
    for ai, ri in zip(a.tolist(), r.tolist()):
        cast[ri].append(ai)
    vic = defaultdict(set)
    for membri in cast.values():
        for i in range(len(membri)):
            for j in range(i + 1, len(membri)):
                u, v = membri[i], membri[j]
                vic[u].add(v)
                vic[v].add(u)
    conta = np.zeros(ESP_MAX + 2, dtype=np.int64)
    archi = 0
    visti = set()
    for u, vs in vic.items():
        for v in vs:
            if u < v:
                if (u, v) in visti:
                    continue
                visti.add((u, v))
                k = len(vic[u] & vic[v])
                conta[min(k, ESP_MAX + 1)] += 1
                archi += 1
    return conta, archi


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4i_proiezione_nulla", cfg)
    if common.exists("proiezione_nulla.parquet") and not force:
        log.info("Fase 4i gia' completata, salto")
        return
    rng = np.random.default_rng(cfg["project"]["seed"])
    righe = []

    for etichetta, dec in (("1940s", 1940), ("1950s", 1950), ("rete intera", None)):
        log.info(f"=== {etichetta} ===")
        a, r, n_art, n_rel = bipartito(cfg, log, dec)

        with Timer(f"{etichetta}: proiezione osservata", log):
            oss, archi_oss = esp_da_bipartito(a, r, n_art)
        log.info(f"  osservata: {archi_oss:,} archi")

        acc = np.zeros(len(oss), dtype=np.float64)
        archi_sim = []
        n_scambi = SCAMBI_PER_ARCO * len(a)
        rip = REPLICHE if dec is not None else 20   # la rete intera costa di piu'
        with Timer(f"{etichetta}: {rip} riproiezioni randomizzate", log):
            for b in range(rip):
                aa, rr, ok = scambia(a, r, rng, n_scambi)
                c, m = esp_da_bipartito(aa, rr, n_art)
                acc += c
                archi_sim.append(m)
                if b == 0:
                    log.info(f"  scambi riusciti: {ok:,} su {n_scambi:,} "
                             f"({ok/n_scambi:.0%})")
        att = acc / rip
        log.info(f"  randomizzata: {np.mean(archi_sim):,.0f} archi in media")

        for k in range(len(oss)):
            if oss[k] or att[k]:
                righe.append({
                    "insieme": etichetta, "esp": k if k <= ESP_MAX else ESP_MAX + 1,
                    "oltre_il_massimo": k > ESP_MAX,
                    "osservati": int(oss[k]), "randomizzati": float(att[k]),
                    "rapporto": oss[k] / att[k] if att[k] else np.nan,
                })
        d = pd.DataFrame(righe)
        common.save(d, "proiezione_nulla.parquet")

    d = pd.DataFrame(righe)
    common.save(d, "proiezione_nulla.parquet")
    common.save_table(d, "t4_proiezione_nulla",
                      "Distribuzione dei partner condivisi per arco: osservata, "
                      "e prodotta riproiettando il grafo bipartito "
                      "artisti-release randomizzato a distribuzioni di grado "
                      "invariate. Nessuna preferenza sociale entra nella "
                      "versione randomizzata: contiene solo il meccanismo")
    pd.set_option("display.width", 200)
    for et in d.insieme.unique():
        log.info(f"\n=== {et} ===\n"
                 + d[d.insieme == et].head(14).round(2).to_string(index=False))
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
