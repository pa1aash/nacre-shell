# Retrodiction pass criterion

Session P0-W2.2, lane p0-w2. This criterion was written, and committed together with `cases.yaml`, before any retrodiction run. The commit is recorded in `ops/reports/P0-W2.2.md` as "fixed before run". The run is session P0-W2.3, which needs checkpoints cp1 and cp2.

The case layout and the input-to-contract mappings are in `SCHEMA.md`. `uv run nacre retro check` recomputes N and k below from `cases.yaml` and fails if they differ.

## 1. What is predicted

For every usable case the run evaluates the C3 barrier ΔG*_het/k_BT of the test surface and of the reference surface with the registered contract (`theory/contract.yaml`, commit recorded in the results).

- **Draws.** There are 20 000 joint Monte Carlo draws, with root seed 0.
- **Shared inputs.** The inputs marked `shared`, and the shared priors, are drawn once per draw and used for both surfaces.
- **Clipping.** cos θ is clipped to [−1, 1] as in lane note N2, and the boundary mass is reported.

The quantity scored is the per-draw difference

  Δ = ΔG*_het(test) − ΔG*_het(reference),

together with its 5 % and 95 % quantiles, q05 and q95.

## 2. Verdict for one case

All usable cases in v1 are pairwise orderings (`comparison: pairwise`). The observed relation is `test_higher_barrier` or `test_lower_barrier`.

| Verdict | Observed `test_higher_barrier` | Observed `test_lower_barrier` |
|---|---|---|
| **correct** | q05 > 0 | q95 < 0 |
| **incorrect** | q95 < 0 | q05 > 0 |
| **inconclusive** | q05 ≤ 0 ≤ q95 | q05 ≤ 0 ≤ q95 |

In words:
- A prediction is **correct** when the central 90 % interval of the predicted barrier difference excludes zero on the observed side. That is, at least 95 % of the propagated input uncertainty puts the barriers in the observed order.
- It is **incorrect** when that interval excludes zero on the opposite side.
- It is **inconclusive** when the interval contains zero: the barrier difference lies within the propagated uncertainty. This includes draws in which both surfaces clip to the same boundary (Δ = 0 exactly).

**How an inconclusive prediction counts.** An inconclusive case stays in N and does **not** count as correct. The rule therefore cannot be met by retreating into uncertainty.
- The number of correct cases among conclusive cases is also reported.
- That number is descriptive only and never enters the pass rule.

## 3. Overall pass rule

Let N be the number of usable cases in the committed `cases.yaml`. Let X be the number of correct verdicts. The null hypothesis is that the pipeline is no better than a coin flip: each case is correct with probability 1/2, independently.

k is the smallest integer with P(X ≥ k | N, 1/2) ≤ 0.05:

  P(X ≥ k) = Σ_{j=k..N} C(N, j) / 2^N.

For the committed cases:

N = 12
k = 10

| k | Σ C(12, j) for j ≥ k | P(X ≥ k) |
|---|---|---|
| 9 | 220 + 66 + 12 + 1 = 299 | 299 / 4096 = 0.0730 |
| 10 | 66 + 12 + 1 = 79 | 79 / 4096 = 0.0193 |

k = 9 fails the 0.05 bound and k = 10 meets it.

**The retrodiction passes if at least 10 of the 12 usable cases are correct.** The chance probability of reaching that by coin flips is 79/4096 = 0.0193.

## 4. Conditions the run must meet

1. **Frozen inputs.** `cases.yaml` and this file are byte-identical to the fixed-before-run commit. The run records both sha256 hashes in `results.json` (`SCHEMA.md`, section 5).
2. **Parameter keys.** Every `params_key` named in `cases.yaml` exists in `lit/params.yaml` and is built from the listed evidence rows.
   - Otherwise the run stops BLOCKED.
   - No substitute value is used.
3. **Fixed mappings.** The input-to-contract mappings are those of `SCHEMA.md`, section 4. The route fixed per case (for example DFS rather than COSMO-RS in RC04 and RC05) is not changed.
4. **Label symmetry.** The code that computes a barrier receives the inputs of one surface and the shared draws only. It never sees the observed relation or which surface is the reference. As a check, the run swaps test and reference for every case and confirms that Δ changes sign draw by draw.
5. **Results only.** No mock or draft prior enters a reported result (track rule R-dry).

## 5. Known limits of the test

These are stated now so that they are not discovered after the result.

- **Not independent.** Several cases share a reference surface and a study:
  - RC01–RC03 share C16-COOH;
  - RC07–RC10 share chitosan;
  - RC04 and RC05 share the carboxyl SAM.

  The effective number of independent tests is below 12, so 0.0193 is a nominal value.
  - A study-level tally is also reported: how many of the six studies have all their cases correct.
  - It is descriptive only.
- **Same direction throughout.** All 12 observed relations are `test_higher_barrier`. This follows from selection rule 3: the references are the carboxyl and chitosan surfaces, which are the strongest nucleators in their studies. The coin-flip null is meaningful only because condition 4 keeps the labels out of the prediction.
- **Correlations already published.** In 11 of the 12 cases the source itself reports the correlation between the input and the outcome (`link_reported_in_source: true`). For example, Hamm et al. (2014) correlate DFS binding energies with B, and Giuffre et al. (2013) correlate γ_S-air with B. Those cases test whether the pipeline maps independent inputs onto barriers with the right sign and conventions (sign-flip SF1 in `theory/contract.yaml`). They are not new evidence for the physics. RC11 is the exception.
- **Strong assumptions.**
  - RC11 rests on a common θ for a CH3 and a COOH surface (A-RC11-1).
  - RC12 rests on configurational MD energies and on deposit mass (A-RC12-1, A-RC12-2).

  These are the weakest cases. They are kept because they are the only usable methyl and catechol cases, not because of an expected result.
- **Coverage.** No usable hydroxyl-terminated case could be built: RX01, RX03, RX05 and RX08 are excluded, with reasons in `cases.yaml`. A result on this set says nothing about hydroxyl-terminated templates.
- **Absolute barriers are not tested.** Only the sign of a within-study difference is scored, so absolute barriers, and the C3 threshold of `theory/thresholds.md`, are not tested.

## 6. What is reported

**If the rule is met.** Report:
- X of N, the chance probability, and the conclusive-only and study-level tallies;
- every inconclusive and incorrect case, with its boundary mass;
- the limits of section 5.

The supported statement is limited to this: the template channel of the C3 barrier reproduces the sign of within-study measured orderings in X of N cases. It is not a claim about absolute barriers, kinetics, or the P0 system itself.

**If the rule is not met.** Diagnose and report. Never tune. For each incorrect or inconclusive case, report:
1. the channel and the input that dominated Δ, from the per-draw contributions;
2. whether a flagged assumption carries the case;
3. the boundary mass;
4. whether the inputs or the outcome reading, rather than the C3 model, are the likelier cause. Two examples: the {104}-for-(012) face substitution, or the common-prefactor reading of a deposit mass.

The result of the frozen set is reported as the result, whichever way it falls.

**Changes after the run.** After the first run, none of the following may change for this criterion:
- the cases;
- the inputs and their distributions;
- the mappings;
- the 90 % level;
- k.

Any change makes a new criterion version with a dated deviation entry (`ops/tracks/p0_deviations.md`), and the frozen version's result is still reported first.
