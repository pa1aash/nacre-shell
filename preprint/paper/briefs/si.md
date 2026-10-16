# Brief: Supplementary Information

- **File:** `si/main_si.tex`. Built by `build.sh` with the same template head as the manuscript.
- **Written:** sections fill as the supplying lanes deliver. S1 is an include.
- **Length target:** no fixed length; each section is as long as its content requires.

## Purpose

Hold everything the main text cites but does not need inline: the full derivation and proof, the parameter provenance, the sensitivity detail, the retrodiction record and the anchor details.

## Sections, in order

1. **S1, full derivation.**
   - Included with `\IfFileExists` from `../../theory/derivation_body.tex`, which p0-w3 provides; the path is relative to `preprint/paper`, so it is `theory/` at the repository root.
   - Until it exists, a draft marker renders, and a release build stops.
2. **S2, no double counting.** The proof that each interfacial free energy enters the chain once (CL-R05), from the W3 derivation.
3. **S3, parameter sources and conflicts.** Full provenance of Table 1 and the conflict list (CL-B01, CL-B02), from p0-w1.
4. **S4, sensitivity detail.** First- and total-order Sobol indices with intervals for every link and regime (CL-G01), from p0-w4.
5. **S5, retrodiction cases.** The case-by-case record (CL-T01), from p0-w2.
6. **S6, anchor details.** Set-up, convergence and the placement against the prior (CL-X02), from p0-w5.

## Figures and tables

These are numbered S1, S2 and so on, as set in `main_si.tex`.

## Macros needed

As each section requires. They are the same `numbers.tex` macros as the main text.

## Claims carried

CL-R05, CL-B01, CL-B02, CL-G01, CL-T01 and CL-X02 (supporting detail only).

## Supplying lanes

p0-w3, p0-w1, p0-w4, p0-w2 and p0-w5. p0-w8 assembles.
