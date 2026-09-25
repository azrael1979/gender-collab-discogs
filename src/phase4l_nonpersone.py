"""FASE 4l — sensibilita': le voci che non sono persone.

Perche' questa fase esiste
--------------------------
La regola sui gruppi (D16) esclude solo le voci con membri registrati in
Discogs. Restano nella popolazione band, orchestre e cori senza membri
registrati, etichette, edizioni e studi grafici accreditati come artisti, e
varianti locali del segnaposto «Various» ("Aavv", "Vari"). Lo ha mostrato la
codifica del campione di validazione italiano (25 settembre 2026).

Quasi tutte queste voci hanno genere indeterminato e sono gia' fuori da ogni
misura di genere; qualcuna ha ricevuto un genere dal nome. Questa fase le toglie
dalla popolazione, con i loro legami, e ricalcola le misure principali:

* assortativita' di genere (soli determinati), come nella Fase 3c;
* R_F e R_M per decennio sotto il nullo per strati di grado, come nella 4j.

Nel confronto internazionale e' una deviazione dichiarata prima di eseguirla
(docs/02-deviazioni.md, DV1): l'analisi primaria resta quella registrata.

La lista e' volutamente esplicita: marcatori multilingue (italiano, spagnolo,
francese, tedesco, svedese, inglese), applicati al solo nome d'arte.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import Timer
from phase3_homophily import edge_attrs, mixing_matrix, assortativity
from phase4j_nullo_grado import confronta

NON_PERSONA = re.compile(
    r"\b("
    r"orchestr\w*|orquesta\w*|orchester\w*|orkester|philharmoni\w*|filarm\w*|"
    r"symphon\w*|sinfon\w*|ensemble|band|banda\s+(?:de|di|del|della|dei|municipal)|trio|quartet\w*|cuarteto|quatuor|"
    r"kvartett|quintet\w*|sextet\w*|sestetto|coro|corale|choir|chor|choeur|chœur|"
    r"kör|singers|cantori|brothers|bröderna|fratelli|hermanos|frères|gebrüder|"
    r"sisters|sorelle|hermanas|schwestern|records|recordings|discos|disques|"
    r"schallplatten|edizioni|ediciones|éditions|editions|verlag|förlag|studios?|"
    r"design|productions?|produzioni|producciones|crew|collective|collettivo|"
    r"company|complesso|conjunto|gruppo|grupo|groupe|gruppe|group"
    r")\b"
    r"|\b(e la sua|e il suo|y su|et son|et ses|und sein|und ihr|and his|and her|"
    r"& his|& her|och hans|och hennes)\b"
    # nomi che cominciano con un articolo plurale o inglese ("I Farmers",
    # "The Nice Guys"); "Le" e "La" restano fuori, perche' sono anche prefissi
    # di cognomi (Le Forestier, La Rosa)
    r"|^(the|i|gli|los|las|les|die)\s",
    re.I)

SEGNAPOSTO = re.compile(
    r"^(aa\.?\s?vv\.?|a\.\s?a\.\s?v\.\s?v\.?|autori vari|artisti vari|vari|"
    r"varios(\s+artistas)?|various(\s+artists)?|divers(\s+artistes)?|"
    r"verschiedene(\s+interpreten)?|diverse(\s+artister)?|v\.\s?a\.?)"
    r"(\s*\(\d+\))?$", re.I)


def marca(pop: pd.DataFrame) -> pd.Series:
    nome = pop.name.fillna("").str.strip()
    motivo = pd.Series(None, index=pop.index, dtype=object)
    motivo[nome.map(lambda s: bool(NON_PERSONA.search(s)))] = "marcatore"
    motivo[nome.map(lambda s: bool(SEGNAPOSTO.match(s)))] = "segnaposto"
    return motivo


def serie_per_grado(E, pop, rng):
    """Come la Fase 4j, decennio per decennio, sulla popolazione data."""
    righe = []
    popi = pop.set_index("artist_id")
    for dec, g in E.groupby("decennio"):
        nodi = np.unique(np.concatenate([g.u.values, g.v.values]))
        nodi = nodi[pd.Index(nodi).isin(popi.index)]
        a = popi.reindex(nodi)
        a = a[a.gender.isin(["M", "F", "mixed"])]
        nodi = a.index.values
        pos = {x: i for i, x in enumerate(nodi)}
        gg = g[g.u.isin(pos) & g.v.isin(pos)]
        if len(nodi) < 100 or len(gg) < 200:
            continue
        ii = gg.u.map(pos).values.astype(np.int32)
        jj = gg.v.map(pos).values.astype(np.int32)
        for r in confronta(a.gender.values.astype(str), ii, jj, rng):
            righe.append({"decennio": int(dec), "categoria": r["categoria"],
                          "rapporto_grado": r["rapporto_grado"],
                          "z_grado": r["z_grado"], "archi": r["archi"]})
    return pd.DataFrame(righe)


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4l_nonpersone", cfg)
    if common.exists("sensibilita_nonpersone.parquet") and not force:
        log.info("Fase 4l gia' completata, salto")
        return
    pop = common.load("population_gender.parquet")
    pop["motivo"] = marca(pop)
    via = pop[pop.motivo.notna()]
    log.info(f"voci che non sono persone: {len(via):,} su {len(pop):,} "
             f"({len(via)/len(pop):.1%}); per motivo:\n"
             + via.motivo.value_counts().to_string()
             + "\nper genere inferito:\n" + via.gender.value_counts().to_string())
    common.save(via[["artist_id", "name", "gender", "label_source", "motivo"]],
                "non_persone.parquet")
    ridotta = pop[pop.motivo.isna()].drop(columns="motivo")
    tolti = set(via.artist_id)

    E = common.load("edges_all.parquet")
    righe = [{"misura": "legami tolti", "primaria": len(E),
              "sensibilita": int((~(E.u.isin(tolti) | E.v.isin(tolti))).sum())}]
    for nome, p in (("primaria", pop), ("sensibilita", ridotta)):
        q = p.copy()
        q.loc[~q.gender.isin(["M", "F"]), "gender"] = None
        a, b, w, cats = edge_attrs(E, q, "gender")
        righe.append({"misura": "assortativita di genere", nome:
                      float(assortativity(mixing_matrix(a, b, k=len(cats))))})
    ass = pd.DataFrame(righe).groupby("misura").first().reset_index()

    rng = np.random.default_rng(cfg["project"]["seed"])
    Ed = common.load("edges_datati.parquet")
    Ed = Ed[Ed.decennio >= 1950]
    with Timer("serie per grado, popolazione primaria", log):
        s1 = serie_per_grado(Ed, pop.drop(columns="motivo"), rng)
    with Timer("serie per grado, senza non-persone", log):
        s2 = serie_per_grado(Ed, ridotta, rng)
    serie = s1.merge(s2, on=["decennio", "categoria"], suffixes=("_primaria", "_sensibilita"))
    log.info("\n" + ass.to_string(index=False))
    log.info("\n" + serie.round(3).to_string(index=False))
    common.save(ass, "sensibilita_nonpersone_assortativita.parquet")
    common.save(serie, "sensibilita_nonpersone.parquet")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
