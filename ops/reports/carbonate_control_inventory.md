# Carbonate control inventory

Session P0-I3R, 2026-10-20. Tag `p0-carbonate-control`. Every number below is copied from the named report section; none is typed from memory. Status values: **sourced** (stands on sourced inputs), **conditional** (conditional on the binding-constant analog `log10_k_ca_catecholate` and on admissibility), **gap** (no value or no verdict in the reports).

The sha column is the last commit that touched the source document, as merged on `preprint/p0`.

| # | Carbonate result | Source document | sha | Report section | Value copied | Status |
|---|---|---|---|---|---|---|
| 1 | Voltage bound, CaCO3 with LiClO4 | `ops/reports/P0-W4.3b.md` (from P0-W4.3, P0-W5.3) | d417d1f | Comparison table, "R-cell, C5c per cathode class"; P0-W4.3 line "E_ox(expt) = 3.938 V" | Falsified for every cutoff above 4.025 V; E_ox(expt) 3.938 V; solid-salt pass (inconclusive) at or below 3.851 V (P0-W5.3); no pass possible, the solvated sink is a gap | sourced (solid-salt sink bounds the onset only) |
| 2 | Cell verdicts per cathode class | `ops/reports/P0-W4.3b.md` | d417d1f | "R-cell, C5c per cathode class (unchanged from P0-W4.3)" | LFP: min inconclusive, value inconclusive, max falsified. Layered NMC/NCA, LCO, LMO, LNMO: falsified, falsified, falsified | sourced |
| 3 | Gas-reference benchmark (CO2/O2 schemes) | `ops/reports/P0-W5.2.md`; `results/preprint/pourbaix/gas_reference.md` | baf16ff; fa04a9c | Task A | janaf overestimates by about +70 kJ/mol (+0.38 to +0.39 V per electron); mp underestimates by about −45 to −65 kJ/mol (−0.22 to −0.23 V per electron); B2 +73.8 (+0.382 V) janaf, −44.9 (−0.233 V) mp; B6 experimental equilibrium 3.823 V vs Li+/Li for Li2CO3 oxidation | sourced |
| 4 | Oxidation onsets, LiClO4 sink (expt / janaf / mp) | `ops/reports/P0-W5.4.md` | 401ef6e | Part 1a table | CaCO3 3.938 / 4.320 / 3.705 V; boehmite 4.751 / 4.828 / 4.605 V; corundum 4.706 / 4.670 / 4.670 V. LiBOB, LiPCP undetermined; solvated: gap | sourced for LiClO4; gap for the other sinks |
| 5 | Slurry dissolution window (C5s) | `ops/reports/P0-W4.3b.md` (Verdicts); `ops/reports/P0-W4.3.md` (C5s) | d417d1f; 5483aec | Verdicts; P0-W4.3 C5s | Feasible for Ca_T >= 1e-4 mol dm⁻³, falsified at 1e-6 and at 1e-5 with C_T min, otherwise inconclusive at 1e-5. Dose window: 24 feasible, 8 falsified, 4 inconclusive of 36 points (P0-W4.3) | sourced (Ω_bulk from sourced speciation and calcite K_sp) |
| 6 | Falsifiability controls of the window | `ops/reports/P0-W4.3.md` | 5483aec | "Ω controls", C5s_phase | The undersaturated control reports dissolution and the supersaturated control reports stability. C5s_phase feasible (worst point 0 eV per non-O, non-H atom, edge 0.124 eV) | sourced |
| 7 | Boehmite window | `ops/reports/P0-W5.4.md`; `results/preprint/pourbaix/supplement_d3` | 401ef6e; fd3d223 | Part 1a | Reduction 2.155 V (expt; Li-open DFT 1.747 V); oxidation 4.751 / 4.828 / 4.605 V (expt / janaf / mp); verdict inconclusive for every cathode class (no budget key); margins 0.149 V (LNMO) to 0.551 V (LFP); dehydration threshold p(H2O) = 2.9 × 10⁻⁵ bar, a_w = 8.9 × 10⁻⁴ | sourced onset; verdict gap |
| 8 | Corundum window | same | 401ef6e; fd3d223 | Part 1a | Reduction 1.221 V (Li-open DFT; no expt route); oxidation 4.706 / 4.670 / 4.670 V; verdict inconclusive for every cathode class; margins 0.106 V (LCO) to 0.506 V (LFP) | sourced onset; verdict gap |
| 9 | CaCO3 reduction limit | same | 401ef6e | Part 1a | 1.776 V (expt; Li-open DFT 1.623 V); margin below which reduction would be feasible 1.024 V; no reduction budget key | sourced |
| 10 | Retrodiction | `ops/reports/P0-W2.3.md`; `preprint/retrodiction/results/` | 6d3bdc2; 2a1f386 | Outcome against the pre-registered rule | 7 of 12 correct; rule (>= 10 of 12) FAIL; misses RC07, RC08, RC09, RC11 incorrect, RC04 inconclusive; permutation null median 5 (central 95 % [2, 8]); reported unchanged | sourced (failed rule; nucleation half not validated) |
| 11 | Admissibility sequence (D27) | `ops/reports/P0-W3.4b.md`; `ops/reports/P0-W4.3b.md` | b391bb7; d417d1f | "The sequence in one plain sentence"; Comparison table | Template-liquid energy negative on every draw under the analog; admissibility condition derived without consulting further screen output; registered as a prior restriction with excluded mass reported; rerun. C3 falsified 24, inconclusive (inadmissible) 12 of 36 points; study falsified 72, inconclusive 36 of 108; unrestricted rerun reproduces falsified 36/36 and 108/108 | conditional |
| 12 | C4 (thin film) | `ops/reports/P0-W4.3b.md` | d417d1f | "C3 and C4 under the rule" | Inconclusive at every point: spreading route fails, closure route a gap (d_max) | gap |
| 13 | Deletion test | `ops/reports/P0-W4.3b.md` | d417d1f | Comparison table | Fails everywhere (bare_oxide not degraded versus template; PVDF a gap) | conditional |
| 14 | Parameter additions behind the control | `ops/reports/P0-W1.4.md` | 592c39b | Deviation entry | 20 additive keys; n_req = ln(1/(1 − p_cred))/A_patch, value null while patch_area is a gap | sourced / gap per key |

## Reading rules for the paper

- Rows 11 to 13 are conditional on the binding analog; cite them only with that label.
- Rows 7, 8 and 9 give onsets, not verdicts; no budget key exists for the Al phases.
- Row 10: report 7 of 12 in the SI and one sentence that the nucleation half is not validated.
