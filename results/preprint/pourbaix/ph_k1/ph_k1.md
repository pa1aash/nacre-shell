# PH-K1 tier 1: oxidation-limit ladder (experimental route, vs Li+/Li)

Gate: carbonate control 3.9378 V vs frozen 3.938 V (-0.18 mV); its budget 0.0870 V equals `window_margin_expt`. Onsets: a_w = 1, a_OH = 1, solid-salt LiClO4 sink (**upper bound on the onset**: *below* stands; *above (ub)* is not a pass, no solvated sink exists). Margin m is provisional.

| Phase | Limiting reaction | E_ox (V) +- m | DFT janaf/mp | 3.65 V | 4.2-4.3 V | 4.4-4.5 V |
|---|---|---|---|---|---|---|
| HAp | r1s (staged, to Ca2P2O7) | 4.067 +- 0.124 | 4.06/3.83 | above (ub) | below | below |
| beta-TCP | r1s (staged, to Ca2P2O7) | 4.022 +- 0.148 | 3.91/3.91 | above (ub) | below | below |
| alpha-TCP | r1s (staged, to Ca2P2O7) | 3.981 +- 0.165 | 3.93/3.93 | above (ub) | below | below |
| OCP | undetermined: r1, r1s | - | 4.60/2.77 | undetermined | undetermined | undetermined |
| brushite (precursor) | r3 (to H3PO4, protons taken up by the phosphate) | 4.266 +- 0.166 | 4.40/2.39 | undetermined | undetermined | undetermined |
| monetite (precursor) | r1 (to P2O5) | 4.698 +- 0.085 | 4.61/3.94 | undetermined | undetermined | undetermined |
| Ca2P2O7 | r1 (to P2O5) | 4.716 +- 0.102 | 4.25/4.25 | undetermined | undetermined | undetermined |
| Ca(PO3)2 | undetermined: r1 | - | 4.84/4.84 | undetermined | undetermined | undetermined |
| AlPO4 | r4 (Al3+ to the sink, anion to P2O5) | 5.211 +- 0.055* | 4.99/4.99 | undetermined | undetermined | undetermined |
| Al(PO3)3 | undetermined: r4 | - | 5.63/5.63 | undetermined | undetermined | undetermined |
| Li3PO4 (competing) | undetermined: r1, r1s | - | 4.03/4.03 | undetermined | undetermined | undetermined |
| CaSiO3 (cmp) | r1 (to SiO2) | 3.717 +- 0.086* | 3.70/3.70 | within | below | below |
| Ca2SiO4 (cmp) | r1s (staged, to CaSiO3) | 3.456 +- 0.094 | 3.52/3.52 | below | below | below |
| Li2SiO3 (cmp) | r1 (to SiO2, Li-open) | 3.632 +- 0.043* | 3.61/3.61 | within | below | below |
| CaCO3 (control) | r1 (to CO2); the registered carbonate reaction | 3.938 +- 0.087 | 4.32/3.71 | above (ub) | below | below |

`*` budget lacks a term (Al(ClO4)3 exchange entropy; quartz uncertainty). A phase with undetermined reactions shows the determined minimum only when it is already below the class. DFT: Materials Project 2026.09.28, BY-C, `dft-unbenchmarked`; CaCO3 DFT values are the frozen production ones.

**Clearing.** No phase passes at any class: a pass needs a solvated sink (keys are gaps). Upper-bound *above*: 3.65 V: HAp, b-TCP, a-TCP, CaCO3; 4.2-4.3 V: none; 4.4-4.5 V: none. Undetermined: OCP, brushite, monetite, Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3, Li3PO4.
**Reading.** The Ca orthophosphates fall at 4.07/4.02/3.98 V (staged release to Ca2P2O7), below the 4.2-4.3 V class and above the LFP class; carbonate sits at 3.938 V. AlPO4's determined reaction is 5.21 V but its staged route to Al(PO3)3 is untabulated (DFT comparator 4.99 V); Ca2P2O7's staged route to Ca(PO3)2 is untabulated (DFT comparator 4.25 V against 4.55 V for its full release). Silicates lie at 3.46-3.63 V, at or below the LFP class.

**Benchmark** (MP formation energy minus tabulated DfH, kJ/mol per formula unit; minus DfG is 40-260 kJ/mol more negative, see benchmark.csv): P2O5 -135; HAp -103; b-TCP -47; a-TCP -62; brushite -210; monetite -77; Ca2P2O7 -68; AlPO4 -68. DFT-minus-experiment onsets, same reaction: -1.08 to 0.60 V (median -0.05 V).

**Biggest gaps.** (1) Solvated sink: every onset is an upper bound. (2) Missing species make the reaction undetermined: Ca(PO3)2 and Al(PO3)3 (no data), Li3PO4 (DfG, S), and the staged routes through them. (3) a_w and the OH-site activity are grids (a_w = 1e-6 lowers a water-releasing onset by 0.02-0.05 V). (4) Brushite/monetite: a_w* = 1.15 (range 0.17-7.99), so brushite is at the dehydration threshold within the row uncertainties. (5) OCP rests on one DfG row (no DfH or S): undetermined; its information-only value is 3.87 V (r1s).

**Key requests for W1**
- `a_w_electrolyte`: a_w of the carbonate electrolyte
- `a_oh_site`: activity
- `solvation_ca_vs_li, solvation_al_vs_li (organic carbonate solvent)`: gaps at this params sha: without a solvated sink every onset is a solid-salt upper bound and no phase can pass at tier 1
- `exchange_entropy_bound_al_clo4_3`: entropy bound of the Al + 3 LiClO4 exchange
- `dfg_li3po4, s_li3po4`: Li3PO4 DfG and S
- `dfh_al_po3_3, dfg_al_po3_3, s_al_po3_3`: Al(PO3)3 has no thermochemistry: AlPO4's staged reaction and Al(PO3)3 itself are undetermined
- `dfh_ca_po3_2, dfg_ca_po3_2`: crystalline Ca(PO3)2
- `dfh_ocp, s_ocp`: OCP DfH and S
