"""FASE 4c — omofilia sulla rete INTEGRALE senza ERGM.

Perche' esiste questa fase
--------------------------
L'ERGM con termine di chiusura triadica non converge sulla rete integrale:
il passo dell'ottimizzatore crolla e le iterazioni raddoppiano di durata, in
tutte le parametrizzazioni provate. E' il problema di degenerazione noto degli
ERGM su reti grandi e molto clusterizzate, e non dipende dall'implementazione.

Qui si risponde alla stessa domanda con due metodi che scalano per costruzione,
ciascuno con un limite diverso — e i limiti non si sovrappongono, il che e' il
motivo per cui vale la pena averli entrambi.

**A. Logit diadico con campionamento caso-controllo.**
Si modella la probabilita' che una coppia sia collegata, in funzione della
concordanza di genere, di genere musicale e di coorte, e dell'attivita' dei due
artisti. Le diadi sono 1,6 miliardi: si prendono tutte quelle connesse e un
campione casuale di quelle non connesse, correggendo l'intercetta per il
rapporto di campionamento — la correzione classica dei disegni caso-controllo,
che lascia inalterati i coefficienti. Gli errori standard vengono da un
bootstrap sui NODI, non sulle diadi: due diadi che condividono un artista non
sono indipendenti, e ignorarlo darebbe intervalli falsamente stretti.
*Limite*: assume che le diadi siano indipendenti date le covariate. Non lo sono
— ed e' esattamente cio' che l'ERGM avrebbe corretto.

**B. Test di permutazione tipo QAP.**
Si permutano le etichette di genere sui nodi tenendo fissa la rete, e si guarda
dove cade l'omofilia osservata nella distribuzione cosi' generata. Non stima
nulla: verifica. Poiche' la struttura della rete resta identica a ogni
permutazione, la chiusura triadica, la distribuzione dei gradi e ogni altra
proprieta' strutturale sono automaticamente tenute costanti. E' il pregio che
il logit non ha.
*Limite*: risponde "quanto e' improbabile sotto il caso", non "di quanto
aumenta la probabilita' di un legame".

Insieme coprono quasi tutto cio' che l'ERGM avrebbe dato. Cio' che resta fuori
e' la stima congiunta di omofilia e chiusura, e il report deve dirlo.
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

# Quante non-connesse per ogni connessa. Cinque e' abbondante: oltre, gli
# errori standard migliorano in modo trascurabile e il campione diventa
# ingombrante.
CONTROLLI_PER_CASO = 5
BOOTSTRAP_B = 200
PERMUTAZIONI = 1000


def rete(cfg, log):
    pop = common.load("population_gender.parquet")
    edges = common.load("edges_all.parquet")
    keep = pop[pop.gender.isin(["M", "F", "mixed"])]
    ids = set(keep.artist_id)
    E = edges[edges.u.isin(ids) & edges.v.isin(ids)]
    G = nx.Graph()
    G.add_nodes_from(ids)
    G.add_weighted_edges_from(E[["u", "v", "w"]].itertuples(index=False, name=None))
    G = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    attrs = pop.set_index("artist_id")
    log.info(f"rete integrale: {G.number_of_nodes():,} nodi, "
             f"{G.number_of_edges():,} archi")
    return G, attrs


def _covariate(u, v, gen, genere_mus, coorte, lognrel):
    """Covariate di una diade, nella stessa forma dei termini ERGM."""
    return {
        "same_F": (gen[u] == "F") & (gen[v] == "F"),
        "same_M": (gen[u] == "M") & (gen[v] == "M"),
        "same_mixed": (gen[u] == "mixed") & (gen[v] == "mixed"),
        "same_genre": genere_mus[u] == genere_mus[v],
        "same_cohort": coorte[u] == coorte[v],
        "sum_lognrel": lognrel[u] + lognrel[v],
    }


def campiona_diadi(G, attrs, seed, log):
    """Tutte le diadi connesse, piu' un campione di quelle non connesse."""
    rng = np.random.default_rng(seed)
    nodi = np.array(sorted(G.nodes()))
    pos = {a: i for i, a in enumerate(nodi)}
    a = attrs.loc[nodi]
    gen = a.gender.values
    gmu = a.musical_genre.fillna("Unknown").values
    coh = a.cohort_decade.astype("Int64").astype(str).fillna("NA").values
    lnr = np.log(a.n_release.fillna(1).clip(lower=1)).values

    casi = np.array([(pos[u], pos[v]) for u, v in G.edges()])
    n_ctrl = len(casi) * CONTROLLI_PER_CASO
    log.info(f"diadi connesse: {len(casi):,}; controlli da estrarre: {n_ctrl:,}")

    # estrazione con rifiuto: le connesse sono lo 0,03% del totale, quindi
    # pescare a caso e scartare le poche collisioni e' piu' semplice e veloce
    # che costruire l'insieme complementare
    archi = set(map(tuple, np.sort(casi, axis=1)))
    ctrl, n = [], len(nodi)
    while len(ctrl) < n_ctrl:
        manca = n_ctrl - len(ctrl)
        i = rng.integers(0, n, manca * 2)
        j = rng.integers(0, n, manca * 2)
        ok = i != j
        cand = np.sort(np.column_stack([i[ok], j[ok]]), axis=1)
        for x, y in cand:
            if (x, y) not in archi:
                ctrl.append((x, y))
                if len(ctrl) >= n_ctrl:
                    break
    ctrl = np.array(ctrl)

    tutte = np.vstack([casi, ctrl])
    y = np.concatenate([np.ones(len(casi)), np.zeros(len(ctrl))])
    u, v = tutte[:, 0], tutte[:, 1]
    X = pd.DataFrame({
        "same_F": ((gen[u] == "F") & (gen[v] == "F")).astype(float),
        "same_M": ((gen[u] == "M") & (gen[v] == "M")).astype(float),
        "same_mixed": ((gen[u] == "mixed") & (gen[v] == "mixed")).astype(float),
        "same_genre": (gmu[u] == gmu[v]).astype(float),
        "same_cohort": (coh[u] == coh[v]).astype(float),
        "sum_lognrel": lnr[u] + lnr[v],
    })
    return X, y, tutte, nodi, len(casi), len(ctrl)


def logit_diadico(G, attrs, cfg, log):
    import statsmodels.api as sm
    seed = cfg["project"]["seed"]
    X, y, diadi, nodi, n_casi, n_ctrl = campiona_diadi(G, attrs, seed, log)

    # correzione caso-controllo: si sono tenute TUTTE le connesse e solo una
    # frazione delle non connesse, quindi l'intercetta va riportata alla
    # popolazione. I coefficienti non ne risentono.
    n = G.number_of_nodes()
    diadi_tot = n * (n - 1) // 2
    frazione = n_ctrl / (diadi_tot - n_casi)
    correzione = np.log(frazione)
    log.info(f"frazione di non connesse campionata: {frazione:.3e} "
             f"(correzione dell'intercetta: {correzione:+.3f})")

    Xc = sm.add_constant(X)
    with Timer("logit diadico", log):
        m = sm.Logit(y, Xc).fit(disp=0)
    coef = m.params.copy()
    coef["const"] = coef["const"] - correzione

    # Bootstrap sui NODI: due diadi che condividono un artista non sono
    # indipendenti, quindi ricampionare le diadi darebbe intervalli troppo
    # stretti. Si ricampionano i nodi e si tengono le diadi interne.
    rng = np.random.default_rng(seed + 1)
    idx_nodo = {i: k for k, i in enumerate(range(len(nodi)))}
    boot = []
    with Timer(f"bootstrap sui nodi (B={BOOTSTRAP_B})", log):
        for b in range(BOOTSTRAP_B):
            tenuti = rng.random(len(nodi)) < 0.5      # meta' dei nodi
            m_ok = tenuti[diadi[:, 0]] & tenuti[diadi[:, 1]]
            if m_ok.sum() < 1000:
                continue
            try:
                mb = sm.Logit(y[m_ok], Xc[m_ok]).fit(disp=0)
                boot.append(mb.params.values)
            except Exception:
                continue
    boot = np.array(boot)
    # Stessa correzione applicata al punto va applicata alle repliche: il
    # bootstrap ricampiona i nodi ma la frazione di non connesse campionata
    # resta quella del disegno, quindi senza questo la riga dell'intercetta
    # confronterebbe una stima corretta con intervalli non corretti.
    if len(boot):
        boot[:, list(Xc.columns).index("const")] -= correzione
    lo = np.percentile(boot, 2.5, axis=0)
    hi = np.percentile(boot, 97.5, axis=0)

    out = pd.DataFrame({
        "termine": Xc.columns, "coef": coef.values,
        "se_naive": m.bse.values,
        "ci_lo_bootstrap": lo, "ci_hi_bootstrap": hi,
        "or": np.exp(coef.values),
    })
    out["repliche_bootstrap"] = len(boot)
    log.info("\n" + out.round(4).to_string(index=False))
    common.save(out, "dyadic_logit.parquet")
    common.save_table(out, "t4_logit_diadico",
                      "Logit diadico caso-controllo sulla rete integrale, con "
                      "intervalli bootstrap sui nodi")
    return out


def qap(G, attrs, cfg, log):
    """Permutazione delle etichette di genere a rete fissa."""
    rng = np.random.default_rng(cfg["project"]["seed"] + 2)
    nodi = np.array(sorted(G.nodes()))
    pos = {a: i for i, a in enumerate(nodi)}
    gen = attrs.loc[nodi].gender.values
    archi = np.array([(pos[u], pos[v]) for u, v in G.edges()])
    u, v = archi[:, 0], archi[:, 1]

    def quote(g):
        """Quota di archi interni a ciascun genere, sul totale degli archi."""
        gu, gv = g[u], g[v]
        return {c: float(((gu == c) & (gv == c)).mean()) for c in ("F", "M", "mixed")}

    oss = quote(gen)
    nulla = {c: [] for c in oss}
    with Timer(f"permutazioni QAP (n={PERMUTAZIONI})", log):
        for _ in range(PERMUTAZIONI):
            q = quote(rng.permutation(gen))
            for c in nulla:
                nulla[c].append(q[c])

    righe = []
    for c, o in oss.items():
        d = np.array(nulla[c])
        righe.append({
            "categoria": c, "osservato": o, "atteso_medio": float(d.mean()),
            "atteso_sd": float(d.std()),
            "rapporto_oss_att": o / d.mean() if d.mean() else np.nan,
            "z": (o - d.mean()) / d.std() if d.std() else np.nan,
            # p a una coda: quante permutazioni raggiungono l'osservato
            "p": float((d >= o).mean()),
            "permutazioni": PERMUTAZIONI,
        })
    out = pd.DataFrame(righe)
    log.info("\n" + out.round(5).to_string(index=False))
    common.save(out, "qap_gender.parquet")
    common.save_table(out, "t4_qap_genere",
                      "Test di permutazione sulle etichette di genere a rete "
                      "fissa: la struttura, inclusa la chiusura triadica, resta "
                      "identica a ogni replica")
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4c_dyadic", cfg)
    if common.exists("dyadic_logit.parquet") and common.exists("qap_gender.parquet") \
            and not force:
        log.info("Fase 4c gia' completata, salto")
        return
    G, attrs = rete(cfg, log)
    with Timer("logit diadico completo", log):
        logit_diadico(G, attrs, cfg, log)
    with Timer("QAP", log):
        qap(G, attrs, cfg, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
