"""FASE 4b — ERGM sulla rete integrale, per scala crescente.

La Fase 4 stimava sottoreti campionate di 1.500 nodi, e il paper doveva
dichiarare che le stime valevano solo per quelle. Qui si toglie quel limite:
si stima la stessa specifica su reti via via piu' grandi, fino all'intera rete
di collaborazione (circa 59.000 nodi e 524.000 archi).

Le scale intermedie non sono un ripiego. Sono la prova di rappresentativita':
se il coefficiente di omofilia femminile resta stabile passando da 1.500 a
59.000 nodi, allora le stime su sottorete della Fase 4 erano informative; se
si muove, lo si vede e lo si dichiara. In entrambi i casi e' un risultato, non
un'approssimazione.

Ogni scala scrive i propri risultati appena finisce, quindi un'interruzione al
livello piu' grande non porta via i precedenti.
"""
from __future__ import annotations
import sys, json, subprocess, shutil, time
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

MODELS = ROOT / "data" / "ergm_full"

# Le scale da percorrere. `None` significa la rete intera.
SCALE = [3_000, 10_000, 25_000, None]


def controlli(n: int, cfg) -> dict:
    """Parametri MCMC scalati sulla dimensione della rete.

    Le catene su reti grandi si muovono piu' lentamente fra configurazioni
    indipendenti: l'intervallo fra campioni deve crescere con il numero di
    archi, altrimenti il campione e' numeroso ma autocorrelato, e la stima
    sembra precisa senza esserlo.
    """
    scala = max(1.0, n / 1500)
    return {
        "samplesize": int(min(4000 * scala ** 0.5, 20000)),
        "burnin": int(min(20000 * scala, 2_000_000)),
        "interval": int(min(1000 * scala, 100_000)),
        "maxit": 60,
        "mple_samplesize": 5_000_000,
        "parallel": 4 if n > 5000 else 0,
        "gwesp_decay": cfg["ergm"]["gwesp_decay"],
        # la GOF simula reti intere: sopra una certa taglia costa piu' della
        # stima stessa, e la si limita alle scale dove e' sostenibile
        "gof": n <= 25_000,
        "gof_nsim": 100 if n <= 10_000 else 50,
    }


def rete_completa(cfg, log):
    """Rete di collaborazione senza i nodi di genere indeterminato.

    A differenza della Fase 4 non si sfoltiscono gli archi deboli: l'obiettivo
    dichiarato e' la rete integrale.
    """
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    keep = pop[pop.gender.isin(["M", "F", "mixed"])]
    ids = set(keep.artist_id)
    E = edges[edges.u.isin(ids) & edges.v.isin(ids)]
    G = nx.Graph()
    G.add_nodes_from(ids)
    G.add_weighted_edges_from(E[["u", "v", "w"]].itertuples(index=False, name=None))
    G = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    comps = sorted(nx.connected_components(G), key=len, reverse=True)
    G = G.subgraph(comps[0]).copy()
    log.info(f"rete integrale: {G.number_of_nodes():,} nodi, "
             f"{G.number_of_edges():,} archi, "
             f"densita {nx.density(G):.2e}, "
             f"{G.number_of_nodes()*(G.number_of_nodes()-1)//2:,} diadi")
    return G, pop


def campiona(G: nx.Graph, n_max: int, seed: int, log) -> nx.Graph:
    """Campione a palla di neve. Conserva i triangoli, che un campione casuale
    di nodi distruggerebbe proprio mentre si stima un termine di chiusura."""
    if G.number_of_nodes() <= n_max:
        return G
    rng = np.random.default_rng(seed)
    nodi = list(G.nodes())
    seen = {nodi[int(rng.integers(len(nodi)))]}
    frontiera = list(seen)
    while frontiera and len(seen) < n_max:
        nxt = []
        for u in frontiera:
            for v in G.neighbors(u):
                if v not in seen:
                    seen.add(v)
                    nxt.append(v)
                    if len(seen) >= n_max:
                        break
            if len(seen) >= n_max:
                break
        frontiera = nxt
    H = G.subgraph(seen).copy()
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    return H.subgraph(comps[0]).copy()


def prepara(G: nx.Graph, pop: pd.DataFrame, nome: str, cfg) -> Path:
    d = MODELS / nome
    d.mkdir(parents=True, exist_ok=True)
    attrs = pop.set_index("artist_id")
    nodes = pd.DataFrame({"artist_id": list(G.nodes())}).join(attrs, on="artist_id")
    nodes["log_nrel"] = np.log(nodes.n_release.fillna(1).clip(lower=1))
    nodes["cohort_decade"] = nodes.cohort_decade.astype("Int64").astype(str).fillna("NA")
    nodes["musical_genre"] = nodes.musical_genre.fillna("Unknown")
    nodes[["artist_id", "gender", "musical_genre", "cohort_decade", "log_nrel"]] \
        .to_csv(d / "nodes.csv", index=False)
    nx.to_pandas_edgelist(G, source="u", target="v")[["u", "v"]] \
        .to_csv(d / "edges.csv", index=False)
    (d / "control.json").write_text(json.dumps(controlli(G.number_of_nodes(), cfg)))
    return d


def esegui(d: Path, cfg, log) -> dict | None:
    rb = ROOT / cfg["ergm"]["r_env"] / "bin" / "Rscript"
    if not rb.exists():
        rb = Path(shutil.which("Rscript") or "")
    if not rb.exists():
        log.error("Rscript non trovato")
        return None
    t0 = time.time()
    # nessun tempo massimo: e' esattamente cio' che si vuole poter spendere
    p = subprocess.run([str(rb), str(ROOT / "R" / "ergm_full.R"), str(d),
                        str(cfg["project"]["seed"])],
                       capture_output=True, text=True)
    (d / "R.log").write_text(p.stdout + "\n---STDERR---\n" + p.stderr)
    log.info(p.stdout.strip()[-2000:] or "(nessun output)")
    if p.returncode != 0:
        log.error(f"Rscript rc={p.returncode}: {p.stderr[-1500:]}")
    log.info(f"  tempo totale: {(time.time()-t0)/3600:.2f} ore")
    f = d / "summary.json"
    return json.loads(f.read_text()) if f.exists() else None


def raccogli(log):
    righe = [pd.read_csv(f).assign(scala=f.parent.name)
             for f in sorted(MODELS.glob("*/coef.csv"))]
    if not righe:
        return
    coef = pd.concat(righe, ignore_index=True)
    common.save(coef, "ergm_full_coef.parquet")
    common.save_table(coef, "t4_ergm_integrale_coefficienti",
                      "Coefficienti ERGM al crescere della dimensione della rete, "
                      "fino alla rete integrale")
    m = coef[(coef.metodo == "MCMLE") &
             coef.term.str.contains("nodematch.gender|gwesp")]
    if len(m):
        piv = m.pivot_table(index="term", columns="n_nodi", values="estimate")
        log.info("coefficienti al crescere di n:\n" + piv.round(3).to_string())
    return coef


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4b_ergm_full", cfg)
    MODELS.mkdir(parents=True, exist_ok=True)
    G, pop = rete_completa(cfg, log)

    for scala in SCALE:
        nome = "integrale" if scala is None else f"n{scala}"
        d = MODELS / nome
        if (d / "summary.json").exists() and not force:
            log.info(f"--- {nome}: gia' stimata, salto")
            continue
        H = G if scala is None else campiona(G, scala, cfg["project"]["seed"], log)
        log.info(f"--- {nome}: {H.number_of_nodes():,} nodi, "
                 f"{H.number_of_edges():,} archi "
                 f"(grado medio {2*H.number_of_edges()/H.number_of_nodes():.1f})")
        d = prepara(H, pop, nome, cfg)
        with Timer(f"ERGM {nome}", log):
            s = esegui(d, cfg, log)
        if s is None or not s.get("mcmle"):
            log.error(f"{nome}: MCMLE non converge; si prosegue comunque")
        raccogli(log)

    raccogli(log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
