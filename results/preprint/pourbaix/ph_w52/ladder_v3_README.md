# ladder_v3.csv (PH-W5.2): K1 ladder v3, tier 1, V vs Li+/Li

Tier 1 only, 298.15 K, a_w = a_OH = 1, E_ub with the solid-salt LiClO4 sink. One row per (phase, framing, stage, reaction); a
row with `reaction_id` = `ALL` aggregates the reactions of one (phase, framing, stage). Conversion-step and matrix rows are kept
(`reaction_id` = step text or `-`). Columns, in this order, are fixed for W4's reader.

| column | meaning |
|---|---|
| phase, framing, stage | ladder entry; framing crystalline or amorphous; stage slurry, cell, comparator, control or conversion |
| reaction_id | r1, r1s, r3, r4 ... as registered; `ALL` aggregate; `-` no reaction |
| route | experimental route and margin rule (`expt route, m_K1`; `glass margin rule`), `gap`, `aggregate`, `conversion step`, `matrix` |
| E_ub_V | oxidation onset upper bound, V (aggregate: the reaction with the smallest E_ub + m) |
| E_lb_V | `pending` in every row (the bracket lower bound is not computed) |
| margin_V | registered margin m, V; empty where the budget is incomplete or the margin is symbolic |
| budget_status | `complete`, `incomplete` (a species lacks an uncertainty or bound), `symbolic: <reason>`, `gap`, `not run` |
| benchmark_status | the PH-W5.1 benchmark label of the phase; any DFT value appears only here, as a comparator with its measured error |
| k1_class_lfp, k1_class_42_43, k1_class_44_45 | verdict at the classes LFP-class (3.65 V), 4.2-4.3 V (4.2 to 4.3 V), 4.4-4.5 V (4.4 to 4.5 V) |
| k1_verdict | overall: falsified at every class = falsified; any pass = pass; otherwise undetermined if a class is undetermined and none falsifies; otherwise inconclusive |
| row_ids | the ph_w51/ladder_v2.csv row this row refines |
| notes | limiting reaction and crossover, ruling applied, reasons for undetermined, by-bound readings (not verdict bases) |

Units: V for E_ub_V, E_lb_V, margin_V; kJ/mol in notes.

## Verdict rules (claims_redirect 2c and 2e; margins from block v6, none chosen here)
- Per reaction and class: **falsified** if E_ub + m < inf(class); **pass** only if E_lb >= sup(class) + m (impossible while E_lb is
  pending); **undetermined** if the budget is incomplete, the margin is symbolic or the route is missing (a partial margin can neither
  pass nor falsify); otherwise **inconclusive**. A class is falsified at its lower end, so a class straddling E_ub + m is inconclusive.
- A row whose budget_status is `incomplete` cannot falsify: a class that would read falsified reads undetermined, and the notes say so
  (PH-W5.2b; applies to the reaction rows; the aggregate follows the rule below).
- ACP is the amorphous slurry-stage row, undetermined (no amorphous thermochemistry); the beta-TCP crystalline value is kept as the
  labelled reference rows `ACP, crystalline` (route and notes say reference).
- Aggregate (`ALL`) rule (PH-W5.3 X1): the aggregate of a (phase, framing, stage) is falsified at a class if and only if some
  complete-budget reaction row of that group is falsified there (E_ub + m < the class edge). Incomplete-budget rows are
  undetermined on their own and never rescue a phase, so they cannot lift a falsification by a complete row. Where no complete row
  falsifies, the aggregate is undetermined if any reaction is undetermined, otherwise inconclusive.
- Amorphous rows: margin from the glass data where block v6 has it (Ca(PO3)2 glass, LiPO3 glass); every other amorphous row has a symbolic
  margin (m_am = m_cr + u/(n_e F), correction a gap) and is undetermined. The block's by-bound readings are in notes only.
- DFT values never decide a verdict (no phosphate reaction qualifies for m_E).

## Margin source
`theory/thresholds.md` at `origin/preprint/p0-w3`: blob `b95f988dfc81763a12da29c278f47c029bebc668`, last changed in `c2c7882af0c7913bd17432157a43a3aca953dff4` (ref tip `e6c86f6b3633248b487f78eeef1acdccfa5be35c`);
sha256 of the extracted margins_v6 block `13bdaf545e6b105875829f3aeada38bf7c1df9d41208bbacb5fe9f81cfd2347b` (copy: margins_v6_block.yaml). Margins are read from the block, not typed.

## Ruling (b)
Crystal Ca(PO3)2 reference row only: direct value 18.87 +- 20.74 kJ/mol, E_ub 4.9664 -> 4.9818 V,
m 0.2907 -> 0.1900 V. The glass row is unchanged. PH-W5.3 X2: the staged Ca(PO3)2 crystal of the Ca2P2O7
r1s row takes the same direct value (the analogue-based staged value is replaced); the Ca2P2O7 r1s row and its `ALL` row are recomputed
(E_ub 4.4651 -> 4.4497 V, m 0.3315 -> 0.2308 V), still inconclusive at every class. The block copy keeps the block's own value.

## F2 bracket status
E_lb is pending: `hydration_free_energy_clo4` is absent at origin/preprint/p0-w1 and the Ca2+ and Al3+ transfer free energies to the cell
solvent are gaps (W3 ruling 10c), so no pass is possible and no row is registered as feasible.

## Passivation window (passivation_window_v3.csv, ruling a)
Governing row Al(OH)3 am (film phase: inferred amorphous), reference boehmite, gibbsite and corundum beside, at 0.1 mM, 10 uM and 1 uM.
The numbers equal PH-W5.1 (al_window.json, a_al3_oxide.csv); no a_al3_oxide.csv v2 is needed.
