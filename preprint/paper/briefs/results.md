# Brief: Results

- **File:** `sections/results.tex`.
- **Written:** after checkpoint cp4 (screen, retrodiction and anchor).
- **Length target:** 1300 to 1700 words, seven paragraphs, plus Table 3.

## Purpose

Report what the screen, the retrodiction, the Pourbaix proxy and the anchor gave, in an order that lets each result rest on the previous one. Every number is a macro.

## Physical argument, in order

1. **Retrodiction (Fig 4, Table 3).**
   - The chain run on literature cases with known outcomes.
   - Agreements, disagreements and undecided cases are counted with macros, and the misses are named.
   - The result is reported as it came out, before any parameter ranking, so the reader can judge the chain first.
   - Claim: CL-T01.
2. **Per-link distributions.**
   - Adhesion in water: the median and interval of the wet work of adhesion.
   - Ca2+ binding (descriptor): the transfer free energy, occupancy, surface excess and adsorption term; no local supersaturation (cp2 ruling).
   - Nucleation: the contact angle, the shape factor and the barrier.
   - All values come from macros. Claims: CL-R01 to CL-R03, as computed quantities.
3. **Barrier map (Fig 5).**
   - The heterogeneous barrier over the plane of the two governing interfacial energies, with the Table 2 criteria drawn as contours.
   - It shows where the criteria are met and where they are not.
   - Claim: CL-G02.
4. **Governing parameters (Fig 6).** Total-order Sobol indices with bootstrap intervals; a small set carries most of the variance. Claim: CL-G01.
5. **Required precision (Fig 6 and Table 2).** For each governing quantity, the accuracy needed to move the outcome across a criterion. This is the paper's main quantitative output. Claim: CL-P01.
6. **Pourbaix proxy (Fig 7).** The pH and potential window where the calcium carbonate phase and the oxide are both stable in the slurry. It is labelled a thermodynamic proxy in the text and the caption. Claim: CL-X01.
7. **Anchor (Fig 8).** One governing input computed once and placed against its prior quantile. It is a consistency check on the prior, not a validation. Claim: CL-X02.

## Figures and tables

- Fig 4: retrodiction.
- Fig 5: barrier map.
- Fig 6: Sobol indices with the required precision.
- Fig 7: Pourbaix.
- Fig 8: anchor.
- Table 3: retrodiction cases.

## Macros needed

All from `preprint/generated/sources.yaml`:

- Retrodiction: `\NumRetroCases`, `\NumRetroConsistent`, `\NumRetroInconsistent`.
- Per-link distributions: `\NumWadhWetMedian`, `\NumWadhWetLow`, `\NumWadhWetHigh`, `\NumDGseqMedian`, `\NumSlocalMedian`, `\NumThetaMedian`, `\NumFthetaMedian`, `\NumDGhetMedian`.
- Sobol: `\NumSobolTotalGammaNucLiq`, `\NumSobolTotalGammaNucLiqLow`, `\NumSobolTotalGammaNucLiqHigh`, `\NumSobolTotalGammaSubNuc`, `\NumSobolTotalDGbind`.
- Required precision: `\NumPrecGammaNucLiq`, `\NumPrecGammaSubNuc`, `\NumPrecDGbind`.
- Pourbaix: `\NumPbxCalciteHullMax`, `\NumPbxPhLow`, `\NumPbxPhHigh`.
- Anchor: `\NumAnchorValue`, `\NumAnchorPriorQuantile`.

All are mock today. R-cell counterparts are added when the screen covers R-cell.

## Claims carried

CL-T01, CL-R01, CL-R02, CL-R03, CL-G02, CL-G01, CL-P01, CL-X01 and CL-X02.

## Supplying lanes

- p0-w2: retrodiction, Table 3.
- p0-w4: screen, Sobol and precision.
- p0-w5: Pourbaix and anchor.
- p0-w6: Figs 4 to 7 (data figures).
- p0-w7: Fig 8 (anchor structure render).
- p0-w8: text.

## Cautions

- Captions carry all information except axes, legends and panel letters (RUNBOOK R5 figures). Captions are linted like text.
- Results are written C1 to C5 where the charter's claim order applies (`charter/branches.md`). Each opens with its registered threshold where one exists.
- No language about function or rates. A favourable barrier is a statement about thermodynamic possibility under the priors only.
