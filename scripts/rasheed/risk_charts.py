"""Analysis 2 chart set — the risk / exposure story.

Produces the charts nobody else's analysis covers: the supply-corridor cascade,
the Egypt concentration trajectory, and (once the scoring outputs are committed)
the risk ranking with intervals.

Usage:
    python scripts/rasheed/risk_charts.py

Charts 1 and 2 need only data/cleaned/trade_matrix_cleaned.csv, which is in the
repo. Chart 3 needs data/cleaned/country_risk.csv from scripts/calculate_risk.py;
it is skipped with a message if that file is absent rather than failing the run.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from plotting import (  # noqa: E402
    ACCENT,
    AXIS,
    INK,
    INK_MUTED,
    INK_SECONDARY,
    MUTED,
    NEUTRAL,
    RISK_LEVEL,
    SURFACE,
    apply_style,
    save,
    source_note,
    title,
)

TRADE = ROOT / "data" / "cleaned" / "trade_matrix_cleaned.csv"
COUNTRY_RISK = ROOT / "data" / "cleaned" / "country_risk.csv"

WHEAT_ITEMS = ["Wheat", "Wheat and meslin flour"]
WINDOW = (2019, 2021)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def wheat_flows() -> pd.DataFrame:
    """Importer-reported wheat flows, one row per reporter x partner x year."""
    cols = [
        "Reporter Countries", "Partner Countries", "Item",
        "Element", "Unit", "Year", "Value",
    ]
    df = pd.read_csv(TRADE, usecols=cols)
    df = df[
        (df["Element"] == "Import quantity")
        & (df["Unit"] == "t")
        & (df["Value"] > 0)
        & (df["Item"].isin(WHEAT_ITEMS))
    ]
    return (
        df.groupby(["Reporter Countries", "Partner Countries", "Year"], as_index=False)["Value"]
        .sum()
        .rename(columns={
            "Reporter Countries": "reporter",
            "Partner Countries": "partner",
            "Value": "q",
        })
    )


def window_shares(flows: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    """Supplier shares over a multi-year window, from summed quantities.

    Summed, not the mean of annual shares — averaging annual shares over-weights
    years a partner happened to be absent and can push the shares above 1.
    """
    w = flows[flows["Year"].between(lo, hi)]
    agg = w.groupby(["reporter", "partner"], as_index=False)["q"].sum()
    total = agg.groupby("reporter")["q"].transform("sum")
    agg["share"] = agg["q"] / total
    agg["mt_per_year"] = total / (hi - lo + 1) / 1e6
    return agg


# ---------------------------------------------------------------------------
# chart 1 — the cascade
# ---------------------------------------------------------------------------

def chart_cascade(flows: pd.DataFrame) -> Path:
    """Russia -> Kazakhstan -> Central Asia, the dependency behind the dependency.

    Emphasis form: the Russia->Kazakhstan link is the one no first-order metric
    shows, so it is the only link in the accent colour. Everything the ordinary
    supplier-share table already tells you is in the context grey.
    """
    lo, hi = WINDOW
    sh = window_shares(flows, lo, hi)

    importers = ["Uzbekistan", "Tajikistan", "Afghanistan", "Kyrgyzstan"]
    rows = []
    for c in importers:
        r = sh[(sh["reporter"] == c) & (sh["partner"] == "Kazakhstan")]
        if r.empty:
            continue
        rows.append({
            "country": c,
            "share": float(r["share"].iloc[0]),
            "mt": float(r["mt_per_year"].iloc[0]),
        })

    kaz = sh[(sh["reporter"] == "Kazakhstan") & (sh["partner"] == "Russian Federation")]
    kaz_share = float(kaz["share"].iloc[0])
    kaz_mt = float(kaz["mt_per_year"].iloc[0])
    downstream_mt = sum(r["mt"] * r["share"] for r in rows)

    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    def node(x, y, label, sub, w=0.155, h=0.105, edge=AXIS, lw=1.2):
        ax.add_patch(FancyBboxPatch(
            (x - w / 2, y - h / 2), w, h,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            facecolor=SURFACE, edgecolor=edge, linewidth=lw, zorder=3,
        ))
        ax.text(x, y + 0.016, label, ha="center", va="center",
                fontsize=11.5, fontweight="semibold", color=INK, zorder=4)
        ax.text(x, y - 0.028, sub, ha="center", va="center",
                fontsize=9, color=INK_MUTED, zorder=4)

    x_rus, x_kaz, x_imp = 0.10, 0.42, 0.80
    y_mid = 0.52

    node(x_rus, y_mid, "Russia", "world's largest\nwheat exporter", edge=ACCENT, lw=1.8)
    node(x_kaz, y_mid, "Kazakhstan", f"imports {kaz_mt:.2f} Mt/yr", edge=ACCENT, lw=1.8)

    ax.add_patch(FancyArrowPatch(
        (x_rus + 0.083, y_mid), (x_kaz - 0.083, y_mid),
        arrowstyle="-|>", mutation_scale=22, linewidth=7.0,
        color=ACCENT, alpha=0.92, zorder=2, shrinkA=0, shrinkB=0,
    ))
    ax.text((x_rus + x_kaz) / 2, y_mid + 0.075, f"{kaz_share:.1%}",
            ha="center", va="bottom", fontsize=13, fontweight="bold", color=ACCENT)
    ax.text((x_rus + x_kaz) / 2, y_mid - 0.075, "of Kazakhstan's own\nwheat imports",
            ha="center", va="top", fontsize=9, color=INK_SECONDARY)

    # the visible links — fan out from the right edge of the Kazakhstan node so
    # no arrow tracks back across the figure to reach a low node
    ys = np.linspace(0.86, 0.20, len(rows))
    heaviest = max(r["mt"] for r in rows)
    for r, y in zip(rows, ys):
        node(x_imp, y, r["country"], f"{r['mt']:.2f} Mt/yr", w=0.19, h=0.098)
        y_start = y_mid + (y - y_mid) * 0.10
        ax.add_patch(FancyArrowPatch(
            (x_kaz + 0.085, y_start), (x_imp - 0.101, y),
            arrowstyle="-|>", mutation_scale=15,
            linewidth=1.0 + 5.0 * (r["mt"] / heaviest),
            color=MUTED, zorder=1, shrinkA=0, shrinkB=0,
        ))
        ax.text(x_imp - 0.118, y + 0.042, f"{r['share']:.1%}",
                ha="right", va="center", fontsize=10.5,
                fontweight="semibold", color=INK_SECONDARY)

    title(
        ax,
        "Central Asia's wheat risk is one step further back than it looks",
        f"Share of each country's wheat imports from its largest supplier · "
        f"quantity, {lo}–{hi} mean",
    )
    ax.text(
        0.5, 0.02,
        f"Four countries and ~{downstream_mt:.1f} Mt a year sit behind a supplier that is itself "
        f"{kaz_share:.1%} single-origin.\nDiversifying toward Kazakhstan is not a hedge against Russia.",
        ha="center", va="bottom", fontsize=11, color=INK, linespacing=1.5,
    )
    source_note(fig)
    return save(fig, "cascade_central_asia_wheat")


# ---------------------------------------------------------------------------
# chart 2 — Egypt
# ---------------------------------------------------------------------------

def chart_egypt(flows: pd.DataFrame) -> Path:
    """Concentration rose after the shock, not before it.

    Two series, both on a 0-1 scale, so they share one axis — never two.
    """
    e = flows[(flows["reporter"] == "Egypt") & (flows["Year"] >= 2016)].copy()
    total = e.groupby("Year")["q"].transform("sum")
    e["share"] = e["q"] / total

    hhi = e.groupby("Year")["share"].apply(lambda s: (s ** 2).sum())
    rus = (
        e[e["partner"] == "Russian Federation"].groupby("Year")["share"].sum()
        .reindex(hhi.index, fill_value=0.0)
    )

    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.axvspan(2022, hhi.index.max(), color="#f4f3ef", zorder=0)

    ax.plot(rus.index, rus.values, color=NEUTRAL, marker="o",
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=3)
    ax.plot(hhi.index, hhi.values, color=ACCENT, marker="o",
            markeredgecolor=SURFACE, markeredgewidth=1.5, zorder=4)

    # direct labels on the left, where the two lines are furthest apart
    ax.annotate("Russia's share of\nEgypt's wheat imports",
                xy=(2019, float(rus.loc[2019])), xytext=(0, 34),
                textcoords="offset points", ha="center", fontsize=10,
                color=NEUTRAL, fontweight="semibold", linespacing=1.4)
    ax.annotate("Supplier concentration (HHI)",
                xy=(2019, float(hhi.loc[2019])), xytext=(0, -30),
                textcoords="offset points", ha="center", fontsize=10,
                color=ACCENT, fontweight="semibold")

    ax.set_ylim(0, max(hhi.max(), rus.max()) * 1.26)

    ax.axvline(2022, color=AXIS, linewidth=1.2, linestyle=(0, (4, 3)), zorder=1)
    ax.text(2022.08, ax.get_ylim()[1] * 0.99, "Black Sea disruption",
            fontsize=9.5, color=INK_SECONDARY, va="top")

    # the delta: a reference line at the 2021 low, and the rise measured against
    # it at the right-hand end — so the bracket cannot be misread as spanning
    # between the two different series
    last = int(hhi.index.max())
    lo_y, hi_y = float(hhi.loc[2021]), float(hhi.loc[last])
    ax.hlines(lo_y, 2021, last, color=ACCENT, linewidth=1.0,
              linestyle=(0, (3, 3)), alpha=0.55, zorder=2)
    ax.annotate("", xy=(last - 0.16, hi_y), xytext=(last - 0.16, lo_y),
                arrowprops=dict(arrowstyle="<->", color=INK_MUTED, linewidth=1.1))
    ax.text(last - 0.26, (lo_y + hi_y) / 2, f"+{(hi_y / lo_y - 1):.0%}",
            ha="right", va="center", fontsize=11, fontweight="bold", color=INK)
    ax.text(2021.05, lo_y - 0.028, "2021 level", fontsize=9,
            color=ACCENT, alpha=0.8, va="top")

    ax.set_xticks(list(hhi.index))
    ax.set_ylabel("Share of imports / HHI (0–1)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)

    title(
        ax,
        "The shock made Egypt's wheat supply more concentrated, not less",
        "Egypt, all wheat items · importer-reported quantities · "
        f"{int(hhi.index.min())}–{int(hhi.index.max())}",
    )
    source_note(
        fig,
        "FAOSTAT Detailed Trade Matrix · Egypt's baladi bread subsidy reached "
        "73 million people in 2023 (IFPRI)",
    )
    return save(fig, "egypt_concentration_trajectory")


# ---------------------------------------------------------------------------
# chart 3 — risk ranking (needs the scoring output)
# ---------------------------------------------------------------------------

def chart_risk_ranking(top_n: int = 20) -> Path | None:
    """Top-N countries by mean risk score, banded by risk level.

    Horizontal bars sorted by value, never alphabetically — the ranking is the
    message. The line through each bar spans the annual values in the window, so
    a country whose score is unstable is visibly unstable. When
    monte_carlo_ranks is wired in, that line becomes the rank interval: a point
    rank claims a precision the method does not have.
    """
    if not COUNTRY_RISK.exists():
        print(f"  skipped chart_risk_ranking - {COUNTRY_RISK.name} not present.")
        print("  Run scripts/calculate_risk.py, or ask Moksh for the committed sample.")
        return None

    df = pd.read_csv(COUNTRY_RISK)
    lo, hi = WINDOW
    recent = df[df["Year"].between(lo, hi)]
    agg = (
        recent.groupby("Country")["country_risk_score"]
        .agg(["mean", "min", "max"])
        .sort_values("mean", ascending=False)
        .head(top_n)
        .iloc[::-1]
    )

    def band(v: float) -> str:
        return ("Very High" if v >= 0.75 else "High" if v >= 0.5
                else "Moderate" if v >= 0.25 else "Low")

    fig, ax = plt.subplots(figsize=(10, 0.34 * len(agg) + 2.4))
    y = np.arange(len(agg))
    ax.barh(y, agg["mean"], color=[RISK_LEVEL[band(v)] for v in agg["mean"]],
            height=0.68, zorder=3)
    ax.hlines(y, agg["min"], agg["max"], color=INK_MUTED, linewidth=1.4, zorder=4)

    for yi, v in zip(y, agg["mean"]):
        ax.text(v + 0.012, yi, f"{v:.2f}", va="center", fontsize=9.5, color=INK_SECONDARY)

    ax.set_yticks(y)
    ax.set_yticklabels(agg.index, fontsize=10, color=INK)
    ax.set_xlim(0, 1.06)
    ax.set_xlabel("Composite risk score (0–1)")
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_color(AXIS)

    title(
        ax,
        f"Top {top_n} countries by staple-import risk",
        f"Mean of {lo}–{hi}; bar is the mean, line spans the annual values",
    )
    source_note(fig, "FoodMatrix composite risk index · dependence x concentration x supplier count")
    return save(fig, "risk_ranking_top20")


def main() -> None:
    apply_style()
    if not TRADE.exists():
        raise SystemExit(f"{TRADE} not found. Run scripts/build_faostat_dataset.py first.")

    flows = wheat_flows()
    print("wrote", chart_cascade(flows))
    print("wrote", chart_egypt(flows))
    p = chart_risk_ranking()
    if p:
        print("wrote", p)


if __name__ == "__main__":
    main()
