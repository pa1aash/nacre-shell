# Outcome branches

Decided in Phase 0, before any result exists, so that the verdict cannot bias what is
published or where. The branch is selected mechanically in Phase 9 item 3 by the
decision rule registered at G2; this file fixes only what each branch publishes.

## Invariants across all branches

- **Same venue.** The venue does not change with the verdict. The target is the one
  recorded in `charter/venue/` (owned by the b-paper lane); the deck names RSC Advances
  (slide 29). A falsified result is not moved to a lesser venue, and a feasible one is
  not moved up.
- **Same preprint.** A ChemRxiv preprint is posted under every branch, linking the
  registration, code and data.
- **Same scope guard.** `charter/scope_guard.md` applies to every branch.
- **Same methods contribution.** The targeted-DFT-plus-MLIP screening workflow, the
  zero-shot failure map and the active-learning ablations are reported under every
  branch; they do not depend on the verdict.
- **Claim order.** Results are written C1 to C5, each opening with its registered
  threshold, then the outcome, the sensitivity statement and the deletion controls.

## Feasible

- **Published:** a feasibility screen. The mechanism is thermodynamically possible under
  the registered framing and regimes, with the assumptions each verdict depends on.
- **Claims carried:** C1-C5 verdicts; the deletion test showing the verdict degrades
  without the mechanism; the sensitivity of C3 to the polymorph framing.
- **Figures carried:** interface structure render; zero-shot vs fine-tuned parity;
  active vs random learning curves; Ca2+ PMF per site with controls; wet work of
  adhesion across binders; f(theta) verdict map with registered thresholds; sensitivity
  ranking; morphology model output; Pourbaix diagram and R-cell window;
  deletion-control comparison. Each must pass the Phase 10 necessity test.
- **Licenses next:** a short wet-lab specification for Prof. Braun's group (Phase 9
  item 4): what a test would need to measure. It is a licensed next step, not a claim.

## Inconclusive

- **Published:** a screen that locates the decision boundary: which input or assumption
  (for example the ACC interfacial energy, the Delta_gamma_water convention, a substrate
  termination) the verdict hinges on, and how far it must move to settle it.
- **Claims carried:** C1-C5 verdicts with their band fractions; the decisive-assumption
  statement; the deletion test.
- **Figures carried:** as for feasible, with the f(theta) verdict map and sensitivity
  ranking as the central figures.
- **Licenses next:** a targeted measurement or calculation of the decisive parameter
  only, not the full wet-lab experiment.

## Falsified

- **Published:** a negative screen and a methods paper. The mechanism fails at the named
  link(s), with the kill criterion that fired and its robustness under Phase 8
  sensitivity. This is a full result: it rules the mechanism out before bench spend.
- **Claims carried:** the failing claim(s) with their registered thresholds; the
  surviving claims; the methods contribution.
- **Figures carried:** as for feasible, centred on the failing link's figure; the
  morphology and Pourbaix figures are kept if they carry a claim.
- **Licenses next:** no wet-lab experiment of this mechanism. It may license screening
  of an alternative template (for example a carboxylate template, if C2 controls point
  there), as a new registration.

## Modifiers that apply to any branch

- **Deletion test fails** (the verdict does not degrade without the mechanism): the
  framing changes to a generic adhesion study, in the same venue.
- **MLIP validation fails at G6:** the registered fallback applies; if it ends in an
  inconclusive MLIP verdict, the free-energy claims (C1, C2) are reported inconclusive
  and the paper becomes a methods-and-failure-map report.
