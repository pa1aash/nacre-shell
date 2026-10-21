# Note for the planning chat: cp5 closure (PH-I5d), 2026-10-22. STATUS: BLOCKED, p0-cp5 not tagged, nothing pushed.
Why: `nacre verify --strict` FAIL (6 tests, below); condition (i) not shown (X6 not identifiable in the repository).

## Hashes (full table: ops/packets/p0-5a2_hashes.txt, tree 7ebb4b3 + manifest 46f9ce8)
| file | sha256 (first 16) |
|---|---|
| lit/params.yaml | 0ee35c055bac4f74 |
| theory/thresholds.md (file) | 57dbc26942a57af5 |
| thresholds.md block v8 | d92b42e9106e574f (equals expected) |
| theory/contract.yaml (v6) | 5249c6695b54ec00 |
| theory/claims_redirect.md | 1e0af21b7d71a593 |
| configs/preprint/thresholds.yaml | 48d99f4292ee1629 |
| configs/preprint/symbol_bindings.yaml | 4d6517f147966178 (header hash 543ca9db6c8b1567) |
| configs/preprint/gap_resolution_ph.yaml | ac7baeed37deb1b7 |
| ladder_v3.csv | 595636ef1c7cfd77 (equals expected) |
| ladder_v3_sens40.csv | 595636ef1c7cfd77 (byte-identical to ladder_v3.csv; PH-W5.3 says no verdict changes at 4.0 V; please confirm that is intended) |
| theory/protocol_computational.md | 57fafbeda8f3535f (informational) |
Code trees: src/nacre/screen 43f05f26a9f3d112, src/nacre/physics 86ea27fa6128751d. MP books: 2026.04.13 (production) and 2026.09.28.

## Aragonite row
log10_ksp_aragonite_25c_i0 = -8.336, uniform [-8.376, -8.296] (+-0.040; printed +-0.020 1 sigma), grade C, source TT-131 (USGS OFR 91-183, 10.3133/ofr91183, Table 2; originates in Plummer and Busenberg 1982, not read). Role sensitivity; registered as the aragonite K2 input in configs/preprint/screen.yaml (PH-W4.2e). The older key log10_ksp_aragonite (-8.34, fixed, no width, TC-045) is not read by the screen; claims_redirect 11a still names it.

## K2 falsifiability controls (PH-W4.2e, dry run, 8192 draws)
Corner: Ca_T 1e-6 mol dm^-3, C_T = dic_slurry min, pH = ph_slurry_modified min. Calcite, aragonite, ACC: falsified, P_bad 1.0 (Omega < 1). Supersaturated control: feasible for all three. Carbonate regression: 34/34 and 4/4 within tolerance (max rel. diff 4e-16).

## Label rule
"nacre-type" only where aragonite AND calcite pass K2 (ACC reported, not required); otherwise "carbonate (calcite)". Verdict text: "thermodynamically suitable against dissolution (a necessary condition) for [phase] in [region]" (claims_redirect Section 11b).

## f_min and percolation (site, params keys)
p_c square 0.59274605809 (TT-132 10.1103/PhysRevE.78.031136; TT-133 10.1103/PhysRevE.64.016706); triangular 0.5 (TT-134); simple cubic 0.31160805 (TT-135, TT-136 10.1088/0305-4470/31/40/009).
f_min interval [1 - p_c_square, 1 - p_c_sc] = [0.4073, 0.6884]; triangular gives 0.5 as lattice sensitivity. K2h stays report-only.

## Scope guard
SG19 narrowed; SG28 (nacre-like architecture), SG29W (nacre-type needs aragonite in the sentence), SG30W (thermodynamically suitable needs for/in/under). Charter tests 17 pass.

## Conditions
(i) X1-X8 applied: NO. Evidenced: X1, X2, X5 (PH-W5.3), X3 (PH-W4.2c), X4, X8 (PH-C0, PH-W3.6), X7 (PH-W2.3, RW1 full text 403). X6 is not defined anywhere in the tracked files.
(ii) housekeeping: yes (copy test passes; Li+ rebuild test passes; deviations filed; manifest written).
(iii) aragonite + K2 controls: yes. (iv) scope guard committed: yes. (v) label text in claims_redirect: yes.

## strict verify: FAIL, 6 tests (1984 passed, 1 skipped); the 9 other checks pass or are inactive
1 test_fig_provenance[thresholds_screen_ph] and 2 test_figs_regime_set ladder labels: figs pin of thresholds.yaml stale (W6 re-pin).
3 test_lit_si_table: params_table.tex stale (embeds params sha 0ee35c055bac; W8 regen).
4-5 test_preprint_lint_scope (2): tests expect warn block SG17W/26W/27W; charter now adds SG29W/SG30W (linter support, PH-W8.2).
6 test_preprint_skeleton title macro: front.tex still has the old working title (PH-W8.2 regen).

## Questions
1. Confirm log10_ksp_aragonite_25c_i0 as the aragonite K2 input; 11a names the older key.
2. Low-dose corner pH end: pH at the ph_slurry_modified minimum. Confirm.
3. Rule: Li+ scale (TATB), Ca(PO3)2 glass-to-crystal bound, K_P concentration form.
4. Confirm the mapping excluded = falsified (D68).
5. PH-W2.5: aragonite at room temperature needs Mg2+ near Mg:Ca 5 or a cationic polyamine near pH 9; calcite 98 % at pH 12, no aragonite at any pH; aragonite only at 50 to 85 C. So "nacre-type" labels dissolution stability only; aragonite formation in an alkaline slurry is unsupported (NU19); alternating aragonite and calcite layers is not nacre-like (NU20). The paper says so plainly.
6. Left to rule at cp5b: f_min, Al polyphosphate Ksp, A_patch.
7. What is X6?
