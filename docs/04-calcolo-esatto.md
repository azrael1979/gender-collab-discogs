# The exact computation

> The figures in this document refer to the network with groups as nodes, on
> which the methods were developed and verified. The current values, without
> groups (D16), are in [`06-risultati.md`](06-risultati.md); the methods and the
> checks do not change.

## What "exact" means, and what it does not

The word qualifies the computation, not the inference. The distinction matters
and has to be made before the numbers, not after.

The following are exact, in the sense that they contain neither sampling nor
simulation error:

* the maximum-likelihood estimate of the dyadic logit, obtained by passing
  over all 1,619,630,155 dyads rather than a sample;
* the mean and variance of the permutation null distribution, obtained in
  closed form rather than from a thousand Monte Carlo replicates;
* betweenness, computed over all 79,013 sources.

The following are not exact, and no computation could make them so:

* the standard errors of the logit. They come from the observed information
  of a model that assumes independence between dyads, and that assumption is
  structurally false; [Phase 4g](05-ergm.md#diagnosis) measures this. The
  point estimates have no sampling error; the standard errors remain
  optimistic.

This is why the article's claim rests on the permutation test, which does not
depend on any independence assumption: the labels are permuted with the
network held fixed, so triadic closure, the degree distribution and every other
structural property remain identical by construction.

Which permutation is used matters as much as the fact of permuting. Holding the
network fixed is not enough: uniform permutation gives every node the same
probability of receiving the F label regardless of its degree, and women have
fewer ties. The article's reference is permutation within degree strata
(Section D); the uniform permutation remains as an exact computation, but it
answers a different question.

---

## A. The logit over all dyads

### The problem

A logistic regression on 1.6 billion observations does not fit in memory: the
design matrix alone would be 1.6·10⁹ × 7 in double precision, that is, 90 GB.

### The solution

The matrix does not need to be held. A Newton step requires only two aggregate
quantities, the observed information `X'WX` (a 7×7 matrix) and the gradient
`X'(y−p)` (a vector of length 7), and both are sums over dyads. The dyads are
traversed in blocks of rows; the quantities are accumulated and each block is
discarded.

Memory use is constant, about 2 GB. A complete pass over the dyads takes
five to six minutes; a Newton iteration with line search takes two passes,
about fourteen minutes (logs of 23 September).

### Line search

The logistic likelihood is concave, so it has a unique maximum. It does not
follow that a full Newton step moves closer to it: starting far away, the
first version worsened the log-likelihood from −4.7 to −27.3 million.

Each iteration therefore makes two passes: one for the gradient and the
information at the current point, and one to evaluate the likelihood at six
fractions of the step and adopt the best. Near the optimum the full step
always wins, so convergence remains quadratic. Cost: ten passes in total.

### Verification

Exactness is measured, not asserted. On a 900-node network, small enough for
all 404,550 dyads to fit in memory, the block-wise estimates are compared with
`statsmodels`:

```
    termine     statsmodels      blocchi    diff in SE
 intercetta     -5.98875223  -5.98873703   3.7e-04
     same_F      1.04606598   1.04606198   9.8e-05
     same_M      0.31997631   0.31997369   1.1e-04
 same_genre      1.49308611   1.49308420   8.1e-05
sum_lognrel      0.39473209   0.39473005   2.7e-04

log-likelihood: -43,178.4153 in both
```

The largest difference is less than a thousandth of a standard error. It is
not zero because the Newton stops when the log-likelihood improves by less
than 10⁻³ (error E8). That criterion was designed for the whole network, where
a sum of 1.6 billion terms has a numerical floor, and on a small network it
stops the estimate at differences of 10⁻⁵ in the coefficients. A first version
of this document reported a difference of 1.19·10⁻⁹, measured *before* E8
changed the stopping criterion; the test, still using the absolute threshold
of 10⁻⁷, had been failing since then without anyone rerunning it. The
threshold is now in standard-error units, the only scale on which a numerical
difference has a meaning.

The test data are generated from known coefficients, and the method recovers
them. The test is in `tests/test_logit_esatto.py`.

### Result

Over all 1,619,630,155 dyads of the network of artists with a determined
gender:

| term | coefficient | std. error | 95% CI | odds ratio |
|---|---|---|---|---|
| intercept | −14.01783 | 0.00598 | — | — |
| `same_F` | +0.34796 | 0.01310 | [0.3223 – 0.3736] | 1.416 |
| `same_M` | +0.20920 | 0.00363 | [0.2021 – 0.2163] | 1.233 |
| `same_mixed` | +0.53341 | 0.05671 | [0.4223 – 0.6446] | 1.705 |
| `same_genre` | +1.66704 | 0.00290 | [1.6614 – 1.6727] | 5.296 |
| `same_cohort` | +1.19208 | 0.00289 | [1.1864 – 1.1978] | 3.294 |
| `sum_lognrel` | +0.74138 | 0.00056 | — | 2.099 |

Log-likelihood: −3,601,952.06.

The intervals for `same_F` and `same_M` do not overlap.

---

## B. The permutation in closed form

### The problem

The QAP test permutes the node labels with the network held fixed and checks
where the observed value falls. A thousand permutations give an *estimate* of
the null distribution, with its own Monte Carlo error.

### The solution

The mean and variance can be written in closed form. Let `X` be the number of
edges with both endpoints in category *c*, given *m* edges, *n* nodes and
*n_c* nodes in that category:

    E[X] = m · p₂        with   p₂ = n_c(n_c−1) / (n(n−1))

The variance requires the probability that *two* edges are both internal, and
this depends on how many distinct nodes they involve: three if they share an
endpoint, four if they are disjoint.

    E[X²] = E[X] + A·p₃ + D·p₄

where `A` is the number of ordered pairs of adjacent edges, that is,
`Σᵢ dᵢ(dᵢ−1)` over the degrees, and `D = m(m−1) − A` the number of disjoint
pairs; `p₃ = p₂·(n_c−2)/(n−2)` and `p₄ = p₃·(n_c−3)/(n−3)`.

The computation is instantaneous, since it is a sum over the degrees.

### Verification

The closed form is compared with 200,000 Monte Carlo permutations on a network
with deliberately Pareto-distributed degrees. This is the case in which the
variance really depends on the structure, and therefore the case in which a
wrong formula would show.

```
  cat   oss   attesi_esatti  attesi_MC  sd_esatta   sd_MC   sd ratio
    F   267        245.17     245.15      39.47     39.56      0.998
    M  2652       2615.47    2615.45     130.29    130.31      1.000
mixed     4          6.63       6.64       3.70      3.71      0.997
```

The difference in the means is within 1.3 Monte Carlo errors; the standard
deviations agree within 0.3%. The test is in
`tests/test_permutazione_esatta.py`.

### Result on the whole network

56,915 nodes, 521,438 edges:

| | nodes | observed edges | expected | exact sd | ratio | *z* |
|---|---|---|---|---|---|---|
| F | 6,931 | 6,329 | 7,731.90 | 418.20 | 0.819 | −3.35 |
| M | 49,111 | 420,181 | 388,244.70 | 3,064.90 | 1.082 | +10.42 |
| mixed | 873 | 323 | 122.54 | 22.27 | 2.636 | +9.00 |

---

## C. What approximation cost

The comparison between the two versions is the real product of the exercise,
because it shows which approximations were harmless and which were not. This
could not have been predicted.

| approximation | did it cost? | magnitude |
|---|---|---|
| QAP with 1,000 permutations | no | differences below 0.4%; it was already exact |
| betweenness on 400 sources | yes, moderately | coefficient 7%, *p* from 0.21 to 0.14 |
| case-control logit | yes, substantially | F/M gap compressed by 40% (91% after D16); `same_F` underestimated by up to 0.17 in the 2020s |
| intercept correction | it was wrong | sign reversed, 12.9 units |

Two of the four distorted the results, and not in the same direction. The
case-control logit attenuated the F/M gap, which is the effect of interest;
sampled betweenness pushed toward significance a female marginality effect
that does not exist (−0.252 with *p* 0.14 instead of −0.236 with *p* 0.21). A
first draft of this document, and of the article, said "always in the
direction of attenuation"; that was true only of the former. The third case
was a genuine error, found only because the exact computation served as a
check on the approximate one.

---

## D. A null that respects activity (Phase 4j)

### The problem

The permutation in Section B is exact, but its null is blind to activity:
every artist has the same probability of carrying the F label. In the 1950s to
1970s women have between 0.65 and 0.70 times the mean degree. The uniform null
therefore expects woman–woman ties that women with so few ties had no
opportunity to form, and it reads a scarcity of ties as distance between
women.

The symptom was already in the data. The Phase 3 mixing matrix, which uses a
degree-preserving null, gives 1.54 for woman–woman ties on the whole network;
uniform permutation on the same network gives 0.82. The data are the same and
the signs are opposite.

### The solution

The labels are permuted within degree strata: artists with the same number of
ties, with adjacent strata merged until each has at least 30 nodes. Each
gender thus keeps its own degree distribution, and the network stays fixed.
With strata the closed form no longer holds, so the mean and standard
deviation come from 2,000 permutations per decade (1,000 on the whole
network). Newman's ratio under the configuration model is computed alongside
and gives the same values to within a few hundredths.

### Verification

The positive control, in `tests/test_permutazione_per_grado.py`, is a network
with no homophily at all, in which the rare category sits on low-degree nodes
(0.65 of the mean degree, like women in the early decades). The uniform null
sees a spurious deficit, 0.405; the stratified null gives 0.943 (*z* −1.5).
The test also checks that the permutation never moves labels across strata.

As a consistency check, under the uniform null Phase 4j reproduces the ratios
of Phase 4e with a maximum difference of 1.1·10⁻¹⁶.

### Result

| decade | mean F degree / mean degree | F uniform | F by degree | *z* | M by degree |
|---|---|---|---|---|---|
| 1950 | 0.65 | 0.479 | 1.125 | 1.3 | 1.003 |
| 1960 | 0.68 | 0.499 | 1.074 | 1.7 | 1.000 |
| 1970 | 0.70 | 0.606 | 1.178 | 3.7 | 1.006 |
| 1980 | 0.83 | 0.900 | 1.289 | 5.9 | 1.007 |
| 1990 | 0.89 | 1.236 | 1.561 | 13.3 | 1.011 |
| 2000 | 0.85 | 1.224 | 1.710 | 19.3 | 1.007 |
| 2010 | 0.83 | 1.168 | 1.669 | 17.9 | 1.009 |
| 2020 | 1.00 | 1.664 | 1.703 | 15.0 | 1.010 |
| whole network | 0.74 | 0.819 | 1.436 | 26.9 | 1.008 |

The deficit of the early decades disappears. Among equally active artists,
women in the 1950s and 1960s formed ties with one another neither less nor
more often than chance would predict. The excess appears in the 1970s, grows
until the 2000s and from then on stays around 1.7. The jump in the 2020s under
the uniform null was also partly the same artifact in reverse: in that decade
the mean degree of women reaches that of men (0.997).

There is no reversal of sign. There is an emergence, from zero to about 70%
above chance. The by-decade logit, which controls for activity through
releases, already showed this: `same_F` between +0.047 and +0.071 up to the
1970s, never significant.

---

## E. What remains beyond computation

Only the ERGM, and not for lack of effort. Its likelihood contains a
normalizing constant that is a sum over *all possible graphs* on 56,915 nodes:
2^1,619,630,155 terms. The problem is not that it would take long; it is
mathematically intractable. That intractability is what makes MCMC necessary,
and therefore what makes it possible for MCMC to fail. The record is in
[`05-ergm.md`](05-ergm.md).
