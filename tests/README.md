# Verifiche

Le affermazioni di esattezza delle Fasi 4e, 4i e 4j non sono argomentative: sono
verificate contro un riferimento indipendente, su casi abbastanza piccoli da
rendere il riferimento calcolabile.

| file | che cosa verifica | contro che cosa |
|---|---|---|
| `test_logit_esatto.py` | il Newton a blocchi su tutte le diadi | `statsmodels` sull'insieme completo delle diadi di una rete da 900 nodi — coefficienti ed errori standard devono coincidere entro un millesimo di errore standard, la log-verosimiglianza entro 1e-3 |
| `test_permutazione_esatta.py` | media e varianza in forma chiusa della permutazione | 200.000 permutazioni Monte Carlo su una rete con gradi pareto (il caso in cui la varianza dipende davvero dalla struttura) |
| `test_correzione_casocontrollo.py` | il segno della correzione di Prentice-Pyke | una popolazione simulata a verita' nota |
| `test_scambio_bipartito.py` | il doppio scambio della Fase 4i | conserva esattamente entrambe le distribuzioni di grado, non crea doppioni, riappaia davvero i crediti |
| `test_permutazione_per_grado.py` | la permutazione entro strati di grado della Fase 4j | non esce dagli strati; su una rete **senza omofilia** con la minoranza a basso grado il nullo uniforme vede un deficit spurio (~0,4) e quello per strati no (~0,94) |

Si eseguono senza argomenti:

```bash
python3 tests/test_logit_esatto.py
python3 tests/test_permutazione_esatta.py
python3 tests/test_correzione_casocontrollo.py
python3 tests/test_scambio_bipartito.py
python3 tests/test_permutazione_per_grado.py
```

Il primo richiede che `src/` sia raggiungibile dalla radice del progetto.
