# Risk index design — FoodMatrix Analysis 2

*Owner: Rasheed · Draft v1 · 28 Aug 2026*
*Method follows OECD/JRC, Handbook on Constructing Composite Indicators (2008).*
*⚠ marks decisions that must be checked against the official dataset before build.*

---

> **SUPERSEDED — do not implement from this file.**
> `analysis2_methodology_spec.md` (v2, 29 Aug) is the version to build from. It
> settles the open questions this draft left, revises the component set, and
> fixes the base window at 2021-23. This file is kept for the reasoning behind
> the normalisation, weighting and aggregation choices, which v2 carries forward
> unchanged.


## 1. What this index measures

> **This index measures a country's structural exposure to a disruption in its
> staple cereal imports.**

**Unit of analysis:** country × commodity (wheat, rice, maize), with a
country-level roll-up for the headline ranking. ⚠ commodity set pending brief.

**Coverage:** all countries resolving to an ISO3 code, three-year mean.
⚠ period pending dataset.

**Food-security framing:** this measures the **stability** dimension of FAO's
four-pillar framework — availability, access, utilisation, stability. Import
dependence is not a problem in normal times; it is a problem when supply is
interrupted. Saying this places the work inside FAO's own framework rather than
alongside it.

**What it deliberately does not measure:** domestic access or affordability,
nutritional adequacy, or a country's fiscal capacity to absorb a price shock.
A wealthy import-dependent country and a poor one can score alike here and
experience a shock completely differently. **This is the index's most important
limitation and we state it ourselves, in the deliverable.**

**Exposure is not harm.** The index measures a channel through which a shock
could travel. It does not predict that one will.

---

## 2. Components

| # | Indicator | Source | Direction | Weight | Why it belongs |
|---|---|---|---|---|---|
| 1 | **Import dependency ratio** — imports ÷ domestic supply | FAOSTAT FBS | higher = more risk | 2 | The share of supply that must arrive from abroad. Without this, concentration is irrelevant — a country importing 3% of its wheat from one supplier does not care |
| 2 | **Supplier concentration (HHI)** — sum of squared partner shares | FAOSTAT TM | higher = more risk | 2 | Few suppliers means a single point of failure. Without this, dependency is not risk — importing 90% from thirty partners is diversified |
| 3 | **Supplier fragility** — import-share-weighted mean centrality of a country's suppliers | TM + network | higher = more risk | 1 | The second-order channel. A country buying from systemically central suppliers carries risk its own numbers do not show |

**The interaction is the insight.** A country is exposed when it is dependent
*and* concentrated. Either alone is not a story. Component 3 is what makes the
index say something the underlying metrics do not.

### Optional fourth component — decide by Aug 26

**Supply buffer** (stock variation, or production volatility over the trend
period), inverted so that a larger buffer means less risk. It adds the
absorption dimension the first three lack. Include it only if FBS stock data
has decent coverage for the country set — ⚠ check before committing. A
component missing for a third of countries costs more than it adds.

### The collinearity trap — read before adding anything

Several tempting metrics are **the same variable wearing different clothes**:

- Effective number of suppliers is *literally* 1 ÷ HHI.
- Top-supplier share, CR3 and HHI move together almost perfectly.
- Supplier fragility correlates with HHI by construction — a single-supplier
  country inherits that supplier's centrality wholesale.

Putting two of these in silently double-weights concentration and makes the
index look more multi-dimensional than it is. **Compute the correlation matrix
before finalising**, and if any pair exceeds ~0.9, drop one or say plainly that
they overlap. Expect components 2 and 3 to correlate moderately; that is
acceptable and worth one sentence, but check the number.

### Direction check — run this before trusting anything

For each component, print the five countries scoring highest on it. Each list
must match an independent expectation of "high risk on this dimension." A
flipped sign produces a ranking that looks entirely sensible and is exactly
backwards. This check takes two minutes and has no substitute.

---

## 3. Data treatment

- **Mirror flows:** importer-reported figures preferred; exporter's used where
  only that side reports. Import declarations attract duty and customs
  valuation, so they are more rigorously audited. This is an analyst convention
  — Our World in Data's — not an FAO rule, and we cite it as a choice.
  **Robustness:** report the Spearman correlation between the headline ranking
  and the same ranking built on exporter-reported figures.
- **Aggregates:** excluded by requiring a resolvable ISO3. Not by name-matching,
  and not by an area-code cutoff — FAO has changed its numbering.
- **Missing values:** never silently dropped. A dropped country reads as zero
  dependency, which is the opposite of the truth. Countries missing a component
  are excluded from the index with the count reported.
- **Outliers:** winsorised at the 5th/95th percentile before normalisation, so
  that one re-export hub does not compress the scale for everyone else.
- **Re-export hubs** (Netherlands, Singapore, UAE, Belgium) will look
  artificially dependent. Flag them; decide whether to exclude or annotate.
- **Reference period:** three-year mean. ⚠ years pending dataset.
- **Data quality:** report the share of underlying rows that are official
  versus estimated or imputed.

---

## 4. Normalisation

**Method:** min–max to [0,1], after winsorising, presented as 0–100.

**Because:** bounded and intuitive; a 0–100 score communicates in a video in a
way a z-score does not. Winsorising controls its known outlier sensitivity.

**Known consequence, to state in the write-up:** min–max scores are relative to
the sample. Add or remove a country and everyone's score changes. This is a
**ranking instrument, not an absolute measurement**, and claiming otherwise
invites an attack we would deserve.

---

## 5. Weighting

**Baseline:** dependency 2, concentration 2, supplier fragility 1.

**Because:** dependency and concentration are the two necessary conditions for
exposure and neither is more fundamental than the other. Supplier fragility is
a genuine second-order channel but rests on more modelling assumptions, so it
gets half the weight of the primaries — a deliberate hedge against the
component that is most contestable.

**Note:** equal weighting would *also* be defensible. The handbook is explicit
that equal weights are themselves a judgement, not the absence of one. What is
not defensible is an unjustified weight vector, which is why the reasoning
above is written down.

**Alternatives to test:** equal; baseline; and each component double-weighted
in turn.

---

## 6. Aggregation

**Method:** weighted **geometric** mean.

**Because:** these components are complements, not substitutes. A country
importing 95% of its wheat from a single supplier is dangerously exposed
regardless of how it scores on anything else, and a linear average would let a
good score elsewhere cancel that out. Geometric aggregation penalises imbalance
— the handbook's framing is that a unit with a low score on one component
"needs a much higher score on the others" to reach the same composite. That is
exactly the behaviour a risk measure should have.

**Mechanics:** geometric aggregation is undefined at zero, so normalised values
are shifted by ε = 1e-3. Note it in a footnote.

**Robustness:** report the linear-aggregation ranking alongside. The countries
that move most between the two are the imbalanced ones — extreme on one
dimension, moderate elsewhere — and naming them is itself a finding.

---

## 7. Robustness plan

- [ ] Recompute under all alternative weight sets; report Spearman ρ vs
      baseline, mean and max rank change
- [ ] Recompute under linear aggregation; name the biggest movers
- [ ] Monte Carlo over the weight simplex, 5,000 Dirichlet draws; report a 90%
      rank interval per country
- [ ] Recompute under the exporter-reported mirror convention; report ρ
- [ ] Correlate the index with **GDP per capita** — the JRC's audit found the
      Global Food Security Index largely tracked capacity to import rather than
      food-system strength. If our index correlates highly with income, we are
      measuring wealth with extra steps, and it is far better that we find that
      than a judge does
- [ ] Correlate with an accepted external food-security measure. Moderate
      correlation is the target: high enough to be credible, low enough to be
      adding information
- [ ] Decompose the top ten: one sentence each on what drove the rank

**Pass criterion, agreed in advance:** the top five are the same set of
countries under every weighting scheme tested, and Spearman ρ ≥ 0.9 throughout.
Setting this before seeing results is what makes it a test rather than a
description of whatever happened.

---

## 8. Division of labour

| Who | Does |
|---|---|
| **Rasheed** | This design; component justification; direction and collinearity checks; interpretation; the "so what" layer; defending the method |
| **Moksh** | Implementation, the robustness runs, the rank intervals |
| **Kemisola** | Network centrality feeding component 3; Analysis 2 charts |
| **Yash** | Clean dependency and concentration inputs at country × commodity × year |

Reusable functions belong in `scripts/`, not notebook cells, so that everyone
computes the same number the same way.

---

## 9. Outputs

- [ ] Ranked table: country, commodity, score, rank, 90% rank interval, top driver
- [ ] Decomposition chart for the top 10 — stacked contribution by component
- [ ] Sensitivity summary table
- [ ] Choropleth or dot plot of scores
- [ ] One "so what" sentence per headline finding

---

## 10. Known limitations — stated by us, first

1. Trade data is unreconciled; we use importer-reported figures and show the
   result holds under the alternative.
2. The index measures exposure, not realised harm. It says nothing about
   fiscal capacity to absorb a price shock.
3. Re-export hubs may appear more dependent than they are.
4. Min–max scores are relative to the country set included.
5. Supplier fragility rests on a network model whose assumptions — static, no
   substitution, no price response — make it a worst-case channel estimate
   rather than a forecast.

A limitation we name reads as rigour. The same limitation found by a judge
reads as a flaw. There is no reason to leave any of these for them.
