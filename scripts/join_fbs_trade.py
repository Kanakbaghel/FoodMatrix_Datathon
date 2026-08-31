import pandas as pd
from pathlib import Path

fbs = pd.read_csv("data/cleaned/fbs_cleaned.csv")

fbs = fbs[
    [
        "Area Code",
        "Area",
        "Year",
        "Item",
        "kcal_per_capita_day",
        "protein_g_per_capita_day",
        "fat_g_per_capita_day",
    ]
].copy()

fbs_map = {
    "Wheat and products": "Wheat",
    "Rice and products": "Rice",
    "Maize and products": "Maize",
}

fbs["Commodity"] = fbs["Item"].map(fbs_map)

fbs = fbs.rename(
    columns={
        "Area Code": "Country Code",
        "Area": "Country",
    }
)

trade = pd.read_csv("data/cleaned/trade_dependency.csv")

trade = trade[
    [
        "Reporter Country Code",
        "Reporter Countries",
        "Year",
        "Commodity",
        "dominant_partner_code",
        "dominant_partner",
        "dominant_partner_import_quantity_t",
        "total_import_quantity_t",
        "dominant_partner_import_share",
    ]
].copy()

trade = trade.rename(
    columns={
        "Reporter Country Code": "Country Code",
        "Reporter Countries": "Country",
    }
)

trade = trade[trade["Year"].between(2010, 2023)].copy()

joined = fbs.merge(
    trade,
    on=["Country Code", "Year", "Commodity"],
    how="inner",
    suffixes=("_fbs", "_trade"),
)

if "Country_fbs" in joined.columns:
    joined = joined.rename(columns={"Country_fbs": "Country"})

if "Country_trade" in joined.columns:
    joined = joined.drop(columns=["Country_trade"])

print("==========================================")
print("FBS + TRADE JOIN")
print("==========================================")
print("FBS rows:", len(fbs))
print("Trade dependency rows:", len(trade))
print("Joined rows:", len(joined))
print("Countries:", joined["Country Code"].nunique())
print("Years:", joined["Year"].min(), "-", joined["Year"].max())
print("\nCommodities:")
print(joined["Commodity"].value_counts())

print("\nMissing dependency values:")
print(joined["dominant_partner_import_share"].isna().sum())

out = Path("data/processed/fbs_trade_joined.csv")
joined.to_csv(out, index=False)

print("\nSaved:", out)
