"""FASE 4b — ERGM sulla rete INTEGRALE.

La Fase 4 stimava sottoreti campionate di 1.500 nodi, e l'articolo doveva
dichiarare che le stime valevano solo per quelle. Qui si toglie il limite e si
stima sulla rete intera: 56.915 nodi, 521.438 archi, 1,62 miliardi di diadi.

Due differenze rispetto alla Fase 4, oltre alla dimensione:

* **Nessuno sfoltimento degli archi.** La Fase 4 teneva solo i legami di peso
  almeno 1, per rendere la stima praticabile. Qui ci sono tutti, compresi i
  legami deboli fra crediti "a ombrello". Non e' un dettaglio tecnico: i due
  oggetti rispondono a domande diverse — chi ha collaborato in modo sostanziale
  contro chi e' semplicemente comparso sullo stesso disco.
* **Nessun tempo massimo.** La stima puo' prendersi i giorni che le servono.

Si stima prima la MPLE, che e' sempre calcolabile e arriva in pochi minuti, poi
la MCMLE. La MPLE non e' un ripiego ma nemmeno un sostituto: e' notoriamente
distorta quando la dipendenza fra archi e' forte, ed e' proprio il caso qui
(il coefficiente gwesp vale oltre 3,7). Serve come riferimento e come garanzia
di avere comunque un risultato; la stima da riportare e' la MCMLE.

Non ci sono scale intermedie. Erano previste, ma misurandole si e' visto che
nessun campionamento conserva cio' che conta: la palla di neve pesca il nucleo
denso e porta il grado medio da 18,3 a 53, mentre il campione casuale di nodi
conserva la densita' ma dimezza il clustering, cioe' distrugge proprio i
triangoli che il termine gwesp deve stimare.
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

# Solo la rete intera. Le scale intermedie erano state previste come scala di
# avvicinamento, ma misurandole si e' visto che nessun campionamento conserva
# cio' che conta: la palla di neve pesca il nucleo denso e porta il grado medio
# da 18,3 a 53, mentre il campione casuale di nodi conserva la densita' ma
# dimezza il clustering (da 0,51 a 0,26), cioe' distrugge proprio i triangoli
# che il termine gwesp deve stimare. Un livello intermedio non direbbe nulla
# sulla rete vera, quindi si stima direttamente quella.
SCALE = [None]


def controlli(n: int, cfg) -> dict:
    """Parametri MCMC scalati sulla dimensione della rete.

    Le catene su reti grandi si muovono piu' lentamente fra configurazioni
    indipendenti: l'intervallo fra campioni deve crescere con il numero di
    archi, altrimenti il campione e' numeroso ma autocorrelato, e la stima
    sembra precisa senza esserlo.
    """
    # Parametri tarati sulla MEMORIA, non sulla velocita'.
    #
    # Una prima versione usava venti milioni di diadi per la MPLE e sei catene
    # parallele. Misurando: la matrice di disegno della MPLE occupa da sola
    # circa un gigabyte ogni quattro milioni di diadi, e con PSOCK viene
    # copiata in OGNI worker. Il risultato erano otto processi R per sessanta
    # gigabyte complessivi, con la macchina in swap e gli altri servizi
    # affamati. Un milione di diadi basta ampiamente a inizializzare la stima
    # e costa 2,8 GB di picco.
    #
    # Il campione MCMC scende da diecimila a tremila: per sette parametri e'
    # piu' che sufficiente, purche' l'intervallo resti ampio abbastanza da
    # decorrelare, ed e' l'intervallo — non la numerosita' — a garantire che i
    # campioni siano indipendenti. Due sole catene tengono il totale sotto i
    # dieci gigabyte.
    #
    # Il prezzo e' il tempo, che qui non e' un vincolo.
    return {
        "samplesize": 3_000,
        "burnin": 300_000,
        "interval": 30_000,
        "maxit": 100,
        "mple_samplesize": 1_000_000,
        "parallel": 2,
        "gwesp_decay": cfg["ergm"]["gwesp_decay"],
        # La bonta' di adattamento simula reti intere: su 57.000 nodi ogni
        # simulazione costa quanto una iterazione della stima, e cento
        # simulazioni costerebbero piu' della stima stessa. Sulla rete
        # integrale la GOF viene quindi saltata, e l'articolo deve dichiararlo:
        # si hanno i coefficienti, non la verifica che il modello riproduca le
        # statistiche della rete.
        "gof": n <= 25_000,
        "gof_nsim": 100 if n <= 10_000 else 50,
    }


def memoria_disponibile_gb() -> float:
    """Memoria realmente disponibile, non quella semplicemente 'libera'."""
    for riga in Path("/proc/meminfo").read_text().splitlines():
        if riga.startswith("MemAvailable:"):
            return int(riga.split()[1]) / 1048576
    return 0.0


def verifica_memoria(log, richiesta_gb: float = 14.0) -> None:
    """La stima non parte se non c'e' margine. La macchina ospita altri
    servizi, e mandarla in swap li danneggia mentre rallenta anche noi: su
    disco rotante una catena MCMC che swappa perde piu' di quanto guadagni
    qualunque parallelismo."""
    disp = memoria_disponibile_gb()
    log.info(f"memoria disponibile: {disp:.0f} GB (richieste ~{richiesta_gb:.0f})")
    if disp < richiesta_gb:
        raise SystemExit(
            f"Memoria insufficiente: {disp:.0f} GB disponibili, ne servono "
            f"almeno {richiesta_gb:.0f}. Liberare memoria o ridurre "
            f"`parallel` e `mple_samplesize` in controlli().")


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
    # Nessun tempo massimo: e' esattamente cio' che si vuole poter spendere.
    # L'output di R viene trascritto riga per riga mentre arriva, invece che
    # raccolto alla fine: su una stima che puo' durare giorni, sapere a quale
    # iterazione si e' arrivati e' la differenza fra sorvegliare e sperare.
    with open(d / "R.log", "w", buffering=1) as fh:
        p = subprocess.Popen(
            [str(rb), str(ROOT / "R" / "ergm_full.R"), str(d),
             str(cfg["project"]["seed"])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1)
        for riga in p.stdout:
            riga = riga.rstrip()
            fh.write(riga + "\n")
            if riga.strip():
                log.info(f"  R| {riga}")
        p.wait()
    if p.returncode != 0:
        log.error(f"Rscript rc={p.returncode}")
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
    verifica_memoria(log)
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
