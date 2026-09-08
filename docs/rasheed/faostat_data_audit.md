# FAOSTAT data audit — what it says, and what is wrong with it

*Rasheed · 28 Aug 2026*
*Full scan of `data/cleaned/trade_matrix_cleaned.csv`, 24,719,738 rows, converted to Parquet for querying. Every figure below is measured.*

---

# Part 1 — What the data says

## 1.1 Rice is the chokepoint story, not wheat

Share of reported milled-rice exports, 2022–24:

| Exporter | Share |
|---|---|
| **India** | **49.2%** |
| Thailand | 22.3% |
| Viet Nam | 12.6% |
| China, mainland | 4.2% |

One country supplies close to half of traded milled rice. Compare wheat, where
the largest reported exporter holds 17.7%, and maize, where the US holds 29.8%.

And the countries buying it are heavily committed to that one source:

| Importer | Rice imports (kt) | From India |
|---|---|---|
| Viet Nam | 235 | 88.5% |
| Egypt | 207 | 84.9% |
| **Saudi Arabia** | **1,433** | **75.3%** |
| United Arab Emirates | 627 | 69.7% |
| Iran | 1,751 | 49.3% |
| Singapore | 395 | 40.3% |

This is the strongest finding available in the dataset, and it comes with its
own proof-of-concept: **India restricted rice exports in 2023.** The
vulnerability the analysis measures has already been demonstrated live, by the
exact country the data identifies. Saudi Arabia at 1.4 Mt and 75% from a single
supplier that has recently shown it will close the tap is a headline finding.

Note the sample limitation still bites: the countries *most* exposed to Indian
rice — Bangladesh, Nepal, West Africa — are not among the 50 reporters. What we
can see is the visible tip.

## 1.2 The 2022 disruption made two countries *more* concentrated, not less

Top-supplier share of wheat imports, and effective number of suppliers:

| | 2018 | 2021 | 2022 | 2023 | 2024 |
|---|---|---|---|---|---|
| **Türkiye** — share from Russia | 83.7% | 70.3% | 70.6% | 75.5% | **83.6%** |
| Türkiye — effective suppliers | 1.4 | 1.9 | 1.8 | 1.6 | **1.4** |
| **Egypt** — share from Russia | 73.6% | 47.1% | 51.2% | 67.4% | **68.8%** |
| Egypt — effective suppliers | 1.8 | 3.0 | 3.1 | 2.1 | **2.0** |

This is counter-intuitive and it is the most interesting thing in the data.
The conventional story is that the Black Sea disruption pushed importers to
diversify. Both of these countries did the opposite: they diversified
*briefly* in 2021–22 and then re-concentrated hard on Russia, ending 2024 more
dependent than they were in 2018.

Türkiye now effectively has **1.4 wheat suppliers**. Egypt has 2.0.

That reframes the whole risk narrative from "a shock happened and markets
adapted" to "a shock happened, exposure briefly fell, and then it came back
worse." It is a better story than the one we planned to tell, and it is
defensible from the data.

## 1.3 Wheat looks diversified — but see flaw 2.1 before believing it

Reported wheat exports 2022–24: Australia 17.7%, Canada 15.9%, US 13.8%,
France 11.1%. That reads as a healthy, competitive market.

**It is an artefact.** Russia — the world's largest wheat exporter — appears
nowhere in that ranking. See below.

---

# Part 2 — Flaws

## 2.1 CRITICAL: Russia stopped reporting after 2021

Russia's self-reported wheat export rows, by year:

| Year | Rows | Reported |
|---|---|---|
| 2021 | 87 | 27,263 kt |
| **2022** | **0** | **—** |
| **2023** | **0** | **—** |
| **2024** | **0** | **—** |

Russia is the **only one of the 50 reporters** that is completely silent on
exports for 2022–24. Meanwhile its partners report importing **56,443 kt** of
Russian wheat over the same window — more than any other origin, including
Australia.

**The trap.** Any analysis built on the export element over a 2022–24 window
shows Russian wheat exports going to zero. A reasonable analyst would write:
*"Russian wheat exports collapsed after the invasion."* That is false. Russia
had record wheat exports in those years. It stopped reporting to FAOSTAT.

Publishing that sentence would be the single worst outcome available to this
project, and the data leads you straight to it.

**Fixes, in order:**
1. **Never rank exporters using the export element.** Build export figures from
   mirror data — what partners report importing. Bulgaria is silent too.
2. **My earlier advice to move the base window to 2022–24 was wrong** and I am
   retracting it. That window is exactly where Russia goes dark. Use **2021–23**
   if working reporter-side, or any window if working mirror-side.
3. Report per-country reporting continuity as a data-quality table. A country
   that stops reporting is not a country that stopped trading.

## 2.2 Mirror coverage is far worse than assumed

Staple flows, 2021–23:

| | Share |
|---|---|
| Both sides reported | **27.4%** |
| Exporter-only | **45.7%** |
| Importer-only | 26.9% |
| Median disagreement where both report | **33.8%** |

Two consequences. First, the importer-preferred convention we adopted governs
only about a quarter of flows — for nearly half the data there is no importer
report at all and we are on exporter figures whether we like it or not. Second,
where both sides do report, the median gap is a **third of the value**. That is
not noise to be waved away; it belongs in the limitations section with the
number attached.

## 2.3 Duplicate keys from mixed units — 70,260 of them

70,260 groups of `(reporter, partner, item, element, year)` appear more than
once. The cause is livestock items reported in two units at once: Camels,
Chickens, Horses, Asses, Buffalo, Turkeys and others carry both `t` and `An` /
`1000 An` rows.

**Anyone who sums `Value` grouped by that key without including `Unit` is adding
tonnes to head counts.** Staples are unaffected — all tonnes — but any
all-commodity aggregation is exposed. Unit must be in the group-by, always.

## 2.4 2.75 million zero-value rows (11.1%)

Zeros are ambiguous: genuine no-trade, or a flow rounded down to zero. They
inflate partner counts for anyone counting rows rather than positive flows —
a country can appear to have 40 suppliers of which 12 supplied nothing.

Filter `Value > 0` before computing partner counts, HHI or diversity. Kanak's
`partner_concentration.sql` does this correctly; ad-hoc notebook code usually
will not.

## 2.5 23,280 self-trade rows

Rows where reporter code equals partner code — a country trading with itself.
An upstream FAOSTAT artefact, not a cleaning error, but it survives into the
cleaned CSV and will distort any concentration measure that does not exclude it.

## 2.6 Missing data is invisible, not preserved

There are **zero nulls** in the Value column. That is not because the data is
complete — it is because absent observations are absent *rows*. The
documentation's "missing values preserved" means no imputation was done, which
is right, but the practical consequence needs stating: **you cannot distinguish
"did not trade" from "did not report."** Russia in 2.1 is exactly this failure
in its most damaging form.

## 2.7 What is clean — say so in the write-up

- **Flags: 98.65% official (A)**, 0.55% estimated, 0.55% imputed, 0.25% from
  international organisations. This is a very clean dataset and the number is
  worth quoting — it makes every other claim stronger.
- **No aggregate leakage.** No partner name matches World, Europe, Africa, Asia,
  Americas, Oceania, any union or development grouping. Kanak's exclusion worked.
- **No negative values.**
- **202 partner countries against 50 reporters** — partners are genuinely
  uncapped, so network analysis is viable.

---

# Part 3 — Suggestions for the team

Ordered by cost-to-benefit. The first three are the ones that change results.

| # | Suggestion | Who | Why it matters |
|---|---|---|---|
| 1 | **Build all exporter-side figures from mirror data.** Never use the export element to rank or total exports. | Yash, Kemisola | Otherwise Russia is zero and the analysis states something false about the most important country in the story |
| 2 | **Add Food Balance Sheets** to the download config | Kanak | Without production data there is no dependency ratio, and concentration alone ranks Russia and Canada as high-risk wheat *importers* |
| 3 | **Swap the 50-country cap for a commodity filter.** Staples are under 2% of rows; keeping them across all ~190 countries is ~15× smaller than the current file | Kanak, Yash | Restores Nigeria, Bangladesh, Pakistan, Ethiopia, Morocco — and Bangladesh is central to the rice finding |
| 4 | Use **2021–23**, not 2022–24, for any reporter-side work | Everyone | 2022–24 is exactly the window where Russia goes dark |
| 5 | Change `partner_concentration.sql` to **quantity, not value** | Kanak | Value-based HHI is price-weighted: a price spike changes concentration with no change in physical supply |
| 6 | Always filter `Value > 0`, exclude self-trade, and include `Unit` in every group-by | Everyone | Three silent corruptions, three one-line guards |
| 7 | Publish a **reporting-continuity table** alongside the analysis | Yash | Turns flaw 2.1 from a hidden landmine into a documented strength |
| 8 | Pick the pipeline of record and fold CPI/CoAHD into it | Kanak, Yash | Four cleaning branches, two conventions, nothing merged |
| 9 | Lead the narrative with **rice and India**, not wheat | Rasheed, Kanak | 49.2% from one exporter, with a 2023 export ban as live proof. Wheat's apparent diversity is partly a reporting artefact |

## The one-paragraph version for the group chat

> Two things in the cleaned data will produce wrong answers if we do not handle
> them. Russia stopped reporting to FAOSTAT after 2021 — it is the only silent
> reporter of the 50 — so any export ranking over 2022–24 shows Russian wheat
> exports at zero, when partners report importing 56 Mt from them. We must build
> export figures from mirror data, never from the export element. And only 27%
> of staple flows have both sides reporting, with a median 34% disagreement
> where they do, so the mirror convention needs stating as a limitation with
> that number attached. On the upside the data is 98.65% officially flagged with
> no aggregate leakage, and it contains a genuinely strong finding: India
> supplies 49% of traded milled rice, Saudi Arabia takes 75% of its rice from
> India, and India banned rice exports in 2023.
