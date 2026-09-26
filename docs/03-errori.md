# Errors found and corrected

All errors are listed, including those that did not change any number. An
error that leaves the results unchanged today may change them later, and
knowing *how* it was found is as useful as knowing that it was corrected.

The errors are ordered by severity, not by date; the number gives the order in
which they were found.

---

## E13. The null for the central claim was blind to activity

*Severity: highest.* It changed the shape of the central result and the title
that summarized it.

*What it was.* The by-decade series ("up to the 1970s women were tied to one
another *less* than chance, from the 1990s *more*: a reversal of sign") rested
on uniform permutation of the labels. That null gives every artist the same
probability of being a woman, whatever their number of ties. In the early
decades women had between 0.65 and 0.70 times the mean degree: the null
expected ties they had no opportunity to form, and the resulting deficit
(0.48–0.61) reflected a scarcity of ties, not distance between women.

*How it came to light.* While rereading the paper to shorten it. Figure 2
(degree-preserving mixing) gave 1.54 for woman–woman ties on the whole network;
the uniform-permutation table gave 0.82. These were two numbers on the same
data with opposite signs, and the text explained the second with a reason
("dominated by the decades in which most ties were formed") that the data did
not support: those very decades had ratios above 1. The by-decade logit, which
controls for activity, already had `same_F` non-significant up to the 1970s.
The signal was there, and it had been read as confirmation rather than as an
objection.

*How it was verified.* Phase 4j: permutation within degree strata, plus a
positive control on a network with no homophily and the same disparity in
activity (the uniform null sees 0.41, the stratified null 0.94). The
prediction was written in the docstring before the run.

*What it changed.* Among equally active artists the F ratio is 1.13 and 1.07
in the 1950s and 1960s (not significant), 1.18 in the 1970s (*z* 3.7), 1.56 in
the 1990s, and ~1.7 from 2000 on. There is no reversal of sign; the pattern is
one of emergence. The jump in the 2020s (1.66 against 1.17 in the preceding
decade) was partly the same artifact in reverse, because in that decade women's
degree reaches men's; under the stratified null it is a plateau. The result
that survives is more solid, and the title "the emergence of…" fits it better
than it fitted the reversal.

*Lesson.* Holding the network fixed is not enough to make a null neutral; what
matters is what is permuted relative to what. In a field where the minority is
also less active, an activity-blind null conflates avoidance with scarcity.

---

## E14. The paper reported sampled betweenness as if it were exact

*Severity: medium.* A wrong coefficient and *p* in a table, and an internal
contradiction.

*What it was.* `paper.py` read the position effects from
`report_numbers.json`, which Phase 7 had written on 21 September, before
Phase 3b switched to exact betweenness. The position table therefore showed
−0.252 (*p* 0.14), while the table "what approximation cost" gave the exact
value as −0.236 (*p* 0.21).

*Correction.* The paper reads the regressions directly from
`position_regressions.parquet`. The sampled value, which can no longer be
reproduced from the data, remains in `paper.py` as a documented constant for
the comparison.

*Principle.* An intermediate file of numbers written by another phase is a
cache, and caches go stale. Every figure should be read from the output of the
phase that computes it.

---

## E15. Internal inconsistencies in the paper, found during the rewrite

*Severity: medium, cumulatively.* None of them changed a result; a referee
would have found all of them.

* "Always in the direction of attenuation": said of two of the four
  approximations, in the paper and in `04-calcolo-esatto.md`. True for the
  case-control logit; false for sampled betweenness, which *exaggerated* a
  nonexistent marginality effect.
* Count of ERGM failures on the full network: "four failures plus a fifth
  with stochastic approximation". There were four in all, and the fourth was
  the stochastic one.
* Wrong internal cross-references: 1.2 → "Section 4.6" (should have been
  4.8); 3.1 and 3.2 → "Section 4.7" (should have been 4.9); 3.4 → "Section
  4.1" (should have been 4.3). The commit message said "21 internal
  cross-references resolved": they existed, but did not point to the right
  place.
* Numbering: two Tables 3, two Tables 5, and no Figure 2 (the mixing figure
  was generated but not included).
* Leftovers of the withdrawn claim: Section 2.2 said ERGMs were used
  "precisely for this reason"; the limitations cited the "post-2000 ERGM
  cohort" and the "matched subnetwork sizes"; the robustness section described
  the goodness of fit of the old subnetwork models ("they reproduce the core
  well"), the opposite of what the decades show; Appendix B stated that Hummel
  termination "brings every model to convergence within a few minutes".
* "0.17 per decade": the case-control discrepancy was an underestimate of
  `same_F` by 0.17 in the 2020s, not a slope.
* "Exact to the fourth decimal place" for the permutation with a thousand
  replicates, two lines below the table that said "within 0.4%".
* "Zero significant interactions out of twelve": the twelve were for
  eigenvector centrality alone. Across the three measures there are 36
  interactions, and one (coreness) is significant at 5%, fewer than chance
  would produce.

---

## E16. A test that had been failing for days, and a figure that depended on it

*Severity: low for the results, high for the method.* No estimate was wrong;
a claim of precision was.

*What it was.* `tests/test_logit_esatto.py` required absolute differences
below 10⁻⁷ between the block-wise Newton and `statsmodels`. After E8 the
Newton also stops when the log-likelihood improves by less than 10⁻³, and on
the test network this halts it at differences of 10⁻⁵ in the coefficients.
The test had been failing since then. Meanwhile `04-calcolo-esatto.md` and the
paper continued to claim agreement "within 10⁻⁹", a value measured before E8.

*How it came to light.* By rerunning all the tests after Phase 4j was added.
A test that nobody reruns verifies nothing.

*Correction.* The threshold is now expressed in standard-error units (largest
observed difference: 3.7·10⁻⁴ standard errors; log-likelihood identical to
the fourth decimal place), and the text was corrected in the document and in
the paper.

---

## E17. A model term that presupposed groups

*Severity: low.* An interruption; no wrong result.

*What it was.* After groups were excluded (D16), Phase 4c failed with
`Singular matrix`: the term `same_mixed` (both nodes are mixed groups) was a
column of zeros. The same term was in the exact logit of Phase 4e, which would
have failed immediately afterwards, or run to no purpose.

*Correction.* The term enters only if the network contains `mixed` nodes
(`termini_di()` in 4e; constant columns dropped in 4c). This was verified with
the existing test, which has mixed nodes, and on simulated data without them,
against `statsmodels` (difference of 10⁻⁵ standard errors). The pipeline loop
was stopped by PID before 4e started.

*Lesson.* A change in the definition of the population has to be followed
through to the model terms, not only to the data.

---

## E18. A cascade level came back into use without a decision

*Severity: low.* 145 labels out of 87,229.

*What it was.* Level 2 of the cascade (Wikidata by name) was empty in the
first run because the Wikidata service was not responding; the README stated
this as a limitation. The names file was downloaded on 21 September, but
Phase 1d had not been rerun. When it was rerun for D16, the level labeled
1,500 artists: almost always as the name-based classification would have, but
135 previously undetermined artists received a label and 10 switched from M to
F or vice versa.

*Why it is recorded.* Two changes in the same rerun confound the before/after
comparison. The effect of this one is negligible compared with that of the
groups, but the paper described three levels, and the README a limitation that
no longer exists. The level is kept: it was part of the design, with its
safeguards against homonyms (the name must be unique in both Wikidata and
Discogs; names with conflicting genders are discarded).

---

## E1. Case-control correction with the sign reversed

*Severity: high.* A published coefficient was wrong.

*What it was.* In the case-control dyadic logit all edges are kept, together
with a fraction *f* of the unconnected dyads, and the intercept has to be
brought back to the population scale. The Prentice–Pyke correction is

    b0_popolazione = b0_campione + log(f)

with `log(f)` negative. The code subtracted instead of adding, which put the
intercept off by `2·log(f)`, about 12.9 units.

*How it came to light.* Not through code review. The exact computation on the
whole network was warm-started from the sample coefficients, and the starting
intercept, −0.615, was incompatible with the observed density of the network
(3.2·10⁻⁴, which is −8.04 on the logit scale). An intercept that high cannot
hold for a network that sparse.

*How it was verified.* Not by argument, but by constructing a simulated
population with known truth (4 million dyads, `b0 = −8`), sampling from it,
and checking which correction recovers it. `b0 + log(f)` gives −7.957;
`b0 − log(f)` gives +4.010. The test is in
`tests/test_correzione_casocontrollo.py`.

*What it changed.* Only the intercept, from −0.615 to −13.478. None of the
slopes changed: the result is invariant to the sampling design, which was
verified both in theory and in the simulation. All published homophily
coefficients remain valid.

*Why it went unnoticed.* Precisely because the slopes are unaffected. The
intercept of a dyadic logit has no substantive interpretation here, so nobody
looked at it.

---

## E2. The case-control logit systematically compressed the effect

*Severity: high.* This was an error of method rather than of code, and it
altered the main result.

*What it was.* Sampling five controls per case produced estimates that differ
from the exact ones by more than their nominal standard error suggested.

| term | sampled | exact | difference |
|---|---|---|---|
| `same_F` | +0.317 | +0.348 | −0.031 (1.7 SE) |
| `same_M` | +0.231 | +0.209 | +0.022 (4.2 SE) |

The gap between female and male homophily went from 0.086 to 0.139: sampling
compressed it by 40%, attenuating precisely the quantity of interest.

On the time series the effect was worse: an underestimate of `same_F` of up to
0.17 in the 2020s, exactly where the curve rises.

*How it came to light.* From the direct comparison with the exact computation,
and by no other route: the sampled estimate was internally consistent, and its
bootstrap intervals flagged nothing.

*What it changed.* The exact curve rises more steeply. The central result is
stronger than it had appeared.

---

## E3. A regex killed a healthy estimation

*Severity: high in terms of time lost.* No wrong result, but fourteen hours of
idle machine time.

*What it was.* The ERGM orchestrator read the optimizer step from lines of the
form `1 Optimizing with step length 0.5774.` using the regex `([0-9.]+)`,
which also captures the period that ends the sentence. `float("0.5774.")`
raises `ValueError`; the exception escaped the reading loop and killed the
orchestrator, and R then died of `SIGPIPE`.

*Aggravating factor.* The step was 0.5774, meaning the estimation was going
well. The monitoring interrupted exactly what it was meant to protect.

*Correction.* The regex became `step length\s+([0-9]*\.?[0-9]+)`, and a
general principle was adopted: the generator that reads R's output never
raises; every error is logged and swallowed. Monitoring is an aid and must not
be able to interrupt what it monitors.

*Consequence.* Eight failure modes were reviewed, and six pre-launch tests
were introduced.

---

## E4. The monitoring depended on what it monitored

*Severity: medium.* It allowed E3 to remain invisible for hours.

*What it was.* All the checks (elapsed time, memory, progress) sat inside the
loop that read R's output. But the step is printed at the *end* of an
iteration: when iterations lengthen without limit (29 minutes, then 62, then
125, then over 243), the output is silent for hours and no check can fire.

*Correction.* A `Sorvegliante` on an independent thread which, every sixty
seconds, checks time, memory and silence, whatever R is doing.

*Verification.* Tested by killing a silent process and by tolerating one that
had already died.

*Consequence.* This mechanism is what later shut down the 1950s estimation
correctly, abandoned after two hours of silence.

---

## E5. Sampled betweenness was not neutral

*Severity: medium.* It changed a coefficient and a significance level.

*What it was.* Betweenness was approximated from 400 sampled sources, with
the justification, written in the code, that the exact version "is not
feasible". That was false: `igraph` computes Brandes over all 79,013 sources
in 56 minutes.

| | sampled (k=400) | exact |
|---|---|---|
| main effect F | −0.252 (p = 0.14) | −0.236 (p = 0.21) |
| R² | 0.539 | 0.546 |

*Why the discrepancy is not minor.* Sampling *k* sources estimates high values
well and low values poorly, and it is the low values that answer the question
about women's marginality. The approximation moved the result toward an
apparently stronger effect.

*Conclusion unchanged:* there is no positional Smurfette effect. It now rests
on an exact computation.

---

## E6. Role classifier too narrow

*Severity: medium.* It distorted RQ5.

*What it was.* 1.1 million credits ended up in "other", and among them were
genuine instruments: *Tenor Saxophone*, *Double Bass*, *Viola*, *Voice*. The
distinction between creative and performing roles, which is the core of RQ5,
was therefore built on a classification that discarded a quarter of the data.

*Correction.* A classifier based on families of keywords instead of a list.
"Other" fell to 210,705.

---

## E7. Machine saturation

*Severity: medium.* No wrong result, but the machine's other services were
starved.

*What it was.* `MPLE.samplesize` was set to 20,000,000. The pseudo-likelihood
design matrix takes about one gigabyte per four million dyads, and with
`PSOCK` it is copied into every worker. With six chains this meant eight R
processes, about 60 GB, a full swap and a load of 34.

*Correction.* `mple_samplesize` reduced to 1,000,000 (2.8 GB peak), the MCMC
sample from 10,000 to 3,000, parallelism from 6 to 2. Result: three processes,
4.1 GB.

*Principle adopted.* Parameters are tuned for memory, not for speed. Time is
not a constraint; coexistence with the other services is.

---

## E8. Unreachable convergence tolerance

*Severity: low.* No wrong result; seven wasted hours avoided.

*What it was.* The exact Newton used `TOLLERANZA = 1e-9` on the step. But the
log-likelihood is a sum of 1.6 billion double-precision floating-point terms,
and accumulated rounding error sets a floor around 10⁻⁷. The estimate had
converged (identical log-likelihood and coefficients stable to the fourth
decimal place for three iterations), but the criterion could never be
satisfied, and the program would have kept running to no purpose until the
limit of 40 iterations.

*Correction.* Tolerance set to 10⁻⁶ (three orders of magnitude below the
smallest standard error, which is ~10⁻³), plus a second, independent criterion
on the improvement in the likelihood, plus a checkpoint at every iteration: a
Newton iteration (a pass for the derivatives plus a pass for the line search)
takes about fourteen minutes and should not have to restart from scratch.

---

## E9. Newton without line search

*Severity: low.* Found immediately; it never entered the results.

*What it was.* The first version of the exact Newton took the full step.
Starting far from the optimum, the log-likelihood worsened from −4.7 to −27.3
million between the first and second iterations. Concavity guarantees a
unique maximum, not that a full step moves closer to it.

*Correction.* Line search over a grid of step fractions, all evaluated in the
same pass over the dyads. It costs six dot products on the same matrix, which
is almost nothing compared with building it.

---

## E10. `pkill -f` killing its own shell

*Severity: low, but recurring.* It happened twice.

*What it was.* `pkill -f "phase4e_esatto"`, launched from a shell whose
command line contains that same string (because the command includes a
here-document that names the file), kills itself before reaching the target.
Exit code 144, target still alive.

*Correction.* The bracket trick (`phase4e_esatt[o]`) works only if the string
does not appear *elsewhere* in the command line. The reliable solution is to
separate the operations and kill by PID.

---

## E11. Minor environment errors

Collected for completeness; none of them affected the results.

* `groupby.nth` raising `KeyError` on pandas 1.5 → replaced with `cumcount()`.
* Backslash inside an f-string, not allowed in Python 3.9 → captions in double
  quotes.
* WDQS responding with 429, 502, 504 and truncated JSON → recursive splitting
  of batches, with 429s counted separately from genuine failures.
* `nodematch("musical_genre")` collinear with `edges` within single-genre
  subnetworks → term included only when the attribute varies.
* Phase 4f tables never written, because the loop was interrupted and the
  collection step runs at the end → produced by hand; `data/` is not under
  version control, so without this they would have been lost.

---

## E12. A wait loop that waited for itself

*Severity: low.* A variant of E10, with a different target.

*What it was.* A process waiting for a phase to finish, written as

    until ! pgrep -f "phase4i_proiezione_null[a]"; do sleep 60; done
    tail -4 logs/phase4i_proiezione_nulla.log

The bracket trick keeps `pgrep` from matching itself, but only for that
occurrence. The next line names `logs/phase4i_proiezione_nulla.log`, which
matches the pattern; the waiting process found itself and waited
indefinitely.

*How it came to light.* The phase had finished nine hours earlier, but the
waiting process was still alive and the machine load was 0.07, meaning nothing
was being computed.

*Correction.* The pattern must be absent from the *entire* command line, not
only from the `pgrep` invocation. In practice: wait by PID, or refer to the
log file indirectly.

*Cost.* No wrong result; a nine-hour delay in reading a result that was
already available.
