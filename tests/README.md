# Verifiche

Le affermazioni di esattezza della Fase 4e non sono argomentative: sono
verificate contro un riferimento indipendente, su casi abbastanza piccoli da
rendere il riferimento calcolabile.

| file | che cosa verifica | contro che cosa |
|---|---|---|
| `test_logit_esatto.py` | il Newton a blocchi su tutte le diadi | `statsmodels` sull'insieme completo delle diadi di una rete da 900 nodi — coefficienti ed errori standard devono coincidere entro 1e-7 |
| `test_permutazione_esatta.py` | media e varianza in forma chiusa della permutazione | 200.000 permutazioni Monte Carlo su una rete con gradi pareto (il caso in cui la varianza dipende davvero dalla struttura) |
| `test_correzione_casocontrollo.py` | il segno della correzione di Prentice-Pyke | una popolazione simulata a verita' nota |

Si eseguono senza argomenti:

```bash
python3 tests/test_logit_esatto.py
python3 tests/test_permutazione_esatta.py
python3 tests/test_correzione_casocontrollo.py
```

Il primo richiede che `src/` sia raggiungibile dalla radice del progetto.
