# Thresholds and decision rules of the P0 screen (G0 fix F9; checkpoints cp2 and cp3)

**Written before any screen output existed.** This file was written in session P0-W3.2 on top
of commit `49100a9d92b5dc48f1db1d15529967dfeeece12d` (lane p0-w3, contract v2 at
`5811a6b2b82565a2d7e991987eee6ab4f167959e`). No screen output was run or read in that session
(rule R7). The commit that adds this file is recorded in `ops/state/p0-w3.json` under
`thresholds.sha`. The cp2 fix-up (P0-W3.2, 2026-10-17) applied the audit fixes F3 to F9 and set
the conventions below, again before any screen output existed; `theory/cp2_fixes.md` lists each
change with its commit. The cp3 amendments (P0-W3.3, planning ruling of 2026-10-17, items R1 to R8,
one commit each) were applied before any screen output existed as well; they are logged with their
commits in the cp3 section of `theory/cp2_fixes.md`. R1 and R2 were set after W5's C5 results
were seen, and R6 after an early calcite estimate; each carries its disclosure. The cp3b
registrations for production (P0-W3.4, items A1 to A4 of lane note N22, one commit each) were
written without consulting any screen output: no file under `results/preprint/screen/` was read.
They are logged in the cp3 section of `theory/cp2_fixes.md`.

This file is the threshold authority of track p0 (rule R-thr). `configs/preprint/thresholds.yaml`
(W4) is a copy of the fenced `thresholds` block at the end, and W4 checks the two equal. After tag
`p0-cp3` this file changes only through a dated entry in `ops/tracks/p0_deviations.md`.

No literature number is typed here (rule R2). Every physical quantity a threshold needs is named
by the `lit/params.yaml` key that will supply it, and "Params keys" at the end lists them.
Rationals such as 1/2 are exact values of the theory, not literature values. The only typed
numbers are the method conventions set by the cp2 audit (Section 1, "Registered conventions"). Equation numbers refer to the
P0-W3.3 cp3 build of `theory/build/derivation.pdf`, with the stable label in brackets.

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

**Link masses are joint, draw by draw (cp3 R7 (1)).** A link with several tests has one good
indicator per Monte Carlo draw, and its band masses are the masses of that indicator, computed on
the same draws:
- an "A and B" link (C3: (a) and (b); C5: its tests) is good on a draw only if every test is good,
  so its falsified-side mass is P(A bad **or** B bad);
- C4 is good on a draw if either route is good, so its falsified-side mass is
  P(S_spread route bad **and** closure route bad) (Section 2, C4).

The verdict applies the shared rule to these joint masses (P_good = 1 - P_bad of the link), and
the deletion test compares the same joint falsified-side masses. The single-test masses are
reported beside them. This replaces the per-test maximum or minimum (W4's interpretation (i)).

**States (cp3 R7 (4)).** Every registered state of a regime is propagated (for R-slurry: slurry
contact and every drying state); no link is run at one representative state.
- C1, the C3 wetting part, C4's spreading route and C5 are necessary at every registered state at
  which they apply. A link's verdict is therefore the worst over those states, ordered feasible <
  inconclusive < falsified, with the joint link mass formed within each state.
- The C3 accessibility part is cumulative: nuclei may form at any state along the registered
  R-slurry path, so it uses the path sum of Eq. (26) [th:eq:access]. The path sum only grows as
  states are added.
- **A missing state.** If a registered state cannot be evaluated (for example a drying state whose
  water activity is a gap), the verdicts are bounded by what was evaluated:
  - C3 (b) (and C4's closure route, which uses the same N_nuc) cannot be falsified unless every
    registered state, drying included, has been evaluated. With a state missing, a shortfall is
    inconclusive and a pass stands, because the missing terms can only add nuclei;
  - for a worst-state link the mirror holds: a falsification at an evaluated state stands, and a
    pass needs every registered state, so with a state missing a pass is inconclusive.
  The report lists every missing state and the links it bounds.

**Water activity at drying states (cp2 fix F7, Q13).** The ion activity product stays
IAP = a_Ca a_CO3. For a hydrated ACC framing CaCO3.nH2O the full product carries a_w^n, and
omitting it overstates Omega by the factor a_w^(-n) whenever a_w < 1. The drying states are
therefore optimistic in the screen: their Omega, and with it the C3 driving force, is biased
toward feasibility. Two requirements follow:
- a_w (`params.a_w_slurry`, per registered drying state) is reported at each drying state;
- where W1 supplies n (`params.acc_hydration_n`), the labelled sensitivity `Omega_bulk_hydrated`
  (contract) is reported beside every drying-state verdict. It never decides a verdict.

**Truncation of gamma_sl0 at zero (cp3 R8).** The Ca-free template-liquid energy
(`params.gamma_sl0_template`) is sampled from its sourced prior truncated to gamma_sl0 >= 0.
A negative interfacial free energy would make the template disperse or swell in water without
limit, so no sharp template-water interface would exist (interface stability,
`theory/ignorance_priors.md`, Section 1). The untruncated prior is run as a labelled
sensitivity, and the report prints the mass the truncation removed and every verdict that
changes without it.

**Bookkeeping (contract v2, unchanged in v3).** Every barrier is evaluated with Omega = Omega_bulk at the regime
activities. The C2 binding enters only through Delta_gamma_ads in gamma_sl, and C2 itself is a
reported descriptor, not a gate (Section 2) (derivation, Section 7
(rule), Eqs. (33) to (36) [th:eq:gibbs to th:eq:composite]). `Omega_local_ideal` and the demonstration composites never enter a
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
| C5 window margin m_E | set by W1 as for m_W; applies to a DFT scheme only where no experimental route exists (cp3b A1) | `thresholds.C5.window_margin` (W1 key `window_margin`) |
| C5 experimental margin m_expt (cp3 R2) | set by W1: the experimental uncertainty budget of the governing route (tabulated uncertainties plus the bound on the neglected Ca(ClO4)2 solid entropy from analog entropies); applies to the all-experimental route (cp3b A1) | `thresholds.C5.window_margin_expt` (W1 key `window_margin_expt`) |

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
  Amended at cp3 (R3): coalescence is a second route to feasibility, not only a supporting
  condition (Section 2, C4).
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
- **Terminations (cp3 R8).** The populated oxide terminations are judged one by one, and the
  report gives a C1 verdict per termination.
  - The mixture verdict uses an ignorance mixture over the weights
    (`regimes.R-slurry.parameters.termination_weights`): the weights are drawn uniformly on the
    simplex (a flat Dirichlet), or uniformly on the sub-region W1's evidence bounds, and the band
    masses are those of the mixture with the weights drawn alongside every other input.
  - A point weight is never used: no fetched distribution of terminations exists, and a point
    weight would put an unsourced number into the verdict.
  - The C1 link verdict is the mixture verdict; the per-termination verdicts are printed beside
    it, and a termination that alone is falsified is named.
- **Regime.** R-slurry only. Retention in the cell is not judged (layer persistence is a stated
  limitation).

### C2, sequestration (R-slurry): a binding descriptor, not a gate

C2 is a binding descriptor. It enters C3 only through Delta_gamma_ads and is not an independent
kill criterion (cp2 ruling, fix F3).

- **Why it does not gate.** At equilibrium the Ca2+ chemical potential is uniform, so binding does
  not raise the driving force (derivation, Section 4). Its only route to nucleation is the
  template-liquid energy, through Delta_gamma_ads, Eq. (33) [th:eq:gibbs], and that route is
  already judged inside C3. A separate C2 verdict would judge the same binding a second time, as a
  pass or kill of its own, which is the double count the bookkeeping removes. At fixed gamma_sl0
  and gamma_sn, the C2 term raises the C3 barrier: SF2, Eq. (35) [th:eq:young-ads].
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
  `cos_theta_young` with an in-situ gamma_sl), Eq. (35) [th:eq:young-ads]. The deck's starting
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
  keyed by `regimes.R-slurry.parameters.framing`. A draw that mixes framings is refused. Both
  framings are registered (cp3 R6), and each is run as a whole chain (Section 3, "Framings").

**(b) Accessibility part: absolute barrier in k_B T.**

- **Threshold and physics.** Eqs. (25) and (26) [th:eq:rate, th:eq:access]. Nuclei form on the
  template at J = J_0 exp(-DG_het / k_B T) per area and time. At least the areal density N_req
  must form within the time t_p that the template spends at the registered R-slurry states:
  N_nuc = sum over states k of J_0 Delta t_k exp(-DG_het,k / k_B T) >= N_req. At a single state
  this is

  DG_het <= B_acc = k_B T ln(J_0 t_p / N_req),

  with DG_het at Omega_bulk. A count N on a collector area A enters as N_req = N / A.
- **N_req (cp2 fix F4, amended at cp3 R5).** N_req is a separately fixed areal density, not the
  C4 closure density:

  N_req = ln(1/q_0) / A_patch, with q_0 = 1 - p_cred,

  with A_patch the particle-collector contact patch, a literature process input.
  - Physics (derivation, Section 5, Eq. [th:eq:nreq]): if nuclei land independently with mean
    areal density N_nuc, the number under one patch is Poisson with mean N_nuc A_patch, so the
    fraction of patches with no nucleus is exp(-N_nuc A_patch). N_nuc >= N_req is exactly the
    statement that at most a fraction q_0 of the patches is left without a nucleus.
  - q_0 = 1 - p_cred ties the admissible fraction of empty patches to the credible level, so it
    moves with the p_cred sweep. The cp2 form 1/A_patch is the special case q_0 = 1/e, which is
    not registered.
  - The closure density N_s_closure stays in C4 only.
- **Keys.**
  - J_0 = `regimes.R-slurry.parameters.J0_het`: a loguniform prior over its fetched range, because
    only ln J_0 enters.
  - t_p = `regimes.R-slurry.parameters.t_proc`: per registered state, slurry contact and drying.
  - A_patch = `regimes.R-slurry.parameters.patch_area`: the particle-collector contact patch
    (literature process input), with N_req = ln(1/(1 - p_cred))/A_patch. The former key
    `thresholds.C3.N_req` is no longer an independent input: W1 records it as derived from
    `patch_area` and the credible level.
  - The Poisson-occupancy form, proposed in `theory/cp2_brief.md` section D, is the registered
    rule since cp3 (R5).
- **Margin.** None beyond the J_0 prior. N_nuc ignores exclusion zones, so it is an upper estimate
  and the criterion is necessary, not sufficient. A state with Omega_bulk <= 1 contributes no
  nuclei.
- **Decision.** feasible if `P(N_nuc >= N_req) >= p`; falsified if `P(N_nuc < N_req) >= p`;
  inconclusive otherwise.
- **Reported, not gating.** DG_het / k_B T and the homogeneous reference DG_hom / k_B T at the
  same state.

**C3 verdict (joint mass, cp3 R7).** Per draw C3 is good only if (a) and (b) are both good.
feasible if P((a) good and (b) good) >= p; falsified if P((a) bad or (b) bad) >= p; inconclusive
otherwise. Either part falsified on its own is sufficient for a falsified C3.

### C4, conformality (R-slurry for wetting, R-cell for the thickness bound)

- **Chosen criterion (lane note N1).** X = `S_spread` (J m^-2), Eq. (37) [th:eq:spread].
  - Derivation Eq. (39) [th:eq:n1] shows that a small-angle bound theta <= theta_max and
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
- **Second route (independent; cp3 R3, formerly the supporting condition): coalescence below the thickness bound.**
  - The condition is N_s >= N_s_closure = tan^2(theta/2) / (2 d_max^2), Eq. (40)
    [th:eq:nclosure], with d_max = max(d_max_ohm, d_max_tun), Eqs. (47) to (49) [th:eq:ohm to th:eq:combined].
  - The island density is N_s = N_nuc from C3(b), an upper estimate. A failure of closure with
    N_nuc is therefore conservative, and a success is only optimistic.
  - The condition is geometric: it uses the geometric thicknesses h_c and h_cl. The charter's
    kinetic critical coalescence thickness (C4 candidate (c)) is named h_coal (cp2 fix F9). It
    needs a nucleation-and-growth model and is not computed in P0.
- **Decision (cp3 R3, with the joint mass of cp3 R7).** Either route to a continuous film
  suffices: complete wetting, or islands that close below the thickness bound. Per draw, C4 is
  good if S_spread >= m_S **or** N_nuc >= N_s_closure, with N_nuc the upper estimate of C3 (b)
  (the path sum over the registered states). The link masses are those of this indicator:
  P_bad(C4) = P(S_spread < m_S and N_nuc < N_s_closure), computed draw by draw, and
  P_good(C4) = 1 - P_bad(C4).
  - feasible if P_good(C4) >= p. In particular `P(S_spread >= m_S) >= p` **or**
    `P(N_nuc >= N_s_closure) >= p` is sufficient (cp3 R3). A feasible verdict reached through
    closure inherits the optimism of the upper estimate, and the report gives the mass of each
    route separately and says which carried the verdict;
  - falsified if P_bad(C4) >= p, which needs both routes to fail at p: `P(S_spread < m_S) >= p`
    **and** `P(N_nuc < N_s_closure) >= p`;
  - inconclusive otherwise.
- **Reported: P(gamma_sl > gamma_nl).** Complete wetting needs gamma_sl >= gamma_nl + gamma_sn >=
  gamma_nl, because gamma_sn >= 0. The prior mass P(gamma_sl > gamma_nl) (gamma_sl at the regime
  activities) is therefore an upper bound on the mass the S_spread route can ever carry, and the
  report prints it at every registered state.
- **Physical result (cp3 R3; derivation, Section 8; `theory/ignorance_priors.md`, Section 2).**
  For any hydrophilic template, gamma_sl <= gamma_nl: water wets the template at least as
  favourably, per area, as it wets the mineral. Then S_spread = gamma_sl - gamma_sn - gamma_nl <=
  -gamma_sn < 0 for every admissible gamma_sn > 0, so complete wetting is excluded whatever the
  template-nucleus contact is, and the C4 S_spread route fails. C4 then rests on coalescence alone.
  Ca2+ binding lowers gamma_sl further (Delta_gamma_ads < 0 for a binding template), so the
  mechanism's own C2 premise works against complete wetting. This is a physics result, not a
  property of the ignorance prior.
- **Regimes.** The wetting energies are R-slurry (solid-water). d_max is the R-cell
  electron-transfer bound and is reported as a limitation, not a performance figure.

### C5, thermodynamic stability (R-slurry and R-cell)

**R-slurry, dissolution: decided by Omega_bulk (cp3 R1).**

- **Threshold and physics.** X = `Omega_bulk` = a_Ca a_CO3 / K_sp with the sourced calcite solubility
  product (`params.log10_ksp_calcite`) and the free-ion activities of the contract's carbonate
  speciation (`a_CO3_speciation`, `a_Ca_speciation`) at the regime pH, C_T, Ca_T and I.
  - A CaCO3 layer in contact with the slurry dissolves when Omega_bulk < 1 and is stable against
    dissolution when Omega_bulk >= 1. The edge is 1, with no margin: the K_sp prior and the
    speciation inputs carry their own uncertainty.
  - This is the quantity C3 uses (derivation, Section 9, Eq. (43) [th:eq:pbx-omega]). A state that
    cannot nucleate CaCO3 (Omega_bulk <= 1, no nuclei in C3 (b)) is a state in which the layer
    dissolves. At equilibrium enrichment does not raise Omega (derivation, Section 7, rule 5),
    so the bulk state decides; an "enriched" evaluation is a labelled non-equilibrium
    sensitivity, never a verdict.
- **Why a hull distance cannot decide dissolution.** At fixed C(IV) the hull distance of CaCO3
  against its dissolved ions is (R T / n_M) ln(1/Omega_bulk) per non-O, non-H atom, Eq. (43)
  [th:eq:pbx-omega].
  - The tolerance n_at e_f / n_M therefore reports dissolution only below
    ln Omega_bulk = -n_at e_f / (R T): the edge alone spans several decades of Omega.
  - An error of the computed dissolution free energy shifts the proxy's K_sp by that error over
    R T ln 10 decades. With the database's dissolved-ion reference this is a bias of its own.
  - W5's falsifiability control (`ops/reports/P0-W5.2.md`, Task B) measured both. The hull
    construction is therefore not used for dissolution.
- **K_sp and framing.** The calcite K_sp decides under every registered framing (Section 3,
  "Framings"). Under the ACC framing, Omega_bulk with the ACC K_sp is the labelled sensitivity
  C5s_ACC (cp2 fix F6, below). It never decides.
- **Design axes: the dose window.** The verdict is computed at each design point of the
  registered axes (a_Ca, C_T): a_Ca the free Ca2+ activity (`params.a_ca_slurry`; where the
  registered grid is in total calcium, `params.ca_total_slurry`, a_Ca is its speciated value and
  both are printed) and C_T the dissolved inorganic carbon (`params.dic_slurry`). The report gives
  the dose window, the set of design points at which C5s is feasible (P(Omega_bulk >= 1) >= p), with
  the falsified and inconclusive sets beside it. Because C3 consumes the same activities, the
  study verdict is formed design point by design point (Section 3).
- **Falsifiability control (C5 item 21), applied to the Omega test.** At W5's registered
  undersaturated control state (pH from `params.ph_slurry_modified`, the lowest registered C_T and
  a_Ca) the Omega test must report dissolution, and at the supersaturated control state it must
  report stability. If either control does not come out as it must, C5s is inconclusive.
- **Carbon redox (assumption).** The regime fixes a_CO3 (G0 fix F2), and carbon is held in the
  C(IV) carbonate system: reduction of dissolved carbonate to CH4 is not observed in aqueous
  processing, so the reduced-carbon phases of the database are not admitted. The construction
  with carbon redox allowed is reported as a labelled sensitivity, never a verdict, and it is
  not a rate statement.
- **States.** Every registered R-slurry state is evaluated, and the verdict is the worst over them
  (Section 1, "States").
- **Decision (per design point).**
  - feasible if `P(Omega_bulk >= 1) >= p` at every registered state, **and** the control comes
    out as it must;
  - falsified if `P(Omega_bulk < 1) >= p` at some evaluated state;
  - inconclusive otherwise, or if the control fails.

**R-slurry, competing phases and the Al baseline: aqueous Pourbaix at fixed C(IV).**

- **Competing-phase test.** X = `Delta_G_pbx` (J mol^-1 per non-O, non-H atom), Eq. (42)
  [th:eq:pbx], for the registered CaCO3 framing phase, with C(IV) fixed at the regime C_T.
  - The competitors are the solid phases of the system. The dissolved Ca-bearing species are
    removed from the hull: dissolution is decided by the Omega test above, so the hull answers
    only whether another solid (a hydroxide, an Al-Ca or Al-C compound) lies below CaCO3.
  - It is evaluated over the registered (pH, E_SHE) region
    (`regimes.R-slurry.parameters.pH_range` and `regimes.R-slurry.parameters.E_SHE_range`),
    worst point.
- **Tolerance (DFT).** tau_hull = n_at e_f / n_M, where e_f = `thresholds.C5.formation_energy_error`
  is the expected error of a computed formation energy per atom, from the database benchmark. Per
  non-O, non-H atom this is the error of the phase's own formation energy, the largest single
  error entering its hull distance. For the ACC framing the edge is
  (n_at e_f + Delta_ACC) / n_M, with Delta_ACC = `regimes.R-slurry.parameters.ACC_offset`. ACC is
  never on the hull, and its metastability above calcite is part of the framing, not an
  instability.
- **What the ACC edge tests (cp2 fix F6).** Adding Delta_ACC to the edge makes the ACC test
  equal to the calcite-level test. ACC lies above calcite by Delta_ACC per formula unit, so
  Psi_ACC = Psi_calcite + Delta_ACC / n_M. It is never on the hull, so the hull is the same with or
  without it. The ACC test, Delta_G_pbx(ACC) <= (n_at e_f + Delta_ACC) / n_M, is therefore
  identical to Psi_calcite - Psi_hull <= n_at e_f / n_M. In words, the competing-phase test decides
  whether CaCO3 is stable as a phase against the other solids at the regime activities, up to the
  metastability that defines the framing. It does not decide whether ACC itself survives.
- **ACC-specific dissolution margin (labelled sensitivity, not gating).** Whether the regime
  solution is supersaturated with respect to ACC is Omega_bulk evaluated with the ACC solubility
  product, the quantity that already enters C3 through K_sp under the ACC framing. C5 reports
  `P(Omega_bulk >= 1)` for the ACC framing at each registered state, labelled as the ACC
  dissolution sensitivity. A value of Omega_bulk below 1 there means ACC dissolves at that state
  even where calcite-level CaCO3 passes C5.
- **Decision.**
  - feasible if `P(Delta_G_pbx <= edge) >= p` at every point;
  - falsified if `P(Delta_G_pbx > edge) >= p` at some point;
  - inconclusive otherwise.
- **Al phases.** The native oxide's Pourbaix state is reported as the bare-oxide baseline, at
  the same fixed C(IV) and with the same DFT tolerance. It does not gate C5, because alkaline
  attack on the native oxide is the corrosion mode the slurry regime describes.

**C5 R-slurry verdict.** feasible if the dissolution test and the competing-phase test are both
feasible; falsified if either is falsified; inconclusive otherwise.

**Disclosure (cp3 R1).** The rule was set after W5 reported that the Pourbaix screen's
falsifiability control does not fail where it must, and after W5 printed the sourced-K_sp Omega
beside each of its design points (`ops/reports/P0-W5.2.md`, Task B). The rule is therefore not
independent of those values, and the report says so.

**R-cell, Li-referenced window (cp3 R2).**

- **Threshold and physics.** Eq. (45) [th:eq:window] with the electrolyte-fixed sink of Eq. (46)
  [th:eq:sink] for the gated phases (Section 2, C5, "Gated phases"). The collector potential range
  [E_cell_min, E_cell_max] (V vs Li+/Li) must lie inside each phase's window: E_red below
  E_cell_min and E_ox above E_cell_max, each beyond its margin.
- **Governing route (cp3 R2).** Wherever its inputs exist, the **all-experimental route**
  (`expt`: tabulated thermochemistry of every reactant and product, gas references included)
  governs the limit.
  - The DFT-referenced schemes (`regimes.R-cell.parameters.gas_reference_schemes`, database
    solids with a JANAF or a database CO2 reference) are **comparators**, each printed with its
    measured benchmark error (W5's gas-reference benchmark).
  - A DFT scheme corrected by its own benchmark error equals the experimental route by
    construction, because the benchmark is that experimental route. A benchmark-corrected value is
    therefore not a second confirmation, and it is never counted as one.
  - Where an input of the experimental route is missing (a reaction with no tabulated product),
    the limit is decided by the cp2 rule over the DFT schemes (fix F5: a pass under the
    lowest-onset scheme, a falsification under every scheme, margin m_E), and the report marks the
    limit as DFT-decided.
- **Margin m_expt.** The experimental uncertainty budget of the route
  (`thresholds.C5.window_margin_expt`, W1 key `window_margin_expt`, per transferred electron), not
  the DFT formation-energy margin:
  - the tabulated uncertainties of every reactant and product, combined per transferred electron
    (W1 keys `params.u_tab_dfh_ca_clo4_2`, `params.u_tab_dfh_liclo4`, `params.u_tab_dfg_co2`,
    `params.u_tab_dfg_caco3`);
  - plus a bound on the neglected solid entropy of Ca(ClO4)2, whose free energy enters through its
    tabulated enthalpy (W5's exchange route), taken from the entropies of analog solid salts. W1
    carries it as the bound on the neglected exchange entropy (`params.exchange_entropy_bound`),
    built from the analog entropy span (`params.s_ca_clo4_2_analog_low`,
    `params.s_ca_clo4_2_analog_high`).

  W1 derives the value and lists its parts in the key's notes.
- **Margin-to-scheme mapping (cp3b A1).** Each margin belongs to one route, and a limit is
  judged with the margin of the route that decides it:

  | Route deciding the limit | Margin | Key (params path; W1 key) |
  |---|---|---|
  | all-experimental route (`expt`), wherever its inputs exist | m_expt | `thresholds.C5.window_margin_expt`; `window_margin_expt` |
  | DFT schemes, **only where no experimental route exists** (the cp2 F5 rule: pass under the lowest-onset scheme, falsification under every scheme) | m_E | `thresholds.C5.window_margin`; `window_margin` |
  | DFT schemes and benchmark-corrected schemes where the experimental route exists | none: comparators, printed with their measured benchmark errors, never deciding | (none) |

  - **Why the margins differ.** m_expt bounds the error of tabulated thermochemistry, so it is the
    whole error of the `expt` route. m_E bounds the error of computed formation energies, so it
    belongs only to a limit that rests on them. Applying m_E to the `expt` route would charge a
    tabulated value with a DFT error it does not carry. Applying m_expt to a DFT scheme would
    understate that scheme's error.
  - **One margin per reaction and sink.** A margin is the budget of one reaction with one sink.
    `window_margin_expt` is the budget of the registered reaction
    CaCO3 + 2 LiClO4 -> Ca(ClO4)2 + CO2 + 1/2 O2 + 2 Li with the solid-salt sink. `window_margin`
    is m_E for the same reaction. For a DFT-decided limit of any other reaction, m_E follows the
    rule W1 used: m_E = n_unc e_f / (Delta_n F). Here n_unc is the number of atoms whose computed
    formation energy does not cancel between the two sides, and Delta_n is the number of electrons
    transferred per formula unit. For the registered reaction, n_unc counts the five atoms of
    CaCO3 and Delta_n = 2. An `expt` limit of any other reaction, including the same reaction with
    the solvated sink (whose solvation terms add their own uncertainty), needs its own budget key.
  - **A limit whose margin key is absent is `undetermined`.** It never gives a pass and never
    falsifies (Section 2, C5, "Undetermined never passes").
- **Oxidation rule (the governing route).**
  - **falsified** if E_ox(expt) + m_expt < E_cell_max, with either sink. The solid-salt sink stands
    here: the true product is the lower in free energy of the solid salt and the solvated ions, so
    a solid-salt onset is an upper bound on the true onset, and a falsification computed with it
    stands.
  - **feasible** only if E_ox(expt) - m_expt >= E_cell_max with the **solvated sink**. A pass
    computed with the solid-salt sink is inconclusive, because the solvated sink can only lower the
    onset.
  - inconclusive otherwise.
- **Reduction rule.** The same with the signs mirrored: falsified if E_red(expt) - m_expt >
  E_cell_min; feasible if E_red(expt) + m_expt <= E_cell_min; inconclusive otherwise. The
  reduction limits are Li-open and need no gas reference.
- **E_cell_max is a design axis.** The charge cutoff is a property of the cathode, so it is
  registered per cathode class (`regimes.R-cell.parameters.E_max`, keyed by
  `regimes.R-cell.parameters.cathode_class`), and the verdict is reported as a function of the
  cutoff:
  - falsified for every cutoff above E_ox(expt) + m_expt;
  - feasible (solvated sink only) for every cutoff at or below E_ox(expt) - m_expt;
  - inconclusive between.

  The report prints these two crossover cutoffs for each gated phase and sink, and the verdict of
  each registered cathode class.
- **Every scheme in one table.** For each gated phase and sink the report prints E_ox and E_red
  under `expt`, under each DFT scheme, and under each benchmark-corrected DFT scheme, with the
  benchmark errors, whether or not they decide.
- **Disclosure (cp3 R2).** The scheme values for CaCO3 with LiClO4 were seen before this rule was
  set (`ops/reports/P0-W5.2.md`, Task C; cp3 packet decision 3). The rule is not independent of
  them, and the report says so beside the table.
- **Gated phases (cp3 R8).** CaCO3, corundum (alpha-Al2O3) and boehmite (gamma-AlOOH). The
  registration key `regimes.R-cell.parameters.al_phases` records corundum and boehmite. Other Al
  phases (diaspore, gibbsite and the transition aluminas) are reported, not gated.
- **Sink (cp2 fix F5 (b)).** A pass counts only with a solvated sink: Ca2+ or Al3+ leaving as
  solvated ions paired with the salt anion, with the solvation free energies relative to Li+.
  The LiBOB and LiPCP sinks stay undetermined (cp3 R8): they never give a pass.
- **Undetermined never passes.** A limit with status `undetermined` (a missing sink phase, a
  missing solvation free energy for the solvated sink, an unregistered salt, or an unbounded
  Li-open limit) gives at best inconclusive.
- **Why carbonate oxidation is the right reading (physics).** Derivation, Section 9, "The
  oxidation sink": the measured onset of Li2CO3 oxidation (`params.li2co3_oxidation_onset`) lies
  near the experimental equilibrium limit of the same reaction (W5 benchmark B6), so a carbonate
  in the cell oxidises close to its thermodynamic limit. That supports reading the CaCO3 limit as
  the onset of an observable reaction, not only as a bound.
- **Decision.**
  - feasible if both rules are feasible for every gated phase, every registered sink determined,
    with a solvated sink;
  - falsified if, for any gated phase, a limit is falsified by the governing route (or, where the
    experimental route is missing, under every DFT scheme);
  - inconclusive otherwise.

  The limits are deterministic, so the band mass is 0 or 1 for each route and sink.
- **Limitation: the electrolyte's own anodic limit (cp2 fix F5 (c)).** Above the electrolyte's
  anodic limit the solvent and salt oxidise first. C5 does not assess that limit. A pass of the
  E_ox test says only that the gated phases are stable up to E_cell_max against the registered
  sinks, not that the electrolyte is.

**C5 verdict.** feasible if both regimes are feasible; falsified if either is falsified;
inconclusive otherwise.

## 3. Study-level verdict

- **Combination.** The gating links are C1, C3, C4 and C5. C2 is a reported descriptor (Section
  2). The study is
  - falsified if any of C1, C3, C4 or C5 is falsified. C1, C3 and C4 are sequential links, any
    one of which can end the mechanism; C5 is a necessary screen;
  - feasible only if all four are feasible and the deletion test below holds;
  - inconclusive otherwise.
- **Design points (cp3 R1).** The verdicts are computed at each design point of the registered
  axes (gap policy (ii): a_Ca and c_bulk; for the C5 dissolution test, (a_Ca, C_T)). The study
  verdict at a design point combines the link verdicts at that point, and the report maps it over
  the axes. C5 R-slurry reports its feasible set as the dose window.
- **Sequestration premise.** The C2 finding of Section 2 is reported with the study verdict. If
  the premise fails, the report says so as a finding, whatever the verdict.
- **Framings (cp3 R6).** Calcite and ACC are both registered framings
  (`regimes.R-slurry.parameters.framing`). The screen runs the whole chain once per framing, with
  K_sp, V_m and gamma_nl of that framing in every link (Q12), and forms a study verdict per framing
  (including its deletion test). The registered study verdict combines them:
  - **falsified** only if the study is falsified under every registered framing;
  - **feasible** if it is feasible under at least one framing. The report names that framing and
    prints the verdict under the other framing beside it;
  - **inconclusive** otherwise.

  Framings are never mixed across links: a chain that is feasible under ACC in C3 and under
  calcite in C4 is not feasible. The C5 dissolution test uses the calcite K_sp under both framings
  (Section 2, C5).
  - **Disclosure.** A calcite-framing estimate near one half was available when the project was
    designed (lane note N5). Registering both framings, with the rule above, keeps the verdict
    from depending on a framing chosen after that estimate; the paper states the sequence.
- **Deletion test (`charter/deletion_register.yaml`, F1).** Only the controls that remove the
  mechanism gate it: `bare_oxide` and `PVDF`.
  - For each of the two, the screen is rerun with the control in place of the template, at the
    same states and with the same rules.
  - The test holds if, for each control, at least one of C3 or C4 degrades. A link degrades
    when its verdict is strictly worse (feasible < inconclusive < falsified), or when its joint
    falsified-side mass (Section 1, cp3 R7) rises by at least p_deg
    (`thresholds.decision.degrade_mass_min`).
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
| `regimes.R-slurry.parameters.framing` | framing | registration (cp3 R6: calcite and ACC both registered) | C3, C4, C5 sensitivity; study combination |
| `regimes.R-slurry.parameters.J0_het` | J0_het | literature | C3 (b), C4 |
| `regimes.R-slurry.parameters.t_proc` | t_proc | literature or process input | C3 (b), C4 |
| `regimes.R-slurry.parameters.patch_area` | A_patch | literature (process input; N_req = ln(1/(1 - p_cred))/A_patch, cp3 R5) | C3 (b) |
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
| `params.log10_ksp_calcite` | K_sp (calcite) | literature | C5 dissolution under every framing (cp3 R1) |
| `params.a_ca_slurry` | a_Ca | design axis | C5 dissolution dose window, C3 (cp3 R1) |
| `params.ca_total_slurry` | Ca_T | design axis (total calcium) | speciation of a_Ca (cp3 R1) |
| `params.dic_slurry` | C_T | design axis | C5 dissolution dose window, speciation (cp3 R1) |
| `params.ph_slurry_modified` | pH (control) | literature | C5 falsifiability control (cp3 R1) |
| `params.a_w_slurry` | a_w | literature (per drying state) | reported at every drying state (F7) |
| `params.acc_hydration_n` | n_hyd | literature (ACC framing) | hydrated-IAP sensitivity (F7) |
| `regimes.R-slurry.parameters.E_SHE_range` | E_SHE | literature | C5 |
| `thresholds.C5.window_margin` | m_E | literature (derived from e_form; W1 key `window_margin`) | C5 R-cell, a DFT scheme only where the experimental route is missing (cp3 R2, cp3b A1) |
| `thresholds.C5.window_margin_expt` | m_expt | literature (experimental uncertainty budget; W1 key `window_margin_expt`; formerly named `thresholds.C5.expt_margin` here) | C5 R-cell governing route (cp3 R2, cp3b A1) |
| `params.u_tab_dfh_ca_clo4_2` | u_tab | literature (tabulated uncertainty) | m_expt (cp3b A1) |
| `params.u_tab_dfh_liclo4` | u_tab | literature (tabulated uncertainty) | m_expt (cp3b A1) |
| `params.u_tab_dfg_co2` | u_tab | literature (tabulated uncertainty) | m_expt (cp3b A1) |
| `params.u_tab_dfg_caco3` | u_tab | literature (tabulated uncertainty) | m_expt (cp3b A1) |
| `params.exchange_entropy_bound` | Delta_S_ex bound | literature (analog entropies) | m_expt (cp3 R2; the solid-entropy part as W1 derived it) |
| `params.s_ca_clo4_2_analog_low` | S analog (low) | literature (analog entropies) | m_expt (cp3 R2) |
| `params.s_ca_clo4_2_analog_high` | S analog (high) | literature (analog entropies) | m_expt (cp3 R2) |
| `regimes.R-cell.parameters.cathode_class` | cathode class | design axis | E_cell_max per class (cp3 R2) |
| `params.li2co3_oxidation_onset` | E (Li2CO3 onset) | literature | physics justification of the carbonate-oxidation reading (cp3 R2) |
| `regimes.R-cell.parameters.E_min` | E_cell_min | literature | C5 R-cell |
| `regimes.R-cell.parameters.E_max` | E_cell_max | literature; design axis by cathode class (cp3 R2) | C5 R-cell |
| `regimes.R-cell.parameters.electrolyte_salts` | salts | literature (fluorine-free) | C5 R-cell sink |
| `regimes.R-cell.parameters.gas_reference_schemes` | schemes | registration (cp2) | C5 R-cell |
| `regimes.R-cell.parameters.al_phases` | phases | registration (cp3 R8: corundum and boehmite) | C5 R-cell |
| `params.gamma_sl0_template` | gamma_sl0 | literature, truncated at 0 (cp3 R8) | C3, C4 through gamma_sl |

The C2-to-C3 inputs that the thresholds consume through Delta_gamma_ads are the existing priors
`Gamma_s`, `delta_s`, `c_bulk` and `gamma_sl0`. `gamma_sl0` is new in contract v2 and replaces a
Ca-free reading of `gamma_sl`.

## 5. Machine-readable form

W4 copies this block into `configs/preprint/thresholds.yaml`. Expressions use the ids of
`theory/symbols.yaml` and the functions of `theory/contract.yaml`. `theory/tools/check_contract.py`
checks that every expression parses, that only registered ids appear, and that each edge has the
unit of its quantity.

```thresholds
version: 3
authority: theory/thresholds.md
written_before_screen_output: true
base_commit: 49100a9d92b5dc48f1db1d15529967dfeeece12d
revised: {session: P0-W3.2 cp2 fix-up, base_commit: 800d5ea3de41a0fb16084519d5c2680eeb14952d, fixes: theory/cp2_fixes.md}
revised_cp3: {session: P0-W3.3, ruling: planning chat 2026-10-17 (cp3), base_commit: ac5cdfb, items: [R1, R2, R3, R5, R6, R7, R8],
              log: theory/cp2_fixes.md (cp3 section), disclosures: [R1, R2, R6]}
revised_cp3b: {session: P0-W3.4, rule: cp3-mandated registrations for production (lane note N22), base_commit: 227d997,
               items: [A1], log: theory/cp2_fixes.md (cp3 section, cp3b registrations), screen_output_consulted: false}
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
    m_expt: {set_by: W1, from: experimental uncertainty budget of the expt route (cp3 R2), params: thresholds.C5.window_margin_expt}
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
  link_mass:
    rule: joint, draw by draw, on the same draws (cp3 R7 (1))
    and_links: 'falsified side = P(any test bad)'
    C4: 'falsified side = P(S_spread route bad and closure route bad)'
    verdict: shared rule on the joint masses; single-test masses reported
    deletion_test: joint falsified-side mass
  states:
    propagate: every registered state of the regime (cp3 R7 (4))
    worst_state_links: falsification at an evaluated state stands; a pass needs every registered state
    path_sum: 'C3b (and the C4 closure route) cannot be falsified unless every registered state, drying included, is evaluated; with a state missing a shortfall is inconclusive and a pass stands'
    report: missing states and the links they bound
  priors:
    gamma_sl0: {truncate_below: '0', reason: interface stability, sensitivity: untruncated prior, labelled,
                report: [truncated mass, verdicts that change], params: params.gamma_sl0_template}
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
        mixture: {over: termination, weights: regimes.R-slurry.parameters.termination_weights,
                  weight_prior: 'ignorance: uniform on the simplex (flat Dirichlet), or on the sub-region W1 bounds',
                  point_weight: never, per_termination_verdicts: reported (cp3 R8)}
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
        edge: log(1/(1 - p_cred))/A_patch
        N_req: {equals: log(1/(1 - p_cred))/A_patch, q_0: 1 - p_cred, rule: cp3 R5 (Poisson occupancy; empty-patch fraction at most q_0),
                not: the C4 closure density}
        equivalent_single_state: {quantity: DG_het, comparator: '<=', edge: k_B*T*log(J0_het*t_proc*A_patch/log(1/(1 - p_cred)))}
        params: {J0_het: regimes.R-slurry.parameters.J0_het, t_proc: regimes.R-slurry.parameters.t_proc,
                 A_patch: regimes.R-slurry.parameters.patch_area, p_cred: thresholds.decision.credible_level}
        report: [DG_het/(k_B*T), DG_hom/(k_B*T)]
    combine: 'C3a and C3b'
    joint_mass: 'falsified side P(C3a bad or C3b bad), draw by draw (cp3 R7)'
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
        role: alternative route (cp3 R3; was supporting)
        quantity: N_nuc
        comparator: '>='
        edge: tan(theta/2)**2/(2*d_max**2)
        d_max: {max_of: [d_max_ohm, d_max_tun]}
        params: {R_A_max: regimes.R-cell.parameters.R_A_max, j_req: regimes.R-cell.parameters.j_req,
                 rho_e: regimes.R-cell.parameters.rho_e, phi_B: regimes.R-cell.parameters.phi_B,
                 m_e: regimes.R-cell.parameters.m_eff, j_0: regimes.R-cell.parameters.j_0}
    combine:
      indicator: 'good per draw if C4 holds or C4s holds'
      feasible: 'P(C4 holds or C4s holds) >= p_cred (sufficient: C4 feasible, or C4s feasible)'
      falsified: 'P(C4 fails and C4s fails) >= p_cred (needs C4 falsified and C4s falsified)'
      inconclusive: otherwise
      joint_mass: 'falsified side P(S_spread < m_S and N_nuc < N_s_closure), draw by draw (cp3 R7)'
      N_nuc: upper estimate of C3b (path sum); a pass through closure is optimistic and labelled
    report_mass: 'P(gamma_sl > gamma_nl) at every registered state'
    complete_wetting_excluded_when: 'gamma_sl <= gamma_nl (hydrophilic template): S_spread <= -gamma_sn for every admissible gamma_sn'
  C5:
    regimes: [R-slurry, R-cell]
    tests:
      - id: C5s
        regime: R-slurry
        role: dissolution
        aggregation: worst_state
        quantity: Omega_bulk
        comparator: '>='
        edge: '1'
        K_sp: calcite under every registered framing (cp3 R1); ACC is the sensitivity C5s_ACC
        activities: {a_Ca: a_Ca_speciation, a_CO3: a_CO3_speciation}
        params: {K_sp: params.log10_ksp_calcite, a_Ca: params.a_ca_slurry, Ca_T: params.ca_total_slurry,
                 C_T: params.dic_slurry, pH: regimes.R-slurry.parameters.pH_range}
        design_axes: [a_Ca, C_T]
        report_as: dose window (design points where C5s is feasible), with the falsified and inconclusive sets
        shares_quantity_with: C3
        state: bulk
        requires: falsifiability_control_fails_where_it_must
        control:
          applies_to: C5s
          undersaturated: must report dissolution (P(Omega_bulk < 1) >= p_cred)
          supersaturated: must report stability (P(Omega_bulk >= 1) >= p_cred)
          params: {pH: params.ph_slurry_modified}
          on_failure: inconclusive
        carbon_redox: {assumption: 'C(IV) fixed by the regime (a_CO3); carbonate reduction to CH4 is not observed in aqueous processing',
                       sensitivity: construction with carbon redox allowed, labelled, never decides}
        hull_not_used_for_dissolution: 'hull distance (R*T/N_M)*log(1/Omega_bulk) per atom; the tolerance hides dissolution down to log(Omega_bulk) = -N_atoms*e_form/(R*T)'
      - id: C5s_phase
        regime: R-slurry
        role: competing_phase
        aggregation: worst_point
        quantity: Delta_G_pbx
        comparator: '<='
        edge_by_framing:
          calcite: N_atoms*e_form/N_M
          ACC: (N_atoms*e_form + Delta_ACC)/N_M
        params: {e_form: thresholds.C5.formation_energy_error, Delta_ACC: regimes.R-slurry.parameters.ACC_offset,
                 pH: regimes.R-slurry.parameters.pH_range, E_SHE: regimes.R-slurry.parameters.E_SHE_range}
        carbon: C(IV) fixed at the regime C_T
        competitors: solid phases only; dissolved Ca-bearing species excluded (dissolution is C5s)
        state: bulk
        acc_edge_equivalence: the ACC edge makes the test equal to the calcite-level test (cp2 fix F6)
        al_baseline: {reported: true, gating: false, tolerance: same DFT tolerance, carbon: C(IV) fixed}
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
        edge: E_cell_max + m_expt
        governing_route: expt (all-experimental thermochemistry) wherever its inputs exist (cp3 R2)
        pass: {route: expt, sink: solvated}
        falsify: {quantity: E_ox, comparator: '<', edge: E_cell_max - m_expt, route: expt, sink: [solvated, solid_salt]}
        otherwise: inconclusive
        comparators: {dft_schemes: regimes.R-cell.parameters.gas_reference_schemes, printed_with: measured benchmark errors,
                      benchmark_corrected: equals expt by construction; never a second confirmation}
        where_expt_missing: {rule: cp2 fix F5, pass: lowest-onset DFT scheme, falsify: every DFT scheme, margin: m_E,
                             edge_pass: E_cell_max + m_E, edge_falsify: E_cell_max - m_E, label: DFT-decided}
        params: {E_cell_max: regimes.R-cell.parameters.E_max, m_expt: thresholds.C5.window_margin_expt, m_E: thresholds.C5.window_margin,
                 schemes: regimes.R-cell.parameters.gas_reference_schemes,
                 salts: regimes.R-cell.parameters.electrolyte_salts}
        margin_by_route:
          expt: {symbol: m_expt, params: thresholds.C5.window_margin_expt, key: window_margin_expt, applies: wherever the expt inputs exist,
                 reaction: CaCO3 + 2 LiClO4 -> Ca(ClO4)2 + CO2 + 1/2 O2 + 2 Li (solid-salt sink)}
          dft_where_expt_missing: {symbol: m_E, params: thresholds.C5.window_margin, key: window_margin, rule: cp2 fix F5,
                                   formula: N_unc*e_form/(Delta_n_Li*F_c), formula_params: {e_form: thresholds.C5.formation_energy_error},
                                   registered_reaction: {N_unc: 5 atoms of CaCO3, Delta_n_Li: 2}}
          dft_where_expt_exists: {margin: none, role: comparator, printed_with: measured benchmark error}
          benchmark_corrected: {margin: none, role: comparator, never: a second confirmation}
          per_reaction: one margin per reaction and sink; an expt limit of any other reaction or sink needs its own budget key
          margin_key_absent: undetermined (never passes, never falsifies)
        m_expt_parts: [tabulated uncertainties of reactants and products per transferred electron,
                       bound on the neglected solid entropy of Ca(ClO4)2 from analog solid-salt entropies]
        m_expt_params: [params.u_tab_dfh_ca_clo4_2, params.u_tab_dfh_liclo4, params.u_tab_dfg_co2, params.u_tab_dfg_caco3,
                        params.exchange_entropy_bound, params.s_ca_clo4_2_analog_low, params.s_ca_clo4_2_analog_high]
        design_axis: {E_cell_max: by cathode class, params: regimes.R-cell.parameters.cathode_class,
                      report: [crossover E_ox - m_expt (feasible at or below, solvated sink), crossover E_ox + m_expt (falsified above)]}
        undetermined: never_passes
        solid_salt_sink: {falsification: stands, pass: inconclusive, reason: upper bound on the onset}
        table: every route and scheme printed (expt, each DFT scheme, each benchmark-corrected scheme)
        disclosure: scheme values were seen before this rule (cp3 R2; packet p0-3 decision 3)
        limitation: electrolyte anodic limit not assessed
      - id: C5c_red
        regime: R-cell
        quantity: E_red
        comparator: '<='
        edge: E_cell_min - m_expt
        governing_route: expt wherever its inputs exist (cp3 R2)
        pass: {route: expt}
        falsify: {quantity: E_red, comparator: '>', edge: E_cell_min + m_expt, route: expt}
        otherwise: inconclusive
        where_expt_missing: {rule: cp2 fix F5, margin: m_E, edge_pass: E_cell_min - m_E, edge_falsify: E_cell_min + m_E,
                             label: DFT-decided}
        params: {E_cell_min: regimes.R-cell.parameters.E_min, m_expt: thresholds.C5.window_margin_expt, m_E: thresholds.C5.window_margin,
                 schemes: regimes.R-cell.parameters.gas_reference_schemes}
        margin_by_route: same as C5c_ox (expt route m_expt; m_E only where the expt route is missing; a reduction limit needs its own budget key)
        undetermined: never_passes
    gated_phases: {R-slurry: [CaCO3 framing phase], R-cell: [CaCO3, corundum, boehmite]}
    al_phases: {registered: [corundum, boehmite], params: regimes.R-cell.parameters.al_phases, others: reported, not gated}
    sinks: {LiClO4: "CaCO3 via the Ca(ClO4)2 exchange route; Al phases undetermined until Al(ClO4)3 is tabulated", LiBOB: undetermined (never a pass), LiPCP: undetermined (never a pass)}
    combine: 'C5s and C5s_phase and C5c_ox and C5c_red'
study:
  framings:
    registered: [calcite, ACC]
    params: {framing: regimes.R-slurry.parameters.framing}
    run: whole chain per framing (K_sp, V_m, gamma_nl of one framing; never mixed across links)
    falsified: falsified under every registered framing
    feasible: feasible under at least one framing; name it and report the other beside it
    inconclusive: otherwise
    c5_dissolution: calcite K_sp under both framings
    disclosure: a calcite-framing estimate near one half was available when the project was designed (N5)
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
