"""FASE 1a — estrazione dal DB `discogs` in SOLA LETTURA.

Vincoli e scelte di implementazione
-----------------------------------
* Ogni sessione gira con `default_transaction_read_only = on`, che in PostgreSQL
  vieta anche le TEMP TABLE: l'estrazione non crea alcun oggetto, nemmeno
  temporaneo. Le liste di id calcolate lato Python tornano al server come
  letterale `int[]`.
* Il cluster e' su disco rotazionale: le query sono scritte per fare passate
  SEQUENZIALI (una sola per tabella grande), non accessi indicizzati random.
  In particolare `n_it` e `n_all` si ottengono con un unico scan aggregato di
  release_artist invece di due join separati.

Output in data/raw/ (CSV + parquet).
"""
from __future__ import annotations
import sys, re
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

RAW = ROOT / "data" / "raw"


def copy_query(cfg, sql: str, out: Path, log, tuning=None) -> int:
    out.parent.mkdir(parents=True, exist_ok=True)
    conn = common.get_conn(cfg, tuning)
    try:
        with conn.cursor() as cur, open(out, "w") as fh:
            with Timer(f"COPY {out.stem}", log):
                cur.copy_expert(f"COPY ({sql}) TO STDOUT WITH (FORMAT csv, HEADER true)", fh)
    finally:
        conn.close()
    n = sum(1 for _ in open(out)) - 1
    log.info(f"{out.stem}: {n:,} righe")
    return n


def int_array(ids) -> str:
    """Letterale int[]: sostituisce la temp table, vietata in read-only."""
    return "'{" + ",".join(str(int(i)) for i in ids) + "}'::int[]"


# --------------------------------------------------------------------------
def step_counts(cfg, log) -> pd.DataFrame:
    """Passata unica su release_artist: n_it e n_all per ogni artista.

    L'aggregazione tiene tutti gli artisti con almeno `min_italian_releases`
    release italiane; la selezione finale (quota, minimo totale, esclusioni
    anagrafiche) avviene dopo, sui dati gia' a terra, cosi' da poter variare le
    soglie in Fase 5 senza rileggere il database.
    """
    p = cfg["population"]
    out = RAW / "raw_artist_counts.csv"
    if out.exists():
        log.info("raw_artist_counts gia' presente, salto")
    else:
        copy_query(cfg, f"""
          SELECT ra.artist_id,
                 count(*) FILTER (WHERE it.id IS NOT NULL) AS n_it,
                 count(*) AS n_all
          FROM release_artist ra
          LEFT JOIN (SELECT id FROM release WHERE country = '{p["country_label"]}') it
                 ON it.id = ra.release_id
          GROUP BY 1
          HAVING count(*) FILTER (WHERE it.id IS NOT NULL) >= {p["min_italian_releases"]}
        """, out, log)
    return pd.read_csv(out)


def select_population(counts: pd.DataFrame, names: pd.DataFrame, cfg, log) -> pd.DataFrame:
    p = cfg["population"]
    df = counts.copy()
    df["italian_share"] = df.n_it / df.n_all
    df = df[(df.italian_share >= p["min_italian_share"]) & (df.n_all >= p["min_total_releases"])]
    df = df.merge(names, on="artist_id", how="left")
    pat = re.compile("|".join(p["exclude_name_patterns"]), re.I)
    bad = df.name.fillna("").str.match(pat)
    log.info(f"esclusi per anagrafica (Various/Unknown/Traditional): {int(bad.sum()):,}")
    return df[~bad].reset_index(drop=True)


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1_extract", cfg)
    RAW.mkdir(parents=True, exist_ok=True)
    marker = RAW / "_extract_done"
    if marker.exists() and not force:
        log.info("estrazione gia' presente, salto (--force per rifarla)")
        return

    # ---- 1. conteggi di italianita' (una passata su release_artist, 28 GB)
    counts = step_counts(cfg, log)
    log.info(f"artisti con >= {cfg['population']['min_italian_releases']} release italiane: "
             f"{len(counts):,}")

    # ---- 2. anagrafica dei soli candidati potenziali
    pre = counts[(counts.n_it / counts.n_all >= cfg["population"]["min_italian_share"]) &
                 (counts.n_all >= cfg["population"]["min_total_releases"])]
    log.info(f"candidati pre-filtro anagrafico: {len(pre):,}")
    A_art = int_array(pre.artist_id)
    copy_query(cfg, f"""
      SELECT a.id AS artist_id, a.name, a.realname, a.profile, a.data_quality
      FROM artist a WHERE a.id = ANY({A_art})
    """, RAW / "raw_artistmeta.csv", log)
    meta = pd.read_csv(RAW / "raw_artistmeta.csv", low_memory=False)

    pop = select_population(counts, meta, cfg, log)
    pop.to_csv(RAW / "raw_artists.csv", index=False)
    log.info(f"POPOLAZIONE FINALE: {len(pop):,} artisti italiani")
    A = int_array(pop.artist_id)

    # ---- 3. crediti (una passata sequenziale per tabella)
    copy_query(cfg, f"""
      SELECT ra.artist_id, ra.release_id, ra.extra,
             NULLIF(btrim(ra.role), '')   AS role,
             NULLIF(btrim(ra.tracks), '') AS tracks
      FROM release_artist ra WHERE ra.artist_id = ANY({A})
    """, RAW / "raw_ra.csv", log)

    copy_query(cfg, f"""
      SELECT rta.artist_id, rta.release_id,
             NULLIF(btrim(rta.track_id), '')       AS track_id,
             NULLIF(btrim(rta.track_sequence), '') AS track_sequence,
             rta.extra,
             NULLIF(btrim(rta.role), '')           AS role
      FROM release_track_artist rta WHERE rta.artist_id = ANY({A})
    """, RAW / "raw_rta.csv", log)

    # ---- 4. release toccate
    with Timer("rel_ids", log):
        rel_ids = pd.unique(pd.concat([
            pd.read_csv(RAW / "raw_ra.csv", usecols=["release_id"]).release_id,
            pd.read_csv(RAW / "raw_rta.csv", usecols=["release_id"]).release_id]))
        log.info(f"release coinvolte: {len(rel_ids):,}")
    R = int_array(rel_ids)

    copy_query(cfg, f"""
      SELECT r.id AS release_id,
             substring(r.released FROM '^[0-9]{{4}}')::int AS year,
             r.country, NULLIF(r.master_id, 0) AS master_id, r.status
      FROM release r WHERE r.id = ANY({R})
    """, RAW / "raw_releases.csv", log)

    copy_query(cfg, f"""
      SELECT ra.release_id,
             count(DISTINCT ra.artist_id) AS n_credited,
             count(DISTINCT ra.artist_id) FILTER (WHERE ra.extra = 0) AS n_main
      FROM release_artist ra WHERE ra.release_id = ANY({R}) GROUP BY 1
    """, RAW / "raw_relsize.csv", log)

    copy_query(cfg, f"""
      SELECT DISTINCT ra.release_id
      FROM release_artist ra JOIN artist a ON a.id = ra.artist_id
      WHERE ra.release_id = ANY({R}) AND ra.extra = 0
        AND a.name ~* '^various( artists?)?( \\(\\d+\\))?$'
    """, RAW / "raw_various.csv", log)

    # Alcune release non hanno alcuna riga in release_artist: i loro crediti
    # esistono solo a livello traccia. Per non far saltare il filtro
    # max_credits, la loro dimensione si conta su release_track_artist.
    with Timer("release senza crediti release", log):
        have = set(pd.read_csv(RAW / "raw_relsize.csv", usecols=["release_id"]).release_id)
        missing = [r for r in rel_ids if r not in have]
        log.info(f"release con soli crediti a livello traccia: {len(missing):,}")
    if missing:
        copy_query(cfg, f"""
          SELECT rta.release_id, count(DISTINCT rta.artist_id) AS n_credited, 0 AS n_main
          FROM release_track_artist rta
          WHERE rta.release_id = ANY({int_array(missing)}) GROUP BY 1
        """, RAW / "raw_relsize_track.csv", log)

    copy_query(cfg, f"""
      SELECT r.id AS release_id, mg.genre
      FROM release r JOIN master_genre mg ON mg.master_id = r.master_id
      WHERE r.id = ANY({R}) AND r.master_id > 0 AND mg.genre IS NOT NULL
    """, RAW / "raw_relgenre.csv", log)

    copy_query(cfg, f"""
      SELECT r.id AS release_id, ms.style
      FROM release r JOIN master_style ms ON ms.master_id = r.master_id
      WHERE r.id = ANY({R}) AND r.master_id > 0 AND ms.style IS NOT NULL
    """, RAW / "raw_relstyle.csv", log)

    # ---- 5. mappa posizione -> traccia (solo dove ci sono crediti posizionali)
    with Timer("need_pos", log):
        ra_t = pd.read_csv(RAW / "raw_ra.csv", usecols=["release_id", "tracks"])
        need = pd.unique(ra_t.loc[ra_t.tracks.notna(), "release_id"])
        log.info(f"release con crediti posizionali da risolvere: {len(need):,}")
    copy_query(cfg, f"""
      SELECT rt.release_id, rt.sequence,
             NULLIF(btrim(rt.position), '') AS position,
             NULLIF(btrim(rt.track_id), '') AS track_id
      FROM release_track rt WHERE rt.release_id = ANY({int_array(need)})
    """, RAW / "raw_reltracks.csv", log)

    # ---- 6. gruppi e varianti di nome
    copy_query(cfg, f"""
      SELECT g.group_artist_id, g.member_artist_id, g.member_name
      FROM group_member g
      WHERE g.group_artist_id = ANY({A}) OR g.member_artist_id = ANY({A})
    """, RAW / "raw_groups.csv", log)

    copy_query(cfg, f"""
      SELECT av.artist_id, av.name
      FROM artist_namevariation av WHERE av.artist_id = ANY({A})
    """, RAW / "raw_namevar.csv", log)

    for csv in sorted(RAW.glob("raw_*.csv")):
        with Timer(f"parquet {csv.stem}", log):
            pd.read_csv(csv, low_memory=False).to_parquet(
                RAW / f"{csv.stem}.parquet", index=False)
    marker.write_text("ok")
    Timer.dump(ROOT / "logs" / "timings.csv")
    log.info("=== ESTRAZIONE COMPLETATA ===")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
