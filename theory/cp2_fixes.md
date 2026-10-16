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
