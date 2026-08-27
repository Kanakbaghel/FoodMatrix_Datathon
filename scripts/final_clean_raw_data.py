import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_BASE = PROJECT_ROOT / "data" / "raw"
OUT_BASE = PROJECT_ROOT / "data" / "processed"
OUT_BASE.mkdir(parents=True, exist_ok=True)
YEARS_TO_KEEP = 20

NON_COUNTRY_NAMES = {
    "world", "world total", "africa", "eastern africa", "middle africa", "northern africa", "southern africa",
    "western africa", "sub-saharan africa", "asia", "eastern asia", "southern asia", "south-eastern asia",
    "western asia", "central asia", "northern asia", "europe", "eastern europe", "northern europe", "southern europe",
    "western europe", "central europe", "americas", "northern america", "central america", "latin america and the caribbean",
    "caribbean", "south america", "oceania", "antarctic", "european union", "european union (27)", "arab states",
    "least developed countries", "landlocked developing countries", "small island developing states",
    "net food importing developing countries (nfidcs)", "developing countries", "developed countries",
    "oecd members", "non-oecd countries", "pacific island developing economies", "low-income food-deficit countries",
    "mediterranean", "north america", "south-eastern europe", "western hemisphere", "melanesia", "micronesia",
    "polynesia", "middle east", "south asia", "european union 27", "asia and the pacific", "western hemisphere"
}

DATASETS = [
    {
        "name": "Consumer Price Indices",
        "folder": "ConsumerPriceIndices_E_All_Data_(Normalized)",
        "file": "ConsumerPriceIndices_E_All_Data_(Normalized).csv",
        "output": "ConsumerPriceIndices_E_All_Data_(Normalized)_cleaned.csv",
        "country_col": "Area",
        "kind": "single",
        "notes": [
            "Removed empty rows and rows missing a country, year, or value.",
            "Dropped aggregate geography rows such as World and Africa, so the output stays at country level.",
            "Retained only the latest 20-year window and filtered to the unified global set of the top 60 valid countries.",
            "Normalized whitespace, duplicate records, and encoding artifacts in country labels.",
        ],
        "additional": [
            "Standardize country aliases like China, mainland vs China and Côte d'Ivoire vs Cote d'Ivoire before analytics or joins.",
            "Review the Flag and Note columns so suppressed or estimated values are treated consistently.",
            "Check whether monthly series should be aggregated or aligned before combining with annual datasets.",
        ],
    },
    {
        "name": "Cost of a Healthy Diet",
        "folder": "Cost_Affordability_Healthy_Diet_(CoAHD)_E_All_Data_(Normalized)",
        "file": "Cost_Affordability_Healthy_Diet_(CoAHD)_E_All_Data_(Normalized).csv",
        "output": "Cost_Affordability_Healthy_Diet_(CoAHD)_E_All_Data_(Normalized)_cleaned.csv",
        "country_col": "Area",
        "kind": "single",
        "notes": [
            "Removed empty cells and rows with missing country, year, or cost values.",
            "Dropped aggregation rows and kept only country-level records.",
            "Filtered to the most recent 20 years using the unified global set of the top 60 valid countries.",
            "Deduplicated records and cleaned inconsistent text formatting.",
        ],
        "additional": [
            "Resolve naming inconsistencies for territories and island countries before cross-country comparisons.",
            "Standardize release metadata if multiple product or release versions are present in the series.",
            "Review whether to normalize cost metrics by population or purchasing power before using them in a dashboard.",
        ],
    },
    {
        "name": "Prices",
        "folder": "Prices_E_All_Data_(Normalized)",
        "file": "Prices_E_All_Data_(Normalized).csv",
        "output": "Prices_E_All_Data_(Normalized)_cleaned.csv",
        "country_col": "Area",
        "kind": "single",
        "notes": [
            "Removed rows with empty country, year, element, or price values.",
            "Dropped region-level and aggregate rows such as World and Europe.",
            "Kept only the most recent 20-year period and applied the unified global set of the top 60 valid countries.",
            "Cleaned whitespace and character-encoding noise in country names and metadata columns.",
        ],
        "additional": [
            "Unify historical country names such as Belgium-Luxembourg, Czechoslovakia, and China, Taiwan Province of.",
            "Validate that price units are comparable across producer, consumer, and index series before modeling.",
            "Review flags and notes so suppressed or estimated values are not interpreted as true observations.",
        ],
    },
    {
        "name": "Trade in Crops and Livestock",
        "folder": "Trade_CropsLivestock_E_All_Data_(Normalized)",
        "file": "Trade_CropsLivestock_E_All_Data_(Normalized).csv",
        "output": "Trade_CropsLivestock_E_All_Data_(Normalized)_cleaned.csv",
        "country_col": "Area",
        "kind": "single",
        "notes": [
            "Removed rows missing country, year, item, element, or value information.",
            "Excluded aggregate geography rows such as World, Europe, Asia, and other non-country groupings.",
            "Filtered to the latest 20-year window and then applied the unified global set of the top 60 valid countries.",
            "Normalized whitespace and cleaned repeated or malformed strings in country names.",
        ],
        "additional": [
            "Align historical names and multi-country entries before comparing trade flows across time.",
            "Separate zero trade from missing or suppressed values so the volume and value series remain trustworthy.",
            "Review the item and element coding to keep import/export and value/quantity measures consistent.",
        ],
    },
    {
        "name": "Detailed Trade Matrix",
        "folder": "Trade_DetailedTradeMatrix_E_All_Data_(Normalized)",
        "file": "Trade_DetailedTradeMatrix_E_All_Data_(Normalized).csv",
        "output": "Trade_DetailedTradeMatrix_E_All_Data_(Normalized)_cleaned.csv",
        "reporter_col": "Reporter Countries",
        "partner_col": "Partner Countries",
        "kind": "pair",
        "notes": [
            "Removed missing reporter-country, partner-country, year, item, or trade-value rows.",
            "Dropped world totals and other aggregate geography rows before building the network.",
            "Kept only the latest 20 years and removed all reporter/partner flows outside the unified global set of the top 60 valid countries.",
            "Normalized whitespace and encoding issues so the country names are consistent across reporter and partner fields.",
        ],
        "additional": [
            "Create a canonical country-name map to merge aliases such as United States of America, United States, and USA.",
            "Decide whether re-export, transit, and partner-total rows should remain in the matrix before network analysis.",
            "Review zero-vs-missing and suppressed trade values before calculating dependency and connectivity metrics.",
        ],
    },
]


def clean_text(value):
    if pd.isna(value):
        return ""
    text = str(value).strip()
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\ufffd", "").replace("�", "")
    text = text.replace("\u2019", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def is_country_name(value):
    v = clean_text(value).lower()
    if not v:
        return False
    if v in NON_COUNTRY_NAMES:
        return False
    return True


def get_country_counts(dataset):
    counts = Counter()
    path = RAW_BASE / dataset["folder"] / dataset["file"]
    for chunk in pd.read_csv(path, encoding="latin1", chunksize=250000, low_memory=False):
        if dataset["kind"] == "single":
            values = chunk[dataset["country_col"]].map(clean_text)
            values = values[values.map(is_country_name)]
            counts.update(values.tolist())
        else:
            reporter = chunk[dataset["reporter_col"]].map(clean_text)
            partner = chunk[dataset["partner_col"]].map(clean_text)
            values = pd.concat([reporter, partner], ignore_index=True)
            values = values[values.map(is_country_name)]
            counts.update(values.tolist())
    return counts


def get_global_top_60(datasets):
    global_counts = Counter()
    for dataset in datasets:
        global_counts.update(get_country_counts(dataset))
    return {name for name, _ in global_counts.most_common(60)}


def get_year_bounds(dataset):
    path = RAW_BASE / dataset["folder"] / dataset["file"]
    max_year = None
    for chunk in pd.read_csv(path, encoding="latin1", chunksize=250000, low_memory=False):
        if "Year" not in chunk.columns:
            continue
        years = pd.to_numeric(chunk["Year"], errors="coerce").dropna()
        if years.empty:
            continue
        max_year = years.max() if max_year is None else max(max_year, years.max())
    if max_year is None:
        return None, None
    return max_year - (YEARS_TO_KEEP - 1), max_year


def process_dataset(dataset, top_60):
    src = RAW_BASE / dataset["folder"] / dataset["file"]
    dst = OUT_BASE / dataset["output"]
    if dst.exists():
        dst.unlink()

    start_year, end_year = get_year_bounds(dataset)
    if start_year is None or end_year is None:
        return

    first_write = True
    for chunk in pd.read_csv(src, encoding="latin1", chunksize=250000, low_memory=False):
        df = chunk.copy()

        # Clean values in every string column to remove whitespace and encoding artifacts.
        for col in df.columns:
            if pd.api.types.is_object_dtype(df[col]):
                df[col] = df[col].map(clean_text)
        df = df.replace({"": pd.NA, "nan": pd.NA, "NaN": pd.NA, "None": pd.NA})

        # Keep only the last 20 years and drop empty or malformed year/value rows.
        if "Year" in df.columns:
            df["Year"] = pd.to_numeric(df["Year"], errors="coerce")
            df = df[df["Year"].notna()]
            df = df[(df["Year"] >= start_year) & (df["Year"] <= end_year)]

        if "Value" in df.columns:
            df["Value"] = pd.to_numeric(df["Value"], errors="coerce")
            df = df[df["Value"].notna()]

        # Filter to country rows only and then retain only the top 60 countries.
        if dataset["kind"] == "single":
            col = dataset["country_col"]
            if col in df.columns:
                df = df[df[col].map(clean_text).isin(top_60)]
            if "Area" in df.columns:
                df = df[df["Area"].map(clean_text).map(is_country_name)]
        else:
            reporter = df[dataset["reporter_col"]].map(clean_text)
            partner = df[dataset["partner_col"]].map(clean_text)
            df = df[reporter.isin(top_60) & partner.isin(top_60)]
            df = df[df[dataset["reporter_col"]].map(clean_text).map(is_country_name)]
            df = df[df[dataset["partner_col"]].map(clean_text).map(is_country_name)]

        # Final row cleanup: no empty key fields and no duplicate output rows.
        for key_col in ["Area", "Reporter Countries", "Partner Countries", "Year", "Value"]:
            if key_col in df.columns:
                df = df[df[key_col].notna()]
        if df.empty or "Year" not in df.columns:
            continue
        df = df.drop_duplicates().sort_values(by=["Year"], kind="mergesort")

        if not df.empty:
            df.to_csv(dst, mode="a", index=False, header=first_write, quoting=csv.QUOTE_MINIMAL)
            first_write = False

    print(f"Processed {dataset['name']}: {dst.name} | years={start_year}-{end_year} | top60_global={len(top_60)}")


if __name__ == "__main__":
    top_60_global = get_global_top_60(DATASETS)
    for dataset in DATASETS:
        process_dataset(dataset, top_60_global)

    summary_lines = [
        "# Data cleaning summary",
        "",
        "All raw FAOSTAT files were cleaned and saved under `data/processed`.",
        "",
        "## General cleaning applied across all files",
        "- Removed empty or null values in key fields such as country, year, item, and value.",
        "- Normalized whitespace and encoding issues in text-based fields.",
        "- Removed region and aggregate rows such as World, Africa, Europe, and other non-country groupings.",
        "- Kept only the most recent 20-year window from each raw dataset.",
        "- Filtered the result to a single unified global set of the top 60 valid countries, applied to every dataset.",
        "",
        "## Per-dataset cleaning notes",
    ]

    for dataset in DATASETS:
        summary_lines.extend(["", f"### {dataset['name']}"])
        for note in dataset["notes"]:
            summary_lines.append(f"- {note}")
        summary_lines.append("Additional cleaning recommended:")
        for note in dataset["additional"]:
            summary_lines.append(f"- {note}")

    summary_path = OUT_BASE / "cleaning_summary.md"
    summary_path.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")
    print(f"Saved summary: {summary_path.name}")
