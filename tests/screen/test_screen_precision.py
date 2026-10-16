"""Required-precision algorithm on the analytic benchmark (configs/preprint/precision_method.md).

For Y = beta^T X with Gaussian X, narrowing the prior of X_i by s scales its standard
deviation by s, the upper 95 % credible bound is mean + z sqrt(beta^T Sigma(s) beta), and
the largest s that brings it under a band edge solves a quadratic (closed form in
nacre.screen.precision.linear_gaussian_ratio).
"""
import numpy as np
import pytest

from nacre.screen import benchmarks as bm
from nacre.screen import precision as pr
from nacre.screen.priors import Prior

BETA, SD = (1.0, 2.0, 0.5), (1.0, 1.0, 1.0)
N = 2 ** 18


def _model(x):
    return bm.linear_model(BETA)(x)["y"]


def _joint(corr=None):
    return bm.linear_gaussian_joint((0.0, 0.0, 0.0), SD, np.eye(3) if corr is None else corr)


def test_required_ratio_matches_the_closed_form_for_independent_inputs():
    res = pr.required_precision(_model, _joint(), "x2", edges=[4.0], n=N, seed=1)
    exact = pr.linear_gaussian_ratio(BETA, SD, 1, 0.0, 4.0)
    assert res.status == "ok" and res.monotone
    assert res.width_ratio == pytest.approx(exact, abs=0.02)
    assert res.required_width == pytest.approx(res.width_ratio * res.prior_width)
    assert res.nearest_threshold == 4.0


def test_required_ratio_matches_the_closed_form_with_correlation():
    corr = np.array([[1.0, 0.5, 0.0], [0.5, 1.0, 0.0], [0.0, 0.0, 1.0]])
    res = pr.required_precision(_model, _joint(corr), "x2", edges=[4.5], n=N, seed=2)
    exact = pr.linear_gaussian_ratio(BETA, SD, 1, 0.0, 4.5, corr=corr)
    assert res.status == "ok"
    assert res.width_ratio == pytest.approx(exact, abs=0.02)


def test_already_decided_and_unreachable_cases():
    assert pr.required_precision(_model, _joint(), "x2", edges=[6.0], n=N, seed=3).status == "already_clears"
    # x1 alone cannot decide it: with x1 fixed the bound is still 1.96 sqrt(4.25) > 4
    assert pr.linear_gaussian_ratio(BETA, SD, 0, 0.0, 4.0) is None
    res = pr.required_precision(_model, _joint(), "x1", edges=[4.0], n=N, seed=4)
    assert res.status == "unreachable" and res.width_ratio is None


def test_record_conforms_to_the_schema_entry():
    import jsonschema
    from nacre.screen import summary
    schema = summary.load_schema()
    res = pr.required_precision(_model, _joint(), "x2", edges=[4.0], n=2 ** 14, seed=5)
    entry = res.as_dict("1", "edge 4.0", "contraction about the median")
    sub = {"$defs": schema["$defs"], **schema["$defs"]["required_precision"]}
    jsonschema.validate({"R-slurry": {"x2": entry}}, sub)


def test_contraction_keeps_the_median_and_scales_central_widths():
    rng = np.random.default_rng(0)
    for p in (Prior("u", "u", "1", "uniform", {"low": 1.0, "high": 3.0}),
              Prior("l", "l", "1", "loguniform", {"low": 1e-3, "high": 1e1}),
              Prior("k", "k", "1", "normal", {"mean": -6.0, "sd": 0.5}, transform="log10")):
        x = p.sample(rng, 200_000)
        y = pr.contract(p, x, 0.25)
        assert np.median(y) == pytest.approx(p.ppf(0.5), rel=0.01)
        w = lambda v: np.diff(pr._stated(p, np.quantile(v, [0.025, 0.975])))[0]
        assert w(y) == pytest.approx(0.25 * w(x), rel=0.02)
        assert np.all(pr.contract(p, x, 0.0) == pytest.approx(p.ppf(0.5)))


def test_decided_and_nearest_edge():
    assert pr.decided((0.1, 0.4), [0.5, 0.8])
    assert not pr.decided((0.4, 0.6), [0.5, 0.8])
    assert pr.nearest_edge((0.6, 0.75), [0.5, 0.8]) == 0.8
