# Analysis 2 — first cut on the real data

*Rasheed · 28 Aug 2026 · run against `data/cleaned/trade_matrix_cleaned.csv` (24,719,738 rows)*
*Reproduce with `scripts/rasheed/wheat_exposure_firstcut.py`.*

Six findings, all measured rather than assumed. Two of them change the plan.

---

## 1. The dependency blocker, demonstrated

Ranking the 50 reporters by wheat supplier concentration alone, 2021–23 mean:

| # | Country | Imports (kt) | HHI | Eff. suppliers | Top partner |
|---|---|---|---|---|---|
| 1 | New Zealand | 616 | 1.000 | 1.0 | Australia (100%) |
| 2 | **Russian Federation** | 123 | 0.945 | 1.1 | Kazakhstan (97%) |
| 3 | **Canada** | 129 | 0.932 | 1.1 | United States (97%) |
| 4 | **United States** | 1,929 | 0.805 | 1.2 | Canada (90%) |
| 5 | Mexico | 4,423 | 0.656 | 1.5 | United States (80%) |

Three of the top four are among the world's largest wheat **exporters**. Their
tiny import volumes happen to come from one neighbour, so a concentration
measure flags them as maximally exposed. Russia — the largest wheat exporter on
earth — ranks second on wheat import risk.

This is the argument from the design doc, now with numbers: **concentration
without dependency is not risk.** If the index ships without a dependency
component, this is the ranking it produces.

## 2. A usable stopgap until Food Balance Sheets arrive

Filtering to net importers and computing **import intensity** =
imports ÷ (imports + exports) produces a defensible ranking from trade data alone:

| Country | Imports (kt) | Net (kt) | Intensity | HHI | Eff. sup. | Top partner |
|---|---|---|---|---|---|---|
| Mexico | 4,423 | 4,236 | 0.96 | 0.656 | 1.5 | United States |
| Taiwan | 1,273 | 1,273 | 1.00 | 0.615 | 1.6 | United States |
| Türkiye | 10,053 | 8,873 | 0.90 | 0.551 | 1.8 | Russian Federation |
| Viet Nam | 4,516 | 4,475 | 0.99 | 0.423 | 2.4 | Australia |
| Japan | 5,166 | 5,166 | 1.00 | 0.351 | 2.9 | United States |
| **Egypt** | 7,547 | 7,545 | 1.00 | 0.346 | 2.9 | Russian Federation |
| Philippines | 6,083 | 6,083 | 1.00 | 0.342 | 2.9 | United States |

Excluded as net exporters: United States, France, Romania, Poland, Germany,
Hungary — exactly the countries that polluted the ranking above.

**Egypt now lands where it should:** 7.5 Mt of wheat, no exports, effectively
2.9 suppliers, largest of them Russia. That is the story from 2022, recovered
from the data.

**Import intensity is not the import dependency ratio.** It separates importers
from exporters and re-export hubs, but it says nothing about how much of
domestic supply is home-grown — a country producing 90% of its own wheat and
importing the rest from one source scores identically to one importing
everything. It is a stopgap. **Adding FBS remains the single highest-value
change to the pipeline.**

## 3. A real re-export artefact, caught in the data

Iran's largest maize supplier is the **United Arab Emirates, at 60%**.

The UAE does not grow maize at meaningful scale. This is transshipment being
recorded as origin, and it corrupts two things at once: it overstates Iran's
concentration on a partner that is not a producer, and it will inflate the
UAE's centrality in the trade network — making a logistics hub look like a
systemic food supplier.

Decide the handling before the network analysis runs, not after: either
annotate hub partners explicitly, or trace flows through them where the data
allows. Netherlands, Belgium, Singapore, Hong Kong and the UAE are all in the
50, so this will recur.

## 4. Small single-neighbour importers top the ranking mechanically

New Zealand imports 616 kt of wheat, all of it from Australia, and therefore
scores a perfect 1.000 HHI. That is geography, not exposure — there is one
plausible supplier within economic reach and it is a stable ally.

Weight by volume, or by per-capita supply, before letting concentration drive
the headline. Otherwise the index's top finding is a country nobody worries
about.

## 5. Two schema facts that break naive code

- **Element names use a lowercase q:** `Import quantity`, `Export quantity`,
  `Import value`, `Export value`. Not `Import Quantity`. A filter on the
  capitalised form returns zero rows silently.
- **Export rows outnumber import rows** — 7.09M vs 5.32M for quantity. The 50
  reporters report more outbound flows than inbound, so under the
  importer-preferred mirror convention a substantial share of flows will fall
  back to the exporter's figure. Report that share by group rather than
  overall.

## 6. Two open questions closed

**2024 is complete.** Row counts by year: 2021: 1,493,411 · 2022: 1,470,004 ·
2023: 1,461,802 · **2024: 1,431,899**. The last year is in line with its
neighbours, not a partial release. A **2022–24** base window is available and
is the more current choice.

**The commodity filter is confirmed as the right cut.** The file carries **521
items** across 50 reporters and 202 partners. The staples are a rounding error
within it:

| Item | Rows |
|---|---|
| Rice, paddy (rice milled equivalent) | 135,714 |
| Wheat and meslin flour | 123,650 |
| Rice, milled | 113,348 |
| Maize (corn) | 104,958 |
| Wheat | 80,636 |

Roughly **435k rows out of 24.7M — under 2%.** Keeping the staples across *all*
~190 reporting countries would yield on the order of 1.6M rows: about **15×
smaller than the current file**, while covering every country the analysis is
actually about. The country cap is doing work the commodity filter should do,
and it is doing it at the cost of the countries that matter.

⚠ Item names must be taken verbatim. It is `Maize (corn)`, not `Maize`. And a
naive `LIKE '%rice%'` match pulls in *"Communion wafers … rice paper and
similar products"*, which is a good reminder to enumerate items explicitly
rather than pattern-match them.

---

## What changes

| # | Change | Owner | Why |
|---|---|---|---|
| 1 | Add Food Balance Sheets to the pipeline | Kanak/Yash | Without it the index ranks Russia and Canada as high-risk wheat importers |
| 2 | Swap the country cap for a commodity filter | Kanak/Yash | 15× smaller, and it restores Nigeria, Bangladesh, Pakistan, Ethiopia, Morocco |
| 3 | Use import intensity as an interim dependency proxy | Rasheed/Moksh | Unblocks Analysis 2 now; replaced by IDR when FBS lands |
| 4 | Decide re-export hub handling before the network runs | Rasheed/Kemisola | UAE at 60% of Iran's maize is not a supply relationship |
| 5 | Weight concentration by volume or per-capita supply | Rasheed | Otherwise New Zealand leads the risk ranking |
| 6 | Move the base window to 2022–24 | Rasheed | 2024 is complete; more current, same robustness |
