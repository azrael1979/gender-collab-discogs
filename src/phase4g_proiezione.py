"""FASE 4g — i partner condivisi sono un processo sociale o un artefatto?

Perche' questa verifica
-----------------------
La bonta' di adattamento degli ERGM per decennio mostra un difetto preciso: la
distribuzione osservata dei partner condivisi per arco e' BIMODALE — molti archi
senza alcun partner condiviso e molti archi immersi in gruppi fitti — mentre
qualunque gwesp, avendo un solo parametro, ne produce una unimodale. Il modello
riproduce il numero di archi ma non la loro forma.

L'ipotesi e' che la colpa non sia del modello ma del concetto. Questa rete e'
la PROIEZIONE di un grafo bipartito artisti-release: ogni pubblicazione con k
artisti accreditati genera meccanicamente una clique di k, e dentro quella
clique ogni arco ha k-2 partner condivisi per costruzione, senza che nessuno
abbia "chiuso un triangolo" in alcun senso sociale. Se e' cosi', il termine
gwesp non sta stimando la chiusura triadica: sta stimando la distribuzione
della dimensione dei cast.

E' un'ipotesi verificabile esattamente, senza stimare nulla.

Il conto
--------
Per ogni arco (u,v) si distinguono:

* i **partner condivisi totali**: i nodi adiacenti sia a u sia a v, cioe' cio'
  che gwesp modella;
* i **partner spiegati dalla proiezione**: quelli che compaiono in una release
  condivisa da u e v. Chiunque sia accreditato in una release che contiene sia
  u sia v e' adiacente a entrambi per costruzione, quindi questi partner sono
  imposti dal disegno dei dati e non da alcun processo di chiusura.

La quota di partner condivisi spiegati dalla proiezione dice quanto di cio' che
gwesp misura sia meccanico. Se e' alta, un ERGM con gwesp su questa rete e'
mal posto — e l'articolo deve dirlo, perche' e' una critica che vale per ogni
rete di co-autorialita', non solo per questa.
"""
from __future__ import annotations
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4g_proiezione", cfg)
    if common.exists("proiezione_esp.parquet") and not force:
        log.info("Fase 4g gia' completata, salto")
        return

    edges = common.load("edges_all.parquet")
    credits = common.load("credits.parquet")[["artist_id", "release_id"]] \
        .drop_duplicates()
    maxc = cfg["network"]["max_credits"]

    with Timer("indici artista-release", log):
        dim = credits.groupby("release_id").artist_id.size()
        # stesso filtro con cui e' stata costruita la rete: le release con
        # troppi accreditati sono raccolte, non collaborazioni
        ok = dim[(dim >= 2) & (dim <= maxc)].index
        c = credits[credits.release_id.isin(ok)]
        cast = c.groupby("release_id").artist_id.apply(set).to_dict()
        rel_di = defaultdict(set)
        for a, r in c.itertuples(index=False):
            rel_di[a].add(r)
        log.info(f"release utilizzabili: {len(cast):,}; "
                 f"artisti accreditati: {len(rel_di):,}")

    with Timer("adiacenza", log):
        vic = defaultdict(set)
        for u, v, _ in edges.itertuples(index=False):
            vic[u].add(v)
            vic[v].add(u)
        log.info(f"rete: {len(vic):,} nodi, {len(edges):,} archi")

    righe = []
    with Timer("partner condivisi, arco per arco", log):
        for u, v, _ in edges.itertuples(index=False):
            comuni = vic[u] & vic[v]
            comuni.discard(u)
            comuni.discard(v)
            condivise = rel_di[u] & rel_di[v]
            spiegati = set()
            for r in condivise:
                spiegati |= cast[r]
            spiegati.discard(u)
            spiegati.discard(v)
            # dimensione della release condivisa piu' grande: e' il tetto ai
            # partner che una singola pubblicazione puo' imporre
            cast_max = max((len(cast[r]) for r in condivise), default=0)
            righe.append((len(comuni), len(spiegati & comuni), len(condivise),
                          cast_max))
    d = pd.DataFrame(righe, columns=["esp", "esp_spiegati", "release_condivise",
                                     "cast_max"])
    # Un arco dentro una release da k artisti riceve k-2 partner condivisi per
    # pura costruzione. Questa e' la soglia oltre la quale nessuna singola
    # pubblicazione puo' piu' spiegare nulla.
    d["tetto_proiezione"] = (d.cast_max - 2).clip(lower=0)
    d["oltre_il_tetto"] = d.esp > d.tetto_proiezione

    tot, spie = int(d.esp.sum()), int(d.esp_spiegati.sum())
    log.info("")
    log.info(f"partner condivisi totali sugli archi : {tot:,}")
    log.info(f"  di cui imposti dalla proiezione    : {spie:,} ({spie/tot:.1%})")
    log.info(f"  residui, compatibili con chiusura  : {tot-spie:,} ({1-spie/tot:.1%})")
    log.info(f"archi senza alcun partner condiviso  : {(d.esp==0).sum():,} "
             f"({(d.esp==0).mean():.1%})")
    log.info(f"archi interamente spiegati           : "
             f"{((d.esp>0)&(d.esp==d.esp_spiegati)).sum():,} "
             f"({((d.esp>0)&(d.esp==d.esp_spiegati)).mean():.1%})")

    # la forma bimodale che gwesp non puo' riprodurre
    dist = (d.groupby("esp").agg(archi=("esp", "size"),
                                 spiegati_medi=("esp_spiegati", "mean"))
              .reset_index())
    dist["quota_archi"] = dist.archi / len(d)
    dist["quota_spiegata"] = dist.spiegati_medi / dist.esp.replace(0, np.nan)
    log.info("\n" + dist.head(20).round(4).to_string(index=False))

    # La verifica decisiva: la quota spiegata deve restare alta finche' i
    # partner condivisi stanno sotto il tetto che la release piu' grande
    # impone, e crollare appena lo superano. Se il crollo cade altrove, la
    # spiegazione per proiezione e' sbagliata.
    sotto = d[~d.oltre_il_tetto & (d.esp > 0)]
    sopra = d[d.oltre_il_tetto & (d.esp > 0)]
    log.info("")
    log.info("verifica del tetto di proiezione (k-2 partner per una release da k)")
    for nome, g in (("entro il tetto", sotto), ("oltre il tetto", sopra)):
        if len(g):
            log.info(f"  {nome}: {len(g):,} archi ({len(g)/len(d):.1%}), "
                     f"quota spiegata {g.esp_spiegati.sum()/g.esp.sum():.3f}")
    tetto = pd.DataFrame([
        {"gruppo": nome, "archi": len(g),
         "quota_archi": len(g) / len(d),
         "esp_totali": int(g.esp.sum()),
         "quota_spiegata": float(g.esp_spiegati.sum() / g.esp.sum()) if len(g) else np.nan}
        for nome, g in (("entro il tetto", sotto), ("oltre il tetto", sopra))])
    common.save(tetto, "proiezione_tetto.parquet")
    common.save_table(tetto, "t4_proiezione_tetto",
                      "Quota dei partner condivisi spiegata dalla proiezione, "
                      "separando gli archi i cui partner stanno entro il tetto "
                      "imposto dalla release condivisa piu' grande da quelli "
                      "che lo superano")

    common.save(d, "proiezione_esp.parquet")
    common.save(dist, "proiezione_distribuzione.parquet")
    riassunto = pd.DataFrame([{
        "archi": len(d), "esp_totali": tot, "esp_spiegati": spie,
        "quota_spiegata": spie / tot,
        "archi_senza_esp": int((d.esp == 0).sum()),
        "quota_archi_senza_esp": float((d.esp == 0).mean()),
        "archi_interamente_spiegati": int(((d.esp > 0) & (d.esp == d.esp_spiegati)).sum()),
    }])
    common.save(riassunto, "proiezione_riassunto.parquet")
    common.save_table(riassunto, "t4_proiezione",
                      "Quota dei partner condivisi imposta meccanicamente dalla "
                      "proiezione bipartita artisti-release, cioe' non "
                      "attribuibile ad alcun processo di chiusura triadica")
    common.save_table(dist, "t4_proiezione_distribuzione",
                      "Distribuzione dei partner condivisi per arco e quota di "
                      "essi spiegata dalla co-presenza nella stessa release")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
