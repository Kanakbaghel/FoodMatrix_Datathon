# Data pipeline vs Analysis 2 — design review

*Rasheed · 28 Aug 2026*
*Based on the pipeline manifest, not yet on the files themselves. Items marked
🔎 need confirming against the actual data once pulled.*

---

> **Superseded in part.** Two recommendations here were later revised against
> the real data, and are kept for traceability rather than deleted:
> producer prices as an index component (Kanak's note that they are farm-gate,
> not international prices, is correct), and the suggestion to move the base
> window to 2022-24 (that is exactly the window where Russia stops reporting).
> See `faostat_data_audit.md` for the corrected position.


## Headline: the risk index cannot be built from this dataset as it stands

**Import dependency ratio needs production data. There is no production data in
the pipeline.**

```
IDR = imports / (production + imports − exports)
                 ^^^^^^^^^^
                 not in any of the three downloaded domains
```

What shipped is three trade-and-price domains:

| Domain | What it gives | What it does not |
|---|---|---|
| Trade_CropsLivestock (TCL) | Reporter-level import/export totals and unit values | Production |
| Trade_DetailedTradeMatrix (TM) | Bilateral flows — who buys from whom | Production |
| Prices | Producer prices | Production |

Production and domestic supply live in **Food Balance Sheets (FBS)** or the
**Production: Crops and Livestock (QCL)** domain. Neither is in the config.

This is not a nice-to-have. Without dependency, the index degrades to a
concentration score — and concentration alone is not risk. A country importing
3% of its wheat from a single supplier scores identically to one importing 90%
from a single supplier. That is exactly the failure the design warned against:
*the interaction is the insight*.

### The fix, in order of preference

1. **Add FBS to the download config** — `FoodBalanceSheets_E_All_Data_(Normalized).zip`.
   Gives production, domestic supply, *and* per-capita food supply in kcal,
   which also opens up a food-security framing the trade data cannot support on
   its own. This is the right answer.
2. **Add QCL (Production: Crops and Livestock)** if FBS is too large or its
   item taxonomy does not line up. Lighter, gives production quantity, no
   supply identity.
3. **Fall back to a trade-only proxy** — net import position, or imports as a
   share of total trade. Weaker and harder to defend: it measures trade
   posture, not dependence on foreign supply. Only if 1 and 2 both fail.

**The ask for Yash:** one entry added to `config/faostat.json` and a re-run of
`download_faostat.py` + `build_faostat_dataset.py`. The pipeline already does
the work; it just is not pointed at the domain we need. Raise it today — this
sits on the critical path for Analysis 2, and analyses are due Aug 29.

---

## Second issue: the 50-area filter may exclude the story

The cleaned data covers **50 high-trade reporting areas**. That is a sensible
engineering decision — it cuts 24.7M rows to something workable — but it has a
consequence worth deciding on deliberately rather than inheriting.

**"High-trade" selects for large economies.** The countries that make the most
compelling food-import-risk story are usually the opposite: small, highly
import-dependent, thin fiscal buffers, few suppliers. Yemen, Haiti, Somalia,
Afghanistan, Lebanon, much of the Sahel. If they are not in the 50, a risk
ranking over the remaining set is substantially a ranking of large economies
by how much they trade — which is a much less interesting finding and one that
invites the "isn't this just measuring size?" question.

🔎 **Check first:** read `data/metadata/top50_reporting_areas_2005_2024.csv`
and see who is actually in it before assuming. The selection may be broader
than the label suggests.

**Two things to note about how the filter interacts with the trade matrix:**

- If the 50 are *reporters* but partners are unrestricted, then bilateral flows
  into and out of the 50 are largely intact, and concentration metrics for
  those 50 are computable. Good.
- But the **mirror-flow convention gets asymmetric.** For a flow between a
  top-50 importer and a non-top-50 exporter, only the importer's report exists;
  reverse the roles and only the exporter's exists. The importer-preference
  rule still works, but the *share of flows where both sides reported* will
  differ systematically between country groups. Report that share by group,
  not just overall.
- For **network analysis** this matters more. A network of 50 reporters plus
  their partners is not the global food trade network; second-order exposure
  through a non-reporting intermediary will be invisible. 🔎 Check whether
  partner countries are unrestricted in the cleaned matrix — if they are, the
  network is usable with a stated caveat; if partners are also capped at the
  50, the second clause of the research question is not answerable as written.

**Proposed resolution:** keep the 50 for the headline analysis (defensible,
tractable, and the data is already built), and ask Yash whether adding a second
tier — say 30–40 high-import-dependency countries regardless of trade volume —
is cheap. If it is one more config entry, it is worth it. If it means
re-engineering, keep the 50 and state the limitation.

---

## Third: producer prices are an unused asset

The Prices domain is in the pipeline and does not appear anywhere in the
Analysis 2 design. It should. Two candidate uses, both cheap:

**As a fourth index component — price volatility exposure.** Coefficient of
variation of the relevant producer price over the period. A country dependent
on a commodity whose price swings hard is exposed even when supply is
physically available, because affordability is the binding constraint. This
adds a dimension genuinely independent of the other three, which is exactly
what the collinearity problem needs.

**As external validation.** If the risk index is measuring something real,
high-scoring countries should show larger price responses around known
disruption events — 2008, 2011, 2022. That is a proper out-of-sample check
rather than another correlation with our own inputs, and it is the strongest
validation available in this dataset.

🔎 Check coverage first: producer prices at 145k rows across 50 areas and 20
years is thin, and FAOSTAT producer price coverage is patchy for exactly the
countries most at risk. If coverage is poor, use it for validation only, not
as a component.

---

## What does not change

- **Mirror-flow convention** — importer-preferred, exporter fallback. Still
  correct, still needs the robustness check under the alternative.
- **Aggregates excluded** — already done in the pipeline. Verify by confirming
  no row resolves to a regional group. 🔎
- **Flags and missing values preserved** — good, and it means we can report the
  official-vs-estimated share as planned. This was the right call by Yash.
- **Original units kept** — so quantity is in tonnes and value in 1000 US$.
  Keep using quantity for dependency and concentration.
- **2005–2024** — comfortably supports a 3-year mean and gives a long enough
  trend for context. Use 2021–23 or 2022–24 as the base window. 🔎 confirm
  2024 is complete rather than partial; the most recent FAOSTAT year often is
  not, and a half-reported year in a 3-year mean is a silent error.

---

## Revised component set

| # | Component | Status |
|---|---|---|
| 1 | Import dependency ratio | **Blocked** — needs FBS or QCL added to the pipeline |
| 2 | Supplier concentration (HHI) | Ready — TM has what it needs |
| 3 | Supplier fragility (weighted supplier centrality) | Ready, subject to the partner-coverage check 🔎 |
| 4 | Price volatility exposure | Candidate — subject to coverage check 🔎 |

If component 1 stays blocked past **Aug 26**, switch to the trade-only proxy
and say so explicitly in the methodology rather than quietly redefining
dependency. A stated compromise is defensible; an unstated one is not.

---

## Immediate actions

| # | Action | Owner | By |
|---|---|---|---|
| 1 | Add FBS (or QCL) to `config/faostat.json`, re-run the pipeline | Yash | Aug 25 |
| 2 | Confirm whether partner countries are capped at the 50 in the cleaned matrix | Yash | Aug 25 |
| 3 | Read `top50_reporting_areas_2005_2024.csv`; decide whether a dependency-weighted second tier is worth adding | Rasheed + Yash | Aug 26 |
| 4 | Confirm 2024 completeness; fix the base window | Rasheed | Aug 26 |
| 5 | Check producer-price coverage; decide component vs validation-only | Rasheed | Aug 26 |
| 6 | Add `networkx` and `scipy` to `requirements.txt` | Rasheed | now |
