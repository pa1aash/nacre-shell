# Brief: Methods

- **File:** `sections/methods.tex`.
- **Written:** P0-W8.3, after cp3; values that depend on production outputs are reported in Results (P0-W8.4), not here.
- **Length:** about 2300 words in eight paragraphs, plus the thresholds table (`tab:thresholds`, the ledger's Table 2). The Day 1 target (600 to 800 words) predates the cp3 rulings and the P0-W8.3 order; the overrun is recorded in `ops/reports/P0-W8.3.md`.

## Order (P0-W8.3, Task C)

1. **Priors.** The construction rule (`lit/corpus/params_README.md`), grades, correlation groups, single-source widening; ignorance priors for unmeasured interfacial energies, with P(feasible) under them never reported as a finding; flagged analog priors side by side; design axes. Claims: CL-M01, CL-M02.
2. **Propagation and sensitivity.** Monte Carlo per registered state with copula correlations; Sobol indices for independent inputs, Shapley effects for correlated ones; the sizing rule and its caps (macros); required precision. Claim: CL-M03.
3. **Thresholds and the decision rule** (Table 2). Each edge from the physics; p_cred, its sweep, m_cos and its sweeps, p_deg and q_0 through macros; joint masses, states; gating links, the C2 finding, the deletion test; the framing rule; frozen at cp3 (rule R-thr). Claims: CL-M04, CL-M05, CL-P02.
4. **Retrodiction.** Case selection, interface mapping, correctness and pass rules, swap check and permutation null, fixed before the run; the limits, including the sources that already report the link (ruling D17). Claim: CL-T02.
5. **Pourbaix and window settings.** The Materials Project data with the attribution text of `results/preprint/pourbaix/cache/attribution_for_paper.md` (version, licence, changes, no endorsement, ion reference data, GNoME excluded); the Omega controls; the gas-reference benchmark; the experimental route and its margin. Claim: CL-M06.
6. **Compute anchor.** The protocol of `src/nacre/anchor/PROTOCOL.md`, a pipeline check that is not a screen input. Claim: CL-M07.
7. **Reproducibility.** One short paragraph. Claim: CL-M09.
8. **Disclosures.** N5 (the earlier rough calcite estimate; framings chosen on literature grounds), cp3 R2 (cell scheme values seen before the rule), cp3 R1 (slurry Omega values seen before the dissolution rule); the thresholds were set before any screen output, not before every calculation. Claim: CL-M08.

## Cautions

- Never "engineered out"; never a claim that the thresholds were set before the calculation in a broader sense than is true (N5).
- No software walkthroughs, file names or command lines in the text, except the one reproducibility paragraph.
- The AI-use statement is in the Acknowledgements (track decision B4), not in Methods.
