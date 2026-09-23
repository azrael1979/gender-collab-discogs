"""La correzione caso-controllo ha un segno, e va verificato su una
popolazione in cui la verita' e' nota.

Serviva: una prima versione della Fase 4c sottraeva log(f) invece di
sommarlo. L'errore era invisibile perche' le pendenze non ne risentono — ed
e' proprio per questo che merita un test.
"""
import numpy as np
import statsmodels.api as sm


def test_segno_della_correzione():
    rng = np.random.default_rng(3)
    N = 4_000_000
    x = rng.normal(0, 1, N)
    b0_vero, b1_vero = -8.0, 0.9
    p = 1 / (1 + np.exp(-(b0_vero + b1_vero * x)))
    y = (rng.random(N) < p).astype(int)

    casi = np.where(y == 1)[0]
    noncasi = np.where(y == 0)[0]
    ctrl = rng.choice(noncasi, size=5 * len(casi), replace=False)
    f = len(ctrl) / len(noncasi)
    idx = np.concatenate([casi, ctrl])
    m = sm.Logit(y[idx], sm.add_constant(x[idx])).fit(disp=0)

    # Prentice-Pyke: tenuti tutti i casi e una frazione f dei controlli,
    # l'intercetta di popolazione e' quella del campione PIU' log(f).
    assert abs((m.params[0] + np.log(f)) - b0_vero) < 0.1
    assert abs((m.params[0] - np.log(f)) - b0_vero) > 10     # il segno opposto
    # la pendenza e' invariante al disegno: e' il motivo per cui l'errore
    # sull'intercetta non tocca nessuna conclusione sostanziale
    assert abs(m.params[1] - b1_vero) < 0.1


if __name__ == "__main__":
    test_segno_della_correzione()
    print("OK: b0_pop = b0_camp + log(f)")
