# PH-W4.1 report: generic mineral screen code and dry runs (lane p0-w4, day 4)

No production run, no change to priors, thresholds, verdict rules or K1 numbers. Base 60dbe6b (the ancestry check for 48e41ab was skipped on the planning chat's ruling).

## Additions
- **Contract v5** (`src/nacre/physics`): ion activity product, `Omega_nu`, `Delta_mu_fu`, `V_m_fu`, `n_star_fu`, `DG_hom_mineral`, `DG_het_mineral`, the two demonstrations (exponent error, per-ion barrier), `a_OH`, phosphate speciation (`gamma_act_3` to `f_phos_closure`, `speciate_phosphate`). Carbonate functions untouched. Registry at version 5, 85 functions plus the composite.
- **Equivalence** against W3 `60dbe6b` (contract changed at `b21dbf0`), rtol 1e-12, recorded in `configs/preprint/contract_check.json`: PASS. Largest error at a well-conditioned point 5.9e-13 (v5 functions: 1.6e-11 for `DG_het_mineral` at one ill-conditioned point); a few points of eight functions, `Pi_ads_max` at most 6.9e-11, are ill-conditioned in the contract expression and pass on the registered "no less accurate than the float reference" clause. Calcite equivalence PASS (`Omega_nu`, `Delta_mu_fu`, `DG_hom_mineral` reduce to `Omega_bulk`, `Delta_mu`, `DG_hom`); nu = 9 and 14 cases tested.
- **Mineral object** (`screen/mineral.py`): name, formula unit, nu (nu_ca + nu_x + nu_y), n_hyd, K_sp / V_m / gamma keys, framing, plus `phase_state` (crystalline | amorphous | liquid_precursor, default crystalline) and `chain_length_n` (integer or null, default null). `chain.evaluate(x, mineral=...)`; the default is calcite and takes the legacy code path. Registered in `screen.yaml` `minerals`: hap, acp, capoly (the condensed-phosphate placeholder).
- **K evaluators** (`screen/kscreen.py`): K2, K3, K4 as in `claims_redirect.md`, framing rule, D27 admissibility with M_adm printed, deletion test on K3 and K4 (`generic` label), K1 reader (two rows per phase and class, one per framing; read, not recomputed). Margins: `screen.yaml` `k_screen`, marked provisional.
- **Gap skeleton** `configs/preprint/gap_resolution_ph.yaml`; mock table `mock_params_ph.yaml`; dry-run driver `screen/ph_dry.py`, CLI `python -m nacre.screen ph-dryrun`.

## Carbonate regression
`python -m nacre.screen.ph_regress` reruns the primary state of the committed W4.3b documents (same table, prior set, framing, seed, draws) through the generalised chain and compares mean and 11 quantiles: `ignorance_adm` anchor, sequester, nucleate, speciation, 34 of 34 quantities; `table_adm` speciation 4 of 4. Largest relative difference 4.0e-16 (tolerance: two standard errors). The committed documents are untouched.

## Dry runs (mock priors, `results/preprint/screen/dryrun_ph/`, git-ignored, not reported; K1 gate overridden because the ladder passes no phase)
| class | time | peak MB |
|---|---|---|
| hydroxyapatite | 3.2 s | 353 |
| ACP framing | 4.1 s | 510 |
| condensed-phosphate placeholder | 2.4 s | 262 |
Total 9.7 s, peak 510 MB, 8192 draws, small Sobol/Shapley; each document validates against the results schema (v4, under `extensions.p0-w4.ph_screen`). Nothing tuned; the mock K_sp and gamma scales were set once to put Omega near 1 on the dose axis.

## Keys without a registered treatment
55 entries read "to register at cp5 freeze": per-phase K_sp, V_m, gamma_nl, gamma_nv (6 phases x 4), the ACP and OCP water keys, the phosphate speciation constants, pKw, p_cred / p_deg / m_cos / m_S / margin_service / m_1, `al_passivation_window`, the ladder keys sigma_corr, rho_film, dv_film, j_corr_max, t_max_corr, s_tol, and the phosphate gamma_nv analog. Filled: gamma_sn0 and delta_gamma_w and delta_s (ignorance), the bare-oxide control (ignorance), P_T / pH / cutoff classes / a_w / a_OH (design axis), competing-phase K_sp, PVDF, `log10_ksp_el_<F>` (unresolved). K1 inputs are W5's.

## Route extension points (`screen/routes.py`, raise NotImplementedError)
`liquid_precursor_wetting`, `formation_accessibility`, `hydrolysis_descriptor` (3). `routes.pending_for(mineral)` lists them beside every result.

## Outstanding
- `tests/screen/test_screen_thresholds.py::test_committed_copy_equals_theory_thresholds` fails: W3's v5 commit `b21dbf0` changed `theory/thresholds.md` after the copy's source `fd5846f`. Not touched here (the copy waits for the cp5 freeze; needs a deviation entry).
- The real K1 ladder passes no phase, so K3 and K4 run only under the dry-run override. The ladder has no `framing` column yet: its single row per class reads as crystalline, and the amorphous K1 row is missing.
- `d_max` for K4 uses the ohmic bound only (the tunnelling bound needs the R-cell keys).
- Tests: `tests/physics tests/screen` 542 passed, 1 failed (the thresholds copy above). verify not run (per brief).
