# Thresholds and decision rules of the P0 screen (G0 fix F9; checkpoint cp2)

**Written before any screen output existed.** This file was written in session P0-W3.2 on top
of commit `49100a9d92b5dc48f1db1d15529967dfeeece12d` (lane p0-w3, contract v2 at
`5811a6b2b82565a2d7e991987eee6ab4f167959e`). No screen output was run or read in that session
(rule R7). The commit that adds this file is recorded in `ops/state/p0-w3.json` under
`thresholds.sha`. The cp2 fix-up (P0-W3.2, 2026-10-17) applied the audit fixes F3 to F9 and set
the conventions below, again before any screen output existed; `theory/cp2_fixes.md` lists each
change with its commit.

This file is the threshold authority of track p0 (rule R-thr). `configs/preprint/thresholds.yaml`
(W4) is a copy of the fenced `thresholds` block at the end, and W4 checks the two equal. After tag
`p0-cp3` this file changes only through a dated entry in `ops/tracks/p0_deviations.md`.

No literature number is typed here (rule R2). Every physical quantity a threshold needs is named
by the `lit/params.yaml` key that will supply it, and "Params keys" at the end lists them.
Rationals such as 1/2 are exact values of the theory, not literature values. The only typed
numbers are the method conventions set by the cp2 audit (Section 1, "Registered conventions"). Equation numbers refer to the
P0-W3.2 cp2 fix-up build of `theory/build/derivation.pdf`, with the stable label in brackets.

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

**States.** C1, the C3 wetting part, C4 and C5 are necessary at every registered state at
which they apply. A link's verdict is therefore the worst over those states, ordered feasible <
inconclusive < falsified. The C3 accessibility part is cumulative: nuclei may form at any state
along the registered R-slurry path, so it uses the path sum of Eq. (26) [th:eq:access].

**Water activity at drying states (cp2 fix F7, Q13).** The ion activity product stays
IAP = a_Ca a_CO3. For a hydrated ACC framing CaCO3.nH2O the full product carries a_w^n, and
omitting it overstates Omega by the factor a_w^(-n) whenever a_w < 1. The drying states are
therefore optimistic in the screen: their Omega, and with it the C3 driving force, is biased
toward feasibility. Two requirements follow:
- a_w (`params.a_w_slurry`, per registered drying state) is reported at each drying state;
- where W1 supplies n (`params.acc_hydration_n`), the labelled sensitivity `Omega_bulk_hydrated`
  (contract) is reported beside every drying-state verdict. It never decides a verdict.

**Bookkeeping (contract v2, unchanged in v3).** Every barrier is evaluated with Omega = Omega_bulk at the regime
activities. The C2 binding enters only through Delta_gamma_ads in gamma_sl, and C2 itself is a
reported descriptor, not a gate (Section 2) (derivation, Section 7
(rule), Eqs. (32) to (35) [th:eq:gibbs to th:eq:composite]). `Omega_local_ideal` and the demonstration composites never enter a
verdict.

### Registered conventions (cp2 ruling, 2026-10-17)

These are method conventions, not literature values. They are set here before any screen output
exists, and W1 records each under its key with the cp2 ruling as the source.

| Convention | Value | Key |
|---|---|---|
| credible level p_cred | 0.9 primary; published sweep 0.6, 0.9, 0.99 | `thresholds.decision.credible_level` |
| degradation mass p_deg | p_deg = 1 - p_cred, so 0.1 at the primary level | `thresholds.decision.degrade_mass_min` |
| C3 margin m_cos | 0 primary (the priors carry the method error); published sweeps 0.1 and 0.2 | `thresholds.C3.margin_cos_theta` |
| C1 margin m_W | set by W1 from fetched method-error evidence, or zero where the prior carries it | `thresholds.C1.margin_W_adh_wet` |
| C4 margin m_S | set by W1 as for m_W | `thresholds.C4.margin_S_spread` |
| C5 window margin m_E | set by W1 as for m_W | `thresholds.C5.window_margin` |

- **p_deg in the sweep.** p_deg is registered as the rule 1 - p_cred, so it moves with the
  credible level in the p_cred sweep (0.4, 0.1, 0.01). A rise of the falsified-side mass by
  1 - p_cred is the smallest shift that can carry a link across one band of the decision rule.
- **The W1 margins.** For each of m_W, m_S and m_E, W1 states in the key's `notes` which case
  applies: a value from fetched method-error evidence (with its sources), or zero because the
  prior already carries the method error (with the reason).
- **Sweeps.** A sweep is reported beside the primary result and never replaces it. A verdict that
  changes within a registered sweep is reported as sensitive to that convention.

**Approved as proposed at cp2.**
- C3: the single edge f = 1/2 (cos(theta) = m_cos) replaces the deck bands, and the absolute
  criterion DG_het <= B_acc is part (b) (Section 2, C3).
- State aggregation: the worst state per link, and a path sum for C3 (b).
- C4: the square-lattice closure is the optimistic supporting condition (Q14). C4 is
  S_spread >= m_S, and a falsified verdict needs the coalescence condition to fail as well.
- The enrichment factor E_enr is reported only as a labelled, non-gating sensitivity. It never
  enters a verdict.

**Sizing rule for the Monte Carlo (W4.3).** The draws are raised until both of these hold:
- the half-width of every verdict-band mass is at most 0.01;
- the half-widths of the top Sobol total-order indices are at most 0.02.

A half-width is twice the Monte Carlo standard error: binomial for a band mass, bootstrap for a
Sobol index. Two caps stop the run first if they are reached:
- **draw cap:** 2^20 base draws per regime state;
- **wall-clock cap:** 6 hours per W4.3 run.

A run stopped by a cap is reported as capped, with the half-widths it reached. Draws stream in
chunks of 2^14, so memory does not grow with the draw count. Every chunk updates the band masses
and the running half-widths, and no full draw table is held in memory.

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

### C2, sequestration (R-slurry): a binding descriptor, not a gate

C2 is a binding descriptor. It enters C3 only through Delta_gamma_ads and is not an independent
kill criterion (cp2 ruling, fix F3).

- **Why it does not gate.** At equilibrium the Ca2+ chemical potential is uniform, so binding does
  not raise the driving force (derivation, Section 4). Its only route to nucleation is the
  template-liquid energy, through Delta_gamma_ads, Eq. (32) [th:eq:gibbs], and that route is
  already judged inside C3. A separate C2 verdict would judge the same binding a second time, as a
  pass or kill of its own, which is the double count the bookkeeping removes. At fixed gamma_sl0
  and gamma_sn, the C2 term raises the C3 barrier: SF2, Eq. (34) [th:eq:young-ads].
- **Reported (every registered R-slurry state).** The distributions of `Delta_G_seq` (J mol^-1,
  the transfer free energy of Ca2+ from hydrated bulk to the site, Eq. (4) [th:eq:cycle]),
  `Theta_occ`, `Gamma_Ca` and `Delta_gamma_ads` at the regime activity. P0 uses one effective
  site type per template (Gamma_s, Delta_G_seq); multi-site populations are deferred (Q4).
- **Finding on the premise.** The mechanism's premise is that the template holds Ca2+ more
  strongly than water does, Delta_G_seq < 0. With the shared band-mass rule at level p:
  - if `P(Delta_G_seq >= 0) >= p`, the report states the finding **"the sequestration premise
    fails"**;
  - if `P(Delta_G_seq < 0) >= p`, it states "the sequestration premise holds";
  - otherwise it states "the sequestration premise is undecided".

  The finding is a statement about the mechanism. It does not enter the study verdict, which is
  carried by C3 through Delta_gamma_ads.
- **Labelled sensitivity.** `P(Delta_G_seq < -m_seq)`, with m_seq =
  `thresholds.C2.margin_DG_seq` the method error of a Ca2+ transfer free energy that the prior
  does not carry, is reported beside the finding.
- **Regime.** R-slurry, at the regime pH and ionic strength.

### C3, nucleation (R-slurry)

C3 has two parts. Both must pass, as the charter's verdict bands require.

**(a) Wetting part: bands for f(theta).**

- **Threshold and physics.** X = f(theta), with cos(theta) from `cos_theta_template` (or from
  `cos_theta_young` with an in-situ gamma_sl), Eq. (34) [th:eq:young-ads]. The deck's starting
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
  m_cos = `thresholds.C3.margin_cos_theta` in [0, 1). Registered at cp2: m_cos = 0 primary (the
  method error of each interfacial energy is carried in its prior), with published sweeps at
  0.1 and 0.2 (Section 1, "Registered conventions").
- **Decision.** feasible if `P(f <= f_e) >= p`; falsified if `P(f > f_e) >= p`; inconclusive
  otherwise. The mass at the clipped boundaries (N2) is reported.
- **Framing consistency (Q12).** K_sp, V_m and gamma_nl come from one framing (ACC or calcite),
  keyed by `regimes.R-slurry.parameters.framing`. A draw that mixes framings is refused.

**(b) Accessibility part: absolute barrier in k_B T.**

- **Threshold and physics.** Eqs. (25) and (26) [th:eq:rate, th:eq:access]. Nuclei form on the
  template at J = J_0 exp(-DG_het / k_B T) per area and time. At least the areal density N_req
  must form within the time t_p that the template spends at the registered R-slurry states:
  N_nuc = sum over states k of J_0 Delta t_k exp(-DG_het,k / k_B T) >= N_req. At a single state
  this is

  DG_het <= B_acc = k_B T ln(J_0 t_p / N_req),

  with DG_het at Omega_bulk. A count N on a collector area A enters as N_req = N / A.
- **N_req (cp2 fix F4).** N_req is a separately fixed areal density, not the C4 closure density:

  N_req = 1 / A_patch,

  with A_patch the particle-collector contact patch, a literature process input. The criterion
  asks for at least one nucleus, in expectation, under every contact patch through which the
  cathode particles touch the collector. The closure density N_s_closure stays in C4 only.
- **Keys.**
  - J_0 = `regimes.R-slurry.parameters.J0_het`: a loguniform prior over its fetched range, because
    only ln J_0 enters.
  - t_p = `regimes.R-slurry.parameters.t_proc`: per registered state, slurry contact and drying.
  - A_patch = `regimes.R-slurry.parameters.patch_area`: the particle-collector contact patch
    (literature process input), with N_req = 1/A_patch. The former key `thresholds.C3.N_req` is
    no longer an independent input: W1 records it as derived from `patch_area`.
  - A proposal for cp3 (a Poisson-occupancy refinement of 1/A_patch) is in
    `theory/cp2_brief.md`, section D. It is not applied.
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

- **Chosen criterion (lane note N1).** X = `S_spread` (J m^-2), Eq. (36) [th:eq:spread].
  - Derivation Eq. (38) [th:eq:n1] shows that a small-angle bound theta <= theta_max and
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
  - The condition is N_s >= N_s_closure = tan^2(theta/2) / (2 d_max^2), Eq. (39)
    [th:eq:nclosure], with d_max = max(d_max_ohm, d_max_tun), Eqs. (41) to (43).
  - The island density is N_s = N_nuc from C3(b), an upper estimate. A failure of closure with
    N_nuc is therefore conservative, and a success is only optimistic.
  - The condition is geometric: it uses the geometric thicknesses h_c and h_cl. The charter's
    kinetic critical coalescence thickness (C4 candidate (c)) is named h_coal (cp2 fix F9). It
    needs a nucleation-and-growth model and is not computed in P0.
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

- **Threshold and physics.** X = `Delta_G_pbx` (J mol^-1 per non-O, non-H atom), Eq. (40)
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
- **What the ACC edge tests (cp2 fix F6).** Adding Delta_ACC to the edge makes the ACC test
  equal to the calcite-level test. ACC lies above calcite by Delta_ACC per formula unit, so
  Psi_ACC = Psi_calcite + Delta_ACC / n_M. It is never on the hull, so the hull is the same with or
  without it. The ACC test, Delta_G_pbx(ACC) <= (n_at e_f + Delta_ACC) / n_M, is therefore
  identical to Psi_calcite - Psi_hull <= n_at e_f / n_M. In words, C5 R-slurry decides whether
  CaCO3 is stable as a phase at the regime activities, up to the metastability that defines the
  framing. It does not decide whether ACC itself survives.
- **ACC-specific dissolution margin (labelled sensitivity, not gating).** Whether the regime
  solution is supersaturated with respect to ACC is Omega_bulk evaluated with the ACC solubility
  product, the quantity that already enters C3 through K_sp under the ACC framing. C5 reports
  `P(Omega_bulk >= 1)` for the ACC framing at each registered state, labelled as the ACC
  dissolution sensitivity. A value of Omega_bulk below 1 there means ACC dissolves at that state
  even where CaCO3 passes C5.
- **Decision.**
  - feasible if `P(Delta_G_pbx <= edge) >= p` at every point, **and** the falsifiability control
    (item 21, W5) fails where it must;
  - falsified if `P(Delta_G_pbx > edge) >= p` at some point;
  - inconclusive otherwise, or if the control passes where it must fail.
- **Al phases.** The native oxide's Pourbaix state is reported as the bare-oxide baseline. It does
  not gate C5, because alkaline attack on the native oxide is the corrosion mode the slurry
  regime describes.

**R-cell, Li-referenced window.**

- **Threshold and physics.** Eq. (42) [th:eq:window] with the electrolyte-fixed sink of Eq. (43)
  [th:eq:sink] for CaCO3 and the protecting Al phases (`regimes.R-cell.parameters.al_phases`).
  The registered regime potential range [E_cell_min, E_cell_max] (V vs Li+/Li,
  `regimes.R-cell.parameters.E_min` and `regimes.R-cell.parameters.E_max`) must lie inside every
  window:

  E_red + m_E <= E_cell_min and E_cell_max + m_E <= E_ox.

- **Margin.** m_E = `thresholds.C5.window_margin`, the expected error of a computed reaction energy
  per transferred electron, derived by W1 from `thresholds.C5.formation_energy_error`.
- **Reference schemes (cp2 fix F5 (a)).** Each limit is computed under every registered CO2 and
  O2 reference scheme (`regimes.R-cell.parameters.gas_reference_schemes`).
  - A **pass** must hold under the scheme with the lowest onset: the lowest E_ox and the highest
    E_red over the schemes.
  - A **falsification** must hold under every registered scheme.
  - Otherwise the limit is inconclusive. A verdict that changes with the reference scheme is
    decided by none of them.
- **Sink (cp2 fix F5 (b)).** A pass counts only with a solvated sink: Ca2+ or Al3+ leaving as
  solvated ions paired with the salt anion, with the solvation free energies relative to Li+.
  - The true product is the lower in free energy of the solid salt and the solvated ions. A limit
    computed with the solid-salt sink alone (CaA2 or AlA3 as a solid) is therefore an upper bound
    on the oxidation onset.
  - A falsification computed with the solid-salt sink stands, because the true onset is at or
    below it.
  - A pass computed with the solid-salt sink is inconclusive, because the solvated sink can only
    lower the onset.
- **Undetermined never passes.** A limit with status `undetermined` (a missing sink phase, a
  missing solvation free energy for the solvated sink, an unregistered salt, or an unbounded
  Li-open limit) gives at best inconclusive. The same holds if E_cell_max is not registered.
- **Decision.**
  - feasible if both inequalities hold for every gated phase, under the lowest-onset scheme and
    with a solvated sink;
  - falsified if, for any gated phase, a limit fails beyond its margin (E_ox < E_cell_max - m_E,
    or E_red > E_cell_min + m_E) under every registered scheme, with either sink;
  - inconclusive otherwise.

  The limits are deterministic, so the band mass is 0 or 1 for each scheme and sink.
- **Limitation: the electrolyte's own anodic limit (cp2 fix F5 (c)).** Above the electrolyte's
  anodic limit the solvent and salt oxidise first. C5 does not assess that limit. A pass of the
  E_ox test says only that the gated phases are stable up to E_cell_max against the registered
  sinks, not that the electrolyte is.
- **W5's reported limits (inputs to the decision, not adjudicated here).** `ops/reports/P0-W5.1.md`
  (R-cell section) reports:
  - a CaCO3 oxidation onset under the nitrate sink that differs by the CO2 reference (JANAF
    against the Materials Project CO2 energy), with the spread stated there;
  - an Al2O3 limit that is undetermined under nitrate (sink phase missing) and finite under
    sulfate or chloride.

  Both are solid-salt limits. Under this file, a CaCO3 falsification must hold under both CO2
  schemes, and a CaCO3 pass needs the solvated sink and the lower of the two schemes. Al2O3 under
  a nitrate electrolyte stays undetermined (never a pass) until the sink thermochemistry is
  fetched.

**C5 verdict.** feasible if both regimes are feasible; falsified if either is falsified;
inconclusive otherwise.

## 3. Study-level verdict

- **Combination.** The gating links are C1, C3, C4 and C5. C2 is a reported descriptor (Section
  2). The study is
  - falsified if any of C1, C3, C4 or C5 is falsified. C1, C3 and C4 are sequential links, any
    one of which can end the mechanism; C5 is a necessary screen;
  - feasible only if all four are feasible and the deletion test below holds;
  - inconclusive otherwise.
- **Sequestration premise.** The C2 finding of Section 2 is reported with the study verdict. If
  the premise fails, the report says so as a finding, whatever the verdict.
- **Deletion test (`charter/deletion_register.yaml`, F1).** Only the controls that remove the
  mechanism gate it: `bare_oxide` and `PVDF`.
  - For each of the two, the screen is rerun with the control in place of the template, at the
    same states and with the same rules.
  - The test holds if, for each control, at least one of C3 or C4 degrades. A link degrades
    when its verdict is strictly worse (feasible < inconclusive < falsified), or when its
    falsified-side mass rises by at least p_deg (`thresholds.decision.degrade_mass_min`).
  - A degradation of C1 alone does not count. C2 is not a deletion link: the control's binding
    descriptors are reported beside the template's, and the binding reaches the test through C3.
  - If the test fails for either control, the study is reported as a generic adhesion study, and
    the framing changes whatever the feasibility verdict. A feasible verdict also requires the
    test to hold.
  - `catechol_only` and `chitosan_only` are computed and reported but do not gate.
    `carboxylate_substituted` is a competing-chemistry comparator, reported either way.
- **Reading under contract v2.** Because Ca2+ binding at fixed gamma_sn raises the C3 barrier, a
  template can satisfy the sequestration premise and fail C3 on the same binding. That outcome is
  a finding about the mechanism, not a defect of the rules.

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
| `thresholds.C2.margin_DG_seq` | m_seq | literature (method error) | C2 labelled sensitivity (not gating) |
| `thresholds.C3.margin_cos_theta` | m_cos | registration (cp2; proposed zero) | C3 (a) |
| `regimes.R-slurry.parameters.framing` | framing | registration (cp3, N5) | C3, C5 |
| `regimes.R-slurry.parameters.J0_het` | J0_het | literature | C3 (b), C4 |
| `regimes.R-slurry.parameters.t_proc` | t_proc | literature or process input | C3 (b), C4 |
| `regimes.R-slurry.parameters.patch_area` | A_patch | literature (process input; N_req = 1/A_patch, cp2 fix F4) | C3 (b) |
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
| `params.a_w_slurry` | a_w | literature (per drying state) | reported at every drying state (F7) |
| `params.acc_hydration_n` | n_hyd | literature (ACC framing) | hydrated-IAP sensitivity (F7) |
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
revised: {session: P0-W3.2 cp2 fix-up, base_commit: 800d5ea3de41a0fb16084519d5c2680eeb14952d, fixes: theory/cp2_fixes.md}
contract_version: 3
decision:
  statistic: band_mass
  credible_level: {symbol: p_cred, params: thresholds.decision.credible_level}
  verdicts:
    feasible: 'P_good >= p_cred'
    falsified: 'P_bad >= p_cred'
    inconclusive: otherwise
  order: [feasible, inconclusive, falsified]
  clipping: {cos_ge_1: {theta: '0', f_theta: '0'}, cos_le_minus_1: {theta: pi, f_theta: '1'}, report: boundary_mass}
  conventions:
    set_at: cp2 ruling 2026-10-17
    p_cred: {primary: 0.9, sweep: [0.6, 0.9, 0.99], params: thresholds.decision.credible_level}
    p_deg: {rule: 1 - p_cred, primary: 0.1, params: thresholds.decision.degrade_mass_min}
    m_cos: {primary: 0, sweep: [0.1, 0.2], params: thresholds.C3.margin_cos_theta}
    m_W: {set_by: W1, from: fetched method-error evidence, or zero where the prior carries it, params: thresholds.C1.margin_W_adh_wet}
    m_S: {set_by: W1, from: fetched method-error evidence, or zero where the prior carries it, params: thresholds.C4.margin_S_spread}
    m_E: {set_by: W1, from: fetched method-error evidence, or zero where the prior carries it, params: thresholds.C5.window_margin}
    approved: [single_edge_f_half_plus_absolute_criterion, worst_state_per_link, path_sum_C3b,
               square_lattice_closure_optimistic_supporting, C4_S_spread_falsified_only_if_coalescence_fails]
    E_enr: labelled non-gating sensitivity
  sizing:
    applies_to: W4.3
    band_mass_half_width_max: 0.01
    sobol_total_order_half_width_max: 0.02
    half_width: 2 x Monte Carlo standard error (binomial for band masses, bootstrap for Sobol indices)
    draw_cap: 2**20 base draws per regime state
    wall_clock_cap: 6 h per run
    chunk: 2**14 draws, streamed
    on_cap: report as capped with the half-widths reached
  omega: Omega_bulk
  forbidden_in_verdicts: [Omega_local_ideal, Delta_mu_local_ideal, DG_het_local_ideal, DG_het_double, E_enr, c_local,
                          Omega_bulk_hydrated]
  drying_states:
    iap: a_Ca*a_CO3
    bias: the anhydrous IAP overstates Omega by a_w**(-n_hyd) when a_w < 1; drying states are optimistic
    report: [a_w]
    sensitivity: Omega_bulk_hydrated
    params: {a_w: params.a_w_slurry, n_hyd: params.acc_hydration_n}
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
    role: descriptor
    gating: false
    regimes: [R-slurry]
    statement: C2 is a binding descriptor. It enters C3 only through Delta_gamma_ads and is not an independent kill criterion.
    enters: {link: C3, via: Delta_gamma_ads}
    report: [Delta_G_seq, Theta_occ, Gamma_Ca, Delta_gamma_ads]
    finding:
      quantity: Delta_G_seq
      premise_fails: 'P(Delta_G_seq >= 0) >= p_cred'
      premise_holds: 'P(Delta_G_seq < 0) >= p_cred'
      otherwise: premise_undecided
      text_on_fail: the sequestration premise fails
    sensitivities:
      - id: C2m
        label: mass beyond the method-error margin (reported, not gating)
        quantity: Delta_G_seq
        comparator: '<'
        edge: -m_seq
        params: {m_seq: thresholds.C2.margin_DG_seq}
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
        edge: 1/A_patch
        N_req: {equals: 1/A_patch, rule: cp2 fix F4, not the C4 closure density}
        equivalent_single_state: {quantity: DG_het, comparator: '<=', edge: k_B*T*log(J0_het*t_proc*A_patch)}
        params: {J0_het: regimes.R-slurry.parameters.J0_het, t_proc: regimes.R-slurry.parameters.t_proc,
                 A_patch: regimes.R-slurry.parameters.patch_area}
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
        acc_edge_equivalence: the ACC edge makes the test equal to the calcite-level test (cp2 fix F6)
    sensitivities:
      - id: C5s_ACC
        label: ACC dissolution margin under the ACC framing (reported, not gating)
        framing: ACC
        quantity: Omega_bulk
        comparator: '>='
        edge: '1'
        uses: K_sp of the ACC framing (the prior already used by C3)
      - id: C5c_ox
        regime: R-cell
        quantity: E_ox
        comparator: '>='
        edge: E_cell_max + m_E
        pass: {reduce: min_over_reference_schemes, sink: solvated}
        falsify: {quantity: E_ox, comparator: '<', edge: E_cell_max - m_E, reduce: every_reference_scheme, sink: [solvated, solid_salt]}
        otherwise: inconclusive
        params: {E_cell_max: regimes.R-cell.parameters.E_max, m_E: thresholds.C5.window_margin,
                 schemes: regimes.R-cell.parameters.gas_reference_schemes,
                 salts: regimes.R-cell.parameters.electrolyte_salts}
        undetermined: never_passes
        solid_salt_sink: {falsification: stands, pass: inconclusive, reason: upper bound on the onset}
        limitation: electrolyte anodic limit not assessed
      - id: C5c_red
        regime: R-cell
        quantity: E_red
        comparator: '<='
        edge: E_cell_min - m_E
        pass: {reduce: max_over_reference_schemes}
        falsify: {quantity: E_red, comparator: '>', edge: E_cell_min + m_E, reduce: every_reference_scheme}
        otherwise: inconclusive
        params: {E_cell_min: regimes.R-cell.parameters.E_min, m_E: thresholds.C5.window_margin,
                 schemes: regimes.R-cell.parameters.gas_reference_schemes}
        undetermined: never_passes
    gated_phases: {R-slurry: [CaCO3 framing phase], R-cell: [CaCO3, regimes.R-cell.parameters.al_phases]}
    combine: 'C5s and C5c_ox and C5c_red'
study:
  gating_links: [C1, C3, C4, C5]
  descriptor_links: [C2]
  falsified: 'any of C1, C3, C4, C5 falsified'
  feasible: 'all of C1, C3, C4, C5 feasible and deletion_test holds'
  inconclusive: otherwise
  report_with_verdict: [C2.finding]
  deletion_test:
    gating_controls: [bare_oxide, PVDF]
    links: [C3, C4]
    degrade: 'verdict strictly worse, or falsified-side mass up by at least p_deg'
    params: {p_deg: thresholds.decision.degrade_mass_min}
    c1_alone_counts: false
    on_failure: framing_generic_adhesion
    reported_not_gating: [catechol_only, chitosan_only, carboxylate_substituted]
```
