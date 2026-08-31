import pandas as pd
from pathlib import Path

df = pd.read_csv("data/cleaned/fbs_trade_joined.csv")

required = [
    "Country Code",
    "Country",
    "Year",
    "Commodity",
    "dominant_partner",
    "dominant_partner_import_share",
    "kcal_per_capita_day",
    "protein_g_per_capita_day",
    "fat_g_per_capita_day",
]

missing = [column for column in required if column not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df["dominant_partner_import_share"] = (
    df["dominant_partner_import_share"].fillna(0)
)

total_kcal = (
    df.groupby(
        ["Country Code", "Country", "Year"],
        as_index=False,
    )["kcal_per_capita_day"]
    .sum()
    .rename(
        columns={
            "kcal_per_capita_day": "total_kcal_3commodities"
        }
    )
)

df = df.merge(
    total_kcal,
    on=["Country Code", "Country", "Year"],
    how="left",
)

df["food_importance"] = (
    df["kcal_per_capita_day"]
    / df["total_kcal_3commodities"]
)

df.loc[
    df["total_kcal_3commodities"] <= 0,
    "food_importance",
] = 0

df["commodity_vulnerability"] = (
    df["dominant_partner_import_share"]
    * df["food_importance"]
)

country_risk = (
    df.groupby(
        ["Country Code", "Country", "Year"],
        as_index=False,
    )["commodity_vulnerability"]
    .sum()
    .rename(
        columns={
            "commodity_vulnerability": "country_risk_score"
        }
    )
)

df = df.merge(
    country_risk,
    on=["Country Code", "Country", "Year"],
    how="left",
)

def risk_level(score):
    if score >= 0.75:
        return "Very High"
    elif score >= 0.50:
        return "High"
    elif score >= 0.25:
        return "Moderate"
    return "Low"

df["risk_level"] = df["country_risk_score"].apply(risk_level)

commodity_out = Path(
    "data/cleaned/commodity_vulnerability.csv"
)

country_out = Path(
    "data/cleaned/country_risk.csv"
)

df.to_csv(commodity_out, index=False)
country_risk.to_csv(country_out, index=False)

print("==========================================")
print("RISK CALCULATION")
print("==========================================")
print("Rows:", len(df))
print("Countries:", df["Country Code"].nunique())
print("Years:", df["Year"].min(), "-", df["Year"].max())

print("\nRisk score statistics:")
print(country_risk["country_risk_score"].describe())

print("\nRisk levels:")
print(
    df[["Country Code", "Year", "risk_level"]]
    .drop_duplicates()["risk_level"]
    .value_counts()
)

print("\nSaved:")
print("Commodity file:", commodity_out)
print("Country risk file:", country_out)
