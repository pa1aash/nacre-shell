# cp2 fix log (session P0-W3.2 fix-up, lane p0-w3)

The planning chat ruled on checkpoint cp2 on 2026-10-17: PASS once F1 to F9 are applied as
written. This log is for the auditor's spot-check. Each fix is its own commit on
`preprint/p0-w3`, based on `800d5ea3de41a0fb16084519d5c2680eeb14952d`.

Equation numbers are those of the fix-up build of `theory/build/derivation.pdf`, and the stable
label is in brackets. "Derivation" means `theory/derivation_body.tex`. Each commit passes
`theory/tools/check_contract.py`. No screen output was run or read (rule R7).

## Audit fixes

| Fix | Files, section or equation | Commit | Summary |
|---|---|---|---|
| F1 | derivation 7, "Template-nucleus interface" and "Consequence for the barrier", new Eq. (33) [th:eq:gibbs-sn]; proof step (3); rule 3 of 7 (rule); contract `conventions.adsorption`; equation sheet sections 2 and 6; symbols `Gamma_Ca_sn` (new), `gamma_sn` | `44f0bc00431505096b9820af225fdec081443f61` | gamma_sn is the grand-canonical excess of the template-crystal contact at the regime chemical potentials, with d gamma_sn/d mu_Ca = -Gamma_Ca,sn. Headline: d(gamma_sl - gamma_sn)/d mu_Ca = -(Gamma_Ca,sl - Gamma_Ca,sn). The screen rule is unchanged and is stated as a rule for supplied inputs: gamma_sn comes from contact data at the regime state and never receives Delta_G_seq. This does not claim Gamma_Ca,sn = 0. |
| F2 | derivation 7, "Template-liquid interface" before Eq. (32) [th:eq:gibbs], and the new paragraph "Limitation: the double-layer term"; contract `conventions.adsorption` and `Delta_gamma_ads` note | `96df9a782f7250715bd6353b7b85bfdb5fe595b7` | The 4 (ii) cancellation concerns the ion product, not the electrocapillary part of gamma_sl. Gibbs-Langmuir is now a neutral-solute approximation. The neglected diffuse-layer term is a stated limitation; ionic strength screens it (I^(-1/2) at a fixed change of charge, low potential). |
| F3 | `theory/thresholds.md` section 2 (C2), section 3 (study) and the machine block (`links.C2`, `study`); checker (descriptor and study-rule checks); `theory/cp2_brief.md` sections A to C | `a4178a1b84cdfbd7b4e1d260217e57ad6f2cda6b` | C2 is reported, not gated: Delta_G_seq, Theta_occ, Gamma_Ca and Delta_gamma_ads. The finding "the sequestration premise fails" is reported if P(Delta_G_seq >= 0) >= p_cred. The study gates on C1, C3, C4 and C5, and deletion_test.links = [C3, C4]. The charter texts for the integrator: the C2 wording plus the ruled sentence, and the deletion-register C2 rows. |
| F4 | `theory/thresholds.md` C3 (b), key table, machine block `C3b`; derivation 5 after Eq. (26) [th:eq:access]; symbols `A_patch` (new), `N_req`; `theory/cp2_brief.md` section D | `4f64f4d569d8239692e297832cf70f3c90546d20` | N_req = 1/A_patch with key `regimes.R-slurry.parameters.patch_area`. The closure density stays in C4 only. A Poisson-occupancy refinement, ln(1/q_0)/A_patch, is recorded as a cp3 proposal. No geometry-independent definition was found that is better. |
| F5 | `theory/thresholds.md` C5 R-cell and the machine block `C5c_ox`, `C5c_red`; derivation 9, sink rule (3) and (5) after Eq. (43) [th:eq:sink]; `theory/open_questions.md` Q9; checker (falsify edges) | `29cc993e5eb145512f7ce8942029544e5400ec3a` | (a) A pass must hold under the lowest-onset CO2 scheme and a falsification under every registered scheme; otherwise inconclusive. (b) A pass counts only with a solvated sink; a solid-salt limit is an upper bound, so its falsification stands and its pass is inconclusive. (c) The electrolyte's own anodic limit is a stated limitation. |
| F6 | `theory/thresholds.md` C5 R-slurry and the machine block (`acc_edge_equivalence`, sensitivity `C5s_ACC`); derivation 8, R-slurry paragraph after Eq. (40) [th:eq:pbx]; `theory/open_questions.md` Q8 | `e5ce0da1389aabe7d66cbafe08b6875c1a6cd42d` | Adding Delta_ACC to the edge makes the ACC test equal to the calcite-level test (Psi_ACC = Psi_calcite + Delta_ACC/n_M, hull unchanged): stability of CaCO3 as a phase at the regime activities, up to the framing's metastability. The ACC dissolution margin (Omega_bulk with the ACC K_sp) is a labelled sensitivity. |
| F7 | contract `Omega_bulk_hydrated` (new, sensitivity only); `theory/thresholds.md` section 1 (water activity) and the machine block `decision.drying_states`, key table; derivation 4, "Structural water (Q13)"; symbols `a_w`, `n_hyd` (new); `theory/open_questions.md` Q13 | `83460ffeb0d36e16dd4a34539b1e21c78b92039d` | IAP = a_Ca a_CO3 is kept. Omitting a_w^n overstates Omega by a_w^(-n) when a_w < 1, so drying states are optimistic (checked: Omega_bulk_hydrated <= Omega_bulk on a_w in (0, 1]). a_w is reported at each drying state, with a labelled a_w^n sensitivity where W1 has n. |
| F8 | derivation 3, the sentence before Eq. (7) [th:eq:enr] | `dacfb15b04a76f36c6fd163c3156ca344da46e15` | "With the local-ideal bookkeeping and dilute, non-interacting sites" becomes "In the dilute limit with non-interacting sites". |
| F9 | symbols `h_coal` (new) and `h_c`; contract `h_c` note; derivation 8, coalescence paragraph after Eq. (37) [th:eq:hc] and candidate (c); `theory/thresholds.md` C4; equation sheet section 7; macro `\hcoal`; `theory/cp2_brief.md` section E | `fad32e5fb91eff607b0ba14474c762b2be30ea49` | The kinetic critical coalescence thickness is renamed h_coal; h_c keeps its geometric meaning. The charter rename is recorded for the integrator. |

## Conventions (section 3 of the ruling)

| Item | Files | Commit | Summary |
|---|---|---|---|
| p_cred | `theory/thresholds.md` section 1 "Registered conventions", `decision.conventions` | `d90967cd58b5b47e253f727ac89e29dcf4a74ff1` | 0.9 primary; sweep 0.6, 0.9, 0.99 |
| p_deg | same | same | p_deg = 1 - p_cred, so 0.1 at the primary level (it moves with the sweep) |
| m_cos | same; C3 (a) margin text | same | 0 primary (the priors carry the method error); published sweeps 0.1 and 0.2 |
| m_W, m_S, m_E | same | same | Set by W1 from fetched method-error evidence, or zero where the prior carries it. Keys: `thresholds.C1.margin_W_adh_wet`, `thresholds.C4.margin_S_spread`, `thresholds.C5.window_margin`. W1 states which case applies. |
| Approved as proposed | same | same | Single edge f = 1/2 plus the absolute criterion; worst state per link and a path sum for C3 (b); square-lattice closure as the optimistic supporting condition (Q14); C4 = S_spread >= m_S, falsified only if coalescence also fails |
| Sizing rule (W4.3) | same, `decision.sizing` | same | Band-mass half-width <= 0.01 and top Sobol total-order half-widths <= 0.02 (half-width = 2 Monte Carlo standard errors). Caps: 2^20 base draws per regime state, 6 h of wall clock per run. Report as capped if a cap is reached. Draws stream in chunks of 2^14. |
| E_enr | same | same | Reported only as a labelled, non-gating sensitivity |
| Checker | `theory/tools/check_contract.py` | same | The convention values are allowed only as these tokens and only in the threshold, fix-log, brief and prior files. Checks: p_cred and its sweep lie in (1/2, 1), p_deg = 1 - p_cred, m_cos lies in [0, 1), and the sizing fields are present. |

## Gap policy, theory part, and the contract version

| Item | Files | Commit | Summary |
|---|---|---|---|
| (i) Ignorance priors | `theory/ignorance_priors.md` (new), symbols `gamma_nv`, `a_site`, `rho_L`, `d_layer`, `r_Ca`; checker `ignorance` block | `9249661f4c1b044a12ff3fdfab2a7afee82ea545` | gamma_sn ~ U[0, gamma_p + gamma_nv] from the dry work of adhesion; the wet work is not bounded. Branch masses are clip((gamma_sl - gamma_nl)/G), 2 gamma_nl/G (interior) and clip(1 - (gamma_sl + gamma_nl)/G), checked as exact integrals. Bounds for gamma_ow, gamma_op and Delta_gamma_w. Reporting rule: flip values and required precision, never P(feasible). |
| (iii) Gamma_s, delta_s | same | same | 0 < Gamma_s <= min(1/(N_A a_site), rho_L d_layer); max(2 r_Ca, Gamma_s V_m) <= delta_s <= d_layer; V_site = delta_s/(N_A Gamma_s). Single-source binding energies are widened to at least m_seq and flagged. |
| (v) Carbonate speciation | contract: `gamma_act_1`, `gamma_act_2`, `m_CT_fn`, `m_CaT_fn`, `A_carb_fn`, `P_pair_fn`, `D_Ca_fn`, `a_CO3_speciation`, `a_Ca_speciation`, `c_Ca_free`; derivation 4, "Activities from speciation", Eqs. (11) and (12) [th:eq:balance, th:eq:aco3]; equation sheet section 3; 20 symbols | `717485662dae8d3442202fb0e3e9ef279301064b` | Free a_CO3 and a_Ca from pH, C_T, Ca_T and I, with CaCO3(aq), CaHCO3+ and CaOH+. Closed-form positive root of the mass-balance quadratic. Davies activities, valid for I <= I_val (fetched) and never past the Davies turning point. Limit cases are checked: no Ca or no pairs gives the carbonate system alone, I -> 0 gives ideal activities, and the carbon balance holds. |
| Contract v3 | `theory/contract.yaml` version 3 and changelog; `theory/thresholds.md` `contract_version: 3`; derivation and equation-sheet PDFs rebuilt; equation numbers beside labels updated | `db872ae9190c3b729bc2b13898919fbfbe56815b` | 11 functions added; 4 entries changed (conventions.adsorption, conventions.speciation, Delta_gamma_ads note, h_c note); none removed. No v2 expression changed. |

## Negative tests (scratch copies, one fault at a time)

Twelve faults were planted, and each makes `check_contract.py` fail:
- C2 put back in the study rule;
- C2 added to the deletion links;
- a verdict test given to C2;
- p_deg not equal to 1 - p_cred;
- a p_cred sweep value below one half;
- a stray decimal in `thresholds.md`;
- a wrong branch mass;
- a wrong unit on an ignorance bound;
- the sign of the speciation root;
- the Davies charge-two exponent;
- the hydrated IAP inverted;
- a wrong unit on the C5 falsify edge.

Two of these first made the checker crash instead of reporting. The dimension errors are now
caught and reported as FAIL.

# cp3 amendments (session P0-W3.3, lane p0-w3)

The planning chat ruled on checkpoint cp3 on 2026-10-17: PASS once R1 to R12 are applied. Items
R1 to R8 belong to this lane and were applied one commit each on `preprint/p0-w3`, based on
`ac5cdfb`; R9 is recorded here only (lane W2 owns the retrodiction criterion). Equation numbers
are those of the P0-W3.3 cp3 build of `theory/build/derivation.pdf`, with the stable label in
brackets. Every commit passes `theory/tools/check_contract.py`. No screen output was run or read
(rule R7). The thresholds machine block is now version 2; the contract stays at version 3 (no
contract expression changed).

| Item | Files, section or equation | Commit | Summary |
|---|---|---|---|
| R1 | `theory/thresholds.md` C5 R-slurry, Section 3 (design points), key table, machine block `C5s`, `C5s_phase`; derivation 9, new paragraph and Eq. (43) [th:eq:pbx-omega], Table 1 row C5, rule 5 of 7; equation sheet 8(a) | `cfa9f2d3644f2d284781f5772b3f6a5b4eae3a49` | Dissolution is decided by Omega_bulk >= 1 with the sourced calcite K_sp and the speciation activities, the quantity C3 uses; derivation states the shared Omega and shows why a hull distance cannot decide it (the tolerance hides undersaturation down to ln Omega = -n_at e_f / (R T); a computed dissolution energy shifts K_sp by its error over R T ln 10). The Pourbaix hull stays for competing solids (dissolved Ca removed) and the Al baseline at fixed C(IV), with its DFT tolerance. The falsifiability control applies to the Omega test. Calcite K_sp decides; ACC Omega is the labelled sensitivity (F6). Verdict per design point over (a_Ca, C_T): the dose window. Carbon redox is an assumption with a labelled sensitivity. Disclosure added. |
| R2 | `theory/thresholds.md` C5 R-cell, key table, machine block `C5c_ox`, `C5c_red`; symbols `m_expt` (new); checker (edges of the no-expt fallback); derivation 9, new paragraph "Which thermochemistry decides the limit" | `eed03d8b8b28fa1437663c35eddeffbe29733d97` | The all-experimental route governs wherever its inputs exist; DFT schemes are comparators with their benchmark errors, and a benchmark-corrected value equals the experimental route by construction (never a second confirmation). m_expt = tabulated uncertainties plus a bound on the neglected Ca(ClO4)2 solid entropy from analog entropies (new W1 keys). Falsified if E_ox(expt) + m_expt < E_cell_max (solid-salt sink stands); a pass needs E_ox(expt) - m_expt >= E_cell_max with the solvated sink. E_cell_max is a design axis by cathode class, with the two crossover cutoffs reported. Every scheme printed; disclosure that the values were seen first. Physics: Li2CO3's measured onset lies near its experimental equilibrium limit (key `li2co3_oxidation_onset`, W5 benchmark B6). Where the experimental route is missing, the F5 rule with m_E applies (interpretation; the ruling is silent there). |
| R3 | `theory/thresholds.md` C4 and machine block `C4`; derivation 8, new paragraph and Eq. (41) [th:eq:spread-bound]; `theory/ignorance_priors.md` Section 2 and block | `63e086ba59ebd87fae849b91abc54b1c231aae53` | C4 is good per draw if S_spread >= m_S or N_nuc >= N_s_closure (upper-estimate N_nuc); falsified only if both fail at p, inconclusive otherwise; P(gamma_sl > gamma_nl) reported. Physical result: S_spread <= gamma_sl - gamma_nl because gamma_sn >= 0, so for any hydrophilic template (gamma_sl <= gamma_nl) S_spread < 0 for every admissible gamma_sn and complete wetting is excluded. |
| R5 | `theory/thresholds.md` C3 (b), key table, machine block `C3b`; derivation 5, new Eq. (27) [th:eq:nreq]; symbols `q_0` (new), `N_req`; equation sheet 6a; checker (single-state edge consistency) | `1ade8de3d9fecf6493a0345e416f61114a73152d` | N_req = ln(1/q_0)/A_patch with q_0 = 1 - p_cred: Poisson occupancy leaves a fraction exp(-N_nuc A_patch) <= q_0 of the contact patches empty. The cp2 form 1/A_patch is q_0 = 1/e. |
| R6 | `theory/thresholds.md` C3 (a), Section 3 ("Framings"), key table, machine block `study.framings`; derivation 4 (K_sp sentence) and Table 11; `theory/open_questions.md` Q12 | `01a809e6d48420b015c0332dea8c8f048c7eacc5` | Calcite and ACC both registered, each run as a whole chain. Falsified only if falsified under every framing; feasible under at least one, named, with the other beside it. Disclosure: a calcite-framing estimate near one half was available when the project was designed. |
| R7 | `theory/thresholds.md` Section 1 ("Link masses", "States"), C3 verdict, deletion test, machine block `decision.link_mass`, `decision.states` | `faca26521255fda6f1fa6d293911ff52b655b458` | (1) Link masses are joint, draw by draw: falsified side P(any test bad) for A-and-B links, P(both routes bad) for C4; the deletion test uses the same joint masses. (4) Every registered state is propagated; C3 (b) (and the C4 closure route) cannot be falsified unless every state, drying included, is evaluated: with a state missing, a shortfall is inconclusive and a pass stands. The mirror for worst-state links (a pass needs every state) is stated as a consequence. |
| R8 | `theory/thresholds.md` C1 terminations, Section 1 (gamma_sl0 truncation), C5 R-cell gated phases and sinks, key table, machine block; `theory/ignorance_priors.md` 1d | `d782db2f19fafb5a40367f604502c36f75d0cc16` | Per-termination C1 verdicts plus an ignorance mixture over the weights (flat Dirichlet), never a point weight. R-cell gated phases CaCO3, corundum and boehmite; LiBOB and LiPCP sinks undetermined (never a pass). gamma_sl0 truncated at 0, untruncated prior a labelled sensitivity. |
| Header, references, PDFs | `theory/thresholds.md` header and `revised_cp3`; equation references in `thresholds.md` and `open_questions.md`; derivation and equation-sheet PDFs | `74ac69c2586c017e2bc08efecbfbc918b94f48ee` | Thresholds marked ready for cp3 at this commit (`ops/state/p0-w3.json` `thresholds_cp3`). Derivation 18 pages, equation sheet 3 pages, no undefined references or overfull boxes. |

**R9 (recorded only; lane W2 owns it).** The retrodiction criterion is approved as frozen. The
requirement that a constant-predictor baseline must fail is dropped: with all 12 outcomes in one
direction, a constant predictor scores 12 of 12, so the requirement cannot be met by any
predictor. A permutation null is reported as a descriptive control. The label-swap check stands.
This amends D17 for W2; nothing in `theory/**` depends on it.

**Interpretations for the auditor.**
- R1: the hull for competing phases excludes dissolved Ca-bearing species, so that it does not
  re-decide dissolution with the bias R1 removes.
- R1: verdicts are formed per design point, and the study verdict is combined at each point.
- R2: where the experimental route is missing, the cp2 F5 rule over the DFT schemes with m_E
  decides, labelled DFT-decided; the reduction limits follow the same route rule.
- R3 with R7: C4's feasible side is the joint P(S_spread route or closure route good); the two
  single-route conditions of R3 are sufficient for it.
- R7: the worst-state mirror of the missing-state rule (a pass needs every registered state).

**Negative tests (scratch copies, one fault at a time).** Each fails the checker: a C3b
single-state edge inconsistent with N_req; a no-expt fallback edge with the wrong unit; the C5s
Omega edge replaced by a voltage margin.

## cp3b registrations for production (session P0-W3.4, lane note N22)

Four registrations required by cp3 for W4.3's production run, one commit each, based on `227d997`
(after tag `p0-cp3`). No screen output was consulted: nothing under `results/preprint/screen/` was
read. The thresholds machine block is now version 3 and the ignorance block version 2. The contract
stays at version 3. Every commit passes `theory/tools/check_contract.py`. Ready mark:
`thresholds_cp3b` at `fd29fcdb023517e7c90b06493f760db77ea47c3c` (after the PDF rebuild).

| Item | Files, section | Commit | Summary |
|---|---|---|---|
| A1 | `theory/thresholds.md` Section 1 conventions, C5 R-cell "Margin m_expt" and the new "Margin-to-scheme mapping", key table, machine block (`decision.conventions.m_expt`, `C5c_ox.margin_by_route`, `C5c_red`); symbol `N_unc`; checker (margin routes) | `0fd2b59aa37c451b25de4ad0491ef26371382844` | m_expt (`thresholds.C5.window_margin_expt`, W1 key `window_margin_expt`) applies to the all-experimental route. m_E (`thresholds.C5.window_margin`, W1 key `window_margin`) applies to a DFT scheme only where no experimental route exists (cp2 F5). Comparators carry no margin. A margin covers one reaction and one sink. m_E for other reactions is n_unc e_f/(Delta_n F), W1's rule. A limit whose margin key is absent is undetermined. The params path `thresholds.C5.expt_margin`, which did not resolve in `lit/params.yaml`, is replaced. The m_expt part keys are named as W1 derived them. |
| A2 | `theory/thresholds.md` C1 "Termination ignorance mixture", machine block `C1.mixture` | `8ff2b532c101bbcac31aefb261853c5cb245981f` | W_mix = sum_k w_k W_k (Dupre works add over disjoint areas), with w ~ Dirichlet(1, ..., 1) drawn once per draw. No point weight and no sub-region. Per-termination verdicts are always beside the mixture. The weight-free bounds P(min_k W_k > m_W) <= P_good(mix) <= P(max_k W_k > m_W) are printed. Otherwise the verdict is labelled conditional on the mixture. |
| A3 | `theory/ignorance_priors.md` Section 4a and block v2 (`geometry.A_patch`, `a_site`, `rho_L`, expanded Gamma_s cap, `delta_s.r_Ca_treatment`, `analog_bounds`, `evaluable_now`); `theory/thresholds.md` C3 (b) keys and `C3b.A_patch_bound`; symbols `d_p`, `a_asp`, `rho_PDA`, `M_u`; checker (N_req range, evaluable-now consistency) | `f338fe96ba09049a9bf835b2178bcb678c9903e7` | a_asp <= A_patch <= pi d_p^2/4, loguniform; both keys absent, so it is a gap (C3b "gap", flip values printed). a_site >= 2 sqrt(3) r_Ca^2 (hexagonal packing of bound ions). rho_L <= rho_PDA/M_u (stoichiometry). r_Ca is the radius at the lowest registered coordination number. While it is a gap, the 2 r_Ca term is dropped (valid, looser), and the Ca-O analog is a labelled sensitivity. Analog-based bounds never refuse draws. Evaluable now: delta_s and V_site. Gaps: A_patch, a_site, rho_L and the Gamma_s cap. |
| A4 | `theory/thresholds.md` C1 "C1 inputs in P0", key table, machine block `C1.p0_inputs`; checker (P0 inputs) | `22ef46446205f63fab6074ba971ee89e18d99489` | No PMF, so the registered C1 verdict is "gap" (inconclusive). Two estimates run side by side: the flagged analog `w_adh_wet_catechol_oxide_analog`, conditional on the analog (positive support only, so it leans toward anchoring), and the Dupre estimate gamma_ow + gamma_pw - gamma_op with the ignorance priors of 1c (its bounds admit both signs; band masses never a finding; flip value gamma_op* and the flip line). Neither estimate resolves terminations or needs the contact-area definition. |
| PDFs | `theory/equation_sheet.tex`, `theory/generated/symbol_table.tex`, `theory/build/equation_sheet.pdf` | `4c0a3b0`, `fd29fcd` | Symbol table regenerated (five new symbols). Row spacing is set as a length, so the sheet stays at 3 pages. `4c0a3b0` failed the theory number scan (a decimal row spacing) and was pushed through a masked exit status. `fd29fcd` fixes it. The derivation is unchanged at 18 pages. |

**Freeze rule.** `theory/thresholds.md` is frozen after `p0-cp3`, and `nacre track check P0-W3.4`
now refuses until `ops/tracks/p0_deviations.md` carries a dated entry. That file belongs to the
integrator (`ops/**`), and the lane-ownership hook rejects it on this branch. The entry text for
the integrator is in `ops/reports/P0-W3.4.md`.

**Interpretations for the auditor (cp4).**
- A1: the m_expt path is taken as W1's `thresholds.C5.window_margin_expt`.
- A1: a margin is per reaction and sink, so the solvated-sink and Al-phase expt limits need their
  own budget keys.
- A2: the mixture quantity is the area-weighted Dupre work, not a mixture of per-termination
  indicators.
- A3: the footprint bound assumes one interfacial layer of sites, as Section 4 did.
- A3: the accessible-site content is not registered as a lower bound on rho_L.
- A4: "the rule already registered" is read as follows. The PMF route decides C1, so it is a gap
  in P0. The analog verdict is conditional, and the ignorance masses are not a finding. Hence no
  study verdict in P0 can be feasible.

**Negative tests (scratch copies, one fault at a time).** Each fails the checker:
- an m_E formula without the Faraday constant;
- the m_expt route path set back to `thresholds.C5.expt_margin`;
- an a_site bound with the unit of a length;
- A_patch marked evaluable while listed as a gap;
- a Dupre support term with an added pure number.

## D27 amendment: admissibility of the template-liquid energy (session P0-W3.4b)

Decision D27 (2026-10-18). After P0-W4.3, W4 reported that with the flagged binding-constant analog
the template-liquid energy gamma_sl is negative on every draw. The amendment was derived from the
physics and from that one fact, as stated in D27 and in the C3 and gap sections of
`ops/reports/P0-W4.3.md`. Nothing under `results/preprint/screen/` and no other screen output was
read. Properties of the priors in `lit/params.yaml` were evaluated only after the rule was committed
(`ops/reports/P0-W3.4b.md`). Contract v4, thresholds block v4, ignorance block v3. Every commit passes
`theory/tools/check_contract.py`. Ready mark: `admissibility` at
`fd5846fd43d43e457566068f381a43ed96a8c1c3`.

| Item | Files, section | Commit | Summary |
|---|---|---|---|
| Checker defect | `theory/tools/check_contract.py` | `30f01ab` | The C1 P0-inputs block of `22ef464` (cp3b A4) ended the per-test loop, so from `22ef464` to `30f01ab` the edge, falsify, margin-route and single-state checks ran for C1 only. The cp3b A1 negative tests were run before `22ef464`. Restored; a planted C3a unit fault passes the old checker and fails the new one. Inequalities accept `subs`. |
| Registration | `theory/contract.yaml` v4, `theory/symbols.yaml` (`pKa2`, `K_Ca_L`, `c_std`), `theory/thresholds.md` Section 1 "Admissibility", C2 "Analog route", C3 (a) "What a favourable template needs", C4, key table, block v4 (`decision.admissibility`, `links.C2.analog_route`); `theory/ignorance_priors.md` Section 2a and block v3; checker (SF4, admissibility, analog route, favourable mass, half-line domains, zero edges) | `6690b52` | gamma_sl = gamma_sl0 + Delta_gamma_ads >= 0 at every registered state and design point. The joint prior of (gamma_sl0, Delta_G_seq, Gamma_s, delta_s) is restricted to it. Refused draws are counted, never clipped or floored. M_adm is printed beside every verdict that uses gamma_sl. If 1 - M_adm >= p_cred, the link verdict is inconclusive ("inadmissible inputs"), with the restricted verdict beside it. The unrestricted run is a labelled sensitivity. New functions: Pi_ads, Pi_ads_max, gamma_sl_floor, r_ads, Delta_G_seq_cycle_2H, Delta_G_site_from_K, x_bind_K. |
| Derivation | `theory/derivation_body.tex` Section 7 (Admissibility) A1 to A5, new labels th:eq:adm, radm, x-analog, cycle2, pimax, overshoot, favourable; `theory/si_derivation.tex` new subsection thsi:sec:admissibility; equation sheet section 2 | `fd5846f` | A1 stability; A2 reference state (double count, pH and ionic-strength shift by Lippmann, small-change validity ratio); A3 solution constant against site (two-proton correction; repulsion and competition make Langmuir an upper bound; geometry two-sided; Pi_ads_max = R T Gamma_s (ln E - 1 + 1/E) < -Gamma_s Delta_G_seq, independent of delta_s and gamma_sl0); A4 rule (i), (ii) and (iii) rejected with reasons; A5 favourable iff gamma_sn <= gamma_sl. |

**Interpretations for the auditor (cp4).**
- The "inadmissible inputs" clause (1 - M_adm >= p_cred gives an inconclusive verdict) goes beyond a
  bare restriction of the prior. Reason: at that level the stability condition rejects the input set at
  the same credibility the decision rule asks of any verdict, so a verdict built on the admissible
  remainder cannot be credited. It applies to feasible and falsified verdicts alike.
- A draw is admissible only if gamma_sl >= 0 at every registered state, because one film meets them all.
  The path condition over Ca2+ doses (gamma_sl_floor >= 0) is reported, not gating: the order in which
  Ca2+ meets the template is not a registered input.
- The analog route charges two protons because W1 records the constant for the fully deprotonated
  ligand (catecholate) and keys pka2_catechol for the dianion fraction. A one-proton reading of the same
  constant overstates the binding.
- The direction of the gamma_sl0 reference-state shift (pure water to the alkaline regime lowers it)
  rests on the electrocapillary maximum at zero charge. It is a direction, not a magnitude, and is not
  used in any rule.

**Negative tests (scratch copies, one fault at a time).** Each fails the checker:
- the sign of the R T term in Pi_ads_max;
- the first-proton exponent in the two-proton cycle;
- an admissibility edge with the unit of a molar energy;
- an SF4 witness whose strong-binding draw is admissible;
- a favourable mass with the margin's sign reversed;
- the `unrestricted` field removed from the admissibility block;
- the standard-state ratio inverted in Delta_G_site_from_K.
