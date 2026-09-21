"""FASE 1c — attributi della popolazione: coorte, attivita', genere musicale.

Da qui in poi non si tocca piu' il database: tutto parte dai parquet di Fase 1a.
"""
from __future__ import annotations
import sys, re
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

RAW = ROOT / "data" / "raw"
DISAMB = re.compile(r"\s*\(\d+\)\s*$")


def raw(name: str) -> pd.DataFrame:
    return pd.read_parquet(RAW / f"{name}.parquet")


def clean_name(s: pd.Series) -> pd.Series:
    """Toglie il suffisso di disambiguazione Discogs: "Mina (3)" -> "Mina"."""
    return s.fillna("").str.replace(DISAMB, "", regex=True).str.strip()


# --------------------------------------------------------------------------
def build_credits(log) -> pd.DataFrame:
    """Tavola unificata dei crediti, con la SPECIFICITA' di ciascuno.

    scope:
      track     credito risolto su una traccia precisa
                (release_track_artist, oppure release_artist.tracks parsato)
      main      artista principale della release (release_artist.extra = 0)
      umbrella  credito secondario senza indicazione di tracce
    """
    ra, rta = raw("raw_ra"), raw("raw_rta")

    # --- crediti a livello traccia dal dump tracce -------------------------
    rta = rta.copy()
    rta["track_key"] = rta.track_id.fillna(
        "S" + rta.release_id.astype(str) + "_" + rta.track_sequence.fillna("?").astype(str))
    t_credits = rta.assign(scope="track", source="rta")[
        ["artist_id", "release_id", "track_key", "role", "scope", "source"]]

    # --- crediti release ---------------------------------------------------
    ra = ra.copy()
    ra["is_main"] = ra.extra.fillna(1).astype(int) == 0
    has_tracks = ra.tracks.notna() & ~ra.is_main

    pos_credits = resolve_positions(ra[has_tracks], log)

    rest = ra[~has_tracks].copy()
    rest["scope"] = np.where(rest.is_main, "main", "umbrella")
    rest["source"] = np.where(rest.is_main, "ra_main", "ra_umbrella")
    rest["track_key"] = pd.NA
    rest = rest[["artist_id", "release_id", "track_key", "role", "scope", "source"]]

    # i crediti posizionali non risolti restano a livello release (umbrella),
    # marcati per poterli contare nel report
    out = pd.concat([t_credits, pos_credits, rest], ignore_index=True)
    log.info("crediti per scope:\n" + out.scope.value_counts().to_string())
    log.info("crediti per fonte:\n" + out.source.value_counts().to_string())
    return out


RANGE_SEP = re.compile(r"\s+(?:to|a|-|–|—)\s+", re.I)


def parse_track_field(s: str) -> list[str] | None:
    """Interpreta il campo `tracks` di Discogs: "A1", "1 to 3", "4, 6, 12",
    "A1, B2 to B4". Testo libero ("all tracks except ...") -> None."""
    if not isinstance(s, str) or not s.strip():
        return None
    s = s.strip()
    if re.search(r"[a-z]{3,}", s, re.I) and not re.fullmatch(
            r"[A-Za-z0-9 ,;&/\-–—]+", s):
        return None
    if re.search(r"\b(all|except|exept|tracks?|tutti|tutte|various|unknown)\b", s, re.I):
        return None
    out = []
    for part in re.split(r"\s*(?:,|&|;|/)\s*", s):
        part = part.strip()
        if not part:
            continue
        m = RANGE_SEP.split(part)
        if len(m) == 2:
            out.append(("RANGE", m[0].strip().upper(), m[1].strip().upper()))
        else:
            out.append(("ONE", part.upper(), None))
    return out or None


def resolve_positions(ra_tracks: pd.DataFrame, log) -> pd.DataFrame:
    """Risolve i crediti release con campo `tracks` in crediti a livello traccia,
    usando la mappa posizione -> traccia estratta da release_track."""
    if ra_tracks.empty:
        return pd.DataFrame(columns=["artist_id", "release_id", "track_key",
                                     "role", "scope", "source"])
    rt = raw("raw_reltracks")
    rt = rt[rt.position.notna()].copy()
    rt["pos_u"] = rt.position.str.upper().str.strip()
    rt["track_key"] = rt.track_id.fillna(
        "S" + rt.release_id.astype(str) + "_" + rt.sequence.astype(str))
    rt = rt.sort_values(["release_id", "sequence"])
    by_rel = {rid: g for rid, g in rt.groupby("release_id")}

    rows, unresolved = [], 0
    for r in ra_tracks.itertuples(index=False):
        spec = parse_track_field(r.tracks)
        g = by_rel.get(r.release_id)
        keys = None
        if spec is not None and g is not None:
            pos = g.pos_u.tolist()
            kk = g.track_key.tolist()
            idx = {p: i for i, p in enumerate(pos)}
            sel = []
            ok = True
            for kind, a, b in spec:
                if kind == "ONE":
                    if a in idx:
                        sel.append(idx[a])
                    else:
                        ok = False
                else:
                    if a in idx and b in idx and idx[a] <= idx[b]:
                        sel.extend(range(idx[a], idx[b] + 1))
                    else:
                        ok = False
            if ok and sel:
                keys = [kk[i] for i in dict.fromkeys(sel)]
        if keys:
            for k in keys:
                rows.append((r.artist_id, r.release_id, k, r.role, "track", "ra_tracks"))
        else:
            unresolved += 1
            rows.append((r.artist_id, r.release_id, pd.NA, r.role, "umbrella",
                         "ra_tracks_unresolved"))
    log.info(f"crediti posizionali: {len(ra_tracks):,} totali, "
             f"{unresolved:,} non risolti ({unresolved/len(ra_tracks):.1%}) "
             f"-> degradati a scope 'umbrella'")
    return pd.DataFrame(rows, columns=["artist_id", "release_id", "track_key",
                                       "role", "scope", "source"])


# --------------------------------------------------------------------------
def build_population(credits: pd.DataFrame, cfg, log) -> pd.DataFrame:
    art = raw("raw_artists")
    rel = raw("raw_releases")[["release_id", "year", "country", "master_id"]]
    cc = cfg["cohort"]

    art["name_clean"] = clean_name(art.name)
    art["realname_clean"] = clean_name(art.realname)

    # ---- attivita' e coorte
    cr = credits[["artist_id", "release_id"]].drop_duplicates().merge(rel, on="release_id", how="left")
    valid = cr.year.between(cc["min_year"], cc["max_year"])
    agg = cr.groupby("artist_id").agg(
        n_release=("release_id", "nunique"),
        n_release_it=("country", lambda s: int((s == "Italy").sum())))
    yr = cr[valid].groupby("artist_id").year.agg(debut_year="min", last_year="max",
                                                 median_year="median")
    pop = art.merge(agg, on="artist_id", how="left").merge(yr, on="artist_id", how="left")

    dec = (pop.debut_year // 10 * 10)
    pop["cohort_decade"] = dec.where(dec >= cc["decade_floor"], cc["decade_floor"] - 10)
    pop["cohort_decade"] = pop.cohort_decade.astype("Int64")
    pop["era"] = np.where(pop.debut_year < 2000, "pre2000",
                          np.where(pop.debut_year.notna(), "post2000", None))

    # ---- genere musicale prevalente
    pop = pop.merge(artist_genre(credits, cfg, log), on="artist_id", how="left")
    pop["musical_genre"] = pop.musical_genre.fillna("Unknown")
    pop["genre_weak"] = pop.genre_weak.fillna(True)

    # ---- gruppo o persona
    gm = raw("raw_groups")
    pop["is_group"] = pop.artist_id.isin(gm.group_artist_id.unique())
    pop["is_member"] = pop.artist_id.isin(gm.member_artist_id.unique())

    log.info(f"popolazione: {len(pop):,} | con anno di debutto: "
             f"{pop.debut_year.notna().sum():,} ({pop.debut_year.notna().mean():.1%}) | "
             f"con genere: {(pop.musical_genre != 'Unknown').sum():,} "
             f"({(pop.musical_genre != 'Unknown').mean():.1%}) | "
             f"gruppi: {pop.is_group.sum():,}")
    return pop


def artist_genre(credits: pd.DataFrame, cfg, log) -> pd.DataFrame:
    """Genere prevalente: tag piu' frequente sulle release accreditate.
    `genre_weak` se il tag top copre meno della soglia (default 40%).
    Se nessuna release ha un master taggato, ripiego sugli stili."""
    g = cfg["musical_genre"]
    rg = raw("raw_relgenre")
    pairs = credits[["artist_id", "release_id"]].drop_duplicates()
    ag = pairs.merge(rg, on="release_id", how="inner")
    cnt = ag.groupby(["artist_id", "genre"]).size().rename("n").reset_index()
    tot = cnt.groupby("artist_id").n.sum().rename("tot")
    ordered = cnt.sort_values(["artist_id", "n"], ascending=[True, False])
    ordered["rank"] = ordered.groupby("artist_id").cumcount()
    first = ordered[ordered["rank"] == 0].set_index("artist_id")
    second = ordered[ordered["rank"] == 1].set_index("artist_id").genre \
                    .rename("musical_genre_2")

    out = pd.DataFrame({"musical_genre": first.genre, "n_genre_tags": tot})
    out["genre_share"] = first.n / tot
    out["genre_weak"] = out.genre_share < g["weak_threshold"]
    out = out.join(second, how="left").reset_index()

    if g.get("fallback_style"):
        missing = set(pairs.artist_id) - set(out.artist_id)
        rs = raw("raw_relstyle")
        as_ = pairs[pairs.artist_id.isin(missing)].merge(rs, on="release_id", how="inner")
        if len(as_):
            c2 = as_.groupby(["artist_id", "style"]).size().rename("n").reset_index()
            t2 = c2.groupby("artist_id").n.sum().rename("tot")
            f2 = c2.sort_values(["artist_id", "n"], ascending=[True, False]) \
                   .groupby("artist_id").head(1).set_index("artist_id")
            add = pd.DataFrame({"musical_genre": f2.style, "n_genre_tags": t2})
            add["genre_share"] = f2.n / t2
            add["genre_weak"] = True          # fonte di ripiego: sempre debole
            add["musical_genre_2"] = pd.NA
            out = pd.concat([out, add.reset_index()], ignore_index=True)
            log.info(f"genere da fallback su master_style: {len(add):,} artisti")
    log.info(f"genere assegnato a {len(out):,} artisti; "
             f"deboli (<{g['weak_threshold']:.0%}): {int(out.genre_weak.sum()):,}")
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1c_population", cfg)
    if common.exists("credits.parquet") and common.exists("population.parquet") and not force:
        log.info("Fase 1c gia' completata, salto")
        return
    with Timer("credits", log):
        credits = build_credits(log)
        common.save(credits, "credits.parquet")
    with Timer("population", log):
        pop = build_population(credits, cfg, log)
        common.save(pop, "population.parquet")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
