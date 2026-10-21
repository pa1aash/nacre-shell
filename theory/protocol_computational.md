# Protocol of the computational package: the computed transfer premise and its benchmark (PH-C0)

Session PH-C0, lane p0-w3. Authority: the COMPUTATIONAL PACKAGE section of `ops/tracks/redirect_plan.md` (item P1) and
standing rule 19 (D61). This file is written, committed and hashed before any transfer free energy is computed. Every
number in it is a registered convention (a cap, a factor, a level or a count chosen here), never a literature value;
benchmark data are named by their evidence row id in `lit/evidence_table.csv` and by their `lit/params.yaml` key.
**Every proposed value is marked "proposed; the planning chat rules at cp5a2"**; the machine form is the entry
`screen_ph.links.K1.premise.computed` of the thresholds block (`theory/thresholds.md`, block version 7). Symbols keep
their ids in `theory/symbols.yaml`: `Delta_G_tr_rel`, `E_lb`, `E_solv`, `Delta_n_Li`, `F_c`, `m_expt`, `E_c`, and the
two added here, `u_tr` (calibrated premise uncertainty) and `Delta_G_tr_rel_lcb` (its credible lower bound).

## 1. Target quantity

**Physical reason.** The lower end of the K1 bracket, E_lb, is the oxidation onset with every ion of the reaction in
water (`claims_redirect.md` Section 2f). The cell solvent changes the onset only through how much better or worse it
solvates the released cation than the consumed Li+ ions, per unit of charge. A single-ion solvation energy carries an
unmeasurable surface-potential term proportional to the ion's charge; in the charge-balanced combination that term
cancels, and so does any constant error per unit charge that a computational method makes.

**Rule 1a (target).** The computed quantity is

    Delta_G_tr_rel = DG_tr(M^z+, w -> PC) - z DG_tr(Li+, w -> PC),     DG_tr(i, w -> PC) = DG*_solv(i, PC) - DG*_solv(i, w),

with every term computed within one method (Section 2): the same functional, basis, continuum model, cluster rule
and thermal treatment for M^z+ and Li+, in water and in propylene carbonate (PC). Only the combination is used; a
computed single-ion transfer value is never quoted as a result and never compared with a single-ion literature value
outside the scale-anchoring rule of Section 3.

**Rule 1b (sign).** With the onset vs Li+/Li in each medium (functions `E_lb`, `E_solv`),

    E_PC = E_aq + Delta_G_tr_rel / (Delta_n_Li F),     Delta_n_Li = n_e = z for a cation-releasing reaction,

so Delta_G_tr_rel >= 0 gives E_PC >= E_aq, and E_aq = E_lb is a lower bound on the onset in the carbonate. This is
the transfer premise of Section 2f; it must hold for every ionic product of every reaction of the row (Ca2+ with
z = 2, Al3+ with z = 3; H+ for reaction r3, which this package does not compute and which therefore stays on measured
data or blocks the pass of an r3-limited row).

## 2. Method class (free tools only)

**Physical reason.** A bare continuum misses the specific donor bonds of the first solvation shell, which dominate the
solvation of a small, highly charged cation and differ between water (O-H donors and acceptors) and PC (a carbonyl
donor, no hydrogen-bond donation). Placing the first shell explicitly and the rest in a continuum (cluster-continuum)
captures that difference; using the identical recipe in both solvents makes the remaining errors correlated, so that
they cancel in the transfer and again in the charge-balanced combination.

**Rule 2a (tools).** xtb and CREST (pinned in `src/nacre/anchor/xtb_env.yaml`) for conformers and cluster
geometries; PySCF or Psi4 for the DFT energies with an implicit-solvent model. No ORCA and no other licensed code.
One code is used for every DFT job of the package; the choice between PySCF and Psi4 is made at PH-C1 before the
first benchmark job, by a feature check (the continuum model of Rule 2d is available for every solvent of Section 3)
that produces no energy.

**Rule 2b (clusters).** The cluster of ion i in solvent S is M(S)_n with n = n_i registered per ion and the same n in
water and in every non-aqueous solvent (correlated first-shell error). Proposed n_i (proposed; the planning chat rules
at cp5a2): Li+ 4; Na+, K+, Rb+, Cs+ 6; Ca2+ 6; Al3+ 6; Cu2+, Zn2+, Cd2+, Hg2+ 6; La3+ 8. Maximum cluster size
n_max = 8 solvent molecules (proposed; the planning chat rules at cp5a2). A sensitivity at n_i - 1 is run for Li+,
Ca2+ and Al3+ only, reported beside the primary value and never replacing it. The solvent cluster (S)_n is built for
every n used, by the same conformer search.

**Rule 2c (geometries and thermal terms).** CREST conformer search of each cluster with GFN2-xTB in the gas phase,
the lowest conformer optimised with GFN2-xTB, and the thermal free-energy correction (quasi-rigid-rotor-harmonic-
oscillator, as implemented in xtb) at that geometry. The same gas-phase geometry and thermal term are used in every
solvent: the continuum enters only through the DFT solvation energy, so no solvent-specific geometry choice can enter
one side of the transfer and not the other.

**Rule 2d (energies).** One hybrid functional with an empirical dispersion correction and one triple-zeta basis with
effective core potentials for the heavy ions, single points on the GFN2-xTB geometries, in the gas phase and in the
continuum (proposed: PBE0-D3(BJ)/def2-TZVP; proposed; the planning chat rules at cp5a2). Continuum model: SMD where
the chosen code implements it and published descriptors exist for every solvent of Section 3; otherwise IEF-PCM
electrostatics for every solvent. The same model is used for all solvents in either case. Solvent descriptors and
dielectric constants are fetched values with their keys (W1), never fitted.

**Rule 2e (the thermodynamic cycle, written out).** For ion A = M^z+ in solvent S with the cluster cycle (the solvent
enters as the cluster (S)_n, which removes the n-fold solvent-concentration term of the monomer cycle):

    DG*_solv(A, S) = DG*_bind(A, S) + DG*_solv(A(S)_n, S) - DG*_solv((S)_n, S) - R T ln([S]/n)
    DG*_bind(A, S) = G_gas(A(S)_n) - G_gas(A) - G_gas((S)_n) - DG(1 atm -> 1 M)

with G_gas the DFT gas-phase energy plus the GFN2-xTB thermal term, DG*_solv the DFT continuum solvation free energy
at 1 M, DG(1 atm -> 1 M) = R T ln(R T / (p0 V0)) the standard-state change of one gas-phase species, and [S] the molar
concentration of the neat solvent (a fetched key per solvent, from its density and molar mass). Written for the two
media of the target:

    water:  DG*_solv(A, w)  = DG*_bind(A, w)  + DG*_solv(A(H2O)_n, w)  - DG*_solv((H2O)_n, w)  - R T ln([H2O]/n)
    PC:     DG*_solv(A, PC) = DG*_bind(A, PC) + DG*_solv(A(PC)_n, PC) - DG*_solv((PC)_n, PC) - R T ln([PC]/n)

The standard-state change cancels in each transfer; nothing else is assumed to cancel.

**Rule 2f (no tuning).** Everything in Rules 2a to 2e is fixed before the first benchmark job. No choice is changed
after any benchmark energy exists. If a job fails for a technical reason, it is rerun unchanged once; a change of
method after the benchmark voids the computed premise, is disclosed as a deviation, and the first result stays the
primary one.

**Rule 2g (cost bound).** Per-job wall-time cap 4 h on 16 cores (proposed; the planning chat rules at cp5a2). A job
that reaches the cap is stopped and recorded `capped`; the ion and solvent it serves are `not computed`, and any
result that needs it is `unresolved`. Every job and its cost is logged in `jobs/ledger/p0-w5.jsonl` (rule 19). PH-C1
projects the cost from the job list (ions and solvents of Section 3, n_max, the per-job cap) and stops if the
projection exceeds the budget of rule 19.

## 3. The benchmark, run first

**Physical reason.** A cluster-continuum transfer energy has no error bar of its own. Its error must be measured on
ions whose transfer into the same solvent is known, and the comparison must be made on the same charge-balanced
quantity as the target, because only that quantity is free of the extrathermodynamic scale of the data and of the
per-charge offset of the method.

**Rule 3a (order).** The benchmark jobs are run and the acceptance test of Rule 3c is evaluated, committed and hashed
before any Ca2+ or Al3+ job is started.

**Rule 3b (ion set, from PH-W1.5).**

| Set | Ions | Solvent | Scale | Rows | Role |
|---|---|---|---|---|---|
| A (acceptance) | Na+, K+, Rb+, Cs+ against Li+ | PC | TATB, selected values | TI-077, TT-092 to TT-095 | relative quantity DG_tr(M+) - DG_tr(Li+); enters the RMSE |
| A' (data spread) | Li+ to Cs+ | PC | TATB, two determinations | TT-096 to TT-105 | spread of the data on the relative quantity; not a benchmark point |
| Q (charge, in PC) | Cu2+, Hg2+ | PC | negligible liquid junction (Cu2+); ferrocene, shifted toward TATB in the compilation (Hg2+) | TT-106, TT-107 | charge-dependence check only (Rule 3d) |
| Q (charge, other solvents) | Cu2+ (MeCN, DMF, DMSO, MeOH); Zn2+, Cd2+ (DMSO); Hg2+ (MeCN, DMSO); La3+ (MeOH; MeCN as a bound) | as listed | as listed per row | TT-108 to TT-117 | charge-extrapolation validation (Rule 3d) |
| Ca (weight zero) | Ca2+ | MeCN | three scales | TT-118 to TT-120 | enters only if one scale is registered (Rule 3e) |

Scales are never mixed within one relative quantity.

**Rule 3c (acceptance).** R_bench is the root-mean-square difference between computed and measured relative
quantities over set A (four values). The benchmark is accepted iff

    R_bench <= R_cap,     R_cap = 12 kJ/mol (proposed; the planning chat rules at cp5a2; the plan value is 15 kJ/mol).

Two registered conditions fix the cap. (i) It is not below the spread of the data themselves on the relative quantity
(set A'), so the test is not decided by the disagreement of the measurements. (ii) The inflated premise uncertainty it
allows, in volts, is not larger than the smallest K1 margin of the Ca rows the premise could decide:
f_2 R_cap / (2 F) <= min over those rows of m_expt (`screen_ph.margins_v6`), so that the computed premise is never the
dominant term of the edge it qualifies. The plan value fails (ii) against the Ca(PO3)2 glass row; the proposed value meets it
with room to spare. **Failure** (R_bench > R_cap, or any job
of set A capped): no computed pass anywhere; the premise is reported `unresolved (benchmark failed)` and every row stays
solid-salt-only, as now.

**Rule 3d (how Cu2+ and Hg2+, and the other multivalent rows, count).** Cu2+ is a Jahn-Teller ion and Hg2+ (like Cd2+)
is a soft, polarisable ion. Their solvation is set by covalent and orbital terms that Ca2+ and Al3+ (hard, closed-shell,
electrostatically bound) do not have, so their errors cannot be transferred to Ca2+ and Al3+ by ion type. They test
only whether the method's error grows with charge. They do not enter R_bench. A multivalent row is **counted** in the
charge check when its relative quantity can be formed on one scale: a monovalent reference ion with a transfer value
on the same scale, in the same solvent, is a key (W1), or the row's scale is defined by such an ion. A counted row
passes the check iff |computed - measured| <= f_z R_bench for its charge z. A row that cannot be anchored is computed and
reported as `scale-unanchored`, and never counts. A bound row (La3+ in MeCN) passes iff the computed value does not
violate the bound by more than f_3 R_bench. If any counted row of charge z fails, the inflation factor of that charge is
not supported and every Ca2+ (z = 2) or Al3+ (z = 3) result is `unresolved (charge check failed)`.

**Rule 3e (hard multivalent benchmark).** A hard multivalent measured benchmark exists iff a hard (closed-shell,
electrostatically solvated) cation of charge >= 2 is a counted row of Rule 3d and passes it. The candidates are La3+ in
MeOH (TT-117; counts if a monovalent reference on the TATB scale in MeOH is a key) and Ca2+ in MeCN (TT-118 to TT-120,
weight zero) once one scale is registered. Of the three Ca2+ scales, the one defined by DG_tr(Rb+) = 0 (TT-118) forms
the relative quantity DG_tr(Ca2+) - 2 DG_tr(Rb+) by construction; that is the proposed registration (proposed; the
planning chat rules at cp5a2). Without a hard multivalent benchmark, Ca2+ and Al3+ carry the label
`extrapolated (ion type)`.

## 4. Calibrated uncertainty for Ca2+ and Al3+

**Physical reason.** Set A measures the method's error at z = 1. The error of a cluster-continuum solvation energy grows
with the ion's charge density (a stronger field polarises the shell and the cavity boundary more, and the second shell
matters more), so the monovalent error understates it for Ca2+ and more so for Al3+.

**Rule 4a (inflation).** u_tr(M) = f_z R_bench, with f_2 = 2 for Ca2+ and f_3 = 3 for Al3+; f_2 = f_3 = 2 only if a
hard multivalent measured benchmark exists (Rule 3e) (proposed; the planning chat rules at cp5a2).

**Rule 4b (sign resolution).** An ion's computed premise is `resolved` iff u_tr(M) < |Delta_G_tr_rel(M)|; otherwise it
is `unresolved (u_tr >= |Delta_G_tr_rel|)`.

**Rule 4c (labels).** With no hard multivalent measured benchmark, every Ca2+ and Al3+ result is labelled
`extrapolated` and supports at most `indicative`, never a plain pass and never `pass (computed premise)`.

## 5. The bracket rule change (verdict-bearing)

**Physical reason.** A computed premise with a calibrated error can establish the sign of Delta_G_tr_rel to a stated
credibility, which a Born-scaling argument cannot. It is weaker evidence than a measurement, so it must carry its error
twice: once in the sign test, and once in the potential edge, so that a pass also survives a premise that is wrong by
up to one calibrated uncertainty (E_PC >= E_aq - u_tr/(Delta_n_Li F) whenever Delta_G_tr_rel >= -u_tr).

**Rule 5a (premise).** The transfer premise is supported if it is (i) measured (form A or B of `claims_redirect.md`
Section 10c), OR (ii) computed under this protocol with

    Delta_G_tr_rel_lcb = Delta_G_tr_rel - k_q u_tr >= 0,

the credible lower bound at the one-sided level q = 95 % (proposed; the planning chat rules at cp5a2), with k_q the
one-sided Student-t quantile at q with N_bench degrees of freedom (N_bench = 4, the residuals that define R_bench;
proposed; the planning chat rules at cp5a2), for every ionic product of the row.

**Rule 5b (edge under a computed premise).** A pass under (ii) needs

    E_lb >= E_c,sup + m_1 + u_tr / (Delta_n_Li F)       (linear sum, as for the margins),

with E_c,sup the top of the cutoff class, m_1 the row's margin (m_expt; m_E where the experimental route is missing),
and u_tr the largest calibrated uncertainty among the row's ionic products, divided by that product's Delta_n_Li. It is
labelled `pass (computed premise)` in the ladder, the tables and the abstract, everywhere it appears.

**Decision table** (rows in order; symbolic examples with u = u_tr, D = Delta_G_tr_rel, E = E_lb, E* = E_c,sup + m_1).

| # | Premise evidence | Condition | K1 tier-1 outcome | Label | Example |
|---|---|---|---|---|---|
| P1 | measured (form A or B) | D - (its stated uncertainty) >= 0 and E >= E* | pass | `pass (premise measured)` | D = 3u_m with stated u_m; E = E* |
| P2 | computed, benchmark accepted, hard multivalent benchmark, charge check passed | D - k_q u >= 0 and E >= E* + u/(Delta_n_Li F) | pass | `pass (computed premise)` | D = 3u (k_q < 3); E = E* + 2u/(Delta_n_Li F) |
| P3 | as P2 | D - k_q u >= 0 and E* <= E < E* + u/(Delta_n_Li F) | inconclusive | `computed premise; edge not cleared` | D = 3u; E = E* + u/(2 Delta_n_Li F) |
| P4 | computed, benchmark accepted, no hard multivalent benchmark | D - k_q u >= 0 and E >= E* + u/(Delta_n_Li F) | inconclusive (at most indicative) | `indicative (computed premise, extrapolated (ion type))` | as P2 without Rule 3e |
| P5 | computed, resolved but not credible | u < abs(D) and D - k_q u < 0 | inconclusive (plausible only) | `computed premise not established` | D = u + (u/2) with k_q > 3/2 |
| P6 | computed, resolved and violated | D + k_q u < 0 | E_lb is no lower bound; solid-salt-only; E_solv printed as a comparator | `premise violated (computed)` | D = -3u |
| P7 | computed, unresolved | u >= abs(D), or charge check failed, or a needed job capped | inconclusive (solid-salt-only) | `unresolved (computed premise)` | D = u/2 |
| P8 | computed, benchmark failed | R_bench > R_cap | inconclusive (solid-salt-only) for every row | `unresolved (benchmark failed)` | R_bench = 2 R_cap |
| P9 | none | no data, no accepted computation | inconclusive | `pass conditional on the transfer premise` (Section 2f, plausible only) | (current state) |

The falsifying side (E_ub < E_c - m_1) does not depend on the premise and is unchanged by this table.

## 6. Scope, sequence and wording

**Rule 6a (solvent proxy).** PC is registered as the proxy of the cyclic-carbonate class only: it is a cyclic
carbonate with a permittivity of the order of water's, so ion pairing is weak and the single-ion transfer describes
the solvated product. Ethylene carbonate (solid at room temperature, measured as a melt or in mixtures) and the linear
carbonates (low permittivity, strong ion pairing, which the single-ion transfer omits) are extrapolations, and every
statement for them says so.

**Rule 6b (sequence disclosure).** Sentence for the paper and the SI: "The K1 upper bounds (solid-salt onsets) of every
phase were computed and seen before this protocol was written; the protocol, the benchmark acceptance cap, the
inflation factors and the credible level were registered and hashed before any transfer free energy was computed."

**Rule 6c (scope guard).** The guard allows "thermodynamic viability (computed premise)" for a row labelled `pass
(computed premise)`, and "indicative" for a row of P4. It still forbids "works", "protects" and "self-heals" (and the
registered patterns of `ops/tracks/redirect_plan.md`) outside hypothesis or criterion wording. A computed premise is
never described as measured, and a PC result is never described as a result for the carbonate electrolyte without the
proxy qualifier.

## 7. What this protocol does not decide

It contains no computed value and no literature value. Which rows become passes depends on PH-C1 to PH-C3; the
headline (A or B of the redirect plan) is decided only after the results packet. The registration of the Ca2+ MeCN
scale, the La3+ reference key, the cap value (12 or 15 kJ/mol) and the quantile family are for the planning chat at
cp5a2.
