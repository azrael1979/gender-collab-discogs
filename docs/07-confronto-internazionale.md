# Feasibility of the international comparison

Study of 25 September 2026, to choose on the basis of the numbers which
countries to compare with Italy in a second paper. Script:
`src/fattibilita_paesi.py`; data in `data/fattibilita/`. Two sequential
read-only passes over the database; everything else runs locally.

Validity check of the script: on Italy it reproduces the pipeline, with
100,202 entries against 100,201 and a precision of 94.5% for the nationality
criterion.

## Figures

Same nationality criterion as for Italy (≥ 2 releases in the country, ≥ 3 in
total, share ≥ 0.50), with groups excluded as in D16.

| country | individual artists | 1950s debuts | nationality precision (P27) | Wikidata gender | real name |
|---|---|---|---|---|---|
| Italy | 87,230 | 1,553 | 94.5% | 6.0% | 16.7% |
| Spain | 51,879 | 848 | 91.4% | 4.7% | 22.1% |
| France | 123,884 | 3,877 | 86.4% | 6.8% | 13.0% |
| Germany | 190,347 | 2,753 | **79.0%** | 6.8% | 17.4% |
| GDR | 3,382 | 339 | 94.2% | 17.9% | 12.0% |
| Sweden | 43,328 | 916 | 96.2% | 7.5% | 21.3% |
| Norway | 26,414 | 249 | 97.4% | 11.1% | 13.9% |
| Denmark | 20,950 | 451 | 95.3% | 9.4% | 14.0% |
| Finland | 35,642 | 317 | 98.0% | 9.4% | 19.3% |
| Netherlands | 58,080 | 755 | 89.5% | 6.0% | 20.9% |
| Portugal | 12,419 | 182 | 88.6% | 5.2% | 16.4% |
| Greece | 23,127 | 350 | 95.2% | 5.4% | 18.0% |
| Japan | 98,661 | 725 | 95.0% | 6.0% | 20.1% |
| Brazil | 40,114 | 614 | 97.8% | 3.9% | 16.6% |
| United Kingdom | 184,552 | 2,347 | **81.6%** | 4.3% | 18.9% |
| United States | 640,197 | 20,638 | 90.5% | 4.3% | 13.5% |

Debuts by decade: `data/fattibilita/fattibilita_paesi_decenni.csv`.

## Interpretation

The nationality criterion holds where the market coincides with the country
and weakens where the market is defined by language. In Germany the errors
are mostly Austrian (469) and Swiss (241) artists; in France, Belgian and
Swiss; in the United Kingdom, American, Australian and Irish. This is a
substantive limitation, not a data limitation: in those cases the natural unit
may be the linguistic field (Germany + Austria + German-speaking Switzerland)
rather than the state. This must be decided before pre-registration.

Two coding pitfalls were found and corrected (to keep in mind for future
work): Wikidata records citizenship as "Kingdom of Denmark" (Q756617),
"Kingdom of the Netherlands" (Q29999) and, for the past, "United Kingdom of
Great Britain and Ireland" (Q174193). With only the codes of the constituent
countries, precision came out as zero.

The GDR is small: 3,382 artists, almost all debuting between 1950 and 1989.
This is enough for the permutation test by decade, but woman–woman ties per
decade will number only a few hundred. The comparison with West Germany will
therefore have low power, and the design must state this.

Gender inference is the bottleneck everywhere. Wikidata gender covers 4–11% of
artists (18% in the GDR), as in Italy. The name-based cascade will do most of
the work, and each country requires its own name dictionary and its own
validation sample. Japan remains the hardest case because of romanized names.

Computation. The exact logit grows with the square of the number of active
artists: Germany would require about ten times Italy's computing time (one
machine-day), the United States about a hundred times more. The latter is out
of reach without sampling, that is, without giving up what distinguishes this
method.

## Proposal

First comparison: Italy, Spain, France and Sweden (or the Nordic countries
together, all above 95% precision), plus Germany and the GDR if the
unit-of-analysis question for linguistic fields is resolved. The United
States (computation) and the United Kingdom (nationality criterion at 82%)
are excluded for now; Japan only with a dedicated gender validation.
