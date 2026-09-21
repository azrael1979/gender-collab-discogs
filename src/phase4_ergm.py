"""FASE 4 — ERGM (R + statnet) sulle reti di collaborazione.

Sulla rete intera (~100k nodi, ~2 milioni di archi) un ERGM non converge: il
campionamento MCMC su uno spazio di quella dimensione non e' praticabile e la
letteratura lo sconsiglia esplicitamente. Si dichiara il limite e si stima su
sottoreti, come previsto dal disegno:

  * i cinque generi musicali piu' popolosi, separatamente;
  * pre-2000 e post-2000, con test della differenza fra coefficienti;
  * un campione a palla di neve della rete complessiva, come riferimento.

Dall'ERGM si escludono i nodi con genere sessuale `unknown`: tenerli come
categoria a se' produrrebbe un termine di omofilia spurio, che misurerebbe la
struttura della copertura dei dati invece che quella delle collaborazioni.
L'incertezza su quei nodi e' trattata in Fase 5 con il Monte Carlo.
"""
from __future__ import annotations
import sys, json, subprocess, shutil
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

MODELS = ROOT / "data" / "ergm"


def r_binary(cfg) -> Path | None:
    p = ROOT / cfg["ergm"]["r_env"] / "bin" / "Rscript"
    return p if p.exists() else (Path(shutil.which("Rscript")) if shutil.which("Rscript") else None)


def snowball(G: nx.Graph, max_nodes: int, seed: int,
             max_edges: int | None = None) -> nx.Graph:
    """Campione a palla di neve: si parte da un nodo a caso e si espande per
    livelli. Conserva la struttura locale molto meglio di un campione casuale
    di nodi, che spezzerebbe proprio i triangoli che il termine gwesp deve
    misurare.

    Il tetto sugli ARCHI, oltre a quello sui nodi, e' necessario perche' il
    costo e la stabilita' numerica dell'ERGM dipendono dalla densita' piu' che
    dal numero di nodi: senza, le sottoreti dei generi piu' affollati
    arriverebbero al modello molto piu' dense di quelle degli altri.
    """
    if G.number_of_nodes() <= max_nodes and (
            max_edges is None or G.number_of_edges() <= max_edges):
        return G
    rng = np.random.default_rng(seed)
    nodes = list(G.nodes())
    start = nodes[int(rng.integers(len(nodes)))]
    seen, frontier = {start}, [start]
    while frontier and len(seen) < max_nodes:
        nxt = []
        for u in frontier:
            for v in G.neighbors(u):
                if v not in seen:
                    seen.add(v)
                    nxt.append(v)
                    if len(seen) >= max_nodes:
                        break
            if len(seen) >= max_nodes:
                break
        if max_edges is not None and G.subgraph(seen).number_of_edges() >= max_edges:
            break
        frontier = nxt
    H = G.subgraph(seen).copy()
    # se il budget di archi e' comunque superato, si toglie qualche nodo dai
    # piu' connessi finche' non rientra
    if max_edges is not None:
        while H.number_of_edges() > max_edges and H.number_of_nodes() > 200:
            hub = max(H.degree, key=lambda x: x[1])[0]
            H.remove_node(hub)
    H = H.subgraph([n for n, d in H.degree() if d > 0]).copy()
    if H.number_of_nodes() == 0:
        return H
    comps = sorted(nx.connected_components(H), key=len, reverse=True)
    return H.subgraph(comps[0]).copy()


def prepare(G: nx.Graph, pop: pd.DataFrame, name: str, cfg) -> Path | None:
    d = MODELS / name
    d.mkdir(parents=True, exist_ok=True)
    attrs = pop.set_index("artist_id")
    nodes = pd.DataFrame({"artist_id": list(G.nodes())})
    nodes = nodes.join(attrs, on="artist_id")
    nodes["log_nrel"] = np.log(nodes.n_release.fillna(1).clip(lower=1))
    nodes["cohort_decade"] = nodes.cohort_decade.astype("Int64").astype(str).fillna("NA")
    nodes["musical_genre"] = nodes.musical_genre.fillna("Unknown")
    nodes = nodes[["artist_id", "gender", "musical_genre", "cohort_decade", "log_nrel"]]
    if nodes.gender.nunique() < 2 or len(nodes) < 50:
        return None
    edges = nx.to_pandas_edgelist(G, source="u", target="v")[["u", "v"]]
    nodes.to_csv(d / "nodes.csv", index=False)
    edges.to_csv(d / "edges.csv", index=False)
    # Dentro una sottorete di un solo genere musicale, nodematch("musical_genre")
    # e' una combinazione lineare di edges: il modello sarebbe NON IDENTIFICATO.
    # Lo stesso vale per qualunque attributo costante nella sottorete. I termini
    # corrispondenti vanno quindi omessi, e R lo sa da qui.
    (d / "control.json").write_text(json.dumps({
        **cfg["ergm"]["mcmc"],
        "gwesp_decay": cfg["ergm"]["gwesp_decay"],
        "usa_genere": bool(nodes.musical_genre.nunique() > 1),
        "usa_coorte": bool(nodes.cohort_decade.nunique() > 1)}))
    return d


def run_r(d: Path, cfg, log) -> dict | None:
    rb = r_binary(cfg)
    if rb is None:
        log.error("Rscript non trovato: ERGM non eseguibile")
        return None
    tmax = cfg["ergm"].get("timeout_s", 1800)
    try:
        with Timer(f"ERGM {d.name}", log):
            p = subprocess.run([str(rb), str(ROOT / "R" / "ergm_models.R"), str(d),
                                str(cfg["project"]["seed"])],
                               capture_output=True, text=True, timeout=tmax)
    except subprocess.TimeoutExpired:
        # R scrive i risultati dopo ogni modello: se il tempo e' scaduto mentre
        # stimava il piu' pesante, quelli gia' conclusi sono comunque su disco
        # e vanno raccolti invece che buttati.
        (d / "R.log").write_text(f"TIMEOUT dopo {tmax}s")
        f = d / "summary.json"
        if f.exists():
            parz = json.loads(f.read_text())
            parz["timeout"] = True
            f.write_text(json.dumps(parz))
            log.warning(f"{d.name}: tempo massimo superato ({tmax}s); "
                        f"si tengono i modelli gia' conclusi: "
                        f"{', '.join(np.atleast_1d(parz.get('modelli', [])))}")
            return parz
        log.error(f"{d.name}: oltre il tempo massimo ({tmax}s), nessun risultato")
        return None
    (d / "R.log").write_text(p.stdout + "\n---STDERR---\n" + p.stderr)
    log.info(p.stdout.strip()[-1500:] or "(nessun output)")
    if p.returncode != 0:
        log.error(f"Rscript rc={p.returncode}: {p.stderr[-1500:]}")
        return None
    f = d / "summary.json"
    return json.loads(f.read_text()) if f.exists() else None


def subnets(pop: pd.DataFrame, edges: pd.DataFrame, cfg, log):
    """Genera le sottoreti da stimare, gia' ripulite dei nodi `unknown`."""
    keep = pop[pop.gender.isin(["M", "F", "mixed"])]
    ids = set(keep.artist_id)
    E = edges[edges.u.isin(ids) & edges.v.isin(ids)]
    log.info(f"rete senza nodi 'unknown': {len(ids):,} nodi, {len(E):,} archi "
             f"(erano {len(pop):,} e {len(edges):,})")
    wmin = cfg["ergm"].get("min_edge_weight_ergm", 0.0)
    if wmin > 0:
        n0 = len(E)
        E = E[E.w >= wmin]
        log.info(f"sfoltimento per l'ERGM (peso >= {wmin}): {n0:,} -> {len(E):,} archi")
    G = nx.Graph()
    G.add_nodes_from(ids)
    G.add_weighted_edges_from(E[["u", "v", "w"]].itertuples(index=False, name=None))

    out = {}
    top = keep[keep.musical_genre != "Unknown"].musical_genre.value_counts() \
        .head(cfg["ergm"]["top_genres_n"]).index
    for g in top:
        sub = set(keep[keep.musical_genre == g].artist_id)
        H = G.subgraph(sub).copy()
        H = H.subgraph([n for n, d in H.degree() if d > 0]).copy()
        if H.number_of_nodes() < 100:
            continue
        comps = sorted(nx.connected_components(H), key=len, reverse=True)
        out[f"genere_{g.replace('/', '-').replace(' ', '_').replace(',', '')}"] = \
            H.subgraph(comps[0]).copy()
    for era in ["pre2000", "post2000"]:
        sub = set(keep[keep.era == era].artist_id)
        H = G.subgraph(sub).copy()
        H = H.subgraph([n for n, d in H.degree() if d > 0]).copy()
        if H.number_of_nodes() >= 100:
            comps = sorted(nx.connected_components(H), key=len, reverse=True)
            out[f"epoca_{era}"] = H.subgraph(comps[0]).copy()
    Gc = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    comps = sorted(nx.connected_components(Gc), key=len, reverse=True)
    out["complessiva"] = Gc.subgraph(comps[0]).copy()
    return out


def coef_diff_test(coef: pd.DataFrame, log) -> pd.DataFrame:
    """Test di Paternoster sulla differenza fra coefficienti pre/post 2000."""
    a = coef[(coef.rete == "epoca_pre2000")]
    b = coef[(coef.rete == "epoca_post2000")]
    if a.empty or b.empty:
        return pd.DataFrame()
    m = a.merge(b, on=["model", "term"], suffixes=("_pre", "_post"))
    m["differenza"] = m.estimate_post - m.estimate_pre
    m["se_diff"] = np.sqrt(m.se_pre ** 2 + m.se_post ** 2)
    m["z"] = m.differenza / m.se_diff
    m["p"] = 2 * (1 - pd.Series(np.abs(m.z)).apply(
        lambda z: 0.5 * (1 + np.math.erf(z / np.sqrt(2)))))
    out = m[["model", "term", "estimate_pre", "se_pre", "estimate_post", "se_post",
             "differenza", "se_diff", "z", "p"]]
    common.save_table(out, "t4_ergm_differenza_epoche",
                      "Test della differenza fra i coefficienti ERGM pre-2000 e "
                      "post-2000 (test di Paternoster)")
    log.info("\n" + out[out.term.str.contains("gender|nodemix", case=False)]
             .to_string(index=False))
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4_ergm", cfg)
    if not cfg["ergm"]["enabled"]:
        log.warning("ERGM disabilitato da config")
        return
    if common.exists("ergm_coef.parquet") and not force:
        log.info("Fase 4 gia' completata, salto")
        return
    rb = r_binary(cfg)
    log.info(f"Rscript: {rb}")
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    nets = subnets(pop, edges, cfg, log)

    rows, summaries = [], []
    for name, G in nets.items():
        n0 = G.number_of_nodes()
        H = snowball(G, cfg["ergm"]["max_nodes_per_model"], cfg["project"]["seed"],
                     cfg["ergm"].get("max_edges_per_model"))
        campionata = H.number_of_nodes() < n0
        log.info(f"--- {name}: {n0:,} nodi -> {H.number_of_nodes():,} "
                 f"({'campione a palla di neve' if campionata else 'rete intera'}), "
                 f"{H.number_of_edges():,} archi")
        d = prepare(H, pop, name, cfg)
        if d is None:
            log.warning(f"{name}: sottorete inadatta, salto")
            continue
        s = run_r(d, cfg, log)
        if s is None or not s.get("converged"):
            log.error(f"{name}: ERGM NON CONVERGE")
            summaries.append({"rete": name, "nodi_originali": n0,
                              "nodi_stimati": H.number_of_nodes(),
                              "archi": H.number_of_edges(),
                              "campionata": campionata, "convergenza": False})
            continue
        c = pd.read_csv(d / "coef.csv")
        c["rete"] = name
        rows.append(c)
        summaries.append({"rete": name, "nodi_originali": n0,
                          "nodi_stimati": H.number_of_nodes(),
                          "archi": H.number_of_edges(), "campionata": campionata,
                          "convergenza": True,
                          "modelli_convergenti": ", ".join(
                              [str(x) for x in np.atleast_1d(s.get("modelli", []))]),
                          "gwesp_converge": bool(s.get("gwesp_ok")),
                          "parziale": bool(s.get("parziale") or s.get("timeout")),
                          "solo_mple": bool(np.atleast_1d(s.get("solo_mple"))[0]),
                          "aic": float(np.atleast_1d(s.get("aic"))[0]),
                          "gof": bool(s.get("gof"))})
    if not rows:
        log.error("nessun ERGM stimato: la fase degrada, vedi report")
        common.save(pd.DataFrame(summaries), "ergm_summary.parquet")
        return
    coef = pd.concat(rows, ignore_index=True)
    common.save(coef, "ergm_coef.parquet")
    # diagnostica MCMC, raccolta da tutte le sottoreti
    mcs = []
    for d in sorted(MODELS.glob("*/mcmc.csv")):
        m = pd.read_csv(d)
        m["rete"] = d.parent.name
        mcs.append(m)
    if mcs:
        mc = pd.concat(mcs, ignore_index=True)
        common.save(mc, "ergm_mcmc.parquet")
        common.save_table(mc, "t4_ergm_mcmc",
                          "Diagnostica MCMC per termine e sottorete: media, "
                          "deviazione e dimensione efficace del campione")
    common.save(pd.DataFrame(summaries), "ergm_summary.parquet")
    common.save_table(coef, "t4_ergm_coefficienti",
                      "Coefficienti ERGM per sottorete (M1 nodematch, M2 nodemix)")
    common.save_table(pd.DataFrame(summaries), "t4_ergm_sintesi",
                      "Sintesi delle stime ERGM: dimensione, campionamento, convergenza")
    coef_diff_test(coef, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
