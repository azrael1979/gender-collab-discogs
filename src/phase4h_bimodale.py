"""FASE 4h — la bimodalita' e' davvero la causa? Un controllo positivo.

Che cosa si sta verificando
---------------------------
La Fase 4g ha misurato che una quota dei partner condivisi e' imposta dalla
proiezione bipartita, e la bonta' di adattamento degli ERGM per decennio
mostra uno scarto a U — centro sovrastimato, entrambe le code sottostimate —
identico nei due decenni in cui la stima converge. L'interpretazione proposta
e' che gwesp, avendo un solo parametro, produca una distribuzione unimodale
dove i dati ne hanno una bimodale.

Finora e' una diagnosi correlazionale: si osserva un difetto e se ne propone
una causa. Qui la si mette alla prova.

Il disegno
----------
Si riestima il decennio 1940 — quello che converge in meno di un'ora — con
termini di dipendenza a DUE componenti, capaci per costruzione di una forma
bimodale, e si guarda se la U si appiattisce. E' un controllo positivo: se la
spiegazione e' giusta, la previsione e' precisa e falsificabile.

Le specifiche provate, e perche':

* `gwesp(0.25) + gwesp(1.5)`  — due scale di chiusura. Il decay basso pesa i
  primi partner condivisi, quello alto la coda. Due parametri, due modi.
* `gwesp(0.25) + esp(0)`      — un parametro dedicato agli archi SENZA alcun
  partner condiviso, che e' il modo che il modello sottostima di piu' (osservati
  79 contro 9 simulati negli anni Quaranta, cioe' 8,7 volte).
* `gwesp(0.75)`               — controllo negativo: un solo parametro, decay
  diverso. Se bastasse cambiare il decay, la U si appiattirebbe anche qui e la
  spiegazione per bimodalita' sarebbe superflua. Serve a distinguere "due
  componenti" da "decay sbagliato", che e' la spiegazione alternativa ovvia.

Il confronto non e' sull'AIC ma sulla GOF: la domanda non e' quale modello si
adatti meglio in media, ma se lo scarto abbia ancora la forma a U.
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

B.ORE_MASSIME = 4
B.SILENZIO_MASSIMO_ORE = 1.5
MODELS = ROOT / "data" / "ergm_bimodale"

DECENNIO = 1940
VARIANTI = [
    ("due_scale",  "gwesp(0.25, fixed = TRUE) + gwesp(1.5, fixed = TRUE)"),
    ("gwesp_esp0", "gwesp(0.25, fixed = TRUE) + esp(0)"),
    ("decay_alto", "gwesp(0.75, fixed = TRUE)"),
]


def rete(cfg, log):
    E = common.load("edges_datati.parquet")
    pop = common.load("population_gender.parquet").set_index("artist_id")
    det = pop[pop.gender.isin(["M", "F", "mixed"])]
    g = E[E.decennio == DECENNIO]
    g = g[g.u.isin(det.index) & g.v.isin(det.index)]
    G = nx.Graph()
    G.add_edges_from(g[["u", "v"]].itertuples(index=False, name=None))
    G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    log.info(f"{DECENNIO}s: {G.number_of_nodes():,} nodi, "
             f"{G.number_of_edges():,} archi")
    return G, pop.reset_index()


def forma_a_u(gof: pd.DataFrame) -> dict:
    """Quanto lo scarto somiglia ancora a una U.

    Si confrontano gli estremi con il centro sul rapporto osservato/simulato.
    Una U ha estremi sopra 1 e centro sotto; se la bimodalita' e' stata
    assorbita, tutti e tre stanno vicino a 1.
    """
    e = gof[gof.statistica == "esp"].copy()
    e["rapporto"] = e.obs / e["mean"].replace(0, np.nan)
    basso = e[e.valore == 0].rapporto.mean()
    centro = e[e.valore.between(1, 2)].rapporto.mean()
    coda = e[e.valore.between(6, 9)].rapporto.mean()
    return {
        "esp0_oss_su_sim": basso,
        "centro_oss_su_sim": centro,
        "coda_oss_su_sim": coda,
        # quanto la U e' pronunciata: estremi diviso centro. 1 = piatta.
        "ampiezza_U": (np.nanmean([basso, coda]) / centro) if centro else np.nan,
        "bin_fuori_scala": int((e["MC.p.value"] < 0.05).sum()),
        "bin_totali": int(len(e)),
    }


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4h_bimodale", cfg)
    if common.exists("ergm_bimodale.parquet") and not force:
        log.info("Fase 4h gia' completata, salto")
        return
    MODELS.mkdir(parents=True, exist_ok=True)
    B.MODELS = MODELS
    G, pop = rete(cfg, log)

    esiti = []
    # riferimento: la specifica a una componente gia' stimata nella Fase 4f
    rif = ROOT / "data" / "ergm_decenni" / f"dec{DECENNIO}" / "gof.csv"
    if rif.exists():
        r = forma_a_u(pd.read_csv(rif))
        r.update({"variante": "gwesp(0.25) — riferimento", "riuscita": True})
        esiti.append(r)
        log.info(f"riferimento a una componente: U = {r['ampiezza_U']:.2f} "
                 f"(esp0 {r['esp0_oss_su_sim']:.2f}, centro "
                 f"{r['centro_oss_su_sim']:.2f}, coda {r['coda_oss_su_sim']:.2f})")

    for nome, dip in VARIANTI:
        log.info(f"=== {nome}: {dip} ===")
        s = None
        try:
            d = B.prepara(G, pop, nome, cfg, dipendenza=dip, metodo="MCMLE")
            c = json.loads((d / "control.json").read_text())
            c["gof"], c["gof_nsim"] = True, 100
            (d / "control.json").write_text(json.dumps(c))
            with Timer(f"ERGM {nome}", log):
                s = B.esegui(d, cfg, log)
        except Exception as e:
            log.error(f"  {nome}: errore imprevisto {e!r}", exc_info=True)
        riuscita = bool(s and s.get("mcmle"))
        r = {"variante": nome, "dipendenza": dip, "riuscita": riuscita,
             "aic": (s or {}).get("aic")}
        gof = MODELS / nome / "gof.csv"
        if gof.exists():
            r.update(forma_a_u(pd.read_csv(gof)))
        ab = MODELS / nome / "abbandonata.txt"
        r["motivo"] = ab.read_text().strip() if ab.exists() else None
        esiti.append(r)
        log.info(f"  {nome}: {'CONVERGE' if riuscita else 'FALLITO'}"
                 + (f", U = {r['ampiezza_U']:.2f}" if "ampiezza_U" in r else ""))
        try:
            common.save(pd.DataFrame(esiti), "ergm_bimodale.parquet")
        except Exception as e:
            log.warning(f"  salvataggio fallito: {e!r}")

    d = pd.DataFrame(esiti)
    common.save(d, "ergm_bimodale.parquet")
    common.save_table(d, "t4_bimodale",
                      "Controllo positivo sulla diagnosi di bimodalita': "
                      f"decennio {DECENNIO} riestimato con termini di dipendenza "
                      "a due componenti, e forma residua dello scarto di "
                      "adattamento sui partner condivisi")
    log.info("\n" + d.round(3).to_string(index=False))
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
