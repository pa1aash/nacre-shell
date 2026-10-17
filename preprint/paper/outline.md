# P0 preprint outline (paragraph level)

Working title (from `ops/tracks/p0.yaml`): *Thermodynamic screening of a biomimetic calcium-carbonate barrier on aluminium current collectors: governing parameters and the precision required for first-principles validation.*

The outline follows the energetics. The chain runs from adhesion in water, through Ca2+ sequestration and nucleation, to film stability. Procedural material stays out of the text except for one short reproducibility paragraph in Methods. Every number is a macro from `preprint/generated/numbers.tex`, and every claim is an id in `preprint/claims.yaml`. Each section has a brief in `briefs/`.

Figures, numbered by first citation:

- Fig 1: hero, the chain at a glance (Introduction).
- Fig 2: the mechanism chain, panels a to d: adhesion in water, sequestration, nucleation, stability (Model).
- Fig 3: the thermodynamic cycle for sequestration (Model).
- Fig 4: retrodiction (Results).
- Fig 5: barrier map (Results).
- Fig 6: Sobol indices with the required precision (Results).
- Fig 7: Pourbaix (Results).
- Fig 8: anchor (Results).

Tables:

- Table 1: parameters (Inputs).
- Table 2: thresholds and decision criteria (Methods).
- Table 3: retrodiction cases (Results).

## Abstract (brief: `briefs/abstract.md`)

1. One paragraph, written last from the ledger. It covers the chain, the literature-bounded inputs, the governing quantities and their required accuracy, the retrodiction as it came out and the Pourbaix proxy. It closes with the scope sentence. Claims: CL-R05, CL-G01, CL-P01, CL-T01, CL-X01, CL-N01.

## 1 Introduction (brief: `briefs/introduction.md`)

1. The problem in physical terms. The native oxide on aluminium collectors meets an alkaline aqueous slurry, and the oxide dissolves. That is why an interfacial calcium-carbonate film is worth asking about. No functional promise is made.
2. The biomimetic idea. Nacre-like mineralisation is templated by a polymer that binds the oxide and gathers Ca2+. The question is whether the thermodynamics allows the sequence at all. Fig 1 is first cited here.
3. Why a screen comes before simulation. The inputs are uncertain over wide literature ranges. A screen says which few quantities decide the outcome, and how accurately a first-principles calculation must give them. Claims: CL-G01, CL-P01 (forward reference).
4. What this paper does and does not do. It writes the chain, bounds the inputs, ranks them, states the required precision, reports the retrodiction as it came out and treats Pourbaix as a proxy. The scope sentence follows. Claims: CL-N01 to CL-N03.

## 2 The chain from adhesion in water to film stability (brief: `briefs/model.md`)

Written in P0-W8.3 to the derivation as audited at cp2 and cp3, in physical order:

1. The two regimes and which links apply in each. Fig 2 is cited. Claims: CL-R09, CL-R05.
2. Adhesion in water (Fig 2a). The wet Dupre balance with water competition; the dry adhesion energy is only a comparator. Claim: CL-R01.
3. Ca2+ binding as a descriptor (Fig 2b, Fig 3). Equilibrium fixes the Ca2+ electrochemical potential, so binding does not raise the driving force; it enters only through the template-liquid energy (Gibbs-Langmuir, a neutral-solute approximation), and Ca2+ at the template-crystal contact belongs to the template-nucleus energy. Binding alone can raise the barrier. Claims: CL-R02, CL-R10.
4. Heterogeneous nucleation (Fig 2c). Young's relation with the fixed sign convention, the single-entry rule and the absolute-barrier criterion. Claims: CL-R03, CL-R05, CL-R11.
5. Film coverage (Fig 2d). The spreading coefficient; complete wetting is excluded when gamma_sl <= gamma_nl, so a continuous film must come from nucleation density closing it. Claim: CL-R12.
6. Stability. R-slurry dissolution by Omega_bulk >= 1 with Pourbaix as the competing-phase baseline; R-cell anodic oxidation of carbonate referenced to Li, experimental route governing, sink fixed by the electrolyte. Claim: CL-R04.
7. What the model leaves out, briefly (full list in the Discussion). Claim: CL-L06.

## 3 Literature-bounded inputs (brief: `briefs/inputs.md`)

1. Where the inputs come from. Each is a fetched literature value with a stated range (Table 1). Claim: CL-B01.
2. Conflicts between sources are recorded, and the prior is widened to bracket them (detail in SI). Claim: CL-B02.
3. Inputs left open by the literature are carried as open ranges, with the regime definitions. Claim: CL-B03.
4. The breadth of the priors, stated once here and taken up again in the Discussion. Claim: CL-L02 (forward).

## 4 Methods (brief: `briefs/methods.md`)

Written in P0-W8.3 (order of the P0-W8.3 prompt, Task C):

1. Priors: the construction rule, grades, correlation groups, ignorance priors (never reported as P(feasible)), flagged analog priors, design axes. Claims: CL-M01, CL-M02.
2. Propagation and sensitivity: Monte Carlo, Sobol indices for independent inputs, Shapley effects for correlated ones, the sizing rule. Claims: CL-G01, CL-M03.
3. Thresholds and the decision rule (Table 2), each from the physics; the conventions through macros; the framing rule. Claims: CL-P02, CL-M04, CL-M05.
4. Retrodiction: case selection, interface mapping, correctness and pass rules, swap check and permutation null, fixed before the run. Claim: CL-T02.
5. Pourbaix and window settings: the Materials Project data with the attribution text; the gas-reference benchmark; the experimental route. Claim: CL-M06.
6. The compute anchor protocol, a pipeline check that is not a screen input. Claim: CL-M07.
7. Reproducibility, one short paragraph.
8. Disclosures (N5, cp3): the earlier rough calcite estimate; the cell-regime scheme values seen before the scheme rule; the slurry Omega values seen before the dissolution rule. Claim: CL-M08.

## 5 Results (brief: `briefs/results.md`)

1. Retrodiction first, as a check of the chain against known cases. Fig 4 and Table 3. Counts come from macros, and the misses are reported. Claim: CL-T01.
2. Distributions per link: the wet work of adhesion, the Ca2+ binding descriptors (transfer free energy, occupancy, surface excess and the adsorption term), and the contact angle, shape factor and barrier at the bulk supersaturation. Medians and intervals come from macros. Claims: CL-R01 to CL-R03 (as computed quantities).
3. The barrier map over the two governing interfacial energies, with the decision criteria overlaid (Fig 5). Claim: CL-G02.
4. Governing parameters. Total-order Sobol indices show a small set carrying most of the variance (Fig 6). Claim: CL-G01.
5. Required precision per governing quantity (Fig 6 and Table 2). Claim: CL-P01.
6. Stability in the slurry: the dose window from the bulk supersaturation, with the Pourbaix construction as the competing-phase baseline (Fig 7). Claim: CL-X01.
7. The anchor: one governing input placed against its prior (Fig 8). Claim: CL-X02.

## 6 Outlook: the calculations that would decide the question (brief: `briefs/outlook.md`)

1. Why these calculations, and in what order. They follow the ranking in Fig 6.
2. Density-functional interfacial energies, with their required accuracy. Claim: CL-O01.
3. Machine-learned-potential molecular dynamics of the hydrated interface (wet adhesion, contact angle), with their required accuracy. Claim: CL-O02.
4. Free-energy calculations for sequestration, with their required accuracy. Claim: CL-O03.
5. What none of these is yet. The scope sentence for the full calculations. Claim: CL-N03.

## 7 Discussion (brief: `briefs/discussion.md`)

1. What the results license: a statement of thermodynamic possibility under stated priors, the ranking of the governing quantities and the precision targets. Claims: CL-G01, CL-P01.
2. What they do not license: the does-not-claim sentences, verbatim. Claims: CL-N01, CL-N02, CL-N04, CL-N05.
3. Contrary evidence, including Osorio-Celestino and co-workers (2020), weighed against the chain. Claim: CL-L05.
4. Limits of the model: classical nucleation and the polymorph framing; the insulating film. Claims: CL-L03, CL-L04.
5. The Pourbaix result is a proxy. Claim: CL-L01.
6. The breadth of the priors, and what narrower priors would change. Claim: CL-L02.

## Declarations (brief: `briefs/declarations.md`)

1. Author contributions: CRediT, generated from the author register.
2. Conflicts of interest: Palaash supplies the statement at W8.5.
3. Data and code availability: the repository and Zenodo DOI macros, filled at C3.
4. Acknowledgements: funding and compute (Palaash at W8.5), then the local-only AI-use disclosure.

## Supplementary Information (brief: `briefs/si.md`)

The SI has six sections:

- S1, the full derivation (W3 include);
- S2, the no-double-counting proof;
- S3, parameter sources and conflicts;
- S4, sensitivity detail;
- S5, the retrodiction cases;
- S6, the anchor details.
