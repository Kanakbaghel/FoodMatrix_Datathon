-- Run after scripts/build_faostat_dataset.py.
-- This is intentionally separate because exact HHI requires a large
-- bilateral group-by and sort. Run it in DuckDB with enough temporary disk.
--
-- Example:
--   duckdb data/processed/faostat.duckdb < scripts/partner_concentration.sql

SET memory_limit='1GB';
SET threads=2;
SET temp_directory='data/processed/tmp_duckdb';

COPY (
  WITH flows AS (
    SELECT
      CAST("Reporter Country Code" AS VARCHAR) AS reporter_code,
      "Reporter Countries" AS reporter,
      CAST("Partner Country Code" AS VARCHAR) AS partner_code,
      "Partner Countries" AS partner,
      CAST("Item Code" AS VARCHAR) AS item_code,
      "Item" AS item,
      CAST("Year" AS INTEGER) AS year,
      "Element" AS element,
      SUM(TRY_CAST("Value" AS DOUBLE)) AS flow_value_1000_usd
    FROM read_parquet('data/processed/trade_matrix_long.parquet')
    WHERE "Element" IN ('Import value', 'Export value')
      AND CAST("Reporter Country Code" AS VARCHAR)
          <> CAST("Partner Country Code" AS VARCHAR)
      AND TRY_CAST("Value" AS DOUBLE) > 0
    GROUP BY ALL
  ),
  scored AS (
    SELECT
      *,
      SUM(flow_value_1000_usd) OVER (
        PARTITION BY reporter_code, reporter, item_code, item, year, element
      ) AS total_flow_value_1000_usd,
      ROW_NUMBER() OVER (
        PARTITION BY reporter_code, reporter, item_code, item, year, element
        ORDER BY flow_value_1000_usd DESC, partner_code
      ) AS partner_rank
    FROM flows
  )
  SELECT
    reporter_code, reporter, item_code, item, year, element,
    MAX(total_flow_value_1000_usd) AS total_flow_value_1000_usd,
    COUNT(*) AS partner_count,
    SUM(POWER(flow_value_1000_usd / NULLIF(total_flow_value_1000_usd, 0), 2))
      AS partner_hhi,
    MAX(CASE WHEN partner_rank = 1
      THEN flow_value_1000_usd / NULLIF(total_flow_value_1000_usd, 0) END)
      AS top_partner_share,
    MAX(CASE WHEN partner_rank = 1 THEN partner END) AS top_partner,
    MAX(CASE WHEN partner_rank = 1 THEN partner_code END) AS top_partner_code,
    SUM(CASE WHEN partner_rank <= 3
      THEN flow_value_1000_usd / NULLIF(total_flow_value_1000_usd, 0)
      ELSE 0 END) AS top3_partner_share
  FROM scored
  GROUP BY reporter_code, reporter, item_code, item, year, element
)
TO 'data/processed/partner_concentration.parquet'
(FORMAT PARQUET, COMPRESSION ZSTD);