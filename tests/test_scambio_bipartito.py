"""Il doppio scambio bipartito deve conservare ESATTAMENTE entrambe le
distribuzioni di grado, e deve davvero randomizzare l'appaiamento.

Due proprieta' distinte, ed entrambe servono: se i gradi cambiano il confronto
con l'osservato non vale nulla; se l'appaiamento non cambia, la "randomizzazione"
restituisce la rete di partenza e il test e' vuoto.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import phase4i_proiezione_nulla as P


def _finto(rng, n_art=200, n_rel=400, maxc=8):
    """Un bipartito con cast di dimensione variabile, senza doppioni."""
    a, r = [], []
    for ri in range(n_rel):
        k = int(rng.integers(2, maxc + 1))
        for ai in rng.choice(n_art, k, replace=False):
            a.append(int(ai)); r.append(ri)
    return np.array(a, np.int32), np.array(r, np.int32)


def test_gradi_conservati_e_appaiamento_cambiato():
    rng = np.random.default_rng(42)
    a, r = _finto(rng)
    ga0 = np.bincount(a, minlength=a.max() + 1)
    gr0 = np.bincount(r, minlength=r.max() + 1)

    aa, rr, ok = P.scambia(a, r, rng, 10 * len(a))
    assert ok > 0, "nessuno scambio riuscito: il test sarebbe vuoto"

    ga1 = np.bincount(aa, minlength=len(ga0))
    gr1 = np.bincount(rr, minlength=len(gr0))
    assert np.array_equal(ga0, ga1), "gradi degli ARTISTI cambiati"
    assert np.array_equal(gr0, gr1), "gradi delle RELEASE cambiati"

    # nessun doppione: un artista non puo' comparire due volte sulla stessa
    # release, altrimenti il cast si accorcerebbe alla proiezione
    coppie = set(zip(aa.tolist(), rr.tolist()))
    assert len(coppie) == len(aa), "creato un doppione (artista, release)"

    # e l'appaiamento deve essere davvero cambiato
    diversi = (r != rr).mean()
    assert diversi > 0.3, f"appaiamento quasi invariato ({diversi:.1%})"
    return ga0, gr0, ok, diversi


if __name__ == "__main__":
    ga, gr, ok, diversi = test_gradi_conservati_e_appaiamento_cambiato()
    print(f"gradi artisti conservati : sì ({len(ga)} artisti)")
    print(f"gradi release conservati : sì ({len(gr)} release)")
    print(f"scambi riusciti          : {ok:,}")
    print(f"crediti riappaiati       : {diversi:.1%}")
    print("\nOK: conserva i gradi e randomizza")
