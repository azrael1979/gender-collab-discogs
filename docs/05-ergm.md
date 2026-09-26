# ERGM record

This document is longer than the others because the ERGM took up most of the
time and in the end produced a negative result, which nonetheless became the
methodological contribution of the study. The sequence of attempts is
therefore as relevant as the outcome.

---

## Rationale for an ERGM

Homophily measures (assortativity, mixing matrices, permutation tests)
indicate whether similar artists collaborate more than chance would predict.
They do not indicate why. Two women may be connected because they seek each
other out, or because they share an acquaintance and triadic closure does the
rest. An ERGM with a closure term (`gwesp`) is the standard way to separate
the two.

The reference specification:

    net ~ edges
        + nodematch('gender', diff = TRUE)
        + nodematch('musical_genre')
        + nodecov('log_nrel')
        + nodematch('cohort_decade')
        + gwesp(0.25, fixed = TRUE)

---

## Phase 1: sampled subnetworks (convergent but uninterpretable)

With snowball-sampled subnetworks capped at 1,500 nodes and 5,000 edges, the
ERGM converges. Median female homophily is 0.679, against 0.074 for men.

The problem was not convergence but the target of inference. For an estimate
from a snowball sample, one cannot say what it is an estimate of: the sample
does not represent any definable population. A referee would have raised this
limitation first, and it is the reason these estimates do not appear in the
final results.

A technical note: `nodematch("musical_genre")` is collinear with `edges`
within a subnetwork that has a single musical genre. The term is included only
when the attribute actually varies.

---

## Phase 2: the full network, four failures

Four parametrizations were tried, and all failed. Their failure signatures are
worth distinguishing, because they have different diagnostic meanings.

| # | specification | method | outcome |
|---|---|---|---|
| 1 | `gwesp(0.25)` | MCMLE | optimizer step size collapsed from ~0.46 to ~0.005 |
| 2 | `gwesp(0.5)` | MCMLE | iterations doubled in length: 29 min, 62, 125, over 243 |
| 3 | `gwesp(0.25) + gwdegree` | MCMLE | same |
| 4 | `gwesp(0.5)` | Stoch. Approx. | convergence reported, and false |

### The two signatures

Collapsing step size (#1). The optimizer reduces the step length by two orders
of magnitude to stay inside the feasible region. This is classic
near-degeneracy.

Lengthening iterations (#2, #3). The iterations took 29 minutes, then 62, then
125, then over 243. Extrapolating, the seventh would have taken thirty-two
hours. An estimation whose iterations lengthen in this way is not converging
slowly; it is diverging slowly.

### The fourth case: false convergence

Stochastic approximation reported success. The goodness-of-fit diagnostics
contradicted it:

* effective sample size ≈ 3 (it should be in the hundreds);
* simulated networks with 40% of the observed edges;
* 4% of the ties between women;
* negative coefficients for musical genre and cohort, i.e. the model predicted
  that artists sharing a musical genre collaborate *less*.

It was a collapse toward the empty graph that looked like convergence.
Without the GOF check it would have ended up in the article.

This led to rule D11: goodness of fit is not optional; it is the only check
that distinguishes real convergence from apparent convergence.

---

## Phase 3: estimation by decade

The suggestion we received, to run the model by decade in order to reduce
complexity, was correct, though not for the obvious reason.

What it solves: size. The decades up to the 1950s have 163, 364 and 1,515
gender-determined nodes (150, 338 and 1,398 in the giant component on which the
ERGM is fitted, as in the table below), the order of magnitude at which
estimation had worked.

What it really solves: a decade is a complete population, not a sample. This
corrects the defect of Phase 1.

What it does not solve: clustering. Measured decade by decade, it stays
between 0.43 and 0.56 in every period. Splitting the network does not lower
it, and cannot: it is a projection artifact.

### Outcome

With groups as nodes (before D16); the rerun without groups is reported at
the end of this document.

| decade | nodes | edges | clustering | outcome | signature |
|---|---|---|---|---|---|
| 1930 | 150 | 514 | 0.466 | converged, 21 min | — |
| 1940 | 338 | 1,932 | 0.466 | converged, 52 min | — |
| 1950 | 1,398 | 15,177 | 0.526 | failed | diverging iterations (no output for 2 h) |
| 2020 | 11,772 | 33,548 | 0.426 | failed | step < 0.02 for 3 iterations |

The prediction stated before the runs was wrong. The module docstring said
"converges up to the 1960s or 1970s". Estimation already breaks down at
15,177 edges. The prediction had been written in advance precisely so that it
could be falsified, and it was.

The test on the 2020s was poorly designed. That decade had been queued as a
test to separate size from clustering: it is the least clustered decade, but
also larger than the 1950s. Because the run failed, its outcome confounds the
two causes and decides nothing. It does not show that size is the
constraint, and it does not rescue the clustering hypothesis.

What remains established is the weaker claim: the estimability threshold lies
between 1,932 and 15,177 edges.

The queue was stopped. The remaining decades were 1960, 1970, 1980, 2010, 1990
and 2000, all larger than *both* failed cases; running them would have taken
about 36 hours to confirm an outcome already determined.

### Estimates for the two converged decades

| | `gwesp` | `gender.F` | `gender.M` | `genere_musicale` |
|---|---|---|---|---|
| 1930 | +2.391 | −0.262 (p 0.79) | +0.011 (p 0.89) | +0.275 |
| 1940 | +3.582 | −0.246 (p 0.36) | **−0.173** (p<10⁻⁴) | +0.361 |

There is no female homophily. This agrees with the permutation test: for those
decades the degree-stratified null gives F ratios of 0.70 and 0.74, with *z*
of −0.4 and −1.1, indistinguishable from chance. (The uniform null gave 0.24
and 0.50, and an earlier reading had taken these as confirmation of *negative*
homophily; it was an effect of women's lower activity, see E13.)

Two methods with opposite assumptions agree on the period in which both work:
the ERGM controls for triadic closure and for activity, while the permutation
test holds the structure fixed by construction, and both find no gender
homophily in those decades. This strengthens the other end of the series: the
excess in the 1990s to 2020s is a real change, not a measurement artifact
that would apply to the whole series.

---

## Diagnosis

The goodness of fit of the two converged decades fails at a specific point,
and with the same shape:

| shared partners | 1930 obs/sim | 1940 obs/sim |
|---|---|---|
| 0 | **2.36** | **8.69** |
| 1 | 0.46 | 0.43 |
| 2 | 0.42 | 0.41 |
| 4 | 1.55 | 1.31 |
| 6 | 5.78 | 4.38 |
| 8 | **20.55** | **6.54** |

The pattern is U-shaped: the center is overestimated and both tails are
underestimated. This is what one obtains by fitting a unimodal distribution
(the only kind `gwesp` can produce, since it has a single parameter) to a
bimodal one.

### The hypothesis and a direct check

The hypothesis is that the bimodality is not a social phenomenon but an
artifact of construction. This network is the projection of a bipartite
artist–release graph, and every release with *k* credited artists generates a
clique of size *k* in which each edge has *k−2* shared partners by
construction, without anyone having closed a triangle in a social sense.

This can be checked exactly, edge by edge, without estimating anything. For
each edge we separate the *total* shared partners (what `gwesp` models) from
those *imposed by the projection*, that is, artists who appear on a release
shared by the edge's two endpoints.

Across all 702,613 edges:

```
 9,460,875  total shared partners
 3,208,170  imposed by the projection         (33.9%)
   259,458  edges fully explained             (36.9%)
    17,353  edges with no shared partner      (2.5%)
```

The overall 33.9% is not high: taken at face value, the hypothesis was wrong,
and this should be stated. The breakdown, however, shows the structure. With
`max_credits = 8`, a release can impose at most 8−2 = 6 shared partners:

| shared partners | share explained |
|---|---|
| 1 | 0.823 |
| 3 | 0.824 |
| 5 | 0.810 |
| 6 | 0.792 |
| **7** | **0.659** |
| 12 | 0.445 |
| 19 | 0.319 |

The share is flat at about 80% up to 6, then drops. The cap test turns this
coincidence into a demonstration. For each edge, *k−2* is computed from the
largest shared release:

| | edges | share explained |
|---|---|---|
| within the cap | 232,783 (33.1%) | **0.988** |
| beyond the cap | 452,477 (64.4%) | **0.276** |

Where a single release *can* explain the triangles, it explains 98.8% of them.
Where it cannot, the share falls. This is not a correlation but the arithmetic
signature of the mechanism.

Status: measured. It does not depend on any model.

---

## A failed attempt at causal confirmation

So far the diagnosis is correlational: a defect is observed and a cause is
proposed. A referee would be right not to be satisfied with that.

### Design

Re-estimate the 1940 decade (the one that converges in under an hour) with
two-component dependence terms, which can produce a bimodal shape by
construction, and measure whether the U flattens. A negative control is
included so that the test can discriminate between explanations.

| specification | components | prediction if the hypothesis is correct |
|---|---|---|
| `gwesp(0.25)` (reference) | 1 | marked U |
| `gwesp(0.25) + gwesp(1.5)` | 2 | flattened U |
| `gwesp(0.25) + esp(0)` | 2 | flattened U |
| `gwesp(0.75)` (negative control) | 1 | U still marked |

The negative control separates "two components" from "wrong decay", which is
the obvious alternative explanation.

The comparison is not based on AIC but on the shape of the misfit: the
question is not which model fits better on average, but whether the defect
still has that shape. The shape is measured as the ratio between the mean of
the extremes (esp 0 and the 6–9 tail) and the center (esp 1–2); a value of 1
means flat.

### Result

| specification | outcome |
|---|---|
| `gwesp(0.25)` (reference) | converges, U = 16.90 (esp0 8.69; center 0.42; tail 5.51) |
| `gwesp(0.25) + gwesp(1.5)` | does not converge (28 min) |
| `gwesp(0.25) + esp(0)` | does not converge (60 min) |
| `gwesp(0.75)` (negative control) | does not converge (2.4 hours; step below 0.02 for three iterations) |

All three variants, including the negative control, fail on a decade where
the reference specification converges in 52 minutes. The negative control
determines how to read this outcome: `gwesp(0.75)` has a single component,
like the reference, and changes only the decay. Because it fails as well, the
failure of the two-component specifications says nothing about bimodality; it
says that estimation on this decade does not withstand any change to the
specification. The test was inconclusive in either direction.

### What stands and what does not

What stands: the projection result (98.8% against 27.6%), because it is a
*measurement* on the data, not a claim about a model. The U-shaped misfit also
stands, observed with the same shape in two independent decades.

What falls: causal demonstration *by this route*. We cannot say "a model that
allows bimodality fits", because that model cannot be estimated. The failed
attempt remains on record.

Confirmation later came by another route that involves no estimation; see
[Confirmation outside the ERGM](#confirmation-outside-the-ergm).

### An approach that does not work

An apparently obvious option is to give the model cast size as an edge
covariate (`edgecov`), so that `gwesp` only has to explain the residual. This
does not work: if two artists share a release they have an edge by
construction, so the covariate would be non-zero exactly on the edges and zero
elsewhere, and would separate the data perfectly.

---

## Confirmation outside the ERGM

Looking for confirmation within the ERGM was a design error. If the ERGM
cannot describe this network, it cannot serve to show why it cannot describe
it. The claim to be tested is not about a model but about the mechanism that
generates the network, and a mechanism is tested by running it.

### Design

The bipartite artist–release structure is randomized while preserving both
degree distributions exactly (releases per artist and artists per release),
then projected again; this is repeated one hundred times. No social preference
enters: artists are assigned to releases at random. The procedure contains
only the mechanism.

The comparison is one of shape: each model is compared with its *own*
observed distribution, normalized to shares. The sets differ by construction
(the ERGM runs on the 338 gender-determined nodes of the giant component, the
projection on all 515 artists of the decade), so comparing them directly would
be incorrect. An earlier reading did so and was redone.

Before the runs, we verified that the bipartite double swap preserves both
degree distributions exactly, creates no duplicates and actually randomizes
the pairing (99.6% of credits re-paired). If the swap altered the degrees, the
comparison would be worthless. Tests are in `tests/test_scambio_bipartito.py`.

### Result

Ratio of simulated to observed share, 1940s:

| shared partners | estimated ERGM | randomized projection |
|---|---|---|
| 0 | **0.13** | 0.49 |
| 1 | **2.59** | 0.72 |
| 2 | **2.67** | 0.74 |
| 4 | 0.85 | 0.86 |
| 6 | **0.25** | 0.83 |
| 8 | **0.17** | 0.97 |
| 12 | **0.27** | 0.98 |

Mean log₂ deviation, replicated on three independent sets:

| set | observed edges | randomized edges | \|log₂\| deviation |
|---|---|---|---|
| 1940s, ERGM | 1,932 | 1,749 | 1.799 |
| 1940s, projection | 3,016 | 4,465 | 0.297 |
| 1950s, projection | 21,990 | 43,690 | 0.768 |
| full network, projection | 898,475 | 2,189,834 | 0.322 |

What matters is the shape, not the level. The ERGM swings by a factor of
twenty, between 0.13 and 2.67; this is the U. The randomized projection is
monotone and flat in all three sets: `0.49 → 0.72 → 0.80 → 0.86 → 0.96` in
the 1940s, with no reversal.

This is achieved by a model with no estimated parameters, which outperforms by
a factor of six an ERGM with six parameters fitted to the data.

The bimodal shape of the shared-partner distribution is therefore produced by
the bipartite projection mechanism, not by a process of triadic closure. The U
is a property of the model, not of the data.

Status: demonstrated. There are no estimated parameters and no inferential
assumptions: a known process was run and the shape it produces was examined.

### A second, unanticipated result

The randomization systematically produces more edges than observed: 1.5 times
as many in the 1940s, 2.0 in the 1950s and 2.4 on the full network.

This means that Italian musicians collaborate repeatedly with the same people
far more than chance would produce: the same pairs recur across different
releases and therefore generate fewer *distinct* edges. Randomization
disperses them.

This is a substantive result, not a methodological one, and it splits the
phenomenon into two parts that should be kept separate:

* the mechanism explains the *shape* of the shared-partner distribution;
* the social process explains its *concentration*.

### What remains unexplained

At esp = 0 the randomized projection gives 0.49: it produces only half the
observed share of isolated edges. This is much better than the ERGM (0.13),
but not perfect. The mechanism does not account for all of the data, and the
text must say so.

---

## After the exclusion of groups (25 September)

Phase 4f was rerun on the individuals-only network (D16), with a new rule:
after two failures on networks of increasing size the queue stops, because
every remaining decade is larger than both. In the first run the queue had
been stopped by hand for the same reason.

| decade | nodes | edges | outcome |
|---|---|---|---|
| 1930 | 139 | 463 | converged, 19 min |
| 1940 | 303 | 1,650 | converged, 41 min |
| **1950** | 1,326 | **13,919** | converged, **2.9 hours** (previously failed) |
| 2020 | 10,778 | 30,629 | failed: step below 0.02 for three iterations |
| 1960 | 4,330 | 41,413 | failed: same; queue closed |

The estimability threshold rises from "between 1,932 and 15,177 edges" to
"between 13,919 and 30,629". This is consistent with the diagnosis: a group
and its members form a clique by construction, that is, mechanical triangles,
and removing groups makes the network less hostile to `gwesp`.

The 1950 decade adds three findings.

1. No gender homophily when controlling for closure: `gender.F` +0.058
   (*p* 0.56), `gender.M` +0.032 (*p* 0.13). This confirms, by a route
   independent of the permutation test, the absence of homophily at the start
   of the series.
2. The U recurs in a third decade: observed/simulated at esp 0 is 8.9; the
   center is 0.26–0.38; the tail is above 1.6 from 11 shared partners upward.
3. The comparison with the randomized projection is less clear-cut: a
   deviation of 1.015 for the ERGM against 0.720 for the projection, 1.4
   times better; in the 1940s, on the network without groups, 12 times better
   (2.779 against 0.236). The projection wins in both cases, but by very
   different margins; the paper reports the range, not the best case.

Not rerun: the four attempts on the full network (Phase 4b) and the
bimodality check (Phase 4h). These are negative results, and without groups
the decade with 41,413 edges already fails, so the full network (586,040
edges) will necessarily fail. The paper states this in Appendix A.

---

## Conclusion

The ERGM cannot be estimated on this network beyond ~2,000 edges (with
groups; without groups the threshold rises to 13,919–30,629, see above). Nine
estimations failed: four parametrizations on the full network (three MCMLE and
one stochastic approximation, with false convergence), two decades (1950,
2020) and three variants on the 1940 decade (two two-component specifications
and the negative control).

The reason, however, is not size as such, and this is the result: on a
network obtained by bipartite projection, a triadic closure term largely
measures cast size rather than a social process. This is no longer an
interpretation: a null model with no parameters reproduces the shape of the
shared-partner distribution six times better than the estimated ERGM, and
without producing the U. This applies to any co-authorship network, which
accounts for half of the literature on collaboration and homophily.

It also justifies, after the fact, the choice to compute rather than
estimate. If the dependence the ERGM was meant to absorb is largely
mechanical, then the exact logit and the permutation test, which hold the
structure fixed by construction instead of modeling it, are not a fallback;
they are the correct choice.
