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


def propagate_chain(evaluate, joint, n, seed, chunk=2 ** 17, key="symbol", redraw=(), redraw_seed=None):
    """Monte Carlo propagation of a joint prior through the chain, in seeded chunks.

    evaluate: x -> (outputs {link: {quantity: array}}, masses {link: {name: BoundaryMass}})
    (nacre.screen.chain.evaluate). The n draws are generated in chunks of at most `chunk`
    rows, each from its own child of SeedSequence(seed), so no array grows beyond
    chunk x (number of inputs) and the result is reproducible from (seed, chunk). Only the
    outputs are kept: one float64 array of n values per quantity.
    Returns (outputs, masses) with outputs {link: {quantity: (n,) array}} and the boundary
    masses summed over chunks.

    Common random numbers: the registered states of a regime are propagated with the same
    seed, so draw i of every state shares the inputs common to the states and per-draw
    indicators combine across states (worst state, path sum, joint masses). The inputs
    named in ``redraw`` (state-specific keys such as T and t_proc) are drawn again from their
    marginals with redraw_seed, so they are independent between states; an input that is
    correlated with another cannot be redrawn this way and is refused.
    """
    idx = [j for j, p in enumerate(joint.priors) if getattr(p, key) in set(redraw)]
    for j in idx:
        if np.any(np.delete(joint.spearman[j], j) != 0):
            raise ValueError("state-specific input %s is correlated with another input" % getattr(joint.priors[j], key))
    rseqs = np.random.SeedSequence(redraw_seed).spawn((n + chunk - 1) // chunk) if idx else None
    if n < 1:
        raise ValueError("number of draws must be at least 1")
    n_chunks = (n + chunk - 1) // chunk
    cols = [getattr(p, key) for p in joint.priors]
    outputs, masses = None, None
    for c, seq in enumerate(np.random.SeedSequence(seed).spawn(n_chunks)):
        m = min(chunk, n - c * chunk)
        xs = joint.sample(np.random.default_rng(seq), m)
        if idx:
            rr = np.random.default_rng(rseqs[c])
            for j in idx:
                xs[:, j] = joint.priors[j].ppf(rr.random(m))
        out, mass = evaluate({col: xs[:, j] for j, col in enumerate(cols)})
        if outputs is None:
            outputs = {lk: {q: np.empty(n) for q in d} for lk, d in out.items()}
            masses = {lk: dict(d) for lk, d in mass.items()}
        else:
            masses = {lk: {q: masses[lk][q] + bm for q, bm in d.items()} for lk, d in mass.items()}
        for lk, d in out.items():
            for q, v in d.items():
                outputs[lk][q][c * chunk:c * chunk + m] = v
    return outputs, masses
