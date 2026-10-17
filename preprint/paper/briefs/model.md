# Brief: Physical model (Model)

- **File:** `sections/model.tex` (section title "Physical model", label `sec:model`).
- **Written:** P0-W8.3, after checkpoints cp2 and cp3, to the derivation as audited there (`theory/derivation_body.tex`, `theory/cp2_brief.md`, `theory/thresholds.md`).
- **Length:** about 2100 words of prose, seven steps, seven numbered equations, Fig 2 and Fig 3. The Day 1 target (1000 to 1300 words, six paragraphs) predates the cp2 and cp3 rulings and the seven-step order of P0-W8.3; the overrun is recorded in `ops/reports/P0-W8.3.md` for the planning chat.

## Purpose

Argue each link physically, then give the relation, in physical order. Each template-dependent input enters once. No procedure, no number and no result.

## Physical argument, in order

1. **The two regimes and which links apply in each** (Fig 2). Adhesion, Ca2+ binding and nucleation are defined only in R-slurry; coverage uses R-slurry wetting energies against an R-cell thickness bound; stability is separate in each regime. The links are necessary conditions in series. Claims: CL-R09, CL-R05.
2. **Adhesion in water** (Fig 2a). The Dupre work in water with the water-competition form; the dry work is only a comparator; the bare oxide fixes the zero. Claim: CL-R01.
3. **Ca2+ binding as a descriptor** (Fig 2b, Fig 3). Equilibrium fixes the Ca2+ electrochemical potential, so binding does not raise the driving force (Delta_mu = k_B T ln Omega_bulk). It enters only through the template-liquid energy, by the Gibbs-Langmuir term (a neutral-solute approximation; the double-layer term is a stated limitation). Ca2+ at the template-crystal contact belongs to gamma_sn. Consequence, stated plainly: binding alone raises the barrier; the template helps only if gamma_sn falls by more. Claims: CL-R02, CL-R10.
4. **Heterogeneous nucleation** (Fig 2c). The capillarity barrier with f(theta); Young's relation with the fixed sign convention and the bare gamma_nl; the water-displacement cost enters gamma_sn once; the single-entry rule (proof in the SI); the absolute-barrier criterion with the Poisson-occupancy N_req. Claims: CL-R03, CL-R05, CL-R11.
5. **Film coverage** (Fig 2d). The spreading coefficient and its bound S_spread <= gamma_sl - gamma_nl from gamma_sn >= 0; complete wetting is excluded when gamma_sl <= gamma_nl, with "hydrophilic" meant relative to the mineral (a water contact angle in air does not decide it); a continuous film must come from nucleation density closing it; d_max is a cell-regime limitation. Claim: CL-R12.
6. **Stability.** R-slurry: dissolution decided by Omega_bulk >= 1, the quantity of nucleation, with the measured calcite K_sp; the Pourbaix construction at fixed carbonate carbon answers competing solids and gives the oxide baseline. R-cell: the anodic oxidation of the carbonate referenced to Li+/Li; the sink is fixed by the electrolyte (solid-salt limit an upper bound on the onset); the all-experimental route governs, computed schemes are benchmarked comparators; the Li2CO3 comparison supports the reading; the electrolyte's own limit is not assessed. Claims: CL-R04, CL-R13.
7. **What the model leaves out**, briefly: classical nucleation theory's validity, the double layer, kinetics, layer persistence (the full list is in the Discussion). Claim: CL-L06.

## Figures

- Fig 2 (`fig:chain`, from p0-w6): panels a to d, letters set by the layout outside the artwork (`layout/panel_letters.tex`).
- Fig 3 (`fig:cycle`, from p0-w6): where the binding enters the barrier.

## Cautions

- Symbols are those of `theory/macros.tex`. Digits only in the allowlisted exact forms (`lint/numbers_allowlist.txt`); chemical formulae through `\ce{}`.
- No sentence lets binding or enrichment raise the supersaturation; no C2 gate.
