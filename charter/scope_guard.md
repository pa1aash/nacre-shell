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
```

```scope-guard-warn
# flagged unless the word 'thermodynamic' appears in the same sentence; lint-scope implements this in PH-W8.1
SG17W  \bstable (up to|above|to) [0-9.]+ ?V\b
```
