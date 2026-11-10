"""Estilo centralizado de las figuras del paper (perfil por defecto; la revista se decide en la compuerta 1).

Para añadir el perfil de una revista: definir una entrada en PROFILES y llamar a
`apply("nombre")` (o exportar FIG_PROFILE=nombre). Todo tamaño sale de aquí.
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Paleta Okabe–Ito (daltonismo-segura)
OI = {"black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
      "yellow": "#F0E442", "blue": "#0072B2", "vermilion": "#D55E00", "purple": "#CC79A7"}
GREY = "#6b6b6b"
LIGHT = "#d9d9d9"
CAT = [OI["blue"], OI["vermilion"], OI["green"], OI["orange"], OI["sky"], OI["purple"], OI["black"]]

PROFILES = {
    "default": dict(col1=3.35, col2=7.0, font=8.0, small=7.0, line=1.0, marker=3.5),
    # "journal-x": dict(col1=..., col2=..., font=..., small=..., line=..., marker=...),
}
_active = dict(PROFILES["default"])


def W(cols: int = 2) -> float:
    return _active["col1"] if cols == 1 else _active["col2"]


def apply(name: str | None = None) -> dict:
    name = name or os.environ.get("FIG_PROFILE", "default")
    p = PROFILES[name]
    _active.clear(); _active.update(p)
    plt.rcParams.update({
        "font.family": "STIXGeneral", "mathtext.fontset": "stix",
        "font.size": p["font"], "axes.labelsize": p["font"], "axes.titlesize": p["font"],
        "xtick.labelsize": p["small"], "ytick.labelsize": p["small"], "legend.fontsize": p["small"],
        "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
        "xtick.major.size": 2.5, "ytick.major.size": 2.5,
        "lines.linewidth": p["line"], "lines.markersize": p["marker"],
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "axes.axisbelow": True, "grid.color": LIGHT, "grid.linewidth": 0.4,
        "axes.prop_cycle": matplotlib.cycler(color=CAT),
        "legend.frameon": False, "legend.handlelength": 1.6, "legend.borderaxespad": 0.2,
        "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
        "savefig.bbox": "tight", "savefig.pad_inches": 0.02, "figure.dpi": 150,
        "axes.titleweight": "normal",
    })
    return p


def panel(ax, letter: str):
    """Rótulo de panel (a), (b)… en la esquina superior izquierda, fuera del área de datos."""
    ax.text(0.0, 1.03, f"({letter})", transform=ax.transAxes, fontsize=_active["font"] + 0.5,
            fontweight="bold", ha="left", va="bottom")
