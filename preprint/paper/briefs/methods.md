# Brief: Methods

- **File:** `sections/methods.tex`.
- **Written:** after checkpoint cp3; finalised after cp4.
- **Length target:** 600 to 800 words, seven short paragraphs, plus Table 2.

## Purpose

Say how the priors become the reported quantities: propagation, variance decomposition, decision criteria, required precision, the retrodiction protocol, the Pourbaix construction and the anchor. The physics is already in Model. Procedural detail is limited to a single reproducibility paragraph (rule R4).

## Physical argument, in order

1. **Propagation.** Monte Carlo draws from the priors through each link, per regime. The draw count comes from a macro. Claim: CL-G01.
2. **Variance decomposition.** First- and total-order Sobol indices with bootstrap confidence intervals, and why the total order is the ranking quantity. Claim: CL-G01.
3. **Decision criteria (Table 2).** The thresholds per link are set at cp2 (theory/thresholds.md is the authority, rule R-thr) and frozen at cp3, changing afterwards only through a dated deviation entry. Do not claim they were set before the calculation (lane note N5). Their status relative to the charter's G2 is stated honestly. The N5 sentence goes here or in the Discussion: an earlier rough estimate under the calcite framing was available when the project was designed, and the primary framing here is chosen on literature grounds. Claim: CL-P02.
4. **Required precision.** The accuracy a governing quantity needs is the change in that quantity that moves the outcome across a decision criterion on the barrier map, at the other inputs' spread. Claim: CL-P01.
5. **Retrodiction protocol.**
   - Literature cases with known outcomes.
   - The coding of agree, disagree and undecided.
   - The rule that every case is reported.
   - Claim: CL-T01.
6. **Pourbaix and anchor.**
   - The Pourbaix decomposition free energy against the aqueous hull, with the ACC offset from fetched thermochemistry.
   - The single anchor calculation and what it checks.
   - Claims: CL-X01 and CL-X02.
7. **Reproducibility (the one procedural paragraph).**
   - Code, inputs and generated numbers are archived: `\nacreRepoURL` and `\nacreZenodoDOI`.
   - Every number in the text is generated from result files with recorded hashes.

## Figures and tables

- Table 2: thresholds and decision criteria. Columns: link, observable, criterion, source of the criterion, status.

## Macros needed

- `\NumScreenDraws`
- `\NumSobolBaseSamples`
- Threshold values, once frozen. They will be added to `sources.yaml` from the W4 threshold file.

## Claims carried

CL-G01, CL-P01, CL-P02, CL-T01, CL-X01 and CL-X02.

## Supplying lanes

- p0-w4: screen design and thresholds.
- p0-w2: retrodiction protocol.
- p0-w5: Pourbaix and anchor.
- p0-w8: text.

## Cautions

- No software walkthroughs, file names or command lines in the text. These live in the repository.
- The AI-use statement is not in Methods for the preprint. It is in the Acknowledgements (track decision, `ops/tracks/p0.yaml` `inputs.ai_disclosure`). The RSC journal route would also need a Methods statement; that ruling is open (requirements.md, conflict 7).
