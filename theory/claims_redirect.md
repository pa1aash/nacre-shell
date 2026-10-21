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

**Solvated sink and the bracket (cp4 F2).** Tier 1 is a bracket [E_lb, E_ub] per reaction (Section 2f): E_ub is the
onset with the solid-salt (LiClO4) sink, an upper bound on the onset (a falsification on it stands); E_lb is the onset
with the most favourable sink, every ion aqueous from tabulated standard data, a lower bound under the transfer premise
of Section 2f. A pass needs E_lb; a falsification needs E_ub. One scheme per row.

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

T1 = tier 1 (the bracket [E_lb, E_ub] of Section 2f against E_c, margin m_1; "below" means E_ub below), T2 = the best available tier 2 record at E_c (class A or B outranks C).

| # | Tier 1 | Tier 2 | K1 verdict at E_c | Label | Symbolic example |
|---|---|---|---|---|---|
| 1 | pass: E_lb >= E_c + m_1 (Section 2f), benchmarked route, transfer premise supported | any or none | feasible | `tier 1`; if T2 is below, `service limit below cutoff, class X` printed beside | E_ox = E_c + 2 m_1 |
| 2 | below: E_ub < E_c - m_1 (Section 2f) | available and below: E_svc < E_c - m_svc | **falsified at E_c** | `tier 1 and tier 2 (class X)` | E_ox = E_c - 2 m_1, E_svc = E_c - 2 m_svc |
| 3 | below | none | falsified at E_c | `tier 1 only` (no tier 2 exists) | E_ox = E_c - 2 m_1 |
| 4 | below | class A or B, E_svc >= E_c + m_svc | **not excluded, kinetically stabilised** | label carries the class (A or B) | E_ox = E_c - 2 m_1, E_svc = E_c + 2 m_svc |
| 5 | below | class C only, E_svc >= E_c + m_svc | inconclusive | `bulk-phase LSV only; not evidence for a film` | as row 4 with class C |
| 6 | within the bracket: neither E_lb >= E_c + m_1 nor E_ub < E_c - m_1 | any | inconclusive | tier 2 printed beside; E_lb, E_ub printed | E_lb < E_c < E_ub |
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
E_x+ = E_lb - m_1 (feasible at or below) and E_x- = E_ub + m_1 (falsified above), for tier 1 (Section 2f); the tier 2 crossovers
E_svc - m_svc and E_svc + m_svc likewise. Outcome frames (A), (B), (C) of the plan are read off these class rows.

### 2f. The bracketed onset (cp4 F2) and its vetting

**Rule.** For each registered reaction r of a phase P, two onsets are computed with the same reaction, the same
reactant phase and the same Li count Delta_n_Li (contract v6, functions `E_ub`, `E_lb`):

- **E_ub**, the onset with the solid-salt sink: the oxidised cation leaves as its solid perchlorate and the Li comes
  from solid LiClO4 (the registered exchange route of the carbonate control, sink `LiClO4`). Inputs: `dfg_<P>`,
  `dfh_` and `s_` of the solid salts (`dfh_ca_clo4_2`, `s_ca_clo4_2` or its analog bounds, `dfg_al_clo4_3`,
  `dfh_liclo4`, `s_liclo4`).
- **E_lb**, the onset with the most favourable sink: every ionic product and the Li+ that is consumed are taken as
  aqueous ions at their standard states, from tabulated standard formation data (`dfg_ca2_aq`, `dfg_al3_aq`,
  `dfg_li_aq`, and for a reaction that releases protons the proton convention of the same table). The cations Ca2+
  and Al3+ and the anion enter from the same table; the absolute single-ion hydration energies
  (`hydration_free_energy_ca`, `hydration_free_energy_al`, `hydration_free_energy_li`,
  `hydration_free_energy_clo4`) are used only in the vetting below and in the cross-check of a Born-Haber route,
  never mixed with the conventional formation values in one row (one scheme per row).

Verdict of tier 1 at a cutoff E_c with the margin m_1 of the row (m_expt or m_E, Section 2a):

| Tier 1 | Condition | Note |
|---|---|---|
| pass | E_lb >= E_c + m_1 | needs the transfer premise below to be `supported` |
| below (falsifying side) | E_ub < E_c - m_1 | tier 2 then decides as already ruled (Section 2c, rows 2 to 5) |
| inconclusive | otherwise (the cutoff lies inside [E_lb - m_1, E_ub + m_1]) | both ends and the bracket width printed |
| undetermined | E_ub and E_lb both missing; or E_lb missing and E_ub >= E_c - m_1 | never passes (Section 2a) |

E_lb missing with E_ub < E_c - m_1 is still on the falsifying side (a solid-salt onset below the cutoff is enough).
E_lb > E_ub is impossible for a consistent row (the solid salt is one of the sinks the minimum runs over, see the
cycle); a row with E_lb > E_ub is flagged as a data inconsistency and counted undetermined. The class verdicts of
Section 2e use the crossovers E_lb - m_1 (feasible at or below) and E_ub + m_1 (falsified above).

**Thermodynamic cycle.** Write a cation-releasing oxidation for a phase that holds the cation M with charge z per
formula unit (M = Ca, z = 2; M = Al, z = 3), with n_e = z electrons and the Li counter electrode:

    P(s) + z Li+(S) -> M(z+)(S) + (neutral products: O2, condensed P-oxide) + z Li(s)      [solvated sink, solvent S]
    P(s) + z LiClO4(s) -> M(ClO4)z(s) + (same neutral products) + z Li(s)                  [solid-salt sink]

The perchlorate is a spectator in the solvated form: z ClO4- are in solution before and after. The onset vs Li+/Li
in the same solvent S is E_S = Delta_G_S/(z F) with

    Delta_G_S = Delta_G_gas-ion terms + [DG_solv(M, S) - z DG_solv(Li+, S)],

and the solvent enters only through the charge-balanced combination in brackets. Taking S = water gives E_lb; the
difference is

    E_S - E_lb = [DG_tr(M, w->S) - z DG_tr(Li+, w->S)] / (z F) = Delta_G_tr_rel / (Delta_n_Li F)   (function `E_solv`).

So E_lb is a lower bound on the onset in the carbonate solvent iff the **transfer premise** holds:

    Delta_G_tr_rel = DG_tr(M, w->S) - z DG_tr(Li+, w->S) >= 0     for every ionic product M (and for H+ in r3).

The solid-salt sink is one of the product states the oxidation can reach, so the thermodynamic onset with every sink
available is min(E_S, E_ub) <= E_ub: E_ub is an upper bound whatever the solvent.

**Vetting.**

1. *The argument as worded fails.* "Hard cations are not better solvated in an organic carbonate than in water"
   gives DG_tr(M, w->S) >= 0 for the product cation. It says nothing about the sign of Delta_G_tr_rel, because the
   reactant Li+ is also a hard cation transferred from water to S, and its transfer term enters with the weight z.
   A single-ion statement cannot bound a charge-balanced combination.
2. *Li-reference consistency.* The bracket is consistent only when every ion of the reaction is taken in the same
   medium: E_lb is the onset vs Li+/Li in water with Ca2+ (or Al3+) and Li+ both aqueous, and E_S is the onset vs
   Li+/Li in S. Mixing an aqueous product with Li+ in S, or with solid LiClO4, compares potentials across a liquid
   junction and is refused. With the conventional table (H+ reference) the H+ convention cancels because the
   combination M(z+) - z Li+ is neutral; the absolute single-ion hydration energies, which rest on an
   extra-thermodynamic assumption, are not needed for E_lb.
3. *The anion term.* With the electrolyte anion a spectator, the anion cancels exactly between the two sides; written
   with neutral salts, Delta_G_tr_rel = DG_tr(M(ClO4)z, w->S) - z DG_tr(LiClO4, w->S), and the anion's own transfer
   energy cancels as well. The anion is therefore not a source of error in E_lb, and its hydration key enters only
   (i) in a Born-Haber cross-check through the solid salts, where the same anion value must be used on both sides,
   and (ii) in a registered reaction that consumes or releases a solvated anion. Water solvates anions far better
   than an aprotic carbonate (no hydrogen-bond donation), so an anion released as a product moves E_lb down (the
   bound survives), while an anion consumed from solution moves it up (the bound fails): a reaction that consumes a
   solvated anion has no E_lb and stays solid-salt-only.
4. *The corrected premise.* With the relative form, the physical reading is: per unit charge, the product cation loses
   at least as much solvation on leaving water as Li+ does. In the Born continuum, DG_tr(i) = z_i^2 B_S / r_i with
   B_S >= 0 when the permittivity of S is below that of water (function `Delta_G_tr_rel_born`), and the premise
   reduces to z/r_M >= 1/r_Li: a cation of higher charge density than Li+ loses more. This holds for the radii of Ca2+
   and Al3+ against Li+ and for H+, but the Born form is a plausibility statement only: specific donor solvation and
   ion pairing in the low-permittivity carbonate (contact pairs with the anion stabilise the multivalent product
   more than Li+) act in the opposite direction and are not bounded by it. Ion pairing is inside the salt-form
   premise above when Delta_G_tr_rel is taken from salt data (solubilities in water and in S).
5. *Water is a solvation medium only.* E_lb uses water to solvate ions; it never lets water react. A product that
   would hydrolyse in water (a condensed P-oxide to phosphoric acid, Al3+ to its hydroxo complexes) is taken in its
   unhydrolysed form; a reaction that consumes water is evaluated with the cell water activity of Section 2a only.

**Verdict of the vetting: holds in corrected form, conditionally.** The bracket rule stands with the transfer premise
as a registered condition, evaluated per row:

| Premise status | Evidence | Effect on a tier-1 pass (E_lb >= E_c + m_1) |
|---|---|---|
| supported | measured transfer or salt-solubility data (water and the cell solvent class) give Delta_G_tr_rel >= 0 for the product ion (`hydration_transfer_ca_water_carbonate`, `hydration_transfer_al_water_carbonate`, with `transfer_free_energy_li_water_pc`) | pass stands, labelled `bracket, premise measured` |
| supported (computed) | no measured data; computed under `theory/protocol_computational.md` with the benchmark accepted and the credible lower bound Delta_G_tr_rel - k_q u_tr >= 0 for every ionic product (PH-C0, Section 10e) | pass only if E_lb >= E_c + m_1 + u_tr/(Delta_n_Li F), labelled `pass (computed premise)`; without a hard multivalent benchmark at most `indicative` |
| plausible only | no transfer data for the product ion; Born scaling satisfied | inconclusive, labelled `pass conditional on the transfer premise`; E_lb and E_ub printed |
| violated | data give Delta_G_tr_rel < 0 | E_lb is replaced by E_solv (the onset in S), and the row is decided with E_solv in place of E_lb |

The falsifying side (E_ub < E_c - m_1) does not depend on the premise. Where the premise is only plausible, no
tier-1 pass is possible and the rule is the solid-salt-only rule of Section 2a for that row; the required transfer
data are listed as gaps.

### 2g. Stage of a results row and the conversion steps (cp4 F4; spec for W4, W5 and W8)

**STAGE field.** Every results row carries `stage`, one of:

| stage | Phases | Conditions that apply | Conditions not evaluated |
|---|---|---|---|
| `slurry` | brushite (precursor), ACP, HAp (and OCP, beta-TCP if kept) | K2, K3, K4 | K1 (printed only as a reference row, labelled `not the cell-stage phase`) |
| `cell` | Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3 (and the Al-salt ladder rungs) | K1 | K2 to K4 (not evaluated for a phase that is not formed in the slurry) |
| `conversion` | one row per precursor-to-cell-stage pair | thresholds of the step (below) | none of K1 to K4 |

A slurry-stage phase that is also the cell-stage phase (no conversion step; for example a Ca orthophosphate used as
formed, the low-cutoff class of cp4 F5) carries both stages in two rows that share a `film_id`, and is the only case in
which K1 and K2 to K4 appear for one film.

**Conversion-step row** (per pair, for example brushite to monetite, monetite to Ca2P2O7, ACP or HAp to a condensed
phase, and the Al-salt pairs where a precursor is registered). Fields:

- `precursor`, `product`, `film_id` of each;
- `a_w_star`: the thermodynamic dehydration or condensation threshold, the water activity at which precursor and product
  (with the released water) have equal free energy, a_w* = exp(-Delta_rG0 / (n_w R T)) for precursor = product + n_w H2O (the product is favoured for a_w < a_w*)
  with Delta_rG0 from the same tabulated route as K1 (Section 2a); reported as a threshold (Section 2a, "Dehydration is
  not an oxidation"), with the temperature at which it is evaluated (`hydration_a_w_star_<pair>`);
- `T_conv_lit`: conversion temperatures from the literature, with source, heating rate and atmosphere
  (`hydration_conversion_temperature_<pair>`);
- `T_cure_baseline`: the cure range of the baked aluminophosphate baseline patent (Tsinghua and Hon Hai family, route
  layer C5; `matrix_baseline_tsinghua_cure_range`) printed beside, with `T_conv_lit` inside, below or above it;
- `hydrolysis`: for a step that passes through an aqueous stage, the K2h verdict of Section 9a;
- `status`: `feasible within the baseline cure range` (T_conv_lit inside or below the range), `requires a higher
  temperature`, or `undetermined` (no conversion temperature sourced). A status is a statement about the process
  path, not a verdict on any condition.

**Presentation rule.** A table or figure never presents K1 of a condensed (cell-stage) phase and K2 to K4 of an
orthophosphate (slurry-stage) phase as one film. A film is reported across stages only as the chain slurry row,
conversion row, cell row with the same `film_id`, and the chain is only as strong as its weakest member: a chain with an
`undetermined` or `requires a higher temperature` conversion row is labelled so in its summary line.

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

Numeric margins (set at PH-W3.2 in the generated entry `margins_v6` of the thresholds block, `theory/thresholds.md`
Section 7; never typed here), priors' parameter values and the sweep grids; the benchmark status of phosphate
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
Stages and conversion steps (cp4 F4, new): `hydration_a_w_star_<pair>` (computed, W5), `hydration_conversion_temperature_<pair>`,
`matrix_baseline_tsinghua_cure_range`.
K1 bracket (cp4 F2, new): `hydration_free_energy_clo4`, `hydration_transfer_ca_water_carbonate`,
`hydration_transfer_al_water_carbonate`, `hydration_transfer_salt_ca_clo4_2_water_carbonate` (salt form, anion cancels);
existing keys used: `dfg_ca2_aq`, `dfg_al3_aq`, `dfg_li_aq`, `hydration_free_energy_ca`, `hydration_free_energy_al`,
`hydration_free_energy_li`, `transfer_free_energy_li_water_pc`.

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

## 9. Route layer (contract v6; rulings C1 to C6)

Authority: the ROUTE LAYER of `ops/tracks/redirect_plan.md` (rulings C1 to C6, binding). Routes: R1 interfacial
gelation of a soluble polyphosphate by Al3+ released at the oxide; R2 a Ca-polyphosphate coacervate that wets the foil
and dries to a glass; R3 dry-trapped Ca-polyphosphate. Every statement is symbolic; values come from the keys of
Section 9g. Each table below is a decision table: its rows are exhaustive and evaluated in order.

### 9a. Hydrolysis descriptor (K2 conditional gate, ruling C1)

**Observable.** The condensed fraction at the end of the wet period. Polyphosphate P-O-P bonds hydrolyse toward
orthophosphate, the low-ceiling phase. Partial hydrolysis to oligophosphates still counts as condensed: only the
orthophosphate fraction is lost, so f_cond = 1 - x_ortho with x_ortho the fraction of P present as orthophosphate.
With first-order loss of condensed P at the rate constant k_eff (registered as first order in the condensed fraction;
the data are reported as rate constants of that form):

    f_cond = 2^(-t_wet / t_half),   t_half = ln 2 / k_eff,   k_eff = tau_k k_hyd        (functions `f_cond`,
                                                                                          `t_half_hyd_fn`, `k_hyd_eff`)

- **t_wet** (the wet residence time) runs from contact of the polyphosphate with water (mixing) through coating and
  drying until the water activity falls below the registered a_w,dry (`hydrolysis_a_w_dry`). It is a process input
  per route and state (`hydrolysis_t_wet_<route>`), never a fitted value.
- **k_hyd** is the measured rate constant at the nearest covered state; **tau_k** is the registered transfer factor
  from the data condition to the process state (`hydrolysis_transfer_factor`, a range [tau_lo, tau_hi] with
  tau_lo <= 1 <= tau_hi unless evidence says otherwise). The data cover gamma-Al2O3 particles at room temperature,
  pH 6 and pH 8, with and without 1 mM Ca2+ (`hydrolysis_polyp_k_ph6`, `_ph6_ca1mm`, `_ph8`, `_ph8_ca1mm`).
  They do not cover foil, drying, other pH or other temperatures.
- **Plausible rates.** k_slow = tau_lo min(k_hyd over the covered rows that bracket the state) and k_fast = tau_hi max(...);
  with Ca2+ present the Ca rows are used. f_cond is decreasing in k_eff and in t_wet (contract monotonicity), so
  f_cond(k_slow) is the most favourable and f_cond(k_fast) the least favourable condensed fraction.
- **f_min** (`hydrolysis_f_min`) is the smallest condensed fraction that keeps the film on the condensed side of the
  K1 ladder (a registration set with the K1 rows; PH-W3.2 sets the number).
- **Coverage.** A state is covered when its pH lies within the measured pH set (interpolation between pH 6 and 8
  only), its temperature equals the data temperature within the registered tolerance, and its Ca2+ level is bracketed
  by the with- and without-Ca rows. Drying states and the pit are never covered.

| # | Coverage | Condition | K2h verdict | Label |
|---|---|---|---|---|
| H1 | outside | any | undetermined, never gating | `hydrolysis: outside data` |
| H2 | covered | f_cond(k_slow) < f_min | falsified at that state | `hydrolysed even at the slowest plausible rate` |
| H3 | covered | f_cond(k_fast) >= f_min | not gating | `condensed fraction kept at the fastest plausible rate` |
| H4 | covered | otherwise | inconclusive | flip value t_wet* = t_half(k) log2(1/f_min) at k_slow and k_fast (`t_wet_max`) |

The evidence grade (`single-source`, `sourced`, `computed`, gap) of every k_hyd used and of tau_k is printed beside
every H2 to H4 verdict. K2h is a conditional gate: it gates a route's row only through H2; H1, H3 and H4 never end a
row. It applies to the condensed rows of R1 to R3 and to the conversion-step rows of Section 2g that pass through an
aqueous stage. The kinetic race of gelation against hydrolysis (R1) stays a labelled hypothesis (C2).

### 9b. Formation criteria (K3 route forms, ruling C2)

**R1, falsifying only.** The gel is an Al polyphosphate with nu_Al Al3+ and nu_PP chain units (PO3-) per formula
unit. With a_PP the free activity of the chain unit and K_sp,AlPP the solubility product of the gel written for the
same formula unit (`polyp_log10_ksp_al`, a gap):

    Omega_AlPP = a_Al^nu_Al a_PP^nu_PP / K_sp,AlPP                                         (function `Omega_AlPP`)

| # | Condition | R1 verdict at the state | Label |
|---|---|---|---|
| F1r | K_sp,AlPP is a gap | undetermined | flip value K_sp* = IAP_AlPP printed (the K_sp below which the gel is accessible) |
| F2r | P(Omega_AlPP < 1) >= p_cred | falsified at that state | `gel cannot form (thermodynamic accessibility)` |
| F3r | P(Omega_AlPP > 1) >= p_cred | not excluded | `not excluded by thermodynamic accessibility` (never a pass) |
| F4r | otherwise | inconclusive | |

- **Two labelled a(Al3+) states.** *Oxide-equilibrium* (slurry stage): a_Al fixed by the oxide or hydroxide in contact,
  a_Al = K_ox,Al a_H^3 / a_w^3 (function `a_Al_oxide_eq`; K_ox,Al from our Al-O-H Pourbaix, W5, key `polyp_al_log_k_oxide`). With the oxide present
  the free Al3+ activity is pinned by this equilibrium whatever the complexation; complexation raises the total
  dissolved Al, not a_Al. *Pit-state* (cell stage): a_Al from the literature pit solution (`polyp_al_activity_pit`),
  higher than the oxide-equilibrium value; it is a separate labelled state, never combined with the first.
- **Polyphosphate complexation of Al3+.** It lowers the free ligand, not the pinned a_Al: a_PP = f_PP,free c_PP/c_std
  with f_PP,free = 1/(1 + beta_AlPP a_Al) for 1:1 complexes in the ideal limit (function `f_PP_free`;
  `polyp_al_log_beta1_*` by ring size or chain). Where beta_AlPP is a gap for the registered chain distribution,
  the free fraction is not set to one silently: the row carries the flag `complexation gap` and is evaluated at
  f_PP,free = 1 (the upper bound on a_PP, so a falsification there stands and an F3r there is labelled optimistic).
- **R2 coacervate binodal.** The state is the point (Ca_T, P_T, pH, I) of the slurry. With the binodal map
  (`coacervate_binodal_map`, with its covered region):

| # | Coverage | Condition | R2 verdict |
|---|---|---|---|
| B1 | state outside the covered region | any | undetermined |
| B2 | covered | state outside the two-phase region with P >= p_cred | falsified at that state (`no liquid precursor`) |
| B3 | covered | state inside the two-phase region with P >= p_cred | not excluded (a liquid precursor exists; K4 route form next) |
| B4 | covered | otherwise | inconclusive |

- **R3** has no formation criterion of its own: it is the dried form of the slurry state and is decided by K2h (9a)
  and the K1 amorphous row (9d). Cut first (one sentence in the paper).

### 9c. Liquid wetting (K4 route form, ruling C3)

Three phases: the substrate s (alumina-covered foil), the dense coacervate n, and the dilute phase l in coexistence
with it. The spreading coefficient of the coacervate on the substrate under the dilute phase is

    S_coac = gamma_sl - gamma_sn - gamma_nl,     cos theta = (gamma_sl - gamma_sn) / gamma_nl   (functions `S_coac`,
                                                                                                  `cos_theta_coac`)

with S_coac = gamma_nl (cos theta - 1) on the partial-wetting branch. Write Dgamma = gamma_sl - gamma_sn (the
substrate's preference for the dense phase over the dilute one).

- **Limit gamma_nl negligible** (gamma_nl << |Dgamma|; ruling C3: coacervate-dilute tensions are orders of magnitude
  below solid-water energies, W1 to source `coacervate_gamma_nl`). S_coac -> Dgamma, and cos theta -> sign(Dgamma)
  times infinity: the coacervate wets completely if Dgamma > 0 and is expelled (theta = pi) if Dgamma < 0. The
  condition reduces to gamma_sn <= gamma_sl. The marginal case Dgamma = 0 is decided by gamma_nl and is reported
  as inconclusive.
- **Limit gamma_nl comparable** (gamma_nl of the order of |Dgamma|). Three branches: complete wetting if
  Dgamma >= gamma_nl (S_coac >= 0); partial wetting with theta < pi/2 if 0 < Dgamma < gamma_nl; non-wetting with
  theta >= pi/2 if Dgamma <= 0. The K4 route test is S_coac >= m_S; theta < pi/2 alone is reported, not gating.
- **Sign tests.** S_coac is increasing in gamma_sl and decreasing in gamma_sn and in gamma_nl; at gamma_nl -> 0 the
  sign of S_coac is the sign of Dgamma (contract limits and monotonicity of `S_coac`).

**Dgamma from polyphosphate adsorption on alumina.** Each interface s|x (x = l, n) carries the registered
Gibbs-Langmuir machinery (contract v2 to v4): Gamma_P sites per area that bind the polyphosphate chain unit with the
Langmuir constant K_P, and a layer of thickness delta_P that excludes the solute. Written at the chemical potentials of
the facing phase (activity a_P of the chain unit and the osmotic pressure Pi_osm of the solution against pure water):

    gamma_sx = gamma_sx^(0) - R T Gamma_P ln(1 + K_P a_P) + delta_P Pi_osm              (function `gamma_sx_ads`)

where gamma_sx^(0) is the energy of the site-free (polyphosphate-free) contact of the substrate with phase x, and the
last term is the grand-potential cost of excluding the solute from the layer (the ideal-dilute reading
delta_P R T c is the depletion term of `Delta_gamma_ads`). This is the general form whose ideal-dilute expansion about
the polyphosphate-free interface is the registered Delta_gamma_ads.

At coexistence the two liquids have equal chemical potentials of every component: equal a_P, equal water activity and
so equal osmotic pressure. Hence the site term and the exclusion term are the same at both interfaces and cancel:

    Dgamma = gamma_sl - gamma_sn = gamma_sl^(0) - gamma_sn^(0)                         (function `Dgamma_coac`, identity)

**Result.** Specific adsorption of polyphosphate on alumina, however strong, gives no preference for the dense phase
within this machinery: it lowers both energies equally. The substrate's preference is the difference of the site-free
contacts, which is a property of the two liquids against the bare oxide (water content, Ca2+ and counter-ion content,
polymer density) and is a gap (`coacervate_gamma_s0_dilute`, `coacervate_gamma_s0_dense`). The spreading coefficient of
the coacervate on alumina is therefore a design result in the form S_coac = (gamma_sl^(0) - gamma_sn^(0)) - gamma_nl
with its flip value Dgamma* = gamma_nl + m_S, and the R2 K4 route form is undetermined until the site-free difference or
a measured contact angle of the coacervate on alumina under its dilute phase exists (a contact angle and gamma_nl give
Dgamma = gamma_nl cos theta directly).

- **Rejected form (demonstration `Dgamma_coac_ideal`).** Applying the ideal-dilute isotherm with the concentrations of
  the two phases, Dgamma = R T [Gamma_P ln((1 + K_c c_n)/(1 + K_c c_l)) - delta_P (c_n - c_l)], attributes the
  concentration difference of coexisting phases to an activity difference, which coexistence forbids; it would credit
  the binding constant with a wetting preference. Never used in a verdict.
- **Admissibility rule (kept).** gamma_sl >= 0 and gamma_sn >= 0 at the regime state; a draw outside is refused and
  counted, never clipped (D27 form). Because the adsorption terms cancel in Dgamma but not in each energy, admissibility
  is checked on each of gamma_sl and gamma_sn with its adsorption term, before the difference is formed.
- **Single-entry rule (kept).** The binding of polyphosphate to alumina (K_P, Gamma_P) enters once, through the site
  term of `gamma_sx_ads`; gamma_sx^(0) never receives it, and a measured contact energy of the coacervate on alumina is
  used as gamma_sn at the regime state without a further adsorption correction.
- **Neutral-solute limitation (stated).** The machinery treats the chain unit with its counter-ions as a neutral solute.
  The electrostatic double-layer term of a charged oxide does not cancel: the two phases have very different ionic
  strengths, so their screening lengths differ, and the double-layer contribution to gamma_sx differs between l and n.
  It is the leading term the cancellation leaves out and is unmodelled; its sign depends on the oxide charge at the
  regime pH relative to the point of zero charge and is not assumed.
- **Descriptors.** The self-limiting thickness of the R1 gel and of the dried R2 film is a descriptor. The insulating
  bound d_max of K4 stays for every route.

### 9d. Framings (ruling C4)

- **In-situ routes R1 to R3.** The products are amorphous (gel or glass), so the **amorphous framing governs** their K1,
  K2 and K3 verdicts. The crystalline framing is an optimistic upper reference: the glass has the higher free energy,
  DeltaG_g->c = G_glass - G_crystal >= 0 per formula unit (`glass_crystal_correction_<P>`), so its oxidation onset is
  lower and its solubility higher:

      E_ox,glass = E_ox,crystal - DeltaG_g->c / (Delta_n_Li F)      (function `E_window_glass`)
      Omega_glass = Omega_crystal exp(-DeltaG_g->c / (R T))          (function `Omega_glass`)

  Glass thermochemistry enters the tier-1 route as DfG_glass = DfH_glass - T (S0_glass - sum of elemental S0) where the
  glass data exist (`glass_dfh_<P>_glass`, `glass_s0_<P>_glass`), otherwise as the crystalline value plus the bounded,
  labelled correction DeltaG_g->c with its inflated uncertainty (cp4 F3).
- **Labels.** Crystalline pass with amorphous fail: `requires crystallisation` (the route as run does not give a passing
  film; a crystallisation step would). Amorphous pass: the crystalline row is printed beside it and adds nothing.
  Both fail: falsified under the governing framing.
- **Baked baselines** (unspecified structure): both framings are reported, neither governs; the row carries
  `structure unspecified`.
- **Nucleus framings unchanged.** For the Ca orthophosphate nucleus framings (ACP versus apatite), "falsified only if
  falsified under every framing" stays (Section 3d). The governing rule above applies to the route products only.

### 9e. Matrix and baseline rules (rulings C5, C6)

| # | Matrix rung (chitosan, PDA, chitosan-polyphosphate) | Matrix K1 entry |
|---|---|---|
| M1 | tier 2 class A or B below the cutoff (E_svc < E_c - m_svc) | reported as the film's ceiling (`matrix ceiling, class X`) beside the mineral's K1; the mineral's verdict is unchanged |
| M2 | tier 2 class A or B at or above the cutoff | no ceiling from the matrix; printed beside |
| M3 | class C only, or no record (gap) | matrix-risk flag; no ceiling; never gating alone |
| M4 | a registered thermal budget could remove the matrix | both variants reported (with and without the matrix) |

The matrix has no tier 1 (an organic polymer has no meaningful thermodynamic onset here); it never gates by itself:
a row is never falsified on a matrix entry alone. Polydopamine carries the stated K1 risk (contrary B4). Tier-2 rows in
LiPF6 are context only and can counter-indicate but not support (evidence consequence 1).

| # | Baseline row (K1, K2, K4 only; no K3, no performance claim) | Rule |
|---|---|---|
| L1 | K2, a literature solubility for the composition exists | used, labelled `composition-based` |
| L2 | K2, no such value | undetermined |
| L3 | Hydro-Quebec Li polyphosphate film | solubility labelled `inference from chemistry` (water-soluble Li polyphosphate), never a patent statement; K2 undetermined unless L1 applies |
| L4 | K1 | the bracket of Section 2f under both framings (9d) |
| L5 | K4 | the insulating bound with the patent thickness keys (`matrix_baseline_*_film_thickness`) |

### 9f. Thresholds structure (symbolic; PH-W3.2 sets the numbers)

- **K2** (unchanged): Omega >= 1 per framing; the amorphous framing governs the route products (9d).
- **K2h** (conditional gate): table H1 to H4 with f_min; margins none beyond tau_k (the transfer range is the margin).
- **K3 route forms**: R1 table F1r to F4r (edge Omega_AlPP against 1, falsifying side only); R2 table B1 to B4.
- **K4 route form**: S_coac >= m_S, with the closure route of Section 3c as the alternative; falsified only if both
  fail on the same draw.
- **K1 amorphous row**: the bracket of Section 2f evaluated with the glass onset; edges E_lb,glass >= E_c + m_1 and
  E_ub,glass < E_c - m_1. Per row the margins are m_1 (m_expt or m_E), m_svc, m_S; no value is set here.

The machine form is the `screen_ph` entry of the `thresholds` block of `theory/thresholds.md` (block version 5).

### 9g. New keys for W1 (names only)

`hydration_free_energy_clo4`, `hydration_transfer_ca_water_carbonate`, `hydration_transfer_al_water_carbonate`,
`hydration_transfer_salt_ca_clo4_2_water_carbonate`, `hydrolysis_a_w_dry`, `hydrolysis_t_wet_r1`, `hydrolysis_t_wet_r2`,
`hydrolysis_t_wet_r3`, `hydrolysis_transfer_factor`, `hydrolysis_f_min`, `hydrolysis_temperature_tolerance`,
`polyp_al_activity_pit`, `polyp_al_log_k_oxide`, `polyp_ads_alumina_gamma_max`, `polyp_ads_alumina_k_langmuir`,
`polyp_ads_alumina_layer_thickness`, `coacervate_binodal_map`, `coacervate_gamma_s0_dilute`,
`coacervate_gamma_s0_dense`, `coacervate_contact_angle_alumina`, `glass_dfh_alpp_gel`, `glass_crystal_correction_alpp`,
`matrix_service_limit_chitosan`, `matrix_service_limit_pda`, `matrix_service_limit_chitosan_polyp`,
`matrix_thermal_budget`, `matrix_baseline_tsinghua_cure_range`, `hydration_a_w_star_<pair>`,
`hydration_conversion_temperature_<pair>` (pair: brushite-monetite, monetite-capp, and each precursor-to-cell-stage pair of
Section 2g).

### 9h. Interpretations for the audit

- **I8.** Rule 2d (F1): "proceeding" does not change the K1 column; an inconclusive K1 never makes a candidate barrier.
- **I9.** F2: the argument as worded fails; the bracket holds with the relative transfer premise; without transfer data
  for the product ion a tier-1 pass is inconclusive (`conditional on the transfer premise`), so the rule is
  solid-salt-only for that row.
- **I10.** F2: a reaction that consumes a solvated anion has no E_lb; E_lb > E_ub flags a data inconsistency.
- **I11.** C1: first-order loss in the condensed fraction; coverage includes interpolation in pH between the two measured
  values and nothing else; with Ca2+ present only the Ca rows bracket the state.
- **I12.** C2: with the oxide present a(Al3+) is pinned by the oxide equilibrium, so polyphosphate complexation acts on
  the free ligand; a complexation gap is evaluated at f_PP,free = 1 and flagged (falsification stands, not-excluded
  labelled optimistic).
- **I13.** C3: at coexistence the Gibbs-Langmuir site and exclusion terms cancel in gamma_sl - gamma_sn; the substrate
  preference is the site-free contact difference (a gap) and the R2 K4 route form is undetermined until it or a contact
  angle exists. The ideal-dilute two-concentration form is a rejected demonstration.
- **I14.** C4: the K1 amorphous row uses the bracket of Section 2f with the glass correction; `requires
  crystallisation` is a label, not a verdict.
- **I15.** C6: a matrix ceiling (M1) is printed as a statement about the composite film beside the mineral's K1 and
  never changes the mineral's verdict; a row is falsified at E_c only through the mineral's own K1.
- **I16.** F4: a cell-stage row inherits K2 to K4 only through its conversion-step row; no film is reported with K1
  from one stage and K2 to K4 from another.
- **I17.** (PH-W3.2, margins.) The falsifying side of an amorphous row needs no glass data. E_ub,glass = E_ub,crystal -
  DeltaG_g->c/(Delta_n_Li F) with DeltaG_g->c >= 0 (the glass is metastable with respect to its crystal), so E_ub,glass +
  m <= E_ub,crystal + m for the margin of the crystalline row. An amorphous row whose correction is a gap is therefore
  falsified wherever its crystalline row is falsified, labelled `falsified (bound)`, and stays undetermined everywhere
  else. It can never pass this way. For the nucleus framings (ACP versus apatite) this makes "falsified under every
  framing" decidable from the crystalline row alone, on the falsifying side only.

## 10. PH-W3.2 rulings: W5's post-hoc choices and the bracket verdict

Session PH-W3.2. Inputs: the PH-W5.1 outputs of lane p0-w5 and `lit/params.yaml` of lane p0-w1, at the commits pinned in
the `margins_v6` entry of the thresholds block (`theory/thresholds.md` Section 7). Numbers are not typed here: each one is
named by its key, its file, or its field of `margins_v6`.

### 10a. Ruling (a): the film solid that governs the passivation window

**W5's choice.** `al_window.json` (field `primary`) takes amorphous Al(OH)3 as the film solid that sets the window, at the
Al level of the one published window that states it (TR-091). It shows crystalline boehmite (field `reference`), gibbsite
and corundum beside it, at three Al levels. The amorphous window is the narrower one. W5 chose this after the windows
were computed, citing the C4 reading.

**Physics.** C4 is a ruling about route products, so it does not decide by itself which solid sets a(Al3+) at the foil.
That is a kinetic fact about the surface: the solid in contact with the slurry during the wet residence time t_wet, in
water, at room temperature. Three points decide the extension:

1. *Which phase is present.* The air-formed film on rolled foil is an amorphous oxide. In room-temperature water it
   hydrates. The first hydrated solid to form at that temperature is the least ordered one (the step rule that C4 applies
   to the route products). Crystalline boehmite is the product of hot-water or hydrothermal treatment, and the crystalline
   trihydroxides form only on ageing. The direction holds without a source, because the amorphous solid is the first
   precipitate. The identity of the room-temperature film within t_wet is still a fact to fetch: new W1 key
   `al_film_phase_rt_water` (phase or phases identified on Al in water at room temperature, with time and method). Until
   it is sourced, the governing row is labelled `film phase: inferred amorphous`.
2. *Nesting.* At every registered Al level, the amorphous window lies inside the window of each crystalline solid
   (`al_window.json`, field `windows`), because the amorphous solid is the most soluble registered Al solid. A state inside
   the amorphous window is therefore inside every registered window. A statement made on the amorphous row holds under
   every film framing, and the converse does not. So the amorphous row is also the conservative choice for the claim the
   window supports (the film holds at that state).
3. *R1 runs the other way.* At oxide equilibrium a(Al3+) is pinned by the film solid, and the amorphous solid gives the
   highest a(Al3+) (`a_al3_oxide.csv`). For the falsifying-only R1 test the amorphous state is the hardest to falsify, so
   an R1 falsification there stands under every film framing. A "not excluded" verdict there is optimistic if the film is
   in fact crystalline.

**Ruling.** The extension of C4 to the oxide film is justified in direction, by points 1 and 2, and conditional on the
phase identity of point 1. The rows are:

| Use | Governing row | Reference row | Also printed |
|---|---|---|---|
| passivation window (comparator state, Section 5) | Al(OH)3 am, at the TR-091 Al level | boehmite (grade A, the gated Al phase of the R-cell window) | gibbsite, corundum; every registered Al level; the published windows TR-090 and TR-091 |
| R1 oxide-equilibrium a(Al3+) (Section 9b) | Al(OH)3 am | boehmite | none |

Both rows are reported wherever either is used. An R1 "not excluded" (F3r) that holds at the amorphous state and fails
at the boehmite state is labelled `not excluded only if the film is amorphous`. An R1 falsification (F2r) at the
amorphous state is reported as robust to the film framing. Corundum is an anhydrous high-temperature phase. It is a
reference only, never a candidate for the hydrated film.

The amorphous solubility constant is single-source, grade C, and has no printed uncertainty (TB-027). The width of its
log10 K_s prior is the largest difference of the Al ion-data benchmark (`margins_v6.K3_R1`), not zero. The window stays a
comparator to the incumbent phosphoric-acid control, never a barrier verdict.

### 10b. Ruling (b): the Ca(PO3)2 glass-to-crystal correction

W5 made three choices (`ph_w51.json`, field `staged_products.vitrification`). Each one is ruled below.

1. **The correction from the LiPO3 and NaPO3 pairs, uncertainty doubled: tighten.** PH-W1.3 supplies the Ca(PO3)2 crystal
   enthalpy itself (`glass_dfh_cameta_crystal`, a CALPHAD assessment over the three polymorphs). It also supplies the
   correction against the same glass enthalpy that the amorphous row uses (`glass_crystal_correction_cameta_calphad` =
   `glass_dfh_cameta_glass` - `glass_dfh_cameta_crystal`). A value matched to the composition outranks an alkali transfer.
   The transfer assumes a vitrification enthalpy per chain unit that does not depend on the cation, and that is
   unsupported: the two alkali pairs differ, and Ca2+ crosslinks the chains. The analogue bound [0, n_PO3 h_max] is
   therefore retired to a consistency check. The direct value per PO3 lies inside it (`margins_v6.m_K1_amorphous.ruling_b.
   analogue_check`). The assessment prints no uncertainty of its own, and the polymorph envelope alone understates it. The
   uncertainty is therefore u = f_infl (half polymorph span + tabulated uncertainty of the glass enthalpy), with the
   inflation factor f_infl of cp4 F3 kept and the label `direct, assessed crystal; inflated`. The band is intersected
   with the physical domain DeltaH_g->c >= 0. Consequence: only the crystalline reference row moves; its onset and margin
   are in `ruling_b.crystalline_reference_row`, for W5 to adopt by entering the crystal through
   `glass_dfh_cameta_crystal` directly. The governing amorphous row does not use the correction, because it is built on
   the glass enthalpy, so it is unchanged.
2. **The excluded pair TT-044 (with TR-042): accept, with the reason restated.** A glass is metastable with respect to its
   crystal, so its enthalpy at room temperature lies above the crystal's, and a negative difference is inconsistent. The pair joins
   two sources whose crystal references differ, so it is the pairing that fails, and TT-044 itself is not shown wrong as a
   glass enthalpy. TT-044 therefore stays in the LiPO3 glass enthalpy of the Li polyphosphate baseline row. There the
   spread of the two glass values enters that row's budget, which widens it and is the conservative direction. After
   point 1 the exclusion touches no Ca(PO3)2 row.
3. **The residual entropy bound [0, R ln 2] per PO3: accept, as a labelled assumption with no source.** Two conditions
   apply. (i) The bound is evaluated at its ends, not as a midpoint: the upper end for E_ub, where the glass is most stable
   and the onset highest, so a falsification there stands; zero for E_lb. With the linear budget the midpoint plus
   half-span gives the same numbers, so no published value moves. (ii) The physical ceiling of the residual entropy is the
   configurational entropy frozen in at the glass transition, which is bounded by the entropy of fusion. If W1 sources it
   (new key `glass_s_fusion_cameta`) and it lies below the upper end, it replaces that end. The full span of the bound moves
   the onset by `margins_v6.m_K1_amorphous.residual_entropy.span_V`, small against the row's margin.

### 10c. The bracket verdict (cp4 F2, after the vetting of Section 2f)

**What would turn "pass inconclusive" into a pass.** By Section 2f, a tier-1 pass needs E_lb >= E_c + m together with
the transfer premise measured. The premise is Delta_G_tr_rel = DG_tr(M, w->S) - z DG_tr(Li+, w->S) >= 0, holding after
its uncertainty, for every ionic product of every reaction that is not already above the cutoff. That means Ca2+ (z = 2)
for the Ca phases, Al3+ (z = 3) for the Al rungs, and H+ for reaction r3, all in the cell solvent class S. Either of two
data forms is admissible:

- (A) single-ion transfer energies of the product cation and of Li+, into the same solvent and on the same
  extrathermodynamic scale (the ferrocene or the tetraphenylarsonium tetraphenylborate assumption), each with its
  uncertainty;
- (B) the assumption-free salt form: DG_tr(M(ClO4)z, w->S) - z DG_tr(LiClO4, w->S), taken from the solubilities and
  solid-salt data of both salts in water and in S, or from cell EMFs. Ion pairing in S is then included.

Two further conditions apply. Data in propylene carbonate count for the cell solvent only if PC is registered as the
proxy of the carbonate class (a planning-chat registration, because a statement for PC is not one for a mixture rich in
linear carbonates). And E_lb must be computed. It needs only the conventional aqueous formation values (`dfg_ca2_aq`,
`dfg_al3_aq`, `dfg_li_aq`, already keys): by Section 2f item 3 the anion cancels, so the missing
`hydration_free_energy_clo4` does not block E_lb. W5's `bracket pending` reason is a convention point, not a missing
input.

**Sufficient now: no.** At the pinned `lit/params.yaml`, `transfer_free_energy_li_water_pc` is single-source,
`transfer_free_energy_ca_water_pc` and `transfer_free_energy_al_water_pc` are gaps, and `hydration_free_energy_clo4` is a
gap. The ClO4- transfer into PC from PH-W1.3 (`transfer_free_energy_clo4_water_pc`, one determination, on the ferrocene
assumption) is neither sufficient nor needed. In the charge-balanced combination the anion cancels exactly, so its value
cannot decide the sign of Delta_G_tr_rel. It could serve only to assemble form (B) from single ions, and that still needs
the cation value that is missing. With Li+ less solvated in PC than in water (its key is positive), the premise asks
DG_tr(Ca2+) >= 2 DG_tr(Li+) and DG_tr(Al3+) >= 3 DG_tr(Li+): this is the Born ordering, and no fetched value tests it.
Every tier-1 row therefore stays solid-salt-only (Section 2f, `plausible only`).

**Go/no-go consequence.** With no pass possible, K1 can only falsify or leave a row inconclusive. By tier 1 alone (the
ladder of PH-W5.1 with the margins of `margins_v6`, before any tier 2 record is applied), the following hold. HAp,
beta-TCP and alpha-TCP, and ACP on its beta-TCP reference, are falsified at C_mid and C_hi. By I17 they are also
falsified on the amorphous framing there, so under every nucleus framing. The carbonate control falls with them.
Brushite is partial at C_hi: falsified only above its crossover inside that class. The silicate comparator Ca2SiO4 is
falsified at all three classes. Nothing is falsified at C_lo. Open, falsified at no class, are the condensed phases and
the Al phosphates. Ca2P2O7 (crystalline; its amorphous row undetermined), Ca(PO3)2 glass and crystal, and the Li
polyphosphate baseline are inconclusive at every class and never pass. AlPO4, Al(PO3)3, the Al-polyphosphate gel and the
baked aluminophosphate baseline are undetermined (no Al(PO3)3 thermochemistry, no bound on the exchange entropy of the
Al perchlorate sink). OCP and Li3PO4 are undetermined, as are CaSiO3 and Li2SiO3, whose budgets are incomplete. Under
rule 2d only Ca2SiO4 stops before K3 and K4. The Ca orthophosphates proceed on C_lo, where they are not falsified. The
condition of evidence consequence 3 of the route layer is that no condensed phosphate has a lower-bound onset above the
top of C_mid. On present data that condition holds, because no condensed phase has a supported lower bound at all, and
the open rows are open only on the upper bound. It changes only if data of form (A) or (B) arrive and the computed E_lb of
a condensed phase clears the top of C_mid plus its margin. This section reports the condition; the headline is the
operator's decision.

### 10d. Interpretations

- **I18.** (a) The film solid that governs the window is a fact about the foil surface during t_wet. It is ruled
  amorphous by the step rule and by nesting, conditional on `al_film_phase_rt_water`. For R1 the amorphous state is the
  falsification-robust one.
- **I19.** (b) A composition-matched correction outranks an analogue transfer, and the analogue bound becomes a
  consistency check. A cross-source pairing that violates metastability is excluded as a pair, never as a datum. The
  residual-entropy bound is evaluated at its ends.
- **I20.** Bracket: the anion term is neither needed for E_lb nor able to decide the premise. The pass needs a cation
  transfer in form (A) or (B) and a registered solvent proxy.

### 10e. The computed transfer premise (PH-C0; bracket rule change, verdict-bearing)

Session PH-C0, before any transfer free energy is computed. Authority: the COMPUTATIONAL PACKAGE section of
`ops/tracks/redirect_plan.md`; the method, the benchmark and the registered conventions are in
`theory/protocol_computational.md`, and the machine form is `screen_ph.links.K1.premise.computed` of the thresholds
block (block version 7). Every registered value is proposed; the planning chat rules at cp5a2.

**The rule.** The pass condition of Section 2f, "measured Delta_G_tr_rel >= 0", becomes: the premise is **measured**
(form A or B of Section 10c), **or computed** under the protocol such that the credible lower bound
Delta_G_tr_rel_lcb = Delta_G_tr_rel - k_q u_tr is >= 0 at the registered one-sided level q, for every ionic product of
the row. Here u_tr = f_z R_bench is the benchmark RMSE on the relative quantity times the charge inflation factor of the
ion. A pass under a computed premise must clear the class edge, the row's margin and the premise uncertainty, combined
as a linear sum:

    E_lb >= E_c + m_1 + u_tr / (Delta_n_Li F),

and it is labelled `pass (computed premise)` everywhere (ladder, tables, abstract). The physical reason for carrying
u_tr twice: the lower-bound test establishes the sign at level q, and the edge term keeps the pass true even if the
premise is wrong by up to one calibrated uncertainty, since E_solv >= E_lb - u_tr/(Delta_n_Li F) whenever
Delta_G_tr_rel >= -u_tr.

**Conditions.** (i) The benchmark is run first and accepted (R_bench <= R_cap on Na+, K+, Rb+ and Cs+ against Li+ in PC);
a failed benchmark leaves every row solid-salt-only, with the premise `unresolved (benchmark failed)`. (ii) Cu2+ and Hg2+
(Jahn-Teller and soft ions) validate the charge dependence only and never stand in for Ca2+ or Al3+ by ion type. (iii)
Without a hard multivalent measured benchmark, Ca2+ and Al3+ are labelled `extrapolated (ion type)` and reach at most
`indicative`, never a pass. (iv) An ion whose u_tr is not smaller than its |Delta_G_tr_rel| is `unresolved`. (v) PC is
the proxy of the cyclic-carbonate class only; ethylene carbonate and the linear carbonates are extrapolations.

**Decision table** (protocol Section 5; D = Delta_G_tr_rel, u = u_tr, E* = E_c + m_1).

| # | Premise | Condition | Tier-1 outcome | Label |
|---|---|---|---|---|
| P1 | measured | D minus its stated uncertainty >= 0, E_lb >= E* | pass | `pass (premise measured)` |
| P2 | computed, hard multivalent benchmark | D - k_q u >= 0, E_lb >= E* + u/(Delta_n_Li F) | pass | `pass (computed premise)` |
| P3 | as P2 | D - k_q u >= 0, E* <= E_lb < E* + u/(Delta_n_Li F) | inconclusive | `computed premise; edge not cleared` |
| P4 | computed, no hard multivalent benchmark | as P2 | inconclusive (at most indicative) | `indicative (computed premise, extrapolated (ion type))` |
| P5 | computed | u < abs(D), D - k_q u < 0 | inconclusive | `computed premise not established` |
| P6 | computed | D + k_q u < 0 | solid-salt-only; E_solv printed as a comparator | `premise violated (computed)` |
| P7 | computed | u >= abs(D), charge check failed, or a needed job capped | inconclusive | `unresolved (computed premise)` |
| P8 | computed | R_bench > R_cap | inconclusive for every row | `unresolved (benchmark failed)` |
| P9 | none | no data, no accepted computation | inconclusive | `pass conditional on the transfer premise` |

The falsifying side does not depend on the premise. Sequence disclosure: the K1 upper bounds were seen before this rule
and the protocol were written; both were written and hashed before any transfer value was computed. The scope guard
allows "thermodynamic viability (computed premise)" for a P2 row and still forbids "works", "protects" and "self-heals"
outside hypothesis wording.

- **I21.** The computed premise is a weaker kind of evidence than a measurement; it enters only through a credible lower
  bound and an edge widened by its own uncertainty, and only after a benchmark on the same relative quantity.

### 10f. The coverage criterion for the hydrolysis descriptor (PH-C0, X4)

**Question.** Section 9a needs f_min, the smallest condensed fraction that keeps the film on the condensed side of the
K1 ladder. The proposal is that the vulnerable orthophosphate fraction must not percolate: f_min = 1 - p_c, with p_c the
site-percolation threshold of the lattice assumed for the film.

**Derivation.** Let x_ortho = 1 - f_cond be the fraction of film sites that are orthophosphate. Assume (A1) each site is
orthophosphate independently with probability x_ortho (no correlation of hydrolysed sites); (A2) an orthophosphate site
fails at its own, lower K1 onset, and a condensed site does not; (A3) a failed site is harmful only through a connected
path of failed sites (an isolated failed site is enclosed by condensed sites and its oxidation stays local); (A4) the
film is a regular lattice of one site type. Under A1 to A4 the film's K1 is that of the condensed phase iff the
failed sites do not form a spanning cluster, which holds (for a large film) iff x_ortho < p_c. So the criterion is
f_cond > 1 - p_c, and f_min = 1 - p_c.

**Which p_c.** The proposed values (square and triangular lattices) are two-dimensional thresholds. They describe a
lateral spanning cluster in the plane of the film. That is the right criterion only for reading L: domains that span
the film thickness (columnar), isolated through-defects tolerated because they stay local (A3 at the substrate), and
failure that matters only by lateral propagation. For reading T, a film many sites thick in which failure matters by a
through-thickness path from electrolyte to metal, the threshold is three-dimensional, smaller than the two-dimensional
ones, so 1 - p_c is larger and the criterion stricter. For a film one site thick, every failed site is a through-path
and no fraction is tolerated (f_min = 1). The triangular site threshold is exactly 1/2; the others are numerical values
to be fetched (new W1 keys `p_c_site_square`, `p_c_site_triangular`,
`p_c_site_sc`, with DOI and locator). The brief's range (f_min from 1 - p_c,square to 1/2)
is therefore the reading-L range only.

**Ruling.** The form f_min = 1 - p_c is accepted as a conditional criterion under A1 to A4; the two-dimensional range
alone is rejected as the criterion, because the reading is not fixed by data. Registration (proposed; the planning chat
rules at cp5a2): f_min is an interval [1 - p_c(reading L), 1 - p_c(reading T)]; H2 (falsified) is evaluated at the lower
end and H3 (not gating) at the upper end, so that neither verdict depends on the unfixed reading, as the transfer range
tau_k does for k_eff. A1 is the weakest assumption: hydrolysis starts at the wetted face, so the orthophosphate is
layered, not random, and a layered vulnerable fraction can fail at any x_ortho. **What the paper may say.** Any K2h
statement is conditional on f_min ("if a non-percolating orthophosphate fraction is tolerable, then ..."); K2h stays
report-only, f_min stays a design axis, and no K2h statement gates a row or enters the headline.

## 11. PH-W3.6 registrations (C2 to C6, X4 as ruled)

Session PH-W3.6, lane p0-w3. Everything is symbolic: names of `lit/params.yaml` keys, no literature number. Values and
verdict text reach the paper only through the generated macros (standing rule 4). Registered in block version 8 of
`theory/thresholds.md` (`screen_ph.w36`).

### 11a. C2: carbonate K2 framings, and the label "nacre-type"

**K2 framings for carbonate** are calcite, aragonite and ACC (amorphous calcium carbonate, the formation-stage
precursor). The K2 test for each polymorph pi is the Omega test of Section 3a at every state of the registered grid:

    Omega_bulk(pi) = a_Ca a_CO3 / K_sp(pi) >= 1           pass at the state; Omega_bulk(pi) < 1 means pi dissolves

| Polymorph | K_sp key | Role in the label rule |
|---|---|---|
| calcite | `log10_ksp_calcite` | required |
| aragonite | `log10_ksp_aragonite` | required |
| ACC | `log10_ksp_acc` (with `acc_hydration_n` for the hydrated product) | reported beside the two; **not required to pass** |

The activities a_Ca and a_CO3 come from the contract speciation at the registered (Ca_T, C_T, pH, I); the framing
changes only K_sp (one framing per run, Q12). The ACC dose window is reported beside the calcite and aragonite
windows: ACC is the precursor of the formation stage, not the phase that has to survive in service.

**Label rule.** A row may be labelled `nacre-type` ONLY where aragonite AND calcite both pass K2 (ACC may fail or be
undetermined and the label stands). Every other carbonate row is labelled `carbonate (calcite)`: a row that fails
aragonite, a row where aragonite is undetermined (data missing), and every row of a study that has not registered the
aragonite test. Passing calcite alone never earns `nacre-type`.

**Falsifiability control, per polymorph.** The same test, with the same code path and the same K_sp key, must flag
undersaturation (Omega_bulk(pi) < 1, dissolution) at the low-dose corner of the registered grid, for each of
calcite, aragonite and ACC. A polymorph whose control does not flag undersaturation there has an inconclusive K2 in
every row, whatever its pass pattern, and the rows that depend on it cannot be labelled `nacre-type`. The existing
supersaturated control of Section 3a is kept beside it.

Which of the two crystalline polymorphs is the more soluble is read from the two keys and printed, never assumed.

### 11b. C3: the verdict label for a K2 pass

The label of a row that passes K2 is, verbatim:

    thermodynamically suitable against dissolution (a necessary condition) for [phase] in [region]

[phase] is the registered polymorph or framing the test was run for (Section 11a); [region] is the registered
(Ca_T, C_T, pH, I) grid over which Omega_bulk >= 1 holds at every state, named by its grid id, never "the process"
or "the slurry". The rules that go with the label, in the same section of the paper:

- It does not address Al's own instability above its passivation window and is not evidence of protection. It is a
  statement about the mineral against its solution at the registered states, and nothing else.
- The acid-adjusted pH state (`params.ph_slurry_acid_adjusted`) is shown as the incumbent comparator in the same table,
  evaluated by the same test and printed beside the registered region.
- No sentence of the paper may use "suitable" without the conditions "for [phase] in [region]" within six words. A
  sentence that cannot carry both conditions uses the vocabulary of Section 11d instead.

### 11c. C4: the low-voltage wording

**Class.** The low-voltage class is **not excluded** at the nominal cutoff (the C_lo class of Section 2e,
`regimes.R-cell.parameters.cutoff_classes`), with a cutoff of 4 V registered as a sensitivity line beside it (a
registered design cutoff, not a result). Both are read off the K1 verdict table of Section 2c for the carbonate row and
the phosphate rows, per cutoff, and the word "excluded" is used only in the sense of Section 11d.

**Wording rule.** The paper words the claim as

    low voltage up to about [tier-2 onset]

where [tier-2 onset] is the number E_svc of the tier-2 row of the ladder (the best record, class A or B outranking C,
Section 2b), emitted by a macro from the hash-pinned ladder file together with the id of that row (macro for the row
identity, macro for the number). Neither the number nor the row is ever typed. If no tier-2 row exists for the claimed
phase, the phrase is not written and the row reads `undetermined (data missing)`.

**The 4 V line.** At the 4 V sensitivity line the carbonate row is close to falsification: the tier-1 crossover (E_x-,
Section 2e) and the tier-2 onset both come from the ladder files by macro, and the paper prints them beside the 4 V
line. The sentence "close to falsification" is emitted only when the generated predicate holds (E_x- lies within the
margin m_1 of the 4 V line, or the tier-2 onset lies within m_svc of it); otherwise the plain crossover and onset are
printed and the sentence is dropped. Proposed; the planning chat rules at cp5b.

### 11d. C5: the regime-table vocabulary

The regime table of the paper uses exactly these five terms, and no other verdict word:

| Term | Meaning | Source of the entry |
|---|---|---|
| excluded | falsified at the cutoff; where the class verdict is partial (Section 2e) the numeric crossover (E_x-) is printed | K1 verdict table, Section 2c |
| not excluded | not falsified, with a feasible or kinetically stabilised K1 verdict (class A or B named) | K1 verdict table, Section 2c |
| thermodynamically suitable against dissolution (a necessary condition) for [phase] in [region] | K2 passes at every state of the registered grid, label text of Section 11b | K2 test of Section 11a |
| open | not falsified, no lower bound: the test is inconclusive on both sides, or the bracket contains the cutoff | verdict row 6 of Section 2c |
| undetermined | data missing: a gap key, an unbenchmarked number or an unregistered sink (`undetermined (data missing)`) | verdict row 7 of Section 2c |

Every cell is **generated** from the hash-pinned ladder and the production outputs only: the ladder file, the margins
file and the production verdict files named in the blocks of `theory/thresholds.md`, through the macro generator. No
cell is typed, and a cell with no source in those files reads `undetermined`. The term "suitable" appears only inside
the full label text of Section 11b.

### 11e. X4 as ruled: the f_min interval

f_min is registered as the interval from 1 - p_c(2D lateral) to 1 - p_c(3D through-thickness), reported as a
sensitivity:

    f_min in [ 1 - p_c_site_square , 1 - p_c_site_sc ]        (keys `p_c_site_square`, `p_c_site_sc`)

The 2D lateral end uses the square lattice, the larger of the two 2D thresholds, so the lowest f_min; the triangular
site threshold (`p_c_site_triangular`) is a lattice sensitivity inside the 2D range, printed beside it. The 3D
through-thickness end uses the simple cubic lattice. H2 (falsified) is evaluated at the lower end and H3 (not gating) at
the upper end, as in Section 10f; a film one site thick has f_min = 1. **K2h is report-only**: no K2h statement gates a
row or enters the headline, f_min stays a design axis, and every statement is conditional on A1 to A4 of Section 10f.
Against PH-C0's registration the form and the use are unchanged; the keys are renamed to the W1 names and the lateral
end is fixed to the square lattice (PH-C0 left the 2D lattice open). The interval is therefore re-registered in block
version 8; the percolation keys are created by PH-W1.6 and no value appears here.

### 11f. C6: status lines

- The bracket rule of block version 7 (Section 10e) is **inactive in v1**: E_lb is pending, so no tier-1 pass is possible
  and every row stays solid-salt-only for the pass edge.
- The protocol hashes of PH-C0 (`theory/protocol_computational.md` and the earlier thresholds block) are informational;
  they gate nothing.
- R_cap, the t-quantile and the cluster sizes defer to v2.
- The abstract order is not set here; the integrator adds it to the plan text. `ops/tracks/*` is not edited.
