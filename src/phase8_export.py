"""FASE 8 — pacchetto di dati ispezionabile da chi revisiona.

Produce `export/`, che contiene **tutto** il materiale intermedio in formati
aperti, con un manifesto, un dizionario delle colonne e i checksum. L'idea e'
che un revisore debba poter rifare ogni conto senza accesso al database
sorgente e senza eseguire la pipeline.

  export/dati/        ogni dataset in Parquet **e** in CSV (compresso sopra
                      una certa soglia): il Parquet conserva i tipi, il CSV si
                      apre ovunque
  export/tabelle/     le tabelle del report, in CSV e LaTeX
  export/figure/      le figure a 300 dpi
  export/log/         i log di esecuzione e i tempi
  export/MANIFEST.md  che cos'e' ogni file, quante righe, quale fase lo produce
  export/DIZIONARIO.md   significato di ogni colonna dei dataset principali
  export/CHECKSUMS.sha256
  export/README.md    come ispezionare il pacchetto
"""
from __future__ import annotations
import sys, shutil, hashlib, gzip, json
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT, Timer

EXPORT = ROOT / "export"
CSV_GZIP_SOGLIA_MB = 20          # sopra questa dimensione il CSV esce compresso

# --------------------------------------------------------------------------
# A che cosa serve ciascun file. Chi revisiona non deve dedurlo dal nome.
# --------------------------------------------------------------------------
DESCRIZIONI = {
    # --- Fase 1a: estrazione grezza dal database
    "raw/raw_artist_counts": ("1a", "For each artist with at least two Italian "
        "releases: how many there are (n_it) and how many releases in total (n_all). "
        "This is the base from which the population is derived, and the file from "
        "which the inclusion thresholds can be recomputed."),
    "raw/raw_artistmeta": ("1a", "Discogs profile data for the candidates before the "
        "name filter: name, real name, free-text profile, data quality."),
    "raw/raw_artists": ("1a", "Italian population before the exclusion of groups "
        "(D16): 100,201 entries, 12,972 of them groups, with the Italian-release "
        "counts and share."),
    "raw/raw_ra": ("1a", "Credits at RELEASE level (release_artist), for population "
        "artists only. `extra=0` marks the main artist; `tracks` is the text field "
        "with track positions, when present."),
    "raw/raw_rta": ("1a", "Credits at TRACK level (release_track_artist). "
        "`track_id` is the global Discogs track identifier."),
    "raw/raw_releases": ("1a", "Metadata for the releases involved: year extracted "
        "from the text field `released`, country, master identifier."),
    "raw/raw_relsize": ("1a", "Number of artists credited on each release (all of "
        "them, not only Italians). Used by the `max_credits` filter."),
    "raw/raw_relsize_track": ("1a", "The same count for releases that have credits "
        "only at track level and are therefore missing from raw_relsize."),
    "raw/raw_various": ("1a", "Releases attributed to an artist named 'Various'. "
        "There are three: this dump does not use the placeholder."),
    "raw/raw_relgenre": ("1a", "Musical genres of the releases, via master_genre. "
        "This is the only available source: release_genre is empty in the dump."),
    "raw/raw_relstyle": ("1a", "Styles (musical subgenres) via master_style, used as "
        "a fallback when the musical genre is missing."),
    "raw/raw_reltracks": ("1a", "Position-to-track map for releases whose positional "
        "credits need resolving (e.g. 'A1' -> track_id)."),
    "raw/raw_groups": ("1a", "Group membership (group_member): used to identify "
        "groups, which are excluded from the analysis (D16), and, in the version "
        "with groups, to classify a group as mixed-gender or single-gender."),
    "raw/raw_namevar": ("1a", "Stage-name variants recorded in Discogs."),
    "raw/raw_wd_names": ("1b", "Name and real name, taken from Discogs, of the "
        "199,812 artists to whom Wikidata assigns a gender. This is the corpus "
        "from which the onomastic dictionary is built."),

    # --- Fase 1b: Wikidata
    "wd_by_discogs": ("1b", "All Wikidata entities with property P1953 (Discogs "
        "identifier) and P21 (sex or gender). The match is exact on the identifier, "
        "not by name. `ambiguous` flags identifiers linked to several entities "
        "with conflicting genders."),
    "onomastic_prior_it": ("1d", "Name-to-gender dictionary built only from Italian "
        "artists labeled with certainty by Wikidata. `purity` is the share of the "
        "prevailing gender, `n` the number of observations."),
    "onomastic_prior_global": ("1d", "The same dictionary built on the whole "
        "worldwide corpus. Used ONLY for names that the Italian lookup does not "
        "recognize."),
    "onomastic_prior_disaccordo": ("1d", "Names on which the two dictionaries "
        "disagree. It is empty; it is a consistency check, not a result."),

    # --- Fase 1c/1d: popolazione e genere
    "population": ("1c", "Population with the computed attributes: debut year, "
        "cohort decade, era, number of releases, prevailing musical genre and "
        "share of the main tag, whether the artist is a group or a group member."),
    "population_gender": ("1d", "**Central table of the study.** The population of "
        "individual artists (87,229; groups excluded under D16) with the inferred "
        "gender, `label_source` (which level of the cascade produced the label) "
        "and `confidence`."),
    "credits": ("1c", "**Unified credit table**, one row per (artist, context). "
        "`scope` is the specificity: `track` a credit on a specific track, `main` "
        "main artist, `umbrella` a credit with no track indication. `source` says "
        "where the credit comes from. `role_class` is the role classification."),

    # --- Fase 2: rete
    "edges_all": ("2", "Weighted artist-artist projection, full network. `w` is the "
        "weight computed as described in Section 3.1 of the Italian report."),
    "edges_creative": ("2", "The same projection, restricted to creative credits "
        "(production, writing, arrangement, composition)."),
    "edges_performance": ("2", "The same projection, restricted to performing "
        "credits (vocals, instruments, conducting, featuring)."),
    "network_stats": ("2", "Descriptive statistics for the three networks: nodes, "
        "edges, density, degrees, components, share of the giant component."),

    # --- Fase 3: omofilia e posizione
    "assortativity_overall": ("3", "Overall assortativity by gender and by musical "
        "genre, with the mean and standard deviation under the null model."),
    "assortativity_strata": ("3", "Assortativity by role subnetwork and era, with "
        "bootstrap intervals. Computed on all gender categories (M, F, unknown)."),
    "assortativity_mf": ("3", "**Reference measure.** The same assortativity "
        "computed only on edges between nodes with determined gender, shown next "
        "to the version with all categories (unknown included) to make the "
        "artifact visible."),
    "homophily_by_genre": ("3", "Gender homophily within each musical genre, with "
        "observed/expected ratios reported separately for men and women."),
    "women_share": ("3", "Share of women by musical genre and debut decade, with "
        "Wilson intervals."),
    "position": ("3", "Centrality of each node in the giant component: "
        "eigenvector, betweenness (exact, from all sources), coreness, degree, "
        "strength, clustering; plus all the artist attributes."),
    "betweenness_campionata": ("3", "The position regression with betweenness "
        "*approximated* from 400 sources, on the same network: the comparison "
        "term for the exact computation (Phase 3d)."),
    "population_gender_con_gruppi": ("1", "The population with inferred gender "
        "BEFORE the exclusion of groups (D16): 100,201 entries, 12,972 of them "
        "groups."),
    "position_regressions": ("3", "Coefficients of the OLS regressions on network "
        "position, with HC3 heteroskedasticity-robust standard errors."),

    # --- Fase 4: ERGM
    "ergm_coef": ("4", "ERGM coefficients for each subnetwork and each model in the "
        "hierarchy (M0 without gwesp, M1 with gwesp, M2 with nodemix)."),
    "ergm_summary": ("4", "For each subnetwork: size, whether it was sampled, which "
        "models converged, whether the gwesp term held."),

    # --- Fase 5: robustezza
    "mc_gender": ("5", "Outcome of each Monte Carlo replicate of the imputation of "
        "artists with unknown gender, plus the two extreme scenarios."),
    "sensitivity": ("5", "Key metrics under each variant of the network "
        "construction parameters, one change at a time."),
    "genre_weak_variants": ("5", "Key metrics under three different treatments of "
        "artists with a weak musical-genre attribution."),

    # --- Fase 1e: verifica dell'italianita'
    "italy_validation": ("1", "Population artists with a citizenship (P27) recorded "
        "in Wikidata: the check of the Italian-nationality heuristic. `italiano` "
        "says whether at least one citizenship is Italian, historical states "
        "included."),
    "wikidata_enriched": ("1", "Wikidata entities with a Discogs identifier "
        "(P1953): sex or gender (P21), citizenships (P27), occupations, in "
        "batches of QIDs."),
    "wd_italian": ("1", "Wikidata entities with Italian citizenship, used for the "
        "Italian onomastic dictionary."),

    # --- Fase 4c-4j: rete integrale, calcolo esatto, proiezione
    "dyadic_logit": ("4", "Case-control dyadic logit (Phase 4c), SUPERSEDED by the "
        "exact computation: kept as a point of comparison. The intercept is "
        "already corrected to the right sign (error E1)."),
    "qap_gender": ("4", "QAP test with a thousand permutations (Phase 4c), "
        "superseded by the closed form in `permutazione_esatta`."),
    "edges_datati": ("4", "Each edge dated by the year of the first release shared "
        "by the two artists, with the corresponding decade. The basis of the "
        "whole time series."),
    "homophily_temporal": ("4", "Sampled time series (Phase 4d), superseded by "
        "`temporale_esatto`."),
    "logit_esatto": ("4", "**Exact dyadic logit** on all 1,306,346,055 dyads of the "
        "network with determined gender: coefficients, standard errors from the "
        "observed information (which assume independence between dyads), "
        "log-likelihood."),
    "logit_esatto_parziale": ("4", "Per-iteration checkpoint of the exact Newton "
        "estimation; only used to resume an interrupted estimate."),
    "permutazione_esatta": ("4", "UNIFORM permutation of the labels over the whole "
        "network: mean and standard deviation in closed form. Blind to activity: "
        "see `nullo_grado`."),
    "temporale_esatto": ("4", "Series by decade of edge formation: share of women, "
        "ratios under uniform permutation in closed form, exact logit per decade "
        "on all dyads of the period."),
    "nullo_grado": ("4", "**Reference null for the time series** (Phase 4j): "
        "observed over expected within-gender ties when labels are permuted among "
        "artists with the same number of ties (2,000 permutations per decade), "
        "next to the uniform null and to the ratio under the configuration model."),
    "non_persone": ("4", "Population entries whose name signals a non-person "
        "(bands, orchestras, labels, studios, variants of Various), with the "
        "reason (Phase 4l)."),
    "sensibilita_nonpersone": ("4", "Series by decade under the degree-stratified "
        "null, with and without the entries that are not persons (Phase 4l)."),
    "sensibilita_nonpersone_assortativita": ("4", "Gender assortativity and number "
        "of ties, with and without the entries that are not persons (Phase 4l)."),
    "densita_genere": ("4", "By decade and musical genre (ties between artists of "
        "the same musical genre): probability that a woman-woman, man-man or mixed "
        "pair is tied, ratios between these probabilities with Poisson intervals "
        "(optimistic), and observed/expected by pair type under the "
        "degree-stratified permutation, with z. `affidabile` (reliable) = at least "
        "30 women and 10 FF ties."),
    "proiezione_esp": ("4", "For each edge: total shared partners, those imposed by "
        "the bipartite projection, the cast of the largest shared release, and "
        "whether the edge lies beyond the ceiling that a single release can "
        "impose."),
    "proiezione_distribuzione": ("4", "Share of shared partners imposed by the "
        "projection, by number of shared partners."),
    "proiezione_riassunto": ("4", "Summary of the projection measure over all "
        "edges."),
    "fattibilita_paesi": ("feasibility study", "Feasibility of the international comparison "
        "(docs/07-confronto-internazionale.md), one row per candidate country: "
        "releases, entries, groups and individuals, share with a Wikidata gender "
        "and share of women among them, share with a real name, and precision of "
        "the nationality criterion against Wikidata citizenship (P27)."),
    "fattibilita_paesi_decenni": ("feasibility study", "For the same candidate countries, the "
        "number of individual artists by decade of debut, 1950s to 2020s."),
    "proiezione_tetto": ("4","Edges within and beyond the projection ceiling, with "
        "the share of shared partners explained in each group (98.5% against "
        "26.5%)."),
    "proiezione_nulla": ("4", "Distribution of shared partners, observed and from "
        "a degree-preserving randomized bipartite projection (Phase 4i), for "
        "three edge sets."),
    "ergm_full_coef": ("4", "Coefficients of the ERGM estimates on the full network "
        "(Phase 4b). None is valid: see `ergm_full_esiti` and docs/05-ergm.md."),
    "ergm_full_esiti": ("4", "Outcome of the ERGM estimates on the full network, "
        "with the reason each was abandoned."),
    "ergm_decenni_coef": ("4", "ERGM coefficients by decade (Phase 4f); valid only "
        "for the decades that converged: 1930, 1940 and 1950."),
    "ergm_decenni_esiti": ("4", "Outcome of the ERGM estimates by decade."),
    "ergm_bimodale": ("4", "Check of the bimodality in the 1940s (Phase 4h): size "
        "of the U-shaped deviation for the reference model; the three variants do "
        "not converge, the negative control included."),
}

# --------------------------------------------------------------------------
# Significato delle colonne che ricorrono.
# --------------------------------------------------------------------------
DIZIONARIO = {
    "decennio": "Decade in which the edge formed: year of the first release shared by the two artists.",
    "rapporto_uniforme": "Observed within-category edges divided by those expected when labels are permuted "
                         "across all nodes, ignoring degree. Blind to activity.",
    "rapporto_grado": "Observed within-category edges divided by those expected when labels are permuted only "
                      "among nodes with the same degree (strata of at least 30). The reference in the article.",
    "z_grado": "Deviation of the observed count from the mean of the degree-stratified permutation, in standard deviations.",
    "grado_medio_relativo": "Mean degree of the nodes in the category divided by the mean degree of all nodes.",
    "esp": "Edgewise shared partners: number of neighbors common to the two endpoints of an edge.",
    "artist_id": "Discogs artist identifier. Join key across all tables.",
    "release_id": "Discogs release identifier.",
    "track_key": "Track identifier: the Discogs `track_id` when present, "
                 "otherwise a synthetic release+sequence key.",
    "name": "Stage name as it appears in Discogs, disambiguation suffix included.",
    "name_clean": "Stage name without the disambiguation suffix: 'Mina (3)' -> 'Mina'.",
    "realname": "Legal name declared in Discogs, when present.",
    "realname_clean": "As above, cleaned.",
    "profile": "Free descriptive text of the Discogs profile.",
    "n_it": "Number of the artist's releases with country = 'Italy'.",
    "n_all": "Total number of releases credited to the artist.",
    "italian_share": "n_it / n_all. The inclusion threshold is 0.50.",
    "n_release": "Distinct releases on which the artist is credited.",
    "debut_year": "Year of the first dated release credited to the artist.",
    "cohort_decade": "Debut decade. The lowest value is a catch-all bin for "
                     "'everything earlier', not a real decade.",
    "era": "pre2000 or post2000, by debut year.",
    "musical_genre": "Prevailing musical genre: the most frequent tag on the "
                     "artist's releases. 'Unknown' if none is tagged.",
    "musical_genre_2": "Second tag by frequency, used in the robustness variants.",
    "genre_share": "Share of the prevailing tag among all of the artist's musical-genre tags.",
    "genre_weak": "True if the prevailing tag covers less than 40% of the tags.",
    "gender": "Inferred gender: M, F, unknown (`mixed`, a group with members of both "
              "genders, appears only in `population_gender_con_gruppi`, before groups "
              "were excluded under D16). **It is not an observed datum: it is inferred.**",
    "label_source": "Which level of the cascade produced the label. "
                    "`wikidata_p1953` is the most reliable (exact match).",
    "confidence": "Declared confidence for that label, from 0 to 1. It is a "
                  "configuration parameter set per level, not an estimated probability.",
    "is_group": "True if the artist has members registered in Discogs. Groups are "
                "excluded from the analysis (D16), so it is False in `population_gender` "
                "and in the network tables.",
    "is_member": "True if the artist is a member of at least one group.",
    "scope": "Specificity of the credit: track / main / umbrella.",
    "source": "Origin of the credit: rta, ra_main, ra_umbrella, ra_tracks, "
              "ra_tracks_unresolved.",
    "role": "Role as written in Discogs, free text.",
    "role_class": "Normalized role: creative / performance / technical / other.",
    "extra": "Discogs field: 0 = main artist, 1 = secondary credit.",
    "tracks": "Discogs field with the track positions, as text.",
    "u": "First endpoint of the edge (artist_id, always the smaller of the two).",
    "v": "Second endpoint of the edge.",
    "w": "Edge weight: shared tracks plus co-presence scaled by specificity.",
    "eigenvector": "Eigenvector centrality, weighted.",
    "betweenness": "Betweenness centrality, computed exactly from all sources "
                   "(`betweenness_approssimata` is True only if the sampled fallback was used).",
    "coreness": "k-core number: the layer of the dense core to which the node belongs.",
    "degree": "Number of distinct collaborators.",
    "strength": "Sum of the weights of the incident edges.",
    "r": "Newman's assortativity coefficient for categorical attributes.",
    "r_null": "Mean value of the same coefficient under the null model.",
    "ci_lo / ci_hi": "Bounds of the 95% bootstrap confidence interval.",
    "z": "Deviation of the observed value from the null model, in standard deviations.",
    "estimate": "ERGM coefficient, in log-odds.",
    "or": "exp(estimate): the coefficient as an odds ratio.",
    "gender_wd": "Gender according to Wikidata, mapped to M / F / other.",
    "discogs_id": "Value of Wikidata property P1953, i.e. the Discogs artist_id.",
    "ambiguous": "True if the same Discogs identifier is linked to several "
                 "Wikidata entities with conflicting genders: those cases are discarded.",
}


def sha256(path: Path, blocco: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(blocco), b""):
            h.update(chunk)
    return h.hexdigest()


def esporta_dataset(log) -> list[dict]:
    dati = EXPORT / "dati"
    dati.mkdir(parents=True, exist_ok=True)
    righe = []
    sorgenti = sorted((ROOT / "data").glob("*.parquet")) + \
               sorted((ROOT / "data" / "raw").glob("*.parquet"))
    for src in sorgenti:
        chiave = ("raw/" if src.parent.name == "raw" else "") + src.stem
        fase, descr = DESCRIZIONI.get(chiave, ("n/a", "(no description recorded)"))
        dest_dir = dati / ("grezzi" if src.parent.name == "raw" else "elaborati")
        dest_dir.mkdir(parents=True, exist_ok=True)
        pq_dest = dest_dir / src.name
        shutil.copy2(src, pq_dest)

        df = pd.read_parquet(src)
        mb = src.stat().st_size / 1048576
        if mb > CSV_GZIP_SOGLIA_MB or len(df) > 1_000_000:
            csv_dest = dest_dir / f"{src.stem}.csv.gz"
            with gzip.open(csv_dest, "wt", newline="", encoding="utf-8") as fh:
                df.to_csv(fh, index=False)
        else:
            csv_dest = dest_dir / f"{src.stem}.csv"
            df.to_csv(csv_dest, index=False, encoding="utf-8")

        righe.append({
            "file_parquet": str(pq_dest.relative_to(EXPORT)),
            "file_csv": str(csv_dest.relative_to(EXPORT)),
            "fase": fase,
            "righe": len(df),
            "colonne": len(df.columns),
            "elenco_colonne": ", ".join(df.columns),
            "byte_parquet": pq_dest.stat().st_size,
            "byte_csv": csv_dest.stat().st_size,
            "sha256_parquet": sha256(pq_dest),
            "descrizione": descr,
        })
        log.info(f"  {chiave:<38} {len(df):>10,} rows")
    return righe


def copia_contorno(log):
    for sorg, dest in [(ROOT / "report" / "tables", EXPORT / "tabelle"),
                       (ROOT / "report" / "figures", EXPORT / "figure"),
                       (ROOT / "logs", EXPORT / "log")]:
        if not sorg.exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        n = 0
        for f in sorg.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
                n += 1
        log.info(f"  {sorg.name}: {n} files")
    # i risultati grezzi dell'ERGM, cartella per cartella
    eg = ROOT / "data" / "ergm"
    if eg.exists():
        dest = EXPORT / "ergm"
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(eg, dest)
        log.info(f"  ergm: {len(list(dest.iterdir()))} subnetworks")
    # configurazione, campione di validazione, stato delle fonti esterne
    for f in [ROOT / "config.yaml", ROOT / "README.md",
              ROOT / "data" / "validation_sample.csv",
              ROOT / "data" / "wikidata_status.json",
              ROOT / "data" / "report_numbers.json",
              ROOT / "data" / "extract.sql"]:
        if f.exists():
            shutil.copy2(f, EXPORT / f.name)
    for f in [ROOT / "report" / "report.md", ROOT / "report" / "report.html",
              ROOT / "report" / "report.pdf"]:
        if f.exists():
            shutil.copy2(f, EXPORT / f.name)
    # l'articolo, e la documentazione di processo che dice come ci si e' arrivati
    # (il report italiano qui sopra e' fermo al 21 settembre: fa fede l'articolo)
    art = EXPORT / "articolo"
    art.mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "paper").glob("paper_poetics.*"):
        shutil.copy2(f, art / f.name)
    for f in [ROOT / "paper" / "NOTE_PER_AUTORE.md", ROOT / "paper" / "VERIFICA_CITAZIONI.md"]:
        if f.exists():
            shutil.copy2(f, art / f.name)
    for sorg, dest in [(ROOT / "paper" / "figures", art / "figures"),
                       (ROOT / "docs", EXPORT / "docs")]:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(sorg, dest)
    # il codice, cosi' che ogni numero sia rintracciabile fino alla riga che lo produce
    for sorg, dest in [(ROOT / "src", EXPORT / "codice" / "src"),
                       (ROOT / "R", EXPORT / "codice" / "R"),
                       (ROOT / "tests", EXPORT / "codice" / "tests")]:
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(sorg, dest, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "run_all.sh", EXPORT / "codice" / "run_all.sh")


def scrivi_manifesto(righe: list[dict], cfg, log):
    man = pd.DataFrame(righe)
    man.to_csv(EXPORT / "manifest.csv", index=False)

    def mb(b):
        return f"{b/1048576:.1f} MB" if b >= 1048576 else f"{b/1024:.0f} KB"

    sezioni = {"elaborati": "Processed datasets",
               "grezzi": "Raw datasets (extracted from the database)"}
    corpo = []
    for chiave, titolo in sezioni.items():
        sub = man[man.file_parquet.str.contains(f"/{chiave}/")]
        if sub.empty:
            continue
        corpo.append(f"\n## {titolo}\n")
        for _, r in sub.sort_values("fase").iterrows():
            corpo.append(
                f"### `{Path(r.file_parquet).name}`\n\n"
                f"*Phase {r.fase}; {r.righe:,} rows × {r.colonne} columns; "
                f"{mb(r.byte_parquet)} as Parquet, {mb(r.byte_csv)} as CSV*\n\n"
                f"{r.descrizione}\n\n"
                f"**Columns:** `{r.elenco_colonne}`\n\n"
                f"**Paths:** `{r.file_parquet}` · `{r.file_csv}`\n\n"
                f"**sha256 (Parquet):** `{r.sha256_parquet}`\n")
    # data in inglese, senza dipendere dal locale del sistema
    ora = pd.Timestamp.now()
    mesi = ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]
    quando = f"{ora.day} {mesi[ora.month - 1]} {ora.year}, {ora:%H:%M}"
    testo = ("# Data manifest\n\n"
             f"Package generated on {quando}. "
             f"It contains {len(man)} datasets, "
             f"{man.righe.sum():,} rows in total.\n\n"
             "Each dataset is provided **twice**: as Parquet, which preserves the "
             "column types and can be read by pandas, R (arrow), DuckDB and Polars; "
             "and as CSV, which opens anywhere. The largest CSV files are "
             "compressed with gzip.\n"
             + "".join(corpo))
    (EXPORT / "MANIFEST.md").write_text(testo)
    log.info(f"manifest: {len(man)} datasets, {man.righe.sum():,} rows")
    return man


def scrivi_dizionario(log):
    voci = "\n".join(f"| `{k}` | {v} |" for k, v in sorted(DIZIONARIO.items()))
    testo = f"""# Column dictionary

Meaning of the columns that recur across the datasets. Columns specific to a
single table are described in the manifest, next to that table.

| column | meaning |
|---|---|
{voci}

## Three caveats to read before using the data

**Gender is inferred, not observed.** The `gender` column does not come from
any source: it is the output of the cascade described in Section 3.2 of the
article (and in Section 2 of the Italian report). `label_source` says which
level each label comes from and `confidence` how much trust is placed in it.
Labels from `wikidata_p1953` come from an exact match on the Discogs
identifier and are the most solid; onomastic labels are inferences from the
first name. The manual validation was carried out on 25 September 2026: 200
artists drawn by stratified sampling were coded blind by the author. The
cascade's M/F labels agree with the annotator in 94.6% of cases (97.5% of
the cases the annotator could determine, with 4 M/F reversals). The sample,
with the `human_gender` column filled in, is in `validation_sample.csv`.

**Italian status is a share, not a nationality.** An artist enters the
population if at least half of their releases have `country = 'Italy'`. It is
a criterion based on place of release, not on biography, because the dump
contains neither nationality nor ties to record labels.

**`unknown` is not a category like the others.** Artists of undetermined
gender collaborate with each other more than chance would predict, but for
reasons of data coverage, not social ones. The study's reference measures
exclude them; the datasets keep them so that excluding them remains the
analyst's choice rather than information already lost.
"""
    (EXPORT / "DIZIONARIO.md").write_text(testo)


def scrivi_readme(man: pd.DataFrame, cfg, log):
    testo = f"""# Data package: gender homophily in Italian music collaborations

This package contains all the intermediate material of the study, in open
formats, so that reviewers can redo the computations without access to the
source database and without rerunning the pipeline.

**Confidentiality.** The package contains the unpublished manuscript
(`articolo/`). It must not be deposited publicly (for example on Zenodo) until
the article is published.

## Contents

```
MANIFEST.md        what each file is, how many rows, which phase produces it
DIZIONARIO.md      meaning of each column (column dictionary)
manifest.csv       the same manifest in tabular form
CHECKSUMS.sha256   hash of every file
config.yaml        all the parameters used in this run
extract.sql        the database extraction queries
articolo/          the article for Poetics (MD, PDF, DOCX), figures, notes for the author
docs/              the process documentation: decisions, errors, ERGM log
report.pdf/.html/.md   the Italian report, FROZEN AT 21 SEPTEMBER: it presents
                       the withdrawn thesis. The article is authoritative
validation_sample.csv  sample for the manual gender validation (human_gender filled in)
wikidata_status.json   outcome of the Wikidata retrieval, degradations included
report_numbers.json    every figure cited in the report, in machine-readable form

dati/elaborati/    the datasets produced by the analysis   (Parquet + CSV)
dati/grezzi/       the data extracted from the database    (Parquet + CSV)
tabelle/           the report tables                       (CSV + LaTeX)
figure/            the figures                             (PNG 300 dpi)
ergm/              raw input and output of each ERGM model
log/               execution logs and timings of each phase
codice/            the complete source code, with the verification tests
```

## How to open the files

```python
import pandas as pd
pop = pd.read_parquet("dati/elaborati/population_gender.parquet")
archi = pd.read_parquet("dati/elaborati/edges_all.parquet")
```

```r
library(arrow)
pop <- read_parquet("dati/elaborati/population_gender.parquet")
```

```sql
-- DuckDB, without importing anything
SELECT gender, count(*) FROM 'dati/elaborati/population_gender.parquet' GROUP BY 1;
```

The CSV files open with any tool; those above {CSV_GZIP_SOGLIA_MB} MB are
compressed with gzip (`pandas.read_csv` reads them directly).

## Where to start to check a number

| to check | start from |
|---|---|
| the definition of the population | `dati/grezzi/raw_artist_counts.parquet`: it contains n_it and n_all for all candidates, so the thresholds can be recomputed |
| the gender inference | `dati/elaborati/population_gender.parquet` plus `wd_by_discogs.parquet` and the two `onomastic_prior_*` files |
| the edge weights | `dati/elaborati/credits.parquet` (columns `scope` and `source`) and `edges_all.parquet` |
| homophily | `assortativity_mf.parquet` is the reference measure; `assortativity_strata.parquet` the version with all gender categories |
| network position | `position.parquet` and `position_regressions.parquet` |
| the time series (main result) | `edges_datati.parquet`, then `nullo_grado.parquet` (reference null) and `temporale_esatto.parquet` (uniform null and logit by decade) |
| the logit on the full network | `logit_esatto.parquet`; the case-control comparison in `dyadic_logit.parquet` |
| the projection artifact | `proiezione_esp.parquet` (edge by edge), `proiezione_tetto.parquet`, `proiezione_nulla.parquet` |
| the ERGMs | `ergm/<subnetwork>/` contains nodes.csv, edges.csv, control.json and the results |

## Reproducibility

Random seed: **{cfg['project']['seed']}**. The complete code is in `codice/`;
`codice/run_all.sh` reruns the whole pipeline. The only step that cannot be
reproduced without the source database is Phase 1a, whose outputs are,
however, included here in `dati/grezzi/`.

## Caveat

Gender is **inferred**, not observed; its manual validation on 200 artists
found 94.6% agreement on the M/F labels. Italian status is defined by country
of release, not by biography. Both limits are discussed in the article
(Sections 3.1 and 3.2) and summarized in `DIZIONARIO.md`.
"""
    (EXPORT / "README.md").write_text(testo)


def scrivi_checksum(log):
    righe = []
    for f in sorted(EXPORT.rglob("*")):
        if f.is_file() and f.name != "CHECKSUMS.sha256":
            righe.append(f"{sha256(f)}  {f.relative_to(EXPORT)}")
    (EXPORT / "CHECKSUMS.sha256").write_text("\n".join(righe) + "\n")
    log.info(f"checksums: {len(righe)} files")


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase8_export", cfg)
    if EXPORT.exists():
        shutil.rmtree(EXPORT)
    EXPORT.mkdir(parents=True)
    with Timer("dataset export", log):
        righe = esporta_dataset(log)
    with Timer("copying tables, figures, logs and code", log):
        copia_contorno(log)
    man = scrivi_manifesto(righe, cfg, log)
    scrivi_dizionario(log)
    scrivi_readme(man, cfg, log)
    with Timer("checksum", log):
        scrivi_checksum(log)
    tot = sum(f.stat().st_size for f in EXPORT.rglob("*") if f.is_file())
    log.info(f"package: {EXPORT} ({tot/1048576:.0f} MB)")
    # archivio unico, per chi preferisce scaricare un file solo
    with Timer("tar.gz archive", log):
        import tarfile
        arch = ROOT / "gender_collab_export.tar.gz"
        if arch.exists():
            arch.unlink()
        with tarfile.open(arch, "w:gz", compresslevel=6) as tf:
            tf.add(EXPORT, arcname="gender_collab_export")
        log.info(f"archive: {arch} ({arch.stat().st_size/1048576:.0f} MB)")
    log.info("=== export completed ===")
    arch = ROOT / "gender_collab_export.tar.gz"
    common.write_json({"percorso": str(EXPORT), "byte": tot,
                       "archivio": str(arch) if arch.exists() else None,
                       "byte_archivio": arch.stat().st_size if arch.exists() else None,
                       "dataset": len(man), "righe_totali": int(man.righe.sum())},
                      "export_status.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
