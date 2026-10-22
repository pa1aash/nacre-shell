# P0-I5d: cp5 closure (integrator)
Status DONE. Tag p0-cp5 (signed) on 1682411; preprint/p0 pushed at 1682411.
- Merges: w4 6f3d678, w2 dcaf0cd, w8 dcf350c, w6 report-only 6a9f193, w1 3e532f5 (PH-W1.6c), w6 b7f805b (PH-W6.1c). The w1 merge also carried a provenance ledger line and conflicts_table.tex (regeneration outputs). Deviation entries 7ebb4b3 (three, Re-audit: cp5b).
- Conditions (i) to (v): all yes; X6 = acceptance of W3 rulings (a), (b), evidence P0-W3.PH-W3.2.md and passivation_window_v3.csv.
- same_bytes for thresholds_screen_ph checked on this tree: HEAD blob and e85e890 both sha256 48d99f42...; true.
- Tests: tests/figs tests/lit tests/preprint tests/charter 572 passed, 1 skipped. `verify --strict` (once, final): full PASS, 1994 passed, 0 failed, 1 skipped; number linter inactive. The earlier strict run failed 6 tests (lane pins and regenerated outputs), fixed by w8, w1, w6.
- Hang rule: strict verify prints its table only at the end; empty log for the first 10 minutes while pytest CPU advanced; not stopped (first run).
- Manifest ops/packets/p0-5a2_hashes.txt re-hashed; no earlier hash changed, two rows added (params_table.tex, figures upstream.yaml). Note ops/packets/p0-5a2_note.md (49 lines).
- `verify --quick` PASS. Lanes w1 to w6 and w8 fast-forwarded to 1682411 (7/8; w7 skipped by instruction).
- Day 6: NOT open. `nacre track open-day 6` (also with --carry P0-W7.4) refuses: day 5 is not complete in the track ledger; ten sessions show "not run" (PH-W8.1, PH-W1.3, PH-W4.2a, PH-W6.1 twice, PH-W4.2b, PH-W1.5, PH-W4.2d, PH-W1.6, PH-W4.2e) although their lane reports exist. Carrying them would break the rule to carry only DONE items; planning chat or the track ledger needs to mark them. State stays day 5.
- Disk free after uv cache clean: 12Gi used, 20Gi free of 228Gi (df -h /). Keep-awake stopped.
