# PH-I6a: day-5 sessions recorded done, day 6 opened (integrator)

Status DONE. No computation; `uv run nacre verify --quick` only.
- **Why "not run".** `nacre track` derives a session's status from the lane state's `last_session`. W1, W4, W6 and W8 states moved on to sessions the ledger does not list (PH-W1.6c, PH-W4.2f, PH-W6.1c, PH-W8.1c), so every session on those lanes read as not run.
- **Mechanism.** No supported way to record a session done existed, so `nacre track` was extended minimally: a top-level `done:` list in `ops/tracks/p0.yaml` that `session_status` reads (used by status, the day-close check and open-day). Two tests added in `tests/test_track.py` (49 pass). No lane state file was edited.
- **Marked done (9 ids, 10 entries; PH-W6.1 is listed twice and left as is):** PH-W8.1, PH-W1.3, PH-W4.2a, PH-W6.1, PH-W4.2b, PH-W1.5, PH-W4.2d, PH-W1.6, PH-W4.2e. Each has a report under ops/reports/ and DONE in its lane's state-commit history (PH-W8.1 report also says DONE). D70 recorded.
- **Day 6 opened** with `--carry P0-W7.4`, accepted. Sessions: PH-W4.2, PH-W4.3, PH-W6.2 (moved from day 7), PH-W8.2, PH-W8.2b, PH-W2.2, PH-W6.3b, PH-I6. PH-W8.2 and PH-W2.2 now require nothing (were cp4). Session-to-session order (W4.3, W6.2, W8.2b, I6 after W4.2) is in each `note`, since `requires` takes checkpoints only. Day 7 keeps PH-W8.3, PH-W7.1, PH-W1.4, PH-W3.3, PH-I7.
- **Lanes** w1 to w6 and w8 fast-forwarded to d8df9f9; w7 skipped (not an ancestor, untouched). `track check` passes for PH-W4.2, PH-W8.2, PH-W2.2.
- Outstanding: the duplicate PH-W6.1 entry; older pending-looking sessions on closed days (e.g. PH-W1.1, PH-W4.1) are not in the done list.
