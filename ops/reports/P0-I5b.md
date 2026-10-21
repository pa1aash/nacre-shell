# P0-I5b (integrator, day 5): BLOCKED, not pushed
1. Merges: w8 (18721b8) already in as f7f466e; w2 (eb73111) merged --no-ff as bd23541; only package text, report and state files differ; no pyproject or lock change.
2. The w2 merge clears the SG26W hits in preprint/package that failed the earlier strict run (5 retro tests); not re-run as a separate step.
3. `uv run nacre verify --strict` (one run, killed by hand after about 20 min): the output log stayed empty, the pytest child died by itself at about 10 min and verify then sat idle with no child and no report. No pass or failure list was produced, so strict verify is not a pass.
4. `uv run pytest -q tests/structures/test_structure_builders.py::test_no_clashes_in_committed` alone: exit 137 (SIGKILL), no output, twice (about 8 min each). It does not pass alone. Memory free was 36-60% at the time.
5. `uv run nacre verify --quick` on the merged head: PASS (8 pass, 1 inactive), so linters, scope guard, attribution, identity, signatures, ownership, frozen paths, provenance and basenames pass. The remaining blocker is the killed test (inferred, not shown by a strict report).
6. Not done per the push rule: packet update and zip rebuild, push, lane fast-forwards, track check PH-W4.2.
7. credit.tex gitignore item dropped: the repository has no such file and CRediT was removed from the guard.
8. Needs a ruling: run the clash test with more memory headroom or move it to a heavy marker (the test itself was not changed or skipped).
