# Brief: Results

- **File:** `sections/results.tex`.
- **Written:** PH-W8.3 (day 7), after cp5r. Structure only at PH-W8.1: no result is stated in this brief.
- **Length target:** 1900 to 2500 words, six subsections, four figures-with-panels and two tables in the text.

## Purpose

Report what the screen gave, per cutoff class and per stage, in an order in which each result rests on the previous one. Every number is a macro. Whatever is undetermined is reported as undetermined, and a verdict is never stated without its STAGE.

## STAGE field and the results table (F4)

Every results row carries a STAGE field.

- **slurry-stage** (brushite, ACP, HAp): K2, K3, K4 apply; the K1 column is shown as the phase's own ceiling if it were retained unchanged and is not a gate for this stage.
- **cell-stage** (Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3): K1 applies; K2 to K4 are replaced by a pointer to the route criteria (hydrolysis, formation, wetting).
- **conversion-step rows**, one per precursor-to-cell-stage pair, between the two blocks: precursor, cell-stage product, thermodynamic dehydration or condensation threshold in the water activity (a_w*), literature conversion temperature, and the cure range of the baked baseline beside it (macros `NumCureLow`, `NumCureHigh`, planned). Indicative pairs, to be fixed by PH-W5.1: brushite to Ca2P2O7 (via monetite); a Ca dihydrogen phosphate to Ca(PO3)2; Al phosphate precursors to AlPO4 and Al(PO3)3.
- Columns of `tab:candidates`: phase; STAGE; framing (amorphous, crystalline, both); K1 per cutoff class (upper bound, lower bound, tier-two class, verdict); K2; K3; K4; proceeds (F1); determined or undetermined flag per cell.
- The table never presents K1 for a condensed phase and K2 to K4 for an orthophosphate as one film. CL-D11.

## Physical argument, in order

1. **Carbonate control** (frozen): one paragraph, one table row, one figure panel. Negative control for K1, positive control for K2. CL-S03, CL-S02.
2. **Phosphate phases, including hydroxide and water.** K1 per phase and cutoff class as brackets; the per-reaction table (lattice oxygen release, structural OH, water of hydration) with a_w and a_OH as design axes; bone mineral near carbonate (tier one) in the words of F6. CL-S04, CL-S05, CL-S01. Fig `fig:ladder` (window ladder: oxidation limits versus cutoffs and the bare-Al onset).
3. **Condensed and amorphous phases.** Condensed phosphates against orthophosphates; amorphous versus crystalline K1 panel (amorphous row governs, crystalline an optimistic upper reference); thresholds reported as thresholds. CL-S06, CL-D17. Fig `fig:k1panel`.
4. **The processing regime.** pH versus supersaturation with the Al passivation window (derived and published windows both); K2 at the processing pH; competing slurry phases; the condensed fraction f_cond per route under slowest and fastest plausible rates. CL-S07, CL-S08, CL-S09. Fig `fig:phmap`.
5. **Required precision for the template-nucleus energy.** The nucleation-barrier map as a hypothesis map (`fig:nucmap`); the required-precision map and flip values (`fig:precision`); the one-sentence statement that the nucleation half is not validated, count in the SI (`tab:retrodiction`). CL-S10, CL-P04, CL-T03.
6. **Candidate ranking with baselines.** The candidate-by-condition heatmap (`fig:heatmap`), the Al-salt film ladder (`fig:alsalt`: AlPO4, Al(PO3)3, Al-polyphosphate, Al2O3, bare-Al onset; Al-borate and Al-oxalate rungs are cut earliest), and the baselines table (`tab:baselines`: baked aluminophosphate; Li polyphosphate; K1, K2, K4 only, solubility undetermined unless a composition-based value exists). The headline frame (A, B or C) is stated here. CL-S11, CL-S12, CL-S13, CL-M14.

## Figures and tables

Figures: `fig:ladder`, `fig:k1panel`, `fig:phmap`, `fig:nucmap`, `fig:precision`, `fig:heatmap`, `fig:alsalt`. Tables: `tab:candidates`, `tab:baselines`; `tab:retrodiction` in the SI. Figures carry no legends and no text inside the axes; letters sit outside; everything else is in the caption.

## Macros needed

Planned from the PH-W5.1, PH-W4.2 and PH-W4.3 result files, registered at PH-W8.3 (names reserved): `NumK1HApLow`, `NumK1HApHigh`, `NumK1CarbonateOnset`, `NumK1CondensedLowerBound`, `NumPbxAlWindowLow`, `NumPbxAlWindowHigh`, `NumFcondR1`, `NumFcondR2`, `NumPrecGammaSubNuc` (registered, mock until PH-W4.3). Registered now: `NumRetroPassCount`, `NumRetroUsableCases`.

## Claims carried

CL-S03 to CL-S12, CL-S13, CL-P04, CL-T03, CL-X03; carbonate era: CL-G01, CL-G02, CL-P01, CL-T01, CL-X01, CL-X02.

## Supplying lanes

- p0-w8 writes it; p0-w5 (ladder, window, per-reaction table, Al-salt ladder); p0-w4 (screen, f_cond, precision map, heatmap rows); p0-w2 (baselines, retrodiction); p0-w6 (figures).

## Cautions

- No nucleation or wetting number as a finding.
- DFT numbers never unlabelled; the DFT spread goes to the SI (CL-X03).
- Tier-two rows in LiPF6 are context only in the fluorine-free regime.
- No ranking of a film against a baseline (CL-N07); baselines enter through K1, K2 and K4 only.
