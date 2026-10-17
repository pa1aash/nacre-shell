# Retrodiction pass criterion

Session P0-W2.2, lane p0-w2; revised in session P0-W2.3 before any retrodiction run. Version 1 was written, and committed together with `cases.yaml`, before any run (`af75ed0`). This revision applies the cp3 ruling R9 and the cp2 interface mapping (decisions D17 and D19, lane notes N11 and N23). It is committed together with `cases.yaml`, `SCHEMA.md` and the run code in one commit, recorded in `ops/state/p0-w2.json` (`criterion_sha`) and `ops/reports/P0-W2.3.md` as "fixed before run". The run is session P0-W2.3, which needs checkpoints cp1 and cp2 and uses the parameter table at tag p0-cp3.

The case layout and the input-to-contract mappings are in `SCHEMA.md`. `uv run nacre retro check` recomputes N and k below from `cases.yaml` and fails if they differ.

## 1. What is predicted

For every usable case the run evaluates the C3 barrier ΔG*_het/k_BT of the test surface and of the reference surface with the registered contract (`theory/contract.yaml`, version 3), through `src/nacre/screen/retro.py`.

- **Bookkeeping (contract v3).** The driving force at the template is the bulk one: Ω is Ω_bulk of the pair, and enrichment never raises it. Every template input acts through θ.
- **Interfaces.** Every input names the interface it acts on (`SCHEMA.md`, section 4):
  - crystal–template adhesion (force-spectroscopy binding free energies, simulated interaction energies) → γ_sn through Dupré;
  - Ca²⁺-binding data (a near-surface Ca²⁺ concentration) → γ_sl through the Gibbs–Langmuir term Δγ_ads;
  - contact-angle surface energies (OWRK) → γ_sl, the interface they are used for, against water with γ_sn common;
  - a simulated net interfacial energy → the net energy of the nucleus, f(θ) = (γ_net/γ_nl)³.
- **Draws.** There are 20 000 joint Monte Carlo draws, with root seed 0.
- **Shared inputs.** The inputs marked `shared`, and the shared priors, are drawn once per draw and used for both surfaces.
- **Clipping.** cos θ is clipped to [−1, 1] as in lane note N2, and the boundary mass is reported.

The quantity scored is the per-draw difference

  Δ = ΔG*_het(test) − ΔG*_het(reference),

together with its 5 % and 95 % quantiles, q05 and q95, taken over the draws where Δ is finite. The fraction of non-finite draws is reported.

## 2. Verdict for one case

All usable cases are pairwise orderings (`comparison: pairwise`). The observed relation is `test_higher_barrier` or `test_lower_barrier`.

| Verdict | Observed `test_higher_barrier` | Observed `test_lower_barrier` |
|---|---|---|
| **correct** | q05 > 0 | q95 < 0 |
| **incorrect** | q95 < 0 | q05 > 0 |
| **inconclusive** | q05 ≤ 0 ≤ q95 | q05 ≤ 0 ≤ q95 |
| **undetermined** | no finite Δ | no finite Δ |

In words:
- A prediction is **correct** when the central 90 % interval of the predicted barrier difference excludes zero on the observed side. That is, at least 95 % of the propagated input uncertainty puts the barriers in the observed order.
- It is **incorrect** when that interval excludes zero on the opposite side.
- It is **inconclusive** when the interval contains zero: the barrier difference lies within the propagated uncertainty. This includes draws in which both surfaces clip to the same boundary (Δ = 0 exactly).
- It is **undetermined** when the pipeline gives no finite Δ for the case.

**Misses.** Incorrect, inconclusive and undetermined cases all stay in N and count as not correct. An undetermined prediction counts as a miss. The rule therefore cannot be met by retreating into uncertainty or by failing to predict.
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

**The retrodiction passes if at least 10 of the 12 usable cases are correct.** The chance probability of reaching that by coin flips is 79/4096 = 0.0193. The rule is unchanged from version 1.

**No constant-predictor baseline (cp3 R9).** Decision D17 had added a constant-predictor baseline that must fail. It is removed: all 12 observed relations are `test_higher_barrier`, so a predictor that always answers "test higher" scores 12 of 12, and no baseline of that kind can fail on this set. The labels are kept out of the prediction instead (condition 4 and the swap check), and the permutation null of section 4 is reported as a descriptive control.

## 4. Conditions the run must meet

1. **Frozen inputs.** `cases.yaml` and this file are byte-identical to the fixed-before-run commit. The run records both sha256 hashes and the commit in `results/results.json` (`SCHEMA.md`, section 5).
2. **Parameter keys.** Every `params_key` named in `cases.yaml` exists in `lit/params.yaml` at tag p0-cp3.
   - A shared prior is drawn from the table's own prior for its key. A case input that names a key carries that key's prior, or the registered treatment of a gap key, as stated in its `basis`.
   - Otherwise the run stops BLOCKED. No substitute value is used.
3. **Fixed mappings.** The input-to-contract mappings are those of `SCHEMA.md`, section 4, with the interface each input names. The route fixed per case (for example DFS rather than COSMO-RS in RC04 and RC05) is not changed.
4. **Label symmetry and the swap check.** The code that computes a barrier receives the inputs of one surface and the shared draws only. It never sees the observed relation or which surface is the reference. As a check, the run swaps test and reference for every case and confirms that Δ changes sign draw by draw. The swap check stands as in version 1; a failure is reported as a defect of the run.
5. **Permutation null (cp3 R9, descriptive).** The surface input sets are shuffled across the test and reference assignments, and the number of correct verdicts is recorded for each shuffle.
   - **What moves.** A surface input set is the drawn template inputs of one surface of one case. Each case keeps its shared draws and its observed relation. Input sets move only between surfaces whose inputs use the same interface mapping, because an input of one kind cannot feed another mapping.
   - **Within studies.** The input sets of a study's cases (test and reference slots together) are permuted over those slots.
   - **Across studies.** The input sets of all cases with the same mapping are permuted over all their slots.
   - **Count.** 2000 permutations per scheme, from the root seed. A case whose two slots receive the same input set gives Δ = 0 and an inconclusive verdict.
   - **Report.** For each scheme: the distribution of the number correct of 12, its median and central 95 % range, and the fraction of permutations at or above the observed count.
   - **Role.** The null does not gate. It shows how many correct verdicts the input values give when their assignment to surfaces is broken.
6. **Results only.** No mock or draft prior enters a reported result (track rule R-dry).

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
- **Correlations already published.** In 11 of the 12 cases the source itself reports the correlation between the input and the outcome (`link_reported_in_source: true`). For example, Hamm et al. (2014) correlate DFS binding energies with B, and Giuffre et al. (2013) correlate γ_S-air with B. So the test checks the pipeline's mapping and signs (sign-flip SF1 in `theory/contract.yaml`), not new physics. RC11 is the exception.
- **Strong assumptions.**
  - RC11 rests on a common Ca-free contact for a CH3 and a COOH surface (A-RC11-1), on single-entry bookkeeping of the bound Ca²⁺ (A-RC11-6) and on a gap key, δ_s, under its registered geometric bound (A-RC11-5). Under contract v3 the Ca²⁺ binding acts on γ_sl, and the sign of RC11's prediction is set by the c_local ordering for any positive Γ_s and δ_s.
  - RC12 rests on configurational MD energies and on deposit mass (A-RC12-1, A-RC12-2).

  These are the weakest cases. They are kept because they are the only usable methyl and catechol cases, not because of an expected result.
- **Coverage.** No usable hydroxyl-terminated case could be built: RX01, RX03, RX05 and RX08 are excluded, with reasons in `cases.yaml`. The gap stands as recorded (ruling E, decision D16, option 1); no case was added. A result on this set says nothing about hydroxyl-terminated templates.
- **Absolute barriers are not tested.** Only the sign of a within-study difference is scored, so absolute barriers, and the C3 threshold of `theory/thresholds.md`, are not tested.

## 6. What is reported

**If the rule is met.** Report:
- X of N, the chance probability, and the conclusive-only and study-level tallies;
- the swap check and the permutation null;
- every inconclusive, incorrect and undetermined case, with its boundary mass;
- the limits of section 5.

The supported statement is limited to this: the template channel of the C3 barrier reproduces the sign of within-study measured orderings in X of N cases. It is not a claim about absolute barriers, kinetics, or the P0 system itself.

**If the rule is not met.** Diagnose and report. Never tune. For each incorrect, inconclusive or undetermined case, report:
1. the interface and the input that dominated Δ;
2. whether a flagged assumption carries the case;
3. the boundary mass;
4. whether the inputs or the outcome reading, rather than the C3 model, are the likelier cause, or whether the cause is in the model, for example the single-entry bookkeeping of bound Ca²⁺. Two input examples: the {104}-for-(012) face substitution, or the common-prefactor reading of a deposit mass.

The result of the frozen set is reported as the result, whichever way it falls.

**Changes after the run.** After the first run, none of the following may change for this criterion:
- the cases;
- the inputs and their distributions;
- the mappings;
- the 90 % level;
- k.

Any change makes a new criterion version with a dated deviation entry (`ops/tracks/p0_deviations.md`), and the frozen version's result is still reported first.
