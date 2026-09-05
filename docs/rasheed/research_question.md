# Research question — FoodMatrix, Trade track

*Rasheed (Domain & Business) · Draft v1 · 28 Aug 2026*
*Status: draft. Sections marked ⚠ must be checked against the official kickoff brief before this is final.*

---

## The recommendation

> **Which countries are most exposed to a disruption in their staple cereal imports — and how much of that exposure is invisible in country-level statistics because it runs through a shared upstream supplier?**

One sentence, two clauses. The first clause is the spine everyone's analysis
hangs from. The second is the distinctive angle, and it is the part that makes
this a Trade-track question rather than a generic food-security one.

## Why this one

**It forces all four analyses to answer the same question.** A weak research
question lets three analyses run in parallel and be stapled together at the
end. This one chains them:

| Piece | What it contributes | Owner |
|---|---|---|
| Analysis 1 — concentration | *How* concentrated is each country's import base? Establishes the country-level picture | Yash, Kemisola |
| Network analysis | Which suppliers are systemically critical, and who shares them? Answers the second clause | Kemisola |
| Analysis 2 — risk index | Combines dependency, concentration and supplier fragility into one defensible ranking | Rasheed (method), Moksh (build) |
| Analysis 3 — prediction | Where is exposure heading? Forecast or classify the exposure measure Analysis 2 defines | Moksh, Kanak |

Analysis 3 gets a target it does not currently have, and it is a target that
falls out of the question rather than being chosen for convenience.

**The second clause is a genuine finding, not a framing device.** Two countries
can look equally diversified — four suppliers each, no supplier above 35% — and
have completely different real exposure, because one country's four suppliers
all buy from the same place. That is measurable, it is invisible in every
country-level table, and most teams will not compute it. It scores on Depth
(35%) and Originality (10%) simultaneously.

**It has an obvious "so what."** Practical Application is 30% of the score. The
answer to this question is a list of countries and a reason, which converts
directly into: diversify toward a specific alternative supplier, size a reserve
to a specific disruption window, or watch a specific upstream relationship.

**Recent history has already run the experiment.** The 2022 Black Sea
disruption and India's 2023 rice export restrictions are both cases where the
countries that got hurt were not always the ones the headline statistics
flagged. That gives the finding immediate credibility with judges who read the
news.

## Scope — the decisions that make it answerable ⚠

Depth is 35% and breadth is a trap. Pin these down before Aug 26.

| Decision | Proposed | Why |
|---|---|---|
| Commodities | **Wheat, rice, maize** | ~Half of global food-energy intake between them; all three heavily traded; all three have had a recent disruption event to anchor against |
| Geography | **Global**, with a named focus region for the narrative (North Africa / Middle East, or Sub-Saharan Africa) | Global keeps the network analysis meaningful — a regional network cuts off the suppliers that matter. The focus region is for storytelling, not for filtering the data |
| Period | **Analysis on a 2020–22 or 2021–23 three-year mean**, trend context from ~2000 | A single year moves with one harvest or one export ban |
| Unit of analysis | **Country × commodity** | "Egypt is exposed" is vague; "Egypt's wheat supply is exposed" is a finding |

⚠ All four must be checked against the official dataset — if the release covers
a narrower period or a different commodity set, these change.

## Alternatives considered

**A. "Which exporters are systemically critical to global staple trade?"**
Cleaner and more original, but it is a supply-side question with a short
answer (a handful of countries everyone can already name) and a weak practical
application — you cannot recommend much to a systemically critical exporter.
Better as a *finding within* the recommended question than as the question.

**B. "Has the global staple trade network become more or less resilient over
the past two decades?"** Strong depth through the time dimension and
genuinely interesting — Puma et al. (2015) found interconnection rising while
fragility rose with it. But it is a research-paper question: the deliverable is
a trend, not an actionable ranking, and it puts heavy weight on getting a long
panel clean in a week. Consider one chart from this as context, not the spine.

**C. "What drives import dependency?"** Explanatory rather than diagnostic.
Ends in a regression table, and regression tables do not make five-minute
videos.

## What this commits us to

- The risk index must produce a **ranking with defensible uncertainty**, not a
  point score. Rank intervals, not just ranks.
- The network analysis is **load-bearing**, not decorative — the second clause
  cannot be answered without it. It needs an owner confirmed this week.
- Every finding needs its consequence sentence. That is the 30%.

## Open questions for the team

1. ⚠ Does the official brief constrain the commodity set, period, or required
   deliverables in a way that changes the scope table?
2. Is the network analysis owner confirmed? The question depends on it.
3. Analysis 3's target: forecast the exposure score forward, or classify
   countries into exposure tiers? Both work; pick one and let Moksh baseline it.
4. Focus region for the narrative — which one has the best story in the data?
   Decide after Analysis 1, not before.
