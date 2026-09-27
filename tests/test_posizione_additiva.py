"""Fase 3f: il coefficiente calcolato per Frisch-Waugh-Lovell nel test di
permutazione coincide con quello OLS del modello additivo; il test rileva un
effetto vero e non ne inventa uno assente; e il coefficiente del modello con
interazioni e' l'effetto nella categoria di riferimento, non la media (E20)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import phase3f_posizione_additiva as f3

rng = np.random.default_rng(1)
n = 6000
generi = np.array(["Altro", "Pop", "Rock", "Jazz"])
d = pd.DataFrame({
    "genere": rng.choice(generi, n, p=[0.05, 0.4, 0.4, 0.15]),
    "coorte": rng.choice(["1970", "1990", "2010"], n),
    "log_nrel": rng.gamma(2.0, 1.0, n),
})
d["gender"] = pd.Categorical(np.where(rng.random(n) < 0.2, "F", "M"), categories=["M", "F"])
F = (d.gender == "F").to_numpy(dtype=float)
# effetto F: nullo in "Altro" (categoria di riferimento), -0.4 negli altri generi
eff = np.where(d.genere == "Altro", 0.0, -0.4)
base = 0.8 * d.log_nrel + (d.genere == "Rock") * 0.3
d["y_eff"] = base + eff * F + rng.normal(0, 1, n)
d["y_nullo"] = base + rng.normal(0, 1, n)

add = smf.ols("y_eff ~ C(gender) + C(genere) + log_nrel + C(coorte)", data=d).fit()
fwl, p_eff = f3.permutazione(d, d.y_eff.to_numpy(), np.random.default_rng(2))
assert abs(fwl - add.params["C(gender)[T.F]"]) < 1e-9, (fwl, add.params["C(gender)[T.F]"])
print(f"FWL = OLS additivo: {fwl:.6f}")

assert p_eff < 0.01, p_eff
_, p_nul = f3.permutazione(d, d.y_nullo.to_numpy(), np.random.default_rng(3))
assert p_nul > 0.01, p_nul
print(f"permutazione: p con effetto {p_eff:.4f}, senza effetto {p_nul:.3f}")

inter = smf.ols("y_eff ~ C(gender) * C(genere) + log_nrel + C(coorte)", data=d).fit()
rif = inter.params["C(gender)[T.F]"]
assert abs(rif) < 0.25 and add.params["C(gender)[T.F]"] < -0.3, (rif, add.params)
print(f"interazioni: coefficiente F = {rif:+.3f} (solo 'Altro'); additivo = "
      f"{add.params['C(gender)[T.F]']:+.3f} (media)")
print("OK")
