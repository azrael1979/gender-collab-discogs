"""Verifica: il Newton a blocchi deve coincidere con statsmodels su una rete
piccola dove TUTTE le diadi stanno in memoria."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src")
from scipy.sparse import csr_matrix
import statsmodels.api as sm
import phase4e_esatto as P

rng = np.random.default_rng(7)
n = 900
g = rng.choice(["M","F","mixed"], n, p=[.75,.2,.05])
gen = rng.integers(0, 12, n).astype(np.int32)
coh = rng.integers(0, 8, n).astype(np.int32)
lnr = rng.normal(2, 1, n)

# rete con omofilia vera, cosi' i coefficienti non sono nulli
I, J = np.triu_indices(n, 1)
eta = -6 + 1.0*((g[I]=="F")&(g[J]=="F")) + 0.3*((g[I]=="M")&(g[J]=="M")) \
      + 1.5*(gen[I]==gen[J]) + 0.5*(coh[I]==coh[J]) + 0.4*(lnr[I]+lnr[J])
y = (rng.random(len(I)) < 1/(1+np.exp(-eta))).astype(np.int8)
ii, jj = I[y==1], J[y==1]
A = csr_matrix((np.ones(len(ii), np.int8), (ii, jj)), shape=(n,n)); A = A + A.T
print(f"rete di prova: {n} nodi, {len(ii)} archi, {n*(n-1)//2} diadi")

attrs = {"gender": g, "genre": gen, "cohort": coh, "lnr": lnr}

# --- riferimento: statsmodels su TUTTE le diadi -------------------------
X = pd.DataFrame({
 "same_F": ((g[I]=="F")&(g[J]=="F")).astype(float),
 "same_M": ((g[I]=="M")&(g[J]=="M")).astype(float),
 "same_mixed": ((g[I]=="mixed")&(g[J]=="mixed")).astype(float),
 "same_genre": (gen[I]==gen[J]).astype(float),
 "same_cohort": (coh[I]==coh[J]).astype(float),
 "sum_lognrel": lnr[I]+lnr[J]})
rif = sm.Logit(y.astype(float), sm.add_constant(X)).fit(disp=0)

import logging; log = logging.getLogger("t"); log.addHandler(logging.NullHandler())
class L:
    def info(self,*a,**k): pass
    def warning(self,*a,**k): pass
P.BLOCCO_RIGHE = 100
mio = P.logit_esatto(n, attrs, A, L())

cmp = pd.DataFrame({"termine": P.TERMINI,
                    "statsmodels": rif.params.values, "blocchi": mio.coef.values,
                    "se_sm": rif.bse.values, "se_blocchi": mio.se.values})
cmp["diff"] = (cmp.statsmodels - cmp.blocchi).abs()
cmp["diff_se"] = (cmp.se_sm - cmp.se_blocchi).abs()
print(cmp.to_string(index=False, float_format=lambda x: f"{x: .8f}"))
print(f"\nmax scarto coefficienti: {cmp['diff'].max():.2e}")
print(f"max scarto errori std : {cmp['diff_se'].max():.2e}")
print(f"logL statsmodels {rif.llf:,.4f}   blocchi {mio.logL.iloc[0]:,.4f}")
assert cmp["diff"].max() < 1e-7 and cmp["diff_se"].max() < 1e-7, "NON COINCIDONO"
print("\nOK: identico a statsmodels sul completo")
