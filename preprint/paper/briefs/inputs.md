# Brief: Literature-bounded inputs

- **File:** `sections/inputs.tex`.
- **Written:** after checkpoint cp3 (parameter table and conflicts).
- **Length target:** 500 to 700 words, four paragraphs, plus Table 1.

## Purpose

Show that every input the chain consumes is bounded by fetched literature, that conflicts are kept visible, and that open ranges stay open.

## Physical argument, in order

1. **Which inputs, and why each matters physically.**
   - The interfacial free energies of the oxide, template, water and nucleus.
   - The binding free energy.
   - The regime variables: pH, temperature, ionic strength and potential.
   - Table 1 lists each with its range and source. Claim: CL-B01.
2. **Conflicts.** Where sources disagree, the prior is widened to bracket them. The conflict list is in the SI. Claim: CL-B02.
3. **Open ranges.** Regime inputs the literature leaves unbounded are carried as open ranges, as the charter requires, and are not filled. Claim: CL-B03.
4. **Breadth.** The priors are broad because the literature is. This is stated once here and taken up in the Discussion. Claim: CL-L02 (forward).

## Figures and tables

- Table 1: parameters. It gives symbol, meaning, range, units, source key and conflict flag. Every number in the table is a macro or a generated table include.

## Macros needed

- `\NumParamCount`
- `\NumParamConflicts`
- The per-parameter bounds, once p0-w1 publishes the parameter file. They will be generated as a table include, not typed.

## Claims carried

CL-B01, CL-B02, CL-B03 and CL-L02 (forward).

## Supplying lanes

- p0-w1 supplies `lit/params.yaml`, `lit/conflicts.md` and `lit/evidence_table.csv`.
- p0-w8 writes the text and generates Table 1 from the parameter file.

## Cautions

- No literature value typed from memory; every bound traces to a fetched source.
- The table-generation path (parameter file to generated LaTeX) is a Day 3 item for this lane.
