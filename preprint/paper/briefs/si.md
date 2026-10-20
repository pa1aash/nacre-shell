# Brief: Supplementary Information

- **File:** `si/main_si.tex`. Built by `build.sh` with the same template head as the manuscript.
- **Written:** sections fill as the supplying lanes deliver. S1 is an include.
- **Length target:** no fixed length; each section is as long as its content requires.

## Purpose

Hold everything the main text cites but does not need inline: the full derivation and proof, the retrodiction record, the thermochemistry benchmark and the DFT spread, the conversion-step rows, the full parameter provenance, the sensitivity detail and the anchor.

## Sections, in order

1. **S1, full derivation.** Included from `theory/si_derivation.tex` (p0-w3); a draft marker renders until it exists.
2. **S2, no double counting.** The proof that each interfacial free energy enters the chain once (CL-R05), from the W3 derivation.
3. **S3, parameter sources and conflicts.** Full provenance of the early parameter table (CL-B01, CL-B02), from p0-w1.
4. **S4, sensitivity detail.** Sobol indices with intervals for every link (CL-G01), from p0-w4.
5. **S5, retrodiction cases** (`tab:retrodiction`, Table S1). The case-by-case record; the count against the registered rule stated as it came out; an optional qualitative consistency check against PDA-promoted apatite, labelled consistency, not validation. CL-T01, CL-T03, from p0-w2.
6. **S6, thermochemistry benchmark and the DFT spread** (`si:thermo`). Benchmark against tabulated formation data; per-reaction onset table with benchmark status; the spread of DFT values on one reaction as a reportable finding; DFT never unlabelled; the carbonate DFT extra from the same database version. CL-X03, CL-M10, CL-M16, from p0-w5.
7. **S7, conversion steps and thresholds** (`si:conversion`). One row per precursor-to-cell-stage pair (F4). CL-D11, from p0-w5 with p0-w1.
8. **S8, sourced parameters** (`si:sourced`). Provenance behind `tab:parameters`. CL-M11, from p0-w1.
9. **S9, anchor details.** Set-up, convergence and placement against the prior (CL-X02, carbonate control, frozen), from p0-w5.

## Figures and tables

Numbered S1, S2 and so on, as set in `main_si.tex`.

## Macros needed

As each section requires; the same `numbers.tex` macros as the main text.

## Claims carried

CL-R05, CL-B01, CL-B02, CL-G01, CL-T01, CL-T03, CL-X02, CL-X03, CL-D11, CL-M10, CL-M11, CL-M16 (supporting detail only).

## Supplying lanes

p0-w3, p0-w1, p0-w4, p0-w2 and p0-w5. p0-w8 assembles.
