# Brief: Introduction

- **File:** `sections/introduction.tex`.
- **Written:** P0-W8.2 (Day 2).
- **Length target:** 550 to 700 words, six paragraphs, one per step below. P0-W8.2 set the six-step order; the Day 1 brief had four paragraphs.

## Purpose

Pose the question physically: is the templated mineralisation sequence thermodynamically possible at the oxide-slurry interface? Then show why a parameter screen with stated precision targets is the right first step.

## Physical argument, in order

1. **The setting.**
   - Water-processed cathodes with fluorine-free binders.
   - The alkaline aqueous slurry, and what it does to the native Al2O3/AlOOH on the collector.
   - Why the slurry stage (R-slurry) matters separately from the cell (R-cell), which is named once as the second set of conditions.
2. **Biomineralisation as a physical hypothesis.**
   - Nacre builds a mineral on an organic matrix; amorphous precursors appear at its growth front.
   - The transplanted chain: adhesion of a catechol-bearing layer to the hydrated oxide in water, Ca2+ binding at the layer, templated nucleation of CaCO3, film stability. Each link is posed as a free-energy question. Fig 1 is cited here.
   - **Sequestration.** Do not assert that Ca2+ binding raises the local supersaturation. How sequestration enters nucleation is settled by the cp2 derivation (W3 questions Q1 and Q2). The template's role is phrased neutrally, as lowering the nucleation barrier through the interfacial energies and the ion activities at the interface, made precise in the Model.
   - **Chitosan.** Do not assume chitosan is present as dissolved chains in an alkaline slurry (lane note N4). The Introduction does not name chitosan; polysaccharide templates appear only inside novelty wording N1 ("a catechol or polysaccharide template"), which describes what was searched.
3. **Why thermodynamics first, and what is unknown.**
   - A link that is unfavourable for every plausible input ends the sequence whatever the kinetics.
   - The governing interfacial and binding free energies are weakly constrained by experiment: proxies and single original determinations (`lit/corpus/coverage_notes.yaml`).
   - A screen that ranks the inputs and states the precision each needs addresses that gap.
4. **Prior work and the gap.**
   - Novelty wording N1, then N2, from `lit/novelty.md`, with both qualifiers ("patent literature not searched"; "within the searched literature").
   - Two departures from the N1 text, recorded in the report of P0-W8.2: the search month is left out (rule R5, no typed numbers), and "sequestration and enrichment" reads "sequestration" (the sequestration caution above).
   - None of the unsupported wordings U1 to U12.
5. **Contrary evidence.**
   - Carbonate scale on aluminium alloys accompanied more corrosion (`lit/contrary.md` B1, Osorio-Celestino and co-workers).
   - A polydopamine coating reduced CaCO3 deposition (B10).
   - The distinction between a porous scale and a coherent templated film is central to what follows; it is argued from the nucleation and conformality links, not assumed.
6. **What the paper does and does not do.**
   - A thermodynamic screen with literature-bounded inputs; the governing quantities and the accuracy each needs; the section order.
   - The scope sentences are the does-not-claim entries, verbatim (CL-N01, CL-N02, CL-N03).

## Figures and tables

- Fig 1, the hero: the chain at a glance from oxide to film, with no numbers in the figure. Until p0-w7 delivers the render, the float holds a missing-input marker; the caption says the scene is illustrative and that its charge is balanced with dissolved carbonate ions (ruling D5).

## Macros needed

None. The Introduction carries no results and no numbers. A number that becomes essential needs a macro source keyed to `lit/params.yaml`, once p0-w1 has pushed it.

## Claims carried

- Background (CL-K01 to CL-K10), traced to evidence rows or DOIs.
- Hypothesis framing (CL-R06 to CL-R08), forward references to CL-R01 to CL-R05.
- Novelty (CL-V01, CL-V02) and contrary evidence (CL-E01 to CL-E03).
- Contribution (CL-G03, CL-P03), forward references to CL-G01 and CL-P01.
- Scope sentences: CL-N01, CL-N02 and CL-N03.
- Each sentence that carries a claim ends with a comment naming its id; `tests/preprint/test_preprint_introduction.py` checks the markers against the ledger.

## Supplying lanes

- p0-w8 writes it.
- Fig 1 comes from p0-w7 (render) with p0-w6 (style).
- Background references come from p0-w1's evidence table and p0-w2's novelty and contrary records. Every reference entered through `nacre bib add --bib preprint/paper/refs.bib <doi>`.

## Cautions

- No functional promise for the film, and none of the out-of-scope wording that rule R6 lists.
- No "first report" wording (SG14), and none of U1 to U12.
- Not the hypothesis wording "engineered out", and no claim that thresholds were set before the calculation (lane note N5). N5's sentence about the earlier calcite estimate belongs to Methods or Discussion.
