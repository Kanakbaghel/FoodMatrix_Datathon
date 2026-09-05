"""Build the shared Food Balance Sheets table for dependency ratios.

Companion to build_faostat_dataset.py, in the same idiom: chunked reads,
config-driven, no imputation, original units recorded rather than assumed.

Produces data/cleaned/fbs_cleaned.csv — one row per area x commodity x year,
carrying Production, Import quantity, Export quantity, Stock Variation and
Domestic supply quantity alongside the per-capita nutrition columns, plus
import-dependency and self-sufficiency ratios computed once so every downstream
script uses the same formula.

Usage:
    python scripts/download_faostat.py      # must include FBS
    python scripts/build_fbs_dataset.py

Three things this script is careful about, each because it silently produces
wrong answers otherwise:

1. **Item taxonomy.** FBS aggregates commodities ("Wheat and products") where
   the trade matrix splits them ("Wheat", "Wheat and meslin flour"). Joining on
   raw item names returns nothing. The mapping is explicit in config, and the
   script fails loudly if an expected FBS item is absent rather than writing a
   short file.

2. **Units.** FBS quantities are published in 1000 tonnes while the trade
   matrix is in tonnes. A dependency ratio built from FBS alone is unaffected
   because the units cancel, but mixing an FBS denominator with a trade-matrix
   numerator is wrong by a factor of 1000. Quantities here are converted to
   tonnes and the source unit is recorded in the metadata report.

3. **Stock sign.** In the FAO supply identity a stock DECREASE adds to supply,
   so Stock Variation enters positively. Reversing it inverts dependency for
   large stockholders such as China and India.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
CLEANED = ROOT / "data" / "cleaned"
METADATA = ROOT / "data" / "metadata"
CONFIG = ROOT / "config" / "faostat.json"
CHUNK_SIZE = 200_000

FBS_ZIP = "FoodBalanceSheets_E_All_Data_Normalized.zip"

# FBS item -> the Commodity label the trade side uses. Kept here rather than in
# the joining script so every consumer maps the same way.
DEFAULT_ITEM_MAP = {
    "Wheat and products": "Wheat",
    "Rice and products": "Rice",
    "Maize and products": "Maize",
}

# Element name -> output column. Matched case-insensitively: FAOSTAT is not
# consistent about capitalising "quantity" between domains, and an exact-case
# filter returns zero rows with no error.
QUANTITY_ELEMENTS = {
    "production": "production",
    "import quantity": "import_quantity",
    "export quantity": "export_quantity",
    "stock variation": "stock_variation",
    "domestic supply quantity": "domestic_supply_published",
}
NUTRITION_ELEMENTS = {
    "food supply (kcal/capita/day)": "kcal_per_capita_day",
    "protein supply quantity (g/capita/day)": "protein_g_per_capita_day",
    "fat supply quantity (g/capita/day)": "fat_g_per_capita_day",
    "food supply quantity (kg/capita/yr)": "food_supply_kg_per_capita_yr",
}
ALL_ELEMENTS = {**QUANTITY_ELEMENTS, **NUTRITION_ELEMENTS}


def zip_member(path: Path, contains: str) -> str:
    with zipfile.ZipFile(path) as archive:
        matches = [n for n in archive.namelist() if contains in n and n.endswith(".csv")]
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
        yield from pd.read_csv(handle, dtype="string", chunksize=CHUNK_SIZE, low_memory=False)
    finally:
        handle.close()
        archive.close()


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def eligible_area_codes(path: Path, config: dict) -> set[str]:
    """Non-aggregate areas, using the same rule as build_faostat_dataset.py."""
    area = read_reference_table(path, "AreaCodes")
    area.columns = area.columns.str.strip()
    area["Area Code"] = area["Area Code"].astype("string").str.strip()
    area["M49 Code"] = area["M49 Code"].astype("string").str.strip()
    is_aggregate = (
        area["Area Code"].astype("int64").ge(5000)
        | area["M49 Code"].str.contains(".", regex=False, na=False)
        | area["Area Code"].isin(config.get("exclude_area_codes", []))
    )
    return set(area.loc[~is_aggregate, "Area Code"])


def collect_fbs(path: Path, config: dict, item_map: dict[str, str]) -> tuple[pd.DataFrame, dict]:
    start, end = config["start_year"], config["end_year"]
    codes = eligible_area_codes(path, config)
    wanted_items = set(item_map)

    seen_items: set[str] = set()
    seen_elements: set[str] = set()
    units: dict[str, set[str]] = {}
    kept: list[pd.DataFrame] = []

    for chunk in iter_csv_chunks(path, "All_Data"):
        seen_items.update(chunk["Item"].dropna().unique().tolist())
        seen_elements.update(chunk["Element"].dropna().unique().tolist())

        element_key = chunk["Element"].str.strip().str.lower()
        years = pd.to_numeric(chunk["Year"], errors="coerce")
        mask = (
            years.between(start, end)
            & chunk["Area Code"].astype("string").str.strip().isin(codes)
            & chunk["Item"].isin(wanted_items)
            & element_key.isin(ALL_ELEMENTS)
        )
        selected = chunk.loc[mask].copy()
        if selected.empty:
            continue
        selected["element_key"] = element_key.loc[selected.index]
        for key, unit_series in selected.groupby("element_key")["Unit"]:
            units.setdefault(key, set()).update(unit_series.dropna().unique().tolist())
        kept.append(selected)

    diagnostics = {
        "expected_items": sorted(wanted_items),
        "items_found_in_file": sorted(i for i in seen_items if i in wanted_items),
        "items_missing": sorted(wanted_items - seen_items),
        "expected_elements": sorted(ALL_ELEMENTS),
        "elements_missing": sorted(
            e for e in ALL_ELEMENTS if e not in {s.strip().lower() for s in seen_elements}
        ),
        "units_by_element": {k: sorted(v) for k, v in sorted(units.items())},
    }

    if not kept:
        raise RuntimeError(
            "No FBS rows survived the filters.\n"
            f"  Expected items:    {sorted(wanted_items)}\n"
            f"  Sample of items in file: {sorted(list(seen_items))[:15]}\n"
            "FBS renames items between releases. Check the item list above and "
            "update fbs_item_map in config/faostat.json."
        )
    if diagnostics["items_missing"]:
        raise RuntimeError(
            f"FBS items not present in this release: {diagnostics['items_missing']}\n"
            "Update fbs_item_map in config/faostat.json rather than letting the "
            "commodity silently drop out of the dependency ratio."
        )

    return pd.concat(kept, ignore_index=True), diagnostics


def to_wide(long: pd.DataFrame, item_map: dict[str, str]) -> pd.DataFrame:
    long["Value"] = pd.to_numeric(long["Value"], errors="coerce")
    long["Year"] = pd.to_numeric(long["Year"], errors="coerce").astype("Int64")
    long["column"] = long["element_key"].map(ALL_ELEMENTS)

    # FBS publishes quantities in 1000 t; the trade matrix uses t. Convert so
    # the two are mixable. Anything already in t is left alone.
    quantity_cols = set(QUANTITY_ELEMENTS.values())
    unit_lower = long["Unit"].astype("string").str.strip().str.lower()
    scale = pd.Series(1.0, index=long.index)
    scale[long["column"].isin(quantity_cols) & unit_lower.isin({"1000 t", "1000 tonnes"})] = 1000.0
    long["value_t"] = long["Value"] * scale

    wide = long.pivot_table(
        index=["Area Code", "Area", "Item", "Year"],
        columns="column",
        values="value_t",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    wide["Commodity"] = wide["Item"].map(item_map)

    for col in ALL_ELEMENTS.values():
        if col not in wide.columns:
            wide[col] = pd.NA

    # The supply identity, computed from components so that IDR and SSR share a
    # denominator. FAO's own "Domestic supply quantity" is kept alongside as a
    # cross-check rather than used as the denominator -- mixing the two is where
    # "why don't these add up?" comes from.
    #
    # Note IDR + SSR does NOT equal 1 in general. Sharing a denominator gives
    #   IDR + SSR = (production + imports) / supply = 1 + (exports - stock)/supply
    # so they sum to 1 only for a country with no exports and no stock change.
    # For a net exporter SSR exceeds 1 and the pair sums well above it. That is
    # correct behaviour, not a bug -- report one ratio or the other rather than
    # presenting them as a partition of supply.
    stock = wide["stock_variation"].fillna(0)
    supply = wide["production"] + wide["import_quantity"] - wide["export_quantity"] + stock
    wide["domestic_supply_computed"] = supply

    valid = supply > 0
    wide["import_dependency_ratio"] = pd.NA
    wide["self_sufficiency_ratio"] = pd.NA
    wide.loc[valid, "import_dependency_ratio"] = wide.loc[valid, "import_quantity"] / supply[valid]
    wide.loc[valid, "self_sufficiency_ratio"] = wide.loc[valid, "production"] / supply[valid]

    # Non-positive supply is a real signal (re-export hubs, reporting gaps), not
    # something to paper over. Left as NA and counted in the report.
    wide["supply_flag"] = "ok"
    wide.loc[~valid, "supply_flag"] = "non_positive_supply"
    wide.loc[supply.isna(), "supply_flag"] = "incomplete_components"

    ordered = [
        "Area Code", "Area", "Year", "Item", "Commodity",
        "production", "import_quantity", "export_quantity", "stock_variation",
        "domestic_supply_computed", "domestic_supply_published",
        "import_dependency_ratio", "self_sufficiency_ratio", "supply_flag",
        "kcal_per_capita_day", "protein_g_per_capita_day",
        "fat_g_per_capita_day", "food_supply_kg_per_capita_yr",
    ]
    return wide[[c for c in ordered if c in wide.columns]].sort_values(
        ["Area", "Commodity", "Year"]
    ).reset_index(drop=True)


def main() -> None:
    config = load_config()
    item_map = config.get("fbs_item_map", DEFAULT_ITEM_MAP)
    path = RAW / FBS_ZIP
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run scripts/download_faostat.py first — it must "
            "include the food_balance_sheets entry."
        )

    long, diagnostics = collect_fbs(path, config, item_map)
    wide = to_wide(long, item_map)

    CLEANED.mkdir(parents=True, exist_ok=True)
    METADATA.mkdir(parents=True, exist_ok=True)
    out = CLEANED / "fbs_cleaned.csv"
    wide.to_csv(out, index=False)

    report = {
        "source": FBS_ZIP,
        "period": [config["start_year"], config["end_year"]],
        "rows_written": int(len(wide)),
        "countries": int(wide["Area Code"].nunique()),
        "commodities": sorted(wide["Commodity"].dropna().unique().tolist()),
        "item_map": item_map,
        "supply_flag_counts": wide["supply_flag"].value_counts().to_dict(),
        "idr_missing": int(wide["import_dependency_ratio"].isna().sum()),
        "notes": [
            "Quantities converted from FBS '1000 t' to tonnes to match the trade matrix.",
            "Supply identity computed from components; FAO's published domestic "
            "supply retained separately as a cross-check.",
            "Stock Variation enters positively (a stock decrease adds to supply).",
            "No imputation. Cells with non-positive or incomplete supply are "
            "flagged and their ratios left null.",
        ],
        "diagnostics": diagnostics,
    }
    (METADATA / "fbs_quality_report.json").write_text(
        json.dumps(report, indent=2, default=str), encoding="utf-8"
    )

    print("=" * 42)
    print("FBS BUILD")
    print("=" * 42)
    print("Rows:", len(wide))
    print("Countries:", wide["Area Code"].nunique())
    print("Years:", wide["Year"].min(), "-", wide["Year"].max())
    print("Commodities:", report["commodities"])
    print("\nUnits seen per element:")
    for key, vals in diagnostics["units_by_element"].items():
        print(f"  {key:<45} {vals}")
    print("\nSupply flags:")
    for key, value in report["supply_flag_counts"].items():
        print(f"  {key:<25} {value}")
    print("\nIDR summary (where computable):")
    print(pd.to_numeric(wide["import_dependency_ratio"], errors="coerce").describe())
    print("\nSaved:", out)
    print("Report:", METADATA / "fbs_quality_report.json")


if __name__ == "__main__":
    main()
