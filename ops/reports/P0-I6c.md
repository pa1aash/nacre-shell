# PH-I6c: merge W4.2g, W6.2, W6.2b, W8.2, W8.2c, W2.6 (integrator) — BLOCKED before push

- Ledger (782b255): PH-W2.6, PH-W8.2c, PH-W6.2b added; done list extended (13 ids, PH-W1.7b and PH-W1.7c have no ledger entry and are listed only); D74 recorded.
- Merges (--no-ff, order w4, w2, w8, w6), no conflicts: w4 2345f00, w2 1964b36, w8 61bded5, w6 22bac43. The w4 head also moves version pins 8 to 9 in src/nacre/screen/ph_prov.py and three screen tests (part of PH-W4.2g).
- Pin check: upstream.yaml pins thresholds_screen_ph to sha256 37c17b67...cb61 and the file on this tree has that sha256. same_bytes is still false (origin holds v8); not rerun, nothing pushed.
- Deviation entries for thresholds.yaml, preprint/paper/** and claims.yaml, and the figures pins added (29a8dde).
- pytest (seven directories): 1449 passed, 1 failed, 1 skipped. Failure: tests/figs/test_fig_captions.py::test_requests_do_not_duplicate_defined_macros. NumRetroCorrect is requested in figures/src/captions/macro_requests.yaml (w6) and now also defined in preprint/generated/sources.yaml (w8, same source, key, format).
- Fix (delete the request, 438 figs and preprint tests pass with it) was refused by the lane-ownership hook: figures/src/captions is outside p0-int. Reverted; hook not bypassed. The fix belongs to a w6 session.
- verify --quick: PASS. Not pushed; lanes not fast-forwarded; track checks not run.
- w6 lane branch fast-forwarded to 6fab325 (pushed alone, no preprint/p0 push, no tag) so a w6 session can fix the duplicate NumRetroCorrect request on the merged tree.
