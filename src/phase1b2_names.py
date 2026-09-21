"""FASE 1b-bis — nomi Discogs di TUTTI gli artisti etichettati da Wikidata.

Il blocco A aggancia 202.480 id Discogs a un valore di P21. Quegli id non sono
solo i nostri italiani: sono musicisti di tutto il mondo. Recuperandone il nome
dal database si ottiene un corpus di oltre duecentomila coppie nome->genere
SPECIFICO DEL DOMINIO musicale, con cui addestrare il prior onomastico. E' una
base molto piu' solida dei soli 5.246 italiani agganciati, e sostituisce la
lista onomastica ISTAT, che in questo ambiente non e' disponibile come dataset
scaricabile.
"""
from __future__ import annotations
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer
from phase1_extract import copy_query, int_array, RAW


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1b2_names", cfg)
    out = RAW / "raw_wd_names.csv"
    if out.exists() and not force:
        log.info("nomi gia' estratti, salto")
        return
    if not common.exists("wd_by_discogs.parquet"):
        log.warning("blocco Wikidata A assente: niente prior onomastico esteso")
        return
    wd = common.load("wd_by_discogs.parquet")
    ok = wd[~wd.ambiguous & wd.discogs_id.between(1, 2147483647)]
    ids = sorted(set(ok.discogs_id.astype(int).tolist()))
    log.info(f"id Discogs etichettati da Wikidata: {len(ids):,}")
    with Timer("nomi degli artisti etichettati", log):
        copy_query(cfg, f"""
          SELECT a.id AS artist_id, a.name, a.realname
          FROM artist a WHERE a.id = ANY({int_array(ids)})
        """, out, log)
    df = pd.read_csv(out, low_memory=False)
    df.to_parquet(RAW / "raw_wd_names.parquet", index=False)
    log.info(f"nomi recuperati: {len(df):,} ({len(df)/len(ids):.1%} degli id)")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
