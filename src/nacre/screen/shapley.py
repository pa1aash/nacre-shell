"""Shapley effects: variance-based sensitivity indices valid for dependent inputs (N2).

With correlated inputs the Sobol decomposition no longer separates the variance into
per-input shares. The Shapley effect of input i (Owen 2014; Song, Nelson and Staum 2016)
is its game-theoretic share of Var(Y) under the cost function

    c(J) = E[ Var(Y | X_{-J}) ]          (variance left when only the inputs outside J are known),

    Sh_i = sum over J not containing i of  |J|! (k - |J| - 1)! / k!  (c(J + i) - c(J)) / Var(Y).

The effects are non-negative for this cost, sum to one over the inputs whatever the
dependence, and reduce for independent inputs to the first-order index plus an equal share
of every interaction the input takes part in. A correlated input that does not enter the
model can still receive a share, by explaining variance through its partners; that is the
intended reading ("how much of Var(Y) is attributable to not knowing X_i").

Estimation. Each needed cost is estimated by double-loop Monte Carlo under the joint
prior: n_outer draws of the whole latent vector; for each, n_inner draws of the free
coordinates from their Gaussian-copula conditional given the others
(JointPrior.conditional_latent); c(J) is the mean over outer draws of the inner sample
variance (ddof = 1, unbiased for each conditional variance). c(empty) = 0 and c(all) =
Var(Y) from n_var independent joint draws, which normalises the effects to sum to one.
Two designs share this machinery:

  * "subsets": every subset of the k varying inputs (2^k - 2 estimated costs), combined
    with the exact Shapley weights. Practical up to about 14 varying inputs.
  * "permutations": m random permutations (Song et al. 2016, Algorithm 1); the costs of
    the subsets the permutations visit are estimated once and reused.

Confidence intervals are percentile bootstrap intervals that resample the outer draws (the
same resample for every cost) and the variance draws. Draws whose output is outside its
physical domain (NaN) are dropped: an outer draw with fewer than two finite inner values
does not count, so the effects describe the variance of the in-domain part of the output.
"""
from math import factorial

import warnings

import numpy as np
from scipy import stats

from nacre.screen.sampling import JointPrior

METHOD = "Shapley effects, double-loop Monte Carlo under the Gaussian copula ({design}); percentile bootstrap"
_BOOT_CHUNK = 50


def _popcount(x):
    return bin(x).count("1")


def _weights_subsets(k):
    """(k, 2^k) matrix A with Sh = A c / Var for the exact Shapley weights."""
    a = np.zeros((k, 2 ** k))
    for i in range(k):
        bit = 1 << i
        for mask in range(2 ** k):
            if mask & bit:
                continue
            s = _popcount(mask)
            w = factorial(s) * factorial(k - s - 1) / factorial(k)
            a[i, mask | bit] += w
            a[i, mask] -= w
    return a


def _weights_permutations(k, perms):
    a = np.zeros((k, 2 ** k))
    for perm in perms:
        prev = 0
        for i in perm:
            new = prev | (1 << int(i))
            a[i, new] += 1.0 / len(perms)
            a[i, prev] -= 1.0 / len(perms)
            prev = new
    return a


def _evaluate(model, x, cols, outputs, chunk):
    n = x.shape[0]
    step = chunk or n
    acc = {o: [] for o in outputs}
    for s in range(0, n, step):
        y = model({c: x[s:s + step, j] for j, c in enumerate(cols)})
        for o in outputs:
            acc[o].append(np.asarray(y[o], float))
    return {o: np.concatenate(v) for o, v in acc.items()}


def _inner_variances(model, joint, cols, players, mask, outputs, n_outer, n_inner, rng, chunk):
    """{output: (n_outer,) inner sample variances, NaN where fewer than 2 finite values}."""
    free = [players[b] for b in range(len(players)) if mask >> b & 1]
    given = [j for j in range(joint.k) if j not in free]
    z = joint.sample_latent(rng, n_outer)
    zf = joint.conditional_latent(rng, z[:, given], given, free, n_inner)
    full = np.repeat(z[:, None, :], n_inner, axis=1)
    full[:, :, free] = zf
    x = joint.to_physical(full.reshape(-1, joint.k))
    y = _evaluate(model, x, cols, outputs, chunk)
    out = {}
    for o in outputs:
        v = y[o].reshape(n_outer, n_inner)
        fin = np.isfinite(v)
        cnt = fin.sum(axis=1)
        vz = np.where(fin, v, 0.0)
        mean = vz.sum(axis=1) / np.maximum(cnt, 1)
        ss = (np.where(fin, v - mean[:, None], 0.0) ** 2).sum(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            out[o] = np.where(cnt >= 2, ss / (cnt - 1), np.nan)
    return out


def _count_chunks(seed_seq, n, n_bootstrap):
    seqs = seed_seq.spawn((n_bootstrap + _BOOT_CHUNK - 1) // _BOOT_CHUNK) if n_bootstrap else []
    for c, sq in enumerate(seqs):
        m = min(_BOOT_CHUNK, n_bootstrap - c * _BOOT_CHUNK)
        r = np.random.default_rng(sq)
        counts = np.empty((m, n))
        for i in range(m):
            counts[i] = np.bincount(r.integers(0, n, n), minlength=n)
        yield counts


def _weighted_var(counts, y):
    ok = np.isfinite(y)
    c = np.where(ok, y - np.nanmean(y), 0.0)
    w = counts * ok
    n = w.sum(axis=-1)
    s1 = w @ c if w.ndim > 1 else (w * c).sum()
    s2 = w @ (c * c) if w.ndim > 1 else (w * c * c).sum()
    return (s2 - s1 ** 2 / n) / (n - 1)


def shapley_effects(model, joint, outputs, n_var, n_outer, n_inner, rng, key="name", design="subsets",
                    n_perm=None, n_bootstrap=200, confidence=0.95, chunk=2 ** 16):
    """Normalised Shapley effects of each output with respect to each varying input.

    joint: JointPrior (dependent or independent). Returns ({output: {input: {"estimate",
    "ci_low", "ci_high"}}}, design_record).
    """
    if not isinstance(joint, JointPrior):
        raise TypeError("joint must be a JointPrior")
    if n_inner < 2 or n_outer < 2 or n_var < 2:
        raise ValueError("n_var, n_outer and n_inner must each be at least 2")
    players = [j for j, p in enumerate(joint.priors) if not p.is_fixed]
    k = len(players)
    cols = [getattr(p, key) for p in joint.priors]
    names = [joint.priors[j].name for j in players]
    if design == "subsets":
        a = _weights_subsets(k)
    elif design == "permutations":
        if not n_perm:
            raise ValueError("the permutation design needs n_perm")
        a = _weights_permutations(k, [rng.permutation(k) for _ in range(n_perm)])
    else:
        raise ValueError("design must be 'subsets' or 'permutations'")
    full = 2 ** k - 1
    needed = [m for m in range(1, full) if np.any(a[:, m] != 0)]
    yv = _evaluate(model, joint.sample(rng, n_var), cols, outputs, chunk)
    v = {o: np.full((len(needed), n_outer), np.nan) for o in outputs}
    for r, mask in enumerate(needed):
        iv = _inner_variances(model, joint, cols, players, mask, outputs, n_outer, n_inner, rng, chunk)
        for o in outputs:
            v[o][r] = iv[o]
    alpha = (1.0 - confidence) / 2.0
    boot_seq = np.random.SeedSequence(int(rng.integers(0, 2 ** 63)))
    outer_seq, var_seq = boot_seq.spawn(2)
    result = {}
    for o in outputs:
        ok = np.isfinite(v[o])
        vz = np.where(ok, v[o], 0.0)
        var = _weighted_var(np.ones(n_var), yv[o])
        cost = np.zeros(2 ** k)
        with np.errstate(invalid="ignore", divide="ignore"):
            cost[needed] = vz.sum(axis=1) / ok.sum(axis=1)
        cost[full] = var
        est = a @ cost / var
        lo = hi = est
        if n_bootstrap:
            boots = []
            for co, cv in zip(_count_chunks(outer_seq, n_outer, n_bootstrap),
                              _count_chunks(var_seq, n_var, n_bootstrap)):
                vb = _weighted_var(cv, yv[o])                              # (m,)
                cb = np.zeros((co.shape[0], 2 ** k))
                with np.errstate(invalid="ignore", divide="ignore"):
                    cb[:, needed] = (co @ vz.T) / (co @ ok.T.astype(float))
                cb[:, full] = vb
                boots.append((cb @ a.T) / vb[:, None])
            boots = np.vstack(boots)
            with np.errstate(all="ignore"), warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)     # an index with no finite resample stays NaN
                lo, hi = np.nanquantile(boots, [alpha, 1 - alpha], axis=0)
        result[o] = {n: {"estimate": float(est[i]), "ci_low": float(lo[i]), "ci_high": float(hi[i])}
                     for i, n in enumerate(names)}
    label = "all %d subsets" % (2 ** k) if design == "subsets" else "%d random permutations" % n_perm
    rec = {"method": METHOD.format(design=label), "n_var": int(n_var), "n_outer": int(n_outer),
           "n_inner": int(n_inner), "costs_estimated": len(needed),
           "evaluations": int(n_var + len(needed) * n_outer * n_inner),
           "bootstrap_resamples": int(n_bootstrap), "confidence_level": float(confidence)}
    return result, rec


def rank_agreement(a, b):
    """Agreement of two parameter rankings {input: index}: Kendall tau and same top input."""
    keys = sorted(set(a) & set(b))
    xa = np.array([a[k] for k in keys], float)
    xb = np.array([b[k] for k in keys], float)
    if len(keys) < 2 or np.all(xa == xa[0]) or np.all(xb == xb[0]):
        tau = 1.0 if np.array_equal(np.argsort(xa), np.argsort(xb)) else 0.0
    else:
        tau = float(stats.kendalltau(xa, xb).statistic)
    return {"kendall_tau": tau, "same_top": bool(keys[int(np.argmax(xa))] == keys[int(np.argmax(xb))])}


def dependence_check(model, joint, outputs, rng, **kw):
    """Robustness of the Shapley ranking to the correlation assumption (Task 4e).

    Recomputes the effects with the correlations removed and returns the schema's
    dependence_check record ({"alternative": "independent", "rank_agreement": {...}}) keyed
    by output, together with both sets of effects.
    """
    dep, _ = shapley_effects(model, joint, outputs, rng=rng, **kw)
    ind, _ = shapley_effects(model, joint.independent(), outputs, rng=rng, **kw)
    agree = {o: rank_agreement({k: v["estimate"] for k, v in dep[o].items()},
                               {k: v["estimate"] for k, v in ind[o].items()}) for o in outputs}
    return {"alternative": "independent", "rank_agreement": agree}, dep, ind
