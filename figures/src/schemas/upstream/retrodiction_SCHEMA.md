# Retrodiction case and outcome schema

Session P0-W2.2, lane p0-w2; revised in P0-W2.3 before the run (interface per input, contract-v3 bookkeeping, result record). This file defines `preprint/retrodiction/cases.yaml` (the frozen cases) and the result record that the retrodiction run (P0-W2.3) writes. Figure 4 (lane p0-w6) and the run conform to it. `src/nacre/retro/cases.py` validates `cases.yaml` against it (`uv run nacre retro check`).

The pass rule is in `criterion.md`. Both files, with this one, were fixed and committed together before any retrodiction run.

## 1. What a case is

A case is one **pairwise, same-study comparison**: a *test* surface against a *reference* surface, both measured in one study under the same solution conditions. The observed outcome says which of the two has the higher heterogeneous nucleation barrier, or is read as having it. The pipeline is scored on whether its predicted barrier difference has the same sign.

Every case is binary, so a chance prediction is right with probability 1/2. This is the coin-flip null of `criterion.md`.

### Why pairwise and same-study

- **Shared conditions.** Inside one study the supersaturation, pH, temperature, ionic strength, flow and detection method are common to both surfaces. They largely cancel in the comparison.
- **Shared bulk inputs.** The template-independent bulk inputs are the same for both surfaces: γ_nl, V_m, T and Ω_bulk. They are drawn once per Monte Carlo draw and used for both surfaces.
- **What is actually tested.** The comparison tests the template-dependent channel and the pipeline's sign conventions, which are the C3 claim. It does not test the absolute value of a barrier, which classical theory at the nanometre scale cannot supply (contrary entry B7).

## 2. Selection rules (outcome-blind)

These rules were applied to every candidate before any prediction was made.

1. **Candidates.**
   - Every `retro_candidate = y` row of `lit/evidence_table.csv` (49 rows on day 1, cross-referenced by `row_id`).
   - Studies found by the searches logged in `ops/reports/P0-W2.2.md`, run for terminations with thin coverage (methyl, hydroxyl, catechol).
2. **Mineral.** The mineral is CaCO3.
   - Calcium phosphate cases are excluded. The P0 chain is framed for CaCO3, and its K_sp, V_m and γ_nl priors are for calcite and ACC.
3. **Reference surface.** Each study names one reference surface:
   - (a) the control or reference named by the authors;
   - otherwise (b) the carboxyl-terminated surface for SAM series;
   - otherwise (c) chitosan for polysaccharide series, because chitosan is P0's template candidate.

   Every other surface in the study that has a directional outcome against the reference gives one case. Surfaces are not paired with each other.
   - This bounds the number of cases per study.
   - It avoids choosing pairs after seeing their inputs.
4. **One condition per study.** If a study reports one comparison at several conditions, the condition closest to R-slurry is used: room temperature, alkaline, aqueous. There is one case per surface pair.
5. **Directional outcome.** The outcome must imply an ordering of barriers.
   - **Excluded.** Outcomes that report only a pathway (ACC first versus direct calcite), a polymorph, an orientation, or an equality of barriers.
   - **Excluded.** Outcomes driven by an applied potential (cathodic deposits).
6. **Independent inputs.** Every template-dependent input is one of the following:
   - measured or computed independently of the nucleation outcome it is compared with (force spectroscopy, contact angles, simulations, ion-selective electrode data);
   - a declared assumption, flagged `assumption: true`, with its basis.

   An interfacial energy fitted from the same nucleation rates (a γ_net or α′ from the slope of ln J against σ⁻²) is the outcome restated. It can never be an input. Cases whose only inputs are of that kind are excluded as circular.
7. **Usable status.** A case is `usable` only if its outcome and every input carry a DOI and a locator, or name a `lit/params.yaml` key. Otherwise it is `excluded` with a reason.

## 3. `cases.yaml` layout

```yaml
schema: retro-cases/v1
session: P0-W2.2
fixed_before_run: true
shared_priors: {<name>: <prior>}     # template-independent inputs, shared within a pair
studies:      [<study>]
cases:        [<case>]
```

### 3.1 Study

| Field | Type | Meaning |
|---|---|---|
| `id` | `S-<AUTHOR><YEAR>` | unique |
| `doi` | DOI | the study |
| `citation` | string | authors, journal, volume, pages, year (Crossref) |
| `read` | `full text` or `abstract` | what this lane read |
| `route` | string | open route of the copy that was read (local-only copy, not committed) |
| `conditions` | mapping | `mineral`, `polymorph`, `supersaturation`, `pH`, `T`, `ionic_strength`, `method`; each value as reported, with `locator` |
| `reference` | string | the reference surface chosen under rule 3, with the sub-rule used |

### 3.2 Case

| Field | Type | Meaning |
|---|---|---|
| `id` | `RC<nn>` (usable) or `RX<nn>` (excluded) | unique |
| `study` | study id | |
| `termination` | `carboxyl`, `hydroxyl`, `methyl`, `amine`, `catechol`, `thiol`, `phosphate`, `mixed`, `polysaccharide`, `peptoid`, `metal`, `mineral` | chemistry class of the test surface |
| `templated` | `none`, `chitosan`, `polysaccharide`, `polypeptide`, `peptoid`, `pda` | the organic template in the pair; `chitosan` marks chitosan-templated mineralisation (chitosan as the test or the reference film) |
| `test`, `reference` | `{label, chemistry}` | the two surfaces |
| `mineral`, `polymorph` | string | the observed phase |
| `conditions` | mapping | overrides of the study conditions, if any |
| `outcome` | outcome | see 3.3 |
| `channel` | `theta`, `omega` | the barrier channel through which the inputs act (`theory/contract.yaml`, `no_double_counting`). Under contract v3 every template input acts through θ and Ω is the bulk value, so a usable case has `theta`; `omega` survives on excluded cases only |
| `inputs` | list of input | see 3.4 |
| `assumptions` | list of `{id, text}` | every modelling assumption of the case, ids `A-<case>-<n>` |
| `evidence_rows` | list of `row_id` | rows of `lit/evidence_table.csv` behind the case, if any |
| `link_reported_in_source` | bool | true when the source itself reports the input–outcome correlation the case tests |
| `negative` | bool | true when the test surface shows suppressed or absent nucleation relative to the reference |
| `status` | `usable` or `excluded` | |
| `exclusion_reason` | string | required when excluded |

A usable case names a study described under `studies`. An excluded case may name a study that is not described there; its outcome DOI and locator identify the source, and its `inputs` may be empty. The outcome-consistency rules of 3.3 apply to usable cases only.

### 3.3 Outcome

| Field | Values | Meaning |
|---|---|---|
| `comparison` | `pairwise` | the only comparison type in v1 |
| `observable` | `cnt_slope_B`, `nucleation_rate`, `induction_time`, `onset_supersaturation`, `presence_absence`, `deposit_mass` | what was measured |
| `test_value`, `reference_value` | number, or `present` / `absent` | as reported |
| `unit` | string | for numeric values |
| `relation` | `test_higher_barrier` or `test_lower_barrier` | the barrier ordering the observation implies |
| `reading` | string | how the observable maps to the barrier, with its assumption |
| `doi`, `locator` | | where the outcome is stated |

Consistency rules (checked by the validator):

| Observable | `test_higher_barrier` holds when |
|---|---|
| `cnt_slope_B` | \|B_test\| > \|B_ref\|, since B is proportional to the barrier at fixed σ |
| `induction_time`, `onset_supersaturation` | test > reference |
| `nucleation_rate`, `deposit_mass` | test < reference. This assumes a common kinetic prefactor, which must be declared as an assumption |
| `presence_absence` | test is `absent` and reference is `present` |

**Rates against barriers.** A rate or count orders surfaces by barrier only if the kinetic prefactor is common.
- Nielsen et al. (2020) and Giuffre et al. (2013) show that this fails: the lowest-B surface had the slowest rate at the experimental σ.
- So `cnt_slope_B` is used wherever a study reports B.

### 3.4 Input

| Field | Meaning |
|---|---|
| `symbol` | a `theory/symbols.yaml` id, or a case-level quantity named in `maps_to` |
| `role` | `test`, `reference` or `shared` (shared inputs are drawn once per draw for both surfaces) |
| `interface` | the interface the input acts on: `gamma_sn`, `gamma_sl`, `gamma_nl`, `net` (the net energy of a simulated nucleus), `bulk` (Ω, T, V_m, c_bulk) or `young` (a shared nuisance Young ratio); required on every usable input and on every shared prior |
| `interface_mapping` | for a surface input (test or reference), the mapping that reaches its interface: `dupre` (→ γ_sn), `gibbs_langmuir` (→ γ_sl), `owrk` (→ γ_sl) or `net`; required for those symbols, absent otherwise |
| `value` / `distribution` | a number (or a mapping of named numbers) with `unit`, or one of `{type: normal, mean, sd}`, `{type: uniform, low, high}`, `{type: loguniform, low, high}` (log of the value uniform), `{type: uniform_log, low_sigma, high_sigma}` (σ = ln Ω uniform; Ω = exp σ) |
| `unit` | |
| `doi`, `locator` | the source, **or** `params_key` (a `lit/params.yaml` key) |
| `evidence_row` | `row_id` in `lit/evidence_table.csv`, if any |
| `maps_to` | how the input enters the contract (for example `cos_theta_young` via Young–Dupré) |
| `assumption` | true when the value or its distribution is assumed, not reported; `basis` is then required |
| `derived_from_outcome` | must be false; true makes the case invalid as usable (rule 6) |

**Pending parameter keys.** `lit/params.yaml` does not yet exist on any branch (lane p0-w1, P0-W1.2).
- An input that names a `params_key` also lists the `evidence_rows` the key is to be built from.
- W2.3 checks that each key exists and reads from those rows before the run.
- A missing key is a BLOCKED precondition of W2.3, not a reason to substitute a value.

## 4. How the run maps inputs to the contract

All mappings use the registered convention of `theory/contract.yaml` (version 3):
- cos θ = (γ_sl − γ_sn0 − Δγ_w)/γ_nl, with γ_sl = γ_sl0 + Δγ_ads;
- ΔG*_het = f(θ) ΔG*_hom(Ω_bulk);
- f(θ) = (2 + cos θ)(1 − cos θ)²/4.

**Bookkeeping (contract v3).** At equilibrium the Ca²⁺ and CO3²⁻ electrochemical potentials are uniform, so the driving force at the template is the bulk one, k_B T ln Ω_bulk. Ca²⁺ binding enters the barrier only through Δγ_ads on γ_sl. A mapping through Ω_local is refused by the run code and by the validator.

**Interfaces in water.** Interfacial energies obtained in water are full in-water free energies, so Δγ_w = 0. The contract says it must then not be added again.

| Input kind | Interface | Mapping (`interface_mapping`) |
|---|---|---|
| Crystal–template adhesion: binding free energy ΔG_b per contact area a (force spectroscopy of calcite on monolayers, in water) | γ_sn | Dupré (`dupre`): W = \|ΔG_b\|/a = γ_nl + γ_sl − γ_sn, so cos θ = W/γ_nl − 1. a is shared within a study |
| Crystal–template adhesion: simulated interaction energy E of a CaCO3 cluster with the hydrated substrate | γ_sn | Dupré (`dupre`): W = \|E\|/A_c with a common contact area A_c, then as for ΔG_b |
| Ca²⁺-binding data: near-surface Ca²⁺ concentration c_local against bulk c_bulk | γ_sl | Gibbs–Langmuir (`gibbs_langmuir`): Δγ_ads = −R T (Γ_s ln(1 + x) − δ_s c_bulk), x = c_local/(c_max − c_local), c_max = Γ_s/δ_s; cos θ = cos θ0 + Δγ_ads/γ_nl, with the Ca-free contact cos θ0 a shared nuisance (declared assumption). Γ_s and δ_s are shared |
| Contact-angle surface energies: OWRK components of the substrate film measured in air (γ_s^d, γ_s^p) | γ_sl (against water) | OWRK (`owrk`): γ_sl = γ_s + γ_w − 2(√(γ_s^d γ_w^d) + √(γ_s^p γ_w^p)). With γ_sn equal for both surfaces (declared assumption), cos θ_test = cos θ_ref + (γ_sl,test − γ_sl,ref)/γ_nl, where cos θ_ref is a shared nuisance |
| Simulated net interfacial energy γ_net of the crystal–substrate–liquid system | net | `net`: same nucleus shape for both surfaces, f(θ) = (γ_net/γ_nl)³ |

Shared inputs name `bulk` (Ω, T, V_m, c_bulk, K_sp), `gamma_nl`, `young` (cos θ_ref, cos θ0), `gamma_sn` (the contact area of a Dupré mapping) or `gamma_sl` (Γ_s and δ_s of a Gibbs–Langmuir term; the water OWRK components).

**Clipping.** cos θ outside [−1, 1] is clipped to θ = 0 or π, and the boundary mass is reported (lane note N2).

## 5. Result record (written by P0-W2.3)

The file is `preprint/retrodiction/results/results.json`. Its schema id is `retro-results/v1`. Fields beyond those below (per-case `mapping`, `interface`, `swap_check`, `nonfinite_fraction`; the summary's `undetermined`, `swap_check`, `permutation_null`, conclusive-only and study-level tallies) are added by the run and are additive.

```json
{
  "schema": "retro-results/v1",
  "mock": false,
  "cases_sha256": "sha256:<hex of cases.yaml bytes>",
  "criterion_sha256": "sha256:<hex of criterion.md bytes>",
  "fixed_before_run_commit": "<40-hex>",
  "provenance": {"git_sha": "<40-hex>", "git_dirty": false, "contract_sha": "<40-hex>", "params_tag": "p0-cp3", "params_file_hash": "sha256:<hex>", "criterion_sha": "<40-hex>"},
  "draws": 20000, "seed": 0,
  "cases": [{
    "id": "RC01",
    "label": "C16-SH vs C16-COOH (Hamm 2014)",
    "termination": "thiol",
    "negative": false,
    "observed_relation": "test_higher_barrier",
    "barrier_test":      {"median": 0.0, "q05": 0.0, "q95": 0.0},
    "barrier_reference": {"median": 0.0, "q05": 0.0, "q95": 0.0},
    "delta":             {"median": 0.0, "q05": 0.0, "q95": 0.0},
    "p_test_higher": 0.0,
    "boundary_mass": 0.0,
    "verdict": "correct | incorrect | inconclusive | undetermined"
  }],
  "summary": {"N": 0, "correct": 0, "incorrect": 0, "inconclusive": 0, "undetermined": 0, "k": 0, "chance_probability": 0.0, "pass": false}
}
```

**Field definitions.**
- **Barriers.** All are in units of k_B T, evaluated at the pair's shared Ω.
- **`delta`.** This is barrier_test − barrier_reference.
- **Verdicts.** Verdicts follow `criterion.md`.

**Figure 4.** Lane p0-w6 replaces its assumed `fig4-retrodiction/assumed-v0` input with this record.
- It drops `threshold`, `barrier_crit` and the binary `layer_formed` / `no_layer` outcome: v1 cases are orderings, not threshold crossings.
- It plots `delta` with its 90 % interval per case.
- The observed relation and the verdict go in the caption, per the figure rules.
