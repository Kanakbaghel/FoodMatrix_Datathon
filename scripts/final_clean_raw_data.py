import pandas as pd
from pathlib import Path

RAW_BASE = Path("data/raw")
OUT_BASE = Path("data/processed")
OUT_BASE.mkdir(parents=True, exist_ok=True)

HIGHLIGHT_COUNTRIES = {
    "India", "United States of America", "China, mainland", "Brazil", 
    "Germany", "France", "Argentina", "Indonesia", "Russian Federation", 
    "Australia", "Canada", "Japan", "Mexico", "United Kingdom", "Nigeria", 
    "South Africa", "Egypt", "Ukraine", "Türkiye", "Turkey", "Viet Nam", "Thailand"
}

def clean_and_process():
    trade_file = RAW_BASE / "Trade_DetailedTradeMatrix_E_All_Data_(Normalized).csv"
    price_file = RAW_BASE / "Prices_E_All_Data_(Normalized).csv"

    print(f"Pass 1: Calculating country trade volumes from {trade_file.name}...")
    
    # Calculate volume in chunks to avoid memory crash
    reporter_vol = pd.Series(dtype=float)
    partner_vol = pd.Series(dtype=float)
    
    chunksize = 200_000
    for chunk in pd.read_csv(trade_file, encoding="latin1", chunksize=chunksize, usecols=["Reporter Countries", "Partner Countries", "Value"]):
        chunk = chunk.dropna(subset=["Value"])
        
        r_sum = chunk.groupby("Reporter Countries")["Value"].sum()
        p_sum = chunk.groupby("Partner Countries")["Value"].sum()
        
        reporter_vol = reporter_vol.add(r_sum, fill_value=0)
        partner_vol = partner_vol.add(p_sum, fill_value=0)

    total_volume = reporter_vol.add(partner_vol, fill_value=0).sort_values(ascending=False)
    top_volume_countries = set(total_volume.head(50).index)
    target_countries = top_volume_countries.union(HIGHLIGHT_COUNTRIES)
    print(f"Filter created: {len(target_countries)} countries selected by trade volume.")

    print(f"\nPass 2: Filtering and saving Trade Matrix...")
    trade_out = OUT_BASE / "Trade_DetailedTradeMatrix_cleaned.csv"
    
    first_chunk = True
    for chunk in pd.read_csv(trade_file, encoding="latin1", chunksize=chunksize, low_memory=False):
        chunk = chunk.dropna(subset=["Reporter Countries", "Partner Countries", "Year", "Value"])
        
        cleaned_chunk = chunk[
            chunk["Reporter Countries"].isin(target_countries) | 
            chunk["Partner Countries"].isin(target_countries)
        ]
        
        cleaned_chunk.to_csv(trade_out, mode='w' if first_chunk else 'a', header=first_chunk, index=False)
        first_chunk = False
        
    print(f"Saved Trade Matrix to: {trade_out}")

    print(f"\nReading Producer Prices: {price_file.name}...")
    df_prices = pd.read_csv(price_file, encoding="latin1", low_memory=False)
    df_prices = df_prices.dropna(subset=["Area", "Year", "Value"])
    
    if "Element" in df_prices.columns:
        df_prices = df_prices[
            df_prices["Element"].str.contains("USD", na=False) | 
            df_prices["Element"].str.contains("tonne", na=False)
        ]
        
    df_prices_cleaned = df_prices[df_prices["Area"].isin(target_countries)]
    
    price_out = OUT_BASE / "Prices_cleaned.csv"
    df_prices_cleaned.to_csv(price_out, index=False)
    print(f"Saved Producer Prices to: {price_out}")

if __name__ == "__main__":
    clean_and_process()

