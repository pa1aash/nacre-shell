# Brief: Declarations (end matter)

- **File:** `sections/declarations.tex`.
- **Written:** scaffolded in PH-W8.1. Palaash fills the statements at P0-W8.5. The repository and archive identifiers are filled at C3.
- **Length target:** 100 to 250 words in all.

## Purpose

Carry the end matter in the publisher's order: conflicts of interest, data and code availability, acknowledgements. Every value is generated, so nothing is retyped. ChemRxiv does not require a contributor-roles statement, so none is generated; the author list in the front matter is kept.

## Content, in order

1. **Conflicts of interest.** `\nacreCompetingInterests`, from `preprint/paper/declarations.yaml` (`competing_interests`). Placeholder for Palaash (W8.5).
2. **Data and code availability.** `\nacreRepoURL` and `\nacreZenodoDOI`, from `declarations.yaml`, filled at C3. The SI DOI (`\nacreSIDOI`, front-matter dagger footnote) is filled at C3 too.
3. **Acknowledgements.** `\nacreFunding` and `\nacreCompute` (Palaash at W8.5), then the local-only AI-use disclosure, included from `.local/p0/ai_ack.tex`. A release build stops if the file is absent.

## Figures and tables

None.

## Macros needed

The declaration macros generated from `declarations.yaml` (`nacreRepoURL`, `nacreZenodoDOI`, `nacreSIDOI`, `nacreCompetingInterests`, `nacreFunding`, `nacreCompute`); no number macro.

## Claims carried

None. No claim of the ledger lives here.

## Supplying lanes

- p0-w8 scaffolds it; Palaash supplies the statements; the integrator fills the C3 identifiers.

## Cautions

- The release guard keeps failing on placeholders, TBD, pending markers, mock macros and unresolved references.
- No personal email address in a committed file.
