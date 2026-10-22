# P0-I6b (integrator, day 6) BLOCKED
- Ledger (ac2cbaa): PH-W4.2g and PH-W4.5 (pending, blocked on cp5b) added; D73 recorded.
- Merged --no-ff in order w3 44d7b45, w1 44e574a, w4 9842d94, w2 9b820c6; no conflicts, pyproject and uv.lock unchanged, no extra commits.
- Block v8 to v9: no numeric value, margin, class edge or interval changed. Changes go beyond names and labels: key name and label text, plus new text-only entries (revised_w37 note, regime_table vocabulary/footnote/kinetic note/acid-adjusted row, required_for_label: none, not_tested). Reported as "other"; the numbers rule did not trigger.
- Deviation entries: 3 (lit/params.yaml, thresholds.md and claims_redirect.md, new _ph result dirs), each with Re-audit: cp5b.
- `pytest -q tests/lit tests/charter tests/preprint`: 352 passed. The thresholds-copy test sits outside these dirs and was not run (expected to fail until PH-W4.2g).
- `nacre verify --quick`: FAIL, check 6 provenance: p0-w1.jsonl:24 hash mismatch lit/corpus/gaps.md. The line (PH-W1.7 merge, code_commit de7afaa) records sha256 673017c0...; the file at w1 head f1a8061 is fe2bfc3a.... The merged blob equals the w1 blob, so the mismatch comes from the lane, not the merge.
- Not pushed; lanes not fast-forwarded; track checks not run. Local preprint/p0 is ahead of origin.
- Needs a ruling: re-record the ledger line (new line from w1) or regenerate gaps.md, then verify --quick and push.
