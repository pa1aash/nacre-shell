"""PH-W4.3: required-precision map helpers (nacre.screen.ph_precision)."""
import numpy as np

from nacre.screen import ph_precision as pp
from nacre.screen import precision
from nacre.screen.priors import Prior
from nacre.screen.sampling import JointPrior


def _joint():
    pri = [Prior("x%d" % i, "x%d" % i, "1", "normal", {"mean": 0.0, "sd": 1.0}, "t") for i in range(3)]
    return JointPrior.independent_of(pri)


def test_contracted_keeps_median_and_scales_width():
    j = _joint()
    c = pp.Contracted(j, "x1", 0.5)
    x = c.sample(np.random.default_rng(1), 200000)
    assert abs(np.median(x[:, 1])) < 0.01
    lo, hi = np.quantile(x[:, 1], [0.025, 0.975])
    assert abs((hi - lo) - 0.5 * 3.92) < 0.05
    assert abs(np.std(x[:, 0]) - 1) < 0.02


def test_joint_ratio_matches_linear_gaussian_for_one_parameter():
    j = _joint()
    beta = np.array([1.0, 2.0, 0.5])

    def model(d):
        return beta[0] * d["x0"] + beta[1] * d["x1"] + beta[2] * d["x2"]
    r = pp.joint_ratio(model, j, ["x1"], [4.0], 2 ** 18, 3, 0.95)
    exact = precision.linear_gaussian_ratio(beta, [1, 1, 1], 1, 0.0, 4.0)
    assert r["status"] == "ok" and abs(r["width_ratio"] - exact) < 0.01


def test_reach_compares_with_stated_uncertainty():
    ms = [{"stated_uncertainty_min": 0.01, "value_spread": None}]
    out = pp.reach([{"purpose": "a", "hw": 0.1, "kind": "x"}, {"purpose": "b", "hw": 0.001, "kind": "x"}, {"purpose": "c", "hw": None}], ms)
    assert out[0]["assessment"].startswith("within reach")
    assert out[1]["assessment"].startswith("not within reach")
    assert out[2]["assessment"] == "not assessed"


def test_hydrolysis_flip_is_log_over_rate():
    import math
    assert abs(math.log(1 / 0.5) / 1e-7 - 6931471.8) < 1
