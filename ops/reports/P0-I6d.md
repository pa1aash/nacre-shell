# PH-I6d: merge W1.8 and W4.5, cp5b deviation entries, ledger (integrator) — BLOCKED before push

- Ledger (4155390): PH-W1.8, PH-W8.2e, PH-W6.3, PH-I6e, PH-W4.6 added; PH-W4.5 note set to DONE; D76 to D78; PH-W1.8 and PH-W4.5 in the done list.
- Merges (--no-ff, no conflicts): w1 0a1d886 (c7274fb), w4 09e4a10 (a2d3ef2). Deviation entries (2dad38a): params.yaml, *_ph2 results, the symbol_bindings hash difference (4d6517f1 is the file at 1eb77f8; 416c954b at 8073c8e and now), the control rule; each with "Re-audit: cp6".
- pytest (seven directories): 1460 passed, 5 failed, 1 skipped. `nacre verify --quick`: PASS.
- Failures, all from the PH-W1.8 params.yaml change (sha f7c109d848ae, was ecc27194534a):
  1. tests/lit/test_lit_si_table.py::test_committed_tables_are_current: lit/corpus/si_table/params_table.tex line 1 and conflicts_table.tex record sha 7b2b1fbafde8, W1 committed them before its last params edit. Also fails in the w1 worktree at 0a1d886. Fix: `uv run python -m nacre.lit.si_table` (hash-only diff). Lane W1.
  2. tests/screen/test_screen_gap_table.py: `p_total_slurry_h3po4_window: no registered treatment`. Fix: one name in post_cp3_accounted of configs/preprint/gap_resolution_ph.yaml. Lane W4.
  3. to 5. regime table stale (test_regeneration_is_byte_identical, test_every_cell_traces..., test_generated_files_are_git_ignored_not_tracked): preprint/generated/regime_table.json records the old params sha. Fix: regenerate in PH-W8.2e, which changes that generator.
- I tried fixes 1 and 2 on the integrator branch; the lane-ownership hook rejected the commit (lane p0-int may not edit those paths). Reverted; nothing bypassed.
- Not done: push, lane fast-forwards, track checks of PH-W8.2e and PH-W6.3. w4 worktree has an uncommitted change to results/preprint/screen/k2_perph_ph2/perph.csv (not touched).
