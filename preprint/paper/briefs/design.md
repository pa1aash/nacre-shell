# Brief: Design rules

- **File:** `sections/design.tex`, which inputs `sections/model.tex` (the templating-thermodynamics subsection, was the Physical model).
- **Written:** PH-W8.2 (day 6), to the contract as frozen at cp4 and amended at cp5.
- **Length target:** 1900 to 2400 words: three subsections (the four conditions; templating thermodynamics; the route layer), six figures and tables in all.

## Purpose

State the screening rules before any number appears: the four gating conditions, how each is decided, how the stage of a phase fixes which conditions apply, the thermodynamics of templating (mineral-neutral), and the route layer that supplies a condensed phosphate in situ.

## Physical argument, in order

### The four conditions (`sec:conditions`)

1. **K1, K2, K3, K4 and the descriptors.** K1 oxidation window above the charge cutoff, per cutoff class, never a single verdict; K2 insoluble at the processing pH; K3 an accessible nucleation window along the dose axis; K4 a thin continuous film (spread or closure). Adhesion and Ca-binding are descriptors, not gates; the deletion test stays on K3 and K4. CL-D03 to CL-D07. Fig `fig:conditions`.
2. **K1 is a bracket with two tiers.** Tier one: onset with the solid-salt sink (upper bound) and with the hydration sink (lower bound); pass needs the lower bound above cutoff plus margin, falsified needs the upper bound below cutoff minus margin, else inconclusive. Tier two: a measured service limit with evidence class A, B or C; a record in a fluorinated electrolyte can counter-indicate, not support. Undetermined never passes. CL-D08, CL-D09.
3. **Which phases proceed.** A phase proceeds to K3 and K4 unless falsified at every cutoff class (F1). CL-D10.
4. **STAGE (F4).** Slurry-stage phases (brushite, ACP, HAp): K2 to K4 apply. Cell-stage phases (Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3): K1 applies. A conversion step joins a precursor to its cell-stage product (thermodynamic dehydration and condensation thresholds, literature conversion temperatures, the cure range of the baked baseline). K1 for a condensed phase and K2 to K4 for an orthophosphate are never presented as one film. CL-D11.
5. **The design rule for a film that is not itself stable.** A corrosion product that is insoluble and oxidation-stable can protect-by-formation (aluminium fluoride is the fluorinated analogue; the fluorine-free analogue is an Al phosphate or borate). Film properties are screened; phosphate supply at a pit is a hypothesis. CL-D12.

### Templating thermodynamics (`sec:model`; mineral-neutral, carbonate-era text)

6. Carbonate-era steps (1) to (7), adapted to the phosphate nucleus: the two regimes; adhesion in water; Ca2+ binding as a descriptor; heterogeneous nucleation; film coverage; stability; what the model leaves out. Step (6) is carbonate-specific and is replaced by the conditions above. Claims CL-R01 to CL-R05, CL-R09 to CL-R13, CL-L06. Figs `fig:chain`, `fig:cycle` (legacy Fig 2, Fig 3).

### The route layer (`sec:routes`)

7. **Routes R1 to R3** and the race against hydrolysis to orthophosphate (the low-ceiling phase). CL-D13. R3 is one sentence and the item cut earliest.
8. **Criteria in route form.** Condensed fraction at the end of the wet period (K2): CL-D14. Formation criteria (K3): R1 falsifying-only, R2 only where the binodal map covers; a(Al3+) in two labelled states (oxide-equilibrium, pit-state). CL-D15. Liquid wetting (K4): gamma_sn <= gamma_sl; spreading coefficient as a design result. CL-D16.
9. **Framings.** Amorphous governs the in-situ routes, crystalline is an optimistic upper reference; "requires crystallisation" label. CL-D17. Matrix rungs: tier two only, never a gate; polydopamine a stated risk. CL-D18.

## Figures and tables

- `fig:pathway`: four-panel bone-like pathway schematic (W6.1).
- `fig:conditions`: the four-conditions diagram, with stage marked (W6.1).
- `fig:chain`, `fig:cycle`: legacy Figs 2 and 3, adapted (W6).
- No table; `tab:thresholds` is in Methods.

## Macros needed

None for results. Symbols from `theory/macros.tex`; chemical formulae through `\ce{}`; digits only in the allow-listed forms.

## Claims carried

CL-D03 to CL-D18, CL-D20; carbonate era: CL-R01 to CL-R03, CL-R05, CL-R09 to CL-R12, CL-L06 (CL-R04 withdrawn at PH-W8.2, replaced by the conditions; CL-R13 moved to the Introduction).

## Supplying lanes

- p0-w8 writes it; p0-w3 supplies the contract (v6) and route derivations; p0-w6 figures.

## Cautions

- Formation, wetting and film behaviour are screened criteria, never statements of fact (CL-N10).
- "Self-healing" only as a design hypothesis or criterion.
- Binding or enrichment never raises the supersaturation (cp2 ruling); C2 is a descriptor, not a gate.
