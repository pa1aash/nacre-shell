# Session report: PH-K1

Track p0, day 4, lane p0-w5. Branch `preprint/p0-w5`. Full results: `results/preprint/pourbaix/ph_k1/ph_k1.md` (ladder), `ph_k1.json` (every reaction, route, budget, row ids), `ladder.csv`, `benchmark.csv`.

**Status: DONE.** Tier 1 only; tier 2 is added later. Every number is a thermodynamic onset vs Li+/Li, not a rate.

- **Gate.** The carbonate control (CaCO3 + 2 LiClO4, experimental route) through the new generic code gives 3.937816 V against the frozen 3.938 V (inventory row 4; full-precision value 3.9378161596): difference 0.18 mV, tolerance 1 mV. Its budget 0.086978 V equals `window_margin_expt`. The gate is a test (`tests/pourbaix/test_ph_k1.py`, 14 pass). Committed first (`240617a`).
- **Method.** One reaction code for all phases (`src/nacre/pourbaix/ph_k1.py`): the phase plus LiClO4 goes to the perchlorate of its cations (tabulated exchange enthalpy, as the carbonate), the anion residue (P2O5, SiO2, a lower phosphate, CO2) and O2. Experimental route where every species has a tabulated DfG row (TR-* ids in `lit/evidence_table.csv`); Materials Project DFT (BY-C, janaf and mp schemes) beside it, labelled `dft-unbenchmarked`. Budget per reaction by the recipe of `window_margin_expt` (provisional, not a registered key).
- **Result.** The Ca orthophosphates start to oxidise at 3.98 to 4.07 V (staged release to Ca2P2O7): above the LFP class, below 4.2-4.3 V and 4.4-4.5 V, by tier 1 alone. Carbonate 3.938 V. Silicates 3.46 to 3.63 V. No phase can pass: the solvated sink is a gap, so each onset is a solid-salt upper bound. Undetermined: OCP, brushite, monetite, Ca2P2O7, Ca(PO3)2, AlPO4 (5.21 V on its determined reaction), Al(PO3)3, Li3PO4.
- **Benchmark.** MP formation energy minus tabulated DfH, kJ/mol per formula unit: HAp -103, beta-TCP -47, alpha-TCP -62, Ca2P2O7 -68, AlPO4 -68, brushite -210, monetite -77, P2O5 -135, silicates -21 to -41. Not a phosphate benchmark (PH-W5.1).

## Deviations and decisions
1. `lit/corpus/phosphate_coverage.yaml` does not exist on any branch. Row ids come from `lit/evidence_table.csv` (TR-001 to TR-119) and `lit/corpus/T-R/gaps.md`.
2. The Materials Project database is now 2026.09.28; the production cache is 2026.04.13. The PH-K1 cache is a separate book from one version and is never pooled with the old one. CaCO3 DFT comparators are the frozen production values. Raw entries are local (`.local/w5/cache_ph/`, sha256 in the committed manifest); 1296 entries, all BY-C.
3. OCP has one DfG row (no DfH or S): undetermined by the brief's rule; its information-only value (3.87 V) is in the json.
4. Staged reactions (to Ca2P2O7, Ca(PO3)2, Al(PO3)3, CaSiO3) are added to the three W3 classes because E_ox is a minimum; those that need an untabulated product are undetermined. a_w and the OH-site activity are grids (no params key); the reference state is a_w = a_OH = 1.
5. Al(ClO4)3 has no exchange-entropy bound and quartz no JANAF uncertainty: those budgets are flagged incomplete.

## Outstanding
Key requests for W1 are in `ph_k1.md`. Tier 2, the solvated sink, the phosphate benchmark (PH-W5.1). Ledger record appended to `jobs/ledger/p0-w5.jsonl`. No full suite, no verify (brief).

Next: PH-I4 (cp4 packet).
