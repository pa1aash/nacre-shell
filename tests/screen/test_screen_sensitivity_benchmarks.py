"""Sensitivity estimators against analytic benchmarks (Task 4d).

Ishigami (independent inputs): Sobol first- and total-order indices and Shapley effects
against their closed forms. Linear model with correlated Gaussian inputs: Shapley effects
against the closed form of Owen and Prieur (2017) and the exact subset formula. Seeds are
fixed, so each tolerance is a deterministic check of the estimator, not a flaky bound.
"""
import numpy as np
import pytest

from nacre.screen import benchmarks as bm
from nacre.screen import shapley, sobol
from nacre.screen.sampling import JointPrior

BETA, SD, RHO = (1.0, 1.0, 1.0), (1.0, 1.0, 2.0), 0.7
PEARSON = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, RHO], [0.0, RHO, 1.0]])
COV = np.diag(SD) @ PEARSON @ np.diag(SD)


@pytest.fixture(scope="module")
def ishigami_sobol():
    return sobol.sobol_indices(bm.ishigami, bm.ishigami_priors(), ["y"], 2 ** 14, np.random.default_rng(1),
                               n_bootstrap=200)[0]["y"]


def test_sobol_ishigami_matches_the_exact_indices(ishigami_sobol):
    ex = bm.ishigami_exact()
    err = max(abs(ishigami_sobol[k][o]["estimate"] - ex[o][k])
              for k in ("x1", "x2", "x3") for o in ("first_order", "total_order"))
    assert err < 0.025


def test_sobol_ishigami_intervals_bracket_their_estimates(ishigami_sobol):
    for d in ishigami_sobol.values():
        for o in ("first_order", "total_order"):
            assert d[o]["ci_low"] <= d[o]["estimate"] <= d[o]["ci_high"]


def test_sobol_convergence_by_doubling_reaches_the_stated_target():
    target = 0.02
    _, design, conv = sobol.size_and_verify(bm.ishigami, bm.ishigami_priors(), ["y"], target, seed=3, pilot=512)
    assert conv["converged"]
    assert conv["max_ci_half_width"] <= target and conv["max_estimate_shift"] <= target
    assert design["base_samples"] == conv["base_samples_doubled"] == 2 * conv["base_samples"]


def test_sobol_sizing_refuses_an_unaffordable_target():
    with pytest.raises(ValueError, match="base rows"):
        sobol.size_and_verify(bm.ishigami, bm.ishigami_priors(), ["y"], 1e-4, seed=0, pilot=256, max_base=2 ** 12)


def test_linear_gaussian_closed_form_equals_the_subset_formula():
    assert np.allclose(bm.linear_gaussian_shapley_closed_form(BETA, SD, RHO),
                       bm.linear_gaussian_shapley_exact(BETA, COV), rtol=0, atol=1e-14)


def test_shapley_linear_gaussian_matches_the_closed_form():
    j = bm.linear_gaussian_joint((0.0, 0.0, 0.0), SD, PEARSON)
    sh, rec = shapley.shapley_effects(bm.linear_model(BETA), j, ["y"], 20_000, 4000, 3, np.random.default_rng(5))
    est = np.array([sh["y"]["x%d" % i]["estimate"] for i in (1, 2, 3)])
    exact = bm.linear_gaussian_shapley_closed_form(BETA, SD, RHO)
    assert np.max(np.abs(est - exact)) < 0.02
    assert est.sum() == pytest.approx(1.0, abs=1e-12)
    for i, e in zip((1, 2, 3), exact):
        d = sh["y"]["x%d" % i]
        assert d["ci_low"] <= e <= d["ci_high"]


def test_shapley_permutation_design_agrees():
    j = bm.linear_gaussian_joint((0.0, 0.0, 0.0), SD, PEARSON)
    sh, _ = shapley.shapley_effects(bm.linear_model(BETA), j, ["y"], 20_000, 2000, 3, np.random.default_rng(7),
                                    design="permutations", n_perm=600)
    est = np.array([sh["y"]["x%d" % i]["estimate"] for i in (1, 2, 3)])
    assert np.max(np.abs(est - bm.linear_gaussian_shapley_closed_form(BETA, SD, RHO))) < 0.04


def test_shapley_ishigami_independent_splits_interactions_equally():
    j = JointPrior.independent_of(bm.ishigami_priors())
    sh, _ = shapley.shapley_effects(bm.ishigami, j, ["y"], 20_000, 4000, 3, np.random.default_rng(6))
    ex = bm.ishigami_exact()["shapley"]
    assert max(abs(sh["y"][k]["estimate"] - ex[k]) for k in ex) < 0.02


def test_shapley_without_correlation_is_the_variance_share_of_a_linear_model():
    j = bm.linear_gaussian_joint((0.0, 0.0, 0.0), SD, np.eye(3))
    sh, _ = shapley.shapley_effects(bm.linear_model(BETA), j, ["y"], 20_000, 2000, 3, np.random.default_rng(8))
    share = np.array(BETA) ** 2 * np.array(SD) ** 2
    share = share / share.sum()
    est = np.array([sh["y"]["x%d" % i]["estimate"] for i in (1, 2, 3)])
    assert np.max(np.abs(est - share)) < 0.02


def test_dependence_check_reports_rank_agreement():
    j = bm.linear_gaussian_joint((0.0, 0.0, 0.0), SD, PEARSON)
    rec, dep, ind = shapley.dependence_check(bm.linear_model(BETA), j, ["y"], np.random.default_rng(9),
                                             n_var=5000, n_outer=1000, n_inner=3, n_bootstrap=0)
    assert rec["alternative"] == "independent"
    ra = rec["rank_agreement"]["y"]
    assert -1 <= ra["kendall_tau"] <= 1 and ra["same_top"]          # x3 carries the most variance either way


def test_rank_agreement_detects_a_reversal():
    assert shapley.rank_agreement({"a": 0.1, "b": 0.5, "c": 0.4}, {"a": 0.1, "b": 0.5, "c": 0.4}) == \
        {"kendall_tau": 1.0, "same_top": True}
    r = shapley.rank_agreement({"a": 0.1, "b": 0.5, "c": 0.4}, {"a": 0.5, "b": 0.1, "c": 0.4})
    assert r["kendall_tau"] < 0 and not r["same_top"]
