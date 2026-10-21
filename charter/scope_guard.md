# Scope guard

This file is the checked-in "does not claim" list (deck slide 8). It binds every
manuscript section, abstract, figure caption, SI file, preprint and talk. The study
establishes feasibility, not function: a positive result licenses an experiment, not a
battery.

## The study does not claim

- No working device.
- No corrosion rate.
- No capacity-retention figure.
- No claim that the interface is optimal; only that it is or is not possible.
- No experimental validation; there is none, by design.
- No novelty wording beyond what the Phase 1 novelty audit supports (design flag 5).

## Stated limitation: insulating film thickness

CaCO3 is an electronic insulator. A thick interfacial film would impede electron transfer
between the cathode coating and the Al collector, so conformality cannot be bought with
thickness. A coarse bound on film thickness versus electronic resistance is computed in
C4, Phase 7 item 18, and is reported as a limitation, not as a performance figure
(design flag 8).

## Stated limitation: layer persistence

C1 to C3 are evaluated in R-slurry. Survival of the anchor and of the morphology through
drying, and in contact with the in-cell electrolyte, is neither computed nor claimed.

## Stated limitation: classical nucleation theory

The C3 verdict is conditional on classical nucleation theory: a spherical-cap nucleus, a
size-independent interfacial energy and the capillary approximation (claim register,
C3 stated limits). Non-classical CaCO3 pathways through pre-nucleation clusters or a dense
liquid precursor may not follow it.

## Forbidden-claim patterns

One pattern per line: an id, whitespace, then a Python regular expression applied
case-insensitively to prose. Lines starting with `#` are comments. A future scope linter
(Phase 12 item 4) reads this block. This file itself and `charter/**` are exempt, since
they quote the forbidden claims in order to forbid them.

```scope-guard
# device and function claims
SG01  \bworking (device|cell|battery|batter(y|ies))\b
SG02  \b(prevents?|eliminates?|stops?) (al(uminium|uminum)? )?(collector )?corrosion\b
SG03  \bwe (show|demonstrate|prove) that the (barrier|layer|film|coating) (protects|prevents|blocks)\b
SG04  \b(battery|cell) (performance|lifetime)\b
# rates
SG05  \bcorrosion[- ]rates?\b
SG06  \bcorrosion current( density)?\b
SG07  \b(mm|µm|um|nm)\s*(/|per)\s*(yr|year)\b
SG08  \bmpy\b
# capacity
SG09  \bcapacity[- ]retention\b
SG10  \bcycle[- ]life\b
# optimality
SG11  \b(optimal|optimum|best[- ]performing) (interface|binder|barrier|layer|coating|design|thickness|template)\b
# experiment
SG12  \bexperimentally (validated|verified|confirmed|demonstrated)\b
# novelty, pending the Phase 1 audit
SG13  \bintersection (is|remains) unoccupied\b
SG14  \b(the )?first (ever )?(report|demonstration|study) of\b
# P0 verdict language
SG15  \b(barrier|layer|film|coating|interface) (is|are) (thermodynamically )?(feasible|viable|effective)\b
SG16  \b(demonstrate|show|establish|prove)s? (the )?feasibility\b
# redirect additions (ops/tracks/redirect_plan.md), applied at PH-I5
SG18  \b(phosphate|apatite) (barrier|layer|film|coating) (works|protects|is effective)\b
# regime frame (PH-I5c-b): "nacre-inspired" is allowed as a lineage word; result wording is forbidden
SG19  \bnacre-(type|inspired) (barrier|film|coating|layer) (works|protects|is effective|forms)\b
SG28  \bnacre-like (architecture|layered structure)\b
SG20  \bwe show\b.* (holds|survives) above\b
SG21  \boutperforms (phosphoric acid|carbon-coated|baked|plain|conventional)\b
SG22  \b(better than) (baked|plain|conventional) (coating|aluminophosphate)\b
SG23  \b(insoluble|crosslinked)\b.* film (forms|assembles) (on|at) (aluminium|aluminum|the foil)\b
SG24  \bcoacervate (wets|forms) on aluminium\b
SG25  \bpolyphosphate (film|gel|glass) (protects|prevents|is stable)\b
```

```scope-guard-warn
# flagged unless the word 'thermodynamic' appears in the same sentence; lint-scope implements this in PH-W8.1
SG17W  \bstable (up to|above|to) [0-9.]+ ?V\b
# redirect additions: SG26W is flagged unless the sentence rests on the novelty audit; SG27W unless the sentence contains 'hypothesis' or 'criterion' (the exemption words need lint-scope support in W8; lint-scope presently exempts only 'thermodynamic')
SG26W  \b(novel|first)\b
SG27W  \bself-heal(s|ing)?\b
# regime frame (PH-I5c-b): SG29W is flagged unless the sentence contains 'aragonite' (the label is only for rows where aragonite AND calcite pass K2); SG30W is flagged when 'thermodynamically suitable' is not followed within six words by 'for', 'in' or 'under' (both need lint-scope support in PH-W8.2)
SG29W  \bnacre-type\b
SG30W  \bthermodynamically suitable\b(?!(?:\W+\w+){0,5}?\W+(?:for|in|under)\b)
```
