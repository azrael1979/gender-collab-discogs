# Tests

The exactness claims of Phases 4e, 4i and 4j do not rest on argument: they are
checked against an independent reference, on cases small enough for the
reference to be computable.

| file | what it checks | against what |
|---|---|---|
| `test_logit_esatto.py` | the block Newton method over all dyads | `statsmodels` on the complete set of dyads of a 900-node network; coefficients and standard errors must agree to within one thousandth of a standard error, the log-likelihood to within 1e-3 |
| `test_permutazione_esatta.py` | closed-form mean and variance of the permutation | 200,000 Monte Carlo permutations on a network with Pareto-distributed degrees (the case in which the variance really depends on the structure) |
| `test_correzione_casocontrollo.py` | the sign of the Prentice-Pyke correction | a simulated population with known ground truth |
| `test_scambio_bipartito.py` | the double swap of Phase 4i | preserves both degree distributions exactly, creates no duplicates, actually re-pairs the credits |
| `test_permutazione_per_grado.py` | the permutation within degree strata of Phase 4j | never leaves the strata; on a network with no homophily and a low-degree minority, the uniform null shows a spurious deficit (~0.4) and the stratified null does not (~0.94) |

They run without arguments:

```bash
python3 tests/test_logit_esatto.py
python3 tests/test_permutazione_esatta.py
python3 tests/test_correzione_casocontrollo.py
python3 tests/test_scambio_bipartito.py
python3 tests/test_permutazione_per_grado.py
```

The first requires `src/` to be reachable from the project root.
