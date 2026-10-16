"""Analytic benchmarks for the sensitivity estimators (Task 4d).

These are mathematical test functions with indices known in closed form. Their constants
are the conventional ones of the test functions, not physical parameters.

Ishigami (independent inputs X_i ~ U(-pi, pi)):
    Y = sin X1 + a sin^2 X2 + b X3^4 sin X1.
    V1 = (1 + b pi^4 / 5)^2 / 2,  V2 = a^2 / 8,  V3 = 0,  V13 = 8 b^2 pi^8 / 225,
    V = a^2 / 8 + b pi^4 / 5 + b^2 pi^8 / 18 + 1/2;
    S_i = V_i / V;  ST1 = (V1 + V13) / V,  ST2 = V2 / V,  ST3 = V13 / V.
    For independent inputs the Shapley effect splits each interaction equally:
    Sh1 = (V1 + V13/2) / V, Sh2 = V2 / V, Sh3 = (V13/2) / V.

Linear model with correlated Gaussian inputs, Y = beta^T X, X ~ N(mu, Sigma):
    the conditional variance of Y given X_{-J} is beta_J^T Sigma_{J|-J} beta_J with the
    Gaussian conditional covariance Sigma_{J|-J} = Sigma_JJ - Sigma_{J,-J} Sigma_{-J,-J}^-1 Sigma_{-J,J},
    so every cost c(J) = E[Var(Y | X_{-J})] is exact and the Shapley effects follow from the
    subset formula. For three inputs with only X2 and X3 correlated (rho) the closed form is
    (Owen and Prieur 2017; Iooss and Prieur 2019):
        sigma^2 = b1^2 s1^2 + b2^2 s2^2 + b3^2 s3^2 + 2 rho b2 b3 s2 s3,
        Sh1 = b1^2 s1^2 / sigma^2,
        Sh2 = (b2^2 s2^2 (1 - rho^2/2) + rho b2 b3 s2 s3 + b3^2 s3^2 rho^2/2) / sigma^2,
        Sh3 = (b3^2 s3^2 (1 - rho^2/2) + rho b2 b3 s2 s3 + b2^2 s2^2 rho^2/2) / sigma^2.
"""
from itertools import combinations
from math import factorial

import numpy as np

from nacre.screen.priors import Prior
from nacre.screen.sampling import JointPrior, gaussian_to_spearman

ISHIGAMI_A, ISHIGAMI_B = 7.0, 0.1


def ishigami(x, a=ISHIGAMI_A, b=ISHIGAMI_B):
    """Ishigami function on {"x1", "x2", "x3"} -> {"y"}."""
    x1, x2, x3 = (np.asarray(x[k], float) for k in ("x1", "x2", "x3"))
    return {"y": np.sin(x1) + a * np.sin(x2) ** 2 + b * x3 ** 4 * np.sin(x1)}


def ishigami_priors():
    return tuple(Prior("x%d" % i, "x%d" % i, "1", "uniform", {"low": -np.pi, "high": np.pi}, "benchmark")
                 for i in (1, 2, 3))


def ishigami_exact(a=ISHIGAMI_A, b=ISHIGAMI_B):
    """Exact first-order, total-order and Shapley indices of the Ishigami function."""
    pi = np.pi
    v1 = 0.5 * (1 + b * pi ** 4 / 5) ** 2
    v2 = a ** 2 / 8
    v13 = 8 * b ** 2 * pi ** 8 / 225
    v = a ** 2 / 8 + b * pi ** 4 / 5 + b ** 2 * pi ** 8 / 18 + 0.5
    return {"first_order": {"x1": v1 / v, "x2": v2 / v, "x3": 0.0},
            "total_order": {"x1": (v1 + v13) / v, "x2": v2 / v, "x3": v13 / v},
            "shapley": {"x1": (v1 + v13 / 2) / v, "x2": v2 / v, "x3": v13 / 2 / v},
            "variance": v}


def linear_model(beta):
    beta = np.asarray(beta, float)

    def model(x):
        return {"y": sum(beta[i] * np.asarray(x["x%d" % (i + 1)], float) for i in range(len(beta)))}
    return model


def linear_gaussian_joint(mu, sd, pearson):
    """JointPrior of X ~ N(mu, Sigma) with Sigma = diag(sd) pearson diag(sd).

    The copula is specified by Spearman correlations; for normal marginals the Gaussian
    copula with Spearman (6/pi) arcsin(rho/2) is exactly the bivariate normal with Pearson rho.
    """
    priors = tuple(Prior("x%d" % (i + 1), "x%d" % (i + 1), "1", "normal", {"mean": float(m), "sd": float(s)},
                         "benchmark") for i, (m, s) in enumerate(zip(mu, sd)))
    rs = gaussian_to_spearman(np.asarray(pearson, float))
    np.fill_diagonal(rs, 1.0)
    return JointPrior(priors, rs)


def linear_gaussian_cost(beta, cov, free):
    """Exact c(J) = E[Var(Y | X_{-J})] = beta_J^T Sigma_{J|-J} beta_J for the free set J."""
    beta, cov = np.asarray(beta, float), np.asarray(cov, float)
    free = list(free)
    given = [i for i in range(len(beta)) if i not in free]
    if not free:
        return 0.0
    s = cov[np.ix_(free, free)]
    if given:
        s = s - cov[np.ix_(free, given)] @ np.linalg.solve(cov[np.ix_(given, given)], cov[np.ix_(given, free)])
    b = beta[free]
    return float(b @ s @ b)


def shapley_from_costs(cost, k):
    """Shapley values from a cost function on subsets: sum over J not containing i of
    |J|! (k - |J| - 1)! / k! (c(J + i) - c(J))."""
    sh = np.zeros(k)
    for i in range(k):
        others = [j for j in range(k) if j != i]
        for size in range(k):
            w = factorial(size) * factorial(k - size - 1) / factorial(k)
            for sub in combinations(others, size):
                sh[i] += w * (cost(set(sub) | {i}) - cost(set(sub)))
    return sh


def linear_gaussian_shapley_exact(beta, cov):
    """Exact normalised Shapley effects of Y = beta^T X for Gaussian X (subset formula)."""
    beta, cov = np.asarray(beta, float), np.asarray(cov, float)
    var = float(beta @ cov @ beta)
    return shapley_from_costs(lambda j: linear_gaussian_cost(beta, cov, j), len(beta)) / var


def linear_gaussian_shapley_closed_form(beta, sd, rho):
    """Closed form for three inputs with only X2 and X3 correlated (module docstring)."""
    b1, b2, b3 = beta
    s1, s2, s3 = sd
    var = b1 ** 2 * s1 ** 2 + b2 ** 2 * s2 ** 2 + b3 ** 2 * s3 ** 2 + 2 * rho * b2 * b3 * s2 * s3
    sh1 = b1 ** 2 * s1 ** 2 / var
    sh2 = (b2 ** 2 * s2 ** 2 * (1 - rho ** 2 / 2) + rho * b2 * b3 * s2 * s3 + b3 ** 2 * s3 ** 2 * rho ** 2 / 2) / var
    sh3 = (b3 ** 2 * s3 ** 2 * (1 - rho ** 2 / 2) + rho * b2 * b3 * s2 * s3 + b2 ** 2 * s2 ** 2 * rho ** 2 / 2) / var
    return np.array([sh1, sh2, sh3])
