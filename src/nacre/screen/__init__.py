"""Parameter screen of the preprint: priors -> Monte Carlo -> Sobol -> per-link thresholds.

Day 1 provides the interfaces and a smoke path on mock priors. Production priors come
from lit/params.yaml; thresholds are frozen from physics (P0-W4.2) before any production
screen runs, so nothing here sets a threshold or a prior.

Modules
    priors      prior-file loader; refuses mock files unless explicitly allowed
    links       per-link physical models evaluated on sampled inputs
    propagate   Monte Carlo propagation of priors through a link model
    sobol       Sobol first- and total-order indices with bootstrap confidence intervals
    thresholds  per-link threshold evaluator (interface only until W4.2)
    summary     results summary conforming to configs/preprint/results_schema.json
    smoke       the mock smoke run
"""
