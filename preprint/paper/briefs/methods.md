# Brief: Methods

- **File:** `sections/methods.tex`.
- **Written:** PH-W8.2 (day 6) for the neutral and new paragraphs; carbonate-specific paragraphs are marked `carbonate control (frozen)` in the file and shrink or move to the SI.
- **Length target:** 1900 to 2400 words, nine paragraphs plus `tab:thresholds`, `tab:parameters` and `tab:thermo`.

## Purpose

State how every verdict is produced: sources, onset pipeline and its benchmark, solubility and window construction, thresholds and the decision rule, and the freeze. Procedure stays in the repository except one reproducibility paragraph. No result is stated.

## Order

1. **Sourced parameters** (`tab:parameters`). Every value from a fetched source with DOI and locator; gaps stay gaps; undetermined never passes. CL-M11, with the carbonate-era CL-B01 to CL-B03 (sourced inputs, conflicts, open ranges) folded in.
2. **Priors** (neutral, adapted). Construction rule, grades, correlation groups, ignorance priors never reported as a pass probability. CL-M01, CL-M02.
3. **Onset pipeline and its benchmark** (`tab:thermo`). Experimental route governs; DFT is a comparator with its measured benchmark error; phosphate DFT stays unbenchmarked until a phosphate benchmark on tabulated data passes; staged reactions as the minimum over registered reactions; glass-to-crystal correction labelled; the hydration bracket and its vetting. CL-M10, CL-M12, CL-D08.
4. **Solubility, speciation and the aluminium window.** Sourced solubility products and speciation (K2); the Al-O-H Pourbaix construction on benchmarked experimental ion data, cross-checked against the published window, both reported. CL-M13. Carbonate-era Pourbaix settings are marked frozen.
5. **Thresholds and the decision rule** (`tab:thresholds`, frozen at cp5). Numeric margins; the proceed rule; the framing rule. CL-P02, CL-M04, CL-M05, CL-D10.
6. **Propagation and sensitivity.** Monte Carlo, Sobol and Shapley indices, sizing rule; used for the required-precision map. CL-M03.
7. **Baselines and the carbonate control.** Baselines as comparator rows through K1, K2 and K4 only; the control from the frozen tag only, with the same-database DFT extra. CL-M14, CL-M16.
8. **Retrodiction** (carbonate control, frozen): the registered rule and its outcome as pre-registered; detail in the SI. CL-T02.
9. **Reproducibility** (one paragraph) and **Disclosures** (carbonate-era N5 and cp3 disclosures stay; the freeze rule: any change after the cp5 freeze is a dated deviation). CL-M09, CL-M08, CL-M15.

## Figures and tables

- `tab:parameters` (sourced parameters; full provenance in SI).
- `tab:thermo` (thermochemistry benchmark: computed against tabulated formation data, error per reaction).
- `tab:thresholds` (thresholds and decision criteria, existing, frozen).

## Macros needed

Registered: `NumPcred`, `NumPcredSweepLow`, `NumPcredSweepHigh`, `NumMcos`, `NumPdeg`, `NumSizingDrawCap`, `NumRetroPassCount`, `NumRetroUsableCases`, `NumMpDatabaseVersion` and the other Methods conventions already in `sources.yaml`. Planned: margins at the cp5 freeze (`NumMarginOx`), hydration-bracket inputs (PH-W1.3), cure range (`NumCureLow`, `NumCureHigh`, from the baseline rows).

## Claims carried

CL-M10 to CL-M16; carbonate era: CL-M01 to CL-M09, CL-P02, CL-T02, CL-B01 to CL-B03.

## Supplying lanes

- p0-w8 writes it; p0-w1 (parameter table, hydration data); p0-w3 (contract, thresholds); p0-w5 (onset pipeline, benchmark, window); p0-w4 (screen settings).

## Cautions

- No claim that the thresholds were set before every calculation (carbonate-era note N5 stands).
- No file names or command lines outside the one reproducibility paragraph.
- The AI-use statement is in the Acknowledgements, not here.
