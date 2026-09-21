"""Utilita' per comporre il report: lettura difensiva dei risultati e
formattazione dei numeri in italiano."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import common
from common import ROOT

FIGDIR = ROOT / "report" / "figures"
TABDIR = ROOT / "report" / "tables"


def have(name: str) -> bool:
    return common.exists(name)


def get(name: str) -> pd.DataFrame | None:
    return common.load(name) if common.exists(name) else None


def n(x, dec: int = 0) -> str:
    """Numero all'italiana: punto per le migliaia, virgola per i decimali."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n.d."
    s = f"{x:,.{dec}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pct(x, dec: int = 1) -> str:
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "n.d."
    return n(x * 100, dec) + "%"


def img(stem: str, caption: str, width: str = "100%") -> str:
    p = FIGDIR / f"{stem}.png"
    if not p.exists():
        return (f"> *Figura «{stem}» non disponibile: i dati necessari non sono "
                f"stati prodotti in questa esecuzione.*\n")
    return (f'<figure>\n<img src="figures/{stem}.png" alt="{stem}" '
            f'style="width:{width}" />\n<figcaption>\n\n{caption}\n\n'
            f"</figcaption>\n</figure>\n")


def table(stem: str, caption: str, max_rows: int = 30,
          cols: list[str] | None = None, float_dec: int = 3,
          rename: dict | None = None) -> str:
    p = TABDIR / f"{stem}.csv"
    if not p.exists():
        return f"> *Tabella «{stem}» non disponibile.*\n"
    df = pd.read_csv(p)
    if cols:
        df = df[[c for c in cols if c in df.columns]]
    if rename:
        df = df.rename(columns=rename)
    truncated = len(df) > max_rows
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: n(v, float_dec))
        elif pd.api.types.is_integer_dtype(d[c]):
            d[c] = d[c].map(lambda v: n(v, 0))
    # `disable_numparse` e' indispensabile: senza, tabulate ri-parsa le stringhe
    # gia' formattate all'italiana ("69.320") come numeri decimali e le rende
    # "69.32", cambiando gli ordini di grandezza sotto gli occhi del lettore.
    out = d.to_markdown(index=False, disable_numparse=True)
    note = (f"\n\n*Mostrate le prime {max_rows} righe di {n(len(df))}; "
            f"la tabella completa e' in `tables/{stem}.csv` e `tables/{stem}.tex`.*"
            if truncated else
            f"\n\n*Dati completi in `tables/{stem}.csv` e `tables/{stem}.tex`.*")
    return f"{out}\n\n**Tabella — {caption}**{note}\n"


def sci(x, dec: int = 1) -> str:
    """Notazione scientifica leggibile: 7,3 x 10^-9 invece di 0,000000007."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)) or x == 0:
        return "n.d."
    import math
    e = int(math.floor(math.log10(abs(x))))
    m = x / (10 ** e)
    return f"{n(m, dec)} × 10<sup>{e}</sup>"


def val(df, query: str, col: str, default=np.nan):
    """Estrae un singolo valore da un DataFrame con una query, senza esplodere."""
    if df is None or df.empty:
        return default
    try:
        s = df.query(query)[col]
        return s.iloc[0] if len(s) else default
    except Exception:
        return default
