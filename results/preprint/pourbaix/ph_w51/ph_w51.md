# PH-W5.1: phosphate benchmark, Al passivation window, K1 ladder v2

Tier 1 only, 298.15 K, a_w = a_OH = 1; margins provisional; DFT = Materials Project 2026.09.28, comparator only. Files: benchmark_w51.csv, al_window.json, a_al3_oxide.csv, ladder_v2.csv, ph_w51.json.

## 1. Phosphate benchmark (MP 2026.09.28 minus tables, kJ/mol per formula unit; DfH basis)
| Phase | MP | DFT-DfH | per atom | Status | Cause |
|---|---|---|---|---|---|
| P2O5 | mp-562613 | -135 | -19.3 | dft-benchmark-failed | covalent P-O only: oxide correction over-corrects |
| HAp | mp-41472 | -103 | -4.7 | dft-benchmarked | within error (OH O corrected) |
| b-TCP | mp-531132 | -47 | -3.6 | dft-benchmarked | within error (ionic Ca-O) |
| a-TCP | mp-1197377 | -62 | -4.8 | dft-benchmarked | within error; alpha/beta order inverted (polymorph) |
| brushite | mp-24389 | -210 | -16.2 | dft-benchmark-failed | hydrate water given the oxide correction |
| monetite | mp-24390 | -77 | -11.0 | dft-benchmark-failed | acid HPO4: over-correction |
| Ca2P2O7 | mp-3531 | -68 | -6.2 | dft-benchmark-failed | P-O-P bridge: over-correction |
| AlPO4 | mp-5331 | -68 | -11.3 | dft-benchmark-failed | covalent Al-O/P-O framework: over-correction |
| Li3PO4 | mp-13725 | -30 | -3.7 | dft-benchmarked | within error (polymorph unstated) |
| LiPO3 | mp-29195 | -49 | -9.8 | dft-benchmark-failed | PO3 chains: over-correction |
| Ca(PO3)2 glass | mp-5680 | -125 | -13.9 | dft-unbenchmarked | glass vs crystal |
| gibbsite | mp-27540 | -88 | -12.5 | dft-benchmark-failed | three OH O corrected |
Shown MP numbers: `dft-benchmarked` = HAp, b-TCP, a-TCP, Li3PO4, Li2SiO3 (|error| <= 5.21 kJ/mol per atom, formation_energy_mae); every other MP number is a labelled comparator with its measured error (`dft-benchmark-failed`) or `dft-unbenchmarked` (DfG-only rows, glasses, Ca(PO3)2 and Al(PO3)3 crystals). The phosphate benchmark does not pass as a set; no DFT number decides a K1 row.
Spread: 47 to 210 kJ/mol over the PH-K1 set. Causes: MP2020 puts one oxide correction (-66.3 kJ/mol per O) on every O (lattice water, OH, covalent P-O, P-O-P); brushite exceeds monetite by -66.5 per lattice water; raw GGA underbinding falls from ~59 (ionic Ca-O) to 39 to 49 kJ/mol per O (P2O5, AlPO4, acid phosphates), so condensed and acid phases are over-corrected; alpha/beta-TCP order inverted (polymorph); glasses vs crystals; MP's P reference is mp-1198724, not white P (offset unquantified). **SI finding:** on one reaction DFT minus experiment runs -1.08 to +0.60 V (median -0.05 V, 32 reaction-scheme pairs).

## 2. Al-O-H passivation window (own speciation, tabulated ion data, pH 3 to 10, I = 0)
| Film solid (log K_s) | 0.1 mM | 10 uM | 1 uM |
|---|---|---|---|
| Al(OH)3 am (10.58) | 4.98-8.29 | 5.50-7.22 | none |
| boehmite (7.92) | 3.99->10 | 4.34-9.95 | 4.71-8.95 |
| gibbsite (7.74) | 3.93->10 | 4.27->10 | 4.64-9.13 |
| corundum (9.15) | 4.42-9.72 | 4.80-8.72 | 5.25-7.70 |
**Window: pH 5.0 to 8.3** (Al(OH)3 am at 0.1 mM, governing: the film is amorphous; chosen here, for PH-W3.2 to vet). Crystalline reference boehmite (grade A): 4.0 (3.7-4.2) to >10. Published: 4.5 to 8.5 (TR-090, grade D) and 4 to 8.5 at 0.1 mM (TR-091, grade C). Ion-data benchmark: aluminate DfG (TB-032) vs TI-022 + TB-026 +1.8 kJ/mol; boehmite TI-026 vs TB-033 -0.6 kJ/mol; gibbsite minimum at pH 6.2 (measured 5.9, microcrystalline, 1.7 log units more soluble).
R1 input (a_al3_oxide.csv): log10 a(Al3+) at pH 5 / 7 / 8.5 = -4.4 / -10.4 / -14.9 (am) and -7.1 / -13.1 / -17.6 (boehmite); slope -3 per pH; polyphosphate complexation leaves a(Al3+) unchanged (linear-chain constants a gap).

## 3-7. K1 ladder v2, tier 1 (V vs Li+/Li; E_ub solid-salt sink +- provisional margin; classes LFP/4.2-4.3/4.4-4.5)
| Phase | Stage | Crystalline E_ub | Amorphous E_ub | E_lb | Classes (cr; am) | Label |
|---|---|---|---|---|---|---|
| brushite | slurry | 4.266 +- 0.166 | und. | pending | ub+/within/within; und/und/und | gap |
| ACP | slurry | 4.022 +- 0.148 | und. | pending | ub+/below/below; und/und/und | gap |
| HAp | slurry | 4.067 +- 0.124 | und. | pending | ub+/below/below; und/und/und | gap |
| OCP | slurry | und. | und. | pending | und/und/und; und/und/und | undetermined in both framings |
| b-TCP | slurry | 4.022 +- 0.148 | und. | pending | ub+/below/below; und/und/und | gap |
| a-TCP | slurry | 3.981 +- 0.165 | und. | pending | ub+/below/below; und/und/und | gap |
| Li3PO4 | slurry | und. | und. | pending | und/und/und; und/und/und | undetermined in both framings |
| Ca2P2O7 | cell | 4.465 +- 0.331 | und. | pending | ub+/within/within; und/und/und | gap |
| Ca(PO3)2 / Ca-polyphosphate glass | cell | 4.966 +- 0.291 | 4.893 +- 0.135 | pending | ub+/ub+/ub+; ub+/ub+/ub+ | amorphous row governs (C4) |
| AlPO4 | cell | 5.211 +- 0.055 | und. | pending | und/und/und; und/und/und | gap |
| Al(PO3)3 | cell | und. | und. | pending | und/und/und; und/und/und | undetermined in both framings |
| Al-polyphosphate (R1 gel) | cell | und. | und. | pending | und/und/und; und/und/und | undetermined in both framings |
| (LiPO3)n Hydro-Quebec film | cell | 5.021 +- 0.120 | 4.984 +- 0.248 | pending | ub+/ub+/ub+; ub+/ub+/ub+ | both framings reported (structure unspecified) |
| baked aluminophosphate (Tsinghua) | cell | 5.211 +- 0.055 | und. | pending | und/und/und; und/und/und | gap |
| CaSiO3 | comparator | 3.717 +- 0.086 | und. | pending | within/below/below; und/und/und | amorphous: not registered |
| Ca2SiO4 | comparator | 3.456 +- 0.094 | und. | pending | below/below/below; und/und/und | amorphous: not registered |
| Li2SiO3 | comparator | 3.632 +- 0.043 | und. | pending | within/below/below; und/und/und | amorphous: not registered |
| CaCO3 | control | 3.938 +- 0.087 | und. | pending | ub+/below/below; und/und/und | control: frozen value governs the gate |
Matrix rungs (C6, tier 2 only): chitosan, polydopamine, chitosan-polyphosphate complex: gap, matrix-risk flag (no tier 2 record at W1.2; polydopamine is the stated K1 risk, contrary B4); never a tier-1 number. Not run: Ca-modified aluminophosphate (no Ca-Al phosphate data).

**F3(a) Ca(PO3)2:** DfG(crystal) = -2295.2 +- 40.4 kJ/mol (glass DfH TR-032 minus h_vit 15.9, u 31.8 inflated x2 from LiPO3/NaPO3 glass-crystal pairs; S0 TR-031; JANAF white P, alpha Ca, O2); glass -2281.1 +- 10.3. It makes Ca(PO3)2 (4.97/4.89 V) and the staged Ca2P2O7 route determined. **F3(b) Al(PO3)3:** undetermined (search logged in ph_w51.json; DFT 5.63 V stays a comparator).
**Conversion steps (a_w*):** brushite->monetite 1.15 (0.17-7.99); monetite->Ca2P2O7 15.1 (0.24-940); Ca2P2O7 + H3PO4 -> Ca(PO3)2 9.6e-05 (5.8e-11-160); AlO(OH) + H3PO4 -> AlPO4 5.92e+04 (2.4e+03-1.48e+06); coacervate->glass, AlPO4->Al(PO3)3, R1 gel: undetermined. Literature conversion temperatures: pending PH-W1.3 (no rows); beside them the 100 to 350 C cure of US 8,252,463 (novelty BL3) and the 150 C dry of US 6,485,866 (BL1).
**Bracket (F2):** bracket pending PH-W1.3: hydration_free_energy_clo4 at origin/preprint/p0-w1 (35dc3b8). Convention when computed: Li+/Li with Li+ hydrated in the same solvent; anion term ClO4-(aq).
**Carbonate (F7):** expt 3.938 V (frozen gate unchanged); DFT 2026.09.28 janaf/mp 4.320/3.705 V against frozen 2026.04.13 4.320/3.705 V.
**Reading.** No row passes (no solvated sink). Ca orthophosphates stay below 4.2 V (ub). Condensed phases sit above every class on the upper bound: Ca(PO3)2 crystal/glass, (LiPO3)n crystal/glass; Ca2P2O7's staged route (4.47 V) is within the 4.2-4.5 V margins. AlPO4 and every Al(PO3)3 or Al-polyphosphate row stay undetermined. No row is 'requires crystallisation'. (LiPO3)n: K2 expected fail (water-soluble; composition-based inference).
