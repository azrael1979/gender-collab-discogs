# Status of the results

Each result is labeled by how solid it is: *measured* (computed on the data;
it fails only if the data are wrong), *estimated* (depends on a model and its
assumptions), *interpreted* (a proposed explanation of a fact; it can be wrong
even if the fact is right).

> Values updated on 25 September 2026, after the exclusion of groups
> (D16 in [`02-decisioni.md`](02-decisioni.md)): the unit of analysis is the
> person. The earlier values, with groups as nodes, are kept in
> `data/con_gruppi_2026-09-24/` and in the git history of this file. The
> conclusions do not change; the magnitudes are smaller.

---

## Main result: emergence

Status: measured. The permutation test does not assume independence between
dyads: it permutes labels while holding the network fixed. The reference is
permutation within degree strata (Phase 4j), which compares each woman with
artists who have the same number of ties; the uniform permutation, which
ignores activity, is reported alongside because it was the earlier reading.

| decade | share of women | F–F obs/expected, by degree | *z* | F–F, uniform | M–M, by degree | logit `same_F` | logit `same_M` |
|---|---|---|---|---|---|---|---|
| 1950 | 13.4% | 1.075 | 0.8 | 0.460 | 1.002 | +0.082 | +0.032 |
| 1960 | 16.5% | 1.033 | 0.7 | 0.480 | 1.004 | +0.053 | +0.039 |
| 1970 | 14.1% | **1.201** | **4.3** | 0.574 | 1.003 | +0.086 | +0.174 |
| 1980 | 11.9% | **1.284** | **5.6** | 0.884 | 1.004 | +0.194 | +0.115 |
| 1990 | 11.5% | **1.457** | **9.7** | 1.182 | 1.009 | +0.368 | +0.120 |
| 2000 | 10.7% | **1.583** | **16.8** | 1.212 | 1.005 | +0.413 | +0.141 |
| 2010 | 10.9% | **1.555** | **15.0** | 1.075 | 1.006 | +0.398 | +0.161 |
| 2020 | 11.4% | **1.519** | **10.6** | 1.362 | 1.006 | **+0.508** | −0.006 |

The result rests on three distinct facts.

1. It is an emergence, not a reversal. Among equally active artists, in the
   1950s and 1960s women formed ties with each other neither more nor less
   often than chance. The excess becomes significant in the 1970s, grows until
   the 2000s and from then on stays around 1.55. The logit, which controls for
   musical genre, cohort and activity, shows the same with a decade's delay:
   `same_F` is not significant through the 1970s, then ranges from +0.19 to
   +0.51. An ERGM on the 1950s, which also controls for triadic closure,
   confirms the initial absence: `gender.F` +0.058 (*p* 0.56), `gender.M`
   +0.032 (*p* 0.13).
2. It is asymmetric. The male ratio lies between 1.002 and 1.009 in every
   decade; `same_M` lies between −0.01 and 0.17, with no trend.
3. It is not a compositional effect. The female share falls from 16.5% to
   10.7% and recovers only to 11.4%. With proportionally *fewer* women, those
   who are present collaborate with each other more and more.

Italian women musicians, in other words, did not gain ground in numbers, but
they increasingly found each other as collaborators.

Two earlier readings were dropped. Under the uniform null the series looked
like a sign reversal (a deficit until the 1970s, 0.46–0.57); this was an
effect of women's lower activity (E13). With groups as nodes the recent excess
appeared to be around 1.7; group–member ties inflated it by about a tenth
(D16).

---

## By pair type, decade and musical genre (Phase 4k)

Status: measured (the densities); the Poisson intervals for the ratios assume
independence between ties and are optimistic.

| decade | woman–woman / mixed | man–man / mixed | woman–woman / man–man | FF by degree | MF by degree |
|---|---|---|---|---|---|
| 1950 | 0.68 | 1.64 | 0.41 | 1.08 | 0.98 |
| 1980 | 1.08 | 1.29 | 0.84 | 1.28 | 0.97 |
| 2000 | 1.45 | 1.24 | 1.17 | 1.58 | 0.95 |
| 2020 | 1.51 | 1.13 | 1.34 | 1.52 | 0.94 |

Mixed pairs below chance are not additional evidence: the null holds each
artist's number of ties fixed, so every woman–woman tie above expectation is a
woman–man tie below expectation. It does show, however, that ties between
women replaced ties with men.

The emergence is not uniform across musical genres. Pop: at chance until the
1970s (0.93–1.03), 1.35–1.72 from the 1980s. Rock: 1.34–2.08 from the 1980s.
Electronic: from 1.02 in the 1980s to 1.56 in the 2010s. Folk and jazz:
significant peaks with no trend. Classical: 1.14–1.52, never significant, so
no emergence. Many cells have too few women to support any conclusion. In the
article: Section 4.4, Table 5, Figure 4.

---

## Musical genre outweighs gender

Status: measured.

| | assortativity |
|---|---|
| musical genre | 0.562 |
| gender | 0.0432 |

The difference is an order of magnitude. This result survives every
robustness variant tried, and the exclusion of groups.

---

## Conditional homophily on the full network

Status: estimated. Exact point estimates on all 1,306,346,055 dyads; standard
errors are optimistic because they assume independence between dyads.

| term | coefficient | 95% CI | odds ratio |
|---|---|---|---|
| `same_F` | **+0.242** | [0.216 – 0.268] | **1.274** |
| `same_M` | **+0.167** | [0.159 – 0.174] | 1.181 |
| `same_genre` | +1.644 | [1.638 – 1.650] | 5.176 |
| `same_cohort` | +1.195 | [1.189 – 1.201] | 3.304 |

The intervals do not overlap: holding musical genre, cohort and activity
constant, a tie between two women is more likely than one between two men.
The degree-stratified permutation agrees on the full network; the uniform
permutation gives F 0.735, for the reason given above.

---

## Credit roles

Status: measured.

| subnetwork | gender assortativity |
|---|---|
| creative (composers, arrangers, producers) | 0.0224 |
| performing (vocals, instruments) | 0.1054 |

A factor of 4.7. Gender homophily is concentrated in performing roles and
nearly absent in creative ones (H4 rejected).

---

## Network position by gender

Status: estimated, with exact betweenness computed from all sources.

| axis | main effect of F | p |
|---|---|---|
| eigenvector | +0.180 | 0.31 |
| coreness | +0.036 | 0.65 |
| betweenness | −0.293 | **0.083** |

No effect is significant at the 5% level, and none of the 36 interactions with
musical genre is. Betweenness is closest to the threshold. With betweenness
sampled from 400 sources (Phase 3d), the same effect would be −0.323 with
*p* 0.040: the usual approximation would have produced a significant
Smurfette effect that the exact computation does not confirm. The inequality
lies in the tail: among the 100 artists with the highest eigenvector
centrality, 2 are women.

---

## Cost of approximation on this network

| | sampled | exact |
|---|---|---|
| case-control logit, `same_F` / `same_M` | 0.201 / 0.194 | **0.242 / 0.167** |
| betweenness, effect of F | −0.323 (*p* 0.040) | **−0.293 (*p* 0.083)** |
| permutation, 1,000 replicates | ratios identical to the fourth digit | closed form |

Case-control sampling compresses the gap between women and men by 91%: with
sampling, H2 would not have been confirmed.

---

## Methodological contribution

Status: demonstrated.

Measured: across all 586,040 edges, where a single release can explain an
edge's shared partners, it explains 98.5% of them; where it cannot, 26.5%.

Observed: the goodness of fit of the ERGMs fails with a U shape in three
independent decades (1930, 1940, 1950).

Demonstrated: the randomized projection, which has no parameters, reproduces
the shape of the shared-partner distribution better than the estimated ERGM in
both comparable decades: 12 times better in the 1940s (deviation 0.236 against
2.779), 1.4 times better in the 1950s (0.720 against 1.015). The margins
differ widely, so the range should be reported, not the best case.

ERGM: estimable up to 13,919 ties (1950s), not beyond 30,629 (2020s); the
1960s fail. With groups the threshold was between 1,932 and 15,177:
group–member cliques added mechanical triangles.

---

## Collaborations recur

Status: measured. On the full network the randomized projection produces
1,875,273 edges against 765,363 observed: actual collaboration is 2.45 times
more concentrated than chance. The projection mechanism explains the *shape*
of the shared-partner distribution; the social process explains its
*concentration*.

---

## Quality of the underlying data

| | |
|---|---|
| Italian entries in Discogs | 100,201, of which 12,972 groups |
| **individual artists** | **87,229** |
| gender determined | 74.6% (55,480 M, 9,613 F) |
| female share among determined | 14.8% |
| credits | 3,682,616, of which 64.1% resolved at track level |
| network | 70,712 nodes with edges, 586,040 edges, giant component 95.4% |
| validation of Italian nationality | 94.5% of 4,634 verifiable with `P27` |

---

## Gender validation (completed)

Status: measured, on 200 artists drawn by stratified sampling and hand-coded
by the author, blind to the labels (25 September 2026; a first version of the
coding was corrected by the author before the final computation).

| | |
|---|---|
| labeled M or F by the cascade | 168 |
| in agreement with the annotator | **94.6%** |
| in agreement, among those the annotator determined | 97.5% (163), 4 M↔F reversals |
| Italian dictionary / Wikidata | 98% / 95% |
| weak point | global dictionary, female labels (4 of 8) |
| undetermined cases resolved by the annotator | 13 of 32: 10 M, 3 F |

The resolved undetermined cases are not more male than the determined ones
(23% women against 14.8%). There is no sign that excluding them inflates the
female share, though this rests on 13 cases. A blind automated annotation,
produced by AI agents on the earlier sample (with groups), is kept in
`data/validazione_ia/` and was not used.

---

## Entries that are not persons (Phase 4l, sensitivity)

The coding revealed bands without registered members, orchestras, choirs,
labels, graphic design studios and variants of "Various" among the
"individuals". Those with an explicit marker in the name number 3,173 (3.6%),
147 of them with an assigned gender; they are involved in 3.5% of ties.
Removing them leaves gender assortativity at 0.0432 and shifts no decade ratio
by more than 0.03. See D17.

---

## Open items

* Italian report (Phase 7): still reflects the withdrawn thesis; it must be
  rewritten or declared superseded.
* Zenodo deposit of the data package, without the manuscript (D15).
