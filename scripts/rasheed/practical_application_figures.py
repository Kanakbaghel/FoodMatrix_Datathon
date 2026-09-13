"""Reproduce every figure quoted in docs/rasheed/practical_application.md.

Reads data/cleaned/trade_matrix_cleaned.csv (importer-reported quantities) and
prints each table in the order the document uses them, so any number in the
video script can be traced back to a command rather than to a spreadsheet.

Usage:
    python scripts/rasheed/practical_application_figures.py

Two deliberate choices, both of which change the answers:

1. **Rice uses "Rice, paddy (rice milled equivalent)" only.** That item is
   FAOSTAT's milled-equivalent aggregate and already contains "Rice, milled".
   Summing the two -- as config/faostat.json and build_quantity_concentration.py
   currently do -- gives ~67 Mt/yr of world rice imports for 2019-21 against an
   actual ~50 Mt/yr. Add the second item to RICE_ITEMS below to reproduce the
   double-counted figures for comparison.

2. **Shares over a multi-year window are computed from summed quantities**, not
   as the mean of annual shares. Averaging annual shares over-weights years in
   which a partner happened to be absent and can produce shares summing above 1.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
TRADE = ROOT / "data" / "cleaned" / "trade_matrix_cleaned.csv"

WHEAT_ITEMS = ("Wheat", "Wheat and meslin flour")
RICE_ITEMS = ("Rice, paddy (rice milled equivalent)",)
MAIZE_ITEMS = ("Maize (corn)",)

WINDOW = (2019, 2021)

CENTRAL_ASIA = (
    "Uzbekistan",
    "Tajikistan",
    "Kyrgyzstan",
    "Afghanistan",
    "Kazakhstan",
    "Azerbaijan",
    "Georgia",
    "Armenia",
    "Mongolia",
)


def connect() -> duckdb.DuckDBPyConnection:
    if not TRADE.exists():
        raise SystemExit(
            f"{TRADE} not found. Run scripts/build_faostat_dataset.py first."
        )

    items = WHEAT_ITEMS + RICE_ITEMS + MAIZE_ITEMS
    item_list = ", ".join(f"'{i}'" for i in items)
    wheat = ", ".join(f"'{i}'" for i in WHEAT_ITEMS)
    rice = ", ".join(f"'{i}'" for i in RICE_ITEMS)

    con = duckdb.connect()
    con.execute(
        f"""
        CREATE TABLE flows AS
        SELECT "Reporter Countries" AS reporter,
               "Partner Countries"  AS partner,
               CASE WHEN Item IN ({wheat}) THEN 'Wheat'
                    WHEN Item IN ({rice})  THEN 'Rice'
                    ELSE 'Maize' END       AS commodity,
               Year,
               sum(Value)                  AS q
        FROM read_csv_auto('{TRADE.as_posix()}')
        WHERE Element = 'Import quantity'
          AND Unit = 't'
          AND Value > 0
          AND Item IN ({item_list})
        GROUP BY 1, 2, 3, 4
        """
    )
    con.execute(
        """
        CREATE TABLE shares AS
        SELECT *,
               q / sum(q) OVER (PARTITION BY reporter, commodity, Year)   AS share,
               sum(q) OVER (PARTITION BY reporter, commodity, Year)       AS total
        FROM flows
        """
    )
    return con


def banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def cascade(con: duckdb.DuckDBPyConnection) -> None:
    """Section 2.1 -- Central Asian wheat cascade."""
    lo, hi = WINDOW
    country_list = ", ".join(f"'{c}'" for c in CENTRAL_ASIA)

    banner(f"2.1  Central Asia / Caucasus wheat, {lo}-{hi} mean")
    print(
        con.execute(
            f"""
            WITH agg AS (
                SELECT reporter, partner, sum(q) AS qsum
                FROM shares
                WHERE commodity = 'Wheat' AND Year BETWEEN {lo} AND {hi}
                  AND reporter IN ({country_list})
                GROUP BY 1, 2
            )
            SELECT reporter,
                   round(sum(qsum) OVER (PARTITION BY reporter) / 3 / 1e6, 2) AS mt_per_year,
                   partner,
                   round(qsum / sum(qsum) OVER (PARTITION BY reporter), 3)    AS share
            FROM agg
            QUALIFY row_number() OVER (PARTITION BY reporter ORDER BY qsum DESC) <= 3
            ORDER BY reporter, share DESC
            """
        ).fetchdf().to_string(index=False)
    )

    banner("2.1  Kazakh and Russian shares by year, 2021-2024 (the 2022 quota window)")
    print(
        con.execute(
            f"""
            WITH t AS (
                SELECT reporter, Year, any_value(total) AS total
                FROM shares WHERE commodity = 'Wheat' GROUP BY 1, 2
            ),
            k AS (
                SELECT reporter, Year, sum(q) AS q FROM shares
                WHERE commodity = 'Wheat' AND partner = 'Kazakhstan' GROUP BY 1, 2
            ),
            r AS (
                SELECT reporter, Year, sum(q) AS q FROM shares
                WHERE commodity = 'Wheat' AND partner = 'Russian Federation' GROUP BY 1, 2
            )
            SELECT t.reporter, t.Year,
                   round(t.total / 1e3, 0)                  AS kt,
                   round(coalesce(k.q, 0) / t.total, 3)     AS kazakh_share,
                   round(coalesce(r.q, 0) / t.total, 3)     AS russian_share
            FROM t LEFT JOIN k USING (reporter, Year) LEFT JOIN r USING (reporter, Year)
            WHERE t.reporter IN ({country_list}) AND t.Year BETWEEN 2021 AND 2024
            ORDER BY reporter, Year
            """
        ).fetchdf().to_string(index=False)
    )


def egypt(con: duckdb.DuckDBPyConnection) -> None:
    """Section 2.2 -- concentration rose after the 2022 shock."""
    banner("2.2  Egypt wheat: imports, partner HHI and Russian share by year")
    print(
        con.execute(
            """
            SELECT Year,
                   round(any_value(total) / 1e3, 0)                       AS kt,
                   round(sum(share * share), 3)                           AS partner_hhi,
                   round(sum(CASE WHEN partner = 'Russian Federation'
                                  THEN share ELSE 0 END), 3)              AS russia_share,
                   count(*)                                               AS n_partners
            FROM shares
            WHERE reporter = 'Egypt' AND commodity = 'Wheat' AND Year >= 2018
            GROUP BY Year ORDER BY Year
            """
        ).fetchdf().to_string(index=False)
    )


def india_rice(con: duckdb.DuckDBPyConnection) -> None:
    """Section 2.3 -- out-of-sample test against the 2023 export restrictions."""
    banner("2.3  Rice importers >50% India-sourced in 2021: volume change to 2023")
    print(
        con.execute(
            """
            WITH t AS (
                SELECT reporter, Year, any_value(total) AS total
                FROM shares WHERE commodity = 'Rice' GROUP BY 1, 2
            ),
            i AS (
                SELECT reporter, Year, sum(q) AS q FROM shares
                WHERE commodity = 'Rice' AND partner = 'India' GROUP BY 1, 2
            ),
            base AS (
                SELECT t.reporter, t.total AS kt21, coalesce(i.q, 0) / t.total AS india21
                FROM t LEFT JOIN i USING (reporter, Year) WHERE t.Year = 2021
            ),
            y23 AS (SELECT reporter, total AS kt23 FROM t WHERE Year = 2023)
            SELECT b.reporter,
                   round(b.india21, 2)                              AS india_share_2021,
                   round(b.kt21 / 1e3, 0)                           AS kt_2021,
                   round(y23.kt23 / 1e3, 0)                         AS kt_2023,
                   round(100 * (y23.kt23 - b.kt21) / b.kt21, 0)     AS pct_change
            FROM base b JOIN y23 USING (reporter)
            WHERE b.india21 > 0.5 AND b.kt21 > 1e5
            ORDER BY pct_change
            """
        ).fetchdf().to_string(index=False)
    )


def rice_double_count(con: duckdb.DuckDBPyConnection) -> None:
    """Section 5 -- evidence for the rice item double-count."""
    lo, hi = WINDOW
    banner("5  Rice item double-count: world import quantity by item")
    print(
        con.execute(
            f"""
            SELECT Item, round(sum(Value) / 3 / 1e6, 1) AS mt_per_year
            FROM read_csv_auto('{TRADE.as_posix()}')
            WHERE Element = 'Import quantity' AND Unit = 't'
              AND Year BETWEEN {lo} AND {hi}
              AND Item LIKE 'Rice%'
            GROUP BY Item ORDER BY mt_per_year DESC
            """
        ).fetchdf().to_string(index=False)
    )
    print(
        "\nWorld rice trade is roughly 50 Mt/yr. Summing the two items above "
        "gives ~67 Mt/yr,\nbecause the milled-equivalent item is the aggregate "
        "and already contains milled rice."
    )
    print()
    print(
        con.execute(
            f"""
            SELECT Year, count(*) AS reporter_partner_pairs_reporting_both
            FROM (
                SELECT "Reporter Country Code" AS rc, "Partner Country Code" AS pc, Year
                FROM read_csv_auto('{TRADE.as_posix()}')
                WHERE Element = 'Import quantity' AND Value > 0
                  AND Item IN ('Rice, paddy (rice milled equivalent)', 'Rice, milled')
                GROUP BY 1, 2, 3
                HAVING count(DISTINCT Item) = 2
            )
            WHERE Year BETWEEN 2020 AND 2024
            GROUP BY Year ORDER BY Year
            """
        ).fetchdf().to_string(index=False)
    )


def main() -> None:
    con = connect()
    cascade(con)
    egypt(con)
    india_rice(con)
    rice_double_count(con)
    print()


if __name__ == "__main__":
    main()
