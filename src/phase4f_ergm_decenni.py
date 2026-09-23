"""FASE 4f — ERGM per decennio di formazione del legame.

L'idea e' di chi legge: se l'ERGM non e' stimabile sulla rete integrale, forse
lo e' spezzandola per epoche. Vale la pena essere precisi su cosa questo
risolve e cosa no.

Che cosa risolve
----------------
La taglia. L'ERGM era convergito su sottoreti con un tetto di 1.500 nodi e
5.000 archi; i decenni fino agli anni Cinquanta stanno in quell'ordine di
grandezza (163, 364, 1.515 nodi). Il regime in cui la stima funzionava torna
a portata.

Soprattutto: **un decennio e' una popolazione, non un campione**. Le sottoreti
della Fase 4 erano campioni a valanga, e di una stima su campione a valanga non
si puo' dire di che cosa sia stima — il campione non e' rappresentativo di
nulla di definibile. Un decennio e' invece un insieme completo: tutti i legami
formatisi in quegli anni. Anche una serie parziale, che copra soltanto la prima
meta' del secolo, e' interpretabile in un modo in cui quelle non lo erano.

E risponde alla domanda che conta: l'omofilia femminile cresce nel tempo **al
netto della chiusura triadica**? Le misure esatte della Fase 4e dicono che
cresce; nessuna di esse tiene conto del fatto che due donne possono ritrovarsi
collegate solo perche' condividono un conoscente.

Che cosa NON risolve
--------------------
Il clustering, che e' la vera causa della degenerazione. Misurato decennio per
decennio, il coefficiente di clustering medio resta fra 0,43 e 0,56 in TUTTI i
periodi: non scende spezzando la rete. Non puo' scendere, perche' e' un
artefatto di proiezione — ogni release con k artisti accreditati genera
meccanicamente una clique di k, e le clique massime vanno da 7 a 18 in ogni
decennio. Un solo parametro gwesp deve riprodurre quell'eccesso di triangoli, e
non ci riesce: e' la stessa ragione per cui e' collassato sulla rete intera.

La previsione, scritta prima di lanciare, e' che converga fino agli anni
Sessanta o Settanta e fallisca dopo. Il modulo procede dal decennio piu' piccolo
al piu' grande proprio per rendere quella previsione falsificabile: se fallisce
dove doveva riuscire, si vede subito.

La bonta' di adattamento resta ATTIVA, a differenza che sulla rete integrale:
qui le reti sono piccole e simularle costa poco. E' l'unico controllo che
distingue una convergenza vera da una apparente — sulla rete integrale una
stima aveva dichiarato successo producendo reti con il 40% degli archi
osservati e il 4% dei legami fra donne.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer
import phase4b_ergm_full as B

# Reti piccole: nessuna ragione di lasciare a una singola stima trenta ore.
# Se un decennio non converge in sei, non convergera'.
B.ORE_MASSIME = 6
B.SILENZIO_MASSIMO_ORE = 2
MODELS = ROOT / "data" / "ergm_decenni"

# Sotto questa soglia un ERGM non ha abbastanza legami per stimare sei termini.
MIN_ARCHI = 300
MIN_NODI = 100


def reti_per_decennio(cfg, log):
    """Una rete per decennio, dal piu' piccolo al piu' grande.

    L'ordine non e' cronologico ma per dimensione crescente: se la previsione
    e' che la convergenza si rompa oltre una certa taglia, conviene arrivarci
    avendo gia' in mano i casi piccoli.
    """
    E = common.load("edges_datati.parquet")
    pop = common.load("population_gender.parquet").set_index("artist_id")
    det = pop[pop.gender.isin(["M", "F", "mixed"])]
    reti = []
    for dec, g in E.groupby("decennio"):
        g = g[g.u.isin(det.index) & g.v.isin(det.index)]
        if len(g) < MIN_ARCHI:
            continue
        G = nx.Graph()
        G.add_edges_from(g[["u", "v"]].itertuples(index=False, name=None))
        if G.number_of_nodes() < MIN_NODI:
            continue
        # La componente gigante: l'ERGM su un grafo con molte componenti
        # isolate stima soprattutto la loro assenza di legami.
        G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
        reti.append((int(dec), G))
        log.info(f"  {dec}s: {G.number_of_nodes():,} nodi, "
                 f"{G.number_of_edges():,} archi, "
                 f"clustering {nx.average_clustering(G):.3f}")
    reti.sort(key=lambda t: t[1].number_of_edges())
    log.info("ordine di stima (dimensione crescente): "
             + ", ".join(f"{d}s" for d, _ in reti))
    return reti, pop.reset_index()


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4f_ergm_decenni", cfg)
    if common.exists("ergm_decenni_esiti.parquet") and not force:
        log.info("Fase 4f gia' completata, salto")
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    B.MODELS = MODELS

    reti, pop = reti_per_decennio(cfg, log)
    esiti = []
    for dec, G in reti:
        nome = f"dec{dec}"
        n, m = G.number_of_nodes(), G.number_of_edges()
        log.info(f"=== {dec}s: {n:,} nodi, {m:,} archi ===")
        s = None
        try:
            d = B.prepara(G, pop, nome, cfg,
                          dipendenza=f"gwesp({cfg['ergm']['gwesp_decay']}, fixed = TRUE)",
                          metodo="MCMLE")
            # la bonta' di adattamento e' il controllo che distingue una
            # convergenza vera da una apparente, e qui costa poco
            c = json.loads((d / "control.json").read_text())
            c["gof"], c["gof_nsim"] = True, 100
            (d / "control.json").write_text(json.dumps(c))
            with Timer(f"ERGM {dec}s", log):
                s = B.esegui(d, cfg, log)
        except Exception as e:
            log.error(f"  {dec}s: errore imprevisto {e!r}", exc_info=True)
        riuscita = bool(s and s.get("mcmle"))
        # il motivo di un abbandono lo scrive esegui() su file, non lo
        # restituisce: summary.json viene prodotto solo da una stima conclusa
        ab = MODELS / nome / "abbandonata.txt"
        esiti.append({"decennio": dec, "nodi": n, "archi": m,
                      "riuscita": riuscita,
                      "motivo": ab.read_text().strip() if ab.exists() else None,
                      "gof": bool(s and s.get("gof")),
                      "secondi": (s or {}).get("secondi")})
        log.info(f"  {dec}s: {'CONVERGE' if riuscita else 'FALLITO'}")
        try:
            common.save(pd.DataFrame(esiti), "ergm_decenni_esiti.parquet")
        except Exception as e:
            log.warning(f"  salvataggio esiti fallito: {e!r}")

    righe = []
    for f in sorted(MODELS.glob("*/coef.csv")):
        try:
            righe.append(pd.read_csv(f).assign(
                decennio=int(f.parent.name.replace("dec", ""))))
        except Exception as e:
            log.warning(f"  {f.parent.name}/coef.csv illeggibile: {e!r}")
    if righe:
        coef = pd.concat(righe, ignore_index=True).sort_values("decennio")
        common.save(coef, "ergm_decenni_coef.parquet")
        common.save_table(coef, "t4_ergm_decenni",
                          "Coefficienti ERGM stimati separatamente per decennio "
                          "di formazione del legame; ogni decennio e' una "
                          "popolazione completa, non un campione")
        log.info("\n" + coef.round(4).to_string(index=False))
    log.info("\n" + pd.DataFrame(esiti).to_string(index=False))
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
