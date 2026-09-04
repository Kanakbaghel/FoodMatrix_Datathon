# Data folder

The raw FAOSTAT zip files are local reproducibility inputs and are excluded
from normal Git commits. The cleaned CSVs are generated from them by:

```bash
python scripts/download_faostat.py
python scripts/build_faostat_dataset.py
python scripts/build_mirror_exports.py
python scripts/build_fbs_dataset.py
```

The files are intentionally kept as CSV so they can be opened by Python, R, SQL
tools, and spreadsheet/data viewers when appropriate. Since the commodity
filter replaced the 50-country cap, the largest cleaned file is about 81 MB —
well inside GitHub's limits — but treat that as a happy accident rather than a
guarantee. If a future config change widens the item list, use Git LFS, a
shared drive, or object storage instead.

## Cleaning choices

- Period: 2005–2024.
- Selection: `geography_mode: commodity_filter` — all non-aggregate reporting
  areas (209 countries), restricted to the staple items in
  `config/faostat.json`. This replaced the earlier 50-country cap, which
  ranked by trade value and so selected for large economies while excluding
  import-dependent countries such as Nigeria, Bangladesh, Pakistan and
  Ethiopia.
- Regional/FAOSTAT aggregate areas are excluded.
- The China aggregate is excluded to avoid double counting the separately
  reported mainland and territory entries.
- Self-trade rows (reporter == partner) are excluded in the pipeline.
- No missing values are filled.
- Original FAOSTAT flags, notes, and units are preserved.
- Producer prices are annual **farm-gate** prices for the producing country.
  They are not international trade prices and not what an importer pays — use
  them for exporter-side economics or validation, not as an importer cost.

## Mirror-corrected exports — how to use `recommended_value`

`mirror_exports_cleaned.csv` rebuilds export figures from partner-reported
imports for countries that stop reporting. `recommended_value` prefers a
country's own report and falls back to the mirror; `coverage_flag` records
which applies (`both_available`, `mirror_only_reporter_silent`,
`self_report_only_no_mirror`).

**Use `recommended_value` for any exporter ranking or market share.** Do not
use the raw `Export quantity` element: Russia files no export rows from 2022
onward, so an export ranking over 2022–24 shows the world's largest wheat
exporter at zero.

### The mirror undercounts, and by roughly how much

Mirror figures only capture what importing partners report, so they are a
**lower bound**. We can quantify it from our own data. Across the 17 years
where Russia *did* self-report wheat exports, comparing `mirror_value` against
`self_reported_value`:

| | mirror as % of self-reported |
|---|---|
| 2005–2021, all years | mean **66%**, median 68%, range 46–93% |
| 2017–2021, most comparable recent years | mean **75%**, range 66–82% |

Applying the 75% factor to the 2023 mirror figure of 33.96 Mt gives ~45 Mt,
which sits beside the ~44.7 Mt independently reported for that season. The
method validates against itself.

**Practical rule:** `recommended_value` is sound for **shares, rankings and
relative comparisons**, where the undercount is roughly proportional across
partners. It is **not** sound for absolute volume claims — do not put a
mirror-derived tonnage on a slide as a country's exports without noting it is a
floor.

### 2024 is the weakest year in the series

`n_partner_reports` for Russian wheat falls from 81 (2021) to 63 (2022–23) to
**42 (2024)**. The mirror thins as the panel approaches the present, so the
undercount is likely worst in the final year. Footnote 2024 wherever it is used,
and prefer 2021–23 as an analysis window where the choice is available.

## Food Balance Sheets — `fbs_cleaned.csv`

Built by `scripts/build_fbs_dataset.py`. One row per area × commodity × year,
carrying Production, Import quantity, Export quantity, Stock Variation and
Domestic supply quantity alongside the per-capita nutrition columns, plus
import-dependency and self-sufficiency ratios computed once so every downstream
script uses the same formula.

Three things it handles that silently produce wrong answers otherwise:

- **Item taxonomy.** FBS aggregates commodities ("Wheat and products") where
  the trade matrix splits them ("Wheat", "Wheat and meslin flour"). The mapping
  lives in `config/faostat.json` under `fbs_item_map`, and the build fails
  loudly with the file's actual item list if an expected item is missing —
  rather than writing a short file nobody notices.
- **Units.** FBS publishes quantities in **1000 t**; the trade matrix uses
  **t**. Quantities are converted to tonnes on the way in. A ratio built from
  FBS alone is unaffected because units cancel, but an FBS denominator under a
  trade-matrix numerator is wrong by a factor of 1000.
- **Stock sign.** A stock *decrease* adds to supply, so Stock Variation enters
  the identity positively. Reversing it inverts dependency for large
  stockholders such as China and India.

```
domestic_supply_computed = production + imports − exports + stock_variation
import_dependency_ratio  = imports    / domestic_supply_computed
self_sufficiency_ratio   = production / domestic_supply_computed
```

FAO's own published "Domestic supply quantity" is retained as
`domestic_supply_published` for cross-checking, but is not used as the
denominator — mixing the two is where "why don't these add up?" comes from.

**IDR and SSR do not sum to 1.** Sharing a denominator gives
`IDR + SSR = 1 + (exports − stock) / supply`, so they sum to 1 only where a
country has no exports and no stock change, and a net exporter's SSR
legitimately exceeds 1. Report one or the other; they are not a partition of
supply.

Rows where supply is non-positive or its components are incomplete are flagged
in `supply_flag` and their ratios left null rather than imputed. Counts are in
`data/metadata/fbs_quality_report.json`.
