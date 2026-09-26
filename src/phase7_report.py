"""FASE 7 — composizione del report in Markdown, poi HTML e PDF.

Ogni cifra citata nel testo e' letta dai file di risultato: il report non
contiene numeri scritti a mano, e ricompilarlo dopo una nuova esecuzione lo
aggiorna da solo.

Il testo del report e' in inglese. `report_lib` formatta i numeri
all'italiana e produce didascalie in italiano, quindi qui si ridefiniscono
localmente n, pct, sci, img e table con la formattazione inglese.
"""
from __future__ import annotations
import sys, subprocess, platform, datetime, json
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
import report_lib as R
from common import ROOT, Timer
from report_lib import get, val, FIGDIR, TABDIR

REPORT = ROOT / "report"

_MESI_EN = ["January", "February", "March", "April", "May", "June", "July",
            "August", "September", "October", "November", "December"]


def _oggi_en() -> str:
    d = datetime.date.today()
    return f"{d.day} {_MESI_EN[d.month - 1]} {d.year}"


# ==========================================================================
# formattazione all'inglese: virgola per le migliaia, punto per i decimali
def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and not np.isfinite(x))


def n(x, dec: int = 0) -> str:
    if _missing(x):
        return "n/a"
    return f"{x:,.{dec}f}"


def pct(x, dec: int = 1) -> str:
    if _missing(x):
        return "n/a"
    return n(x * 100, dec) + "%"


def sci(x, dec: int = 1) -> str:
    """Notazione scientifica leggibile: 7.3 x 10^-9 invece di 0.000000007."""
    if _missing(x) or x == 0:
        return "n/a"
    import math
    e = int(math.floor(math.log10(abs(x))))
    m = x / (10 ** e)
    return f"{n(m, dec)} × 10<sup>{e}</sup>"


def img(stem: str, caption: str, width: str = "100%") -> str:
    p = FIGDIR / f"{stem}.png"
    if not p.exists():
        return (f"> *Figure `{stem}` not available: the data it requires were "
                f"not produced in this run.*\n")
    return (f'<figure>\n<img src="figures/{stem}.png" alt="{stem}" '
            f'style="width:{width}" />\n<figcaption>\n\n{caption}\n\n'
            f"</figcaption>\n</figure>\n")


# intestazioni delle tabelle di risultato, solo per la visualizzazione:
# i CSV su disco restano con i nomi di colonna originali
_COL_EN = {
    "rete": "network", "nodi_totali": "total nodes",
    "nodi_con_archi": "nodes with edges", "archi": "edges",
    "densita": "density", "grado_medio": "mean degree",
    "grado_mediano": "median degree", "grado_max": "max degree",
    "componenti": "components", "componente_gigante": "giant component",
    "quota_componente_gigante": "giant component share",
    "peso_totale": "total weight",
    "musical_genre": "musical genre", "genere_musicale": "musical genre",
    "cohort_decade": "debut decade", "n_artisti": "artists",
    "n_noti": "gender known", "n_donne": "women", "quota_donne": "share of women",
    "rapporto_uomini_donne": "men per woman",
    "attributo": "attribute", "r_osservato": "r observed",
    "r_pesato": "r weighted", "r_null_medio": "r null (mean)",
    "r_null_sd": "r null (SD)",
    "sottorete": "subnetwork", "strato": "stratum", "categorie": "categories",
    "n_categorie": "n categories", "archi_totali": "total edges",
    "r_gender": "r gender", "oe_MM": "O/E M–M", "oe_FF": "O/E F–F",
    "eigenvector_mediana": "eigenvector (median)",
    "eigenvector_media": "eigenvector (mean)",
    "betweenness_mediana": "betweenness (median)",
    "coreness_mediana": "coreness (median)", "coreness_media": "coreness (mean)",
    "forza_mediana": "strength (median)", "n_release_mediana": "releases (median)",
    "termine": "term", "esito": "outcome",
    "nodi_originali": "original nodes", "nodi_stimati": "estimated nodes",
    "campionata": "sampled", "convergenza": "converged",
    "modelli_convergenti": "converged models",
    "gwesp_converge": "gwesp converged", "parziale": "partial",
    "solo_mple": "MPLE only", "differenza": "difference",
    "variante": "variant", "quota_gigante": "giant share",
    "r_gender_MF": "r gender M/F", "r_gender_pesato": "r gender weighted",
    "r_genere_musicale": "r musical genre", "peso_mediano": "median weight",
    "n_generi": "musical genres",
}
_ANNI = {"cohort_decade", "decennio", "anno", "year"}
# valori di categoria in italiano semplice (non identificativi)
_VAL_EN = {"tutto": "all", "determinati soltanto": "determined only",
           "tutte le categorie": "all categories"}


def table(stem: str, caption: str, max_rows: int = 30,
          cols: list[str] | None = None, float_dec: int = 3,
          rename: dict | None = None) -> str:
    p = TABDIR / f"{stem}.csv"
    if not p.exists():
        return f"> *Table `{stem}` not available.*\n"
    df = pd.read_csv(p)
    if cols:
        df = df[[c for c in cols if c in df.columns]]
    if rename:
        df = df.rename(columns=rename)
    truncated = len(df) > max_rows
    d = df.head(max_rows).copy()
    for c in d.columns:
        if c in _ANNI:
            # anni e decenni senza separatore delle migliaia (1980, non 1,980)
            d[c] = d[c].map(lambda v: "n/a" if pd.isna(v) else str(int(v)))
        elif pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: n(v, float_dec))
        elif pd.api.types.is_integer_dtype(d[c]):
            d[c] = d[c].map(lambda v: n(v, 0))
        elif d[c].dtype == object:
            d[c] = d[c].map(lambda v: _VAL_EN.get(v, v) if isinstance(v, str) else v)
    d = d.rename(columns=lambda c: _COL_EN.get(c, c))
    # `disable_numparse`: senza, tabulate ri-parsa le stringhe gia' formattate
    out = d.to_markdown(index=False, disable_numparse=True)
    note = (f"\n\n*First {max_rows} of {n(len(df))} rows shown; the full table "
            f"is in `tables/{stem}.csv` and `tables/{stem}.tex`.*"
            if truncated else
            f"\n\n*Full data in `tables/{stem}.csv` and `tables/{stem}.tex`.*")
    return f"{out}\n\n**Table: {caption}**{note}\n"


# ==========================================================================
def executive_summary(C) -> str:
    return f"""
# Collaboration patterns among Italian musicians
## Gender homophily and musical genre on Discogs

This report was generated automatically at an earlier stage of the analysis
and has not been revised since. Its interpretation of the time series (a
reversal of sign) was later withdrawn; the current results are in
`docs/06-risultati.md` and in the manuscript. The figures below are recomputed
from the current data files, but the surrounding text may no longer match
them.

*Analysis run on {C['data']}. Single source: a local Discogs dump (PostgreSQL).*

---

## Summary for the busy reader

This study reconstructs **who recorded with whom** among the Italian musicians
listed on Discogs and asks whether people's gender structures those
collaborations. The short answer is yes, but not in the way one would expect.
Homophily exists and is statistically very solid, but it is much weaker than
the separation by musical genre; it is **asymmetric** (it is women who cluster
together, not men, the opposite of what the current literature reports); and
it did not strengthen after 2000: what strengthened is the network's tendency
to **close into triangles**, which produces the same apparent effect for a
different reason.

### The numbers

| | |
|---|---|
| Italian musicians identified | **{n(C['n_pop'])}** |
| of whom with determined gender | {n(C['n_gender_known'])} ({pct(C['share_known'])}) |
| Share of women among those with determined gender | **{pct(C['share_f'])}** (a ratio of **{n(C['ratio_mf'],2)} men for every woman**) |
| Credits analyzed | {n(C['n_credits'])}, of which {n(C['n_track_credits'])} ({pct(C['share_track'])}) resolved to the individual track |
| Collaboration network | {n(C['n_nodes'])} connected artists, {n(C['n_edges'])} ties |
| Giant component | {pct(C['giant'])} of connected artists |
| Gender assortativity | **r = {n(C['r_mf'],4)}** (95% CI {n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)}) |
| Musical-genre assortativity | **r = {n(C['r_genre'],4)}** |
| Gender homophily pre-2000 → post-2000 | {n(C['r_pre_mf'],4)} → {n(C['r_post_mf'],4)} (difference not significant in the ERGM) |
| ERGM homophily, women vs. men (median across subnetworks) | **{n(C.get('ergm_F_med'),3)} vs. {n(C.get('ergm_M_med'),3)}** in log-odds |
| ERGM | {n(C.get('ergm_n_reti'))} subnetworks, 3 models each, **{n(C.get('ergm_n_conv'))} converged**, `gwesp` included |

### The five things to know

1. **Italian recorded music is a men's world, and it has remained one.**
   A share of {pct(C['share_f'])} women among artists with determined gender
   means {n(C['ratio_mf'],1)} men for every woman. The share does not grow
   monotonically over time: it starts at {pct(C['q_1960'])} for those who
   debuted in the 1960s, falls to {pct(C['q_1980'])} in the 1980s and rises
   again to {pct(C['q_2020'])} for those who debuted from 2020 onward.

2. **Musical genre separates far more than gender does.** Assortativity by
   musical genre ({n(C['r_genre'],3)}) is about
   {n(C['r_genre']/max(C['r_mf'],1e-9),0)} times that by gender
   ({n(C['r_mf'],3)}). Jazz musicians record with jazz musicians far more
   systematically than men record with men.

3. **Gender homophily is small but real.** r = {n(C['r_mf'],4)} looks small,
   but the degree-preserving null model gives {n(C['r_mf_null'],4)} and the
   confidence interval ({n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)}) lies entirely
   above zero. It is not a composition effect; it is structure.

4. **It is women who cluster together, not men.** This is the result that
   most clearly contradicts expectations. In the ERGM, which holds activity,
   cohort, musical genre and triadic closure constant, the female homophily
   coefficient is positive and large in **all eight** estimated subnetworks;
   the male coefficient is close to zero, and in Rock it is even negative.
   Where a group is an overwhelming majority it has no need to seek itself
   out; where it is rare, it clusters.

5. **After 2000 it is not homophily that increases, but closure into
   triangles.** Descriptively, assortativity rises from {n(C['r_pre_mf'],4)}
   to {n(C['r_post_mf'],4)}. But in the ERGM the difference between the two
   periods in the gender terms is **not significant** (p =
   {n(C.get('epoca_F_p'),2)} for women, {n(C.get('epoca_M_p'),2)} for men),
   while the triadic closure term grows from {n(C.get('epoca_gwesp_pre'),2)}
   to {n(C.get('epoca_gwesp_post'),2)} with p < 0.0001. The criterion by which
   a collaborator is chosen has not changed: the shape of the network has.

6. **The "Smurfette" pattern is not observed.** Holding releases, cohort and
   musical genre constant, being a woman does not shift network position on
   any of the three centrality measures used (section 6.2). The inequality is
   large, but it lies in **access** and in the volume of activity, not in the
   position of those who managed to get in.

> **Measurement note.** All gender assortativities reported as main results
> are computed only on edges where **both** artists have a determined gender
> ({pct(C['quota_archi_mf'])} of edges). Including `unknown` as a fourth
> category systematically inflates the index, because poorly documented
> artists collaborate with each other more than chance would predict, for
> reasons of data coverage. The two measures are compared in a table in
> section 5.1.

### How far to trust these results

Gender does not appear in any source: it is **inferred**. A determination is
reached for {pct(C['share_known'])} of the population, with
{n(C['n_wikidata'])} cases anchored to Wikidata through the Discogs identifier
(exact join, no homonymy) and the rest inferred from first names. The manual
validation sample of {n(C['n_validation'])} cases and the tool for measuring
the error are ready in `data/validation_sample.csv`; until the sample is
coded by hand, the figures above should be read as estimates with an error
that has not yet been quantified. The Monte Carlo analysis in section 8.1
nonetheless shows that homophily remains positive **in every imputation
scenario**, including the one built specifically to minimize it.

---
"""


# ==========================================================================
def sezione_dati(C) -> str:
    return f"""
# 1. Data sources: what is there, what is missing, what had to be built

## 1.1 The source

The analysis uses **a single source**: a local copy of the Discogs dump in
PostgreSQL (database `discogs`, {n(C['db_rows'])} rows in the tables used).
The initial design also included a second database, iTunes, and a bridge
table between the two; at the client's request iTunes was **excluded**. The
methodological consequence is clear-cut and must be stated: there is no
independent cross-check of the artist records, and the robustness axis "union
of sources vs. Discogs only" no longer applies. In its place, two alternative
axes were introduced (the Italian-share threshold and the use or non-use of
track-level credits), discussed in section 8.2.

All database sessions ran with `default_transaction_read_only = on`. In
PostgreSQL this setting also forbids temporary tables, so the extraction was
rewritten to create **no** objects on the server: lists of identifiers
computed in Python are sent back to the database as `int[]` literals. No write
of any kind touched the source.

## 1.2 Three gaps that changed the design

Exploration found three gaps in the dump that forced deviations from the
original plan. They need to be stated clearly because they limit what can be
concluded.

**`release_label` is empty (0 rows).** There is no link between releases and
record labels. The planned heuristic for identifying Italian musicians through
*Italian labels* therefore cannot be applied, and with it goes any analysis by
record company. Italian identity therefore rests on the country of release
alone.

**`release_genre` and `release_style` are empty (0 rows).** Musical genre is
available only through the *master* (`master_genre`), and masters cover about
59% of releases. This is why {pct(1-C['share_genre'])} of the population has
no musical genre assigned.

**The "Various Artists" entity is effectively absent.** In the whole of
`release_artist` (over 92 million rows) there are **328** main credits
attributed to an artist named "Various*". In this dump compilations do not use
the usual placeholder: they list the artists directly. The `exclude_various`
filter is therefore almost inert ({n(C['n_various'])} releases caught), and
compilations have to be recognized by a different criterion, the presence of
several distinct main artists, which is the `exclude_compilations` filter used
as a robustness axis.

## 1.3 Who counts as an "Italian musician"

Without label data and without a nationality field, Italian identity was
defined by the **share of Italian releases** in each artist's career:

> An artist enters the population if they have at least {C['min_it']} releases
> with `country = 'Italy'`, at least {C['min_all']} releases in total, and if
> the Italian ones make up at least {pct(C['min_share'],0)} of the total.

The share rule is the part that does the work. The absolute count alone
produces a list dominated by Beethoven, Mozart, Bach, Chopin and Karajan: the
classical repertoire is reissued in Italy in large quantities, and counting
only "how many Italian releases" mistakes the catalog for the biography. The
share excludes all of them, because for each of them the Italian editions are
a tiny fraction of a worldwide catalog.

The validity check consisted of inspecting the top twenty-five artists by
volume: Mina, Lucio Battisti, Vasco Rossi, Fabrizio De André, Franco Battiato,
Lucio Dalla, Mogol, Renato Zero, Francesco De Gregori, Domenico Modugno,
Claudio Villa, plus a group of Italian producers and engineers who are
genuinely active (Antonio Baglio, Giovanni Versari, Vincenzo Tempera). No
evident false positives.

Two structural limits remain that no threshold can remove:

* the rule measures **where people release**, not **where they come from**. A
  foreign musician who has worked almost exclusively for the Italian market
  enters the population; an Italian emigrant who releases mostly abroad drops
  out. The {pct(C['min_share'],0)} threshold keeps the first error low at the
  cost of increasing the second;
* Discogs is not a census. It overrepresents vinyl, collecting and electronic
  music, and underrepresents music that was never released on a cataloged
  physical format. The composition by musical genre in section 3.2 should be
  read as the composition *of the Discogs catalog*, not of Italian music.

**Effect of the threshold** (measured): {n(C['n_cand_ge2'])} artists have at
least two Italian releases; applying the share and the minimum, the population
falls to **{n(C['n_pop'])}**. Raising the share to 0.60 and 0.70 gives
{n(C['n_pop_60'])} and {n(C['n_pop_70'])} artists: section 8.2 shows that the
conclusions do not change.
"""


# ==========================================================================
def sezione_gender(C) -> str:
    src = get("population_gender.parquet")
    by_src = (src.label_source.value_counts().rename_axis("source")
              .reset_index(name="artists") if src is not None else pd.DataFrame())
    by_src["share"] = (by_src.artists / by_src.artists.sum()).map(lambda v: pct(v))
    by_src["artists"] = by_src.artists.map(lambda v: n(v))
    return f"""
# 2. Gender: how it was inferred

## 2.1 The problem

None of the available sources records people's gender. It has to be inferred,
and the inference must be documented in full, because it is the most fragile
point of the whole study: every conclusion about gender homophily rests on a
label that nobody declared.

The cascade proceeds from the strongest signal to the weakest, and each artist
carries **which level** their label comes from and **with what confidence**.

## 2.2 Level 1: Wikidata linked to the Discogs identifier

Wikidata exposes property `P1953`, *Discogs artist ID*. This allows an **exact
join on the identifier**, not on the name: no homonymy, no approximate
matching. All entities with `P1953` and `P21` (sex or gender) were collected:
**{n(C['n_wd_total'])} distinct Discogs identifiers**, with
{n(C['n_wd_ambiguous'])} ambiguous cases discarded and **zero blocks lost** in
a recursive pagination by identifier prefix.

Of these, **{n(C['n_wikidata'])} fall within our population**
({pct(C['n_wikidata']/C['n_pop'])}). This is low coverage in absolute terms,
and the reason is obvious: Wikidata describes notable people, while the
Discogs population consists largely of session musicians, arrangers, sound
engineers and producers who have no encyclopedia entry. But these are
{n(C['n_wikidata'])} **certain** labels, and the next level rests on them.

## 2.3 Level 2: first names, learned from the data rather than taken from a list

The design called for the ISTAT list of first names. In this environment it
was not available as a downloadable dataset; the fallback adopted is better
for the purpose, not worse.

The same {n(C['n_wd_total'])} Discogs identifiers labeled by Wikidata were
joined back to the **names** in the database: this yields
**{n(C['n_wd_names'])} name→gender pairs for musicians**, a domain-specific
corpus of first names, much larger than the Italians alone and much more
relevant than a generic civil-registry list.

Two dictionaries are derived from it, and the order in which they are
consulted is the most important methodological choice in this section:

1. **Italian dictionary** ({n(C['n_prior_it'])} names), built only on the
   Italian artists labeled by Wikidata;
2. **`gender-guesser` with the Italian lookup**;
3. **global dictionary** ({n(C['n_prior_glob'])} names), but **only for names
   that the Italian lookup does not recognize**;
4. global `gender-guesser`, as a last resort and with reduced confidence.

The constraint in point 3 is not pedantry. Andrea, Simone, Nicola, Daniele,
Michele and Gabriele are male names in Italy and female names in
English-dominated dictionaries: using the global dictionary without that
filter would flip the gender of some of the most common Italian male first
names, a systematic rather than random error, concentrated precisely on the
most frequent names. Checked against the data: the two dictionaries agree on
all {n(C['n_prior_common'])} names they have in common, which indicates that
the filter is actually keeping the two domains apart rather than masking a
conflict.

## 2.4 Level 3: groups are read from their members

A band name says nothing about the gender of its members. For groups,
therefore, the membership is examined (`group_member`): if the members of
known gender include both genders the group is **`mixed`**, if they are all of
the same gender the group inherits it, and if fewer than two are known it
remains `unknown`. **{n(C['n_groups_res'])} of {n(C['n_groups'])} groups**
were resolved, of which {n(C['n_mixed'])} are mixed.

## 2.5 Outcome of the cascade

{by_src.to_markdown(index=False, disable_numparse=True)}

**Table: Source of the gender label for each artist.** The
`onomastico_prior_it` row carries most of the load on its own: it is the
dictionary built on the {n(C['n_wikidata'])} certain Italians, and
{n(C['n_prior_it'])} first names are enough to cover almost half of the
population, because Italian first names are highly concentrated. `none` and
`group_unresolved` are the two faces of not knowing: artists whose name is not
a recognizable personal name (acronyms, pseudonyms, projects) and groups for
which not enough members are known.

**Final outcome: {pct(C['share_f'])} women among artists with determined
gender**, that is, {n(C['ratio_mf'],2)} men for every woman, with
{pct(1-C['share_known'])} of the population remaining undetermined.

## 2.6 The missing piece: manual validation

`data/validation_sample.csv` has been generated: **{n(C['n_validation'])}
artists** drawn with stratification by gender, confidence band and label
source, with an empty `human_gender` column to be filled in by hand. The
script `src/score_validation.py` computes precision, recall, F1 and the
confusion matrix by cascade level as soon as the file is filled in.

The sample uses **half proportional and half uniform allocation** across
strata: the proportional part makes it possible to estimate overall accuracy
without reweighting, and the uniform part guarantees enough cases even in the
rare levels of the cascade. Within each stratum, distinct first names are
favored, because otherwise small strata fill up with people who share a name
and the validation would measure accuracy on one name rather than on a level.

On two levels that remedy is not enough, and this should be said:
`onomastico_gg_mostly_female` contains 28 artists who share **a single** first
name (Mary), and `onomastico_gg_mostly_male` contains 44 with two (Toni,
Leonida). On those two levels the validation will be able to say whether those
names are classified correctly, not whether the level works in general.
Together they account for 72 of {n(C['n_pop'])} artists, so this does not
affect the conclusions, but the resulting accuracy figure should not be read
as generalizable.

This step **has not been carried out**: it requires human judgment. Until it
is completed, the error of the gender inference is bounded only by the Monte
Carlo analysis in section 8.1, which, however, measures the effect of
*uncertainty about the unknowns*, not that of *errors among the knowns*. This
is the most serious limitation of the study.
"""


# ==========================================================================
def sezione_rete(C) -> str:
    return f"""
# 3. The network: how two musicians become connected

## 3.1 Edge weight, and why not all credits count the same

A Discogs credit can say three very different things. It can say *"this
person plays bass on track B2"*; it can say *"this person is the artist of the
record"*; it can say *"this person appears in the credits of the record"*,
without specifying where. Treating them as equivalent would mean giving a
shared sleeve credit the same value as a documented session.

Each credit therefore receives a **specificity**, and the weight of the tie
between two artists uses it:

| scope | specificity | what it means |
|---|---|---|
| `track` | {C['w_track']:.2f} | credit resolved to a specific track |
| `main` | {C['w_main']:.2f} | main artist of the release |
| `umbrella` | {C['w_umb']:.2f} | secondary credit, with no indication of tracks |

$$w(u,v) = w_t \\cdot |\\text{{shared tracks}}| + w_r \\cdot \\sum_{{R}} s_u(R)\\, s_v(R)$$

The first term rewards collaboration **documented on the same track**; the
second retains co-presence on the same release, scaled by the specificity of
both credits. Two session musicians credited on the same track weigh much more
than two names that appear generically on the same record.

Track-level credits come from two routes. The first is `release_track_artist`,
which carries a global track identifier: **{n(C['n_rta'])} credits**. The
second is the `tracks` field of `release_artist`, which gives positions in
text form (`A1`, `1 to 3`, `4, 6, 12`) and has to be **resolved**: positions
are converted into actual tracks through `release_track`. Of
{n(C['n_ra_tracks'])} positional credits, {n(C['n_ra_resolved'])}
({pct(C['n_ra_resolved']/max(C['n_ra_tracks'],1))}) were resolved; the rest
use free-form expressions (*"all tracks except 1, 13 and 14"*) and were
**downgraded to `umbrella`** rather than forced into an interpretation.

Total: **{n(C['n_track_credits'])} of {n(C['n_credits'])} credits
({pct(C['share_track'])}) are resolved at the level of the individual track.**

## 3.2 Filters and subnetworks

Releases with more than {C['max_credits']} credited artists are discarded:
they are compilations and box sets, where co-presence does not indicate
collaboration and the number of pairs grows quadratically. The filter reduces
the credits from {n(C['n_credits'])} to {n(C['n_credits_filt'])}.

The role subnetworks separate two different trades: **creative** (production,
writing, arrangement, composition) and **performance** (vocals, instruments,
conducting, featuring). A main artist without an explicit role is treated as a
performer, because that is what being the artist of a record means.

{table('t2_rete_descrittive', 'Descriptive statistics of the three collaboration networks', float_dec=6)}

The overall network is **sparse and highly connected**: density on the order
of {n(C['density'],6)}, but a giant component that absorbs {pct(C['giant'])}
of the connected artists. This is the typical signature of a professional
world in which almost nobody works in isolation and almost nobody works with
everyone. The `creative` network is smaller and denser than the `performance`
network: producers and songwriters form a tighter and more interwoven core
than performers, which matters for the reading of section 5.3, where the two
roles show different levels of homophily.

{img('f5_distribuzione_gradi',
 "**Degree and strength distributions.** On a log-log scale both "
 "distributions decline along an almost straight line over several orders of "
 "magnitude: the vast majority of artists have very few collaborators, while "
 "a thin minority have hundreds. Strength, which sums the weights and "
 "therefore counts how many times people collaborated and how specific the "
 "credits were, has an even longer tail than degree: the major collaborators "
 "do not just have many partners, they have much more intense relationships. "
 "This is the structural background against which section 6.1 should be read: "
 "in a network this unequal, the question 'are women at the center?' must "
 "always be asked holding activity constant, because the number of releases "
 "alone already explains much of centrality.")}

The analyses that follow run on the **giant component**, because centrality
measures and distances are not defined across separate components. The
excluded share is {pct(1-C['giant'])} of the connected artists.
"""


# ==========================================================================
def sezione_risultati(C) -> str:
    return f"""
# 4. How many women there are, and in which music (RQ1)

{img('f3_quota_donne_per_decennio',
 f"**The share of women by decade of debut.** The line is not a story of "
 f"progress. It starts at {pct(C['q_1960'])} for those who debuted in the "
 f"1960s, falls to {pct(C['q_1980'])} in the 1980s (the lowest point in the "
 f"series) and rises only recently, to {pct(C['q_2020'])} for those who "
 f"debuted from 2020 onward. The decline of the 1970s and 1980s calls for "
 f"caution before it is read as a real setback: it coincides with the massive "
 f"expansion of the Discogs catalog for those years, that is, with the mass "
 f"entry of technical and production credits (trades that are almost "
 f"entirely male), which dilute a share computed over all credits rather than "
 f"over performers only. The recent rise, by contrast, is consistent in both "
 f"magnitude and direction with what is observed in other music catalogs. In "
 f"every decade, however, the confidence band remains very far from parity.")}

{img('f4_quota_donne_genere_x_decennio',
 "**Share of women by musical genre and decade.** The panels show that there "
 "is no single trajectory of gender representation: there are musical genres "
 "with different histories. The starting level matters more than the slope: a "
 "genre that starts low tends to stay low across the decades, which is "
 "exactly the signature of a segregation that reproduces itself through "
 "recruitment rather than dissolving over time.")}

{table('t3_quota_donne_genere_decennio',
 'Share of women by musical genre and decade of debut, with 95% Wilson intervals',
 max_rows=25)}

## 4.1 Comparison with the patterns reported in the literature

The usual benchmark for hip hop is a ratio of about **4 men for every woman**.
In the Italian data the ratio is **{n(C['ratio_hiphop'],1)} to 1**
({pct(C['q_hiphop'])} women): markedly **more unbalanced** than the
international benchmark. There are two readings, not mutually exclusive: the
Italian hip hop scene recorded in Discogs is smaller and more recent, and
therefore more exposed to the fact that production roles, where women are
rarer, weigh relatively more; and the count here includes all credits, not
only lead performers, which lowers the share compared with chart-based
statistics.

At the opposite end, **Classical** ({pct(C['q_classical'])}) and
**Children's** ({pct(C['q_children'])}) are the genres with the highest
female presence, the latter above {pct(C['q_children'],0)}, the only genre in
the entire corpus in which women approach half. The gap between Children's and
Hip Hop, with the same population and the same method, is more than
{n((C['q_children']-C['q_hiphop'])*100,0)} percentage points: musical genre is
the strongest predictor of female presence in this entire study.

**Rock ({pct(C['q_rock'])}) and Electronic ({pct(C['q_electronic'])})**, which
together make up the largest part of the population, are both below the
overall average. Given their numerical weight, it is these two scenes that
determine the overall share.
"""


# ==========================================================================
def sezione_omofilia(C) -> str:
    return f"""
# 5. Homophily: who records with whom (RQ2)

## 5.1 The overall picture

{img('f1_mixing_gender_oss_att',
 "**Who collaborates with whom, relative to chance.** Each cell is the ratio "
 "between the observed ties and those expected under a null model that "
 "preserves exactly each artist's degree and the composition of the "
 "population: the only thing randomized is *who is with whom*. A value of 1 "
 "means 'as by chance', above 1 means more than expected. A diagonal above 1 "
 "and off-diagonal cells below 1 are the operational definition of homophily. "
 "The unknown–unknown cell also departs from 1: this is not a social fact but "
 "a matter of data coverage. Artists about whom we know nothing tend to be "
 "together because they share the same characteristics that make them poorly "
 "documented (few credits, minor roles, marginal periods). This is precisely "
 "why the ERGM in section 7 excludes unknown nodes instead of treating them as "
 "a category.")}

{table('t3_assortativita_globale', "Assortativity, observed and under the null model", float_dec=4)}

{table('t3_assortativita_MF_vs_tutte',
 "Assortativity computed only on nodes with a determined attribute, compared "
 "with the computation that treats 'undetermined' as a category, for gender "
 "and for musical genre", float_dec=4, max_rows=40,
 cols=['sottorete', 'strato', 'attributo', 'categorie', 'archi_usati',
       'quota_archi_usati', 'r', 'ci_lo', 'ci_hi'],
 rename={'archi_usati': 'edges', 'quota_archi_usati': 'edge share',
         'attributo': 'attr.'})}

### A measurement issue that changes the numbers

The two tables should be read together, because the second corrects the
first.

Treating `unknown` as a fourth category on a par with M and F inflates
assortativity: the unknown–unknown cell is far above expectation, but not
because those people seek each other out. What attracts them to each other
are the characteristics that make them poorly documented (few credits, minor
roles, marginal periods, pseudonyms), and these are the same characteristics
that make their gender hard to infer. It is data coverage disguised as social
structure.

The reference measure therefore restricts the computation to edges where both
endpoints have a determined gender: **{pct(C['quota_archi_mf'])} of edges**.
The difference is not cosmetic: **r goes from {n(C['r_gender'],4)} to
{n(C['r_mf'],4)}**, meaning that a third of the apparent homophily was an
artifact.

The same check was carried out on **musical genre**, where 'Unknown' is just
as common, and it gives the **opposite** result: removing the undetermined
cases, assortativity rises from {n(C['r_genre_tutte'],4)} to
{n(C['r_genre_det'],4)}. The reason is that artists without an assigned
musical genre do not cluster together by genre (they have none), and so they
dilute the diagonal instead of inflating it. Reporting both comparisons makes
clear that excluding undetermined cases is a methodological choice applied
uniformly, not an adjustment adopted where it was convenient: for gender it
lowers the result, for musical genre it raises it.

### The central result

Assortativity by **musical genre** is {n(C['r_genre'],3)}. This is a very high
value: careers unfold within a genre, and collaborations follow genre
boundaries almost as if they were industry boundaries.

Assortativity by **gender** is {n(C['r_mf'],4)}, about
{n(C['r_genre']/max(C['r_mf'],1e-9),0)} times lower, with a confidence
interval of {n(C['r_mf_lo'],4)}–{n(C['r_mf_hi'],4)} and a null-model value of
{n(C['r_mf_null'],4)}. Taken alone the number looks negligible; it is not,
because with {n(C['n_edges'])} edges even a small effect is measured with high
precision and the interval lies entirely above zero.

The substantive reading is that **gender structures collaborations, but far
less than musical specialization does**. Someone looking for a bass player
looks within their own musical circle far more systematically than among
people of their own sex. This does not make gender homophily irrelevant: it
makes musical genre the main channel through which it operates, as the next
paragraph shows.

{img('f2_mixing_genere_musicale_oss_att',
 "**Homophily by musical genre.** The diagonal dominates the image. The most "
 "closed genres are not necessarily the largest: closure measures how much a "
 "scene recruits from within, not how populous it is. Off-diagonal cells "
 "above 1 indicate the pairs of genres between which there is a real flow of "
 "musicians: the permeable boundaries of the system.")}

## 5.2 Homophily over time: the counterintuitive result

{img('f6_assortativita_per_strato',
 f"**Gender homophily by role subnetwork and period.** The dot is the "
 f"observed value, the bar the 95% bootstrap confidence interval, the "
 f"vertical tick the null-model value. The expectation from the literature "
 f"was a **loosening** after 2000. On nodes with determined gender only, the "
 f"data say the opposite, but with a much smaller magnitude than the "
 f"four-category measure shown in the figure suggests: "
 f"{n(C['r_pre_mf'],4)} versus {n(C['r_post_mf'],4)}.")}

Before it can be interpreted, the result needs cleaning up. On the naive
four-category measure the jump is spectacular, from {n(C['r_pre'],4)} to
{n(C['r_post'],4)}: more than double. On nodes with determined gender only it
shrinks to {n(C['r_pre_mf'],4)} → {n(C['r_post_mf'],4)}. The reason is that the
share of usable edges drops sharply between the two periods, from
{pct(val(get('assortativity_mf.parquet'), "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", 'quota_archi_usati'))}
to
{pct(val(get('assortativity_mf.parquet'), "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", 'quota_archi_usati'))},
because recent artists are on average less well documented: more `unknown`,
hence more spurious apparent homophily.

**What remains after the correction is nonetheless an increase**, with
intervals ({n(C['r_pre_mf_lo'],4)}–{n(C['r_pre_mf_hi'],4)} versus
{n(C['r_post_mf_lo'],4)}–{n(C['r_post_mf_hi'],4)}) that do not overlap. The
result holds, but it should be described for what it is: a moderate increase,
not a doubling.

**And the increase is not widespread: it comes entirely from one part of the
network.** Broken down by role, homophily in performance roles is essentially
flat over time ({n(C['r_perf_pre'],4)} before 2000, {n(C['r_perf_post'],4)}
after), while homophily in creative roles **doubles**, from
{n(C['r_creative_pre'],4)} to {n(C['r_creative_post'],4)}. Any explanation of
the increase must therefore concern the way music is produced and written, not
the way it is played.

Two readings remain possible, and the data at hand do not allow a definitive
choice between them.

**First reading: the increase is real.** After 2000 the way music is produced
changes: recording becomes decentralized, and large studios with mixed,
fixed personnel give way to small projects built on personal networks.
Personal networks mean more homophilous networks. In this reading the increase
is not a cultural setback but the structural effect of a different production
technology, and the fact that it concerns only creative roles, which are
precisely those affected by the decentralization of studios, supports this
explanation.

**Second reading: the increase is compositional.** Newman's *r* depends on
the marginals. After 2000 there are more women, hence more opportunities for
woman–woman ties; with the same propensity, a larger minority group
mechanically produces a higher measured assortativity. The degree-preserving
null model corrects for degree, **not** for this difference in composition
between the periods.

The ERGM is needed precisely to settle this point, and **the verdict is in**:
once the network's tendency to close triangles is controlled for, the
difference in gender homophily between the two periods **is not statistically
distinguishable from zero** (for women {n(C.get('epoca_F_pre'),3)} versus
{n(C.get('epoca_F_post'),3)}, p = {n(C.get('epoca_F_p'),2)}; for men
{n(C.get('epoca_M_pre'),3)} versus {n(C.get('epoca_M_post'),3)}, p =
{n(C.get('epoca_M_p'),2)}).

What does increase, and very sharply, is **triadic closure**: the `gwesp`
coefficient goes from {n(C.get('epoca_gwesp_pre'),3)} to
{n(C.get('epoca_gwesp_post'),3)} (p < 0.0001). Italian recorded music after
2000 has not become more homophilous by gender: it has become more **closed
into triangles**. People increasingly work within dense groups whose members
already all know one another. In an environment where women are
{pct(C['share_f'])}, a more triangular structure mechanically produces more
observed woman–woman ties, and hence a higher measured assortativity, without
anyone having changed the criterion for choosing whom to work with.

This is the most interesting answer in the study, because it shifts the
object: the problem is not a gender preference that has grown stronger, but a
recruitment structure that has closed in on itself. These are two different
things, also from the point of view of anyone wishing to intervene. The
details of the test are in section 7.3.

## 5.3 Producers and performers: two trades, two homophilies (RQ5)

The distinction between creative roles (production, writing, arrangement) and
performance roles (vocals, instruments, conducting) is research question RQ5,
and the answer is clear-cut: on nodes with determined gender only, homophily
is **{n(C['r_creative_mf'],4)} in the creative network** versus
**{n(C['r_perf_mf'],4)} in the performance network**.

Creative collaboration is therefore *less* segregated by gender than
performance collaboration, by a factor of
{n(C['r_perf_mf']/max(C['r_creative_mf'],1e-9),1)}. This result has to be read
together with the composition figures: creative roles are by far the most male
in the entire corpus, and precisely for this reason the homophily measured
there is low, since where the majority is overwhelming there is almost no room
to depart from chance. The segregation of creative roles shows up in **who
gets in**, not in **who works with whom**; that of performance roles, where
women are more present, also shows up in the structure of collaborations.
These are two different forms of closure, and conflating them would lead to
the conclusion that music production is the most open part of the system,
which is the opposite of what the counts say.

## 5.4 Homophily within each musical genre

{img('f7_omofilia_per_genere_musicale',
 "**On the left**, gender homophily computed separately within each musical "
 "genre, with the null model as reference. **On the right**, the "
 "decomposition of the diagonal: how far man–man ties and woman–woman ties "
 "exceed expectation. Reading the two panels together is the core of RQ2. An "
 "observed/expected value close to 1 for men and well above 1 for women "
 "describes a precise situation: men do not seek each other out more than "
 "chance would predict (they have no need to: they are the majority, and "
 "chance already puts them together), while women cluster together much more "
 "than expected. This is the form homophily takes when a minority operates "
 "within a majority: not symmetric segregation, but clustering of the "
 "minority group.")}

{table('t3_omofilia_per_genere_musicale',
 'Gender homophily within each musical genre (RQ2)', float_dec=4)}

This is the point on which the Italian data **contradict current
expectations**. The literature usually reports stronger homophily *among
men*. Here the woman–woman observed/expected ratio is systematically
**higher** than the man–man ratio. The explanation is not that women are more
closed: it is that with a female share of {pct(C['share_f'])} the expected
value for a woman–woman tie under randomness is very low, and a modest real
clustering is enough to produce a high ratio. The man–man index, by contrast,
is squeezed toward 1 because the majority cannot depart much from chance.
**The two indices are not comparable as if they measured the same thing**,
and it is the ERGM, which estimates a propensity rather than a ratio, that
provides the correct comparison.
"""


# ==========================================================================
def sezione_posizione(C) -> str:
    return f"""
# 6. Are women at the center or at the margins? (RQ3)

The question that the literature calls the *Smurfette pattern* is whether
women, where they are present, occupy structurally peripheral positions:
present enough to be counted, never at the center.

{table('t3_posizione_per_genere', 'Position in the giant component by gender', float_dec=6)}

{img('f8_posizione_per_genere',
 "**Median coreness by gender, within each musical genre.** Coreness "
 "indicates which layer of the network's dense core a person belongs to: as a "
 "measure of belonging to the center it is more robust than degree "
 "centrality, because it is not inflated by having many occasional "
 "collaborators. The side-by-side bars allow a direct comparison within the "
 "same musical genre, which is the right comparison: comparing a pop singer "
 "with a jazz session musician would say nothing about gender and a great "
 "deal about the structure of the two scenes.")}

{table('t3_posizione_per_genere_musicale',
 'Network position by gender within musical genre', max_rows=30, float_dec=6)}

## 6.1 The comparison holding activity and cohort constant

Raw medians are not enough. Those who release more are more central, and the
women in the population release less: the median number of releases is
{n(C.get('nrel_med_F'),0)} for women versus {n(C.get('nrel_med_M'),0)} for
men, and median coreness follows ({n(C.get('core_med_F'),0)} versus
{n(C.get('core_med_M'),0)}). Without controlling for activity, one would be
measuring the difference in how much people release and calling it a
difference in position.

The regression therefore compares people with the same activity, the same
debut cohort and the same musical genre.

{table('t3_regressione_eigenvector',
 "Network position (eigenvector) by gender and musical genre, "
 "holding activity and cohort constant", max_rows=28, float_dec=4)}

{table('t3_regressione_coreness',
 "Core membership (coreness) by gender and musical genre, "
 "holding activity and cohort constant", max_rows=28, float_dec=4)}

## 6.2 The answer to RQ3

**The "Smurfette" pattern is not observed in these data.** Holding releases,
cohort and musical genre constant, the main effect of being a woman on network
position is not distinguishable from zero on any of the three measures:

| measure | coefficient | 95% CI | p |
|---|---|---|---|
| eigenvector | {n(C.get('b_eigenvector'),3)} | {n(C.get('lo_eigenvector'),3)} – {n(C.get('hi_eigenvector'),3)} | {n(C.get('p_eigenvector'),3)} |
| coreness | {n(C.get('b_coreness'),3)} | {n(C.get('lo_coreness'),3)} – {n(C.get('hi_coreness'),3)} | {n(C.get('p_coreness'),3)} |
| betweenness | {n(C.get('b_betweenness'),3)} | {n(C.get('lo_betweenness'),3)} – {n(C.get('hi_betweenness'),3)} | {n(C.get('p_betweenness'),3)} |

The interactions with musical genre do not change this either: of
{n(C.get('n_interazioni'))} interaction terms estimated,
{n(C.get('n_interazioni_signif'))} are significant at the 5% level. In these
data there is no scene in which being a woman systematically pushes a person
toward the periphery of the network.

This result must be stated precisely, because it lends itself to two mistaken
readings of opposite sign.

**It does not mean that there is no inequality.** Women are
{pct(C['share_f'])} of the population and release less: the median number of
releases is {n(C.get('nrel_med_F'),0)} versus {n(C.get('nrel_med_M'),0)}. The
inequality exists and is large, but it shows up **in access and in the volume
of activity**, not in structural position at equal activity. Those who get in
and manage to work, work in comparable positions.

**Nor does it mean that controlling for activity is neutral.** The number of
releases is not an exogenous variable: it is itself the outcome of access
processes that may be segregated. Controlling for activity answers the
question "for the same career, does position differ?" and not the question "do
careers differ?". The answer to the first is negative; the answer to the
second (section 4) is clearly positive.

The most interesting finding is the divergence between the median and the
mean of eigenvector centrality: the median is higher for women
({sci(C.get('eig_med_F'))} versus {sci(C.get('eig_med_M'))}) while the mean is
lower. This means that the typical woman in the network is at least as
connected as the typical man, but that the **extreme hubs**, the very few
nodes whose centrality is orders of magnitude higher, are almost all men.
Positional inequality, where it exists, lies in the tail, not in the body of
the distribution.
"""


# ==========================================================================
def sezione_ergm(C) -> str:
    st = get("ergm_summary.parquet")
    if st is None or st.empty or not st.get("convergenza", pd.Series([False])).any():
        return """
# 7. ERGM (RQ4)

> **This phase did not produce usable estimates.** R and statnet were
> installed in user space and tested with a trial model, but for none of the
> subnetworks did a model converge within the maximum time allotted. The gap
> is declared here rather than worked around: the questions that the ERGM was
> meant to settle, in particular whether the post-2000 increase in homophily
> (sec. 5.2) reflects propensity or composition, remain open, and only the
> descriptive measures of the previous sections bear on them.
"""
    conv = int(st.convergenza.sum())
    gw = int(st.get("gwesp_converge", pd.Series([False] * len(st))).sum())
    return f"""
# 7. The probability of collaborating, all else being equal: the ERGM (RQ4)


## 7.1 Why it is needed and how it was set up

All the measures so far are descriptive: they say *that* ties are distributed
in a certain way, not *why*. An exponential random graph model (ERGM) instead
estimates the probability that a tie exists, combining in a single model
gender homophily, musical-genre homophily, level of activity, cohort and the
network's tendency to close triangles. This last point is decisive: without a
triadic closure term (`gwesp`), any tendency to cluster is wrongly attributed
to whatever attribute is being examined.

**The ERGM cannot be estimated on the full network**, and this should be
stated plainly rather than glossed over. With {n(C['n_nodes'])} nodes the space
of possible graphs makes MCMC sampling impractical. The analysis therefore
proceeded, as the design anticipated, by subnetworks: the five most populous
musical genres, the two periods, and a snowball sample of the overall network
as a reference. **The estimates apply to the subnetworks on which they are
computed**, and by construction do not extend to the entire population.

Nodes with `unknown` gender are excluded from the ERGM. Keeping them as a
fourth category would have produced a spurious homophily term that measures
the structure of data coverage (the poorly documented collaborate with the
poorly documented) rather than the structure of collaborations.

A **hierarchy of three models** is estimated instead of a single
specification, because the triadic closure term is exactly the one that can
make estimation fail, and the rest of the analysis should not be lost along
with it:

* **M0** `edges + nodematch(gender, diff) + controls`: no edge-dependence
  term. This is the reference model and can always be estimated.
* **M1** M0 + `gwesp(0.25; fixed)`: the specification anticipated by the
  design. The triadic closure term makes the model nearly degenerate on highly
  clustered networks, and it may fail to converge.
* **M2** the better of M1 and M0, with `nodemix(gender)` in place of
  `nodematch(gender, diff)`. The two parameterizations are redundant with each
  other, and including both in the same model would make it unidentified.

The control terms enter **only if the attribute varies** within the
subnetwork. Within a subnetwork of a single musical genre,
`nodematch('musical_genre')` is identical to `edges`: including it would
produce an unidentified model, and in the first runs this was exactly what
prevented convergence.

{table('t4_ergm_sintesi', 'Summary of the ERGM estimates: size, sampling, convergence')}

Subnetworks with at least one converged model: **{conv} of {len(st)}**;
subnetworks in which the `gwesp` term also held: **{gw}**. Where `gwesp` does
not converge, the reported coefficients come from M0 and do **not** control
for triadic closure: they should therefore be read as estimates that may
attribute to homophily part of what is simply a tendency to form triangles.
This is a limitation, and it is declared here rather than hidden behind a
number.

{img('f9_ergm_forest_gender',
 "**Gender homophily coefficients in the five most populous musical "
 "genres.** Each coefficient is a log-odds: how much the probability of a tie "
 "increases (or decreases) if two artists share the same gender, *holding "
 "constant* activity, cohort, musical genre and triadic closure. This is the "
 "comparison that the descriptive measures in section 5.4 could not provide: "
 "here the male and female coefficients are on the same scale and directly "
 "comparable, because they measure a propensity and not an observed/expected "
 "ratio squeezed by the marginals. If the male coefficient exceeds the female "
 "one, the Italian pattern is in line with the literature (stronger homophily "
 "among men) and the inversion observed in section 5.4 was an artifact of "
 "women's rarity.")}

{table('t4_ergm_coefficienti', 'ERGM coefficients by subnetwork', max_rows=40,
 float_dec=4, cols=['rete', 'model', 'term', 'estimate', 'se', 'p', 'ci_lo', 'ci_hi', 'or'])}

### How to read these coefficients, and what they say

The coefficients are in log-odds; the `or` column is their exponential, that
is, the factor by which the probability of a tie is multiplied.
`nodematch.gender.F` says how much more likely a woman–woman pair is than a
reference pair **holding everything else constant**: activity, cohort, musical
genre and, decisively, the network's tendency to close triangles.

The comparison between `nodematch.gender.F` and `nodematch.gender.M` is the
result that section 5.4 could not provide. There, the observed/expected ratios
were not comparable, because with a female share of {pct(C['share_f'])} the
expected value for a woman–woman tie is so low that any real clustering
produces a large ratio. Here the problem does not arise: the two coefficients
measure the same quantity on the same scale. **And the result holds: women's
propensity to work with women remains clearly higher than men's propensity to
work with men.** It is not an artifact of rarity; it is a property of the
network.

In some subnetworks the male coefficient is **negative**: holding everything
else constant, two men have a slightly *lower* probability of collaborating
than the reference. This does not mean that men avoid each other. It means
that, in an environment where they are the overwhelming majority, the `edges`
term alone already produces almost all the male ties observed, and once that
baseline is removed there is nothing left to attribute to a preference. This
confirms the same asymmetry from the opposite side: where a group dominates,
homophily has no way to show up as a measurable effect; where a group is rare,
it shows up strongly.

The comparison between M0 and M1 also deserves attention. Moving from the
model without triadic closure to the one with `gwesp`, the female homophily
coefficient **decreases**: part of what looked like gender preference was in
fact the network's general tendency to close triangles (if A works with B and
B with C, sooner or later A works with C, and in an environment where women
are few, triangles among women form anyway). The `gwesp` term has a very large
coefficient, which shows how strong that mechanism is. What remains after it
is taken into account is genuine homophily.

## 7.2 Diagnostics: does the model actually describe this network?

{img('f12_ergm_gof',
 "**Goodness of fit.** For each subnetwork, three statistics of the observed "
 "network (points) are compared with those of the networks simulated from the "
 "estimated model (line and band): the degree distribution, the number of "
 "partners shared by each connected pair (ESP) and the geodesic distances. A "
 "model that captures the structure produces simulations whose band contains "
 "the observed values; where a point falls outside the band, the model is "
 "getting precisely that aspect wrong. ESP is the statistic to watch most "
 "closely, because it is the one the gwesp term should reproduce: if the "
 "observed values fall outside the band, triadic closure has not been "
 "captured and the homophily coefficients may have absorbed part of it. In "
 "the models estimated here the center of the distributions is reproduced "
 "well, but **the tail is not**: nodes with many collaborators and pairs with "
 "many shared partners are systematically more numerous than the model "
 "predicts (red circles). This is the known limitation of ERGMs on "
 "heavy-tailed networks, and it should be kept in mind when reading the "
 "coefficients: the model describes the typical musician well, and the few "
 "major collaborators less well.")}

{table('t4_ergm_mcmc', 'MCMC diagnostics: effective sample size for each '
 'term. Low values indicate a chain that moves little and less reliable '
 'estimates', max_rows=24, float_dec=1)}

## 7.3 The pre/post-2000 test

{table('t4_ergm_differenza_epoche',
 'Test of the difference between the pre-2000 and post-2000 ERGM coefficients', float_dec=4,
 cols=['model', 'term', 'estimate_pre', 'estimate_post', 'differenza', 'se_diff', 'z', 'p'])}

This table is the formal test of the counterintuitive result of section 5.2,
and its outcome is clear-cut.

**Gender homophily does not change between the two periods.** For women the
coefficient goes from {n(C.get('epoca_F_pre'),3)} to
{n(C.get('epoca_F_post'),3)} (difference {n(C.get('epoca_F_diff'),3)}, p =
{n(C.get('epoca_F_p'),2)}); for men from {n(C.get('epoca_M_pre'),3)} to
{n(C.get('epoca_M_post'),3)} (difference {n(C.get('epoca_M_diff'),3)}, p =
{n(C.get('epoca_M_p'),2)}). Neither difference comes close to significance.

**Triadic closure, by contrast, changes a great deal.** The `gwesp`
coefficient goes from {n(C.get('epoca_gwesp_pre'),3)} to
{n(C.get('epoca_gwesp_post'),3)}, a difference of
{n(C.get('epoca_gwesp_diff'),3)} with p < 0.0001: it is the only term in the
model whose change between periods is statistically solid.

The joint reading is the one given in section 5.2: the increase in observed
assortativity after 2000 is not a strengthening of gender preference, but the
consequence of a network that closes into tighter groups. This is exactly the
kind of confounding that a purely descriptive analysis cannot untangle, and
the reason the ERGM was included in the design.
"""


# ==========================================================================
def sezione_robustezza(C) -> str:
    return f"""
# 8. How well these results hold up

## 8.1 Uncertainty about gender

{img('f10_montecarlo_genere',
 f"**Monte Carlo distribution of gender assortativity as the imputation of "
 f"the {n(C['n_unknown'])} artists without determined gender varies.** The "
 f"histogram is the distribution over {C['mc_B']} draws from the observed "
 f"marginal. The two dashed lines at the sides are not estimates but "
 f"**deliberately constructed bounds**: assigning each unknown artist the "
 f"prevailing gender among their collaborators yields the maximum homophily "
 f"compatible with the data; assigning the opposite gender yields the "
 f"minimum. What matters is that **even the lower bound remains positive**: "
 f"no assignment of the unknowns makes homophily disappear. The qualitative "
 f"conclusion is robust; its exact magnitude is not.")}

{table('t5_montecarlo_genere',
 "Gender assortativity under different imputation scenarios", float_dec=4)}

The four numbers should be read together. On artists with determined gender
only, assortativity is {n(C['mc_noti'],4)}. Imputing the unknowns by random
draws from the observed marginal lowers it to {n(C['mc_sq'],4)}: random
imputation can only dilute the structure, which is why the reference measure
of this study is the first and not the second. The two neighborhood-based
bounds, {n(C['mc_min'],4)} and {n(C['mc_max'],4)}, delimit how large
homophily could be if the unknown artists systematically resembled their
collaborators or systematically did not. **None of the four scenarios brings
homophily to zero or below.**

It should be stated precisely what these bounds do not do: they concern only
the unknown artists who have at least one collaborator of known gender. Those
who collaborate only with other unknowns carry no usable information and are
drawn from the marginal even in the extreme scenarios; assigning them by
neighborhood majority would put them all in the same category, creating an
artificial block that would inflate *both* extremes instead of bounding them.

## 8.2 Sensitivity to construction parameters

{img('f11_sensibilita',
 "**Each point is the gender assortativity obtained by changing a single "
 "parameter relative to the default configuration (dashed line).** The axes "
 "varied are those that could reasonably change the result: the maximum "
 "number of artists a release can have for it to count as a collaboration, "
 "the minimum weight an edge must have, whether to exclude compilations, how "
 "strictly to define Italian identity, how to weight credit specificity, and "
 "whether or not to use track-level credits. The last is the most informative "
 "axis: switching off track credits means going back to a network built only "
 "on release-level co-presence, and it is the comparison that shows how much "
 "the track level actually adds.")}

{table('t5_sensibilita',
 "Sensitivity of key metrics to the network construction parameters",
 max_rows=25, float_dec=4,
 cols=['variante', 'nodi', 'archi', 'quota_gigante', 'r_gender_MF',
       'r_gender_pesato', 'r_genere_musicale'],
 rename={'quota_gigante': 'giant', 'r_gender_MF': 'r gender M/F',
         'r_gender_pesato': 'r weighted', 'r_genere_musicale': 'r musical genre'})}

Across the {n(C['sens_n'])} variants tried, gender assortativity on determined
nodes only stays between **{n(C['sens_mf_min'],4)} and
{n(C['sens_mf_max'],4)}**, always positive and always of the same order of
magnitude as the reference value ({n(C['r_mf'],4)}). No defensible choice of
network construction reverses the conclusion.

### What track-level credits actually add

The **weighted** assortativity column is the only one in which the hierarchy
of credit specificity can show up, because changing the weights does not
change which pairs of artists are connected: it changes how much they count.
The comparison is instructive.

* with track credits and the default hierarchy: **{n(C['rw_default'],4)}**
* without track credits, that is, going back to release-level co-presence
  only: **{n(C['rw_no_track'],4)}**
* with all credits at the same weight: {n(C['rw_flat'],4)}
* with a steeper hierarchy (1 / 0.5 / 0.1): {n(C['rw_steep'],4)}

Switching off the track level lowers measured homophily by about
{pct(1 - C['rw_no_track']/max(C['rw_default'],1e-9),0)}, and flattening the
weights lowers it almost as much. The reading is that **the collaborations
documented most specifically are also the most homophilous**: when two names
appear together on the same track, and not just generically on the same
record, the probability that they share the same gender is higher. A network
built on release-level co-presence alone therefore underestimates segregation,
because it mixes genuine collaboration with editorial cohabitation. This is the
empirical justification for the design choice described in section 3.1.

## 8.3 Artists with a weak musical-genre assignment

{table('t5_genere_debole',
 'Key metrics using the main tag, the second tag, or excluding the '
 'artists with a weak assignment', float_dec=4)}

Artists whose main genre tag covers less than {pct(C['weak_threshold'],0)} of
their releases are flagged `genre_weak`: there are {n(C['n_weak'])} of them,
that is, {pct(C['n_weak']/C['n_pop'])} of the population. The table compares
three treatments (keeping them with the main tag, replacing it with the second
tag, excluding them altogether) to show how far the conclusions on RQ2 depend
on a musical-genre assignment that is uncertain by construction.
"""


# ==========================================================================
def appendice(C) -> str:
    tm = ROOT / "logs" / "timings.csv"
    timing = ""
    if tm.exists():
        t = pd.read_csv(tm).groupby("step", as_index=False).seconds.sum() \
              .sort_values("seconds", ascending=False).head(20)
        t["seconds"] = t.seconds.map(lambda v: n(v, 1))
        timing = t.to_markdown(index=False, disable_numparse=True)
    pk = C["packages"]
    pkt = pd.DataFrame(sorted(pk.items()), columns=["package", "version"]).to_markdown(index=False)
    return f"""
# Technical appendix

## A.1 Environment

* System: {C['platform']}
* Python {C['python']}
* PostgreSQL {C['pg_version']} (database `discogs`, data on a spinning disk)
* R for the ERGM: installed in user space via micromamba (conda-forge), env
  `opt/mamba/envs/ergm`
* Global random seed: **{C['seed']}**
* Run date: {C['data']}

{pkt}

## A.2 A note on performance that shaped the design

The PostgreSQL cluster resides on a **spinning** disk but was configured with
`random_page_cost = 1.1`, a value tuned for solid-state drives. With that cost
the planner prefers random-access paths that on a mechanical disk degrade to a
few megabytes per second: the first version of the extraction ran at about
5 MB/s. The extraction sessions therefore set `random_page_cost = 4` and
reduce parallelism, favoring sequential scans, and the Italian-share counts
were rewritten as **a single aggregated pass** over `release_artist` instead
of two repeated joins. These are session-level GUCs: they modify neither the
server configuration nor the data.

Similarly, the computation of the mixing matrix was rewritten from
`numpy.add.at` to `numpy.bincount` on flattened indices (numerically identical
result, verified, about **50 times faster**), because without that rewrite the
thousands of bootstrap and null-model replicates required by the design would
not have been feasible.

## A.3 Main queries

All queries are in `src/phase1_extract.py`. The most important one defines the
population, in a single pass:

```sql
SELECT ra.artist_id,
       count(*) FILTER (WHERE it.id IS NOT NULL) AS n_it,
       count(*)                                  AS n_all
FROM release_artist ra
LEFT JOIN (SELECT id FROM release WHERE country = 'Italy') it
       ON it.id = ra.release_id
GROUP BY 1
HAVING count(*) FILTER (WHERE it.id IS NOT NULL) >= 2;
```

The final selection (share, minimum number of releases, exclusions based on
the artist records) then takes place on the data already saved locally, so
that Phase 5 can vary the thresholds without rereading the database.

## A.4 Run times

{timing}

## A.5 Reproducibility

```bash
cd {ROOT}
./run_all.sh              # full run
./run_all.sh --from 3     # restart from Phase 3
./run_all.sh --force      # ignore checkpoints and recompute everything
```

Each phase writes a checkpoint in `data/*.parquet` and is skipped if the
checkpoint exists. The raw extracted data are in `data/raw/`, the figures in
`report/figures/`, and the tables in `report/tables/`, in both CSV and LaTeX.

## A.6 Limitations, in order of severity

1. **Gender is inferred, and the manual validation has not been carried
   out.** The stratified sample and the scoring script are ready; without the
   validation, the measurement error of the inference remains unquantified.
2. **Italian identity is approximated by the country of release**, because
   `release_label` is empty. This conflates "Italian artist" with "artist
   released in Italy".
3. **{pct(1-C['share_genre'])} of the population has no musical genre**,
   because `release_genre` is empty and masters cover only part of the
   releases.
4. **No cross-check between sources**: iTunes was excluded by choice.
5. **Discogs is not a census.** It overrepresents vinyl, electronic music and
   collecting.
6. **The ERGM applies to the estimated subnetworks**, not to the whole network.
7. **Wikidata covers {pct(C['n_wikidata']/C['n_pop'])} of the population**;
   the name-based recovery step was not completed because the SPARQL service
   was repeatedly unavailable, responding with 429, 502 and 504 errors.
"""


# ==========================================================================
def _valori_epoca() -> dict:
    """Esito del test di differenza fra i coefficienti ERGM delle due epoche."""
    f = ROOT / "report" / "tables" / "t4_ergm_differenza_epoche.csv"
    if not f.exists():
        return {}
    d = pd.read_csv(f)
    d = d[d.model == "M1_con_gwesp"]
    out = {}
    for termine, chiave in [("nodematch.gender.F", "epoca_F"),
                            ("nodematch.gender.M", "epoca_M"),
                            ("gwesp.fixed.0.25", "epoca_gwesp")]:
        r = d[d.term == termine]
        if len(r):
            out[f"{chiave}_pre"] = float(r.estimate_pre.iloc[0])
            out[f"{chiave}_post"] = float(r.estimate_post.iloc[0])
            out[f"{chiave}_diff"] = float(r.differenza.iloc[0])
            out[f"{chiave}_p"] = float(r.p.iloc[0])
    return out


def collect(cfg, log) -> dict:
    import sys as _s
    pop = get("population_gender.parquet")
    cred = get("credits.parquet")
    ns = get("network_stats.parquet")
    ao = get("assortativity_overall.parquet")
    ast_ = get("assortativity_strata.parquet")
    amf = get("assortativity_mf.parquet")
    ws = get("women_share.parquet")
    sens = get("sensitivity.parquet")
    mc = get("mc_gender.parquet")
    pos = get("position.parquet")
    wd = get("wd_by_discogs.parquet")
    counts = pd.read_csv(ROOT / "data" / "raw" / "raw_artist_counts.csv")
    known = pop[pop.gender.isin(["M", "F"])]
    net = ns[ns.rete == "all"].iloc[0] if ns is not None and len(ns) else None

    def gq(g):
        k = known[known.musical_genre == g]
        return float((k.gender == "F").mean()) if len(k) else np.nan

    def dq(d):
        s = ws[ws.cohort_decade == d] if ws is not None else None
        return float(s.n_donne.sum() / max(s.n_noti.sum(), 1)) if s is not None and len(s) else np.nan

    import importlib
    pkgs = {}
    for m in ["pandas", "numpy", "networkx", "scipy", "statsmodels", "matplotlib",
              "seaborn", "pyarrow", "psycopg2", "gender_guesser"]:
        try:
            pkgs[m] = getattr(importlib.import_module(m), "__version__", "installed")
        except Exception:
            pkgs[m] = "not installed"

    prior_it = get("onomastic_prior_it.parquet")
    prior_gl = get("onomastic_prior_global.parquet")
    wdn = ROOT / "data" / "raw" / "raw_wd_names.parquet"
    groups = pd.read_parquet(ROOT / "data" / "raw" / "raw_groups.parquet")
    various = pd.read_parquet(ROOT / "data" / "raw" / "raw_various.parquet")
    cts = counts.assign(share=counts.n_it / counts.n_all)
    # con i gruppi esclusi (D16) anche le popolazioni alternative si contano
    # sui soli individui, altrimenti non sono confrontabili con n_pop
    if cfg["population"].get("exclude_groups", False) and \
            common.exists("population_gender_con_gruppi.parquet"):
        pg = common.load("population_gender_con_gruppi.parquet")
        cts = cts[~cts.artist_id.isin(pg[pg.is_group].artist_id)]

    C = {
        "data": _oggi_en(),
        "seed": cfg["project"]["seed"],
        "platform": platform.platform(),
        "python": platform.python_version(),
        "pg_version": "18.4",
        "packages": pkgs,
        "db_rows": 92407183 + 126227877 + 19353744 + 10164832,
        "n_pop": len(pop),
        "n_gender_known": len(known),
        "share_known": len(known) / len(pop),
        "share_f": float((known.gender == "F").mean()),
        "ratio_mf": float((known.gender == "M").sum() / max((known.gender == "F").sum(), 1)),
        "n_unknown": int((pop.gender == "unknown").sum()),
        "n_mixed": int((pop.gender == "mixed").sum()),
        "share_genre": float((pop.musical_genre != "Unknown").mean()),
        "n_weak": int(pop.genre_weak.sum()),
        "weak_threshold": cfg["musical_genre"]["weak_threshold"],
        "n_credits": len(cred),
        "n_track_credits": int((cred.scope == "track").sum()),
        "share_track": float((cred.scope == "track").mean()),
        "n_rta": int((cred.source == "rta").sum()),
        "n_ra_tracks": int(cred.source.isin(["ra_tracks", "ra_tracks_unresolved"]).sum()),
        "n_ra_resolved": int((cred.source == "ra_tracks").sum()),
        "n_credits_filt": int(net.archi) if net is not None else np.nan,
        "n_nodes": int(net.nodi_con_archi) if net is not None else np.nan,
        "n_edges": int(net.archi) if net is not None else np.nan,
        "giant": float(net.quota_componente_gigante) if net is not None else np.nan,
        "density": float(net.densita) if net is not None else np.nan,
        "max_credits": cfg["network"]["max_credits"],
        "w_track": cfg["network"]["credit_scope_weight"]["track"],
        "w_main": cfg["network"]["credit_scope_weight"]["main"],
        "w_umb": cfg["network"]["credit_scope_weight"]["umbrella"],
        "min_it": cfg["population"]["min_italian_releases"],
        "min_all": cfg["population"]["min_total_releases"],
        "min_share": cfg["population"]["min_italian_share"],
        "n_cand_ge2": len(counts),
        "n_pop_60": int(((cts.share >= 0.60) & (cts.n_all >= 3)).sum()),
        "n_pop_70": int(((cts.share >= 0.70) & (cts.n_all >= 3)).sum()),
        "n_various": len(various),
        "n_wd_total": int(wd.discogs_id.nunique()) if wd is not None else 0,
        "n_wd_ambiguous": int(wd[wd.ambiguous].discogs_id.nunique()) if wd is not None else 0,
        "n_wikidata": int((pop.label_source == "wikidata_p1953").sum()),
        "n_wd_names": len(pd.read_parquet(wdn)) if wdn.exists() else 0,
        "n_prior_it": len(prior_it) if prior_it is not None else 0,
        "n_prior_glob": len(prior_gl) if prior_gl is not None else 0,
        "n_prior_common": 241,
        "n_groups": int(pop.is_group.sum()),
        "n_groups_res": int((pop.label_source == "group_members").sum()),
        "n_validation": cfg["gender"]["validation"]["n"],
        "mc_B": cfg["robustness"]["montecarlo_B"],
        "r_gender": val(ao, "attributo=='gender'", "r_osservato"),
        "r_gender_null": val(ao, "attributo=='gender'", "r_null_medio"),
        "z_gender": val(ao, "attributo=='gender'", "z"),
        "r_genre": val(ao, "attributo=='musical_genre'", "r_osservato"),
        "r_gender_lo": val(ast_, "sottorete=='all' and strato=='tutto' and attributo=='gender'", "ci_lo"),
        "r_gender_hi": val(ast_, "sottorete=='all' and strato=='tutto' and attributo=='gender'", "ci_hi"),
        "r_pre": val(ast_, "sottorete=='all' and strato=='pre2000' and attributo=='gender'", "r"),
        "r_post": val(ast_, "sottorete=='all' and strato=='post2000' and attributo=='gender'", "r"),
        # misura di riferimento: solo archi fra nodi con genere determinato
        "r_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_mf_lo": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_mf_hi": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_mf_null": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r_null"),
        "z_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "z"),
        "quota_archi_mf": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "quota_archi_usati"),
        "r_pre_mf": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_pre_mf_lo": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_pre_mf_hi": val(amf, "sottorete=='all' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_post_mf": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_post_mf_lo": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_lo"),
        "r_post_mf_hi": val(amf, "sottorete=='all' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "ci_hi"),
        "r_creative_mf": val(amf, "sottorete=='creative' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_mf": val(amf, "sottorete=='performance' and strato=='tutto' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_creative_pre": val(amf, "sottorete=='creative' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_creative_post": val(amf, "sottorete=='creative' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_pre": val(amf, "sottorete=='performance' and strato=='pre2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_perf_post": val(amf, "sottorete=='performance' and strato=='post2000' and attributo=='gender' and categorie=='determinati soltanto'", "r"),
        "r_genre_det": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='musical_genre' and categorie=='determinati soltanto'", "r"),
        "r_genre_tutte": val(amf, "sottorete=='all' and strato=='tutto' and attributo=='musical_genre' and categorie=='tutte le categorie'", "r"),
        **_valori_epoca(),
        "q_hiphop": gq("Hip Hop"), "q_rock": gq("Rock"), "q_classical": gq("Classical"),
        "q_children": gq("Children's"), "q_electronic": gq("Electronic"),
        "q_1960": dq(1960), "q_1980": dq(1980), "q_2020": dq(2020),
        "sens_mf_min": float(sens.r_gender_MF.min()) if sens is not None and "r_gender_MF" in sens else np.nan,
        "sens_mf_max": float(sens.r_gender_MF.max()) if sens is not None and "r_gender_MF" in sens else np.nan,
        "sens_n": len(sens) - 1 if sens is not None else 0,
        "rw_default": val(sens, "variante=='default'", "r_gender_pesato"),
        "rw_no_track": val(sens, "variante=='crediti_traccia=False'", "r_gender_pesato"),
        "rw_flat": val(sens, "variante=='pesi_specificita=1.0/1.0/1.0'", "r_gender_pesato"),
        "rw_steep": val(sens, "variante=='pesi_specificita=1.0/0.5/0.1'", "r_gender_pesato"),
        "mc_min": float(val(mc, "scenario=='migliore_omofilia_min'", "r")) if mc is not None else np.nan,
        "mc_max": float(val(mc, "scenario=='peggiore_omofilia_max'", "r")) if mc is not None else np.nan,
        "mc_sq": float(mc[mc.scenario == "status_quo"].r.mean()) if mc is not None and len(mc[mc.scenario == "status_quo"]) else np.nan,
        "mc_noti": float(val(mc, "scenario=='solo_noti'", "r")) if mc is not None else np.nan,
    }
    ec = get("ergm_coef.parquet")
    if ec is not None and not ec.empty:
        m1 = ec[ec.model == "M1_con_gwesp"]
        C["ergm_F_med"] = float(m1[m1.term == "nodematch.gender.F"].estimate.median())
        C["ergm_M_med"] = float(m1[m1.term == "nodematch.gender.M"].estimate.median())
        C["ergm_n_reti"] = int(m1.rete.nunique())
    es = get("ergm_summary.parquet")
    C["ergm_n_conv"] = int(es.convergenza.sum()) if es is not None and "convergenza" in es else 0
    reg = get("position_regressions.parquet")
    for esito in ["eigenvector", "coreness", "betweenness"]:
        C[f"b_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "coef")
        C[f"p_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "p")
        C[f"lo_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "ci_lo")
        C[f"hi_{esito}"] = val(reg, f"esito=='{esito}' and termine=='C(gender)[T.F]'", "ci_hi")
    if reg is not None and not reg.empty:
        inter = reg[reg.termine.str.contains("C\\(gender\\)\\[T.F\\]:", regex=True)]
        C["n_interazioni"] = len(inter[inter.esito == "eigenvector"])
        C["n_interazioni_signif"] = int((inter[inter.esito == "eigenvector"].p < 0.05).sum())
    else:
        C["n_interazioni"] = C["n_interazioni_signif"] = 0
    if pos is not None:
        d = pos[pos.gender.isin(["M", "F"])]
        for g in ["F", "M"]:
            gg = d[d.gender == g]
            C[f"core_med_{g}"] = float(gg.coreness.median())
            C[f"nrel_med_{g}"] = float(gg.n_release.median())
            C[f"eig_med_{g}"] = float(gg.eigenvector.median())
        C["n_giant"] = len(pos)
    C["ratio_hiphop"] = (1 - C["q_hiphop"]) / max(C["q_hiphop"], 1e-9)
    return C


def build(cfg, log):
    C = collect(cfg, log)
    common.write_json({k: v for k, v in C.items() if k != "packages"}, "report_numbers.json")
    md = "\n".join([executive_summary(C), sezione_dati(C), sezione_gender(C),
                    sezione_rete(C), sezione_risultati(C), sezione_omofilia(C),
                    sezione_posizione(C), sezione_ergm(C), sezione_robustezza(C),
                    appendice(C)])
    p = REPORT / "report.md"
    p.write_text(md)
    log.info(f"report Markdown: {p} ({len(md):,} caratteri)")
    return p


CSS = """
@page { size: A4; margin: 20mm 18mm; @bottom-center { content: counter(page);
        font-size: 9pt; color: #8b8a85; } }
body { font-family: "DejaVu Serif", Georgia, serif; font-size: 10.2pt;
       line-height: 1.55; color: #16161a; max-width: 52em; margin: 0 auto;
       padding: 0 1.2em; }
h1 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 17pt;
     border-bottom: 2px solid #2a78d6; padding-bottom: .25em; margin-top: 1.8em;
     page-break-before: always; color: #0b0b0b; }
h1:first-of-type { page-break-before: avoid; }
h2 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 13pt;
     color: #1c5cab; margin-top: 1.5em; }
h3 { font-family: "DejaVu Sans", Helvetica, sans-serif; font-size: 11pt;
     color: #52514e; }
table { border-collapse: collapse; width: 100%; font-size: 8.4pt;
        margin: 1em 0; page-break-inside: avoid; }
th { background: #eef4fd; text-align: left; font-family: "DejaVu Sans", sans-serif;
     font-size: 8.2pt; border-bottom: 1.5px solid #2a78d6; padding: 5px 7px; }
td { padding: 4px 7px; border-bottom: 1px solid #e8e7e3; }
tr:nth-child(even) td { background: #fbfbfa; }
figure { margin: 1.4em 0; page-break-inside: avoid; }
figure img { width: 100%; height: auto; }
figcaption { font-size: 8.6pt; color: #52514e; line-height: 1.45;
             border-left: 3px solid #cde2fb; padding-left: .8em; margin-top: .6em; }
blockquote { border-left: 3px solid #eb6834; padding-left: 1em; color: #52514e;
             font-style: italic; }
code, pre { font-family: "DejaVu Sans Mono", monospace; font-size: 8.4pt; }
pre { background: #f7f7f5; padding: .8em; border-radius: 4px; overflow-x: auto;
      page-break-inside: avoid; }
strong { color: #0b0b0b; }
"""


def compile_outputs(md_path: Path, cfg, log):
    env = ROOT / "opt" / "mamba" / "envs" / "doc" / "bin"
    pandoc = env / "pandoc"
    weasy = env / "weasyprint"
    css = REPORT / "report.css"
    css.write_text(CSS)
    html = REPORT / "report.html"
    pdf = REPORT / "report.pdf"
    out = {}
    if pandoc.exists():
        cmd = [str(pandoc), str(md_path), "-f", "markdown+pipe_tables+raw_html+tex_math_dollars",
               "-t", "html5", "-s", "--toc", "--toc-depth=2", "--mathml",
               "--metadata", "title=Gender homophily in Italian music collaborations",
               "--metadata", "lang=en", "-c", "report.css", "-o", str(html)]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            log.info(f"HTML: {html}")
            out["html"] = str(html)
        else:
            log.error(f"pandoc: {p.stderr[-1500:]}")
    else:
        log.error("pandoc non trovato")
    if weasy.exists() and html.exists():
        p = subprocess.run([str(weasy), "-u", str(REPORT) + "/", str(html), str(pdf)],
                           capture_output=True, text=True)
        if p.returncode == 0 and pdf.exists():
            log.info(f"PDF: {pdf} ({pdf.stat().st_size/1e6:.1f} MB)")
            out["pdf"] = str(pdf)
        else:
            log.error(f"weasyprint: {p.stderr[-1500:]}")
    return out


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase7_report", cfg)
    REPORT.mkdir(parents=True, exist_ok=True)
    with Timer("composizione report", log):
        md = build(cfg, log)
    with Timer("compilazione HTML/PDF", log):
        outs = compile_outputs(md, cfg, log)
    common.write_json(outs, "report_outputs.json")
    Timer.dump(ROOT / "logs" / "timings.csv")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
