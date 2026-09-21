"""FASE 2 — rete bipartita artista-opera e proiezione pesata artista-artista.

Peso dell'arco
--------------
Ogni credito porta una SPECIFICITA' `s`, secondo quanto preciso e' il legame
fra artista e musica:

    track     s = 1.00   credito su una traccia precisa
    main      s = 0.70   artista principale della release
    umbrella  s = 0.30   credito secondario senza indicazione di tracce

Il peso fra due artisti u e v somma due termini su tutte le opere condivise:

    w(u,v) = w_t * |tracce condivise|  +  w_r * SUM_release s_u(R) * s_v(R)

Il primo termine premia la collaborazione documentata sulla stessa traccia; il
secondo tiene la co-presenza sulla stessa release, scalata dalla specificita' di
entrambi i crediti. Due artisti accreditati sulla stessa traccia pesano quindi
molto piu' di due nomi che compaiono entrambi, genericamente, sullo stesso
disco. I pesi sono in config e sono un asse di sensibilita' in Fase 5.
"""
from __future__ import annotations
import sys, re, itertools
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

RAW = ROOT / "data" / "raw"
BRACKET = re.compile(r"\[[^\]]*\]")


# ------------------------------------------------------------- ruoli
def split_roles(role: str) -> list[str]:
    """"Written-By, Producer" -> ["Written-By","Producer"];
    "Engineer [Assistant]" -> ["Engineer"]."""
    if not isinstance(role, str) or not role.strip():
        return []
    r = BRACKET.sub("", role)
    return [p.strip() for p in r.split(",") if p.strip()]


# Il vocabolario dei ruoli Discogs e' testo libero e conta migliaia di varianti:
# un elenco chiuso di nomi lascia fuori "Tenor Saxophone", "Double Bass",
# "Soprano Vocals" e centinaia di altri strumenti veri, che finirebbero in
# "other" falsando proprio il confronto fra ruoli creativi ed esecutivi (RQ5).
# Si classifica quindi per famiglie di parole chiave, con gli elenchi del
# config come conferma.
PAT_CREATIVE = re.compile(
    r"\b(written|write|writing|wrote|composed|composer|composition|arrang|"
    r"lyric|words\s+by|music\s+by|songwriter|producer|produced|production|"
    r"remix|adapt|orchestrat|score|scored|compiled|dj\s+mix|libretto|"
    r"instrumentation|co-?produc)\b", re.I)
PAT_PERFORMANCE = re.compile(
    r"\b(vocal|voice|vocals|sing|singer|chorus|choir|backing|lead\s+vocals|"
    r"guitar|bass|drum|percussion|piano|keyboard|organ|synth|moog|rhodes|"
    r"mellotron|clavinet|harpsichord|violin|viola|cello|contrabass|"
    r"double\s+bass|saxophone|sax|trumpet|trombone|horn|flute|clarinet|oboe|"
    r"bassoon|harp|accordion|harmonica|mandolin|banjo|ukulele|sitar|tabla|"
    r"bouzouki|bandoneon|theremin|marimba|vibraphone|xylophone|timpani|tuba|"
    r"cornet|fiddle|lute|zither|strings|brass|woodwind|reeds|instruments?|"
    r"conductor|conducted|orchestra|ensemble|quartet|quintet|trio|septet|"
    r"octet|band|performer|performed|featuring|feat|soloist|solo|"
    r"directed\s+by|accompanied\s+by|turntables|scratches|whistl|clap|"
    r"handclaps|beatbox|rap|mc|toasting|narrator)\b", re.I)
PAT_TECHNICAL = re.compile(
    r"\b(engineer|mixed\s+by|mixing|mastered|mastering|remaster|recorded|"
    r"recording|lacquer|edited\s+by|editing|programmed|programming|"
    r"sequenced|sampler|transfer|restoration|technician|pressed|"
    r"cut\s+by|overdub)\b", re.I)
PAT_PARATESTO = re.compile(
    r"\b(photograph|artwork|art\s+direction|design|graphic|illustration|"
    r"cover|layout|liner\s+notes|sleeve|painting|model|translation|"
    r"translated|coordinator|management|manager|legal|a&r|licens|"
    r"executive|supervisor|research|curat|text\s+by|notes)\b", re.I)


def role_classifier(cfg):
    """Classifica un credito in creative / performance / technical / other.

    L'ordine di precedenza e' creative > performance > technical > paratesto:
    un credito composto come "Written-By, Guitar" descrive prima di tutto un
    apporto autoriale, ed e' li' che va contato.

    I crediti SENZA ruolo esplicito non sono tutti uguali:
      * artista principale della pubblicazione -> e' l'interprete del disco;
      * credito risolto su una traccia precisa -> e' l'artista di quel brano;
      * credito a ombrello senza ruolo -> non dice nulla, resta "other".
    """
    R = cfg["network"]["roles"]
    lut = {}
    for cls, names in R.items():
        for nome in names:
            lut[nome.lower()] = cls

    def classify(role: str, scope: str) -> str:
        parti = split_roles(role)
        if not parti:
            return "performance" if scope in ("main", "track") else "other"
        # 1. conferma dagli elenchi espliciti del config
        cls = {lut.get(x.lower()) for x in parti} - {None}
        if "creative" in cls:
            return "creative"
        if "performance" in cls:
            return "performance"
        # 2. famiglie di parole chiave
        testo = " ".join(parti)
        if PAT_CREATIVE.search(testo):
            return "creative"
        if PAT_PERFORMANCE.search(testo):
            return "performance"
        if "technical" in cls or PAT_TECHNICAL.search(testo):
            return "technical"
        if PAT_PARATESTO.search(testo):
            return "other"
        return "other"

    return classify


# ------------------------------------------------------------- filtri
def filter_credits(credits: pd.DataFrame, cfg, log, overrides: dict | None = None):
    n = {**cfg["network"], **(overrides or {})}
    rel = pd.read_parquet(RAW / "raw_releases.parquet")[["release_id", "year", "country"]]
    size = pd.read_parquet(RAW / "raw_relsize.parquet")
    # le release i cui crediti esistono solo a livello traccia hanno la
    # dimensione contata su release_track_artist
    st = RAW / "raw_relsize_track.parquet"
    if st.exists():
        size = pd.concat([size, pd.read_parquet(st)], ignore_index=True) \
                 .drop_duplicates("release_id")
    various = pd.read_parquet(RAW / "raw_various.parquet")

    c = credits.merge(size, on="release_id", how="left").merge(rel, on="release_id", how="left")
    n0 = len(c)
    c = c[c.n_credited.fillna(1) <= n["max_credits"]]
    log.info(f"filtro max_credits<={n['max_credits']}: {n0:,} -> {len(c):,} crediti")
    # nota: in questo dump l'entita' "Various Artists" e' quasi assente
    # (328 crediti su 92 milioni): le raccolte si riconoscono da n_main > 1.
    if n["exclude_various"] and len(various):
        c = c[~c.release_id.isin(various.release_id)]
        log.info(f"escluse release 'Various Artists': -> {len(c):,} crediti")
    if n.get("exclude_compilations"):
        # euristica: piu' artisti principali distinti = raccolta
        c = c[c.n_main.fillna(1) <= 1]
        log.info(f"escluse raccolte (n_main>1): -> {len(c):,} crediti")
    if not n["use_track_credits"]:
        c.loc[c.scope == "track", "scope"] = "umbrella"
        c["track_key"] = pd.NA
        log.info("crediti a livello traccia disattivati: degradati a 'umbrella'")
    return c, n


# ------------------------------------------------------------- proiezione
def _pairs(df: pd.DataFrame, key: str, weight_col: str | None, w_mult: float,
           max_size: int) -> pd.DataFrame:
    """Coppie non ordinate dentro ciascun gruppo, via self-join.
    I gruppi oltre `max_size` vengono scartati (esplosione quadratica)."""
    sizes = df.groupby(key).artist_id.nunique()
    ok = sizes[(sizes >= 2) & (sizes <= max_size)].index
    d = df[df[key].isin(ok)]
    if d.empty:
        return pd.DataFrame(columns=["u", "v", "w"])
    cols = ["artist_id", key] + ([weight_col] if weight_col else [])
    d = d[cols].drop_duplicates(subset=["artist_id", key]) if not weight_col else \
        d[cols].groupby(["artist_id", key], as_index=False)[weight_col].max()
    m = d.merge(d, on=key, suffixes=("_u", "_v"))
    m = m[m.artist_id_u < m.artist_id_v]
    if m.empty:
        return pd.DataFrame(columns=["u", "v", "w"])
    w = (m[f"{weight_col}_u"] * m[f"{weight_col}_v"] * w_mult) if weight_col else w_mult
    out = pd.DataFrame({"u": m.artist_id_u.values, "v": m.artist_id_v.values, "w": w})
    return out.groupby(["u", "v"], as_index=False).w.sum()


def project(credits: pd.DataFrame, n: dict, log) -> pd.DataFrame:
    sw = n["credit_scope_weight"]
    c = credits.copy()
    c["s"] = c.scope.map(sw).fillna(sw["umbrella"])

    # --- termine 1: tracce condivise
    tr = c[c.track_key.notna()]
    with Timer(f"coppie a livello traccia ({tr.track_key.nunique():,} tracce)", log):
        e_track = _pairs(tr, "track_key", None, n["w_track_shared"], n["max_credits"])
    log.info(f"  archi da tracce condivise: {len(e_track):,}")

    # --- termine 2: co-presenza sulla release, scalata dalla specificita'
    with Timer(f"coppie a livello release ({c.release_id.nunique():,} release)", log):
        e_rel = _pairs(c, "release_id", "s", n["w_release_pair"], n["max_credits"])
    log.info(f"  archi da co-presenza su release: {len(e_rel):,}")

    e = pd.concat([e_track, e_rel], ignore_index=True) \
          .groupby(["u", "v"], as_index=False).w.sum()
    if n["min_edge_weight"] > 0:
        n0 = len(e)
        e = e[e.w >= n["min_edge_weight"]]
        log.info(f"filtro peso minimo {n['min_edge_weight']}: {n0:,} -> {len(e):,} archi")
    log.info(f"ARCHI TOTALI: {len(e):,} | peso: mediana {e.w.median():.2f}, "
             f"media {e.w.mean():.2f}, max {e.w.max():.1f}")
    return e


# ------------------------------------------------------------- grafi
def build_graph(edges: pd.DataFrame, pop: pd.DataFrame) -> nx.Graph:
    G = nx.Graph()
    attrs = pop.set_index("artist_id")
    G.add_nodes_from(attrs.index)
    G.add_weighted_edges_from(edges[["u", "v", "w"]].itertuples(index=False, name=None))
    for col in ["gender", "musical_genre", "cohort_decade", "era", "n_release",
                "label_source", "confidence", "genre_weak", "is_group", "debut_year"]:
        if col in attrs:
            nx.set_node_attributes(G, attrs[col].to_dict(), col)
    return G


def describe(G: nx.Graph, name: str, log) -> dict:
    Gs = G.subgraph([n for n, d in G.degree() if d > 0]).copy()
    comps = sorted(nx.connected_components(Gs), key=len, reverse=True) if Gs.number_of_nodes() else []
    giant = len(comps[0]) if comps else 0
    deg = np.array([d for _, d in Gs.degree()]) if Gs.number_of_nodes() else np.array([0])
    st = {
        "rete": name,
        "nodi_totali": G.number_of_nodes(),
        "nodi_con_archi": Gs.number_of_nodes(),
        "archi": Gs.number_of_edges(),
        "densita": nx.density(Gs) if Gs.number_of_nodes() > 1 else 0.0,
        "grado_medio": float(deg.mean()),
        "grado_mediano": float(np.median(deg)),
        "grado_max": int(deg.max()),
        "componenti": len(comps),
        "componente_gigante": giant,
        "quota_componente_gigante": giant / Gs.number_of_nodes() if Gs.number_of_nodes() else 0.0,
        "peso_totale": float(sum(d["weight"] for *_, d in Gs.edges(data=True))),
    }
    log.info(f"[{name}] nodi {st['nodi_con_archi']:,} archi {st['archi']:,} "
             f"densita {st['densita']:.2e} grado medio {st['grado_medio']:.1f} "
             f"gigante {st['quota_componente_gigante']:.1%}")
    return st


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase2_network", cfg)
    if common.exists("edges_all.parquet") and not force:
        log.info("Fase 2 gia' completata, salto")
        return
    pop = common.load("population_gender.parquet")
    credits = common.load("credits.parquet")
    classify = role_classifier(cfg)
    with Timer("classificazione ruoli", log):
        credits["role_class"] = [classify(r, s) for r, s in
                                 zip(credits.role, credits.scope)]
        common.save(credits, "credits.parquet")
    log.info("crediti per classe di ruolo:\n" + credits.role_class.value_counts().to_string())

    c, n = filter_credits(credits, cfg, log)
    stats = []
    for sub in cfg["network"]["subnetworks"]:
        cc = c if sub == "all" else c[c.role_class == sub]
        log.info(f"--- sottorete '{sub}': {len(cc):,} crediti ---")
        e = project(cc, n, log)
        common.save(e, f"edges_{sub}.parquet")
        G = build_graph(e, pop)
        stats.append(describe(G, sub, log))
    df = pd.DataFrame(stats)
    common.save(df, "network_stats.parquet")
    common.save_table(df, "t2_rete_descrittive",
                      "Descrittive delle reti di collaborazione per sottorete di ruolo")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
