"""FASE 1d — inferenza del genere sessuale a cascata.

Livelli, in ordine di priorita':

  1. wikidata_p1953   P21 di Wikidata agganciato via `P1953` (Discogs artist ID).
                      E' un join ESATTO sull'identificativo: nessun matching per
                      nome, nessuna omonimia. Livello piu' affidabile.
  2. wikidata_name    P21 di musicisti italiani agganciati per nome normalizzato
                      (etichetta o alias). Solo se il nome e' UNIVOCO nel blocco
                      Wikidata e nella popolazione Discogs; altrimenti scartato.
  3. onomastic        Primo nome -> genere, con due dizionari combinati:
                      (a) gender-guesser, lookup italiano e globale;
                      (b) prior empirico ricavato dai nomi degli artisti gia'
                          etichettati al livello 1 (sostituisce la lista ISTAT,
                          non disponibile come dataset scaricabile: vedi report).
  4. group_members    Per i gruppi: genere dei membri via `group_member`
                      -> mixed / omogeneo (M o F) / unknown.
  5. unknown

Ogni artista porta `gender`, `label_source` e `confidence`.
"""
from __future__ import annotations
import sys, re, unicodedata
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

RAW = ROOT / "data" / "raw"
DISAMB_RE = re.compile(r"\s*\(\d+\)\s*$")
NON_PERSON = re.compile(
    r"\b(orchestra|ensemble|quartet|quartetto|trio|quintet|coro|choir|band|"
    r"группа|gruppo|studio|records|edizioni|orchestre|the |i |gli |le )\b", re.I)


def norm(s: str) -> str:
    """Normalizzazione per il matching: senza accenti, minuscolo, solo lettere."""
    if not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def first_token(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = re.sub(r"^(dr|prof|maestro|mr|mrs|ms|sig|don)\.?\s+", "", s.strip(), flags=re.I)
    parts = [p for p in re.split(r"[\s\.]+", s) if p]
    return parts[0] if parts else ""


def looks_like_person(name: str) -> bool:
    """Un nome proprio plausibile: 2-4 token, nessun marcatore di ensemble."""
    if not isinstance(name, str) or not name.strip():
        return False
    if NON_PERSON.search(name):
        return False
    toks = [t for t in re.split(r"\s+", name.strip()) if t]
    return 2 <= len(toks) <= 4 and all(len(t) >= 2 for t in toks[:2])


# ---------------------------------------------------------------- livello 1
def level_wikidata_p1953(pop: pd.DataFrame, log) -> pd.DataFrame:
    if not common.exists("wd_by_discogs.parquet"):
        log.warning("blocco Wikidata A assente: livello 1 saltato")
        return pd.DataFrame(columns=["artist_id", "gender", "label_source", "confidence"])
    wd = common.load("wd_by_discogs.parquet")
    if wd.empty:
        return pd.DataFrame(columns=["artist_id", "gender", "label_source", "confidence"])
    wd = wd[~wd.ambiguous & wd.gender_wd.isin(["M", "F"])]
    wd = wd.drop_duplicates("discogs_id")[["discogs_id", "gender_wd"]]
    m = pop[["artist_id"]].merge(wd, left_on="artist_id", right_on="discogs_id", how="inner")
    out = pd.DataFrame({"artist_id": m.artist_id, "gender": m.gender_wd,
                        "label_source": "wikidata_p1953", "confidence": 0.98})
    log.info(f"livello 1 (Wikidata via Discogs ID): {len(out):,} artisti")
    return out


# ---------------------------------------------------------------- livello 2
def level_wikidata_name(pop: pd.DataFrame, done: set, log) -> pd.DataFrame:
    if not common.exists("wd_italian.parquet"):
        return pd.DataFrame(columns=["artist_id", "gender", "label_source", "confidence"])
    wd = common.load("wd_italian.parquet")
    if wd.empty:
        return pd.DataFrame(columns=["artist_id", "gender", "label_source", "confidence"])
    wd = wd[wd.gender_wd.isin(["M", "F"])]
    names = pd.concat([
        wd[["wd_qid", "gender_wd", "label"]].rename(columns={"label": "nm"}),
        wd[["wd_qid", "gender_wd", "alias"]].rename(columns={"alias": "nm"})])
    names = names.dropna(subset=["nm"])
    names["key"] = names.nm.map(norm)
    names = names[names.key.str.len() >= 4]
    # un nome usato da piu' persone Wikidata con generi discordi -> ambiguo
    g = names.groupby("key").gender_wd.nunique()
    names = names[names.key.isin(g[g == 1].index)].drop_duplicates("key")[["key", "gender_wd"]]

    cand = pop[~pop.artist_id.isin(done)].copy()
    cand["key"] = cand.name_clean.map(norm)
    # e il nome deve essere univoco anche dentro Discogs
    dup = cand.key.value_counts()
    cand = cand[cand.key.map(dup).eq(1) & cand.key.str.len().ge(4)]
    m = cand.merge(names, on="key", how="inner")
    out = pd.DataFrame({"artist_id": m.artist_id, "gender": m.gender_wd,
                        "label_source": "wikidata_name", "confidence": 0.85})
    log.info(f"livello 2 (Wikidata per nome): {len(out):,} artisti")
    return out


# ---------------------------------------------------------------- livello 3
def _name_gender_table(names: pd.DataFrame, gmap: dict, min_n: int,
                       min_purity: float) -> pd.DataFrame:
    """Tabella primo-nome -> genere a partire da artisti gia' etichettati."""
    d = names.copy()
    d["gender"] = d.artist_id.map(gmap)
    d = d[d.gender.isin(["M", "F"])]
    src = d.realname.fillna("").where(d.realname.fillna("").str.len() > 0, d.name.fillna(""))
    src = src.str.replace(DISAMB_RE, "", regex=True)
    d = d.assign(fn=src.map(first_token).map(norm))
    d = d[d.fn.str.len() >= 3]
    t = d.groupby(["fn", "gender"]).size().unstack(fill_value=0)
    for c in ("M", "F"):
        if c not in t:
            t[c] = 0
    t["n"] = t.M + t.F
    t["purity"] = t[["M", "F"]].max(axis=1) / t.n
    t["gender"] = np.where(t.M >= t.F, "M", "F")
    return t[(t.n >= min_n) & (t.purity >= min_purity)]


def empirical_priors(pop: pd.DataFrame, lab: pd.DataFrame, log):
    """Due dizionari onomastici, in ordine di priorita'.

    `prior_it`  costruito sui SOLI artisti italiani della popolazione che
                Wikidata etichetta con certezza. Piccolo ma culturalmente
                calibrato: sa che Andrea, Simone, Nicola, Michele sono nomi
                maschili in Italia.
    `prior_glob` costruito su tutti i 199.812 artisti Discogs che Wikidata
                etichetta, in tutto il mondo. Molto piu' ampio, ma da usare
                solo quando il nome NON e' riconosciuto come italiano: il
                dizionario globale e' dominato dall'inglese e rovescerebbe
                il genere dei nomi appena citati.

    Insieme sostituiscono la lista onomastica ISTAT, che in questo ambiente
    non e' reperibile come dataset scaricabile (vedi report, limiti).
    """
    wd_lab = lab[lab.label_source == "wikidata_p1953"].set_index("artist_id").gender.to_dict()

    it_names = pop[["artist_id", "name", "realname"]]
    prior_it = _name_gender_table(it_names, wd_lab, min_n=3, min_purity=0.85)

    glob_path = RAW / "raw_wd_names.parquet"
    if glob_path.exists():
        wd = common.load("wd_by_discogs.parquet")
        gmap_all = dict(zip(wd[~wd.ambiguous].discogs_id, wd[~wd.ambiguous].gender_wd))
        prior_glob = _name_gender_table(pd.read_parquet(glob_path), gmap_all,
                                        min_n=10, min_purity=0.92)
    else:
        log.warning("corpus globale dei nomi assente: solo prior italiano")
        prior_glob = prior_it.iloc[:0]

    log.info(f"prior onomastico italiano: {len(prior_it):,} nomi "
             f"(da {len(wd_lab):,} artisti etichettati)")
    log.info(f"prior onomastico globale:  {len(prior_glob):,} nomi "
             f"(da {len(prior_glob.n.sum() and prior_glob) and int(prior_glob.n.sum()):,} osservazioni)")
    # quanti nomi i due dizionari valutano in modo opposto: misura diretta
    # del rischio che si correrebbe usando il solo dizionario globale
    both = prior_it.join(prior_glob[["gender"]], rsuffix="_glob", how="inner")
    disc = both[both.gender != both.gender_glob]
    log.info(f"nomi su cui i due prior sono in disaccordo: {len(disc):,} "
             f"({len(disc)/max(len(both),1):.1%} di {len(both):,} in comune)")
    if len(disc):
        log.info("  esempi: " + ", ".join(disc.index[:12]))
    common.save(prior_it.reset_index(), "onomastic_prior_it.parquet")
    common.save(prior_glob.reset_index(), "onomastic_prior_global.parquet")
    common.save(disc.reset_index(), "onomastic_prior_disaccordo.parquet")
    return (dict(zip(prior_it.index, prior_it.gender)),
            dict(zip(prior_glob.index, prior_glob.gender)))


def level_onomastic(pop: pd.DataFrame, done: set, priors, cfg, log) -> pd.DataFrame:
    """Cascata onomastica. L'ordine e' deliberato: prima le fonti calibrate
    sull'italiano, poi quelle globali, e queste ultime SOLO per nomi che il
    lookup italiano non conosce."""
    import gender_guesser.detector as gd
    prior_it, prior_glob = priors
    det = gd.Detector(case_sensitive=False)
    conf = cfg["gender"]["onomastic"]
    gg_conf, min_acc = conf["gender_guesser_confidence"], conf["min_confidence_accept"]

    cand = pop[~pop.artist_id.isin(done) & ~pop.is_group].copy()
    src = cand.realname_clean.where(cand.realname_clean.str.len() > 0, cand.name_clean) \
        if conf["use_realname_first"] else cand.name_clean
    cand["person_like"] = src.map(looks_like_person)
    cand["fn_raw"] = src.map(first_token)
    cand["fn"] = cand.fn_raw.map(norm)
    cand = cand[cand.person_like & cand.fn.str.len().ge(3)]
    log.info(f"livello 3: {len(cand):,} candidati con un nome proprio plausibile")

    rows = []
    for r in cand.itertuples(index=False):
        g_it = det.get_gender(r.fn_raw, "italy")
        noto_in_italia = g_it not in ("unknown", "andy")
        # 1. prior empirico italiano
        if r.fn in prior_it:
            rows.append((r.artist_id, prior_it[r.fn], "onomastico_prior_it",
                         conf["istat_confidence"]))
        # 2. gender-guesser, lookup italiano
        elif g_it in ("male", "mostly_male"):
            rows.append((r.artist_id, "M", f"onomastico_gg_it_{g_it}", gg_conf[g_it]))
        elif g_it in ("female", "mostly_female"):
            rows.append((r.artist_id, "F", f"onomastico_gg_it_{g_it}", gg_conf[g_it]))
        # 3. prior globale, solo per nomi che l'italiano non conosce
        elif not noto_in_italia and r.fn in prior_glob:
            rows.append((r.artist_id, prior_glob[r.fn], "onomastico_prior_globale", 0.80))
        else:
            g_gl = det.get_gender(r.fn_raw)
            if g_gl in ("male", "mostly_male"):
                rows.append((r.artist_id, "M", f"onomastico_gg_globale_{g_gl}",
                             gg_conf[g_gl] - 0.10))
            elif g_gl in ("female", "mostly_female"):
                rows.append((r.artist_id, "F", f"onomastico_gg_globale_{g_gl}",
                             gg_conf[g_gl] - 0.10))
    out = pd.DataFrame(rows, columns=["artist_id", "gender", "label_source", "confidence"])
    out = out[out.confidence >= min_acc]
    log.info(f"livello 3 (onomastico): {len(out):,} artisti\n" +
             out.label_source.value_counts().to_string())
    return out


# ---------------------------------------------------------------- livello 4
def level_groups(pop: pd.DataFrame, indiv: pd.DataFrame, cfg, log) -> pd.DataFrame:
    """Per i gruppi, il genere si legge dalla composizione: se i membri noti
    sono di entrambi i generi -> `mixed`; se sono tutti dello stesso -> quello;
    se se ne conoscono troppo pochi -> `unknown`."""
    gm = pd.read_parquet(RAW / "raw_groups.parquet")
    c = cfg["gender"]["group_members"]
    gmap = dict(zip(indiv.artist_id, indiv.gender))
    groups = pop[pop.is_group].artist_id
    gm = gm[gm.group_artist_id.isin(groups)].copy()
    gm["mg"] = gm.member_artist_id.map(gmap)
    known = gm[gm.mg.isin(["M", "F"])]
    agg = known.groupby("group_artist_id").mg.agg(["nunique", "count",
                                                   lambda s: s.mode().iat[0]])
    agg.columns = ["nun", "n", "modal"]
    agg = agg[agg.n >= c["min_members_known"]]
    gender = np.where(agg.nun > 1, "mixed", agg.modal)
    confidence = np.where(agg.nun > 1, c["confidence_mixed"], c["confidence_homogeneous"])
    out = pd.DataFrame({"artist_id": agg.index, "gender": gender,
                        "label_source": "group_members", "confidence": confidence})
    log.info(f"livello 4 (composizione dei gruppi): {len(out):,} gruppi risolti "
             f"({(out.gender == 'mixed').sum():,} mixed) su {len(groups):,} gruppi totali")
    return out


# --------------------------------------------------------------------------
def build(cfg, log) -> pd.DataFrame:
    pop = common.load("population.parquet")
    l1 = level_wikidata_p1953(pop, log)
    done = set(l1.artist_id)
    l2 = level_wikidata_name(pop, done, log)
    done |= set(l2.artist_id)
    priors = empirical_priors(pop, l1, log)
    l3 = level_onomastic(pop, done, priors, cfg, log)

    indiv = pd.concat([l1, l2, l3], ignore_index=True).drop_duplicates("artist_id")
    l4 = level_groups(pop, indiv, cfg, log)

    # i gruppi risolti dalla composizione prevalgono sull'onomastica, che su un
    # nome di band non e' informativa; non prevalgono su Wikidata P1953.
    keep_wd = set(l1.artist_id)
    l4 = l4[~l4.artist_id.isin(keep_wd)]
    lab = pd.concat([l1, l2, l3[~l3.artist_id.isin(l4.artist_id)], l4],
                    ignore_index=True).drop_duplicates("artist_id")

    out = pop.merge(lab, on="artist_id", how="left")
    out["gender"] = out.gender.fillna("unknown")
    out["label_source"] = out.label_source.fillna("none")
    out["confidence"] = out.confidence.fillna(0.0)
    # i gruppi non risolti restano 'unknown', ma si distinguono dai solisti
    out.loc[out.is_group & (out.gender == "unknown"), "label_source"] = "group_unresolved"

    log.info("distribuzione finale del genere:\n" +
             out.gender.value_counts(dropna=False).to_string())
    log.info("per fonte dell'etichetta:\n" + out.label_source.value_counts().to_string())
    return out


def validation_sample(df: pd.DataFrame, cfg, log):
    """Campione per la validazione manuale, stratificato per genere, fascia di
    confidenza e fonte dell'etichetta.

    L'allocazione e' meta' PROPORZIONALE alla dimensione degli strati e meta'
    UNIFORME fra strati. Le due meta' servono a cose diverse: la parte
    proporzionale permette di stimare l'accuratezza complessiva senza
    riponderare, quella uniforme garantisce abbastanza casi anche nei livelli
    rari della cascata, che altrimenti resterebbero non valutabili.

    Dentro ogni strato si privilegiano nomi propri DIVERSI. Senza questo
    accorgimento gli strati piccoli si riempiono di omonimi — il livello
    `mostly_female` del lookup italiano, per esempio, e' quasi tutto fatto di
    artiste chiamate Mary — e la validazione finirebbe per misurare
    l'accuratezza su un solo nome invece che sul livello.
    """
    v = cfg["gender"]["validation"]
    n_tot = v["n"]
    rng = np.random.default_rng(cfg["project"]["seed"])
    d = df.copy()
    d["confidence_bin"] = pd.cut(d.confidence, [-0.01, 0.5, 0.75, 0.9, 1.0],
                                 labels=["0-0.5", "0.5-0.75", "0.75-0.9", "0.9-1"])
    src = d.realname_clean.where(d.realname_clean.str.len() > 0, d.name_clean)
    d["_fn"] = src.map(first_token).map(norm)

    gruppi = list(d.groupby(v["strata"], observed=True))
    k = len(gruppi)
    quota_unif = n_tot // 2
    quota_prop = n_tot - quota_unif
    tot = len(d)

    parti = []
    for chiave, g in gruppi:
        n_unif = quota_unif / k
        n_prop = quota_prop * len(g) / tot
        n_i = max(1, int(round(n_unif + n_prop)))
        n_i = min(n_i, len(g))
        # un nome proprio per volta, finche' bastano; poi si completa a caso
        g = g.sample(frac=1.0, random_state=int(rng.integers(1e6)))
        primi = g.drop_duplicates("_fn")
        scelti = primi.head(n_i)
        if len(scelti) < n_i:
            resto = g[~g.index.isin(scelti.index)]
            scelti = pd.concat([scelti, resto.head(n_i - len(scelti))])
        parti.append(scelti)
    smp = pd.concat(parti)

    # aggiustamento alla dimensione voluta
    if len(smp) > n_tot:
        smp = smp.sample(n_tot, random_state=cfg["project"]["seed"])
    elif len(smp) < n_tot:
        resto = d[~d.artist_id.isin(smp.artist_id)]
        smp = pd.concat([smp, resto.sample(min(len(resto), n_tot - len(smp)),
                                           random_state=cfg["project"]["seed"])])

    cols = ["artist_id", "name", "name_clean", "realname", "profile", "musical_genre",
            "debut_year", "n_release", "is_group", "gender", "label_source",
            "confidence", "confidence_bin"]
    out = smp[cols].copy()
    out["human_gender"] = ""          # da compilare a mano: M / F / mixed / unknown
    out["note"] = ""
    out["profile"] = out.profile.fillna("").str.slice(0, 500)
    out = out.sort_values(["label_source", "gender", "name"])
    p = ROOT / "data" / "validation_sample.csv"
    out.to_csv(p, index=False)

    n_nomi = smp._fn.nunique()
    log.info(f"campione di validazione: {len(out)} righe, {n_nomi} nomi propri "
             f"distinti -> {p}")
    log.info("composizione degli strati:\n" +
             out.groupby(["label_source", "gender"], observed=True).size().to_string())


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase1d_gender", cfg)
    if common.exists("population_gender.parquet") and not force:
        log.info("Fase 1d gia' completata, salto")
        return
    with Timer("gender_cascade", log):
        df = build(cfg, log)
        common.save(df, "population_gender.parquet")
    validation_sample(df, cfg, log)
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
