import pandas as pd
import numpy as np
from pathlib import Path


FBS_PATH = Path("data/cleaned/fbs_cleaned.csv")
TRADE_PATH = Path("data/processed/quantity_concentration.parquet")

COMMODITIES = ["Maize", "Rice", "Wheat"]
EPSILON = 1e-3


# ------------------------------------------------------------
# 1. Load FBS and trade concentration data
# ------------------------------------------------------------

fbs = pd.read_csv(FBS_PATH)
trade = pd.read_parquet(TRADE_PATH)

fbs = fbs[fbs["Year"].between(2010, 2023)].copy()
trade = trade[trade["Year"].between(2010, 2023)].copy()

trade = trade.rename(
    columns={
        "Reporter Country Code": "Area Code",
        "Reporter Countries": "Area",
    }
)

trade = trade[
    [
        "Area Code",
        "Area",
        "Year",
        "Commodity",
        "partner_count",
        "partner_hhi",
        "top_partner_share",
    ]
].copy()


# ------------------------------------------------------------
# 2. Join FBS dependency with trade concentration
# ------------------------------------------------------------

df = fbs.merge(
    trade,
    on=["Area Code", "Year", "Commodity"],
    how="inner",
    suffixes=("_fbs", "_trade"),
)

df = df[df["Commodity"].isin(COMMODITIES)].copy()


# ------------------------------------------------------------
# 3. Keep complete component observations
# ------------------------------------------------------------

required = [
    "import_dependency_ratio",
    "partner_hhi",
    "partner_count",
    "kcal_per_capita_day",
]

df["components_complete"] = df[required].notna().all(axis=1)


# ------------------------------------------------------------
# 4. Within-commodity winsorisation + min-max normalization
# ------------------------------------------------------------

def winsorize(series):
    lower = series.quantile(0.05)
    upper = series.quantile(0.95)
    return series.clip(lower=lower, upper=upper)


def minmax(series):
    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(0.0, index=series.index)

    return (series - minimum) / (maximum - minimum)


# Initialize component columns
normalization_columns = [
    "idr_w",
    "idr_norm",
    "hhi_w",
    "hhi_norm",
    "partner_count_w",
    "partner_count_norm",
    "partner_count_risk",
]

for column in normalization_columns:
    df[column] = np.nan


valid = df["components_complete"]

# Normalize each commodity separately.
# This prevents Maize, Rice and Wheat distributions from
# being compared against each other.
for commodity in COMMODITIES:

    mask = valid & (df["Commodity"] == commodity)

    # IDR: higher = higher risk
    df.loc[mask, "idr_w"] = winsorize(
        df.loc[mask, "import_dependency_ratio"]
    )
    df.loc[mask, "idr_norm"] = minmax(
        df.loc[mask, "idr_w"]
    )

    # HHI: higher = higher risk
    df.loc[mask, "hhi_w"] = winsorize(
        df.loc[mask, "partner_hhi"]
    )
    df.loc[mask, "hhi_norm"] = minmax(
        df.loc[mask, "hhi_w"]
    )

    # Partner count: higher = lower risk
    df.loc[mask, "partner_count_w"] = winsorize(
        df.loc[mask, "partner_count"]
    )
    df.loc[mask, "partner_count_norm"] = minmax(
        df.loc[mask, "partner_count_w"]
    )

    df.loc[mask, "partner_count_risk"] = (
        1 - df.loc[mask, "partner_count_norm"]
    )


# ------------------------------------------------------------
# 5. Weighted geometric-mean commodity risk
# ------------------------------------------------------------

df["commodity_risk_score"] = np.nan

df.loc[valid, "commodity_risk_score"] = (
    (df.loc[valid, "idr_norm"] + EPSILON) ** (2 / 5)
    * (df.loc[valid, "hhi_norm"] + EPSILON) ** (2 / 5)
    * (df.loc[valid, "partner_count_risk"] + EPSILON) ** (1 / 5)
)


# ------------------------------------------------------------
# 6. Country-year coverage
# ------------------------------------------------------------

coverage = (
    df.groupby(
        ["Area Code", "Area_fbs", "Year"],
        as_index=False,
    )
    .agg(
        commodity_count=("Commodity", "nunique"),
        valid_component_count=("components_complete", "sum"),
    )
)

coverage["complete_coverage"] = (
    (coverage["commodity_count"] == 3)
    & (coverage["valid_component_count"] == 3)
)

complete_country_years = coverage[
    coverage["complete_coverage"]
].copy()

dropped_country_years = coverage[
    ~coverage["complete_coverage"]
].copy()


# ------------------------------------------------------------
# 7. Calorie-weighted country-year risk score
# ------------------------------------------------------------

valid_df = df[df["components_complete"]].copy()

# Calculate each commodity's share of the country's
# calorie supply across Maize, Rice and Wheat.
valid_df["total_selected_kcal"] = (
    valid_df.groupby(
        ["Area Code", "Area_fbs", "Year"]
    )["kcal_per_capita_day"].transform("sum")
)

valid_df["calorie_weight"] = (
    valid_df["kcal_per_capita_day"]
    / valid_df["total_selected_kcal"]
)

# Weighted commodity risk contribution
valid_df["weighted_risk"] = (
    valid_df["commodity_risk_score"]
    * valid_df["calorie_weight"]
)

country_scores = (
    valid_df.groupby(
        ["Area Code", "Area_fbs", "Year"],
        as_index=False,
    )
    .agg(
        country_risk_score=("weighted_risk", "sum"),
        commodity_count=("Commodity", "nunique"),
    )
)


# ------------------------------------------------------------
# 8. Keep scores only for complete 3/3 country-years
# ------------------------------------------------------------

country_risk = coverage.merge(
    country_scores[
        [
            "Area Code",
            "Area_fbs",
            "Year",
            "country_risk_score",
        ]
    ],
    on=["Area Code", "Area_fbs", "Year"],
    how="left",
)

country_risk.loc[
    ~country_risk["complete_coverage"],
    "country_risk_score",
] = np.nan


# ------------------------------------------------------------
# 9. Risk classification
# ------------------------------------------------------------

def risk_level(score):
    if pd.isna(score):
        return "Insufficient coverage"

    if score >= 0.75:
        return "Very High"
    elif score >= 0.50:
        return "High"
    elif score >= 0.25:
        return "Moderate"

    return "Low"


country_risk["risk_level"] = (
    country_risk["country_risk_score"].apply(risk_level)
)


# ------------------------------------------------------------
# 10. Add country risk to commodity output
# ------------------------------------------------------------

df = df.merge(
    country_risk[
        [
            "Area Code",
            "Area_fbs",
            "Year",
            "country_risk_score",
            "risk_level",
        ]
    ],
    on=["Area Code", "Area_fbs", "Year"],
    how="left",
)


# ------------------------------------------------------------
# 11. Save outputs
# ------------------------------------------------------------

commodity_out = Path(
    "data/processed/commodity_vulnerability.csv"
)

country_out = Path(
    "data/processed/country_risk.csv"
)

commodity_out.parent.mkdir(
    parents=True,
    exist_ok=True,
)

df.to_csv(commodity_out, index=False)
country_risk.to_csv(country_out, index=False)


# ------------------------------------------------------------
# 12. Validation
# ------------------------------------------------------------

print("==========================================")
print("RISK CALCULATION")
print("==========================================")

print("Joined rows:", len(df))
print("Countries:", df["Area Code"].nunique())
print(
    "Years:",
    df["Year"].min(),
    "-",
    df["Year"].max(),
)

print("\nCommodity coverage:")
print(
    df["Commodity"].value_counts().sort_index().to_string()
)

print("\nValid component rows:")
print(
    df["components_complete"].value_counts().to_string()
)

print(
    "\nComplete 3/3 country-years:",
    len(complete_country_years),
)

print(
    "Dropped country-years:",
    len(dropped_country_years),
)

print(
    "Countries with complete country-years:",
    complete_country_years["Area Code"].nunique(),
)

print("\nRisk summary:")
print(country_risk["country_risk_score"].describe())

print("\nRisk levels:")
print(country_risk["risk_level"].value_counts().to_string())

print("\nSaved:")
print(commodity_out)
print(country_out)
