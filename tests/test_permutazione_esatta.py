"""Verifica: media e sd in forma chiusa devono coincidere con 200.000
permutazioni Monte Carlo (entro l'errore Monte Carlo)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, "src")
import phase4e_esatto as P

rng = np.random.default_rng(11)
n, m = 1200, 5000
g = rng.choice(["M","F","mixed"], n, p=[.72,.23,.05])
# rete con gradi molto eterogenei: e' il caso in cui la varianza DIPENDE
# dalla struttura, quindi quello in cui una formula sbagliata si vede
w = rng.pareto(1.3, n) + 1
p = w / w.sum()
ii = rng.choice(n, m, p=p); jj = rng.choice(n, m, p=p)
ok = ii != jj; ii, jj = ii[ok], jj[ok]
e = set(map(tuple, np.sort(np.column_stack([ii,jj]), axis=1)))
ii = np.array([a for a,b in e]); jj = np.array([b for a,b in e]); m = len(ii)
gradi = np.bincount(np.concatenate([ii,jj]), minlength=n)
print(f"prova: {n} nodi, {m} archi, grado max {gradi.max()}, "
      f"coppie adiacenti {int((gradi*(gradi-1)).sum()):,}")

class L:
    def info(self,*a,**k): pass
esatto = P.permutazione_esatta(n, {"gender": g}, ii, jj, gradi, L())

B = 200_000
mc = {c: np.empty(B) for c in ("F","M","mixed")}
for b in range(B):
    gg = rng.permutation(g)
    a, bb = gg[ii], gg[jj]
    for c in mc:
        mc[c][b] = ((a==c)&(bb==c)).sum()

righe = []
for _, r in esatto.iterrows():
    c = r.categoria; d = mc[c]
    righe.append({"cat": c, "oss": r.archi_osservati,
      "attesi_esatti": r.attesi, "attesi_MC": d.mean(),
      "sd_esatta": r.sd_esatta, "sd_MC": d.std(),
      "err_media_sd": abs(r.attesi-d.mean())/(d.std()/np.sqrt(B)),
      "rapp_sd": r.sd_esatta/d.std()})
t = pd.DataFrame(righe)
print(t.to_string(index=False, float_format=lambda x: f"{x: .4f}"))
print(f"\nscarto della media in unita' di errore Monte Carlo (|z|<3 atteso): "
      f"{t.err_media_sd.abs().max():.2f}")
print(f"rapporto sd esatta/MC (1.000 atteso): {t.rapp_sd.min():.4f}-{t.rapp_sd.max():.4f}")
assert t.err_media_sd.abs().max() < 4, "MEDIA SBAGLIATA"
assert (t.rapp_sd - 1).abs().max() < 0.02, "VARIANZA SBAGLIATA"
print("\nOK: forma chiusa confermata da 200.000 permutazioni")
