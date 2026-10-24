# PH-I6g: day-6 integrator sessions recorded done, day 7 opened, requirements corrected (integrator)
Status DONE. No computation; `uv run nacre verify --quick` PASS.
- Only PH-I6 and PH-I6e still blocked day 6. Each has a report reading DONE, a DONE state commit (73ce44e, 8f7782d) and is on origin/preprint/p0. Both added to the done: list; D81 recorded.
- `track open-day 7 --carry P0-W7.4` accepted (eea10f8); no other session named.
- D82: requires cp5r changed to cp5b for PH-W8.3, PH-W7.1, PH-W1.4, PH-W3.3 (the only four naming cp5r); the cp5r definition is kept and marked superseded by cp5b. The tag p0-cp5r was not created.
- Code: src/nacre/cli/commands/track.py derives the tag as <track>-<cp>; no hardcoded list, so data only. cp5b has no entry in the checkpoints block (not needed by the check; not added).
- Lanes w1 to w6 and w8 fast-forwarded to d905e60 and synced; w7 untouched. `track check` PH-W8.3, PH-W1.4 (w1), PH-W3.3 (w3): all OK.
