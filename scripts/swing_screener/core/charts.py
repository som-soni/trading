"""Chart styling shared by every report.

One palette, defined once. The categorical slots are validated for
colour-vision deficiency rather than chosen by eye (blue/orange clear the CVD
separation, normal-vision and contrast checks on both surfaces); the diverging
pair is used only where the data has a sign. Grid and axes are recessive
hairlines, marks are thin, and nothing is dashed — dashing reads as
"threshold" when it is only a gridline.
"""

import matplotlib

matplotlib.use("Agg")  # no display on a headless/background run
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402,F401
from pathlib import Path  # noqa: E402

# --- palette: validated categorical slots + diverging pair + chrome ink ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_STRATEGY = "#2a78d6"   # categorical slot 1 (blue)
SERIES_BENCHMARK = "#eb6834"  # categorical slot 2 (orange)
POS = "#2a78d6"               # diverging: cool arm
NEG = "#d03b3b"               # diverging: warm arm
NEUTRAL = "#f0efec"           # diverging midpoint


def _style() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.titleweight": "regular",
        "axes.titlecolor": INK,
        "axes.labelcolor": INK_2,
        "axes.edgecolor": AXIS,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.linestyle": "-",   # never dashed: dashing reads as "threshold"
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "lines.linewidth": 2.0,
        "figure.dpi": 140,
    })


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return path
