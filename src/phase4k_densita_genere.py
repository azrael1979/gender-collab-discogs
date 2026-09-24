"""FASE 4k — quanto e' probabile collaborare, per tipo di coppia, decennio e genere.

La domanda
----------
Per decennio e per genere musicale: quanto e' probabile che due donne
collaborino, rispetto a due uomini o a un uomo e una donna?

Le fasi precedenti la sfiorano senza rispondere. La 4e e la 4j danno i
rapporti osservato/atteso per decennio, ma su tutti i generi insieme; la Fase 3
li da' per genere, ma su tutto il periodo; nessuna confronta direttamente i tre
tipi di coppia.

Il disegno
----------
Una cella e' un decennio (anno della prima release condivisa, come nella 4d) e
un genere musicale (quello prevalente dell'artista). Nella cella stanno gli
artisti di quel genere, con genere sessuale determinato (M o F), che hanno
almeno un legame nato in quel decennio con un altro artista dello stesso
genere; e quei legami. I legami fra generi musicali diversi restano fuori: se
ne riporta la quota, perche' non e' trascurabile.

Per ciascun tipo di coppia — FF, MM, MF — la **densita'** e' la probabilita'
che una coppia di quel tipo sia legata:

    d_FF = legami FF / C(n_F, 2)
    d_MM = legami MM / C(n_M, 2)
    d_MF = legami MF / (n_F * n_M)

I rapporti d_FF/d_MF e d_MM/d_MF dicono quante volte e' piu' probabile che
collaborino due donne, o due uomini, rispetto a una coppia mista. Non
dipendono dalla composizione: una densita' e' gia' divisa per le coppie
possibili.

Non tengono pero' conto dell'attivita': se le donne hanno meno legami, tutte le
densita' che le coinvolgono scendono insieme. Per questo accanto si riporta,
per ogni tipo di coppia, il rapporto osservato/atteso sotto la permutazione
entro strati di grado della Fase 4j, calcolata dentro la cella.

Incertezza
----------
Gli intervalli dei rapporti fra densita' sono quelli di Poisson sul logaritmo,
sqrt(1/L_a + 1/L_b), e assumono indipendenza fra legami: sono ottimistici,
come gli errori standard del logit. L'inferenza che non assume indipendenza e'
lo z della permutazione per strati. Le celle con meno di MIN_DONNE donne o
meno di MIN_LEGAMI_FF legami donna-donna sono marcate come poco affidabili, non
tolte.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import Timer
from phase4j_nullo_grado import strati_di_grado, permuta_negli_strati

REPLICHE = 500
MIN_DONNE = 30
MIN_LEGAMI_FF = 10
MIN_ARTISTI = 100
TUTTI = "(all genres)"


def cella(g: pd.DataFrame, gen: pd.Series, rng) -> dict | None:
    """Densita' e nullo per strati su un insieme di legami gia' filtrato."""
    nodi = np.unique(np.concatenate([g.u.values, g.v.values]))
    if len(nodi) < MIN_ARTISTI:
        return None
    pos = pd.Series(np.arange(len(nodi)), index=nodi)
    ii, jj = pos[g.u].values, pos[g.v].values
    F = (gen.reindex(nodi) == "F").values
    nF, nM = int(F.sum()), int((~F).sum())
    if nF < 2 or nM < 2:
        return None

    def conta(lab):
        a, b = lab[ii], lab[jj]
        return int((a & b).sum()), int((~a & ~b).sum()), int((a ^ b).sum())

    ff, mm, mf = conta(F)
    dFF = ff / (nF * (nF - 1) / 2)
    dMM = mm / (nM * (nM - 1) / 2)
    dMF = mf / (nF * nM)

    def rapp(x, y, lx, ly):
        if lx == 0 or ly == 0:
            return x / y if y else np.nan, np.nan, np.nan
        r, se = x / y, np.sqrt(1 / lx + 1 / ly)
        return r, r * np.exp(-1.96 * se), r * np.exp(1.96 * se)

    r_ff, r_ff_lo, r_ff_hi = rapp(dFF, dMF, ff, mf)
    r_mm, r_mm_lo, r_mm_hi = rapp(dMM, dMF, mm, mf)

    gradi = np.bincount(np.concatenate([ii, jj]), minlength=len(nodi))
    strati = strati_di_grado(gradi)
    sim = np.empty((REPLICHE, 3))
    for r in range(REPLICHE):
        sim[r] = conta(permuta_negli_strati(F, strati, rng))
    mu, sd = sim.mean(0), sim.std(0, ddof=1)
    oss = np.array([ff, mm, mf])
    with np.errstate(divide="ignore", invalid="ignore"):
        oe = oss / mu
        z = (oss - mu) / sd

    return {
        "artisti": len(nodi), "donne": nF, "uomini": nM,
        "quota_donne": nF / len(nodi), "legami": len(g),
        "legami_FF": ff, "legami_MM": mm, "legami_MF": mf,
        "grado_medio_relativo_F": float(gradi[F].mean() / gradi.mean()),
        "densita_FF": dFF, "densita_MM": dMM, "densita_MF": dMF,
        "FF_su_MF": r_ff, "FF_su_MF_lo": r_ff_lo, "FF_su_MF_hi": r_ff_hi,
        "MM_su_MF": r_mm, "MM_su_MF_lo": r_mm_lo, "MM_su_MF_hi": r_mm_hi,
        "FF_su_MM": dFF / dMM if dMM else np.nan,
        "oe_FF_grado": oe[0], "z_FF_grado": z[0],
        "oe_MM_grado": oe[1], "z_MM_grado": z[1],
        "oe_MF_grado": oe[2], "z_MF_grado": z[2],
        "affidabile": bool(nF >= MIN_DONNE and ff >= MIN_LEGAMI_FF),
    }


def main(force: bool = False):
    cfg = common.load_config()
    log = common.setup_logging("phase4k_densita_genere", cfg)
    if common.exists("densita_genere.parquet") and not force:
        log.info("Fase 4k gia' completata, salto")
        return
    rng = np.random.default_rng(cfg["project"]["seed"])

    pop = common.load("population_gender.parquet").set_index("artist_id")
    pop = pop[pop.gender.isin(["M", "F"])]
    gen, mus = pop.gender, pop.musical_genre.fillna("Unknown")

    E = common.load("edges_datati.parquet")
    E = E[E.u.isin(pop.index) & E.v.isin(pop.index) & (E.decennio >= 1950)].copy()
    E["gu"], E["gv"] = mus.reindex(E.u).values, mus.reindex(E.v).values
    generi = [x for x in mus.value_counts().index if x != "Unknown"]

    righe = []
    for dec, g in E.groupby("decennio"):
        stesso = g[g.gu == g.gv]
        quota_intra = len(g[(g.gu == g.gv) & (g.gu != "Unknown")]) / len(g)
        with Timer(f"{int(dec)}s", log):
            r = cella(g, gen, rng)
            if r:
                righe.append({"decennio": int(dec), "genere_musicale": TUTTI,
                              "quota_legami_intra_genere": quota_intra, **r})
            for gm in generi:
                r = cella(stesso[stesso.gu == gm], gen, rng)
                if r:
                    righe.append({"decennio": int(dec), "genere_musicale": gm,
                                  "quota_legami_intra_genere": quota_intra, **r})

    out = pd.DataFrame(righe)
    log.info("\n" + out[["decennio", "genere_musicale", "donne", "legami_FF",
                         "FF_su_MF", "MM_su_MF", "oe_FF_grado", "z_FF_grado",
                         "affidabile"]].round(2).to_string(index=False))
    common.save(out, "densita_genere.parquet")
    common.save_table(out, "t6_densita_genere",
                      "Probabilita' di legame per tipo di coppia, decennio e genere "
                      "musicale, con il nullo per strati di grado")


if __name__ == "__main__":
    main(force="--force" in sys.argv)
