# PH-I3b report (integrator, day 4)

Status: BLOCKED. Merges, freeze rule, ownership and decisions are committed locally; nothing is pushed.

- Merges (no-ff, no conflicts, extra commits were reports/state only): w3 6c10918, w1 94af130, w2 0a10434.
- Freeze rule (cebfb88): `freeze_problems` counts only M/D/R of files existing at the tag; 3 new tests; tests/test_track.py 47 pass.
- Ownership: p0-w1..w8 own ops/reports/PH-W<N>.*.md, p0-w5 also PH-K1.md; 2 new tests in tests/test_track_lanes.py (hook accepts PH-K1 on w5, rejects on w1).
- Decisions D41, D42 added to ops/tracks/p0.yaml.
- Checks: `pytest -k "track or lane or freeze or ownership"` 146 pass. `nacre verify --quick` FAIL on check 6 (provenance only; checks 1-5, 7-9 pass).
- Cause: jobs/ledger/p0-w1.jsonl line 11 (`nacre.lit merge --ledger P0-W1.4`) records hashes for lit/evidence_table.csv, lit/corpus/coverage.yaml and lit/corpus/gaps.md. W1's commit 8137752 (T-R rows) changed all three without appending a new ledger record. At 168bbea the hashes matched.
- Fix: the W1 lane reruns the lit merge with its PH-W1.1 ledger id and commits the new ledger line (jobs/ledger/p0-w1.jsonl is outside the integrator's paths, so it is not patched here).
- Not done because the push is gated on verify: push of preprint/p0, lane fast-forwards (w1..w8), `track check PH-K1` in w5.
