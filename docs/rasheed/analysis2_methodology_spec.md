# Analysis 2 — methodology specification (v2)

*Rasheed, Domain & Business · 29 Aug 2026*
*Supersedes `risk_index_design.md` v1 where they differ. This is the version to implement.*

Answers to the open methodology questions, with the reasoning for each so the
choices can be defended rather than just applied.

---

## 1. Risk definition

### What we are calling food-trade risk

> **The exposure of a country's staple cereal supply to an interruption in
> imports from its trading partners.**

Specifically the second of the two options: **vulnerability to disruption of a
major trade partner**, not general import vulnerability.

**Why the narrower definition wins.** General import vulnerability is a
food-security question — it needs domestic production, income, distribution and
price data to answer honestly, and a trade dataset cannot carry it. Partner
disruption is a question trade data *can* answer completely, and it is the
Trade track's question. Choosing the answerable one is not a compromise; an
index that overreaches its data is the most common way this kind of work fails.

**Where it sits in the accepted framework:** this measures the **stability**
dimension of FAO's four pillars (availability, access, utilisation, stability).
Saying so places the work inside FAO's own framing rather than beside it.

### What it explicitly is not

**Exposure is not harm.** The index measures a channel a shock could travel
through. It does not predict one will occur, and it says nothing about a
country's fiscal capacity to absorb a price spike. A wealthy import-dependent
country and a poor one can score identically and experience the same disruption
completely differently.

State this once, plainly, in the deliverable. It is the single most likely line
of attack and it costs nothing to disarm.

---

## 2. Core methodology

### Unit of analysis

**Country × Commodity**, computed on a **three-year mean (2021–23)**.

Build the panel at Country × Commodity × Year — you need the year dimension for
trend charts and for the robustness check — but the **index itself is not
annual**. A yearly index is noisy: rank churn driven by one harvest or one
delayed shipment forces you to explain movement that carries no signal.

Roll up to a country-level headline ranking by weighting each commodity by that
country's import volume, and report the commodity-level detail underneath.

**On the window:** 2021–23, not 2022–24. Russia files no export rows from 2022,
and Iran, Viet Nam and the UAE stop at 2022 or 2023. 2021–23 keeps one year of
Russian self-reporting as a cross-check on the mirror rebuild.

### Import dependency

```
IDR = imports / (production + imports − exports + stock_variation)
```

Compute the denominator from its components rather than taking FBS's published
"Domestic supply quantity" element, so that IDR and SSR share a denominator.
Mixing the two is where the "why don't these add up?" question comes from.

**Correction to v1 of this spec:** I previously wrote that IDR and SSR sum to 1.
They do not. Sharing a denominator gives
`IDR + SSR = (production + imports) / supply = 1 + (exports − stock) / supply`,
so they sum to 1 only for a country with no exports and no stock change, and a
net exporter's SSR legitimately exceeds 1. Report one ratio or the other; do not
present the pair as a partition of supply. Caught by unit tests on the FBS
build script.

**Stock variation follows the FAO sign convention:** a stock *decrease* is
positive because it adds to supply. Getting this backwards inverts dependency
for large stockholders like China and India, and it is a silent error.

⚠ **The FBS join is the live trap.** Food Balance Sheets use a different item
taxonomy from the trade matrix — FBS has aggregated groups like "Wheat and
products" where the trade matrix has "Wheat", "Wheat and meslin flour" and
"Bran of wheat" as separate items. Joining on item name returns nothing or the
wrong thing, and since IDR is the denominator of the whole index, a bad join
produces a plausible-looking index built on nonsense. **Print the distinct FBS
item list and map explicitly, then assert the row count.**

### Quantity or value

**Quantity — tonnes — for everything in the index.**

Food security is about calories physically arriving. Value moves with prices,
so a value-weighted concentration measure changes when wheat prices spike even
though the physical supply structure is identical. This is not theoretical: the
team's `partner_concentration.sql` currently runs on `Import value`, which
should change.

Keep a value-based view as a secondary economic lens if it is useful for the
narrative, clearly labelled as such.

### HHI, Top-1, or both

**Both — but for different jobs, and only one goes in the index.**

| Measure | Where it goes | Why |
|---|---|---|
| **HHI** (and its reciprocal, effective suppliers) | **In the index** | Uses the whole share distribution; distinguishes "four suppliers, one at 90%" from "four at 25% each", which Top-1 cannot |
| **Top-1 supplier share** | **In the narrative and charts** | It is the number a non-expert understands instantly: "Egypt takes 69% of its wheat from Russia" |

**Do not put both in the index.** They correlate at roughly 0.9 by
construction — including both silently double-weights concentration and makes
the index look more multi-dimensional than it is. Compute the correlation
matrix and report it.

**Report effective suppliers (1 ÷ HHI) rather than raw HHI in anything a
non-specialist reads.** "Türkiye has, in effect, 1.4 wheat suppliers" lands
where "HHI 0.72" does not.

---

## 3. Data handling

### Missing values

**Do not impute. Anywhere.**

There are no nulls in the cleaned matrix — missing observations are absent
*rows*, not blanks. The consequence: **you cannot distinguish "did not trade"
from "did not report."**

The rule:
1. Run the reporting-continuity check first (`scripts/faostat_audit.py`).
2. **Exclude any country × commodity cell where the importer has no reporting
   continuity across the window**, rather than treating its absence as zero
   trade. A country that stopped reporting would otherwise score as perfectly
   self-sufficient, which is the opposite of the truth.
3. **Report the exclusion count** in the methods section. A stated exclusion is
   rigour; a silent one is a hole.

**Zeros:** filter `Value > 0` before computing partner counts, shares or HHI.
Around 11% of rows were zeros in the previous build — counting rows rather than
positive flows gives a country "40 suppliers" of which a dozen supplied nothing.

**Self-trade:** now excluded in the pipeline. Verify it after re-running.

### Mirror-export data

**Use `recommended_value` for the exporter side. Use the importer's own report
for the importer side.**

The asymmetry is deliberate and matters:

- **Importer-side concentration** — who a country buys from, and in what
  shares — should come from the importer's own declarations. They are the
  reporter, the data exists, and import declarations attract duty and customs
  valuation so they are the better-audited side.
- **Exporter-side figures** — total exports, global market share, who is
  systemically central — must come from mirror data, because major exporters go
  silent. Russia files nothing from 2022.

**A hard limit on the mirror data, which must be documented.** Mirror exports
capture only what importers report, and many of Russia's largest customers
report patchily themselves. The rebuild gives Russia roughly 22–34 Mt/year of
wheat exports; the actual figures are 44.7 Mt (2022/23) and 55.4 Mt (2023/24).

So: **`recommended_value` is sound for shares and rankings** — the undercount is
roughly proportional across partners — and **unsound for absolute volume
claims**. No slide should state a mirror-derived tonnage as a country's exports.

### Flagging mirrored observations

**Yes — explicitly, and treat it as a strength rather than a caveat.**

Carry a provenance column on every derived figure: `self_reported`,
`mirror_derived`, or `both_agree`. Then report, in the methods section, what
share of the index rests on each.

Two reasons this is worth the effort. It pre-empts the obvious challenge — a
reviewer who asks "how much of this is inferred?" gets a number instead of a
shrug. And only about 27% of staple flows have both sides reporting, with a
median 34% disagreement where they do, so the provenance split is a substantive
finding about the data in its own right.

---

## 4. Risk and resilience

### Alternative suppliers

**Yes — but as an input to recommendations, not as an index component.**

Judging whether an alternative is genuinely available requires spare export
capacity, freight feasibility and product-class fit. That is real analysis and
it belongs in the country dossiers behind each recommendation. Quantifying it
defensibly as an index component is not achievable in the time available, and a
badly-quantified component is worse than none.

**One cheap exception that is defensible:** *number of suppliers holding more
than a 5% share*. It proxies substitutability, it is trivially computed, and it
is interpretable — a country with one 90% supplier and eight 1% suppliers has
no real alternatives, which raw partner count hides.

### The "largest supplier disappears" simulation

**Yes. This is the highest-value single analysis available to Analysis 2 —
prioritise it above refining the index.**

Reasons, in order:

1. It produces the headline number the whole submission can hang on: *"if this
   exporter stopped, N countries would lose more than half their wheat supply."*
2. It is instantly intuitive. A composite score needs explaining; a
   supplier-removal simulation explains itself.
3. It is a counterfactual, which is what makes the index *mean* something
   rather than describe something.
4. It replays 2022 and 2023 on our own data, which is where the credibility
   comes from.

**Method:** remove one exporter, recompute each importer's remaining supply, and
report volume lost, share lost, and suppliers remaining. Compare targeted
removal against random removal — targeted is consistently more damaging, and
demonstrating that on our own data beats citing it.

**State the assumption honestly:** this is a static accounting shock with no
substitution, no price response and no rerouting. It is a worst-case bound, not
a forecast. Real markets partially reroute, which is precisely why 2022 raised
prices more than it cut volumes. Saying this yourself converts the method's
weakness into evidence you understand it.

### Producer prices

**No — not as an index component.**

FAOSTAT producer prices are **farm-gate prices in the producing country**. They
describe an exporter's economics, not what an importer pays. Building an
importer-risk component on them would be a category error, and it is the kind a
domain reviewer spots immediately.

**Two legitimate uses:**
- **Validation** — if the index measures something real, high-scoring countries
  should show larger price responses around 2008, 2011 and 2022. That is a
  genuine out-of-sample check rather than another correlation with our own
  inputs.
- **A separate price-exposure dimension**, if the team wants one, built from
  import unit values (available in the TCL domain) or from the Consumer Price
  Index and Cost & Affordability of a Healthy Diet data on the other cleaning
  branch. That is a different analysis, not a patch to this one.

---

## 5. Final output

### Composite score or multiple dimensions

**Both, structured deliberately: a composite for the ranking, always presented
with its decomposition.**

A naked composite invites "it's a black box." Separate dimensions with no
composite give the reader no answer to "who is most at risk." The combination
solves both:

1. **The ranked table** — country, commodity, score, rank, 90% rank interval,
   and the component that drove the rank.
2. **The signature chart** — dependency on one axis, concentration on the other,
   bubble size by import volume, colour by composite score. The upper-right
   quadrant *is* the finding, visible without reading a number, and it shows why
   each country sits where it does.
3. **The simulation** — the counterfactual that proves the ranking means
   something.

### Components and weights

| Component | Direction | Weight | Source |
|---|---|---|---|
| Import dependency ratio | higher = riskier | 2 | FBS |
| Supplier concentration (HHI) | higher = riskier | 2 | Trade matrix, importer-reported |
| Suppliers above 5% share | lower = riskier | 1 | Trade matrix |

**On the third component.** v1 proposed supplier fragility from network
centrality. **Network analysis still has no owner**, and designing around a
component nobody is building is how a methodology section ends up describing
something that does not exist. Decision rule: **if network analysis has an owner
by 31 August, supplier fragility replaces the 5%-share count. If not, the index
ships with the three components above** and the network view becomes a separate
qualitative section if anyone gets to it.

**Aggregation: weighted geometric mean.** These components are complements, not
substitutes — a country importing 95% of its wheat from one supplier is exposed
regardless of how it scores elsewhere, and a linear average lets a good score
elsewhere cancel that out. Geometric penalises imbalance, which is the behaviour
a risk measure should have. Normalised inputs shifted by ε = 1e-3 since
geometric aggregation is undefined at zero.

**Normalisation:** min–max to [0,1] after winsorising at the 5th/95th
percentile, presented as 0–100. State that min–max scores are relative to the
country set — this is a ranking instrument, not an absolute measurement.

### Justifying the weights

This is the question every reviewer asks, so it gets answered before it is
asked. Four moves, all cheap:

1. **Name the judgement.** The OECD/JRC handbook is explicit that equal weights
   are themselves a judgement, not the absence of one. Ours: dependency and
   concentration are the two necessary conditions for exposure and neither is
   more fundamental, so they weight equally; the third component rests on more
   assumptions and gets half.
2. **Rank stability across schemes.** Recompute under equal weights, the
   baseline, and each component double-weighted in turn. Report Spearman ρ
   against the baseline plus mean and maximum rank change.
3. **Monte Carlo over the weight simplex.** 5,000 Dirichlet draws, reported as a
   90% rank interval per country. *"Egypt ranks 2nd, 90% interval 1–4"* is a
   stronger and more honest claim than *"Egypt ranks 2nd."*
4. **A pass criterion set in advance:** the top five are the same set of
   countries under every weighting tested, and Spearman ρ ≥ 0.9 throughout.
   Fixing this before seeing results is what makes it a test.

**And one guard against the known failure mode:** correlate the finished index
with GDP per capita. The JRC's audit found the Global Food Security Index
largely tracked capacity to import rather than food-system strength. If ours
correlates highly with income, we are measuring wealth with extra steps — far
better that we find it than a judge does.

### What the team needs to decide

The one question in this list I cannot answer is what the team wants the final
output to look like, because that depends on the deck and the video, which are
Kanak's. The specific things to settle:

- Does Analysis 2 get its own segment in the video, or is it folded into the
  overall narrative?
- Is the headline the **ranking** (who is most exposed) or the **simulation**
  (what happens if a supplier stops)? My recommendation is the simulation as the
  hook and the ranking as the evidence — the counterfactual is more memorable —
  but the deck structure decides it.
- Power BI or Python for the final charts? Affects what Moksh and I hand to
  Kemisola and in what format.

---

## Implementation order for Moksh

1. FBS join with an explicit item mapping, and assert the row count
2. IDR and SSR from the supply identity, sharing a denominator
3. HHI, effective suppliers, top-1 share, and the >5% supplier count — importer-reported, `Value > 0`, self-trade excluded
4. Provenance column on every derived figure
5. Normalise, weight, aggregate geometrically
6. Sensitivity: alternative weights, alternative aggregation, Dirichlet Monte Carlo
7. GDP-per-capita correlation check
8. The supplier-removal simulation — **do not leave this last if time is short; it is worth more than steps 5 and 6 combined**
