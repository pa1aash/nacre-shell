"""Screen scaffold: prior loader guards, Sobol estimator on an exact case, smoke summary."""
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from nacre.screen import links, priors, smoke, sobol, summary, thresholds
from nacre.screen.priors import MockPriorsRefused, Prior, PriorFileError, load_priors

ROOT = Path(__file__).resolve().parents[2]
MOCK = ROOT / "configs" / "preprint" / "mock_priors.yaml"
SUMMARY = ROOT / "results" / "preprint" / "screen" / "mock" / "summary.json"


def _write(tmp_path, text):
    p = tmp_path / "p.yaml"
    p.write_text(text, encoding="utf-8")
    return p


GOOD = """mock: false
regimes:
  R-slurry:
    parameters:
      x: {symbol: x, units: "1", distribution: uniform, low: 0, high: 1, source: s}
"""


def test_mock_file_is_refused_without_the_mock_flag():
    with pytest.raises(MockPriorsRefused):
        load_priors(MOCK)


def test_mock_file_loads_with_the_mock_flag():
    ps = load_priors(MOCK, allow_mock=True)
    assert ps.mock is True
    assert ps.sha256.startswith("sha256:")
    assert set(ps.names("R-slurry")) == set(links.NUCLEATE_INPUTS)


def test_mock_file_is_marked_mock():
    import yaml
    assert yaml.safe_load(MOCK.read_text(encoding="utf-8"))["mock"] is True


def test_production_file_loads_without_the_flag(tmp_path):
    ps = load_priors(_write(tmp_path, GOOD))
    assert ps.mock is False and ps.names("R-slurry") == ["x"]


@pytest.mark.parametrize("text", [
    GOOD.replace("mock: false\n", ""),                       # mock flag must be explicit
    GOOD.replace("R-slurry", "R-other"),                     # unknown regime
    GOOD.replace("uniform", "triangular"),                   # unknown distribution
    GOOD.replace("low: 0, high: 1", "low: 1, high: 0"),     # empty support
    GOOD.replace("distribution: uniform, low: 0", "distribution: loguniform, low: 0"),
    GOOD.replace("units: \"1\", ", ""),                      # units required
    "mock: false\nregimes: {}\n",
])
def test_malformed_prior_files_are_rejected(tmp_path, text):
    with pytest.raises(PriorFileError):
        load_priors(_write(tmp_path, text))


def test_samples_respect_their_support():
    rng = np.random.default_rng(1)
    u = Prior("u", "u", "1", "uniform", {"low": 2.0, "high": 3.0}).sample(rng, 1000)
    lu = Prior("l", "l", "1", "loguniform", {"low": 1e-3, "high": 1e3}).sample(rng, 1000)
    assert u.min() >= 2.0 and u.max() <= 3.0
    assert lu.min() >= 1e-3 and lu.max() <= 1e3


def test_sobol_indices_of_an_additive_linear_model_are_exact():
    # Y = sum a_i X_i with independent X_i ~ U(0, 1): S_i = ST_i = a_i^2 / sum a_j^2.
    a = np.array([1.0, 2.0, 3.0])
    pri = [Prior("x%d" % i, "x", "1", "uniform", {"low": 0.0, "high": 1.0}) for i in range(3)]
    model = lambda x: {"y": sum(a[i] * x["x%d" % i] for i in range(3))}
    res, design = sobol.sobol_indices(model, pri, ["y"], 20000, np.random.default_rng(7),
                                      n_bootstrap=50)
    exact = a ** 2 / np.sum(a ** 2)
    for i in range(3):
        r = res["y"]["x%d" % i]
        assert r["first_order"]["estimate"] == pytest.approx(exact[i], abs=0.03)
        assert r["total_order"]["estimate"] == pytest.approx(exact[i], abs=0.03)
        assert r["first_order"]["ci_low"] <= r["first_order"]["ci_high"]
    assert design["evaluations"] == 20000 * 5


def test_shape_factor_depends_only_on_the_contact_angle():
    ps = load_priors(MOCK, allow_mock=True)
    res, _ = sobol.sobol_indices(links.nucleate, ps.parameters("R-slurry"), ["shape_factor"], 256,
                                 np.random.default_rng(3), n_bootstrap=0)
    for name, r in res["shape_factor"].items():
        if name != "cos_theta":
            assert r["total_order"]["estimate"] == 0.0


def test_nucleation_link_marks_undersaturated_draws_invalid():
    y = links.nucleate({"gamma_nuc_liq": [1.0, 1.0], "molar_volume": 1e-6, "omega": [0.5, 10.0],
                        "temperature": 300.0, "cos_theta": 0.0})
    assert np.isnan(y["barrier_hom_kT"][0]) and np.isfinite(y["barrier_hom_kT"][1])
    assert y["barrier_het_kT"][1] == pytest.approx(0.5 * y["barrier_hom_kT"][1], rel=1e-12)


def test_threshold_evaluator_refuses_until_frozen():
    with pytest.raises(thresholds.ThresholdsNotFrozen):
        thresholds.load_thresholds("configs/preprint/thresholds.yaml")
    with pytest.raises(thresholds.ThresholdsNotFrozen):
        thresholds.evaluate_link("nucleate", {}, {})


def test_smoke_run_writes_a_schema_conforming_summary(tmp_path):
    out = tmp_path / "mock" / "summary.json"
    path, doc = smoke.run(ROOT, MOCK, out, draws=256, sobol_base=64, bootstrap=20, seed=5,
                          allow_mock=True)
    summary.validate(json.loads(path.read_text(encoding="utf-8")))
    assert doc["mock"] is True
    reg = doc["regimes"]["R-slurry"]
    assert reg["draws"] + reg["sobol_design"]["evaluations"] <= smoke.MAX_DRAWS


def test_smoke_run_is_reproducible_from_its_seed(tmp_path):
    kw = dict(draws=128, sobol_base=32, bootstrap=10, seed=11, allow_mock=True)
    _, d1 = smoke.run(ROOT, MOCK, tmp_path / "mock" / "a.json", **kw)
    _, d2 = smoke.run(ROOT, MOCK, tmp_path / "mock" / "b.json", **kw)
    assert d1["regimes"] == d2["regimes"]


def test_smoke_run_refuses_non_mock_output_and_oversize_runs(tmp_path):
    with pytest.raises(ValueError):
        smoke.run(ROOT, MOCK, tmp_path / "real" / "summary.json", allow_mock=True)
    with pytest.raises(ValueError):
        smoke.run(ROOT, MOCK, tmp_path / "mock" / "s.json", draws=9000, sobol_base=512,
                  allow_mock=True)


def test_committed_mock_summary_conforms_to_the_schema():
    doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
    summary.validate(doc)
    assert doc["mock"] is True
    assert doc["provenance"]["prior_file"] == "configs/preprint/mock_priors.yaml"
    reg = doc["regimes"]["R-slurry"]
    assert reg["draws"] + reg["sobol_design"]["evaluations"] <= 10_000


def test_schema_rejects_a_corrupted_committed_summary():
    doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
    doc["regimes"]["R-slurry"]["links"]["nucleate"]["quantities"]["shape_factor"].pop("quantiles")
    with pytest.raises(jsonschema.ValidationError):
        summary.validate(doc)
