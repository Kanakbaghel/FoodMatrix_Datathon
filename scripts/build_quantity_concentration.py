import pandas as pd
from pathlib import Path

INPUT = Path("data/cleaned/trade_matrix_cleaned.csv")
OUTPUT = Path("data/processed/quantity_concentration.parquet")

df = pd.read_csv(INPUT)

# ------------------------------------------------------------
# 1. Keep import quantities only
# ------------------------------------------------------------

df = df[
    (df["Element"] == "Import quantity")
    & (df["Unit"] == "t")
    & (df["Value"] > 0)
].copy()

# ------------------------------------------------------------
# 2. Map detailed FAOSTAT items to 3 commodities
# ------------------------------------------------------------

item_map = {
    "Wheat": "Wheat",
    "Wheat and meslin flour": "Wheat",
    "Rice, paddy (rice milled equivalent)": "Rice",
    "Rice, milled": "Rice",
    "Maize (corn)": "Maize",
}

df["Commodity"] = df["Item"].map(item_map)
df = df[df["Commodity"].notna()].copy()

# ------------------------------------------------------------
# 3. Aggregate detailed items by reporter/partner/commodity/year
# ------------------------------------------------------------

flows = (
    df.groupby(
        [
            "Reporter Country Code",
            "Reporter Countries",
            "Partner Country Code",
            "Partner Countries",
            "Commodity",
            "Year",
        ],
        as_index=False,
    )["Value"]
    .sum()
    .rename(columns={"Value": "import_quantity_t"})
)

# ------------------------------------------------------------
# 4. Total imports
# ------------------------------------------------------------

totals = (
    flows.groupby(
        [
            "Reporter Country Code",
            "Reporter Countries",
            "Commodity",
            "Year",
        ],
        as_index=False,
    )["import_quantity_t"]
    .sum()
    .rename(columns={"import_quantity_t": "total_import_quantity_t"})
)

flows = flows.merge(
    totals,
    on=[
        "Reporter Country Code",
        "Reporter Countries",
        "Commodity",
        "Year",
    ],
    how="left",
)

# ------------------------------------------------------------
# 5. Supplier shares
# ------------------------------------------------------------

flows["partner_share"] = (
    flows["import_quantity_t"]
    / flows["total_import_quantity_t"]
)

# ------------------------------------------------------------
# 6. HHI
# ------------------------------------------------------------

hhi = (
    flows.assign(
        share_squared=flows["partner_share"] ** 2
    )
    .groupby(
        [
            "Reporter Country Code",
            "Reporter Countries",
            "Commodity",
            "Year",
        ],
        as_index=False,
    )["share_squared"]
    .sum()
    .rename(columns={"share_squared": "partner_hhi"})
)

# ------------------------------------------------------------
# 7. Other concentration metrics
# ------------------------------------------------------------

concentration = (
    flows.groupby(
        [
            "Reporter Country Code",
            "Reporter Countries",
            "Commodity",
            "Year",
        ],
        as_index=False,
    )
    .agg(
        partner_count=(
            "Partner Country Code",
            "nunique",
        ),
        top_partner_share=(
            "partner_share",
            "max",
        ),
        suppliers_over_5pct=(
            "partner_share",
            lambda x: (x > 0.05).sum(),
        ),
    )
)

# ------------------------------------------------------------
# 8. Identify dominant supplier
# ------------------------------------------------------------

flows["rank"] = (
    flows.groupby(
        [
            "Reporter Country Code",
            "Reporter Countries",
            "Commodity",
            "Year",
        ]
    )["partner_share"]
    .rank(
        method="first",
        ascending=False,
    )
)

top_partner = flows[flows["rank"] == 1][
    [
        "Reporter Country Code",
        "Reporter Countries",
        "Commodity",
        "Year",
        "Partner Country Code",
        "Partner Countries",
    ]
].rename(
    columns={
        "Partner Country Code": "dominant_partner_code",
        "Partner Countries": "dominant_partner",
    }
)

# ------------------------------------------------------------
# 9. Combine metrics
# ------------------------------------------------------------

out = concentration.merge(
    hhi,
    on=[
        "Reporter Country Code",
        "Reporter Countries",
        "Commodity",
        "Year",
    ],
    how="left",
)

out = out.merge(
    top_partner,
    on=[
        "Reporter Country Code",
        "Reporter Countries",
        "Commodity",
        "Year",
    ],
    how="left",
)

out = out[
    [
        "Reporter Country Code",
        "Reporter Countries",
        "Year",
        "Commodity",
        "partner_count",
        "partner_hhi",
        "top_partner_share",
        "suppliers_over_5pct",
        "dominant_partner_code",
        "dominant_partner",
    ]
].sort_values(
    [
        "Reporter Country Code",
        "Year",
        "Commodity",
    ]
)

# ------------------------------------------------------------
# 10. Save
# ------------------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

out.to_parquet(
    OUTPUT,
    index=False,
)

print("==========================================")
print("QUANTITY-BASED CONCENTRATION")
print("==========================================")
print("Input rows:", len(df))
print("Flow rows:", len(flows))
print("Output rows:", len(out))
print("Countries:", out["Reporter Country Code"].nunique())
print("Years:", out["Year"].min(), "-", out["Year"].max())

print("\nCommodities:")
print(out["Commodity"].value_counts())

print("\nSaved:", OUTPUT)
