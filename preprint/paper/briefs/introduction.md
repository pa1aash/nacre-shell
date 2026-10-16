# Brief: Introduction

- **File:** `sections/introduction.tex`.
- **Written:** P0-W8.2 (Day 2).
- **Length target:** 550 to 700 words, four paragraphs.

## Purpose

Pose the question physically: is the templated mineralisation sequence thermodynamically possible at the oxide-slurry interface? Then show why a parameter screen with stated precision targets is the right first step.

## Physical argument, in order

1. **The interface.** The native Al2O3/AlOOH on the collector meets a water-processed, alkaline cathode slurry with a fluorine-free binder. At high pH the native oxide dissolves. This is the regime R-slurry of `charter/regimes.yaml`. The cell regime (R-cell) is introduced in one sentence as the second set of conditions.
2. **The biomimetic proposal.** Nacre-like mineralisation uses a polymer template (catechol and amine functions) that binds the oxide in water and gathers Ca2+, followed by nucleation of calcium carbonate on the template. Fig 1 is cited here.
3. **Why a screen.** Every link depends on interfacial free energies and binding free energies that the literature brackets only loosely. Before any expensive simulation, the useful questions are:
   - which few inputs decide the outcome;
   - how accurately a first-principles method must deliver them.

   This is the paper's contribution, stated as relations and precision targets, not as a verdict on function.
4. **What follows.** The section order of the paper. The scope sentence uses the does-not-claim wording verbatim (CL-N01, CL-N02, CL-N03).

## Figures and tables

- Fig 1, the hero: the chain at a glance from oxide to film, with no numbers in the figure.

## Macros needed

None. The Introduction carries no results.

## Claims carried

- CL-R05 (forward reference to the consistent chain).
- CL-G01 and CL-P01 (forward reference to the contribution).
- CL-N01, CL-N02 and CL-N03 (scope sentence).
- Background statements need reference entries added through `nacre bib add <doi>`. The claims must not run ahead of the cited literature.

## Supplying lanes

- p0-w8 writes it.
- Fig 1 comes from p0-w7 (render) with p0-w6 (style).
- Background references come from p0-w1's corpus and p0-w2's novelty record (`lit/novelty.md`). Novelty wording stays within what that audit supports (scope guard, design flag 5).

## Cautions

- No functional promise for the film, and none of the out-of-scope wording that rule R6 lists.
- No "first report" wording (SG14) unless the novelty audit supports it.
