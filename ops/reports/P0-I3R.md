# Session report: P0-I3R

Integrator, branch `preprint/p0`, 2026-10-20. Merge and freeze the carbonate control, load the calcium-phosphate plan, open day 4.

## Preconditions
- Clean tree on `preprint/p0` at b0b6348 (equal to origin); tags g0, p0-cp1, p0-cp2, p0-cp3 present; `.venv` symlink to `~/.nacre-venvs/p-int`; nacre imports from `src`.
- Lane worktrees: w1 592c39b, w2 92b1292, w3 b391bb7, w4 d417d1f, w5 401ef6e, w6 b0b6348, w8 242644f clean. **w7 (2226beb) dirty**: modified `tests/structures/test_scene_config.py` and untracked `figures/blender/preview.py`; its head is not a HOLD state commit and its state file still reads P0-W7.3 DONE. Skipped by P5: not merged, not fast-forwarded, not edited. W7.4 is carried as HOLD.

## Merges (--no-ff, signed)
w3 01f55b4, w4 0f923b6, w1 c0aaab9, w5 78dbd5c, w2 6425286; w7 skipped (above). No conflicts; `pyproject.toml` and `uv.lock` unchanged by the merges.
One full pytest run after the merges: 1555 passed.
Later, verify found 5 failures in `tests/retro/test_retro_package.py`: the package metadata title no longer equalled the ledger title. The integrator may not edit w2 paths (lane-ownership hook), so the fix was a w2 commit (bb736f3, D38) merged again as 08ffea6.

## Deliverables
- Deviation entries (4) in `ops/tracks/p0_deviations.md`, dated 2026-10-20, each with "Re-audit: cp5 (carbonate control)": lit/params.yaml (W1.4), theory/thresholds.md (D27), theory/ignorance_priors.md and theory/contract.yaml, configs/preprint/thresholds.yaml.
- Fetch-log rows from the Day 3 reports (72 rows; fields a report does not state are marked so).
- Tag `p0-carbonate-control` (signed, annotated) at 4333dfd; `ops/reports/carbonate_control_inventory.md`.
- Freeze rule is data: `freeze:` block in `ops/tracks/p0.yaml` (tag p0-carbonate-control; results/preprint/**, ops/reports/P0-W*.md, preprint/retrodiction/results/**); tests added to `tests/test_track.py`. The fixed p0-cp3 list is removed from `track.py`.
- `nacre verify --quick` (all checks except the full pytest run), with tests.
- `ops/tracks/standing_rules.md`, `ops/tracks/redirect_plan.md`.
- Ledger: `retired:` block, cp4/cp5/cp5r/cp6, PH- days 4 to 7, decisions D34 to D40; day 4 opened carrying P0-W7.4.

## Judgement calls
- Also retired P0-W2.5, P0-W4.5, P0-W6.5, P0-W7.5 (successors on the retired days 4 and 5, not named in the brief's list).
- P0-I3 replaced by P0-I3R in the day 3 ledger (so the integrator state resolves).
- `DONE-PART1` added to the passing statuses of `nacre track` (D36: the W5.4 pod part is not run).
- Post-day operator items moved to days 8 to 11 and now require cp6.

## Checks
- `uv run nacre verify --strict` (after 08ffea6): PASS, 1563 passed, 1 skipped, 9 deselected; attribution, identity, signatures (verified), lane ownership, provenance, preprint linters, test basenames pass; number linter inactive by config. Report and state were added after that run.

## Outstanding
1. w7: dirty tree; the owner must commit or discard before w7 can merge (W7.4 HOLD).
2. The freeze block covers `results/preprint/**`; phosphate outputs written there need deviation entries. Put phosphate outputs elsewhere or change the block at PH-I5 (planned: tag p0-cp5 with phosphate paths).
3. `preprint/generated/front.tex` was not regenerated for the new title.
4. Patent route has no Lens token (gap for PH-W2.1).
5. Operator: send the scope-change notice and collect consent (incl. the line for Prof. Braun).
