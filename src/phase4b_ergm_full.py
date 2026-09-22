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
import sys, json, re, subprocess, shutil, time
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

# Le specifiche da provare, in ordine. gwesp(0.25) e' quella prevista dal
# disegno, ma sulla rete integrale non converge: lo step dell'ottimizzatore
# crolla da 0,48 a 0,005 alla seconda iterazione, in due tentativi
# indipendenti con parametri MCMC diversi. E' la firma della quasi-degenerazione.
#
# Le alternative seguono la diagnosi. Con decay basso gwesp si comporta quasi
# come un conteggio di triangoli, che e' la forma piu' instabile; alzandolo si
# avvicina al conteggio di partner condivisi, molto meglio condizionato. Se
# non basta, si aggiunge un termine sulla distribuzione dei gradi, che in
# letteratura stabilizza i modelli con gwesp vincolando l'altra dimensione
# lungo cui il modello puo' degenerare. Come ultima risorsa si cambia
# algoritmo: la Stochastic-Approximation non insegue il massimo della
# verosimiglianza per passi, quindi non soffre del collasso dello step.
VARIANTI = [
    ("gwesp050", "gwesp(0.5, fixed = TRUE)", "MCMLE"),
    ("gwesp075", "gwesp(0.75, fixed = TRUE)", "MCMLE"),
    ("gwesp025_gwdeg", "gwesp(0.25, fixed = TRUE) + gwdegree(0.5, fixed = TRUE)", "MCMLE"),
    ("gwesp050_stocapp", "gwesp(0.5, fixed = TRUE)", "Stochastic-Approximation"),
]

# Soglie per l'abbandono precoce. Aspettare cento iterazioni una stima che ha
# gia' mostrato il collasso costa giorni e non produce nulla: se lo step resta
# sotto la soglia per piu' iterazioni consecutive, si passa alla variante
# successiva.
STEP_MINIMO = 0.02
# Sotto questa soglia la stima viene interrotta: sulla macchina girano
# altri servizi, e mandarla in swap danneggia loro mentre rallenta anche
# noi. La memoria va sorvegliata durante, non solo all'avvio: e' durante
# che cresce.
MEMORIA_MINIMA_GB = 12
COLLASSI_TOLLERATI = 3
ORE_MASSIME = 30


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
        "dipendenza": None,   # riempito dalla variante
        "metodo": "MCMLE",    # idem
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


def prepara(G: nx.Graph, pop: pd.DataFrame, nome: str, cfg,
            dipendenza: str = "gwesp(0.25, fixed = TRUE)",
            metodo: str = "MCMLE") -> Path:
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
    c = controlli(G.number_of_nodes(), cfg)
    c["dipendenza"], c["metodo"] = dipendenza, metodo
    (d / "control.json").write_text(json.dumps(c))
    return d


# La riga che interessa ha la forma "1 Optimizing with step length 0.5774.".
# Il punto finale chiude la frase e NON fa parte del numero: una prima versione
# lo includeva nel gruppo catturato, float() sollevava ValueError, l'eccezione
# usciva dal ciclo di lettura e uccideva l'orchestratore — lasciando poi R a
# morire di SIGPIPE. La sorveglianza aveva interrotto proprio la stima che
# doveva proteggere, e per giunta una che stava andando bene.
STEP_RE = re.compile(r"step length\s+([0-9]*\.?[0-9]+)")


def leggi_passo(riga: str, log) -> float | None:
    """Estrae il passo dell'ottimizzatore, se la riga lo contiene.

    Non solleva mai: la sorveglianza e' un ausilio, e nessun errore di lettura
    deve poter fermare una stima che dura giorni.
    """
    m = STEP_RE.search(riga)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        log.warning(f"  passo non interpretabile: {m.group(1)!r}")
        return None


def leggi_righe(p, fh, log):
    """Righe dell'output di R, trascritte sul file e restituite una a una.

    Qualunque errore di lettura viene registrato e ingoiato. La sorveglianza
    e' un ausilio: non deve poter interrompere la stima che sorveglia. E'
    esattamente quello che era gia' successo una volta, con una regex che
    catturava il punto finale della frase e faceva fallire float(), uccidendo
    una stima che stava andando bene.
    """
    try:
        for riga in p.stdout:
            riga = riga.rstrip()
            try:
                fh.write(riga + "\n")
            except Exception as e:
                log.warning(f"  scrittura del log fallita: {e!r}")
            if riga.strip():
                log.info(f"  R| {riga}")
            yield riga
    except Exception as e:
        log.error(f"  lettura dell'output di R interrotta: {e!r}")


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
    collassi, abbandonata = 0, None
    with open(d / "R.log", "w", buffering=1) as fh:
        p = subprocess.Popen(
            [str(rb), str(ROOT / "R" / "ergm_full.R"), str(d),
             str(cfg["project"]["seed"])],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
            # un byte non decodificabile nell'output di R non deve far cadere
            # una stima di giorni
            errors="replace",
            # R in una sessione sua: un segnale diretto all'orchestratore non
            # se lo porta dietro, e resta il tempo di chiuderlo con ordine
            start_new_session=True)
        ultimo_battito = time.time()
        for riga in leggi_righe(p, fh, log):
            # sorveglianza: uno step minuscolo, ripetuto, significa che il
            # modello genera reti lontanissime da quella osservata e che
            # l'ottimizzatore non ha spazio per muoversi
            # Battito: un log puo' restare muto per mezz'ora fra due
            # iterazioni, e senza questo non si distingue "lento" da "morto".
            if time.time() - ultimo_battito > 900:
                ultimo_battito = time.time()
                mem = memoria_disponibile_gb()
                log.info(f"  [battito] {(time.time()-t0)/3600:.1f}h trascorse, "
                         f"{mem:.0f} GB liberi")
                if mem < MEMORIA_MINIMA_GB:
                    abbandonata = (f"memoria scesa a {mem:.0f} GB, sotto la "
                                   f"soglia di {MEMORIA_MINIMA_GB}")
                    log.warning(f"  ABBANDONO: {abbandonata}")
                    p.terminate()
                    break
            passo = leggi_passo(riga, log)
            if passo is not None:
                collassi = collassi + 1 if passo < STEP_MINIMO else 0
                if collassi >= COLLASSI_TOLLERATI:
                    abbandonata = (f"step sotto {STEP_MINIMO} per "
                                   f"{collassi} iterazioni consecutive")
                    log.warning(f"  ABBANDONO: {abbandonata}")
                    p.terminate()
                    break
            if (time.time() - t0) / 3600 > ORE_MASSIME:
                abbandonata = f"superate {ORE_MASSIME} ore"
                log.warning(f"  ABBANDONO: {abbandonata}")
                p.terminate()
                break
        try:
            p.wait(timeout=60)
        except subprocess.TimeoutExpired:
            p.kill()
    if abbandonata:
        (d / "abbandonata.txt").write_text(abbandonata)
    elif p.returncode != 0:
        log.error(f"Rscript rc={p.returncode}")
    log.info(f"  tempo totale: {(time.time()-t0)/3600:.2f} ore")
    f = d / "summary.json"
    return json.loads(f.read_text()) if f.exists() else None


def raccogli(log):
    """Unisce i coefficienti delle varianti concluse.

    Protetta per singolo file: un CSV troncato — possibile se una variante e'
    stata interrotta mentre scriveva — non deve impedire di raccogliere le
    altre, ne' fermare il ciclo.
    """
    righe = []
    for f in sorted(MODELS.glob("*/coef.csv")):
        try:
            righe.append(pd.read_csv(f).assign(scala=f.parent.name))
        except Exception as e:
            log.warning(f"  {f.parent.name}/coef.csv illeggibile: {e!r}")
    if not righe:
        return
    coef = pd.concat(righe, ignore_index=True)
    try:
        common.save(coef, "ergm_full_coef.parquet")
        common.save_table(coef, "t4_ergm_integrale_coefficienti",
                          "Coefficienti ERGM sulla rete integrale, per specifica "
                          "del termine di dipendenza")
    except Exception as e:
        log.warning(f"  salvataggio dei coefficienti fallito: {e!r}")
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

    esiti = []
    for nome, dipendenza, metodo in VARIANTI:
        d = MODELS / nome
        if (d / "summary.json").exists() and not force:
            log.info(f"--- {nome}: gia' stimata, salto")
            continue
        log.info(f"=== variante {nome}: {dipendenza} [{metodo}] ===")
        # Ogni variante e' isolata: un errore imprevisto in un tentativo non
        # puo' costare l'intera sequenza. E' il caso che si e' gia' verificato.
        s = None
        try:
            d = prepara(G, pop, nome, cfg, dipendenza, metodo)
            with Timer(f"ERGM {nome}", log):
                s = esegui(d, cfg, log)
        except Exception as e:
            log.error(f"  {nome}: errore imprevisto {e!r}", exc_info=True)
        riuscita = bool(s and s.get("mcmle"))
        esiti.append({"variante": nome, "dipendenza": dipendenza,
                      "metodo": metodo, "convergenza": riuscita,
                      "abbandonata": (d / "abbandonata.txt").exists(),
                      "motivo": (d / "abbandonata.txt").read_text()
                                if (d / "abbandonata.txt").exists() else None,
                      "ore": round(s.get("ore", 0), 2) if s else None})
        try:
            common.save(pd.DataFrame(esiti), "ergm_full_esiti.parquet")
            raccogli(log)
        except Exception as e:
            log.warning(f"  raccolta intermedia fallita: {e!r}")
        if riuscita:
            log.info(f"=== {nome} CONVERGE: la rete integrale e' stimata ===")
            break
        log.warning(f"--- {nome} non converge, passo alla variante successiva")

    df = pd.DataFrame(esiti)
    if len(df):
        common.save_table(df, "t4_ergm_integrale_varianti",
                          "Specifiche provate sulla rete integrale ed esito di "
                          "ciascuna")
        log.info("\n" + df.to_string(index=False))
    raccogli(log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
