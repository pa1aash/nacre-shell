# P0-I6b (integrator, day 6) DONE
- Ledger (ac2cbaa): PH-W4.2g and PH-W4.5 (pending, blocked on cp5b) added; D73 recorded.
- Merged --no-ff: w3 44d7b45, w1 d6635f2 (PH-W1.7 and PH-W1.7c; second merge of w1), w4 9842d94, w2 9b820c6; no conflicts, pyproject and uv.lock unchanged, no extra commits.
- Block v8 to v9 diff accepted by the planning chat chair (text-only entries; no number changed). Verified: key name, label text, revised_w37, regime_table, required_for_label: none, not_tested; version 8 to 9.
- Deviation entries: 3 (lit/params.yaml, thresholds.md and claims_redirect.md, new _ph result dirs), each with Re-audit: cp5b.
- `pytest -q tests/lit tests/charter tests/preprint`: 352 passed. The thresholds-copy test sits outside these dirs and was not run (expected to fail until PH-W4.2g).
- `nacre verify --quick`: PASS (check 6 provenance passes for lane W1 after PH-W1.7c).
- Lane fast-forward and track checks: see the END BLOCK.
