"""FoodMatrix shared chart style — import this instead of setting colours by hand.

Why this file exists: five people plotting independently produces a deck that
reads as five projects. One palette, defined once and imported everywhere, is the
single highest-leverage thing we can do for the Presentation bucket.

Usage
-----
    import sys; sys.path.append("scripts")      # from a notebook
    from plotting import apply_style, COMMODITY, RISK, ACCENT, MUTED, save

    apply_style()
    fig, ax = plt.subplots()
    ax.plot(x, y, color=COMMODITY["Wheat"])
    save(fig, "wheat_exposure")                 # -> visualizations/wheat_exposure.png

Rules the palette encodes, so nobody has to remember them
--------------------------------------------------------
* **Red means risk, always.** `RISK` is a single-hue red ramp, light to dark,
  monotonic in lightness — so it still reads correctly in greyscale and in print.
  Never use red for a non-risk series.
* **Commodities have fixed colours.** Wheat is blue, Rice orange, Maize aqua —
  everywhere, in every chart, so a reader learns them once. Assigned in fixed
  order, never cycled.
* **Emphasis over category.** When one country is the point, colour it `ACCENT`
  and put every other series in `MUTED`. This is the most under-used chart form
  and usually the honest answer to "make this clearer".
* **One axis, never two.** Two measures on different scales are two charts.

Colour choices were validated for colour-vision deficiency: the three commodity
hues clear the all-pairs CVD and normal-vision separation floors on both light
and dark surfaces. Rice-orange against Maize-aqua is the tightest pair, so both
carry direct labels rather than relying on a legend.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
VIZ = ROOT / "visualizations"

# --- surfaces and ink -------------------------------------------------------

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

# --- commodities: fixed, never reassigned -----------------------------------

COMMODITY = {
    "Wheat": "#2a78d6",   # blue
    "Rice": "#eb6834",    # orange
    "Maize": "#1baf7a",   # aqua
}

# --- risk: single-hue sequential, light -> dark ------------------------------
# Monotonic in relative luminance (0.82 -> 0.08), so it survives greyscale.

RISK = ["#fde5df", "#fbc4b5", "#f79c85", "#ef7256", "#e34948", "#c22f34", "#97202a"]

#: Four ordered risk bands, matching the Low / Moderate / High / Very High
#: labels the scoring script already emits. Same ramp, four steps.
RISK_LEVEL = {
    "Low": "#fbc4b5",
    "Moderate": "#f79c85",
    "High": "#e34948",
    "Very High": "#97202a",
}

# --- emphasis ---------------------------------------------------------------

ACCENT = "#c22f34"     # the one country or finding being highlighted
MUTED = "#c9c8c2"      # everything that is context, not the point
NEUTRAL = "#52514e"    # a second non-risk series where no identity is implied


def apply_style() -> None:
    """Set the rcParams every FoodMatrix chart shares. Call once per notebook."""
    mpl.rcParams.update(
        {
            "figure.figsize": (10, 5.6),          # 16:9-ish, reads well in video
            "figure.dpi": 110,
            "savefig.dpi": 200,
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "savefig.bbox": "tight",
            "font.family": "sans-serif",
            "font.sans-serif": ["DejaVu Sans", "Segoe UI", "Helvetica", "Arial"],
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.titleweight": "semibold",
            "axes.titlelocation": "left",
            "axes.titlepad": 14,
            "axes.labelsize": 11,
            "axes.labelcolor": INK_SECONDARY,
            "axes.edgecolor": AXIS,
            "axes.linewidth": 1.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "axes.axisbelow": True,
            "grid.color": GRID,
            "grid.linewidth": 0.8,
            "xtick.color": INK_MUTED,
            "ytick.color": INK_MUTED,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "xtick.direction": "out",
            "ytick.direction": "out",
            "legend.frameon": False,
            "legend.fontsize": 10,
            "lines.linewidth": 2.0,
            "lines.markersize": 8,
            "text.color": INK,
        }
    )


def title(ax, headline: str, subtitle: str | None = None) -> None:
    """Headline states the finding; subtitle carries units and reference period.

    A chart that leaves the reader guessing at the period invites exactly the
    question you do not want during the video.

    Both lines are drawn as axes-relative text rather than via ``set_title`` so
    the two never collide however long the headline is — ``set_title`` anchors to
    a fixed pad and a subtitle placed underneath it does not move out of the way.
    """
    ax.set_title("")
    y = 1.135 if subtitle else 1.045
    ax.text(
        0.0, y, headline, transform=ax.transAxes,
        fontsize=15, fontweight="semibold", color=INK, va="bottom", ha="left",
    )
    if subtitle:
        ax.text(
            0.0, 1.035, subtitle, transform=ax.transAxes,
            fontsize=10, color=INK_SECONDARY, va="bottom", ha="left",
        )


def source_note(fig, text: str = "FAOSTAT Detailed Trade Matrix, importer-reported quantities") -> None:
    """Provenance line along the bottom. Checkable is credible."""
    fig.text(0.0, -0.04, text, fontsize=9, color=INK_MUTED, ha="left", va="top")


def save(fig, name: str, subdir: str = "") -> Path:
    """Write to visualizations/<subdir>/<name>.png and return the path."""
    out_dir = VIZ / subdir if subdir else VIZ
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def emphasise(values: dict, highlight) -> list:
    """Colour list putting `highlight` in ACCENT and everything else in MUTED.

    >>> emphasise({"a": 1, "b": 2}, "b")
    ['#c9c8c2', '#c22f34']
    >>> emphasise({"a": 1, "b": 2}, ["a", "b"])
    ['#c22f34', '#c22f34']
    """
    keys = highlight if isinstance(highlight, (list, tuple, set)) else {highlight}
    return [ACCENT if k in keys else MUTED for k in values]


if __name__ == "__main__":
    import doctest

    failures, _ = doctest.testmod()
    print("plotting.py doctests:", "PASS" if not failures else "FAIL")
    raise SystemExit(1 if failures else 0)
