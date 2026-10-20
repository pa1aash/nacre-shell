# P0-I4b (PH-I4b) integrator report, 2026-10-20

- Merged (--no-ff) preprint/p0-w1 d9b37f6 (PH-W1.2) as 25833ad and preprint/p0-w4 e83a737 (PH-W4.1) as 2b94ee0. No conflicts; no extra commits beyond reports and state.
- Full test suite not run (as specified). Known failure: test_committed_copy_equals_theory_thresholds (W3 v5 contract_version vs W4 copy); recorded in D45, not xfail, W4 copy not edited; the cp5 freeze regenerates it.
- Deviation entries (2026-10-20, "Re-audit: cp5 freeze"): lit/params.yaml (185 additive keys), theory/thresholds.md (contract_version 4 to 5). Commit 42136f5.
- Plan: "ROUTE LAYER (draft, pending ruling)" appended to ops/tracks/redirect_plan.md (96fdc11).
- Ledger: PH-W2.2a (w2, Sonnet, day 4) and PH-W3.2a (w3, Opus, day 5, requires cp4) added; PH-W4.2 set to Sonnet (PH-W4.3 already Sonnet); notes N35 to N38; decisions D45 to D48. No PH-W1.3 route session (D47).
- `nacre track status` runs; `nacre verify --quick` PASS (8 pass, 1 inactive).
- preprint/p0 pushed at d45bb95 (before this report commit). Lanes w1-w6, w8 fast-forwarded to d45bb95 and synced; w7 skipped (holds 2 own commits).
- `nacre track check PH-W2.2a` in the w2 worktree: OK.
- Outstanding: cp4 PASS; cp5 freeze (regenerate thresholds copy, apply scope-guard additions); route-layer ruling by the planning chat; w7 own commits.
