# Data cleaning summary

This file documents the FAOSTAT cleaning pipeline and the final, analysis-ready outputs saved in data/processed. It records what was cleaned, which script is canonical, the unified global top‑60 country filter that was applied to every dataset, which countries were excluded from each dataset because they fall outside that common 60, and recommended next steps.

---

## Canonical cleaning script

- Canonical script (kept): scripts/final_clean_raw_data.py
  - This script performs chunked, memory-safe cleaning and writes cleaned CSVs into data/processed.
  - It computes a single unified global top‑60 country set (across all input datasets) and applies that same set to every dataset.
- Wrapper/old script: scripts/clean_raw_data.py was removed; only the final script remains in the repo to avoid confusion.

## Files written to data/processed
- ConsumerPriceIndices_E_All_Data_(Normalized)_cleaned.csv
- Cost_Affordability_Healthy_Diet_(CoAHD)_E_All_Data_(Normalized)_cleaned.csv
- Prices_E_All_Data_(Normalized)_cleaned.csv
- Trade_CropsLivestock_E_All_Data_(Normalized)_cleaned.csv
- Trade_DetailedTradeMatrix_E_All_Data_(Normalized)_cleaned.csv
- combined_analysis_table.csv (standardized union/stack of the cleaned datasets)

The combined table script is: scripts/build_combined_analysis_table.py

---

## General cleaning applied across all files
- Loaded FAOSTAT main fact tables with latin1 encoding and processed in chunks to avoid memory issues.
- Trimmed whitespace, normalized Unicode and common encoding artifacts.
- Dropped empty/null values in key fields (country, year, value, item/element where present).
- Removed non-country aggregate rows (World, regional aggregates like Africa, Europe, "Americas", etc.).
- Limited each dataset to a 20‑year window based on the dataset's latest year.
- Applied a single, unified global top‑60 country filter (see below) so the same country sample is present across all files.
- Deduplicated rows and wrote cleaned CSVs with consistent quoting/UTF‑8 where possible.

---

## Unified global top‑60 country set (applied to every dataset)
The unified set is the 60 most frequently-occurring valid country names across all five FAOSTAT fact files. Using a single set guarantees consistent country membership across datasets and simplifies joins and downstream models.

Global top 60 (alphabetical):
Argentina, Australia, Austria, Belgium, Belgium-Luxembourg, Brazil, Bulgaria, Canada, Chile, China, Hong Kong SAR, China, Taiwan Province of, China, mainland, Croatia, Cyprus, Czechia, Denmark, Egypt, Estonia, Finland, France, Germany, Greece, Hungary, India, Indonesia, Ireland, Israel, Italy, Japan, Latvia, Lebanon, Lithuania, Malaysia, Mexico, Netherlands (Kingdom of the), New Zealand, Norway, Pakistan, Peru, Philippines, Poland, Portugal, Republic of Korea, Romania, Russian Federation, Saudi Arabia, Singapore, Slovakia, Slovenia, South Africa, Spain, Sri Lanka, Sweden, Switzerland, Thailand, Türkiye, Ukraine, United Arab Emirates, United Kingdom of Great Britain and Northern Ireland, United States of America

(Count = 60)

---

## Per-dataset removed countries (examples and why)
Note: a country appears in the 'removed' list below only because it did not make the unified global top‑60 set. Being removed from the cleaned files is a design choice to create a common analysis sample — it is not an indictment of data quality.

Consumer Price Indices (removed examples, 158 countries removed):
- Examples: Afghanistan; Albania; Algeria; Angola; Armenia; Azerbaijan; Bangladesh; Belarus; Bhutan; Bolivia (Plurinational State of); Bosnia and Herzegovina; Botswana; Brunei Darussalam; Cambodia; Cameroon; Chad; Colombia; Congo; Costa Rica; Cuba; Dominican Republic; many small island & lower-frequency economies.
- Why removed: CPI series exist for these countries in FAOSTAT but they are reported less frequently across the combined FAOSTAT sources and therefore did not appear among the 60 most frequent countries overall.

Cost of a Healthy Diet (removed examples, 127 countries removed):
- Examples: Albania; Algeria; Angola; Antigua and Barbuda; Armenia; Aruba; Azerbaijan; Bahamas; Bahrain; Bangladesh; Belarus; Belize; Bhutan; Bolivia; Bosnia and Herzegovina; Botswana; Brunei; Burkina Faso; Burundi; Cabo Verde; Cambodia; Cameroon; Cayman Islands; Central African Republic; Chad; China; Colombia; etc.
- Why removed: this CoAHD file is smaller in coverage for many countries; many of the smaller economies simply do not occur often enough across all datasets to be in the common set.

Prices (Producer & Consumer) (removed examples, 124 countries removed):
- Examples: Afghanistan; Albania; Algeria; Angola; Antigua and Barbuda; Armenia; Azerbaijan; Bahrain; Bangladesh; Barbados; Belarus; Belize; Benin; Bhutan; Bolivia; Bosnia and Herzegovina; Botswana; Brunei Darussalam; Burkina Faso; Burundi; Cabo Verde; Cambodia; Cameroon; Central African Republic; Chad; Colombia; Comoros; Congo; Cook Islands; Costa Rica; etc.
- Why removed: many price series are localized or sparse — several smaller or less frequently-reported markets were filtered out by the global frequency threshold.

Trade in Crops & Livestock (removed examples, 194 countries removed):
- Examples: Afghanistan; Albania; Algeria; Angola; Armenia; Azerbaijan; Bahamas; Bahrain; Bangladesh; Barbados; Belarus; Belize; Benin; Bhutan; Bolivia; Bosnia and Herzegovina; Botswana; Brunei; Burkina Faso; Burundi; Cabo Verde; Cambodia; Cameroon; Caribbean (excluding intra-trade); many region-aggregate entries (e.g., "Africa (excluding intra-trade)").
- Why removed: the trade datasets include regional aggregates and many smaller reporters; after requiring reporter AND partner to be in the common 60 (for bilateral flows), many smaller/reporting countries and aggregate labels are excluded.

Detailed Trade Matrix (removed examples, 135 countries removed):
- Examples: Afghanistan; Albania; Algeria; Angola; Antigua and Barbuda; Armenia; Azerbaijan; Bahamas; Bahrain; Bangladesh; Barbados; Belarus; Belize; Benin; Bhutan; Bolivia; Bosnia and Herzegovina; Botswana; Brunei; Burkina Faso; Burundi; Cabo Verde; Cambodia; Cameroon; Central African Republic; China, Macao SAR; Colombia; Comoros; Congo; Cook Islands; etc.
- Why removed: same reason as above; detailed bilateral flows require both reporter and partner to be in the global 60 — this removes many small or infrequent bilateral pairs.

---

## Exact removed-country lists
Full removed-country lists per dataset are available by running the script helper (this was used to compute the lists that produced the cleaned CSVs). If you want the full explicit lists written into a file (per-dataset CSV/MD), say so and I will generate them and place them in data/processed/removed_countries_by_dataset/.

---

## Repro & how to re-run the pipeline
- To recompute the unified top‑60 and regenerate cleaned files:
  - python scripts/final_clean_raw_data.py
  - This reads data/raw/* main CSVs, computes the global top-60, and writes cleaned CSVs to data/processed.
- To build the combined standardized table used for modeling (stacked/union of cleaned files):
  - python scripts/build_combined_analysis_table.py
  - Output: data/processed/combined_analysis_table.csv

---

## Recommendations / next steps
- If the objective is to include some smaller countries despite their lower global frequency, consider:
  - expanding the global sample to top‑80 or top‑100, or
  - using a per-project whitelist to ensure certain policy-relevant countries are always included.
- Harmonize country name aliases (create a canonical mapping: "United States of America" ⇄ "USA", "China, mainland" ⇄ "China") — this will increase effective coverage and reduce splitting of counts across aliases.
- Inspect Flag and Note columns before final modeling to treat estimated/suppressed values consistently.
- If doing bilateral network analysis, consider whether to keep flows where at least one side is in the top‑60 (instead of requiring both) — this keeps more edges but reduces symmetry of the sample.

---

If you want, I will now:
- 1) write the explicit per-dataset removed-country CSVs under data/processed/removed_countries_by_dataset/ (recommended), and
- 2) regenerate the combined CSV after that if you want the lists embedded in the repository for documentation.

