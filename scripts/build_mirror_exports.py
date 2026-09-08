"""Build mirror-corrected export figures from the detailed trade matrix.

Why this exists: some reporters (Russia, Bulgaria — see faostat_data_audit.md
2.1) stop self-reporting exports in certain years. Any script that ranks or
sums exports using the "Export quantity"/"Export value" element directly will
show these countries at zero for those years, which is false — the trade
still happened, just recorded by the partner instead.

Fix: for every (country, item, year), reconstruct implied exports as the sum
of what OTHER countries report importing FROM that country. This is possible
because partner countries in trade_matrix_long.parquet are NOT restricted to
the top 50 reporters (only reporters are) — so a full mirror is available.

Usage:
    python scripts/build_mirror_exports.py

Run this AFTER build_faostat_dataset.py, since it reads
data/processed/trade_matrix_long.parquet.

Output:
    data/processed/mirror_exports.parquet
    data/cleaned/mirror_exports_cleaned.csv
"""

from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CLEANED = ROOT / "data" / "cleaned"

TM_LONG = PROCESSED / "trade_matrix_long.parquet"
OUT_PARQUET = PROCESSED / "mirror_exports.parquet"
OUT_CSV = CLEANED / "mirror_exports_cleaned.csv"


def main() -> None:
    if not TM_LONG.exists():
        raise SystemExit(
            f"{TM_LONG} not found. Run build_faostat_dataset.py first."
        )
    CLEANED.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute(
        f"""
        COPY (
          WITH self_reported AS (
            -- What the country itself says it exported.
            SELECT
              CAST("Reporter Country Code" AS VARCHAR) AS area_code,
              "Reporter Countries" AS area,
              CAST("Item Code" AS VARCHAR) AS item_code,
              "Item" AS item,
              CAST("Year" AS INTEGER) AS year,
              "Element" AS element,
              SUM(TRY_CAST("Value" AS DOUBLE)) AS self_reported_value
            FROM read_parquet('{TM_LONG}')
            WHERE "Element" IN ('Export quantity', 'Export value')
              AND CAST("Reporter Country Code" AS VARCHAR)
                  <> CAST("Partner Country Code" AS VARCHAR)  -- drop self-trade
              AND TRY_CAST("Value" AS DOUBLE) > 0
            GROUP BY ALL
          ),
          mirrored AS (
            -- What every OTHER country says it imported FROM this country.
            -- This is the reconstruction: it does not depend on the country's
            -- own reporting at all, so it survives a reporting blackout.
            SELECT
              CAST("Partner Country Code" AS VARCHAR) AS area_code,
              "Partner Countries" AS area,
              CAST("Item Code" AS VARCHAR) AS item_code,
              "Item" AS item,
              CAST("Year" AS INTEGER) AS year,
              REPLACE("Element", 'Import', 'Export') AS element,
              SUM(TRY_CAST("Value" AS DOUBLE)) AS mirror_value,
              COUNT(*) AS n_partner_reports
            FROM read_parquet('{TM_LONG}')
            WHERE "Element" IN ('Import quantity', 'Import value')
              AND CAST("Reporter Country Code" AS VARCHAR)
                  <> CAST("Partner Country Code" AS VARCHAR)
              AND TRY_CAST("Value" AS DOUBLE) > 0
            GROUP BY ALL
          )
          SELECT
            COALESCE(s.area_code, m.area_code) AS area_code,
            COALESCE(s.area, m.area) AS area,
            COALESCE(s.item_code, m.item_code) AS item_code,
            COALESCE(s.item, m.item) AS item,
            COALESCE(s.year, m.year) AS year,
            COALESCE(s.element, m.element) AS element,
            s.self_reported_value,
            m.mirror_value,
            m.n_partner_reports,
            -- The value to actually use downstream. Prefer self-report when
            -- present; fall back to mirror when the country goes silent.
            COALESCE(s.self_reported_value, m.mirror_value) AS recommended_value,
            CASE
              WHEN s.self_reported_value IS NULL AND m.mirror_value IS NOT NULL
                THEN 'mirror_only_reporter_silent'
              WHEN s.self_reported_value IS NOT NULL AND m.mirror_value IS NULL
                THEN 'self_report_only_no_mirror'
              WHEN s.self_reported_value IS NOT NULL AND m.mirror_value IS NOT NULL
                THEN 'both_available'
              ELSE 'neither'
            END AS coverage_flag
          FROM self_reported s
          FULL OUTER JOIN mirrored m
            USING (area_code, area, item_code, item, year, element)
        )
        TO '{OUT_PARQUET}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
    )
    con.execute(
        f"""
        COPY (SELECT * FROM read_parquet('{OUT_PARQUET}'))
        TO '{OUT_CSV}' (FORMAT CSV, HEADER, DELIMITER ',')
        """
    )
    n_rows = con.execute(f"SELECT COUNT(*) FROM read_parquet('{OUT_PARQUET}')").fetchone()[0]
    n_silent = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{OUT_PARQUET}') "
        "WHERE coverage_flag = 'mirror_only_reporter_silent'"
    ).fetchone()[0]
    con.close()

    print(f"Wrote {n_rows:,} rows to {OUT_CSV}")
    print(f"{n_silent:,} country-item-year-element cells exist ONLY because of "
          f"the mirror (i.e. the reporter went silent there — Russia post-2021 "
          f"wheat exports will show up in this count).")
    print("\nDownstream rule: for any exporter ranking or total, use "
          "'recommended_value', never the raw self-reported export element "
          "directly. Check 'coverage_flag' to see which cells were rescued.")


if __name__ == "__main__":
    main()