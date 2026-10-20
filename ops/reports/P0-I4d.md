# P0-I4d (integrator, day 5)
- Filed CP4 FIXES F1-F9 with owners and packet rulings 1-11 in ops/tracks/redirect_plan.md.
- charter/scope_guard.md: new `scope-guard-warn` block with SG17W; the existing `scope-guard` block is untouched. tests/charter needed no change (17 pass).
- Ledger: D53, lane notes N42-N46, PH-W2.2b (lane w2, Sonnet, day 5, requires []). p0-cp4 tag left as is.
- Renumbering: the brief named N39-N43, but N39-N41 already exist (PH-I4b, PH-I4c), so the new notes are N42 (W3.2a), N43 (W5.1), N44 (W1.3), N45 (W8.1), N46 (W4.2a).
- `nacre gate G0 --check` did NOT stay PASS: layer A FAIL, 2 failed / 1677 passed. One failure is the known D45 test (test_committed_copy_equals_theory_thresholds); the other was not identified (full suite is 25 min). The charter, lit, retro, figs and preprint-claims modules pass. The FAIL record in ops/gates/G0.md was reverted, not committed; the last recorded A-check stays PASS 2026-10-17.
- verify --quick PASS. preprint/p0 pushed (35dc3b8).
- Lanes w1-w6 and w8 fast-forwarded to 35dc3b8 (all clean, no live sessions); w7 skipped as instructed. track check PH-W2.2b OK in w2.
- Outstanding: identify the second G0 test failure; G0 layer A needs re-check by the integrator.
