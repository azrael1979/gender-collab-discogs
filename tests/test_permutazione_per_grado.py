"""Verifica della permutazione entro strati di grado (Fase 4j).

Due controlli.

1. La permutazione non esce dagli strati: in ogni strato il numero di
   etichette di ciascun genere resta identico.
2. Controllo positivo sul caso che la Fase 4j deve smascherare. Si costruisce
   una rete in cui le etichette dipendono SOLO dal grado — la categoria rara
   sta sui nodi a basso grado — e l'appaiamento e' casuale, cioe' non c'e'
   alcuna omofilia. Il nullo uniforme deve vedere un deficit spurio (rapporto
   ben sotto 1); il nullo per strati di grado deve dare circa 1.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from phase4j_nullo_grado import strati_di_grado, permuta_negli_strati, confronta

rng = np.random.default_rng(1)

# ---------------------------------------------------------------- 1
gradi = rng.integers(1, 60, size=5000)
strati = strati_di_grado(gradi)
lab = rng.random(5000) < 0.2
for _ in range(20):
    p = permuta_negli_strati(lab, strati, rng)
    for s in np.unique(strati):
        assert p[strati == s].sum() == lab[strati == s].sum()
assert np.all(np.bincount(strati) >= 30)
print("1. conteggi per strato conservati; strati:", strati.max() + 1)

# ---------------------------------------------------------------- 2
n = 6000
peso = rng.pareto(2.2, n) + 1                      # attivita' eterogenea
rara = np.zeros(n, dtype=bool)
rara[np.argsort(peso)[: n // 8]] = True            # la categoria rara ha poca attivita'
rara[rng.choice(n, n // 40, replace=False)] ^= True  # un po' di rumore
m = 60000
pr = peso / peso.sum()
ii = rng.choice(n, m, p=pr)
jj = rng.choice(n, m, p=pr)                        # appaiamento indipendente dal genere
ok = ii != jj
coppie = np.unique(np.sort(np.c_[ii[ok], jj[ok]], axis=1), axis=0)
ii, jj = coppie[:, 0].astype(np.int32), coppie[:, 1].astype(np.int32)
gender = np.where(rara, "F", "M")

r = {d["categoria"]: d for d in confronta(gender, ii, jj, rng, repliche=400)}
F = r["F"]
print(f"2. F: grado medio relativo {F['grado_medio_relativo']:.2f}  "
      f"uniforme {F['rapporto_uniforme']:.3f}  per grado {F['rapporto_grado']:.3f} "
      f"(z {F['z_grado']:+.2f})  configurazione {F['rapporto_configurazione']:.3f}")
assert F["rapporto_uniforme"] < 0.8, "il nullo uniforme dovrebbe vedere il deficit spurio"
assert abs(F["rapporto_grado"] - 1) < 0.1 and abs(F["z_grado"]) < 3, \
    "il nullo per strati di grado non dovrebbe vedere omofilia dove non c'e'"
print("OK")
