"""Joint sampler: Gaussian copula for stated rank correlations, independence otherwise."""
import numpy as np
import pytest
from scipy import stats

from nacre.screen.priors import Prior
from nacre.screen.sampling import JointPrior, gaussian_to_spearman, spearman_to_gaussian


def _priors():
    return (Prior("u", "u", "1", "uniform", {"low": 0.0, "high": 2.0}),
            Prior("l", "l", "1", "loguniform", {"low": 1e-3, "high": 1e1}),
            Prior("n", "n", "1", "normal", {"mean": 3.0, "sd": 0.5}),
            Prior("k", "k", "1", "normal", {"mean": -6.0, "sd": 0.5}, transform="log10"))


RS = np.array([[1.0, 0.6, -0.4, 0.0],
               [0.6, 1.0, 0.0, 0.3],
               [-0.4, 0.0, 1.0, 0.0],
               [0.0, 0.3, 0.0, 1.0]])


def test_spearman_gaussian_conversion_round_trips_and_fixes_the_ends():
    r = np.linspace(-1, 1, 41)
    assert np.allclose(gaussian_to_spearman(spearman_to_gaussian(r)), r, atol=1e-14)
    assert spearman_to_gaussian(0.0) == 0.0
    assert spearman_to_gaussian(1.0) == pytest.approx(1.0, abs=1e-15)
    assert spearman_to_gaussian(-1.0) == pytest.approx(-1.0, abs=1e-15)


def test_copula_realises_the_stated_rank_correlations():
    j = JointPrior(_priors(), RS)
    x = j.sample(np.random.default_rng(0), 200_000)
    emp = stats.spearmanr(x).statistic
    assert np.max(np.abs(emp - RS)) < 0.01


def test_copula_preserves_each_marginal():
    j = JointPrior(_priors(), RS)
    x = j.sample(np.random.default_rng(1), 200_000)
    levels = np.array([0.05, 0.25, 0.5, 0.75, 0.95])
    for col, p in enumerate(j.priors):
        assert np.allclose(np.quantile(x[:, col], levels), p.ppf(levels), rtol=0.02)


def test_log10_key_is_sampled_as_the_physical_quantity():
    p = _priors()[3]
    y = np.log10(p.sample(np.random.default_rng(2), 100_000))
    assert y.mean() == pytest.approx(-6.0, abs=0.01)
    assert y.std() == pytest.approx(0.5, rel=0.02)


def test_identity_means_independent_and_independent_drops_correlations():
    j = JointPrior(_priors(), RS)
    assert not j.is_independent
    ind = j.independent()
    assert ind.is_independent
    assert ind.dependence_record() == {"method": "independent"}
    x = ind.sample(np.random.default_rng(3), 100_000)
    assert np.max(np.abs(stats.spearmanr(x).statistic - np.eye(4))) < 0.01


@pytest.mark.parametrize("bad", [
    np.array([[1.0, 0.5], [0.4, 1.0]]),          # not symmetric
    np.array([[1.0, 0.0], [0.0, 0.9]]),          # diagonal not one
    np.array([[1.0, 1.2], [1.2, 1.0]]),          # outside [-1, 1]
])
def test_invalid_correlation_matrices_are_rejected(bad):
    with pytest.raises(ValueError):
        JointPrior(_priors()[:2], bad)


def test_non_positive_semidefinite_matrix_is_rejected():
    bad = np.array([[1.0, 0.9, -0.9], [0.9, 1.0, 0.9], [-0.9, 0.9, 1.0]])
    with pytest.raises(ValueError, match="positive semi-definite"):
        JointPrior(_priors()[:3], bad)


def test_fixed_input_cannot_carry_a_correlation():
    pri = (Prior("a", "a", "1", "uniform", {"low": 0, "high": 1}), Prior("f", "f", "1", "fixed", {"value": 2.0}))
    with pytest.raises(ValueError, match="fixed"):
        JointPrior(pri, np.array([[1.0, 0.5], [0.5, 1.0]]))
    x = JointPrior.independent_of(pri).sample(np.random.default_rng(0), 10)
    assert np.all(x[:, 1] == 2.0)


def test_conditional_latent_matches_the_gaussian_conditional():
    j = JointPrior(_priors(), RS)
    c = j.gaussian_correlation
    given, free = [0, 2], [1, 3]
    zg = np.array([[1.0, -0.5]])
    draws = j.conditional_latent(np.random.default_rng(4), zg, given, free, 200_000)[0]
    a = c[np.ix_(free, given)] @ np.linalg.inv(c[np.ix_(given, given)])
    mean = a @ zg[0]
    cov = c[np.ix_(free, free)] - a @ c[np.ix_(given, free)]
    assert np.allclose(draws.mean(axis=0), mean, atol=0.01)
    assert np.allclose(np.cov(draws.T), cov, atol=0.01)


def test_sampling_is_reproducible_from_the_seed():
    j = JointPrior(_priors(), RS)
    a = j.sample(np.random.default_rng(9), 1000)
    b = j.sample(np.random.default_rng(9), 1000)
    assert np.array_equal(a, b)
