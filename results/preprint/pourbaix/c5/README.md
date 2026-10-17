# C5 inputs for cp3 (P0-W5.3)

Written by `uv run python -m nacre.pourbaix.c5 --config results/preprint/pourbaix/config/c5.yaml`
at params `8bc15c8` (W1 P0-W1.3; the sha is in every file). The first C5 run of this session was at
`680a44b`; every R-slurry and Omega-fixture key is identical at the two shas, and the R-cell inputs changed
(cathode classes as W1's e_cell_max design axis, m_expt and m_E computed), so all of C5 was rerun at
`8bc15c8`. Both runs are in `jobs/ledger/p0-w5.jsonl`; the later records supersede. W4 implements the evaluators; nothing here is a verdict
of the study until W4's evaluators run on it. Thermodynamic proxies only; no rates.

| File | Content |
|---|---|
| `slurry/aCa<a>_CT<c>_Al<al>.json` | schema v2, one per (a_Ca, C_T, total Al): the Pourbaix diagram as the competing-phase and Al-phase baseline at fixed C(IV) (cp3 decision 2). Compact JSON. Water lines under `extensions.p0-w5`. |
| `slurry_summary.json` | per design point: decomposition energies against the DFT tolerance (the C5 edge), the Al baseline per total Al, the proxy control, F6, F7 |
| `slurry_c5_inputs.json` | the baseline in cp3 terms: tolerance, the calcite offset stated (Ksp bias -2.48 and edge shift, so the proxy is context), competing phases, Al phases, carbon-redox sensitivity |
| `../omega_control.json` | the falsifiability fixture for W4's Omega test (one dissolving, one supersaturated case; keys and row ids only) |
| `cell/<sink>.json` | schema v2, one per registered sink and the solvated sink, as `run_cell` writes them (`oxidation` is the lowest over the schemes, per the schema text); the governing route of cp3 decision 3 is in `cell_scheme_table.json` |
| `cell_summary.json` | the R-cell window under each scheme (as in P0-W5.2, rerun at this commit); its single cp2 F5 verdict is taken at the upper end of the class envelope (5.0 V), and the per-class verdicts in `cell_scheme_table.json` govern |
| `cell_scheme_table.json` | every scheme in one table: expt governing, janaf and mp as comparators with their B2 benchmark errors (+0.382, -0.233 V per electron), the corrected values, the margin of the governing route (m_expt = window_margin_expt for expt, m_E = window_margin for corrected DFT), and the verdict at the min, value and max of each of W1's cathode classes |

`../final/` holds the P0-W5.2 runs and stays as recorded in the ledger; its Fig 7 export
(`fig7_pourbaix_input.json`, `fig7_schema_check.json`) is no longer produced (lane note N12).
