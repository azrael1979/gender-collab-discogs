"""Stile grafico condiviso: palette validata per daltonismo, assi discreti.

Slot categoriali in ordine fisso (mai ciclati); rampa sequenziale a una sola
tinta per le magnitudini; coppia divergente blu<->rosso con grigio neutro al
centro per i rapporti osservato/atteso, dove il punto neutro e' 1.
"""
from __future__ import annotations
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap, Normalize
import seaborn as sns

# slot categoriali, ordine fisso
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
       "#008300", "#4a3aa7", "#e34948"]
GENDER_COLOR = {"F": CAT[0], "M": CAT[1], "mixed": CAT[2], "unknown": "#9a9a95"}
GENDER_LABEL = {"F": "donne", "M": "uomini", "mixed": "gruppi misti",
                "unknown": "non determinato"}

SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
       "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
DIV_LO, DIV_MID, DIV_HI = "#0d366b", "#f0efec", "#e34948"

INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8b8a85"
SURFACE = "#fcfcfb"

cmap_seq = LinearSegmentedColormap.from_list("seq_blu", SEQ)
cmap_div = LinearSegmentedColormap.from_list("div_blu_rosso",
                                             [DIV_LO, "#86b6ef", DIV_MID, "#f0a0a0", DIV_HI])


def setup():
    sns.set_theme(style="white", context="paper")
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE, "savefig.dpi": 300,
        "font.size": 9, "axes.titlesize": 11, "axes.labelsize": 9.5,
        "axes.titleweight": "semibold", "axes.titlepad": 10,
        "axes.labelcolor": INK2, "text.color": INK,
        "xtick.color": INK2, "ytick.color": INK2,
        "axes.edgecolor": "#d8d7d2", "axes.linewidth": 0.8,
        "grid.color": "#e8e7e3", "grid.linewidth": 0.6,
        "legend.frameon": False, "legend.fontsize": 8.5,
        "xtick.labelsize": 8.5, "ytick.labelsize": 8.5,
        "lines.linewidth": 2.0, "lines.markersize": 5,
        "figure.constrained_layout.use": True,
    })


def tidy(ax, grid: str = "y"):
    """Assi recessivi: niente cornice, griglia tenue su un solo asse."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#d8d7d2")
    if grid in ("y", "both"):
        ax.yaxis.grid(True, alpha=0.7)
    if grid in ("x", "both"):
        ax.xaxis.grid(True, alpha=0.7)
    ax.set_axisbelow(True)
    return ax


def ratio_scale(M, cap_pct: float = 99.0):
    """Prepara una matrice di rapporti osservato/atteso per la mappa divergente.

    Un rapporto non e' simmetrico in spazio lineare: 2 e 0,5 sono scostamenti
    di pari entita' in direzioni opposte, ma una scala lineare centrata su 1
    darebbe al primo il doppio dello spazio del secondo, e sprecherebbe meta'
    della barra su valori negativi che un rapporto non puo' assumere. Si lavora
    percio' in log2, dove lo zero e' il neutro e la simmetria e' quella giusta.

    Restituisce (valori in log2, norma simmetrica, tick, etichette dei tick).
    """
    L = np.log2(np.where(np.isfinite(M) & (M > 0), M, np.nan))
    lim = np.nanpercentile(np.abs(L), cap_pct)
    lim = float(max(lim, 0.1))
    norm = Normalize(vmin=-lim, vmax=lim)
    cand = np.array([0.25, 0.4, 0.5, 0.67, 0.8, 1.0, 1.25, 1.5, 2.0, 2.5, 4.0])
    keep = cand[np.abs(np.log2(cand)) <= lim * 1.001]
    return L, norm, np.log2(keep), [f"{v:g}×" if v != 1 else "1× (atteso)" for v in keep]


def caption(fig, text: str, size: float = 7.8):
    fig.text(0.0, -0.02, text, ha="left", va="top", fontsize=size,
             color=MUTED, wrap=True)


def decade_axis(ax, floor: int = 1950):
    """Il decennio piu' basso e' un contenitore ('tutto cio' che precede'),
    non un decennio vero: va etichettato come tale per non trarre in inganno."""
    ax.xaxis.set_major_formatter(
        lambda v, _: (f"<{floor}" if int(round(v)) == floor - 10 else f"{int(round(v))}"))
    return ax
