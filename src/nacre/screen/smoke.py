"""Smoke run of the screen on mock priors.

Exercises the whole path (prior loader -> Monte Carlo -> Sobol -> summary) on synthetic
priors and writes a schema-conforming summary. It refuses production priors and refuses
to write anywhere but a ``mock`` directory, so a smoke output can never be mistaken for a
result. Thresholds are not evaluated (they are frozen in P0-W4.2).
"""
from pathlib import Path

import numpy as np

from nacre.screen import boundary, links, priors, propagate, sobol, summary

MAX_DRAWS = 10_000


def run(root, prior_path, out_path, draws=4096, sobol_base=512, bootstrap=200, seed=0,
        confidence=0.95, allow_mock=False):
    root = Path(root)
    out_path = Path(out_path)
    if "mock" not in out_path.parts:
        raise ValueError("smoke output must live in a 'mock' directory, got %s" % out_path)
    ps = priors.load_priors(prior_path, allow_mock=allow_mock)
    if not ps.mock:
        raise ValueError("the smoke run uses mock priors only")
    config = {"kind": "smoke", "prior_file": Path(prior_path).as_posix(), "draws": draws,
              "sobol_base": sobol_base, "bootstrap": bootstrap, "seed": seed,
              "confidence": confidence, "links": sorted(links.LINKS)}
    children = np.random.SeedSequence(seed).spawn(len(ps.regimes))
    regimes = {}
    for child, regime in zip(children, sorted(ps.regimes)):
        regime_seed = int(child.generate_state(1)[0])
        mc_seq, sobol_seq = np.random.SeedSequence(regime_seed).spawn(2)
        pri = ps.parameters(regime)
        names = [p.name for p in pri]
        out_links = {}
        total = draws
        design = None
        masses = {}
        for link, (model, inputs, outputs) in links.LINKS.items():
            if not set(inputs) <= set(names):
                continue
            x, y = propagate.monte_carlo(model, pri, draws, np.random.default_rng(mc_seq))
            masses[link] = ({"cos_theta": boundary.clip_cos_theta(x["cos_theta"])[1].as_dict()}
                            if "cos_theta" in x else {})
            quantities = {}
            for name, meta in outputs.items():
                d = propagate.describe(y[name])
                quantities[name] = {"symbol": meta.symbol, "units": meta.units, **d}
            idx_s, design = sobol.sobol_indices(model, pri, list(outputs), sobol_base,
                                                np.random.default_rng(sobol_seq),
                                                n_bootstrap=bootstrap, confidence=confidence)
            total += design["evaluations"]
            out_links[link] = {"quantities": quantities, "sobol": idx_s, "threshold_evaluation": None}
        if not out_links:
            continue
        if total > MAX_DRAWS:
            raise ValueError("smoke run exceeds %d model evaluations (%d)" % (MAX_DRAWS, total))
        regimes[regime] = {"draws": draws, "seed": regime_seed, "sobol_design": design,
                           "parameters": names, "links": out_links, "boundary_mass": masses}
    doc = summary.build(regimes, summary.provenance(root, config, ps), mock=True)
    return summary.write(doc, out_path), doc
