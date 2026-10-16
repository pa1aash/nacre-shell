# Checkpoint cp2 brief: equation sheet, derivation signs, thresholds

Session P0-W3.2, lane p0-w3. Contract v2 is at `5811a6b`, thresholds at `3c9568b`.
`theory/tools/check_contract.py` passes: 42 functions, every monotonicity and sign proven
symbolically, plus the thresholds block. Equation numbers refer to `theory/build/derivation.pdf`
(this build), with stable labels in brackets.

## What cp2 audits

1. **Sign convention (unchanged from P0-W3.1).**
   - theta is measured through the nucleus, and cos(theta) = (gamma_sl - gamma_sn)/gamma_nl with
     the bare gamma_nl.
   - Delta_gamma_w = gamma_sn - gamma_sn0 > 0 is a cost on the substrate side.
   - S = IAP/K_sp = Omega, with Delta_mu = k_B T ln Omega per CaCO3 formula unit and V_m per
     formula unit (F3).
   - Pointers: derivation Section 6, Eqs. (25) to (28); contract SF1; equation sheet Sections 3
     and 5. One deviation was fixed: the old derivation let the letter S denote the per-ion root.
2. **Q1 and Q2 result: the bookkeeping rule.**
   - At equilibrium the electrochemical potentials of Ca2+ and CO3^2- are uniform (Eq. (12)
     [th:eq:uniform]), so the driving force at the template is k_B T ln Omega_bulk (Eq. (13)
     [th:eq:dmu-uniform]).
   - Specific binding raises the local concentration exactly as much as it lowers the local
     standard potential (Eq. (14) [th:eq:no-gain]).
   - A mean potential cancels in the neutral solid and in the ion product, which settles Q2.
   - Uniform chemical potential is the consistent bookkeeping. Local-ideal hides the assumption
     that the layer is a reservoir held above the bulk.
   - The bound Ca2+ belongs to the template-liquid interface only, through the Gibbs-Langmuir term
     Delta_gamma_ads = -R T (Gamma_s ln(1 + x) - delta_s c_bulk) (Eq. (30) [th:eq:gibbs]).
   - At fixed gamma_sl0 and gamma_sn, stronger binding raises the barrier: SF2 reversed against
     v1 (Eq. (31) [th:eq:young-ads]). Binding helps only if gamma_sn falls by more than gamma_sl
     does.
3. **No-double-counting proof.**
   - Pointers: derivation Section 7, the grand potential of a cap (Eq. (29) [th:eq:grand]) and
     the screen composite (Eq. (32) [th:eq:composite]).
   - The screen rule is in Section 7 (rule): Omega_bulk only; Delta_G_seq enters once, through
     Delta_gamma_ads; nothing is added when gamma_sl is computed in situ.
   - Checked mechanically: channel partition, the Omega channel free of template inputs, single
     entry, and the two named demonstrations (`DG_het_local_ideal`, `DG_het_double`).
4. **Thresholds** (`theory/thresholds.md`).
   - One band-mass rule at a credible level p.
   - C1 and C2: sign with a margin.
   - C3: a single physical edge at f = 1/2, which replaces the deck bands, plus the
     accessibility bound below.
   - C4: S_spread >= m_S, with coalescence as the independent supporting condition.
   - C5: the hull tolerance from the formation-energy error, and the Li-window rule in which
     "undetermined" never passes.
   - The study rule includes the F1 deletion test.
5. **C3 absolute-barrier derivation.** J = J_0 exp(-DG_het/k_B T) gives
   N_nuc = J t_p >= N_req, equivalently DG_het <= B_acc = k_B T ln(J_0 t_p / N_req) (Eqs. (23)
   and (24) [th:eq:rate, th:eq:access]). The keys are `regimes.R-slurry.parameters.J0_het`,
   `regimes.R-slurry.parameters.t_proc` and `thresholds.C3.N_req`.
6. **Q9, the R-cell oxidation sink** (derivation Section 9, Eq. (40) [th:eq:sink]).
   - The sink is fixed by the electrolyte. Electroneutrality pairs the released Ca2+ or Al3+ with
     the salt anion, and the electrons plate Li from LiA.
   - Rule: only the registered salt's anions are admissible; take the minimum over sinks and over
     the registered gas-reference schemes; a solid-salt limit is an upper bound on the onset;
     "undetermined" never passes.
   - Inputs, not adjudicated: W5's CaCO3 onsets under the two CO2 references, and Al2O3
     undetermined under nitrate but finite under sulfate or chloride (`ops/reports/P0-W5.1.md`,
     R-cell section).
7. **Remaining questions for cp2:** Q8, Q9, Q13 and Q14 (`theory/open_questions.md`,
   Dispositions). Q1, Q2, Q6, Q11 and Q16 are resolved. Q3, Q4, Q5, Q7, Q10, Q12 and Q15 are
   deferred, with an owner for each.

## Charter wording change requested (A5)

The register's C2 mapping (enrichment, then local S) is inconsistent at equilibrium. The
replacement text for `charter/claim_register.yaml`, claim C2, is given here. It is applied only
through the audit fix list, one commit per fix, by the integrator.

- **`physical_observable.definition`:** "Free energy of moving one Ca2+ from the hydrated bulk
  reference (Ca2+(aq) at the regime activity) to a template binding site, built as a
  thermodynamic cycle with protonation-state and ionic-strength corrections at the regime pH. It
  sets the site occupancy and the Ca2+ surface excess at the regime activity (Langmuir) and,
  through the Gibbs adsorption equation, the change Delta_gamma_ads of the template-liquid
  interfacial energy consumed by C3. The enrichment factor c_local/c_bulk = exp(-Delta_G_seq / RT)
  is a concentration ratio and is reported; it does not change the supersaturation, which at
  equilibrium is the bulk S = IAP/K_sp at the template."
- **`physics`:** "The template sequesters Ca2+ only if it holds Ca2+ more strongly than water
  does. Delta_G_seq measures precisely that competition, with the hydration free energy of Ca2+ on
  the reference side of the cycle, so a negative value means net binding at the interface and a
  positive one means the polymer is a worse ligand than bulk water. At equilibrium the
  electrochemical potential of Ca2+ is the same at the site as in the bulk, so binding raises the
  local concentration but not the driving force for nucleation. Its effect on nucleation runs
  through the interfacial energies: bound Ca2+ lowers the template-liquid energy, which at a fixed
  template-nucleus energy raises the heterogeneous barrier, and binding favours nucleation only if
  the template-nucleus energy falls by more. C2 establishes the binding link; C3 judges its
  consequence."

Consequential fields, with the same physics, proposed for the same fix:

- **C3 `physical_observable.definition`**: "using the local S from C2" becomes "at the bulk S of
  the regime state, with the C2 adsorption term inside gamma_sub,liq".
- **C3 `physics`**: "the local supersaturation S from C2" becomes "the bulk supersaturation of
  the regime state; the template's Ca2+ binding enters through gamma_sub,liq (C2), not through S".
- **C3 `kill_criterion`**: "at the C2 local supersaturation" becomes "at the regime bulk
  supersaturation".
- **C3 `depends_on_rationale`**: "the local supersaturation S comes from the C2 enrichment factor"
  becomes "the C2 binding enters gamma_sub,liq through the Gibbs adsorption term".
- **C5 `physics`**: the last two sentences become "If the bulk S is below 1, CaCO3 is unstable
  against dissolution at the template as well, because at equilibrium enrichment does not raise
  the driving force. C5 is decided at the bulk state; an evaluation at the C2-enriched
  concentrations is reported only as a labelled non-equilibrium sensitivity."
- **C5 `computation.method`**: "it is reported for both the bulk state and the C2-enriched state"
  gains ", the latter as a labelled non-equilibrium sensitivity that never decides the verdict".
- **C3 open item (design flag 3)**: record the registered Delta_gamma_w convention (item 1 above).

## Decisions requested

1. Accept the Q1 and Q2 result and the screen rule (derivation Section 7, rule; contract v2).
2. Approve the C2 replacement wording and the consequential C3 and C5 fields above, for the
   integrator's fix list.
3. Approve the C3 rule: the deck bands are replaced by the single edge f = 1/2 (cos(theta) = m_cos,
   with m_cos = 0 proposed), and the accessibility bound DG_het <= B_acc is the absolute
   criterion.
4. Fix N_req: either the C4 closure density (proposed, so that "enough nuclei" means "enough to
   close the film") or a separately registered areal density.
5. Q9: approve the sink rule. Then decide whether the solid-salt sink is the registered sink, so
   that a pass computed with it counts as feasible conditional on it, or whether the solvated
   sink is required (undetermined until the Ca2+ and Al3+ solvation free energies relative to
   Li+ are fetched).
6. Q8: approve the C5 R-slurry rule: regime activities at the bulk state, worst (pH, E_SHE)
   point, tolerance n_at e_f / n_M, and the ACC edge (n_at e_f + Delta_ACC)/n_M.
7. Q13: keep IAP = a_Ca a_CO3 in P0, with the hydrated form as a stated limitation for the drying
   states (proposed), or add a_w^n and n to the contract before cp3.
8. Q14: accept the square-lattice closure as the optimistic supporting condition of C4, with the
   random-site uncovered fraction deferred.
9. Approve C4: S_spread >= m_S is the chosen criterion. A falsified verdict needs the coalescence
   condition to fail as well; island growth with credible closure is inconclusive.
10. Set the registration conventions `thresholds.decision.credible_level` (p > 1/2) and
    `thresholds.decision.degrade_mass_min`. Approve state aggregation: worst state per link, and
    a path sum for C3 accessibility.
11. Resolve the h_c name collision carried from P0-W3.1. The theory's `h_c` is the geometric cap
    height at first contact; the charter's C4 (c) h_c is a kinetic critical coalescence
    thickness. Proposed: the charter's quantity takes another name.

## cp2 ruling and the charter texts for the integrator (P0-W3.2 fix-up)

The planning chat ruled on checkpoint cp2 on 2026-10-17: PASS once fixes F1 to F9 are applied
as written. The fixes, their commits and a one-line summary of each are in `theory/cp2_fixes.md`.
Accepted without change: uniform chemical potential as the bookkeeping rule; Delta_G_seq acts
only through Delta_gamma_ads; contract v2. The integrator applies every charter text below
through the audit fix list, one commit per fix. This lane does not edit `charter/**`.

### A. C2 wording (fix F3; approved charter text)

- **C2 `physical_observable.definition`:** the text drafted above under "Charter wording change
  requested (A5)", unchanged.
- **C2 `physics`:** the text drafted above, followed by this sentence: "C2 is a binding
  descriptor. It enters C3 only through Delta_gamma_ads and is not an independent kill
  criterion."
- **Consequential C3 and C5 fields:** the seven items drafted above under "Consequential
  fields", unchanged.

### B. `charter/deletion_register.yaml`, step `sequester` (claim C2): replacement rows (fix F3)

No row may show enrichment raising S. Replacement text, field by field:

- **`survives_without_mechanism`:** "Whatever Ca2+ affinity the hydroxylated oxide has on its
  own. Binding raises the local Ca2+ concentration, not the supersaturation: at equilibrium the
  template sees the bulk S. The binding reaches nucleation only through the template-liquid
  energy (Delta_gamma_ads in C3), so this step is reported as a binding descriptor and is not a
  deletion link."
- **`controls`:**
  - `bare_oxide`: computation "Delta_G_seq, Theta_occ, Gamma_Ca and Delta_gamma_ads for Ca2+ at
    bare oxide sites"; expected_direction "weaker binding (less negative Delta_G_seq) than the
    template; reported, and its consequence judged in C3".
  - `catechol_only`: computation "Delta_G_seq at catechol/catecholate sites at the regime pH";
    expected_direction "weak binding if catechol is largely protonated (design flag 4)".
  - `chitosan_only`: computation "Delta_G_seq at chitosan sites"; expected_direction "weaker
    binding than the combined PDA/chitosan template".
  - `carboxylate_substituted`: computation "Delta_G_seq at carboxylate sites"; expected_direction
    "possibly more negative than PDA; if so the transplant table changes (design flag 4)".
  - `PVDF`: computation "Delta_G_seq near PVDF fragments"; expected_direction "no net binding
    (Delta_G_seq not negative)".

Two consequential texts follow directly from the ruled `deletion_test.links = [C3, C4]`:

- **`rule`**, first sentence after "The verdict must degrade when the nacre mechanism is
  removed.": "...the study-level verdict must move toward falsified on at least one of C3 or C4.
  If it does not (or if only C1 degrades), the paper is a generic adhesion study..." (C2 is
  dropped from the list; the rest of the paragraph is unchanged).
- **Step `nucleate`, control `catechol_only`, `expected_direction`:** "higher barrier than the
  full template if the template-crystal contact needs chitosan" (replaces "if enrichment needs
  chitosan").

### C. Consistency of the C2 register entry: needs a ruling, not approved text

With C2 no longer gating, three fields of `charter/claim_register.yaml` C2 still describe a gate:
`kill_criterion`, `verdict_bands` and `threshold.status`. The texts below are a **proposal for
the planning chat**, not approved charter text. The integrator should not apply them until they
are ruled on.

- `kill_criterion.statement`: "None. C2 is a binding descriptor. It enters C3 only through
  Delta_gamma_ads and is not an independent kill criterion. If Delta_G_seq is not negative under
  the registered decision rule, the report states the finding that the sequestration premise
  fails."
- `verdict_bands`: replaced by `finding_bands`: holds "Delta_G_seq < 0 with at least the credible
  mass"; fails "Delta_G_seq >= 0 with at least the credible mass"; undecided otherwise.
- `threshold.status`: "descriptor in P0 (theory/thresholds.md, cp2 fix F3); no threshold".
