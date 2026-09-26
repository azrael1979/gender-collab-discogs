# Project history

## The brief

To study homophily in collaborations among Italian musicians along two axes,
gender and predominant musical genre, using local data only. Five questions:
the share of women by musical genre and decade; whether gender homophily varies
with musical genre; whether women occupy marginal positions (the "Smurfette"
question); the probability of collaboration at equal activity and cohort; and
differences by credit role.

Constraints set at the outset and never violated: read-only access to the
source databases, with new material written only under `analysis/`;
idempotence and checkpoints; no external infrastructure; external sources that
cannot be reached are degraded gracefully and the degradation is documented,
instead of blocking the pipeline.

After the first exploration the scope was narrowed to Discogs alone, on
explicit instruction; iTunes was dropped.

## The five phases and their complications

### 1. Extraction and population

The first obstacle was the read-only constraint: PostgreSQL with
`default_transaction_read_only = on` also forbids temporary tables, which are
the natural way of passing lists of identifiers between queries. The
extraction was rewritten so that it creates no server-side object and sends
the lists back as `int[]` literals.

The second was performance: the cluster runs on a spinning disk but is
configured with `random_page_cost = 1.1`, a value meant for SSDs. The planner
chose index scans and the extraction proceeded at 5 MB/s. This was solved with
session-level GUC settings and a single sequential aggregate pass.

Italian nationality is not a field in the data; it is inferred from the share
of releases with `country = 'Italy'`. Because this is a heuristic, it was
validated against Wikidata `P27` (citizenship) on 4,663 verifiable artists:
94.5% are Italian citizens, and precision rises monotonically with the
threshold (95.7% at 0.60, 96.8% at 0.70, 97.4% at 0.80).

Final population: 100,201 artists.

### 2. Gender, which no source records

Neither database has a gender field. Inference proceeds as a cascade, and the
order matters:

1. Wikidata `P21`, linked through `P1953` (the Discogs identifier), hence by
   exact match and never by name;
2. name dictionaries, consulting the Italian prior before the global one. This
   is not a detail: Andrea, Simone, Nicola, Daniele, Michele and Gabriele are
   male names in Italian and female names in dictionaries dominated by
   English-language data. The reverse order would have introduced a
   systematic error, unbalanced by gender;
3. group composition via `group_member`, which produces the `mixed` category.

Result: 71.2% determined (60,671 M, 9,703 F, 997 mixed, 28,830 unknown), with a
female share of 13.8% among the determined cases, a ratio of 6.25 to 1.

### 3. The network and the weighting of credits

On explicit instruction, track credits are fundamental and must carry more
weight; release credits with specified tracks are comparable; "umbrella"
credits, with no track, must carry less. Hence the weighting formula with three
levels of specificity (track 1.0; main release 0.7; umbrella 0.3).

The Discogs field `release_artist.tracks` is free text (`A1`, `1 to 3`,
`4, 6, 12`) and is resolved to the actual tracks; anything that cannot be
parsed is downgraded to umbrella rather than forced.

4,169,130 credits, 64.0% of them resolved at track level. Network: 82,595
nodes with edges and 702,613 edges; the giant component holds 95.7%.

### 4. Homophily, and the first solid result

Newman's assortativity is 0.5865 on musical genre and 0.0511 on gender. The
two differ by an order of magnitude, and this is the most solid result of the
whole project: people who make music in Italy cluster by musical genre, not by
sex.

By role the difference is sharp: 0.0235 for creative roles against 0.1175 for
performing roles, a factor of five.

On the Smurfette question there is no positional effect. None of twelve
interactions is significant, and the main effect for women is not significant
on any of the three measures (eigenvector +0.223, p=0.19; coreness +0.039,
p=0.60; betweenness −0.236, p=0.21).

### 5. The ERGM and its four failures

The work stalled here for a long time. The model with a triadic closure term
does not converge on the full network under any of the parameterizations
tried. The full record is in [`05-ergm.md`](05-ergm.md); the outcome is enough
here: the model cannot be estimated, and one apparent convergence was exposed
by the goodness-of-fit checks.

## The five points at which the approach changed

The work did not proceed in a straight line. Three external interventions
redirected it, and each one improved the result. A fourth change came from
within, while rewriting the article.

### First: "I want the full network, not sampled subnetworks"

The earlier version of the article stated that the full network was out of
reach and estimated models on subnetworks drawn by snowball sampling. The
objection was correct and methodologically decisive: for an estimate based on a
snowball sample, one cannot say what it is an estimate of. The sample does not
represent anything definable.

This led to the dyadic logit and QAP on the full network, methods that scale by
construction, and to the definitive abandonment of subnetworks.

### Second: "We need to see how it evolves over time"

This produced the central result of the work. Dating each tie by the year of
the first shared release, instead of by agreement between debut cohorts (a
definition that discarded precisely the intergenerational collaborations),
revealed a series that no aggregate measure had shown.

### Third: "Why not compute on the full network instead of estimating?"

This was the sharpest objection, and there was no good answer to it. Many
quantities had been estimated by sampling even though they could be computed
exactly: the logit on three million dyads instead of all 1,619,630,155; QAP on
a thousand permutations instead of the closed-form moments; betweenness from
400 sources instead of all 79,013.

Removing these approximations had three effects, documented in
[`04-calcolo-esatto.md`](04-calcolo-esatto.md) and [`03-errori.md`](03-errori.md):

* two of the four approximations biased the results: the case-control logit
  attenuated the gap between women and men, and sampled betweenness
  exaggerated a marginality effect that does not exist;
* the comparison between exact and approximate results revealed a sign error
  in the case-control correction, which could not have been detected any other
  way;
* the gap between female and male homophily turned out to be almost twice as
  large as it had appeared.

### Fourth: "The paper is too long"

While the article was being cut to 8,000 words, two numbers for the same
network ended up a few lines apart: the degree-preserving mixing matrix gave
1.54 for woman–woman ties, the uniform permutation 0.82. The text explained the
second with a reason the data did not support. The cause was the null model:
the uniform permutation does not take into account that women have fewer ties,
and reads the scarcity of ties as distance between women.

Phase 4j recomputes the series by permuting labels among artists with the same
number of ties. The deficit of the early decades disappears, and with it the
sign reversal. What remains is an emergence, from no homophily in the 1950s and
1960s to about 70% above chance from 2000 onward. See E13 in
[`03-errori.md`](03-errori.md) and D12 in [`02-decisioni.md`](02-decisioni.md).

### Fifth: "Isn't counting groups and their members double counting?"

It is. A group and its members appear on the same releases: counting both
duplicated ties and created group–member ties, which are not collaboration
choices, and the groups, almost all of them male, lowered the female share.
Since 24 September the unit of analysis has been the person (D16): 87,229
individual artists out of 100,201 entries. The pipeline was rerun in full.

The emergence holds; the magnitudes fall (the recent plateau goes from about
1.7 to about 1.55 times chance). There were two unforeseen effects. The 1950s
become estimable with an ERGM, which confirms the initial absence of homophily
while also controlling for closure. The cost of the approximations also becomes
more serious: sampled betweenness would have produced a significant Smurfette
effect, and the case-control logit would have almost erased the gap between
women and men.

## Current status

The thesis has changed twice. It is no longer "minority homophily" as a stable
state, and no longer a sign reversal, which was an artifact of the null model.
What remains is a dated emergence: among equally active artists, Italian women
musicians did not form ties with one another more than chance until the 1960s;
from the 1970s they did, and from 2000 at about 1.55 times chance, while their
share does not grow but falls from 15.5% to 9.6% before rising slightly. Men
remain at chance in every decade.

Two unplanned methodological contributions have been added to this. The first:
on a network obtained by bipartite projection, a triadic closure term largely
measures the size of casts rather than a social process; this was measured
edge by edge and confirmed by running the mechanism. The second: in a field
where the minority is also less active, a null model blind to activity
manufactures results, and it manufactures them in the direction that makes an
article more interesting.

The article was rewritten around this thesis (24 September) and cut from 11,247
to 7,719 words of main text. The results by pair type and musical genre
(Phase 4k) were then integrated, bringing it back to 8,541 words, and it was
then tightened to 7,936 by moving computational details to the appendices and
removing repetition; the long version is kept locally in `paper/versioni/`.
After groups were excluded (D16) and the gender validation was completed (25
September: 94.6% agreement on the M/F labels), the main text stands at 7,989
words. The manuscript is not in the public repository (see D15 in
[`02-decisioni.md`](02-decisioni.md)). What remains are the editorial elements:
see
[`06-risultati.md`](06-risultati.md#open-items).
