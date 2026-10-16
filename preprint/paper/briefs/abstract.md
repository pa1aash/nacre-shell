# Brief: Abstract

- **File:** `sections/abstract.tex`. It defines `\nacreAbstract`, which the template head places in the front matter.
- **Written:** last, from the claim ledger, once Results and Discussion are drafted.
- **Length target:** 150 to 200 words, one paragraph. The ChemRxiv limit is 500 words (`ops/policy/p0/requirements.md`, T1).

## Purpose

State the one claim of the paper in the order of the energetics, and nothing beyond it.

## Physical argument, in order

1. **Problem.** In the aqueous slurry, the native oxide on the aluminium collector meets alkaline water.
2. **Chain.** A templated calcium-carbonate film needs four things in sequence: adhesion in water, Ca2+ sequestration, heterogeneous nucleation and thermodynamic stability. The chain can be written consistently.
3. **Screen.** Literature-bounded priors are propagated through the chain, and a small set of quantities governs the outcome.
4. **Precision.** The accuracy each governing quantity needs from a first-principles calculation is stated.
5. **Checks.** The retrodiction is reported as it came out. The Pourbaix result is a thermodynamic proxy.
6. **Scope.** The scope sentence closes the abstract (CL-N01).

## Figures and tables

None.

## Macros needed

At most two, and only if a number is essential. Candidates are the leading total-order Sobol index (`\NumSobolTotalGammaNucLiq`) and one required precision (`\NumPrecGammaNucLiq`). The abstract prefers words to numbers.

## Claims carried

CL-R05, CL-G01, CL-P01, CL-T01, CL-X01, CL-N01.

## Supplying lanes

- p0-w8 writes it.
- Its inputs come from p0-w4 (screen), p0-w2 (retrodiction) and p0-w5 (Pourbaix).
