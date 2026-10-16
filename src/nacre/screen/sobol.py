"""Variance-based (Sobol) sensitivity indices with bootstrap confidence intervals.

Saltelli design with N base rows and k inputs: matrices A and B of independent prior
draws and, for each input i, A_B^(i) (A with column i taken from B), giving N (k + 2)
model evaluations. Estimators (Saltelli et al. 2010 for first order, Jansen 1999 for total
order):

    S_i  = mean(f_B (f_AB_i - f_A)) / Var(f)
    ST_i = mean((f_A - f_AB_i)^2) / (2 Var(f))

with Var(f) from the pooled A and B evaluations. Confidence intervals are percentile
bootstrap intervals over the N base rows. Rows where any of the evaluations involved is
non-finite are dropped for that input. Validation on analytic test functions beyond the
linear case is part of P0-W4.2.
"""
import numpy as np



def saltelli_design(priors, n_base, rng):
    """Return (A, B, names): two (n_base, k) matrices of independent prior draws."""
    names = [p.name for p in priors]
    a = np.column_stack([p.sample(rng, n_base) for p in priors])
    b = np.column_stack([p.sample(rng, n_base) for p in priors])
    return a, b, names


def _evaluate(model, mat, names):
    return model({n: mat[:, j] for j, n in enumerate(names)})


def _indices(fa, fb, fab):
    var = np.var(np.concatenate([fa, fb]), ddof=1)
    if not var > 0:
        return np.nan, np.nan
    return np.mean(fb * (fab - fa)) / var, np.mean((fa - fab) ** 2) / (2.0 * var)


def sobol_indices(model, priors, outputs, n_base, rng, n_bootstrap=200, confidence=0.95):
    """Sobol first- and total-order indices of each output with respect to each prior.

    model: link model (dict of input arrays -> dict of output arrays).
    outputs: names of the model outputs to analyse.
    Returns ({output: {input: {"first_order": {...}, "total_order": {...}}}}, design) where
    each index dict is {"estimate", "ci_low", "ci_high"} and design records the sample sizes.
    """
    if n_base < 2:
        raise ValueError("Sobol design needs at least 2 base rows")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie in (0, 1)")
    a, b, names = saltelli_design(priors, n_base, rng)
    ya, yb = _evaluate(model, a, names), _evaluate(model, b, names)
    yab = []
    for j in range(len(names)):
        ab = a.copy()
        ab[:, j] = b[:, j]
        yab.append(_evaluate(model, ab, names))
    boot = rng.integers(0, n_base, size=(n_bootstrap, n_base)) if n_bootstrap else None
    alpha = (1.0 - confidence) / 2.0
    result = {}
    for out in outputs:
        fa, fb = np.asarray(ya[out], float), np.asarray(yb[out], float)
        per_input = {}
        for j, name in enumerate(names):
            fab = np.asarray(yab[j][out], float)
            ok = np.isfinite(fa) & np.isfinite(fb) & np.isfinite(fab)
            s1, st = _indices(fa[ok], fb[ok], fab[ok])
            lo1 = hi1 = s1
            lot = hit = st
            if boot is not None:
                samples = []
                for rows in boot:
                    r = rows[ok[rows]]
                    if r.size > 1:
                        samples.append(_indices(fa[r], fb[r], fab[r]))
                if samples:
                    s = np.array(samples)
                    lo1, hi1 = np.nanquantile(s[:, 0], [alpha, 1 - alpha])
                    lot, hit = np.nanquantile(s[:, 1], [alpha, 1 - alpha])
            per_input[name] = {
                "first_order": {"estimate": float(s1), "ci_low": float(lo1), "ci_high": float(hi1)},
                "total_order": {"estimate": float(st), "ci_low": float(lot), "ci_high": float(hit)},
            }
        result[out] = per_input
    design = {"method": "Saltelli design; Saltelli 2010 first order, Jansen total order; "
                        "percentile bootstrap",
              "base_samples": int(n_base), "evaluations": int(n_base * (len(names) + 2)),
              "bootstrap_resamples": int(n_bootstrap), "confidence_level": float(confidence)}
    return result, design
