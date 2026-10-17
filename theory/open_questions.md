# Open questions for the cp2 sign audit (sessions P0-W3.1, P0-W3.2)

Each entry lists a choice made in `theory/equation_sheet.tex`, `theory/derivation_body.tex` or
`theory/contract.yaml`, the alternative, and what changes if the alternative is taken.
Priorities: **A** can change the sign of a link's verdict, **B** changes magnitudes or the
uncertainty budget, **C** concerns scope or bookkeeping. Q1 and Q2 bear directly on the
no-double-counting proof of P0-W3.2.

| # | Pri. | Link | Topic |
|---|---|---|---|
| Q1 | A | C2→C3 | Enrichment bookkeeping (local-ideal versus grand-canonical) |
| Q2 | A | C2→C3 | Carbonate held at its bulk activity |
| Q3 | B | C2 | Activity coefficients and the Langmuir closure |
| Q4 | B | C2 | Site volume, standard state and protonation stoichiometry |
| Q5 | B | C1 | Contact-area normalisation of the PMF |
| Q6 | A | C3, C4 | Placement and sign of the water-displacement term |
| Q7 | B | C3 | Young beyond its range, and the computed contact angle |
| Q8 | A | C5 | Aqueous Pourbaix references and the ACC offset |
| Q9 | A | C5 | Li-open window for a Li-free phase |
| Q10 | B | C4 | Tunnelling parameters of the film bound |
| Q11 | C | C3 | One supersaturation variable |
| Q12 | B | C3 | Framing consistency of K_sp, V_m and gamma_nl |
| Q13 | B | C3 | Structural water in the ion activity product of ACC |
| Q14 | B | C4 | Lattice versus random nucleation sites in the closure estimate |
| Q15 | C | C4 | Conformality judged in water, not after drying |
| Q16 | C | C3 | Barrier accessibility without a kinetic prefactor |

## Dispositions (P0-W3.2, sign audit B1)

Equation numbers are those of the P0-W3.3 cp3 build of `theory/build/derivation.pdf`; the label
in brackets is stable across rebuilds. "Contract" is `theory/contract.yaml` version 2.

| # | Disposition | Where, or to whom, and the decision requested |
|---|---|---|
| Q1 | resolved | Uniform chemical potential is the consistent bookkeeping; Ca2+ binding enters only gamma_sl. Derivation Section 7 (all subsections), Eqs. (32) to (36) [th:eq:grand, th:eq:gibbs, th:eq:gibbs-sn, th:eq:young-ads, th:eq:composite]; contract `Delta_gamma_ads`, `cos_theta_template`, SF2, `no_double_counting`. The charter wording that follows from it is cp2 decision 2 in `theory/cp2_brief.md` |
| Q2 | resolved | A mean potential cancels in the ion product and in Delta_mu; carbonate needs no correction. Derivation 4 (ii), Eq. (15) [th:eq:dmu-uniform] |
| Q3 | deferred | Main study, Phase 7 item 6 (ionic-strength correction) and the C2 site model. In v2 the closure sets only the size of Delta_gamma_ads: d gamma_sl / d Delta_G_seq = Gamma_s Theta >= 0 for any isotherm with Theta >= 0, so its sign does not depend on the closure. P0 reports Langmuir as a stated closure |
| Q4 | deferred | P0-W1.2 (standard-state conversion of fetched binding constants with Eq. (6) [th:eq:stdstate] at one V_site, and the pKa row) and the main study (multidentate sites). V_site is fixed once by the parameter table |
| Q5 | deferred | Main study Phase 2 derivation freeze, as the charter states. P0 judges C1 per area (J m^-2) with one contact-area definition from the parameter table (`theory/thresholds.md`, C1) |
| Q6 | resolved | Registered: Delta_gamma_w = gamma_sn - gamma_sn0 > 0 is a cost on the substrate side, bare gamma_nl in Young. Derivation 6, Eqs. (28) to (31) [th:eq:young to th:eq:deck-sign]; contract SF1. Recording it in the charter is part of cp2 decision 2 |
| Q7 | deferred | Main study Phase 7 item 10 (geometric angle of an ACC nanodroplet in MD). P0 has no MD contact angle: Young decides C3, cos(theta) is clipped and the boundary mass reported (lane note N2, W4) |
| Q8 | ruled at cp2 (fix F6) | C5 R-slurry rule approved: regime activities at the bulk state, worst (pH, E_SHE) point, tolerance n_at e_f / n_M, ACC edge (n_at e_f + Delta_ACC)/n_M. Adding Delta_ACC makes the ACC test equal to the calcite-level test (stability of CaCO3 as a phase at the regime activities, up to the framing's metastability); the ACC-specific dissolution margin, Omega_bulk with the ACC K_sp, is a labelled sensitivity. The falsifiability test (item 21) stays with W5 |
| Q9 | ruled at cp2 (fix F5) | Sink rule of derivation 9, Eq. (46) [th:eq:sink] approved: anion of the registered salt, minimum over admissible sinks, undetermined never passes. A pass must hold under the lowest-onset CO2 reference scheme and a falsification under every registered scheme, otherwise inconclusive. A pass counts only with a solvated sink; a solid-salt limit is an upper bound on the onset, so its falsification stands and its pass is inconclusive. The electrolyte's own anodic limit is a stated limitation. `theory/thresholds.md`, C5 R-cell |
| Q10 | deferred | P0-W1.2 (parameter rows for the barrier height, effective mass and prefactor) and the main study (transport model). The bound enters only the C4 supporting condition |
| Q11 | resolved | F3: S = IAP/K_sp = Omega, Delta_mu = k_B T ln Omega per formula unit, V_m per formula unit. Derivation 4, Eq. (10) [th:eq:omega]; contract `conventions.supersaturation`. The per-ion form in this entry's text is the square root of Omega and carries no letter of its own (sign audit B3) |
| Q12 | deferred | P0-W1.2: K_sp, V_m and gamma_nl are taken from one framing (the framing key of the parameter table), enforced by the C3 rule of `theory/thresholds.md`; the framing was fixed at cp3 (R6): calcite and ACC are both registered, each run as a whole chain; falsified only under every framing, feasible under at least one (named), `theory/thresholds.md` Section 3 |
| Q13 | ruled at cp2 (fix F7) | IAP = a_Ca a_CO3 is kept. Bias direction stated: for a hydrated ACC framing, omitting a_w^n overstates Omega when a_w < 1, so drying states are optimistic. a_w is reported at each drying state, and where W1 has n the labelled sensitivity `Omega_bulk_hydrated` (contract) is reported. Derivation 4, Structural water; `theory/thresholds.md`, Section 1 |
| Q14 | ruled at cp2 (approved as proposed) | The square-lattice closure is the optimistic supporting condition of C4; the random-site uncovered fraction is deferred to the main study. `theory/thresholds.md`, Section 1, Registered conventions |
| Q15 | deferred | Main study; stated limitation "layer persistence" (charter/scope_guard.md). The P0 screen judges wetting in water only |
| Q16 | resolved | Absolute-barrier criterion DG_het <= B_acc = k_B T ln(J_0 t_p / N_req), derivation 5, Eqs. (25) and (26) [th:eq:rate, th:eq:access]; contract `B_acc`, `N_nuc`; thresholds C3 |

Counts after the cp2 ruling: resolved 5 (Q1, Q2, Q6, Q11, Q16); ruled at cp2 4 (Q8, Q9, Q13, Q14); deferred 7 (Q3, Q4, Q5, Q7, Q10, Q12, Q15). Before it: for
cp2 4 (Q8, Q9, Q13, Q14).

## Q1 (A). Enrichment bookkeeping: local-ideal (registered) or grand-canonical

- **Choice.** Bookkeeping B: the binding free energy is carried by `Delta_G_seq` and enters the
  driving force through `Omega_local = (c_local/c_bulk) Omega_bulk`. `gamma_sl` and `gamma_sn`
  are those of the template without the Ca2+ excess.
- **Alternative.** Bookkeeping A: uniform chemical potentials, `Delta_mu = Delta_mu_bulk`, with
  Ca2+ adsorption inside grand-canonical interfacial energies through the Gibbs adsorption
  equation.
- **Consequence.** Under B, `Delta_G_seq < 0` always lowers the barrier. Under A, adsorption that
  stabilises only the template–water interface lowers `gamma_sl`, which lowers `cos(theta)` and
  *raises* the barrier. The barrier falls only if the substrate–nucleus interface gains more from
  the bound ions than the substrate–liquid interface does. B can therefore favour the mechanism
  where A does not. P0-W3.2 must show the two agree for the barrier, or bound their difference,
  before any C3 output is read. Mixing A's Ca-loaded `gamma_sl` with B's `Omega_local` is the
  double count that C3 item 13 demonstrates.

## Q2 (A). Carbonate held at its bulk activity

- **Choice.** Only Ca2+ is enriched; `a_CO3` keeps its bulk value in `Omega_local`.
- **Alternative.** Treat carbonate in the same template field: a Boltzmann factor for CO3^2- from
  its own PMF, or an electroneutral (Donnan) layer.
- **Consequence.** An anionic template that attracts Ca2+ repels CO3^2-, so the choice is an
  upper estimate of `Omega_local` that is biased toward feasibility. In the limiting case where
  the enrichment is purely electrostatic (a mean potential acting on charges +2 and -2), the
  Ca2+ factor and the CO3^2- factor are reciprocal. Their product is then one, and
  `Omega_local = Omega_bulk`: there is no supersaturation gain at all. Only specific,
  non-electrostatic binding raises the ion product. The C2 computation must separate the two
  contributions, or C3 must carry the carbonate PMF.

## Q3 (B). Activity coefficients and the Langmuir closure

- **Choice.** Local and bulk activity coefficients are equal. Sites are independent and
  equivalent, with one ion per site (Langmuir).
- **Alternative.** A local ionic-strength activity model in the layer, plus electrostatic
  coupling between charged sites (a mean-field or Frumkin closure).
- **Consequence.** Equal coefficients make `E_enr` both a concentration ratio and an activity
  ratio. Coupled sites saturate earlier than Langmuir predicts, which lowers `c_local` at a given
  `Delta_G_seq`. The saturation bound `c_local <= c_max` holds either way.

## Q4 (B). Site volume, standard state and protonation stoichiometry

- **Choice.** `V_site` is the binding-layer volume per site, and `Delta_G_site` uses the
  site-volume standard state. One coordinating group with one proton gives the correction
  `R T ln(1 + 10^(pKa - pH))`.
- **Alternative.** A different `V_site`, a multidentate site releasing n protons with several pKa
  values, or a 1-mol-per-volume standard state.
- **Consequence.** `V_site` shifts `Delta_G_site` by `R T ln(V'/V)`. A literature binding constant
  is comparable only after the standard-state correction of the derivation (Section 3), and only
  at the same `V_site`. A multidentate site multiplies or reshapes the protonation correction,
  which moves the pH at which catechol stops binding (design flag 4).

## Q5 (B). Contact-area normalisation of the PMF

- **Choice.** `W_adh_wet = Delta_F_pmf / A_c`, with one definition of `A_c` for all fragments.
- **Alternative.** Report per fragment (kJ/mol) without an area, or use a solvent-accessible
  contact area.
- **Consequence.** The sign of `W_adh_wet` does not change, but the ranking across binders and
  controls can, and with it the C1 margin. The charter defers this to the Phase 2 freeze.

## Q6 (A). Placement and sign of the water-displacement term

- **Choice.** `Delta_gamma_w = gamma_sn - gamma_sn0`, with **positive meaning a cost**, placed on the
  substrate side of Young. The denominator is the bare `gamma_nl`. The term is zero when `gamma_sn`
  is computed directly in water.
- **Alternative.** The deck's `gamma_eff = gamma_nl - Delta_gamma_w` in the denominator of Young.
  Alternatively, keep the deck's subtraction but reverse the sign convention of `Delta_gamma_w`.
- **Consequence.** Under the deck form, on the wetting side (`gamma_sl > gamma_sn0`), a cost lowers
  the barrier: sign-flip test SF1 reverses. It also breaks `DG_het = f DG_hom`, because the cap's
  surface term no longer factorises. Reversing only the sign convention gives the right direction
  but still modifies `gamma_nl`, which the displaced water never touches. The registered form
  also enters `S_spread` with the same sign. Preferred practice is to compute `gamma_sn` directly
  in water, so that `Delta_gamma_w = 0` and no correction is applied.

## Q7 (B). Young beyond its range, and the computed contact angle

- **Choice.** `cos(theta)` is clipped to [-1, 1]. If `cos >= 1`, then `f = 0` (spreading). If
  `cos <= -1`, then `f = 1`. The branch is reported.
- **Alternative.** Take the contact angle from the geometry of an ACC nanodroplet in MD, the C3
  cross-check.
- **Consequence.** At nanometre scale, the geometric angle includes line tension and curvature
  effects that the Young angle omits. The two estimates may disagree beyond their uncertainty,
  and the registration must say which one decides C3 and how a disagreement is reported.

## Q8 (A). Aqueous Pourbaix references and the ACC offset

- **Choice.** `Psi_pbx` per non-O, non-H atom, with dissolved-ion activities as inputs and the ACC
  phase placed by a fetched offset above calcite.
- **Alternative.** Report `Delta_G_pbx` as a function of the dissolved-ion activity. Separately,
  frame the screen on calcite.
- **Consequence.** The dissolved-ion activity reference decides whether solids appear stable at
  all, so the screen can be passed by construction (C5 item 21). ACC is never on the hull: its
  distance above the hull is at least its offset, so the tolerance registered at G2 decides C5
  for the ACC framing.

## Q9 (A). Li-open window for a Li-free phase

- **Choice.** For R-cell, use the Li-open grand potential `Phi = G - n_Li mu_Li`, with
  `mu_Li = mu_Li0 - F E_Li` and limits `E* = Delta_G_r / (Delta_n F)`.
- **Alternative.** Add open components for the anodic side, such as O2 or CO2, the electrolyte
  anion, or dissolved Ca2+ and Al3+. Alternatively, compute oxidation reactions against the
  electrolyte directly.
- **Consequence.** CaCO3 holds no Li, so no reaction has `Delta_n > 0`, and its Li-open `E_ox` is
  unbounded. The construction then declares CaCO3 anodically stable by construction, which is
  exactly the failure C5 item 21 guards against. Without the alternative, the R-cell anodic
  stability of CaCO3 and the Al phases cannot be tested; only lithiation (reduction) limits are
  meaningful.

## Q10 (B). Tunnelling parameters of the film bound

- **Choice.** WKB through a rectangular barrier: `kappa = sqrt(2 m_e phi_B)/hbar` with the free
  electron mass, the prefactor `j_0` as an input, and `d_max = max(d_ohm, d_tun)`.
- **Alternative.** An effective tunnelling mass, a Simmons-type prefactor with image-force
  lowering, or trap-assisted and hopping transport.
- **Consequence.** `d_max_tun` scales as `1/sqrt(m phi_B)` and only logarithmically with
  `j_0 / j_req`. The effective mass and the barrier height dominate the uncertainty. Defects can
  only raise the current, so the bound is conservative for a defect-free film.

## Q11 (C). One supersaturation variable

- **Choice.** `Omega = IAP/K_sp` with `Delta_mu = k_B T ln(Omega)`.
- **Alternative.** The per-ion form `S = Omega^(1/2)` with `Delta_mu = 2 k_B T ln(S)`.
- **Consequence.** The two are the same physics. If they are mixed, `Delta_mu` is off by a factor
  of two and the barrier by a factor of four. The charter's `S` for C3 is read as `Omega`; the
  integrator should confirm that W2 and W4 use the same reading.

## Q12 (B). Framing consistency of K_sp, V_m and gamma_nl

- **Choice.** `K_sp`, `V_m` and `gamma_nl` all belong to the single framing registered at G2 (ACC
  or calcite). `gamma_nl` is isotropic.
- **Alternative.** Mixed sources, for example an ACC solubility with a calcite interfacial
  energy, or an anisotropic, facet-averaged `gamma_nl` for calcite.
- **Consequence.** Mixing framings produces a barrier that belongs to no phase. For calcite, an
  isotropic `gamma_nl` misstates both the cap shape and the barrier. This is a limitation of
  Eq. (21) [th:eq:dg-cap] of the derivation for faceted nuclei.

## Q13 (B). Structural water in the ion activity product of ACC

- **Choice.** `IAP = a_Ca a_CO3`, with `V_m` per CaCO3 formula unit.
- **Alternative.** For a hydrated framing CaCO3·nH2O, use `IAP = a_Ca a_CO3 a_w^n`, with `V_m` per
  hydrated formula unit.
- **Consequence.** In the slurry the two agree, because `a_w = 1`. During drying, `a_w` falls (it
  is an R-slurry input in `charter/regimes.yaml`), and the hydrated form lowers `Omega`. Adding
  `a_w` and `n` to the contract is a contract change and needs a cp2 decision.

## Q14 (B). Lattice versus random nucleation sites in the closure estimate

- **Choice.** Equal caps on a square lattice. `h_c` is the height at first contact and
  `h_cl = sqrt(2) h_c` the height at closure.
- **Alternative.** Random (Poisson) nucleation sites, with coverage `1 - exp(-N_s pi rho^2)` in
  the Avrami-type picture.
- **Consequence.** With random sites, geometric coverage approaches one only asymptotically. Full
  closure then has no finite thickness, and C4 needs a registered uncovered-fraction tolerance in
  place of exact closure. The lattice estimate is the optimistic bound.

## Q15 (C). Conformality judged in water, not after drying

- **Choice.** `S_spread` and `theta` use solid–water energies (R-slurry).
- **Alternative.** Re-evaluate wetting against air or the dried binder after drying.
- **Consequence.** A film that closes in the slurry can crack or dewet when a hydrated amorphous
  layer shrinks. The screen is silent on this, and it is reported as a limitation.

## Q16 (C). Barrier accessibility without a kinetic prefactor

- **Choice.** C3 reports the absolute barrier in units of `k_B T`. Accessibility is a registered
  bound on `DG_het / k_B T`.
- **Alternative.** A rate `J = J_0 exp(-DG_het / k_B T)` with a fetched or computed prefactor.
- **Consequence.** Without `J_0`, a bound in `k_B T` implies an order-of-magnitude rate statement
  at best. The scope guard forbids rate claims about corrosion, but a nucleation-rate statement
  would still need a prefactor source. The registration should say which form the bound takes.
