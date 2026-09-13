# Practical application and business context

**Owner:** Rasheed (Domain & Business lead) · **Analysis 2 companion** · Drafted 11 Sep 2026

This is the "so what" layer for the FoodMatrix submission. Analyses 1–3 produce
metrics; this document says who the metrics are for, what they would change, and
where they stop being trustworthy. Every number below is computed from
`data/cleaned/trade_matrix_cleaned.csv` (importer-reported quantities, tonnes)
unless a source is cited, and every claim that rests on an outside fact carries
the source so a judge can check it.

Reproduce every figure here with:

```bash
python scripts/rasheed/practical_application_figures.py
```

---

## 1. Who this is for

The composite risk index is not an academic ranking. It is written for three
decision-makers, and each one needs a different cut of the same number.

| User | The question they actually ask | What the index gives them |
|---|---|---|
| A national grain buyer or food-security unit | "If our largest supplier stops shipping next quarter, how much of our staple supply is at risk and where else could we buy?" | Their own exposure decomposed into dependence, concentration and supplier count |
| A humanitarian / development agency (WFP, FAO, a development bank) | "Where should limited pre-positioning money and reserve financing go before the next shock, not after it?" | A cross-country ranking with intervals, so money goes to structural exposure rather than to the last headline |
| A commodity trader or insurer | "Which import corridors carry so much single-origin concentration that a disruption reprices the whole route?" | Corridor-level concentration and the second-order exposure from Analysis 3 |

The unifying framing for the video: **the index measures who gets hurt if a
supplier stops, not who will get hurt.** That distinction matters, we tested it,
and section 2.3 shows why it has to be stated out loud.

---

## 2. What the data says, in business terms

### 2.1 The Central Asian wheat cascade — a dependency that hides behind a diversification

This is the strongest structural finding in the data and the clearest candidate
for the originality mark, because it is invisible to any first-order metric.

Three-year mean, 2019–21, importer-reported quantities:

| Importer | Wheat imports | Largest supplier | Share |
|---|---|---|---|
| Uzbekistan | 2.88 Mt/yr | Kazakhstan | **99.2%** |
| Tajikistan | 1.13 Mt/yr | Kazakhstan | **94.7%** |
| Kyrgyzstan | 0.25 Mt/yr | Kazakhstan 73.4% + Russia 24.9% | **98.3% combined** |
| Afghanistan | 0.77 Mt/yr | Kazakhstan 54.5%, Pakistan 26.6%, Uzbekistan 18.7% | 73.2% Kazakh-origin once Uzbek re-export is traced |
| **Kazakhstan** | **0.78 Mt/yr** | **Russian Federation** | **99.9%** |

Read the last row again. Kazakhstan is the region's supplier *and* is itself a
single-origin importer. A country looking at Uzbekistan's numbers sees
dependence on Kazakhstan and might call that a hedge against Russia. It is not.
Trace one step further and the exposure is to a single Russia–Kazakhstan
corridor that four countries and roughly 5 Mt of annual wheat sit behind.

The Caucasus is the same shape without the intermediary: Armenia 97.6% Russia,
Azerbaijan 91.6%, Georgia 91.5%, Mongolia 99.3% (2019–21 means).

**So what.** Diversification advice built on first-order supplier shares would
tell Uzbekistan to keep buying from Kazakhstan. Second-order exposure — which is
exactly what Eve's network analysis computes — says the only real hedge is a
route that does not pass through the Russia–Kazakhstan corridor at all. For
landlocked Central Asia that means Iranian or Pakistani port access, or physical
reserves. It is an infrastructure decision, not a procurement one, and it takes
years, which is the argument for starting from a structural index rather than
from last year's price.

**The corridor has already been tested once.** On 14 April 2022 Kazakhstan
imposed export quotas of 1 Mt of wheat and 300,000 t of wheat flour, extended on
15 June to 1.55 Mt and 670,000 t and running to 30 September 2022
([FAO GIEWS](https://www.fao.org/giews/food-prices/food-policies/detail/en/c/1585321/)).
Uzbekistan alone buys 2.9–3.2 Mt of Kazakh wheat a year. A quota below one
country's annual requirement, covering the whole export programme, is the
definition of a system with no slack.

What the data then shows is instructive and worth being precise about: the quota
did **not** cut Uzbek or Tajik volumes — both rose in 2022. The visible
reaction is Kyrgyzstan, whose Kazakh share fell from 55.8% (2021) to 10.2%
(2022) while its Russian share rose from 43.4% to 89.7%. One country in the
cascade could re-route inside the same corridor; the ones with no second option
simply kept buying. We present this as coincident with the quota, not as proven
causation — annual data cannot carry a causal claim about a five-month measure.

### 2.2 Egypt — the shock made the most exposed country *more* exposed

Egypt is the world's largest wheat importer and runs the *baladi* bread subsidy,
which reached **73 million people, about 65% of the population, in 2023**
([IFPRI](https://www.ifpri.org/blog/egypt-increases-price-of-subsidized-bread-for-the-first-time-since-1989-implications-for-nutrition-and-food-security/)).
There is no larger single concentration of food-security consequence attached to
one trade flow anywhere in this dataset.

Egypt's wheat supplier concentration, from our own pipeline:

| Year | Imports | Partner HHI | Russia share |
|---|---|---|---|
| 2018 | 12.2 Mt | 0.565 | 73.5% |
| 2019 | 10.4 Mt | 0.356 | 55.0% |
| 2020 | 9.0 Mt | 0.434 | 60.2% |
| 2021 | 5.9 Mt | 0.330 | 46.9% |
| 2022 | 8.0 Mt | 0.320 | 51.1% |
| 2023 | 8.2 Mt | **0.483** | 67.2% |
| 2024 | 13.1 Mt | **0.497** | 68.7% |

**Concentration rose by half after the shock that was supposed to teach
diversification** — HHI 0.330 in 2021 against 0.497 in 2024. This is the finding
to lead the practical-application section with, because it is counter-intuitive,
checkable, and it reframes the entire recommendation set.

The honest qualifier, which we should offer before we are asked for it: Egypt
was *more* concentrated in 2018 (HHI 0.565) than it is now, so 2024 is not an
all-time high. What the series shows is a three-year diversification trend
running to 2021, reversed by the shock rather than reinforced by it. That is
still the point — the episode that made the risk visible is the episode that
undid the progress — but "worst ever" would be wrong and a judge with the series
in front of them would catch it.

Two supporting notes. First, it independently validates the pipeline: IFPRI
reports Russia at ~54% for 2022 and ~75% for 2023 against our 51.1% and 67.2% —
a few points apart, consistent with calendar-year versus marketing-year
accounting, and close enough that the cleaning is evidently doing the right
thing. Second, it explains *why*: after 2022 Russian wheat was the cheapest and
most available origin, and a country under acute foreign-exchange pressure buys
the cheapest wheat. Resilience lost to affordability, in the procurement
decision, every time.

**So what.** Diversification does not emerge from the market — it has to be paid
for and mandated. The levers that actually work are the ones that make a second
origin a rule rather than a preference: a reserved share in the state tender, a
strategic reserve sized to the switching window rather than to a round number of
months, or concessional financing that closes the price gap between the cheapest
origin and the second one. "Egypt should diversify" is not a recommendation.
"Egypt's tender rules should reserve 20% for a non-Black-Sea origin, and here is
what that costs per tonne" is.

### 2.3 India's 2023 rice restrictions — and the honest limit of what we can claim

India banned broken-rice exports in August 2022 and non-basmati white rice in
July 2023, with further parboiled and basmati measures in August 2023
([IFPRI](https://www.ifpri.org/blog/indias-export-restrictions-rice-continue-disrupt-global-markets-supplies-and-prices/)).
Our 2019–21 window predates all of it, which makes the event a genuine
out-of-sample test of whether the exposure metric predicts harm.

We ran that test on every rice importer above 100 kt that sourced more than half
its rice from India in 2021, comparing 2021 and 2023 volumes. **The result does
not support a simple story, and we should say so before a judge finds it.**

| Outcome | Countries |
|---|---|
| Volume collapsed | Sri Lanka −80%, Ethiopia −69% (97.5% India-sourced), Madagascar −35%, Viet Nam −29% |
| Volume held, supplier swapped | Senegal +9% with India's share falling 75% → 29% by 2024; Benin +7%; Saudi Arabia +2% |
| Volume rose sharply | Indonesia +651%, Togo +81%, Burkina Faso +190% |

Madagascar's −35% sits beside IFPRI's independently published −44% for the same
episode — again, the pipeline reproduces an outside figure.

But Sri Lanka's collapse coincides with its foreign-exchange crisis, and
Indonesia's surge with an El Niño harvest shortfall. Concentration did not
determine the outcome; national circumstances did. We tested a geographic
hypothesis too — that landlocked importers would fare worse than coastal ones —
and the data did not support it, so it is not in the deck.

**So what.** This is the caveat that makes the rest of the work credible rather
than the weakness that undermines it. The index measures *exposure*: the size of
the loss if a supplier stops. It does not forecast *outcome*, because
governments respond, harvests vary, and money decides who can substitute. That
is how FAO and IFPRI frame their own vulnerability indicators, and saying it
plainly is what separates a defensible ranking from a naive one.

---

## 3. Three archetypes, three different interventions

Lumping every high-scoring country into "diversify your suppliers" wastes the
index. The scores decompose into three structurally different problems, each
with a different lever, cost and time horizon.

| Archetype | Signature in the data | Example | Lever that actually applies | Horizon |
|---|---|---|---|---|
| **Corridor-locked** | Very high single-supplier share, few physical routes, supplier itself concentrated | Uzbekistan, Tajikistan, Afghanistan, Mongolia | Physical reserves and alternative route capacity. Procurement policy alone cannot fix this | 3–10 years, capital-intensive |
| **Affordability-constrained** | High and *rising* concentration, large volumes, FX pressure | Egypt, and the demand side of the 2022 Black Sea episode | Tender rules that reserve a share for a second origin; concessional financing to close the price gap | 1–3 years, costs money not time |
| **Substitutable** | High concentration but deep alternative markets and port access | Senegal, Benin, Saudi Arabia | Contract diversification and buffer stock; this is the cheap case, and the data shows these countries already doing it unaided | Under 1 year |

The practical value of the index is that it tells you which of these three a
country is in **before** the shock, which is when the cheap interventions are
still available. After the shock, only the expensive ones remain.

---

## 4. What we will say about limitations

Stated by us, these read as rigour. Found by a judge, they read as flaws.

1. **Exposure, not forecast.** Section 2.3. The index ranks who has most to lose,
   not who will lose it.
2. **Mirror-derived export figures are a floor.** Russia files no export rows
   from 2022 onward; our rebuilt figures recover a mean of 66% of self-reported
   volumes across the years where both exist (75% for 2017–21), so they are sound
   for shares and rankings and unsound for absolute tonnage. Documented in
   `data/README.md`.
3. **2024 is the weakest year.** Partner reports for Russian wheat fall from 81
   (2021) to 42 (2024). Any 2024 figure is footnoted.
4. **Three commodities, not a food system.** Wheat, rice and maize are roughly
   half of traded calories, not all of them. Pulses, oils and fertiliser are out
   of scope, and fertiliser in particular is a real omission for a resilience
   story.
5. **Annual data cannot resolve sub-annual policy.** A five-month export quota is
   not visible in a calendar-year panel except as a coincidence, which is exactly
   how section 2.1 presents it.
6. **Concentration is measured on realised trade.** A country buying 100% from
   one supplier because it is cheapest looks identical to one with no
   alternative. The Senegal/Ethiopia contrast in 2.3 is that ambiguity made
   visible, and closing it needs price and logistics data we do not have.

---

## 5. Open items for the team

- **Rice items are double-counted in the commodity map.** `build_quantity_concentration.py`
  and `config/faostat.json` both map *Rice, paddy (rice milled equivalent)* and
  *Rice, milled* to "Rice" and sum them. The first is FAOSTAT's milled-equivalent
  aggregate and already contains the second. For 2019–21 the sum gives ~67 Mt/yr
  of world rice imports against an actual ~50 Mt/yr, and 2,908 reporter–partner
  pairs in 2021 alone report both items. Shares are less distorted than volumes,
  but any rice tonnage on a slide is currently ~35% too high. The figures in this
  document use the milled-equivalent item only; the script prints the evidence.
- **The risk outputs are not in the repo.** `country_risk.csv` and
  `commodity_vulnerability.csv` are gitignored, so nobody can review the ranking
  without rebuilding it, and the copies sitting in working directories are from
  an earlier version of the scoring code. A small committed sample, or the
  top-40 table as CSV, would let the rest of us check it.
- **Two reporting gaps to check before anything is said about them.** Nepal's
  panel stops at 2022, and Mongolia's wheat imports fall from 228 kt (2021) to
  3.5 kt (2022) — almost certainly a reporting gap rather than a 98% collapse,
  but it needs confirming rather than assuming.

---

## Sources

- [FAO GIEWS — Kazakhstan extends wheat export restrictions until 30 September 2022](https://www.fao.org/giews/food-prices/food-policies/detail/en/c/1585321/)
- [IFPRI — Egypt increases the price of subsidised bread for the first time since 1989](https://www.ifpri.org/blog/egypt-increases-price-of-subsidized-bread-for-the-first-time-since-1989-implications-for-nutrition-and-food-security/)
- [IFPRI — India's export restrictions on rice continue to disrupt global markets](https://www.ifpri.org/blog/indias-export-restrictions-rice-continue-disrupt-global-markets-supplies-and-prices/)
