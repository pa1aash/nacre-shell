# P0 preprint outline (paragraph level), retargeted at PH-W8.1

Working title (from `ops/tracks/p0.yaml`, unfrozen, final at cp6): *Thermodynamic screening of bone-inspired calcium phosphate barriers for aluminium current collectors in fluorine-free lithium-ion cells.*

The paper is a thermodynamic screen, not a promise of a pass. Carbonate is the control: one paragraph, one table row, one figure panel. The text follows the decisions of `ops/tracks/redirect_plan.md`. Every number is a macro from `preprint/generated/numbers.tex`, every claim an id in `preprint/claims.yaml`, and each section has a brief in `briefs/`. Carbonate-era text is kept for adaptation and marked `carbonate control (frozen)` in the source.

## Sections

1. **Abstract** (`briefs/abstract.md`), written last in the wording of the outcome frame (A, B or C).
2. **Introduction** (`briefs/introduction.md`): setting; incumbents and prior art (phosphoric-acid pH control, carbon-coated foil; no patent is cited, PH-W8.9); the bone-mineral idea with the plain statement that hydroxyapatite and the tricalcium phosphates sit near carbonate; why a screen; the carbonate control; what the paper does not do.
3. **Design rules** (`briefs/design.md`): the four conditions (K1 to K4, two-tier K1, STAGE); templating thermodynamics (mineral-neutral, kept); the route layer (R1 to R3).
4. **Methods** (`briefs/methods.md`): sourced parameters; priors; onset pipeline and benchmark; solubility and the Al window; thresholds and the freeze; sensitivity; baselines and the control; retrodiction rule; reproducibility; disclosures.
5. **Results** (`briefs/results.md`; order set at PH-W8.3): the regime map; processing-stage dissolution stability and the acid-adjusted comparator; the carbonate control and the K1 exclusion map; phosphates and the condensed and aluminium phosphates; nucleation and templating as model statements; the required-precision map; the baselines.
6. **Predictions** (`briefs/predictions.md`): the initial experiment and the conditional predictions.
7. **Discussion and limits** (`briefs/discussion.md`).
8. **Declarations** (`briefs/declarations.md`) and **SI** (`briefs/si.md`).

## Figures (labels; numbered by order of citation)

- `fig:hero`: hero render (phosphate, alone, late; cut before the schematic). Introduction.
- `tab:conditions`: the four conditions, their test and their status (replaces the four-conditions diagram, PH-W8.4 ruling 4; the pathway schematic is dropped). Design rules.
- `fig:ladder`: window ladder (oxidation limits versus cutoffs and the bare-Al onset). Results.
- `fig:phmap`: pH versus supersaturation map with the Al passivation window. Results.
- `fig:nucmap`: nucleation-barrier map. Results.
- `fig:precision`: required-precision map. Results.
- `fig:heatmap`: candidate-by-condition heatmap. Results.
- `fig:alsalt`: Al-salt film ladder. Results.
- `fig:k1panel`: amorphous versus crystalline K1 panel. Results.
- Legacy carbonate-era figures kept for the claims that cite them: Fig 1 (chain at a glance), Fig 2 and Fig 3 (`fig:chain`, `fig:cycle`, in the templating thermodynamics), Fig 4 to Fig 8 (retrodiction, barrier map, Sobol and precision, Pourbaix, anchor), mapped at PH-W8.2 onto the labels above or to the SI.

## Tables

- `tab:candidates`: candidates versus conditions, with the STAGE field and conversion-step rows. Results.
- `tab:parameters`: sourced parameters (full provenance in the SI). Methods.
- `tab:thermo`: thermochemistry benchmark. Methods.
- `tab:thresholds`: thresholds and decision criteria (frozen at cp5). Methods.
- `tab:predictions`: the conditional predictions of the experiment (test, observable, expected under the model, what would refute it; cp6 F12). Predictions.
- `tab:baselines`: baselines (baked aluminophosphate, Li polyphosphate) through K1, K2 and K4. Results.
- `tab:retrodiction`: retrodiction cases (SI, Table S1).

## Rules for every section

- STAGE is stated wherever a verdict appears; K1 for a condensed phase and K2 to K4 for an orthophosphate are never shown as one film.
- Claims that depend on unmeasured inputs are conditional; NS7 only with its four qualifiers.
- The does-not-claim sentences are used verbatim.
