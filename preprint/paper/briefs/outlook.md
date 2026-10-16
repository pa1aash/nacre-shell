# Brief: Outlook, the calculations that would decide the question

- **File:** `sections/outlook.tex`.
- **Written:** after checkpoint cp4, because the required accuracies come from the Sobol result.
- **Length target:** 400 to 550 words, five paragraphs.

## Purpose

Turn the required-precision result into a concrete plan of calculations. Each calculation is tied to the governing quantity it would deliver and the accuracy it needs. Nothing here is a result.

## Physical argument, in order

1. **Order of attack.** The calculations follow the ranking of Fig 6: the quantity with the largest total-order index and the tightest required precision comes first.
2. **Density-functional theory.**
   - Targets: the template-oxide and nucleus-substrate interfacial energies, from slab calculations with explicit treatment of hydroxylation.
   - Needed accuracy: `\NumPrecGammaSubNuc`.
   - What a value outside that accuracy would and would not settle.
   - Claim: CL-O01.
3. **Machine-learned-potential molecular dynamics.**
   - Method: a potential fine-tuned on targeted first-principles data, run on the hydrated interface.
   - Targets: the potential of mean force for the wet work of adhesion, and the contact angle of the nucleus.
   - Needed accuracy: `\NumPrecGammaNucLiq`.
   - Claim: CL-O02.
4. **Free-energy calculations.**
   - Target: a potential of mean force for Ca2+ at each binding site, with protonation and ionic-strength corrections.
   - Needed accuracy: `\NumPrecDGbind`.
   - Claim: CL-O03.
5. **Status.** None of these has been run for this paper. The scope sentence for the full calculations is used verbatim (CL-N03).

## Figures and tables

- Fig 6 is referred back to; no new figure.

## Macros needed

- `\NumPrecGammaSubNuc`
- `\NumPrecGammaNucLiq`
- `\NumPrecDGbind`

## Claims carried

CL-O01, CL-O02, CL-O03 and CL-N03.

## Supplying lanes

- p0-w4: precision values.
- p0-w8: text.
- The methods plan follows the charter's targeted-DFT-plus-learned-potential workflow (`charter/branches.md`, methods contribution).

## Cautions

- Plans in the future tense, without any expected outcome.
- No compute-budget or schedule promises.
