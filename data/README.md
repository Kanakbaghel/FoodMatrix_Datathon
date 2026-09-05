# Data folder

The raw FAOSTAT zip files are local reproducibility inputs and are excluded
from normal Git commits. The cleaned CSVs are generated from them by:

```bash
python scripts/download_faostat.py
python scripts/build_faostat_dataset.py
```

The detailed bilateral CSV is about 2.4 GB and the aggregate trade CSV is
about 135 MB. Do not push these through ordinary Git: use Git LFS, a shared
drive, or object storage. The files are intentionally kept as CSV so they
can be opened by Python, R, SQL tools, and spreadsheet/data viewers when
appropriate.

## Cleaning choices

- Period: 2005–2024.
- Selection: 50 reporting areas ranked by 20-year import value plus export
  value.
- Regional/FAOSTAT aggregate areas are excluded.
- The China aggregate is excluded to avoid double counting the separately
  reported mainland and territory entries.
- No missing values are filled.
- Original FAOSTAT flags, notes, and units are preserved.
- Producer prices are annual farm-gate prices; they are not international
  import/export prices.