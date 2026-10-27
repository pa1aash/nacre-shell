# Brief: The screening framework

- **File:** `sections/framework.tex`.
- **Written:** PH-W8.13, the main contribution of the paper, placed after the Introduction.
- **Length target:** 500 to 700 words plus one compact table.

## Purpose

State the open screening framework as the contribution: what goes in, what each stage tests, what comes out, and how a reader adds a candidate phase and reruns the screen.

## Order

1. **Inputs.** Sourced thermochemical data with uncertainties and evidence grades; the candidate list; the pH, dose and cutoff windows.
2. **Stage logic.** Processing-stage dissolution test (supersaturation at every state of the grid); cell-stage oxidation upper bound for a saturated sink; conversion steps as water-activity thresholds only. The cell stage can exclude a phase but cannot admit one.
3. **Outputs.** Exclusion map, break-even ratio, required-precision map, flip values.
4. **Adding a phase.** The data needed, the file to edit and the command to run, named as in the repository.
5. **Release.** The open repository biomin-screen; the URL is the pending author field `nacreRepoURL`, never typed.

## Figures and tables

- `tab:framework`: inputs, stage logic, outputs and how a phase is added.

## Macros needed

None; no number appears in the section.

## Claims carried

CL-M18, CL-M19; summarised from Design and Methods: CL-M01, CL-M02, CL-M11, CL-D05, CL-D08, CL-D11, CL-D20, CL-M17, CL-S03, CL-S13, CL-P04, CL-M09.

## Supplying lanes

- p0-w8 writes it.
