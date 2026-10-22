# P0-I5d: cp5 closure (integrator)
Status BLOCKED (resumed: w8 c878f70 merged at dcf350c). preprint/p0 local only (not pushed); tag p0-cp5 not created; lanes not fast-forwarded; day 6 not opened.
- Merges: w4 6f3d678 (1eb77f8: PH-W4.2e, PH-W4.2f), w2 dcaf0cd (3cca9c7: PH-W2.5); no conflicts, no extra commits beyond reports and state. Deviation entries 7ebb4b3 (three, each Re-audit: cp5b). Manifest 46f9ce8.
- Conditions: (i) yes (X6 = acceptance of W3 rulings (a), (b), PH-W3.2 and passivation_window_v3.csv, supplied by the planning chat; X1-X5, X7, X8 evidenced); (ii) yes; (iii) yes; (iv) yes; (v) yes.
- Manifest: block v8 sha256 d92b42e9... equal; ladder_v3.csv sha256 595636ef... equal; ladder_v3_sens40.csv is byte-identical to ladder_v3.csv (flagged in the note).
- strict verify (once, 1185 s of tests): FAIL, 6 tests failed, 1984 passed, 1 skipped; other checks pass (number linter inactive).
  Failures: figs pin of thresholds.yaml (2: test_fig_provenance[thresholds_screen_ph], test_figs_regime_set ladder labels); params_table.tex stale (test_lit_si_table); lint_scope warn block expects SG17W/26W/27W (2); front.tex working title (test_preprint_skeleton). Lane work (W6 re-pin, W8 regen and linter, PH-W8.2); not fixed here.
- Resume: after merging w8, the previously failing files give 3 failures: figs pin of thresholds.yaml (2, lane W6; pinned ef87a276..., file 48d99f42...) and params_table.tex stale (1, lane W1; embeds 2f1fa4f78196, params.yaml 0ee35c055bac). The lint_scope and title failures are cleared by w8. No push, no tag.
- Hang rule: strict verify's log stayed empty for over 10 minutes (verify prints its table only at the end); pytest CPU time kept advancing, so the run was not stopped. Deviation from the rule, recorded here.
- Note: ops/packets/p0-5a2_note.md (54 lines).
- Disk free after uv cache clean: 12Gi of 228Gi (df -h /). My keep-awake (pid 19459) stopped; other caffeinate processes on the machine are not mine.
- Lane sync: merged origin/preprint/p0-w6 (91d7bf0, report and state only) as 6a9f193; pushed 6a9f193 fast-forward to preprint/p0-w6 and preprint/p0-w1 (w1 had received 66f2e6e first); worktrees ~/dev/nacre-shell-p-w6 and -w1 fast-forwarded to 6a9f193. preprint/p0 not pushed, no tag.
