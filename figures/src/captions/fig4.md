# Fig. 4 caption draft

Built from W2's retrodiction record `preprint/retrodiction/results/results.json` (P0-W2.3), pinned with its commit and sha256 in `figures/src/schemas/upstream.yaml` (`retro_results`). Numbers in the draft are macro names only (rule R5); the macros W8 has to add are in `figures/src/captions/macro_requests.yaml`.

## Draft

**Fig. 4** (a) Predicted barrier difference, test minus reference (median, \NumRetroIntervalLevel interval), for \NumRetroUsableCases same-study orderings grouped by input interface (γ_sn, net energy, γ_sl). Circle: correct; square: incorrect; open diamond: inconclusive (RC04); triangle: observed ordering. (b) Correct counts with inputs shuffled within (solid) and across studies (dashed), median \NumRetroNullMedian, range \NumRetroNullLow to \NumRetroNullHigh; line: observed count.

## Checklist (R4, R5, R7)

- Physical claim: the model orders the surfaces as observed where the input acts on the template–nucleus contact (γ_sn) and mostly fails where it acts on the template–liquid interface (γ_sl); the retrodiction falls short of its registered pass count.
- The two nulls have the same median and range in the record (a test guards this sentence).
- The swap check is stated, not drawn. No legend or in-axes text; keys are here.
