# Decision log

Each entry is a choice that could have been made differently. The alternatives
are listed because a referee will propose them, and it is better for the
answer to be already written.

---

## D1. Extraction without server-side objects

*Choice.* No temporary tables, no views, no functions: lists of identifiers are
sent back to the database as `int[]` literals.

*Alternative.* Temporary tables, which are the natural approach.

*Why rejected.* The read-only constraint forbids them. `CREATE TEMP TABLE`
fails under `default_transaction_read_only = on`, because a temporary table is
still a write to the catalog.

*Consequence.* Longer and less readable queries, in exchange for the guarantee
that the source databases were not touched. This can be checked: there is no
`INSERT`, `CREATE` or `UPDATE` anywhere in `src/`.

---

## D2. Italian nationality as a declared heuristic, not as data

*Choice.* An artist is Italian if at least half of their releases have
`country = 'Italy'`, with a minimum of two Italian releases.

*Alternative.* Use Wikidata `P27` as the criterion.

*Why rejected.* `P27` covers only the fraction of artists present in Wikidata:
4,663 of 100,201, or 4.7%. Using it as the criterion would have restricted the
population to those well known enough to have an entry, which is exactly the
bias to avoid when studying a minority.

*Why it is defensible nonetheless.* `P27` was used not as a criterion but as a
validation: on the 4,663 verifiable artists the heuristic has a precision of
94.5%, which rises monotonically with the threshold. The monotonicity matters
more than the level: it shows that the measure ranks correctly, not only that
it is often right.

---

## D3. Order of the name dictionaries: Italian before global

*Choice.* The Italian prior is consulted first; the global one only when the
Italian one has no answer.

*Alternative.* A global dictionary, larger and apparently more neutral.

*Why rejected.* Andrea, Simone, Nicola, Daniele, Michele and Gabriele are male
in Italian and female in dictionaries dominated by English-language data. On an
Italian population the reverse order would have classified thousands of men as
women, and the error would have been systematic and directional: it would have
inflated the female share in exactly the direction that makes the article more
interesting. This kind of error does not show up in the totals.

---

## D4. `unknown` excluded from the assortativity calculation

*Choice.* Assortativity is computed on determined cases only; the version with
`unknown` as a fourth category is reported separately.

*Alternative.* Keep `unknown` as a category, which uses all edges.

*Why rejected.* Undetermined gender is not a gender; it is an absence of
information. Treating it as a category partly measures the co-occurrence of
obscure artists, not homophily.

*Why the choice is not opportunistic.* On gender the exclusion *lowers* the
coefficient (from 0.0735 to 0.0511), that is, it weakens the result. On musical
genre it *raises* it (from 0.5186 to 0.5865). The signs are opposite and the
same rule is applied: the rule was not chosen by looking at the outcome.

---

## D5. Three levels of credit specificity

*Choice.* Tie weight `w(u,v) = w_t·|shared tracks| + w_r·Σ s_u·s_v`, with
specificity 1.0 for track, 0.7 for main release and 0.3 for umbrella credits.

*Alternative.* Count every co-occurrence in the same way.

*Why rejected.* Two musicians credited on the same track have collaborated; two
named at the end of a compilation may never have met. Weighting them equally
conflates the two. The Discogs `tracks` field is free text, and whatever cannot
be resolved is downgraded to umbrella rather than forced onto a track: when in
doubt, the tie weighs less, never more.

---

## D6. Dating ties, not people

*Choice.* Each edge is dated by the year of the first release shared by the two
artists.

*Alternative.* Define an edge as "pre-2000" if both endpoints debuted before
2000.

*Why rejected.* A tie formed in 1975 between a newcomer and a veteran is a 1975
tie, not a tie belonging to two eras. Moreover, the agreement rule discards
precisely the intergenerational collaborations, which are among the most
interesting.

*Consequence.* This is the decision that made the central result visible. With
the cohort-based definition the reversal could not be seen.

---

## D7. Snowball subnetworks abandoned

*Choice.* No estimate on a sampled subnetwork appears in the final results.

*Alternative.* Keep them as an approximation, stating their limitations.

*Why rejected.* For an estimate based on a snowball sample, one cannot say what
it is an estimate of: the sample is not representative of any definable
population. Stating the limitation does not remove it.

*Replaced by.* The decade as the unit, which is a complete population, and
exact computation on the whole network.

---

## D8. Compute rather than estimate, wherever possible

*Choice.* Dyadic logit on all 1,619,630,155 dyads; closed-form permutation
moments; exact betweenness from all 79,013 sources.

*Alternative.* Case-control sampling, a thousand permutations, 400 sources,
that is, what was there before.

*Why rejected.* There was no good reason to approximate what can be computed,
and two of the four approximations biased the results (see
[`03-errori.md`](03-errori.md)).

*Cost.* About three hours of machine time for the exact logit and one hour for
betweenness. Everything else is faster than the sampled version, because a
closed-form expression costs less than a thousand permutations.

---

## D9. The decade as the unit of ERGM analysis

*Choice.* Where the ERGM can be estimated, it is estimated by decade.

*Alternative.* Sampled subnetworks of the desired size.

*Why rejected.* See D7. A decade has a flaw (it is not independent of the
others), but it is a flaw that can be declared, whereas the lack of a
reference population for a snowball sample cannot.

---

## D10. The projection not given to the model as a covariate

*Choice.* No `edgecov` term with the size of the shared cast was added.

*Alternative.* Give it to the model, so that `gwesp` has to explain only the
residual.

*Why rejected.* If two artists share a release they have an edge by
construction: the covariate would be non-zero exactly on the edges and zero
elsewhere, so it would separate the data perfectly. This is a dead end, and it
is documented because it looks like the obvious route.

---

## D11. Goodness of fit enabled for the decades, disabled for the full network

*Choice.* GOF with 100 simulated networks for the decades; no GOF on the full
network.

*Reason.* Simulating a network of 57,000 nodes costs as much as one iteration
of the estimation; a hundred simulations would cost more than the estimation
itself. On the decades it is cheap.

*Relevance.* It was the GOF that exposed an apparent convergence on the full
network: an estimate that reported success while producing networks with 40%
of the observed edges and 4% of the ties between women. Without it, that
result would have ended up in the article.

---

## D12. The reference null model conditions on activity

*Choice.* The observed/expected ratios of the time series are computed by
permuting labels within degree strata (Phase 4j). The closed-form uniform
permutation is still reported, for comparison.

*Alternative.* The uniform permutation, which was the reference until 24
September and is exact.

*Why rejected.* It is exact as a computation but answers a different question:
"do women form ties with one another more than labels assigned at random to
*any* artist would?". Women have fewer ties, and that null compares them with
artists more active than they are. The question of the article is whether
women form ties with one another more than artists *with the same activity*
would. See E13 in [`03-errori.md`](03-errori.md).

*Why the choice is not opportunistic.* It weakens the most striking result (the
sign reversal disappears) and strengthens another: the recent level goes from
1.17–1.66 to a stable plateau around 1.7. It also agrees with the two tools
already in place that conditioned on activity, the degree-preserving mixing
matrix and the logit with `sum_lognrel`.

---

## D13. The paper is limited to 8,000 words of main text

*Choice.* From the abstract to the conclusion, including tables and captions,
excluding references and appendices, following the convention of Elsevier
journals. The count is done in `paper.py` and written to
`data/paper_status.json`; Markdown table separators and image paths do not
count as words.

*Alternative.* The raw count of the whole file, which was the figure reported
earlier (12,811) and which also counted the `|` characters of the tables.

*Consequence.* The long version is kept locally in
`paper/versioni/2026-09-24_v2_12811-parole/`.

---

## D14. Stated hypotheses, and what remains exploratory

*Choice.* The paper poses one research question and six hypotheses (H1–H6,
with a competing hypothesis H2′). The differences between musical genres and
the sensitivity to the null model that accounts for activity are declared
exploratory.

*Alternative.* Turn these two results into hypotheses as well, which would
strengthen the article.

*Why rejected.* They arose from the analysis (Phases 4j and 4k, 24 September),
not from theory: presenting them as hypotheses would be HARKing (formulating
hypotheses after seeing the results), and this documentation, which is public,
would show it. For the same reason H3 has no direction: the brief asked
*whether* homophily changed over time, not that it increased.

*Caution about the others.* The paper says that the hypotheses derive from the
literature, not that they were registered before the analysis. The brief posed
the questions behind H1, H4 and H5 (musical genre, roles, position), but not
the direction of H4, and H2 was written down after the first estimates. The
formulations follow the cited literature, and H4 and H5 are rejected: they were
not adjusted to fit the results. But none of them is preregistered, and it must
not be claimed that any is.

---

## D15. The manuscript kept out of the public repository

*Choice.* `paper/` and the two scripts that generate the article
(`src/paper.py`, which contains its full text, and `src/paper_figures.py`) are
not under version control, and were removed from the entire history of the
repository on 24 September, with a history rewrite and a force push. They
remain local.

*Reason.* The repository is public, and a manuscript under submission should
not circulate before publication.

*Consequence.* Phase 9 of `run_all.sh` runs only where those files are
present. Everything else (data, analysis, tests, documentation) remains
verifiable by third parties. The hashes of commits made before 24 September
have changed, and the tag `paper-v2-12811` no longer exists.

---

## D16. The person as the unit of analysis: groups are removed

*Choice.* Groups (artists with members registered in Discogs) are removed from
the population after gender inference (`population.exclude_groups` in
`config.yaml`), and their credits are removed from the network (Phase 2). This
leaves 87,229 individual artists out of 100,201. The full population is kept in
`population_gender_con_gruppi.parquet`.

*Alternatives.*
1. Keep groups as nodes, as was done until 24 September.
2. Replace each group with its members, transferring the credits to them.

*Why rejected.*
1. A group and its members appear on the same releases: counting both
   duplicates ties and creates group–member ties (15,074, 3% of the total)
   that are not collaboration choices. Of the registered members, 76% are also
   in the population as individuals, and 5,411 of the 5,958 groups present in
   the network are tied to at least one of their own members. In addition,
   groups are almost all male (5,288 against 128 female), and counting them as
   "artists" lowered the female share from 14.8% to 13.8%.
2. The dump has no membership dates: a 1972 record would be attributed to
   someone who joined the group in 1990.

*Why it is not opportunistic.* It weakens the central result: in a preliminary
check, by decade and at equal activity, the excess of woman–woman ties falls
from about 1.7 to about 1.55 times chance. The emergence remains intact: no
homophily in the 1950s and 1960s, significant from the 1970s, men always at
1.00–1.01. The `mixed` category, which existed only for groups, disappears, and
with it the `same_mixed` term of the logits.

*Requested* by the author on 24 September, after noticing the risk of double
counting.

---

## D17. Entries that are not persons: a sensitivity analysis, not a new definition

*Choice.* The population remains the one defined in D16. A sensitivity phase
(4l) removes the entries whose name signals a non-person (bands, orchestras,
choirs, labels, music publishers, studios, "e la sua orchestra", names that
begin with a plural article, local variants of "Various") and recomputes
assortativity and the series by decade.

*Alternative.* Change the primary definition of the population.

*Why rejected.* The effect is negligible (assortativity unchanged, series
within 0.03), almost all of those entries are already undetermined, and in the
international comparison the definition is registered on OSF: changing it
across the two studies would have created a divergence, or a deviation, for
nothing. The filter is a declared approximation: it does not catch entries
without markers (pseudonyms).

*Origin.* The manual coding of the validation sample, 25 September 2026.
