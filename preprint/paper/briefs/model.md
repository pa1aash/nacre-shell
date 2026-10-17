# Brief: The chain from adhesion in water to film stability (Model)

- **File:** `sections/model.tex`.
- **Written:** after checkpoint cp2 (equation sheet and derivation signs).
- **Length target:** 1000 to 1300 words, six paragraphs, with four to six numbered equations.

## Purpose

Write the four links as one consistent chain, in energetic order, with each observable defined once and each interfacial free energy entering once.

## Physical argument, in order

1. **Overview.** The links are anchor, sequester, nucleate and stability. They are conditions in series, so a failure at any link ends the chain. Fig 2 is cited. Claim: CL-R05.
2. **Adhesion in water (Fig 2a).**
   - The wet Dupre work of adhesion is W_adh,wet = gamma_ox,w + gamma_pol,w - gamma_ox,pol: the reversible work to replace the oxide-template contact with two water interfaces.
   - Why the dry adhesion energy is the wrong quantity: the slurry never presents a dry oxide.
   - Claim: CL-R01.
3. **Sequestration (Fig 2b and Fig 3).**
   - The free energy of moving Ca2+ from the hydrated bulk at the regime activity to a binding site.
   - It is built as a thermodynamic cycle (Fig 3) with protonation-state and ionic-strength legs at the regime pH.
   - Pending cp2 (W3 questions Q1 and Q2): whether sequestration enters nucleation through a local enrichment and supersaturation, c_local/c_bulk = exp(-Delta_G_seq/RT), or through the interfacial energies. The Introduction (P0-W8.2) states the template's role neutrally, as lowering the barrier through the interfacial energies and the ion activities at the interface; write this paragraph to the cp2 ruling and do not assert enrichment before it.
   - Claim: CL-R02.
4. **Nucleation (Fig 2c).**
   - The heterogeneous barrier is the shape factor f(theta) times the homogeneous barrier, with the Young relation for theta.
   - If cp2 keeps the enrichment route, the local S from step 3 enters the homogeneous barrier through k_B T ln S; otherwise the sequestration term enters through the interfacial energies.
   - The f(theta) expression and the 16 pi / 3 prefactor are allowlisted forms. Every other number is a macro.
   - Claim: CL-R03.
5. **Stability (Fig 2d).**
   - R-slurry: the Pourbaix decomposition free energy above the aqueous hull, for the CaCO3 phase and the Al oxide or oxyhydroxide.
   - R-cell: the lithium-referenced stability window.
   - Claim: CL-R04.
6. **Consistency.**
   - Each interfacial free energy appears in exactly one link. The shared gamma terms between adhesion and nucleation are identified, not duplicated.
   - The proof is in the SI (no-double-counting section).
   - Claim: CL-R05.

## Figures and tables

- Fig 2, panels a to d: the mechanism chain, one panel per link.
- Fig 3: the thermodynamic cycle for sequestration.

## Macros needed

None for the relations themselves; the model section is symbolic. Results macros are cited from Results, not here.

## Claims carried

CL-R01, CL-R02, CL-R03, CL-R04 and CL-R05.

## Supplying lanes

- p0-w3 supplies the derivation and the equation sheet (`theory/**`; the SI includes `theory/derivation_body.tex`).
- p0-w6 supplies Fig 2 and Fig 3.
- p0-w8 writes the text.

## Cautions

- Use symbols exactly as the W3 equation sheet defines them; reconcile at cp2.
- No digits in prose outside macros and the allowlisted forms (`lint/numbers_allowlist.txt`). Chemical formulae go through `\ce{}`.
