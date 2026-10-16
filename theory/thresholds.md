# Thresholds and decision rules of the P0 screen (G0 fix F9; checkpoint cp2)

**Written before any screen output existed.** This file was written in session P0-W3.2 on top
of commit `49100a9d92b5dc48f1db1d15529967dfeeece12d` (lane p0-w3, contract v2 at
`5811a6b2b82565a2d7e991987eee6ab4f167959e`). No screen output was run or read in that session
(rule R7). The commit that adds this file is recorded in `ops/state/p0-w3.json` under
`thresholds.sha`.

This file is the threshold authority of track p0 (rule R-thr). `configs/preprint/thresholds.yaml`
(W4) is a copy of the fenced `thresholds` block at the end, and W4 checks the two equal. After tag
`p0-cp3` this file changes only through a dated entry in `ops/tracks/p0_deviations.md`.

No number is typed here (rule R2). Every number a threshold needs is named by the
`lit/params.yaml` key that will supply it, and "Params keys" at the end lists them. Rationals
such as 1/2 are exact values of the theory, not literature values. Equation numbers refer to the
P0-W3.2 build of `theory/build/derivation.pdf`, with the stable label in brackets.

What a verdict means: a link that is "feasible" under these rules meets a necessary condition
under the stated framing and inputs. It does not show that a barrier works, and no rate, capacity
or device statement follows from any rule here (`charter/scope_guard.md`).

## 1. The decision rule shared by every link

**Propagated distribution.** For each registered regime state, W4 propagates the prior-weighted
inputs (`lit/params.yaml`) through the contract functions by Monte Carlo. Each link has one
decisive quantity X (Section 2) and an edge e. The edge is the physical threshold moved by a
systematic margin m in the conservative direction: m covers method error that the priors do not
already carry. Where the priors carry it, W1 sets m to zero and says so.

**Registered statistic.** It is the fraction of prior-weighted mass on each side of the edge:
`P_good` on the side the link needs, and `P_bad = 1 - P_good`.

**Credible-bound condition.** Let p be the credible level (`thresholds.decision.credible_level`,
a registration convention set at cp2, with p > 1/2). Then:

| Verdict | Condition | The same condition as a credible bound |
|---|---|---|
| feasible | `P_good >= p` | the bound at level p on the bad side lies beyond the edge on the good side |
| falsified | `P_bad >= p` | the bound at level p on the good side lies on the bad side of the edge |
| inconclusive | otherwise | the interval at level p straddles the edge |

With p > 1/2, feasible and falsified cannot both hold.

**Clipping (lane note N2).** Draws with Young cos(theta) >= 1 count as theta = 0 (f = 0); draws
with cos(theta) <= -1 count as theta = pi (f = 1). The boundary mass is reported for every link
that uses theta.

**States.** C1, C2, the C3 wetting part, C4 and C5 are necessary at every registered state at
which they apply. A link's verdict is therefore the worst over those states, ordered feasible <
inconclusive < falsified. The C3 accessibility part is cumulative: nuclei may form at any state
along the registered R-slurry path, so it uses the path sum of Eq. (24) [th:eq:access].

**Bookkeeping (contract v2).** Every barrier is evaluated with Omega = Omega_bulk at the regime
activities. The C2 binding enters only through Delta_gamma_ads in gamma_sl (derivation, Section 7
(rule), Eqs. (30) to (32)). `Omega_local_ideal` and the demonstration composites never enter a
verdict.

## 2. Links

### C1, anchoring (R-slurry)

- **Threshold and physics.** X = `W_adh_wet` (J m^-2), the Dupre work in water, Eq. (1)
  [th:eq:dupre], obtained from the PMF, Eq. (3) [th:eq:pmf]. Its sign is the decision. W > 0
  means the contact is lower in free energy than the two water-wetted surfaces, so the template
  stays at the oxide against water. W <= 0 means water displaces it. The bare oxide has W = 0 by
  construction and fixes the zero.
- **Margin.** e = +m_W, where m_W = `thresholds.C1.margin_W_adh_wet` is the systematic error of
  the wet adhesion free energy per area that the prior does not carry. The contact area is defined
  once for all fragments (`thresholds.C1.contact_area_definition`, Q5).
- **Decision.** feasible if `P(W > m_W) >= p`; falsified if `P(W <= m_W) >= p`; inconclusive
  otherwise. This matches the charter bands ("exceeds" and "at or below the registered margin").
- **Terminations.** The populated oxide terminations enter as a discrete input with weights
  `regimes.R-slurry.parameters.termination_weights`, so the band masses are those of the
  population-weighted mixture.
- **Regime.** R-slurry only. Retention in the cell is not judged (layer persistence is a stated
  limitation).

### C2, sequestration (R-slurry)

- **Threshold and physics.** X = `Delta_G_seq` (J mol^-1), the transfer free energy of Ca2+ from
  hydrated bulk to the site, Eq. (4) [th:eq:cycle]. Its sign is the mechanistic statement: the
  template holds Ca2+ more strongly than water does.
- **How C2 is judged after Task A.** Task A moved C2's action on nucleation out of the driving
  force and into the interfacial energies. C2 is therefore judged as the link it names, binding
  against the solvated reference, and nothing more. A feasible C2 no longer implies any help to
  C3. Its consequence for nucleation is judged inside C3, through Delta_gamma_ads, Eq. (30)
  [th:eq:gibbs]. At fixed gamma_sl0 and gamma_sn, that term raises the barrier: SF2, Eq. (31)
  [th:eq:young-ads].
- **Margin.** e = -m_seq, where m_seq = `thresholds.C2.margin_DG_seq` is the systematic error of
  a Ca2+ transfer free energy (hydration benchmark) that the prior does not carry.
- **Decision.** feasible if `P(Delta_G_seq < -m_seq) >= p`; falsified if
  `P(Delta_G_seq >= -m_seq) >= p`; inconclusive otherwise.
- **Reported, not gating.** `Theta_occ` and `Gamma_Ca` at the regime activity, and the
  distribution of `Delta_gamma_ads`. P0 uses one effective site type per template (Gamma_s,
  Delta_G_seq); multi-site populations are deferred (Q4).
- **Regime.** R-slurry, at the regime pH and ionic strength.

### C3, nucleation (R-slurry)

C3 has two parts. Both must pass, as the charter's verdict bands require.

**(a) Wetting part: bands for f(theta).**

- **Threshold and physics.** X = f(theta), with cos(theta) from `cos_theta_template` (or from
  `cos_theta_young` with an in-situ gamma_sl), Eq. (31) [th:eq:young-ads]. The deck's starting
  bands (charter C3 `threshold.proposed`) are **replaced** by one edge at f = 1/2, which is theta = pi/2 and cos(theta) = 0.
  - f = 1/2 is the only value in (0, 1) where the physics changes. There gamma_sl = gamma_sn: the
    sign of the Young numerator flips.
  - For f < 1/2 the template prefers the nucleus to the liquid. This is the minimal content of
    "templating".
  - For f > 1/2 any surface with theta < pi still lowers the barrier relative to homogeneous
    nucleation. The template then does no more than a generic surface: water is a better partner
    for it than the nucleus is.
  - The deck's upper edge falls at an obtuse angle where nothing changes. Its intermediate
    band encoded uncertainty as a fixed interval. Here the credible-mass rule supplies the
    inconclusive verdict, and part (b) carries the magnitude.
- **Margin.** The edge moves to cos(theta) = m_cos, that is f_e = (2 + m_cos)(1 - m_cos)^2/4, with
  m_cos = `thresholds.C3.margin_cos_theta` in [0, 1). The proposal for cp2 is m_cos = 0: the
  method error of each interfacial energy is carried in its prior.
- **Decision.** feasible if `P(f <= f_e) >= p`; falsified if `P(f > f_e) >= p`; inconclusive
  otherwise. The mass at the clipped boundaries (N2) is reported.
- **Framing consistency (Q12).** K_sp, V_m and gamma_nl come from one framing (ACC or calcite),
  keyed by `regimes.R-slurry.parameters.framing`. A draw that mixes framings is refused.

**(b) Accessibility part: absolute barrier in k_B T.**

- **Threshold and physics.** Eqs. (23) and (24) [th:eq:rate, th:eq:access]. Nuclei form on the
  template at J = J_0 exp(-DG_het / k_B T) per area and time. At least the areal density N_req
  must form within the time t_p that the template spends at the registered R-slurry states:
  N_nuc = sum over states k of J_0 Delta t_k exp(-DG_het,k / k_B T) >= N_req. At a single state
  this is

  DG_het <= B_acc = k_B T ln(J_0 t_p / N_req),

  with DG_het at Omega_bulk. A count N on a collector area A enters as N_req = N / A.
- **Keys.**
  - J_0 = `regimes.R-slurry.parameters.J0_het`: a loguniform prior over its fetched range, because
    only ln J_0 enters.
  - t_p = `regimes.R-slurry.parameters.t_proc`: per registered state, slurry contact and drying.
  - N_req = `thresholds.C3.N_req`: the required areal density. Proposal for cp2: the C4 closure
    density, so that "enough nuclei" means "enough to close the film" (decision 4).
- **Margin.** None beyond the J_0 prior. N_nuc ignores exclusion zones, so it is an upper estimate
  and the criterion is necessary, not sufficient. A state with Omega_bulk <= 1 contributes no
  nuclei.
- **Decision.** feasible if `P(N_nuc >= N_req) >= p`; falsified if `P(N_nuc < N_req) >= p`;
  inconclusive otherwise.
- **Reported, not gating.** DG_het / k_B T and the homogeneous reference DG_hom / k_B T at the
  same state.

**C3 verdict.** feasible if (a) and (b) are both feasible; falsified if either is falsified;
inconclusive otherwise.

### C4, conformality (R-slurry for wetting, R-cell for the thickness bound)

- **Chosen criterion (lane note N1).** X = `S_spread` (J m^-2), Eq. (33) [th:eq:spread].
  - Derivation Eq. (35) [th:eq:n1] shows that a small-angle bound theta <= theta_max and
    S_spread >= -s are one criterion at different strictness, both tests of the Young numerator
    relative to gamma_nl.
  - S_spread >= 0 is chosen. It is the strict end (complete wetting) and the only member of the
    family that needs no kinetic or transport scale: a finite theta_max can be justified only
    through the coalescence condition, i.e. theta_max = 2 arctan(d_max sqrt(2 N_s)).
  - It is also defined where Young has no solution.
  - Complete wetting means layer growth: the film is continuous at any thickness, so the thickness
    bound is met by how much mineral is grown, not by coalescence.
- **Margin.** e = +m_S, where m_S = `thresholds.C4.margin_S_spread` is the systematic error not
  carried in the interfacial-energy priors.
- **Supporting condition (independent): coalescence below the thickness bound.**
  - The condition is N_s >= N_s_closure = tan^2(theta/2) / (2 d_max^2), Eq. (36)
    [th:eq:nclosure], with d_max = max(d_max_ohm, d_max_tun), Eqs. (41) to (43).
  - The island density is N_s = N_nuc from C3(b), an upper estimate. A failure of closure with
    N_nuc is therefore conservative, and a success is only optimistic.
- **Decision.**
  - feasible if `P(S_spread >= m_S) >= p`;
  - falsified if `P(S_spread < m_S) >= p` **and** `P(N_nuc < N_s_closure) >= p`: islands that do
    not close below the thickness bound, which is the charter's kill criterion;
  - inconclusive otherwise, including island growth with credible closure. A thermodynamic
    screen cannot exclude a coalesced film there.
- **Regimes.** The wetting energies are R-slurry (solid-water). d_max is the R-cell
  electron-transfer bound and is reported as a limitation, not a performance figure.

### C5, thermodynamic stability (R-slurry and R-cell)

**R-slurry, aqueous Pourbaix.**

- **Threshold and physics.** X = `Delta_G_pbx` (J mol^-1 per non-O, non-H atom), Eq. (37)
  [th:eq:pbx], for the registered CaCO3 framing phase.
  - It is evaluated at the regime activities of Ca2+ and carbonate (F2), at the bulk state: the
    driving force is Omega_bulk (derivation, Section 7, rule 5).
  - An "enriched" evaluation is a labelled non-equilibrium sensitivity, never a verdict.
  - It is evaluated over the registered (pH, E_SHE) region (`regimes.R-slurry.parameters.pH_range`
    and `regimes.R-slurry.parameters.E_SHE_range`), worst point.
- **Tolerance.** tau_hull = n_at e_f / n_M, where e_f = `thresholds.C5.formation_energy_error` is
  the expected error of a computed formation energy per atom, from the database benchmark. Per
  non-O, non-H atom this is the error of the phase's own formation energy, the largest single
  error entering its hull distance. For the ACC framing the edge is
  (n_at e_f + Delta_ACC) / n_M, with Delta_ACC = `regimes.R-slurry.parameters.ACC_offset`. ACC is
  never on the hull, and its metastability above calcite is part of the framing, not an
  instability.
- **Decision.**
  - feasible if `P(Delta_G_pbx <= edge) >= p` at every point, **and** the falsifiability control
    (item 21, W5) fails where it must;
  - falsified if `P(Delta_G_pbx > edge) >= p` at some point;
  - inconclusive otherwise, or if the control passes where it must fail.
- **Al phases.** The native oxide's Pourbaix state is reported as the bare-oxide baseline. It does
  not gate C5, because alkaline attack on the native oxide is the corrosion mode the slurry
  regime describes.

**R-cell, Li-referenced window.**

- **Threshold and physics.** Eq. (39) [th:eq:window] with the electrolyte-fixed sink of Eq. (40)
  [th:eq:sink] for CaCO3 and the protecting Al phases (`regimes.R-cell.parameters.al_phases`).
  The registered regime potential range [E_cell_min, E_cell_max] (V vs Li+/Li,
  `regimes.R-cell.parameters.E_min` and `regimes.R-cell.parameters.E_max`) must lie inside every
  window:

  E_red + m_E <= E_cell_min and E_cell_max + m_E <= E_ox.

- **Margin.** m_E = `thresholds.C5.window_margin`, the expected error of a computed reaction energy
  per transferred electron, derived by W1 from `thresholds.C5.formation_energy_error`.
- **Reference schemes.** Each limit is the lowest (E_ox) or highest (E_red) over the registered
  CO2 and O2 reference schemes (`regimes.R-cell.parameters.gas_reference_schemes`).
- **Undetermined never passes.** A limit with status `undetermined` (a missing sink phase, an
  unregistered salt, or an unbounded Li-open limit) gives at best inconclusive. The same holds if
  E_cell_max is not registered.
- **Solid-salt sink.** With the solid-salt sink alone, E_ox is an upper bound on the true onset.
  A falsification computed with it stands. A pass is conditional on the sink and counts as
  feasible only if cp2 accepts the solid-salt sink as registered (decision 5); otherwise it is
  inconclusive.
- **Decision.** feasible if both inequalities hold for every gated phase; falsified if either
  fails beyond its margin (E_ox < E_cell_max - m_E, or E_red > E_cell_min + m_E) for any gated
  phase; inconclusive otherwise. The limits are deterministic, so the band mass is 0 or 1 for each
  scheme.
- **W5's reported limits (inputs to the decision, not adjudicated here).** `ops/reports/P0-W5.1.md`
  (R-cell section) reports:
  - a CaCO3 oxidation onset under the nitrate sink that differs by the CO2 reference (JANAF
    against the Materials Project CO2 energy), with the spread stated there;
  - an Al2O3 limit that is undetermined under nitrate (sink phase missing) and finite under
    sulfate or chloride.

  Under this file, the CaCO3 limit is the lower of the two schemes, and Al2O3 under a nitrate
  electrolyte stays undetermined (never a pass) until the sink thermochemistry is fetched.

**C5 verdict.** feasible if both regimes are feasible; falsified if either is falsified;
inconclusive otherwise.

## 3. Study-level verdict

- **Combination.** The study is
  - falsified if any of C1 to C5 is falsified. C1 to C4 are sequential links, any one of which
    can end the mechanism; C5 is a necessary screen;
  - feasible only if all of C1 to C5 are feasible and the deletion test below holds;
  - inconclusive otherwise.
- **Deletion test (`charter/deletion_register.yaml`, F1).** Only the controls that remove the
  mechanism gate it: `bare_oxide` and `PVDF`.
  - For each of the two, the screen is rerun with the control in place of the template, at the
    same states and with the same rules.
  - The test holds if, for each control, at least one of C2, C3 or C4 degrades. A link degrades
    when its verdict is strictly worse (feasible < inconclusive < falsified), or when its
    falsified-side mass rises by at least p_deg (`thresholds.decision.degrade_mass_min`).
  - A degradation of C1 alone does not count.
  - If the test fails for either control, the study is reported as a generic adhesion study, and
    the framing changes whatever the feasibility verdict. A feasible verdict also requires the
    test to hold.
  - `catechol_only` and `chitosan_only` are computed and reported but do not gate.
    `carboxylate_substituted` is a competing-chemistry comparator, reported either way.
- **Reading under contract v2.** Because Ca2+ binding at fixed gamma_sn raises the C3 barrier, a
  template can pass C2 and fail C3 on the same binding. That outcome is a finding about the
  mechanism, not a defect of the rules.

## 4. Params keys

Every number above comes from these keys. Registration conventions are set at cp2 and recorded in
`lit/params.yaml` with the cp2 ruling as source. All other keys are fetched by W1.

| Key | Symbol | Kind | Used by |
|---|---|---|---|
| `thresholds.decision.credible_level` | p_cred | registration (cp2) | all links |
| `thresholds.decision.degrade_mass_min` | p_deg | registration (cp2) | deletion test |
| `thresholds.C1.margin_W_adh_wet` | m_W | literature (method error) | C1 |
| `thresholds.C1.contact_area_definition` | A_c rule | registration (cp2) | C1 |
| `regimes.R-slurry.parameters.termination_weights` | weights | literature | C1 |
| `thresholds.C2.margin_DG_seq` | m_seq | literature (method error) | C2 |
| `thresholds.C3.margin_cos_theta` | m_cos | registration (cp2; proposed zero) | C3 (a) |
| `regimes.R-slurry.parameters.framing` | framing | registration (cp3, N5) | C3, C5 |
| `regimes.R-slurry.parameters.J0_het` | J0_het | literature | C3 (b), C4 |
| `regimes.R-slurry.parameters.t_proc` | t_proc | literature or process input | C3 (b), C4 |
| `thresholds.C3.N_req` | N_req | registration (cp2, decision 4) | C3 (b) |
| `thresholds.C4.margin_S_spread` | m_S | literature (method error) | C4 |
| `regimes.R-cell.parameters.R_A_max` | R_A_max | registration input | C4 (d_max) |
| `regimes.R-cell.parameters.j_req` | j_req | registration input | C4 (d_max) |
| `regimes.R-cell.parameters.rho_e` | rho_e | literature | C4 (d_max) |
| `regimes.R-cell.parameters.phi_B` | phi_B | literature | C4 (d_max) |
| `regimes.R-cell.parameters.m_eff` | m_e (effective) | literature | C4 (d_max) |
| `regimes.R-cell.parameters.j_0` | j_0 | literature | C4 (d_max) |
| `thresholds.C5.formation_energy_error` | e_form | literature (database benchmark) | C5 |
| `regimes.R-slurry.parameters.ACC_offset` | Delta_ACC | literature | C5 (ACC framing) |
| `regimes.R-slurry.parameters.pH_range` | pH | literature | C5, all R-slurry states |
| `regimes.R-slurry.parameters.E_SHE_range` | E_SHE | literature | C5 |
| `thresholds.C5.window_margin` | m_E | literature (derived from e_form) | C5 R-cell |
| `regimes.R-cell.parameters.E_min` | E_cell_min | literature | C5 R-cell |
| `regimes.R-cell.parameters.E_max` | E_cell_max | literature | C5 R-cell |
| `regimes.R-cell.parameters.electrolyte_salts` | salts | literature (fluorine-free) | C5 R-cell sink |
| `regimes.R-cell.parameters.gas_reference_schemes` | schemes | registration (cp2) | C5 R-cell |
| `regimes.R-cell.parameters.al_phases` | phases | registration (cp2) | C5 R-cell |

The C2-to-C3 inputs that the thresholds consume through Delta_gamma_ads are the existing priors
`Gamma_s`, `delta_s`, `c_bulk` and `gamma_sl0`. `gamma_sl0` is new in contract v2 and replaces a
Ca-free reading of `gamma_sl`.

## 5. Machine-readable form

W4 copies this block into `configs/preprint/thresholds.yaml`. Expressions use the ids of
`theory/symbols.yaml` and the functions of `theory/contract.yaml`. `theory/tools/check_contract.py`
checks that every expression parses, that only registered ids appear, and that each edge has the
unit of its quantity.

```thresholds
version: 1
authority: theory/thresholds.md
written_before_screen_output: true
base_commit: 49100a9d92b5dc48f1db1d15529967dfeeece12d
contract_version: 2
decision:
  statistic: band_mass
  credible_level: {symbol: p_cred, params: thresholds.decision.credible_level}
  verdicts:
    feasible: 'P_good >= p_cred'
    falsified: 'P_bad >= p_cred'
    inconclusive: otherwise
  order: [feasible, inconclusive, falsified]
  clipping: {cos_ge_1: {theta: '0', f_theta: '0'}, cos_le_minus_1: {theta: pi, f_theta: '1'}, report: boundary_mass}
  omega: Omega_bulk
  forbidden_in_verdicts: [Omega_local_ideal, Delta_mu_local_ideal, DG_het_local_ideal, DG_het_double, E_enr, c_local]
links:
  C1:
    regimes: [R-slurry]
    aggregation: worst_state
    tests:
      - id: C1
        quantity: W_adh_wet
        comparator: '>'
        edge: m_W
        params: {m_W: thresholds.C1.margin_W_adh_wet}
        mixture: {over: termination, weights: regimes.R-slurry.parameters.termination_weights}
    combine: C1
  C2:
    regimes: [R-slurry]
    aggregation: worst_state
    tests:
      - id: C2
        quantity: Delta_G_seq
        comparator: '<'
        edge: -m_seq
        params: {m_seq: thresholds.C2.margin_DG_seq}
    report: [Theta_occ, Gamma_Ca, Delta_gamma_ads]
    combine: C2
  C3:
    regimes: [R-slurry]
    tests:
      - id: C3a
        aggregation: worst_state
        quantity: f_theta
        cos_function: cos_theta_template
        comparator: '<='
        edge: (2 + m_cos)*(1 - m_cos)**2/4
        params: {m_cos: thresholds.C3.margin_cos_theta}
        deck_bands: replaced by the single edge at f = 1/2 (cos theta = m_cos); the deck upper edge is dropped
      - id: C3b
        aggregation: path_sum
        quantity: N_nuc
        comparator: '>='
        edge: N_req
        equivalent_single_state: {quantity: DG_het, comparator: '<=', edge: k_B*T*log(J0_het*t_proc/N_req)}
        params: {J0_het: regimes.R-slurry.parameters.J0_het, t_proc: regimes.R-slurry.parameters.t_proc,
                 N_req: thresholds.C3.N_req}
        report: [DG_het/(k_B*T), DG_hom/(k_B*T)]
    combine: 'C3a and C3b'
  C4:
    regimes: [R-slurry, R-cell]
    aggregation: worst_state
    tests:
      - id: C4
        quantity: S_spread
        comparator: '>='
        edge: m_S
        params: {m_S: thresholds.C4.margin_S_spread}
      - id: C4s
        role: supporting
        quantity: N_nuc
        comparator: '>='
        edge: tan(theta/2)**2/(2*d_max**2)
        d_max: {max_of: [d_max_ohm, d_max_tun]}
        params: {R_A_max: regimes.R-cell.parameters.R_A_max, j_req: regimes.R-cell.parameters.j_req,
                 rho_e: regimes.R-cell.parameters.rho_e, phi_B: regimes.R-cell.parameters.phi_B,
                 m_e: regimes.R-cell.parameters.m_eff, j_0: regimes.R-cell.parameters.j_0}
    combine:
      feasible: 'C4 feasible'
      falsified: 'C4 falsified and C4s falsified'
      inconclusive: otherwise
  C5:
    regimes: [R-slurry, R-cell]
    tests:
      - id: C5s
        regime: R-slurry
        aggregation: worst_point
        quantity: Delta_G_pbx
        comparator: '<='
        edge_by_framing:
          calcite: N_atoms*e_form/N_M
          ACC: (N_atoms*e_form + Delta_ACC)/N_M
        params: {e_form: thresholds.C5.formation_energy_error, Delta_ACC: regimes.R-slurry.parameters.ACC_offset,
                 pH: regimes.R-slurry.parameters.pH_range, E_SHE: regimes.R-slurry.parameters.E_SHE_range}
        state: bulk
        requires: falsifiability_control_fails_where_it_must
      - id: C5c_ox
        regime: R-cell
        quantity: E_ox
        comparator: '>='
        edge: E_cell_max + m_E
        reduce: min_over_reference_schemes
        params: {E_cell_max: regimes.R-cell.parameters.E_max, m_E: thresholds.C5.window_margin,
                 schemes: regimes.R-cell.parameters.gas_reference_schemes,
                 salts: regimes.R-cell.parameters.electrolyte_salts}
        undetermined: never_passes
        solid_salt_sink: {falsification: stands, pass: conditional_on_cp2_decision_5}
      - id: C5c_red
        regime: R-cell
        quantity: E_red
        comparator: '<='
        edge: E_cell_min - m_E
        reduce: max_over_reference_schemes
        params: {E_cell_min: regimes.R-cell.parameters.E_min, m_E: thresholds.C5.window_margin}
        undetermined: never_passes
    gated_phases: {R-slurry: [CaCO3 framing phase], R-cell: [CaCO3, regimes.R-cell.parameters.al_phases]}
    combine: 'C5s and C5c_ox and C5c_red'
study:
  falsified: 'any of C1, C2, C3, C4, C5 falsified'
  feasible: 'all of C1, C2, C3, C4, C5 feasible and deletion_test holds'
  inconclusive: otherwise
  deletion_test:
    gating_controls: [bare_oxide, PVDF]
    links: [C2, C3, C4]
    degrade: 'verdict strictly worse, or falsified-side mass up by at least p_deg'
    params: {p_deg: thresholds.decision.degrade_mass_min}
    c1_alone_counts: false
    on_failure: framing_generic_adhesion
    reported_not_gating: [catechol_only, chitosan_only, carboxylate_substituted]
```
