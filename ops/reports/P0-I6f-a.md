# P0-I6f-a (integrator, day 6)
Merged preprint/p0-w4 (558f767, PH-W4.6) and preprint/p0-w8 (aff5366, PH-W8.2f) into preprint/p0 with --no-ff; no conflicts, no pyproject change, no uv.lock change.
Deviation entry for the ph3 results filed (Re-audit: cp6); PH-W4.6 and PH-W8.2f added to the done list in ops/tracks/p0.yaml.
pytest (lit, charter, preprint, physics, screen, retro): 1225 passed, 0 failed. tests/figs: 270 passed, 3 failed, 1 skipped (stale regime_table.csv pin; expected until W6.3c re-pins).
Failing: test_fig_provenance.py::test_snapshot_equals_the_owner_commit_where_git_has_it[regime_table]; test_figs_stability.py::test_fig15_agrees_with_the_regime_table_except_the_stale_rows and ::test_fig15_refuses_a_disagreeing_table_row.
verify --quick: PASS; regime-table --check: up to date. preprint/p0 pushed at 5fc613c before this report; fast-forward pushes to preprint/p0-w6 and preprint/p0-w8.
Lane worktrees are under ~/Desktop, not ~/dev. Fast-forwarded: w6, w8 (5fc613c). w1, w2, w3, w5 (8f7782d) and w4 (558f767) are unchanged: their lane branches were not in this chore.
No tag created.
