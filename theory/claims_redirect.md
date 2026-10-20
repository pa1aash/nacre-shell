# Claims of the redirected screen: K1 to K4, the K1 rule, the Al-salt ladder (PH-W3.1)

Session PH-W3.1, lane p0-w3, written before any phosphate output exists. Authority: `ops/tracks/redirect_plan.md`
(D34 to D40). Everything is symbolic: no literature number appears here, and every value is named by the
`lit/params.yaml` key that will supply it (Section 7). Symbols of the contract keep their ids
(`theory/symbols.yaml`); symbols new to this file are defined where they first appear. The shared decision rule is
the one of `theory/thresholds.md` (Section 1): a test is **feasible** if P_good >= p_cred, **falsified** if
P_bad >= p_cred, **inconclusive** otherwise, evaluated draw by draw on the same draws.

## 0. Conventions

- **Cutoff.** E_c is the charge cutoff (V vs Li+/Li), a design axis. A cutoff class is a set of cutoffs:
  C_lo (LFP-class), C_mid, C_hi, registered under `regimes.R-cell.parameters.cutoff_classes`. All K1 statements are
  made per E_c and then per class (Section 2e).
- **Candidate.** A candidate phase P (panel of the plan) with a registered framing set F(P): `apatite` (crystalline,
  K_sp, V_m, gamma_nl of the crystalline phase) and `ACP` (K_sp, V_m, n_hyd, gamma_nl of the amorphous phase). A
  framing is never mixed across links (one K_sp, V_m, gamma_nl per run).
- **Stoichiometry.** A mineral has nu ions per formula unit, nu = nu_Ca + nu_X + nu_Y (contract v5). Omega is
  IAP/K_sp of the formula unit with the exponents nu_i and a_w^n for structural water; the driving force is
  k_B T ln Omega per formula unit. The per-ion form never enters a barrier.
- **Gate or descriptor.** K1 to K4 are gates. Adhesion (W_adh_wet) and Ca binding (Delta_G_seq, Theta_occ) are
  descriptors: reported, never decisive.

## 1. The register

| Id | Observable | Regime | Symbolic threshold | Decision rule | Role |
|---|---|---|---|---|---|
| K1 | E_ox(P) = min over registered oxidation reactions r of E_r (tier 1); E_svc (tier 2, class A, B or C) | R-cell, cutoff E_c | tier 1: E_ox >= E_c + m_1 (pass), E_ox < E_c - m_1 (below), m_1 in {m_expt, m_E}; tier 2: E_svc >= E_c + m_svc | two-tier table (Section 2c), per E_c, then per class | gate |
| K2 | Omega_bulk(P) in the Omega of contract v5, from sourced K_sp and speciation | R-slurry, pH range, dose axes | Omega_bulk >= 1 | worst registered state; shared rule on P(Omega_bulk >= 1) | gate |
| K3 | window W_3(P) along the dose axis D | R-slurry | DG_het(D) <= B_acc and DG_hom(D) > B_acc, with C3a: f <= 1/2 edge | exists a dose with P_good >= p_cred (feasible); every dose with P_bad >= p_cred (falsified) | gate (deletion test) |
| K4 | S_spread, and N_nuc against N_s_closure | R-slurry (wetting), R-cell (thickness) | S_spread >= m_S OR N_nuc >= N_s_closure(theta, d_max) | feasible if P(either) >= p_cred; falsified only if P(both fail) >= p_cred | gate (deletion test) |

K3 and K4 run for every phase whose K1 verdict is not falsified at EVERY registered cutoff class (Section 2d, cp4 F1).
A phase is falsified only
if falsified under every registered framing; feasible under at least one framing, which is named, with the other
reported beside it; inconclusive otherwise. The study table has one row per phase, columns K1 per class, K2, K3,
K4, and the carbonate row is the control run through the same pipeline.

## 2. K1, the two-tier oxidation rule

### 2a. Registered oxidation reactions

For each phase P a list R(P) of oxidation reactions, each written with n_e electrons removed and the electrons
balanced by n_e Li formed at the counter electrode (the Li-open reading of contract `Delta_Phi_r`, `E_window`):

| r | Reaction class | Activity dependence | Sink |
|---|---|---|---|
| r1 | lattice oxygen release, O(2-) in the lattice to 1/2 O2(g) | none beyond the sink | solvated cations |
| r2 | structural OH oxidation, 2 OH(-) to H2O + 1/2 O2 + 2 e | a_w^{nu_w} a_OH^{nu_OH} | solvated |
| r3 | water oxidation in hydrates, n H2O to 2n H+ + n/2 O2 + 2n e | a_w^n; H+ taken up by the solvated sink | solvated |
| r4 | Al-phase reactions: Al, Al2O3, AlPO4, Al(PO3)3, Al-borate, Al-oxalate to solvated Al(3+) (and the anion) | a_Al | solvated |

Onset of reaction r, with Q_r the reaction quotient of the non-electron species:

E_r(a_w, a_OH) = [ Delta_G_r0 + R T ln Q_r ] / (n_e F),  Q_r = prod_j a_j^{nu_j},

so a_w and a_OH are design axes (reported as a curve or map E_r(a_w, a_OH), never a single number). The phase onset
is E_ox(P) = min over r in R(P) of E_r (the E_window rule: minimum over reactions with positive Delta_n_Li).
Dehydration is not an oxidation: the a_w at which a hydrate loses its water is reported as a threshold a_w*(P) beside
the table, with the K1 row evaluated on both sides of it.

**Routes and benchmark status.** The experimental route (tabulated formation data, fetched with DOI and locator)
governs wherever its inputs exist. DFT (database) is a comparator only, printed with its measured benchmark error
(`thresholds.C5.formation_energy_error`); a benchmark-corrected DFT value equals the experimental route by
construction and is never a second confirmation. Phosphate DFT numbers are unbenchmarked until the phosphate
benchmark on tabulated formation data passes (W5): until then they are labelled `unbenchmarked` and cannot pass or
falsify. Every number in the per-reaction table carries one of `expt`, `dft-benchmarked`, `dft-unbenchmarked`.

**Solvated sink.** A pass needs the oxidation products to leave into the electrolyte as solvated species
(solvation free energies from `params`, one scheme per row). A solid-salt sink gives an upper bound on the onset:
a falsification stands, a pass is inconclusive.

**Margins.** m_1 = m_expt (`thresholds.C5.window_margin_expt`, one budget per reaction and sink) on the
experimental route; m_E (`thresholds.C5.window_margin`) only where the experimental route is missing and the row is
labelled DFT-decided. A missing margin key makes the reaction **undetermined**.

**Undetermined never passes.** Any reaction with a missing input, an unbenchmarked number, an absent margin, or an
unregistered sink is `undetermined` and E_ox(P) is then undetermined unless the determined reactions already fall
below E_c - m_1 (a lower bound from a subset of reactions is enough to falsify tier 1, because E_ox is a minimum).

### 2b. Tier 2: measured service limit

A record has an evidence class: **A** potential hold or LSV on a coated Al collector; **B** coating on a cathode
particle cycled to a stated charge cutoff in carbonate electrolyte (indirect); **C** LSV of the bulk phase. It logs
the electrolyte (salt set, with a flag F_el if it contains fluoride), temperature T_svc, cutoff or hold potential,
duration t_svc, and the current-density criterion j_svc used to call the limit. E_svc is the highest potential at
which the record shows service (current at or below j_svc for at least t_svc,min at T_svc >= T_cell). Tier 2 passes
at E_c when E_svc >= E_c + m_svc (`thresholds.K1.margin_service`, the potential-reading uncertainty of the record);
it is below when E_svc < E_c - m_svc. A record logged with F_el is kept and labelled; it is not silently
transferred to the fluorine-free regime.

### 2c. Verdict table (per phase, per E_c)

T1 = tier 1 (E_ox against E_c, margin m_1), T2 = the best available tier 2 record at E_c (class A or B outranks C).

| # | Tier 1 | Tier 2 | K1 verdict at E_c | Label | Symbolic example |
|---|---|---|---|---|---|
| 1 | pass: E_ox >= E_c + m_1, benchmarked route, solvated sink | any or none | feasible | `tier 1`; if T2 is below, `service limit below cutoff, class X` printed beside | E_ox = E_c + 2 m_1 |
| 2 | below: E_ox < E_c - m_1 | available and below: E_svc < E_c - m_svc | **falsified at E_c** | `tier 1 and tier 2 (class X)` | E_ox = E_c - 2 m_1, E_svc = E_c - 2 m_svc |
| 3 | below | none | falsified at E_c | `tier 1 only` (no tier 2 exists) | E_ox = E_c - 2 m_1 |
| 4 | below | class A or B, E_svc >= E_c + m_svc | **not excluded, kinetically stabilised** | label carries the class (A or B) | E_ox = E_c - 2 m_1, E_svc = E_c + 2 m_svc |
| 5 | below | class C only, E_svc >= E_c + m_svc | inconclusive | `bulk-phase LSV only; not evidence for a film` | as row 4 with class C |
| 6 | within margin: E_c - m_1 <= E_ox < E_c + m_1 | any | inconclusive | tier 2 printed beside | E_ox = E_c |
| 7 | undetermined (Section 2a) | any | inconclusive | `undetermined never passes`; tier 2 printed beside | E_r unsourced |

Rule behind the table: falsified at E_c only if tier 1 and the available tier 2 both fall below it; tier 1 only if
no tier 2 exists. Rows 5 to 7 and the tier-2-below note of row 1 are the places where the plan is silent: they are
registered here conservatively (interpretations I1 to I3, Section 8).

**Carbonate.** CaCO3 runs through the same table (reaction r1 with the exchange route registered in C5c_ox; its
tier 2 records are looked up like any other). Its row is the negative control for K1; it is expected to remain
falsified at the classes where its experimental onset is below E_c, because a measured service limit near its
thermodynamic onset puts it in row 2. K1 is evaluated for carbonate only through the table; no carbonate result is
recomputed here.

### 2d. Which phases proceed (cp4 F1)

A phase proceeds to K3 and K4 unless its K1 verdict is falsified at EVERY registered cutoff class. A phase that is
inconclusive or undetermined at any class proceeds, and its K1 status is shown in its row.

Equivalently: K3 and K4 are skipped only for a phase whose class verdict (Section 2e) is `falsified for the class`
for C_lo, C_mid and C_hi alike; its row then says so. A phase that is feasible or not excluded (kinetically
stabilised, class A or B) at some class proceeds with that class named; a phase that is only inconclusive,
undetermined or partial proceeds with its per-class K1 status printed in its row beside K2 to K4. The reason (cp4
ruling): while the solvated sink is a gap no phase can pass K1, and the earlier rule (proceed only on a pass) would
have run nothing. K2 is evaluated for every phase (it is a property of the slurry) and gates the study row, not the
decision to run K3. Proceeding is not passing: the K1 column keeps its verdict, and a row with K1 inconclusive is
never reported as a candidate barrier.

### 2e. Cutoff classes

The pass set is a down-set in E_c: a pass at E_c is a pass at every lower cutoff; a falsification at E_c is a
falsification at every higher cutoff. A class verdict is therefore: **feasible for the class** if feasible at
sup C; **falsified for the class** if falsified at inf C; otherwise **partial**, with the two crossovers reported:
E_x+ = E_ox - m_1 (feasible at or below) and E_x- = E_ox + m_1 (falsified above), for tier 1; the tier 2 crossovers
E_svc - m_svc and E_svc + m_svc likewise. Outcome frames (A), (B), (C) of the plan are read off these class rows.

## 3. K2, K3, K4

### 3a. K2

Omega_bulk >= 1 with a_i from the phosphate speciation (contract v5) at every registered state of the slurry; a pass
needs every state, a falsification at an evaluated state stands (worst-state rule of the carbonate link). The
dose window of K2 is the set of (Ca_T, P_T) where Omega_bulk >= 1. Control: an undersaturated registered state must
report dissolution and a supersaturated one stability, else K2 is inconclusive. The acid-adjusted pH state (Section 6)
is evaluated as a comparator row, not as a regime of the barrier.

### 3b. K3, the accessible window

Let D be the dose axis (ln of the total dose at fixed ratio, so that ln Omega is monotone in D at fixed pH). With
f = f_theta(cos theta) from the template (C3a) and the same absolute criterion for both barriers:

- heterogeneous meets the criterion: DG_het(D) = f DG_hom(D) <= B_acc, B_acc = k_B T ln(J0_het t_proc / N_req),
  N_req = ln(1/(1 - p_cred))/A_patch;
- homogeneous does not: DG_hom(D) > B_acc.

W_3 = { D : f DG_hom(D) <= B_acc < DG_hom(D) }. Because DG_hom is proportional to (ln Omega)^-2, define L_hom by
DG_hom(L_hom) = B_acc; then W_3 is the interval ln Omega in [ sqrt(f) L_hom, L_hom ), non-empty iff f < 1 and bounded
below by the K2 edge ln Omega >= 0. The window closes where bulk precipitation takes over (DG_hom <= B_acc); that
upper edge is **stated** with every K3 row, together with the saturation of each competing phase pi (Li3PO4, AlPO4,
other calcium phosphates): Omega_pi(D) >= 1 at a dose in W_3 is reported as a competing phase and, where its own
barrier meets B_acc first, closes the window from above. The favourable template condition is gamma_sn <= gamma_sl
- m_cos gamma_nl (Section 5). K3 feasible: exists D in the registered dose range (and inside K2) with P_good(D) >=
p_cred; falsified: P_bad(D) >= p_cred at every D; the set of feasible doses is the reported window, with the falsified
and inconclusive sets. Prior masses are never findings (ignorance-prior rule, Section 5).

### 3c. K4

K4 holds if S_spread >= m_S OR closure is credible, closure being N_nuc >= N_s_closure(theta, d_max) with
d_max = max(d_max_ohm, d_max_tun) (the insulating-thickness bound) and N_nuc the path-sum estimate of C3b.
Falsified only if both fail on the same draw with joint mass P(S_spread < m_S and N_nuc < N_s_closure) >= p_cred.
Complete wetting is excluded when gamma_sl <= gamma_nl for every admissible gamma_sn; the closure route is
optimistic and carries that label.

### 3d. Framings and the deletion test

ACP and apatite are both registered as nucleus framings; the whole chain runs per framing. A phase is falsified only
if falsified under every framing; if it passes under one, that framing is named and the other is reported beside it.
The **deletion test** applies to K3 and K4 only (K1 and K2 do not depend on the template): remove the template
(bare oxide, PVDF controls) and require that the K3 or K4 joint verdict degrade (strictly worse, or falsified-side mass
up by at least p_deg). A pass that does not degrade is labelled `generic`, not template-specific.

## 4. The Al-salt film ladder

Film candidates: AlPO4, Al(PO3)3, Al-borate, Al-oxalate, Al2O3, and the bare-Al onset as the reference rung. Cut order
keeps AlPO4, Al(PO3)3 and Al2O3. A film F passes the ladder iff all three hold at the cutoff E_c:

- **(a) Oxidation limit.** The K1 table of Section 2c for F at E_c is feasible or not excluded (kinetically
  stabilised, class A or B); tier 1 and tier 2 both printed. Undetermined never passes.
- **(b) Insolubility in the electrolyte.** With K_sp,el(F) the solubility product of F in the registered electrolyte
  (solvent and salt set; `params`), the equilibrium dissolved level of the film cation at the registered anion
  activity is s_sat = (K_sp,el / prod_other a_i^nu_i)^(1/nu_Al). Pass iff s_sat <= s_tol (the loss budget that keeps
  the film through t_life: s_tol = d_film rho_film A_el /(M_film V_el)-type, defined by the registered geometry) or,
  at the pit solution, Omega_el = IAP_pit/K_sp,el >= 1. K_sp,el unsourced in that electrolyte: **undetermined**
  (never passes).
- **(c) Ionic blocking.** With sigma_corr the partial ionic conductivity of the corrosion-carrying ions (Al
  cation out, anion or solvent-derived oxidant in), DV_film the potential drop across the film at the cutoff and
  j_corr,max the tolerated corrosion current density, ionic blocking requires j_ion = sigma_corr DV_film / d_film
  <= j_corr,max, that is d_film >= d_block = sigma_corr DV_film / j_corr,max, and the transference condition
  t_corr = sigma_corr / (sigma_corr + sigma_Li + sigma_e) <= t_max for the film to be a barrier and not a
  conductor of the corrosion ions. Together with the insulating bound of K4, d_block <= d_film <= d_max defines the
  admissible thickness interval; an empty interval fails (c).

Ladder output: for each rung the triple (a), (b), (c) with its label (pass, fail, undetermined), ranked by the
oxidation limit; the bare-Al onset is the reference rung against which the other rungs are read.

**Design rule.** A barrier need not be thermodynamically stable against oxidation if the corrosion product forms an
insoluble, oxidation-stable film: the ladder tests exactly the film properties (a), (b), (c). Fluoride protection
works through AlF3 in this way; the fluorine-free analogue is an Al-phosphate or Al-borate film. Two parts are
labelled apart: **film properties are screened here**; the **supply of phosphate at a pit** (from an additive,
co-solvent, or a binder or film reservoir) is a hypothesis outside the screen, and no screen result depends on it.
Nothing is claimed to self-heal: the word appears only as a design hypothesis or criterion.

## 5. Phosphate thresholds and ignorance priors (symbolic)

The carbonate structure is reused unchanged; only the mineral enters through the generalised Omega, V_m, gamma_nl.

- **C3a.** f_theta <= 1/2 edge, that is cos theta >= m_cos (m_cos symbolic, primary and sweep from
  `thresholds.C3.margin_cos_theta`); single edge, no upper edge. Favourable template condition: gamma_sn <= gamma_sl -
  m_cos gamma_nl with gamma_sn >= 0, gamma_sl >= 0, and gamma_sn <= gamma_sl being the f <= 1/2 edge at m_cos = 0.
- **Admissibility.** gamma_sl = gamma_sl0 + Delta_gamma_ads >= 0 at every registered state and design point; draws
  outside are refused and counted, never clipped or floored; M_adm (the retained fraction of the joint prior over
  gamma_sl0, Delta_G_seq, Gamma_s, delta_s) is printed beside every verdict that uses gamma_sl (K3, K4, the deletion
  test); 1 - M_adm >= p_cred gives `inconclusive, inadmissible inputs`; the unrestricted run is a labelled
  sensitivity. Phosphate templates use the same priors with the phosphate framing's gamma_nl, gamma_nv.
- **Decision constants.** p_cred (primary and sweep from `thresholds.decision.credible_level`), p_deg = 1 - p_cred
  (`thresholds.decision.degrade_mass_min`); m_cos, m_S, m_W, m_seq, m_E, m_expt, m_svc symbolic here; PH-W3.2 sets
  numbers from the W5 benchmark and the W1 method-error rows. No margin takes a value in this file.
- **gamma_sn prior.** gamma_sn ~ U[0, gamma_p + gamma_nv(P, framing)] on the total in-water contact energy with
  Delta_gamma_w = 0; gamma_nv per phase and framing is a new key. gamma_nl, V_m, K_sp, n_hyd are per phase and per
  framing. A_patch bounds, J0_het, t_proc as for carbonate.
- **Sizing rule.** Band-mass half-width (2 x Monte Carlo standard error) at most the registered width, Sobol total-order
  half-width at most the registered width, draw cap and wall-clock cap, chunked streaming, capped runs reported with the
  half-widths reached (`thresholds.decision`, unchanged from the carbonate link).
- **Reporting.** Prior masses and band masses under an ignorance prior are never findings: the output is the flip
  value and the required-precision map (the precision of gamma_sl0, gamma_sn, K_sp, V_m that flips each verdict).
- **K2 in the new Omega.** K2: Omega_bulk,P >= 1 with Omega_bulk,P = prod_i a_i^nu_i a_w^n / K_sp,P (contract v5).
- **Acid-adjusted pH state (comparator).** The state in the Al passivation window (derived from the Al-O-H
  Pourbaix on benchmarked ion data, cross-checked against the published window; both reported) is a comparator to the
  incumbent phosphoric-acid pH control, not a regime of the barrier. At that state K2 is evaluated as a comparator
  row and no K3 or K4 verdict is drawn from it.

## 6. What this file does not decide

Numeric margins, priors' parameter values and the sweep grids (PH-W3.2); the benchmark status of phosphate
thermochemistry (W5); which tier 2 records exist (W2); the code (W4). A statement of the form "phosphate X passes" is
not made anywhere in this file.

## 7. New `lit/params.yaml` keys (names; values come from W1, fetched with DOI and locator)

Per phase P in {hap, acp, ocp, btcp, capp, cameta} (apatite and ACP framings registered separately where both exist):
`log10_ksp_<P>`, `v_m_<P>`, `gamma_nl_<P>`, `gamma_nv_<P>`, `nu_ca_<P>`, `nu_x_<P>`, `nu_y_<P>`, `acp_hydration_n` (n for
hydrated forms, `n_hyd_<P>`). Speciation: `pka1_h3po4`, `pka2_h3po4`, `pka3_h3po4`, `log10_k_cahpo4_aq`,
`log10_k_cah2po4`, `log10_k_capo4`, `pkw`, `p_total_slurry` (design axis P_T), `ph_slurry_acid_adjusted`,
`al_passivation_window`. K1: `regimes.R-cell.parameters.cutoff_classes`, `thresholds.K1.margin_service`,
`regimes.R-cell.parameters.t_svc_min`, `j_svc`, `dfg_<species>` for every species of the registered reactions r1 to r4,
`dfh_<species>` and `s_<species>` where tabulated, `solvation_<ion>` per scheme, `a_oh_range`, `a_w_cell` (water
activity of the electrolyte, `electrolyte_water_content`), tier 2 records as evidence rows with class A, B or C, electrolyte,
temperature, cutoff and duration. Al-salt ladder: `log10_ksp_el_<F>` (F in alpo4, al_pmeta3, al_borate, al_oxalate,
al2o3 as hydroxide or oxide form), `sigma_corr_<F>`, `dv_film`, `j_corr_max`, `t_max_corr`, `s_tol`, `rho_film_<F>`.

## 8. Interpretations for the cp4 audit

- **I1.** Row 5 of the K1 table (tier 1 below, tier 2 class C only above): inconclusive, because a bulk-phase LSV is not
  evidence for a film in service. The plan names only classes A and B for "kinetically stabilised".
- **I2.** Row 1 note: tier 1 pass with a tier 2 record below is feasible with the contradiction printed; the plan
  falsifies only when both fall below. A tier 2 record of class A below the cutoff is flagged for the audit.
- **I3.** Rows 6 and 7: within the margin band, or undetermined tier 1, is inconclusive even where tier 2 is above or
  below; the plan's falsification needs tier 1 below.
- **I4.** Superseded by cp4 F1 (Section 2d): the test is no longer "passes at any class" but "not falsified at every
  class"; the not-excluded, kinetically stabilised verdict (class A or B) is one of the statuses that proceed.
- **I5.** Tier 2 records logged with a fluoride-containing electrolyte are kept, labelled F_el, and not excluded; the
  plan asks only that the electrolyte be logged.
- **I6.** The bulk-precipitation competition in K3 uses the same absolute criterion B_acc for the homogeneous
  barrier (as stated in the brief); a separate bulk prefactor and volume is deferred to PH-W3.2 as a labelled sensitivity.
- **I7.** Ionic blocking (c) is stated with the ohmic partial-conductivity form and the transference condition;
  a high-field form is a refinement for W3.2 if sigma_corr is only available as a field-dependent law.
