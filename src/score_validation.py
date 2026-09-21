"""Valutazione dell'inferenza di genere sul campione annotato a mano.

Uso:
    python3 src/score_validation.py [percorso_csv]

Il file atteso e' `data/validation_sample.csv` con la colonna `human_gender`
compilata (M / F / mixed / unknown). Le righe lasciate vuote sono ignorate e
conteggiate a parte: la copertura dell'annotazione e' essa stessa un dato.

Produce: precisione, richiamo e F1 per classe e per livello della cascata,
matrice di confusione, e una stima dell'errore per fascia di confidenza — che
e' cio' che serve per capire se le soglie del config sono tarate bene.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common
from common import ROOT

LABELS = ["M", "F", "mixed", "unknown"]


def prf(y_true: pd.Series, y_pred: pd.Series) -> pd.DataFrame:
    rows = []
    for c in LABELS:
        tp = int(((y_pred == c) & (y_true == c)).sum())
        fp = int(((y_pred == c) & (y_true != c)).sum())
        fn = int(((y_pred != c) & (y_true == c)).sum())
        prec = tp / (tp + fp) if tp + fp else np.nan
        rec = tp / (tp + fn) if tp + fn else np.nan
        f1 = 2 * prec * rec / (prec + rec) if prec and rec and (prec + rec) else np.nan
        rows.append({"classe": c, "supporto": int((y_true == c).sum()),
                     "veri_positivi": tp, "falsi_positivi": fp, "falsi_negativi": fn,
                     "precisione": prec, "richiamo": rec, "f1": f1})
    df = pd.DataFrame(rows)
    sup = df.supporto.sum()
    if sup:
        df.loc[len(df)] = {
            "classe": "media ponderata", "supporto": sup,
            "veri_positivi": df.veri_positivi.sum(),
            "falsi_positivi": df.falsi_positivi.sum(),
            "falsi_negativi": df.falsi_negativi.sum(),
            "precisione": np.average(df.precisione.fillna(0), weights=df.supporto),
            "richiamo": np.average(df.richiamo.fillna(0), weights=df.supporto),
            "f1": np.average(df.f1.fillna(0), weights=df.supporto)}
    return df


def main(path: str | None = None):
    cfg = common.load_config()
    log = common.setup_logging("score_validation", cfg)
    p = Path(path) if path else ROOT / "data" / "validation_sample.csv"
    if not p.exists():
        log.error(f"file non trovato: {p}")
        raise SystemExit(1)
    d = pd.read_csv(p)
    if "human_gender" not in d.columns:
        log.error("manca la colonna `human_gender`")
        raise SystemExit(1)
    d["human_gender"] = d.human_gender.astype(str).str.strip()
    ann = d[d.human_gender.isin(LABELS)].copy()
    log.info(f"righe totali {len(d)}, annotate {len(ann)} ({len(ann)/max(len(d),1):.1%})")
    if ann.empty:
        log.warning("nessuna riga annotata: compilare `human_gender` "
                    "con M / F / mixed / unknown e rilanciare")
        raise SystemExit(0)

    acc = float((ann.gender == ann.human_gender).mean())
    log.info(f"accuratezza complessiva: {acc:.3f}")

    overall = prf(ann.human_gender, ann.gender)
    common.save_table(overall, "t2_validazione_prf",
                      f"Precisione, richiamo e F1 dell'inferenza di genere "
                      f"sul campione annotato (n={len(ann)}, accuratezza {acc:.1%})")
    log.info("\n" + overall.round(3).to_string(index=False))

    cm = pd.crosstab(ann.human_gender, ann.gender, rownames=["reale"],
                     colnames=["inferito"], dropna=False).reindex(
        index=LABELS, columns=LABELS, fill_value=0)
    common.save_table(cm.reset_index(), "t2_validazione_confusione",
                      "Matrice di confusione dell'inferenza di genere")
    log.info("\n" + cm.to_string())

    bysrc = ann.groupby("label_source").apply(
        lambda g: pd.Series({"n": len(g),
                             "accuratezza": float((g.gender == g.human_gender).mean()),
                             "confidenza_media": float(g.confidence.mean())})
    ).reset_index().sort_values("n", ascending=False)
    common.save_table(bysrc, "t2_validazione_per_fonte",
                      "Accuratezza dell'inferenza per livello della cascata: "
                      "dice quali livelli meritano la confidenza che il config "
                      "assegna loro")
    log.info("\n" + bysrc.round(3).to_string(index=False))

    if "confidence_bin" in ann:
        byconf = ann.groupby("confidence_bin", observed=True).apply(
            lambda g: pd.Series({"n": len(g),
                                 "accuratezza": float((g.gender == g.human_gender).mean())})
        ).reset_index()
        common.save_table(byconf, "t2_validazione_per_confidenza",
                          "Accuratezza per fascia di confidenza dichiarata: "
                          "verifica che la confidenza sia calibrata")
        log.info("\n" + byconf.round(3).to_string(index=False))

    common.write_json({"n_annotate": int(len(ann)), "n_totali": int(len(d)),
                       "accuratezza": acc}, "validation_score.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
