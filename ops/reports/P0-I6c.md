# PH-I6c: merge W4.2g, W6.2, W6.2b, W8.2, W8.2c, W2.6, W6.2c (integrator) — DONE

- Ledger (782b255): PH-W2.6, PH-W8.2c, PH-W6.2b added; done list extended; D74. PH-W1.7b and PH-W1.7c are recorded in the done list only (no ledger entries).
- Merges (--no-ff, no conflicts): w4 2345f00, w2 1964b36, w8 61bded5, w6 22bac43; then w6 0911e71 (PH-W6.2c) after the first pytest run found NumRetroCorrect requested by w6 and defined by w8. The w4 head also moves version pins 8 to 9 in src/nacre/screen/ph_prov.py and three screen tests (part of PH-W4.2g).
- Deviation entries added for thresholds.yaml, preprint/paper/** and claims.yaml, and the figures pins.
- pytest (seven directories): 1449 passed, 0 failed, 1 skipped. verify --quick: PASS. preprint/p0 pushed at 2e0f623 (before this report).
- Figure pin: upstream.yaml pins thresholds.yaml at sha256 37c17b67...cb61 and the file matches. The tool's comparison against the pushed state gives same_bytes true.
- The tool's output (branch preprint/p0, same_bytes true) was not committed: the lane-ownership hook refuses figures/src/schemas/upstream.yaml for p0-int. The committed registry still reads false; a w6 session reruns `pin_upstream.py --only thresholds_screen_ph` and commits.
- Lanes w1..w6 and w8 fast-forwarded to 2e0f623 (7 of 8; w7 skipped by rule). Track checks PH-W8.2b (w8 worktree) and PH-I6: OK.
