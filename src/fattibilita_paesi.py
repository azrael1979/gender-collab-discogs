"""Studio di fattibilita' per il confronto internazionale (proposto il 25/9/2026).

Non fa parte della pipeline dell'articolo italiano: serve a scegliere, sui
numeri, quali paesi confrontare con l'Italia prima di pre-registrare le ipotesi
del lavoro comparativo.

Per ogni paese candidato misura cio' da cui dipende la fattibilita' del metodo:

* **dimensione**: artisti che passano lo stesso criterio di nazionalita' usato
  per l'Italia (>= 2 release nel paese, >= 3 in totale, quota >= 0,50), e
  quanti di loro sono gruppi, da escludere come in D16;
* **profondita' storica**: quanti di loro debuttano in ciascun decennio dal 1950;
* **inferenza del genere**: quota con un genere Wikidata agganciato per
  identificativo (P1953 + P21) e quota con un nome anagrafico registrato;
* **validita' del criterio di nazionalita'**: fra gli artisti con cittadinanza
  Wikidata (P27), quanti sono cittadini del paese — la stessa verifica che per
  l'Italia da' 94,5%.

Il database e' letto in SOLA LETTURA con due passate sequenziali (release e
release_artist; artist), come nella Fase 1. Nessun oggetto viene creato.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer
from phase1_extract import copy_query

OUT = ROOT / "data" / "fattibilita"

# etichetta Discogs del paese -> QID Wikidata delle cittadinanze che contano
PAESI = {
    "Italy": ["Q38", "Q172579"],                       # + Regno d'Italia
    "Spain": ["Q29"],
    "France": ["Q142"],
    "Germany": ["Q183", "Q713750", "Q41304", "Q16957"],  # + Germania Ovest, Weimar, DDR
    "German Democratic Republic (GDR)": ["Q16957", "Q183"],
    # Wikidata usa spesso lo stato, non il paese costitutivo: Regno di Danimarca,
    # Regno dei Paesi Bassi, Regno Unito di Gran Bretagna e Irlanda (storico)
    "Sweden": ["Q34"], "Norway": ["Q20"], "Denmark": ["Q35", "Q756617"], "Finland": ["Q33"],
    "Netherlands": ["Q55", "Q29999"], "Portugal": ["Q45"], "Greece": ["Q41"],
    "Japan": ["Q17"], "Brazil": ["Q155"], "UK": ["Q145", "Q174193"], "US": ["Q30"],
}


def conteggi(cfg, log) -> pd.DataFrame:
    """Una passata: per ogni artista, release totali, release per paese
    candidato e primo anno. Tiene chi ha almeno 2 release in un candidato."""
    f = OUT / "conteggi_artisti.csv"
    if not f.exists():
        filtri = ",\n".join(
            f"count(*) FILTER (WHERE r.country = '{p}') AS \"n_{i}\""
            for i, p in enumerate(PAESI))
        almeno = " OR ".join(
            f"count(*) FILTER (WHERE r.country = '{p}') >= 2" for p in PAESI)
        copy_query(cfg, f"""
          SELECT ra.artist_id, count(*) AS n_all,
                 min(NULLIF(substring(r.released FROM '^[0-9]{{4}}'), '')::int)
                   FILTER (WHERE substring(r.released FROM '^[0-9]{{4}}')
                           BETWEEN '1900' AND '2026') AS debutto,
                 {filtri}
          FROM release_artist ra JOIN release r ON r.id = ra.release_id
          GROUP BY 1 HAVING {almeno}
        """, f, log)
    return pd.read_csv(f)


def uscite_per_paese(cfg, log) -> pd.DataFrame:
    f = OUT / "release_per_paese.csv"
    if not f.exists():
        copy_query(cfg, """
          SELECT country,
                 (NULLIF(substring(released FROM '^[0-9]{3}'), '') || '0') AS decennio,
                 count(*) AS release
          FROM release GROUP BY 1, 2
        """, f, log)
    return pd.read_csv(f)


def metadati(cfg, log) -> pd.DataFrame:
    """Due scansioni sequenziali invece di una sottoquery per artista: sul disco
    rotante una EXISTS correlata diventerebbe milioni di letture casuali."""
    fa, fg = OUT / "artisti_realname.csv", OUT / "gruppi.csv"
    if not fa.exists():
        copy_query(cfg, """
          SELECT id AS artist_id,
                 (realname IS NOT NULL AND btrim(realname) <> '') AS ha_realname
          FROM artist
        """, fa, log)
    if not fg.exists():
        copy_query(cfg, "SELECT DISTINCT group_artist_id FROM group_member", fg, log)
    a = pd.read_csv(fa)
    a["ha_realname"] = a.ha_realname.astype(str).isin(["t", "True", "true"])  # COPY scrive t/f
    g = set(pd.read_csv(fg).group_artist_id)
    a["gruppo"] = a.artist_id.isin(g)
    return a


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("fattibilita_paesi", cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    with Timer("release per paese e decennio", log):
        rel = uscite_per_paese(cfg, log)
    with Timer("conteggi per artista", log):
        cnt = conteggi(cfg, log)
    with Timer("metadati degli artisti", log):
        meta = metadati(cfg, log).set_index("artist_id")

    wd = common.load("wd_by_discogs.parquet")
    wd = wd[~wd.ambiguous & wd.gender_wd.isin(["M", "F"])].drop_duplicates("discogs_id").set_index("discogs_id")
    wc = common.load("wikidata_enriched.parquet").dropna(subset=["cittadinanze"])
    wc = wc.drop_duplicates("discogs_id").set_index("discogs_id").cittadinanze.astype(str)

    righe, decenni = [], []
    for i, (paese, qids) in enumerate(PAESI.items()):
        c = cnt[[ "artist_id", "n_all", "debutto", f"n_{i}"]].rename(columns={f"n_{i}": "n_c"})
        pop = c[(c.n_c >= 2) & (c.n_all >= 3) & (c.n_c / c.n_all >= 0.5)].copy()
        pop["gruppo"] = pop.artist_id.map(meta.gruppo).fillna(False).astype(bool)
        ind = pop[~pop.gruppo]
        con_p27 = ind[ind.artist_id.isin(wc.index)]
        cit = con_p27.artist_id.map(wc)
        preciso = cit.map(lambda s: any(q in s.replace(",", " ").replace("|", " ").split()
                                       for q in qids))
        gen = ind.artist_id.map(wd.gender_wd)
        r_ = rel[rel.country == paese]
        righe.append({
            "paese": paese,
            "release": int(r_.release.sum()),
            "release_1950_1979": int(r_[pd.to_numeric(r_.decennio, errors="coerce")
                                         .between(1950, 1970)].release.sum()),
            "voci": len(pop), "gruppi": int(pop.gruppo.sum()), "individui": len(ind),
            "con_genere_wikidata": float(gen.notna().mean()) if len(ind) else np.nan,
            "donne_fra_wikidata": float((gen == "F").sum() / max(gen.notna().sum(), 1)),
            "con_realname": float(ind.artist_id.map(meta.ha_realname).fillna(False).mean()),
            "verificabili_p27": len(con_p27),
            "precisione_nazionalita": float(preciso.mean()) if len(con_p27) else np.nan,
        })
        dd = (ind.debutto // 10 * 10).value_counts()
        decenni.append({"paese": paese, **{f"{int(d)}s": int(dd.get(d, 0))
                                           for d in range(1950, 2030, 10)}})
    out = pd.DataFrame(righe)
    dec = pd.DataFrame(decenni)
    common.save(out, "fattibilita_paesi.parquet")
    common.save(dec, "fattibilita_paesi_decenni.parquet")
    out.to_csv(OUT / "fattibilita_paesi.csv", index=False)
    dec.to_csv(OUT / "fattibilita_paesi_decenni.csv", index=False)
    pd.set_option("display.width", 250)
    log.info("\n" + out.round(3).to_string(index=False))
    log.info("\n" + dec.to_string(index=False))


if __name__ == "__main__":
    main(force="--force" in sys.argv)
