"""First-cut import-exposure analysis on the cleaned FAOSTAT trade matrix.

Runs against data/cleaned/trade_matrix_cleaned.csv (2.4 GB) using duckdb, so it
streams rather than loading the file into memory. A full run is about a minute.

What it does, and why in this order:

1. Filters to one commodity and a three-year window.
2. Computes supplier concentration per importer (HHI, effective suppliers,
   top partner and share).
3. Computes each reporter's net trade position and import intensity.
4. **Excludes net exporters.** This step is not cosmetic — without it the
   ranking is topped by Russia, Canada and the United States, whose small
   import volumes happen to come from a single neighbour. Concentration
   without dependency is not risk.

Import intensity = imports / (imports + exports) is a stopgap for the import
dependency ratio, which needs production data (FAOSTAT Food Balance Sheets or
the Production domain) that is not in the current pipeline. It separates real
importers from exporters and re-export hubs, but it is NOT dependency: it says
nothing about how much of domestic supply is home-grown. Replace it with the
proper IDR as soon as FBS lands.

Usage:
    python wheat_exposure_firstcut.py                     # wheat, 2021-23
    python wheat_exposure_firstcut.py --item "Maize (corn)"
    python wheat_exposure_firstcut.py --years 2022 2024 --min-kt 100
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import duckdb
import pandas as pd

# Resolved relative to the repository root so this works on any teammate's
# machine. Override with --csv or the FAOSTAT_MATRIX environment variable if
# your cleaned data lives outside the repo (it is gitignored, so it usually
# does).
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CSV = REPO_ROOT / "data" / "cleaned" / "trade_matrix_cleaned.csv"

# Item names must match the file exactly. FAOSTAT renames things between
# releases -- it is "Maize (corn)", not "Maize" -- and a mismatch yields an
# empty result rather than an error, so the script checks and says so.
STAPLES = ["Wheat", "Rice, milled", "Maize (corn)", "Rice, paddy (rice milled equivalent)"]


def build(csv_path: Path, item: str, y0: int, y1: int, min_kt: float) -> pd.DataFrame:
    con = duckdb.connect()
    src = f"read_csv_auto('{csv_path}', header=true)"
    query = f"""
    WITH base AS (
      SELECT "Reporter Countries" AS rep, "Partner Countries" AS ptn,
             Element AS el, avg(Value) AS qty
      FROM {src}
      WHERE Item = ? AND Element IN ('Import quantity','Export quantity')
        AND Year BETWEEN ? AND ?
      GROUP BY 1,2,3
    ),
    imp AS (SELECT rep AS c, ptn, qty FROM base WHERE el='Import quantity'),
    tot AS (SELECT c, sum(qty) AS imports FROM imp GROUP BY 1),
    exp AS (SELECT rep AS c, sum(qty) AS exports FROM base WHERE el='Export quantity' GROUP BY 1),
    sh  AS (SELECT i.c, i.ptn, i.qty / t.imports AS share
            FROM imp i JOIN tot t USING(c) WHERE t.imports > 0),
    conc AS (SELECT c, count(*) AS n_partners, sum(share*share) AS hhi,
                    max(share) AS top_share, arg_max(ptn, share) AS top_partner
             FROM sh GROUP BY 1)
    SELECT t.c AS country,
           t.imports / 1000 AS imp_kt,
           coalesce(e.exports, 0) / 1000 AS exp_kt,
           (t.imports - coalesce(e.exports, 0)) / 1000 AS net_imp_kt,
           t.imports / nullif(t.imports + coalesce(e.exports, 0), 0) AS imp_intensity,
           conc.n_partners, conc.hhi, 1 / conc.hhi AS eff_suppliers,
           conc.top_share, conc.top_partner
    FROM tot t LEFT JOIN exp e USING(c) JOIN conc USING(c)
    WHERE t.imports > ?
    ORDER BY conc.hhi DESC
    """
    return con.execute(query, [item, y0, y1, min_kt * 1000]).df()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, default=Path(os.environ.get("FAOSTAT_MATRIX", DEFAULT_CSV)))
    p.add_argument("--item", default="Wheat", help=f"one of e.g. {STAPLES}")
    p.add_argument("--years", nargs=2, type=int, default=[2021, 2023], metavar=("FROM", "TO"))
    p.add_argument("--min-kt", type=float, default=200.0, help="minimum import volume, thousand tonnes")
    p.add_argument("--out", type=Path, help="write the net-importer table to CSV")
    args = p.parse_args()

    if not args.csv.exists():
        raise SystemExit(f"Cleaned matrix not found at {args.csv}\nPass --csv or set FAOSTAT_MATRIX.")

    y0, y1 = args.years
    df = build(args.csv, args.item, y0, y1, args.min_kt)
    if df.empty:
        raise SystemExit(
            f"No rows for item {args.item!r}. Item names must match the file exactly — "
            f"try one of: {STAPLES}"
        )

    net_importers = df[df.net_imp_kt > 0].copy()
    net_exporters = df[df.net_imp_kt <= 0].copy()

    show = ["country", "imp_kt", "net_imp_kt", "imp_intensity", "n_partners",
            "hhi", "eff_suppliers", "top_share", "top_partner"]
    fmt = {c: "{:.3f}".format for c in ("imp_intensity", "hhi", "top_share")}
    fmt |= {c: "{:,.0f}".format for c in ("imp_kt", "net_imp_kt")}
    fmt["eff_suppliers"] = "{:.1f}".format

    print(f"\n{args.item.upper()} — net importers, {y0}-{y1} mean, ranked by supplier concentration")
    print(net_importers[show].to_string(index=False, formatters=fmt))

    if len(net_exporters):
        print(f"\nExcluded — net exporters ({len(net_exporters)}). Concentration alone would have")
        print("ranked these as high risk, which is why the dependency filter matters:")
        print(net_exporters[["country", "imp_kt", "exp_kt", "hhi"]]
              .to_string(index=False, formatters={"imp_kt": "{:,.0f}".format,
                                                  "exp_kt": "{:,.0f}".format,
                                                  "hhi": "{:.3f}".format}))

    # A small-volume importer buying from one neighbour will always top a
    # concentration ranking. Flag them rather than let them lead the story.
    small = net_importers[net_importers.imp_kt < net_importers.imp_kt.median()]
    if len(small):
        print(f"\nNote: {len(small)} of {len(net_importers)} net importers are below median volume. "
              "Concentration is mechanically high for small single-neighbour buyers "
              "(New Zealand/Australia is geography, not exposure) — weight by volume or "
              "per-capita supply before drawing conclusions.")

    if args.out:
        net_importers.to_csv(args.out, index=False)
        print(f"\nWrote {len(net_importers)} rows to {args.out}")


if __name__ == "__main__":
    main()
