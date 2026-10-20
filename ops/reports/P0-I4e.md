# P0-I4e: Day 5 lane merges, ledger, deviation entries
Status DONE. preprint/p0 pushed; `nacre verify --quick` PASS (8 pass, 1 inactive). No test suite, no full verify (as specified).
- Ledger (683a15a): PH-W5.2 (w5) and PH-W4.2b (w4) added to day 5, both Sonnet, requires []; D54, D55.
- Merges, all --no-ff, no conflicts, no extra commits: w3 80838c7, w5 ff316d3, w1 638d92e, w4 1a41c38, w8 eab883c. `uv sync -q` after each; uv.lock unchanged.
- Deviation entries (4, dated 2026-10-21, Re-audit: cp5 freeze): thresholds.md (W3.2a), contract.yaml (W3.2a, v5 to v6), thresholds.md (W3.2, block v6), lit/params.yaml (W1.3, 20 additive keys). ignorance_priors.md has no diff in these merges, so no entry.
- Lanes w1 to w6 and w8 fast-forwarded to e6c86f6 (7/7 clean); w7 untouched.
- Track check: PH-W5.2 OK (w5), PH-W4.2b OK (w4). First attempt BLOCKED on an untracked preprint/generated/credit.tex in both worktrees; removed it (regenerable, outside git) and both passed.
- Note: preprint/generated/.gitignore lacks credit.tex (dropped from the generator list at c76068c); the file reappears untracked and blocks track check. W8 to add the ignore line.
- Outstanding: test_committed_copy_equals_theory_thresholds still fails until PH-W4.2b (D45); 15 offloaded placeholder files not seen this session; equation-sheet table split; W1 transfer data and al_film_phase_rt_water; planning-chat items (PC proxy, LFP 3.65 vs 4.0 V, f_min).
