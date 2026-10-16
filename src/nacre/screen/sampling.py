"""Joint sampling of the screen's inputs: marginal priors coupled by a Gaussian copula.

The parameter table states each input's marginal prior and, for correlation groups, a
Spearman rank-correlation matrix (lit/corpus/params_README.md, section 5). A Gaussian
copula realises a stated rank correlation exactly for any continuous marginals: draw
Z ~ N(0, C), map each coordinate to a probability U_i = Phi(Z_i) and then to the physical
value X_i = F_i^-1(U_i). The Pearson matrix C of the latent Gaussian follows from the
Spearman matrix R_s entry by entry,

    C_ij = 2 sin(pi R_s,ij / 6)          (and back: R_s,ij = (6 / pi) arcsin(C_ij / 2)),

because the Spearman correlation of a bivariate normal with Pearson rho is
(6 / pi) arcsin(rho / 2). Rank correlations are invariant under monotone transforms, so a
log10 key is coupled identically on either scale. Inputs with no stated correlation are
independent (identity entries). Fixed inputs are constants and must carry no correlation.

The copula also gives the conditional laws needed by dependent-input sensitivity
analysis: Z_F | Z_G = z_G is Gaussian with mean C_FG C_GG^+ z_G and covariance
C_FF - C_FG C_GG^+ C_GF.
"""
from dataclasses import dataclass, field

import numpy as np
from scipy import special

_TOL = 1e-10


def spearman_to_gaussian(rho_s):
    """Latent Gaussian (Pearson) correlation that realises Spearman rho_s under the copula."""
    return 2.0 * np.sin(np.pi * np.asarray(rho_s, dtype=float) / 6.0)


def gaussian_to_spearman(rho):
    """Spearman rank correlation of a bivariate normal with Pearson correlation rho."""
    return 6.0 / np.pi * np.arcsin(np.asarray(rho, dtype=float) / 2.0)


def _psd_factor(c):
    """L with L L^T = c for a symmetric positive semi-definite c (eigen-decomposition)."""
    w, v = np.linalg.eigh(c)
    if w.min() < -1e-9:
        raise ValueError("correlation matrix is not positive semi-definite (smallest eigenvalue %.3g)" % w.min())
    return v * np.sqrt(np.clip(w, 0.0, None))


def _check_correlation(r, k, what):
    r = np.asarray(r, dtype=float)
    if r.shape != (k, k):
        raise ValueError("%s must be %d x %d" % (what, k, k))
    if not np.all(np.isfinite(r)) or np.any(np.abs(r) > 1 + _TOL):
        raise ValueError("%s entries must be finite and lie in [-1, 1]" % what)
    if not np.allclose(r, r.T, atol=_TOL, rtol=0):
        raise ValueError("%s must be symmetric" % what)
    if not np.allclose(np.diag(r), 1.0, atol=_TOL, rtol=0):
        raise ValueError("%s must have a unit diagonal" % what)
    _psd_factor(r)
    return r


@dataclass(frozen=True, eq=False)
class JointPrior:
    """Joint prior of the sampled inputs of one regime.

    priors: tuple of nacre.screen.priors.Prior (one per input, in design order).
    spearman: k x k Spearman rank-correlation matrix (identity: independent inputs).
    pairs: the stated non-zero correlations with their sources, for the results record.
    """
    priors: tuple
    spearman: np.ndarray
    pairs: tuple = field(default=())

    def __post_init__(self):
        k = len(self.priors)
        r = _check_correlation(self.spearman, k, "Spearman matrix")
        for i, p in enumerate(self.priors):
            if p.is_fixed and np.any(np.abs(np.delete(r[i], i)) > _TOL):
                raise ValueError("fixed input %s cannot carry a correlation" % p.name)
        c = spearman_to_gaussian(r)
        np.fill_diagonal(c, 1.0)
        object.__setattr__(self, "spearman", r)
        object.__setattr__(self, "_gaussian", c)
        object.__setattr__(self, "_factor", _psd_factor(c))

    @classmethod
    def independent_of(cls, priors):
        return cls(tuple(priors), np.eye(len(priors)))

    @property
    def names(self):
        return [p.name for p in self.priors]

    @property
    def symbols(self):
        return [p.symbol for p in self.priors]

    @property
    def k(self):
        return len(self.priors)

    @property
    def gaussian_correlation(self):
        return self._gaussian.copy()

    @property
    def is_independent(self):
        return bool(np.allclose(self.spearman, np.eye(self.k), atol=_TOL, rtol=0))

    def independent(self):
        """The same marginals with the correlations removed (robustness check, Task 4e)."""
        return JointPrior.independent_of(self.priors)

    def dependence_record(self):
        """The ``dependence`` entry of a results regime (schema $defs/dependence)."""
        if self.is_independent:
            return {"method": "independent"}
        return {"method": "gaussian_copula", "rank_correlations": [dict(p) for p in self.pairs]}

    # ------------------------------------------------------------------ sampling

    def sample_latent(self, rng, n):
        """n draws of the latent Gaussian Z ~ N(0, C), shape (n, k)."""
        return rng.standard_normal((n, self.k)) @ self._factor.T

    def to_physical(self, z):
        """Map latent Gaussian draws (..., k) to physical input values through each marginal."""
        u = special.ndtr(np.asarray(z, dtype=float))
        # keep u inside (0, 1): Phi(z) rounds to 0 or 1 only for |z| > 8, far in the tails
        u = np.clip(u, np.finfo(float).tiny, 1.0 - np.finfo(float).epsneg)
        out = np.empty(u.shape, dtype=float)
        for j, p in enumerate(self.priors):
            out[..., j] = p.ppf(u[..., j])
        return out

    def sample(self, rng, n):
        """n joint draws of the physical inputs, shape (n, k), columns in design order."""
        return self.to_physical(self.sample_latent(rng, n))

    def conditional_latent(self, rng, z_given, given, free, n_inner):
        """Draws of Z_free | Z_given = z_given for each row of z_given.

        z_given: (n_outer, |given|); returns (n_outer, n_inner, |free|).
        """
        given, free = list(given), list(free)
        z_given = np.asarray(z_given, dtype=float).reshape(-1, len(given))
        c = self._gaussian
        if given:
            a = c[np.ix_(free, given)] @ np.linalg.pinv(c[np.ix_(given, given)])
            mean = z_given @ a.T
            cov = c[np.ix_(free, free)] - a @ c[np.ix_(given, free)]
        else:
            mean = np.zeros((z_given.shape[0], len(free)))
            cov = c[np.ix_(free, free)]
        cov = 0.5 * (cov + cov.T)
        factor = _psd_factor(cov)
        e = rng.standard_normal((z_given.shape[0], n_inner, len(free)))
        return mean[:, None, :] + e @ factor.T
