"""Build auditable, analysis-ready FAOSTAT tables for the datathon.

The script uses a two-pass design:
1. Rank reporting areas by 20-year trade value.
2. Filter aggregate trade, producer prices, and bilateral trade flows to the
   selected reporting areas and years.

No missing values are silently filled. All quantities retain their original
FAOSTAT units, because tonnes, animals, and counts cannot be compared safely.

Usage:
    python scripts/build_faostat_dataset.py
"""

from __future__ import annotations

import json
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
METADATA = ROOT / "data" / "metadata"
CONFIG = ROOT / "config" / "faostat.json"
CHUNK_SIZE = 200_000


def zip_member(path: Path, contains: str) -> str:
    with zipfile.ZipFile(path) as archive:
        matches = [name for name in archive.namelist() if contains in name and name.endswith(".csv")]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one CSV containing {contains!r} in {path}, found {matches}")
    return matches[0]


def read_reference_table(path: Path, contains: str) -> pd.DataFrame:
    member = zip_member(path, contains)
    with zipfile.ZipFile(path) as archive, archive.open(member) as handle:
        return pd.read_csv(handle, dtype="string")


def iter_csv_chunks(path: Path, contains: str) -> Iterable[pd.DataFrame]:
    member = zip_member(path, contains)
    archive = zipfile.ZipFile(path)
    handle = archive.open(member)
    try:
        yield from pd.read_csv(
            handle,
            dtype="string",
            chunksize=CHUNK_SIZE,
            low_memory=False,
        )
    finally:
        handle.close()
        archive.close()


def write_parquet_chunks(
    path: Path,
    output: Path,
    filter_chunk,
    columns: list[str],
) -> int:
    """Filter a CSV inside a zip and stream the result to Parquet."""
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    if temporary.exists():
        temporary.unlink()
    writer = None
    rows_written = 0
    completed = False
    try:
        for chunk in iter_csv_chunks(path, "All_Data"):
            filtered = filter_chunk(chunk)
            if filtered.empty:
                continue
            filtered = filtered[columns].copy()
            table = pa.Table.from_pandas(filtered, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(temporary, table.schema, compression="zstd")
            writer.write_table(table)
            rows_written += len(filtered)
        completed = True
    finally:
        if writer is not None:
            writer.close()
            if completed:
                temporary.replace(output)
            elif temporary.exists():
                temporary.unlink()
        elif temporary.exists():
            temporary.unlink()
    return rows_written


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def select_reporting_areas(config: dict) -> tuple[pd.DataFrame, set[str]]:
    trade_zip = RAW / "Trade_CropsLivestock_E_All_Data_Normalized.zip"
    area = read_reference_table(trade_zip, "AreaCodes")
    area["Area Code"] = area["Area Code"].astype("string").str.strip()
    area["M49 Code"] = area["M49 Code"].astype("string").str.strip()
    area["is_aggregate"] = (
        area["Area Code"].astype("int64").ge(5000)
        | area["M49 Code"].str.contains(".", regex=False, na=False)
        | area["Area Code"].isin(config.get("exclude_area_codes", []))
    )
    eligible_codes = set(area.loc[~area["is_aggregate"], "Area Code"])
    start, end = config["start_year"], config["end_year"]

    if config.get("geography_mode") == "commodity_filter":
        # Verified against the raw detailed trade matrix: the staple items
        # are 2.4% of all 52.4M global rows (1,278,643 rows), which is
        # smaller than the current 24.7M-row, 50-country cap -- while
        # covering every country instead of only the 50 largest traders.
        # This restores small import-dependent countries (Nigeria,
        # Bangladesh, Pakistan, Ethiopia, Morocco) that a trade-value
        # ranking excludes but which are central to the risk-index story.
        ranked = area.loc[~area["is_aggregate"]].copy()
        ranked.insert(0, "rank", range(1, len(ranked) + 1))
        ranked = ranked.rename(columns={"Area": "area", "Area Code": "area_code", "M49 Code": "m49_code"})
        ranked["trade_value_1000_usd_2005_2024"] = None
        ranked["avg_annual_trade_value_1000_usd"] = None
        ranked["selection_period"] = f"{start}-{end}"
        ranked["rank_metric"] = "commodity_filter: all non-aggregate areas, staple items only"
        ranked.to_csv(METADATA / "top50_reporting_areas_2005_2024.csv", index=False)
        return ranked, set(ranked["area_code"].astype(str))
    totals: defaultdict[str, float] = defaultdict(float)

    for chunk in iter_csv_chunks(trade_zip, "All_Data"):
        years = pd.to_numeric(chunk["Year"], errors="coerce")
        mask = (
            years.between(start, end)
            & chunk["Area Code"].isin(eligible_codes)
            & chunk["Element"].isin(["Import value", "Export value"])
        )
        selected = chunk.loc[mask, ["Area Code", "Area", "Value"]].copy()
        if selected.empty:
            continue
        selected["Value"] = pd.to_numeric(selected["Value"], errors="coerce").fillna(0)
        for code, value in selected.groupby("Area Code", sort=False)["Value"].sum().items():
            totals[str(code)] += float(value)

    area["trade_value_1000_usd_2005_2024"] = area["Area Code"].map(totals).fillna(0.0)
    area["avg_annual_trade_value_1000_usd"] = (
        area["trade_value_1000_usd_2005_2024"] / (end - start + 1)
    )
    ranked = (
        area.loc[~area["is_aggregate"]]
        .sort_values("trade_value_1000_usd_2005_2024", ascending=False)
        .head(config["n_reporting_areas"])
        .copy()
    )
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    ranked = ranked.rename(columns={"Area": "area", "Area Code": "area_code", "M49 Code": "m49_code"})
    ranked["selection_period"] = f"{start}-{end}"
    ranked["rank_metric"] = config["rank_metric"]
    ranked.to_csv(METADATA / "top50_reporting_areas_2005_2024.csv", index=False)
    return ranked, set(ranked["area_code"].astype(str))


def build_aggregate_tables(selected_codes: set[str], config: dict) -> dict[str, int]:
    path = RAW / "Trade_CropsLivestock_E_All_Data_Normalized.zip"
    start, end = config["start_year"], config["end_year"]
    columns = [
        "Area Code", "Area", "Item Code", "Item", "Element", "Year",
        "Unit", "Value", "Flag", "Note",
    ]

    staple_items = config.get("staple_items") if config.get("geography_mode") == "commodity_filter" else None

    def filter_trade(chunk: pd.DataFrame) -> pd.DataFrame:
        years = pd.to_numeric(chunk["Year"], errors="coerce")
        mask = (
            years.between(start, end)
            & chunk["Area Code"].isin(selected_codes)
            & chunk["Element"].isin(
                ["Import value", "Export value", "Import quantity", "Export quantity"]
            )
        )
        if staple_items is not None:
            # Item names must match FAOSTAT verbatim (e.g. "Maize (corn)",
            # not "Maize") -- see analysis2_first_cut.md section 6.
            mask &= chunk["Item"].isin(staple_items)
        return chunk.loc[mask]

    rows = write_parquet_chunks(
        path, PROCESSED / "trade_aggregate_long.parquet", filter_trade, columns
    )
    return {"trade_aggregate_long": rows}


def build_price_table(selected_codes: set[str], config: dict) -> dict[str, int]:
    path = RAW / "Prices_E_All_Data_Normalized.zip"
    start, end = config["start_year"], config["end_year"]
    columns = [
        "Area Code", "Area", "Item Code", "Item", "Element", "Year",
        "Months", "Unit", "Value", "Flag",
    ]

    def filter_prices(chunk: pd.DataFrame) -> pd.DataFrame:
        years = pd.to_numeric(chunk["Year"], errors="coerce")
        return chunk.loc[
            years.between(start, end)
            & chunk["Area Code"].isin(selected_codes)
            & chunk["Months"].eq("Annual value")
            & chunk["Element"].isin(
                ["Producer Price (USD/tonne)", "Producer Price Index (2014-2016 = 100)"]
            )
        ]

    rows = write_parquet_chunks(
        path, PROCESSED / "producer_prices_annual_long.parquet", filter_prices, columns
    )
    return {"producer_prices_annual_long": rows}


def build_detailed_matrix(selected_codes: set[str], config: dict) -> dict[str, int]:
    path = RAW / "Trade_DetailedTradeMatrix_E_All_Data_Normalized.zip"
    start, end = config["start_year"], config["end_year"]
    partner_reference = read_reference_table(path, "PartnerCountries")
    partner_reference["Partner Country Code"] = (
        partner_reference["Partner Country Code"].astype("string").str.strip()
    )
    partner_reference["M49 Code"] = partner_reference["M49 Code"].astype("string").str.strip()
    eligible_partner_codes = set(
        partner_reference.loc[
            partner_reference["Partner Country Code"].astype("int64").lt(5000)
            & ~partner_reference["M49 Code"].str.contains(".", regex=False, na=False)
            & ~partner_reference["Partner Country Code"].isin(config.get("exclude_area_codes", [])),
            "Partner Country Code",
        ]
    )
    columns = [
        "Reporter Country Code", "Reporter Countries",
        "Partner Country Code", "Partner Countries",
        "Item Code", "Item", "Element", "Year", "Unit", "Value", "Flag",
    ]

    staple_items = config.get("staple_items") if config.get("geography_mode") == "commodity_filter" else None

    def filter_matrix(chunk: pd.DataFrame) -> pd.DataFrame:
        years = pd.to_numeric(chunk["Year"], errors="coerce")
        reporter = chunk["Reporter Country Code"].astype("string")
        partner = chunk["Partner Country Code"].astype("string")
        mask = (
            years.between(start, end)
            & reporter.isin(selected_codes)
            & partner.isin(eligible_partner_codes)
            & chunk["Element"].isin(
                ["Import value", "Export value", "Import quantity", "Export quantity"]
            )
            # Self-trade rows (reporter == partner) survive into the cleaned
            # CSV otherwise -- see faostat_data_audit.md 2.5. Excluded here
            # rather than left for every downstream script to remember.
            & (reporter != partner)
        )
        if staple_items is not None:
            mask &= chunk["Item"].isin(staple_items)
        return chunk.loc[mask]

    rows = write_parquet_chunks(
        path, PROCESSED / "trade_matrix_long.parquet", filter_matrix, columns
    )
    return {"trade_matrix_long": rows}


def create_feature_tables() -> dict[str, int]:
    """Create transparent ratios/rolling statistics; do not impute missing data."""
    PROCESSED.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    trade_country_item_year = PROCESSED / "trade_country_item_year.parquet"
    price_country_item_year = PROCESSED / "price_country_item_year.parquet"
    feature_output = PROCESSED / "country_item_year_features.parquet"
    con.execute(
        """
        CREATE OR REPLACE TABLE trade AS
        SELECT
          CAST("Area Code" AS VARCHAR) AS area_code,
          "Area" AS area,
          CAST("Item Code" AS VARCHAR) AS item_code,
          "Item" AS item,
          CAST("Year" AS INTEGER) AS year,
          "Element" AS element,
          "Unit" AS unit,
          TRY_CAST("Value" AS DOUBLE) AS value,
          "Flag" AS flag
        FROM read_parquet(?)
        """,
        [str(PROCESSED / "trade_aggregate_long.parquet")],
    )
    con.execute(
        f"""
        COPY (
          SELECT
            area_code, area, item_code, item, year,
            MAX(CASE WHEN element = 'Import value' THEN value END) AS import_value_1000_usd,
            MAX(CASE WHEN element = 'Export value' THEN value END) AS export_value_1000_usd,
            MAX(CASE WHEN element = 'Import quantity' AND unit = 't' THEN value END) AS import_quantity_tonnes,
            MAX(CASE WHEN element = 'Export quantity' AND unit = 't' THEN value END) AS export_quantity_tonnes,
            MAX(CASE WHEN element = 'Import quantity' THEN unit END) AS import_quantity_unit,
            MAX(CASE WHEN element = 'Export quantity' THEN unit END) AS export_quantity_unit
          FROM trade
          GROUP BY ALL
        )
        TO '{trade_country_item_year}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    con.execute(
        """
        CREATE OR REPLACE TABLE prices AS
        SELECT
          CAST("Area Code" AS VARCHAR) AS area_code,
          "Area" AS area,
          CAST("Item Code" AS VARCHAR) AS item_code,
          "Item" AS item,
          CAST("Year" AS INTEGER) AS year,
          "Element" AS element,
          TRY_CAST("Value" AS DOUBLE) AS value
        FROM read_parquet(?)
        """,
        [str(PROCESSED / "producer_prices_annual_long.parquet")],
    )
    con.execute(
        f"""
        COPY (
          SELECT
            area_code, area, item_code, item, year,
            MAX(CASE WHEN element = 'Producer Price (USD/tonne)' THEN value END)
              AS producer_price_usd_per_tonne,
            MAX(CASE WHEN element = 'Producer Price Index (2014-2016 = 100)' THEN value END)
              AS producer_price_index
          FROM prices
          GROUP BY ALL
        )
        TO '{price_country_item_year}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    con.execute(
        f"""
        COPY (
          SELECT
            t.*,
            t.import_value_1000_usd + t.export_value_1000_usd AS total_trade_value_1000_usd,
            t.export_value_1000_usd - t.import_value_1000_usd AS net_trade_value_1000_usd,
            CASE
              WHEN t.import_value_1000_usd + t.export_value_1000_usd > 0
              THEN t.import_value_1000_usd /
                   (t.import_value_1000_usd + t.export_value_1000_usd)
            END AS import_share_of_two_way_trade,
            p.producer_price_usd_per_tonne,
            p.producer_price_index
          FROM read_parquet('{trade_country_item_year}') t
          LEFT JOIN read_parquet('{price_country_item_year}') p
            USING (area_code, area, item_code, item, year)
        )
        TO '{feature_output}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """,
    )
    counts = {
        "trade_country_item_year": con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{trade_country_item_year}')"
        ).fetchone()[0],
        "price_country_item_year": con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{price_country_item_year}')"
        ).fetchone()[0],
        "country_item_year_features": con.execute(
            f"SELECT COUNT(*) FROM read_parquet('{feature_output}')"
        ).fetchone()[0],
    }
    con.close()
    return counts


def export_cleaned_csvs() -> dict[str, int]:
    """Export the cleaned intermediate Parquet tables as shareable CSVs."""
    cleaned = ROOT / "data" / "cleaned"
    cleaned.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    outputs = {
        "trade_aggregate_cleaned": (
            PROCESSED / "trade_aggregate_long.parquet",
            cleaned / "trade_aggregate_cleaned.csv",
        ),
        "producer_prices_cleaned": (
            PROCESSED / "producer_prices_annual_long.parquet",
            cleaned / "producer_prices_cleaned.csv",
        ),
        "trade_matrix_cleaned": (
            PROCESSED / "trade_matrix_long.parquet",
            cleaned / "trade_matrix_cleaned.csv",
        ),
    }
    counts = {}
    for name, (source, destination) in outputs.items():
        temporary = destination.with_suffix(destination.suffix + ".part")
        if temporary.exists():
            temporary.unlink()
        con.execute(
            f"""
            COPY (SELECT * FROM read_parquet('{source}'))
            TO '{temporary}' (FORMAT CSV, HEADER, DELIMITER ',')
            """
        )
        temporary.replace(destination)
        counts[name] = con.execute(
            f"SELECT COUNT(*) FROM read_csv('{destination}', HEADER=TRUE)"
        ).fetchone()[0]
    con.close()
    return counts


def create_quality_report(config: dict, selected: pd.DataFrame, row_counts: dict[str, int]) -> None:
    report = {
        "source_snapshot": {
            "trade_aggregate": "Trade_CropsLivestock_E_All_Data_(Normalized).zip",
            "trade_detailed_matrix": "Trade_DetailedTradeMatrix_E_All_Data_(Normalized).zip",
            "producer_prices": "Prices_E_All_Data_(Normalized).zip",
            "period": [config["start_year"], config["end_year"]],
        },
        "selection": {
            "n_reporting_areas": int(len(selected)),
            "aggregate_exclusion_rule": "Area Code >= 5000 OR M49 Code contains a decimal",
            "manual_exclusions": config.get("exclude_area_codes", []),
            "ranking_metric": config["rank_metric"],
        },
        "rows_written": row_counts,
        "validation_notes": [
            "Trade values are in 1000 USD.",
            "Quantities retain their original FAOSTAT units; tonnes, animals, and counts are not mixed.",
            "Producer prices are farm-gate prices and are not international trade unit values.",
            "Missing observations are preserved as null; no imputation is performed.",
            "The bilateral CSV excludes FAOSTAT aggregate partners.",
        ],
    }
    (METADATA / "quality_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)
    config = load_config()
    selected, selected_codes = select_reporting_areas(config)
    counts = {}
    counts.update(build_aggregate_tables(selected_codes, config))
    counts.update(build_price_table(selected_codes, config))
    counts.update(build_detailed_matrix(selected_codes, config))
    counts.update(export_cleaned_csvs())
    create_quality_report(config, selected, counts)
    print(json.dumps({"selected_reporting_areas": len(selected), "rows_written": counts}, indent=2))


if __name__ == "__main__":
    main()