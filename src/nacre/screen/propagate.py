"""Monte Carlo propagation of priors through a link model."""
import numpy as np


def sample_inputs(priors, n, rng):
    """Draw n independent samples of every prior; returns {name: array}."""
    if n < 1:
        raise ValueError("number of draws must be at least 1")
    return {p.name: p.sample(rng, n) for p in priors}


def monte_carlo(model, priors, n, rng):
    """Propagate n prior draws through model; returns (inputs, outputs) dicts of arrays."""
    x = sample_inputs(priors, n, rng)
    return x, model(x)


QUANTILE_LEVELS = (0.025, 0.05, 0.25, 0.5, 0.75, 0.95, 0.975)


def describe(values, levels=QUANTILE_LEVELS):
    """Mean, standard deviation and quantiles of the finite draws of one output."""
    v = np.asarray(values, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        raise ValueError("no draw of this quantity lies in its physical domain")
    q = np.quantile(v, levels)
    return {"n_valid": int(v.size), "mean": float(v.mean()), "sd": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "quantiles": {repr(float(p)): float(x) for p, x in zip(levels, q)}}
