"""FASE 1e — verifica dell'euristica di italianita' con la cittadinanza Wikidata.

Il problema che questa fase affronta
------------------------------------
La popolazione e' definita sulla quota di pubblicazioni italiane, perche' il
dump Discogs non contiene ne' la nazionalita' degli artisti ne' il legame fra
pubblicazioni ed etichette. E' un criterio su DOVE SI PUBBLICA, non su da dove
si viene, ed e' il secondo limite dichiarato dell'articolo.

Wikidata la nazionalita' ce l'ha (P27). Non copre tutta la popolazione — si
parla di poche migliaia di artisti notabili su centomila — ma su quel
sottoinsieme consente di misurare quanto spesso l'euristica sbagli. Non la
sostituisce: la verifica.

Un dettaglio che cambia il risultato: fra le cittadinanze dei "non italiani"
la piu' frequente e' Q172579, il Regno d'Italia (1861-1946). Sono artisti
italiani, semplicemente nati sotto uno stato che non si chiamava Repubblica
Italiana. Contarli come stranieri sarebbe un errore di lettura, non
dell'euristica.
"""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

# Entita' statali che corrispondono all'Italia nelle sue forme storiche.
# Q38 e' la Repubblica Italiana, Q172579 il Regno d'Italia.
ITALIA = {"Q38", "Q172579"}

# Etichette dei paesi che compaiono fra i non italiani, per leggibilita' della
# tabella. Non sono esaustive: servono solo a rendere il risultato leggibile.
PAESI = {
    "Q30": "Stati Uniti", "Q414": "Argentina", "Q142": "Francia",
    "Q145": "Regno Unito", "Q155": "Brasile", "Q183": "Germania",
    "Q29": "Spagna", "Q39": "Svizzera", "Q40": "Austria", "Q34": "Svezia",
    "Q16": "Canada", "Q55": "Paesi Bassi", "Q31": "Belgio", "Q408": "Australia",
    "Q159": "Russia", "Q801": "Israele", "Q36": "Polonia", "Q213": "Cechia",
    "Q172579": "Regno d'Italia", "Q38": "Italia",
}


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1e_validate_italy", cfg)
    if not common.exists("wikidata_enriched.parquet"):
        log.warning("dati di cittadinanza assenti: eseguire prima "
                    "src/wikidata_enrich.py")
        return
    if common.exists("italy_validation.parquet") and not force:
        log.info("verifica gia' eseguita, salto")
        return

    pop = common.load("population_gender.parquet")
    e = common.load("wikidata_enriched.parquet")
    e = e[e.cittadinanze.notna()].drop_duplicates("discogs_id")
    m = pop.merge(e[["discogs_id", "cittadinanze"]],
                  left_on="artist_id", right_on="discogs_id")
    m["citt_set"] = m.cittadinanze.str.split("|").map(set)
    m["italiano"] = m.citt_set.map(lambda s: bool(s & ITALIA))

    n_ver = len(m)
    n_it = int(m.italiano.sum())
    log.info(f"artisti verificabili (con P27 su Wikidata): {n_ver:,} "
             f"({n_ver/len(pop):.1%} della popolazione)")
    log.info(f"di cui cittadini italiani: {n_it:,} -> {n_it/n_ver:.1%}")

    # chi sono i falsi positivi, e da dove vengono
    nn = m[~m.italiano]
    c = Counter(q for s in nn.citt_set for q in s)
    tab = pd.DataFrame(
        [{"paese": PAESI.get(q, q), "qid": q, "artisti": k}
         for q, k in c.most_common(12)])
    log.info(f"falsi positivi: {len(nn):,} ({len(nn)/n_ver:.1%})\n"
             + tab.to_string(index=False))

    # la precisione migliora se si stringe la soglia di italianita'?
    righe = []
    for soglia in [0.50, 0.60, 0.70, 0.80]:
        s = m[m.italian_share >= soglia]
        righe.append({"soglia": soglia, "verificabili": len(s),
                      "italiani": int(s.italiano.sum()),
                      "precisione": float(s.italiano.mean())})
    prec = pd.DataFrame(righe)
    log.info("precisione per soglia di italianita':\n" + prec.round(4).to_string(index=False))

    common.save(m[["artist_id", "name", "italian_share", "n_it", "n_all",
                   "cittadinanze", "italiano"]], "italy_validation.parquet")
    common.save_table(prec, "t1_validazione_italianita",
                      "Precisione dell'euristica di italianita' verificata sulla "
                      "cittadinanza Wikidata, per soglia di quota italiana")
    common.save_table(tab, "t1_validazione_falsi_positivi",
                      "Cittadinanze degli artisti della popolazione che Wikidata "
                      "non registra come italiani")
    common.write_json({"verificabili": n_ver, "italiani": n_it,
                       "precisione": n_it / n_ver,
                       "quota_popolazione": n_ver / len(pop),
                       "falsi_positivi": len(nn)}, "italy_validation.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
