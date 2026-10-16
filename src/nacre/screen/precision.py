"""Required precision of a governing parameter (configs/preprint/precision_method.md).

Question: how much narrower must the prior of one parameter become, the others held at
their priors, for the verdict statistic to be decided, that is for its credible interval
to clear the nearest threshold and lie inside a single verdict band?

Narrowing. The prior of parameter i is contracted about its median m_i by a factor
s in [0, 1] in its stated variable v (the quantity itself for normal and uniform priors,
its natural log for log-uniform priors, log10 of the quantity for log10 keys):
v' = m_i + s (v - m_i). Every central interval of the narrowed prior is s times as wide
as the prior's, the median and the shape are kept, and because the map is monotone the
rank correlations of the copula are unchanged. s = 1 is the prior; s = 0 fixes the
parameter at its median.

Search. With common random numbers (one set of joint draws reused at every s), the
statistic g(s) is a smooth function of s. s = 1 already decided -> "already_clears";
s = 0 still undecided -> "unreachable" (no reduction of this parameter alone decides the
verdict); otherwise a monotonicity scan on a grid followed by bisection finds the largest
s that decides it, s*. The required width is s* times the prior width (the central
95 % interval of the stated variable).
"""
import math
from dataclasses import dataclass

import numpy as np

PRIOR_WIDTH_LEVEL = 0.95
GRID = 11


def rule_level(credible_level):
    """Interval level equivalent to the band-mass rule at credible level p: 2p - 1.

    Under the frozen rule a test is inconclusive exactly when its edge lies inside the
    equal-tailed interval [q_(1-p), q_p], whose level is 2p - 1.
    """
    if not 0.5 < credible_level < 1:
        raise ValueError("the credible level must lie in (1/2, 1)")
    return 2.0 * credible_level - 1.0


def credible_interval(values, level=0.95):
    """Equal-tailed credible interval of the finite values at the given level."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    a = (1.0 - level) / 2.0
    return tuple(float(x) for x in np.quantile(v, [a, 1.0 - a]))


def decided(interval, edges):
    """True when no band edge lies inside the open interval (it sits in one band)."""
    lo, hi = interval
    return not any(lo < e < hi for e in edges)


def nearest_edge(interval, edges):
    """The band edge nearest to the interval's centre."""
    c = 0.5 * (interval[0] + interval[1])
    return min(edges, key=lambda e: abs(e - c))


def _stated(prior, x):
    """Physical value -> stated variable (log for log-uniform, log10 for log10 keys)."""
    y = np.log10(x) if prior.transform == "log10" else np.asarray(x, float)
    return np.log(y) if prior.distribution == "loguniform" else y


def _physical(prior, y):
    v = np.exp(y) if prior.distribution == "loguniform" else y
    return 10.0 ** v if prior.transform == "log10" else v


def prior_width(prior, level=PRIOR_WIDTH_LEVEL):
    """Width of the prior's central interval in the stated variable."""
    a = (1.0 - level) / 2.0
    lo, hi = _stated(prior, prior.ppf(np.array([a, 1.0 - a])))
    return float(hi - lo)


def contract(prior, x, s):
    """Physical draws x of the prior contracted by s about the median in the stated variable."""
    m = _stated(prior, prior.ppf(0.5))
    return _physical(prior, m + s * (_stated(prior, x) - m))


@dataclass
class Precision:
    status: str                 # ok | already_clears | unreachable
    width_ratio: float          # s* (None unless ok)
    prior_width: float
    required_width: float
    nearest_threshold: float
    interval_at_prior: tuple
    monotone: bool

    def as_dict(self, units, edge_name, method):
        """Entry of the results document (schema $defs/required_precision)."""
        ok = self.status == "ok"
        return {"status": self.status, "units": units, "prior_width": self.prior_width,
                "required_width": self.required_width if ok else (self.prior_width if self.status == "already_clears" else None),
                "width_ratio": self.width_ratio if ok else (1.0 if self.status == "already_clears" else None),
                "nearest_threshold": edge_name, "method": method}


def required_precision(model, joint, parameter, edges, n, seed, level=0.95, key="name", tol=1e-4,
                       statistic=credible_interval):
    """Required precision of one parameter for the verdict statistic of model's output.

    model: {input key: array} -> array of the decisive quantity. joint: JointPrior.
    parameter: name of the governing parameter. edges: band edges of the decisive
    quantity (from the frozen thresholds). statistic(values, level) -> (lo, hi).
    """
    names = joint.names
    j = names.index(parameter)
    prior = joint.priors[j]
    if prior.is_fixed:
        raise ValueError("%s is fixed: it has no prior width" % parameter)
    x = joint.sample(np.random.default_rng(seed), n)          # common random numbers
    cols = [getattr(p, key) for p in joint.priors]

    def g(s):
        xs = x.copy()
        xs[:, j] = contract(prior, x[:, j], s)
        return statistic(model({c: xs[:, i] for i, c in enumerate(cols)}), level)

    width = prior_width(prior)
    at1 = g(1.0)
    edge = nearest_edge(at1, edges)
    if decided(at1, edges):
        return Precision("already_clears", 1.0, width, width, edge, at1, True)
    if not decided(g(0.0), edges):
        return Precision("unreachable", None, width, None, edge, at1, True)
    grid = np.linspace(0.0, 1.0, GRID)
    flags = [decided(g(s), edges) for s in grid]
    monotone = all(flags[i] >= flags[i + 1] for i in range(len(flags) - 1))
    last = max(i for i, f in enumerate(flags) if f)            # largest grid s that decides
    lo, hi = grid[last], grid[last + 1]
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if decided(g(mid), edges):
            lo = mid
        else:
            hi = mid
    return Precision("ok", float(lo), width, float(lo * width), edge, at1, monotone)


def linear_gaussian_ratio(beta, sd, i, mean, edge, level=0.95, corr=None):
    """Closed form s* for Y = beta^T X, X Gaussian, one edge above the upper bound's target.

    The upper credible bound is mean + z sqrt(beta^T Sigma(s) beta), Sigma(s) with row and
    column i scaled by s; the largest s with bound <= edge solves a quadratic in s.
    """
    beta, sd = np.asarray(beta, float), np.asarray(sd, float)
    corr = np.eye(len(beta)) if corr is None else np.asarray(corr, float)
    z = float(_ndtri(0.5 + level / 2.0))
    target = ((edge - mean) / z) ** 2
    b = beta * sd
    a2 = b[i] ** 2                                   # coefficient of s^2
    a1 = 2 * b[i] * sum(corr[i, k] * b[k] for k in range(len(b)) if k != i)
    a0 = sum(corr[k, l] * b[k] * b[l] for k in range(len(b)) for l in range(len(b)) if k != i and l != i)
    disc = a1 ** 2 - 4 * a2 * (a0 - target)
    if disc < 0:
        return None
    return (-a1 + math.sqrt(disc)) / (2 * a2)


def _ndtri(p):
    from scipy import special
    return special.ndtri(p)
