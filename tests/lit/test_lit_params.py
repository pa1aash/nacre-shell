"""Loader and validator of lit/params.yaml (rule: lit/corpus/params_README.md)."""
import copy
from pathlib import Path

import numpy as np
import pytest
import yaml

from lit_helpers import good_row
from nacre.lit import evidence as E
from nacre.lit import params as P
from nacre.screen.priors import Prior, PriorSet
from nacre.screen.propagate import sample_inputs
from nacre.screen.sobol import saltelli_design

REPO = Path(__file__).resolve().parents[2]

SYMBOLS = {"symbols": [
    {"id": "gamma_nl", "unit": "J m^-2", "interval": "(0, oo)"},
    {"id": "V_m", "unit": "m^3 mol^-1", "interval": "(0, oo)"},
    {"id": "K_sp", "unit": "1", "interval": "(0, oo)"},
    {"id": "pH", "unit": "1", "interval": "(-oo, oo)"},
    {"id": "T", "unit": "K", "interval": "(0, oo)"},
    {"id": "c_bulk", "unit": "mol m^-3", "interval": "(0, oo)"},
]}


def entry(**kw):
    e = {"symbol": "gamma_nl", "transform": "none", "unit": "J m^-2", "regimes": ["R-slurry"],
         "status": "sourced", "value": 0.1, "range": {"min": 0.05, "max": 0.15},
         "prior": {"family": "uniform", "low": 0.05, "high": 0.15}, "rule": "U1",
         "sources": ["TC-002", "TC-003"], "best_grade": "C", "method": "span of the admitted intervals",
         "conditions": "T=298 K", "correlation_group": None, "notes": ""}
    e.update(kw)
    return e


def base_doc():
    return {
        "mock": False, "meta": {"session": "test"},
        "params": {
            "gamma_nl_calcite": entry(),
            "v_m_calcite": entry(symbol="V_m", unit="m^3 mol^-1", value=3.69e-5, range={"min": 3.68e-5, "max": 3.70e-5},
                                 prior={"family": "normal", "mean": 3.69e-5, "sd": 2e-8}, rule="N1",
                                 sources=["TC-004", "TC-005"], best_grade="A"),
            "log10_ksp_calcite": entry(symbol="K_sp", transform="log10", unit="1", value=-8.48,
                                       range={"min": -8.52, "max": -8.44},
                                       prior={"family": "uniform", "low": -8.52, "high": -8.44}, rule="U1",
                                       correlation_group="solubility"),
            "log10_ksp_acc": entry(symbol="K_sp", transform="log10", unit="1", value=-6.4,
                                   range={"min": -6.5, "max": -6.3},
                                   prior={"family": "uniform", "low": -6.5, "high": -6.3}, rule="U1",
                                   correlation_group="solubility"),
            "c_bulk_slurry": entry(symbol="c_bulk", unit="mol m^-3", value=1.0, range={"min": 0.1, "max": 10.0},
                                   prior={"family": "loguniform", "low": 0.1, "high": 10.0}, rule="L1"),
            "t_slurry": entry(symbol="T", unit="K", value=298.15, range={"min": 298.15, "max": 298.15},
                              prior={"family": "fixed", "value": 298.15}, rule="P1", sources=["TC-002"]),
            "gamma_sl_organic": entry(status="gap", value=None, range=None, range_reason="gap: no admitted row",
                                      prior={"family": "none"}, rule="X1", sources=[], best_grade=None),
        },
        "correlation_groups": {
            "solubility": {"members": ["log10_ksp_calcite", "log10_ksp_acc"], "kind": "rank",
                           "matrix": [[1.0, 0.6], [0.6, 1.0]], "sources": ["TC-002"],
                           "reason": "test"},
        },
    }


@pytest.fixture
def root(tmp_path):
    (tmp_path / "theory").mkdir()
    (tmp_path / "theory" / "symbols.yaml").write_text(yaml.safe_dump(SYMBOLS))
    (tmp_path / "lit").mkdir()
    rows = [good_row(row_id="TC-002", grade="C"), good_row(row_id="TC-003", grade="C"),
            good_row(row_id="TC-004", grade="A"), good_row(row_id="TC-005", grade="B")]
    E.write_csv(tmp_path / "lit" / "evidence_table.csv", rows)
    return tmp_path


def write(root, doc):
    path = root / "lit" / "params.yaml"
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    return path


def problems(root, doc):
    return P.load_params(write(root, doc), root, strict=False).errors


def test_valid_file_loads(root):
    p = P.load_params(write(root, base_doc()), root)
    assert p.errors == [] and p.sha256.startswith("sha256:")


def test_prior_is_a_screen_prior_and_samples(root):
    p = P.load_params(write(root, base_doc()), root)
    pr = P.prior("gamma_nl_calcite", p)
    assert isinstance(pr, Prior) and pr.distribution == "uniform" and pr.grade == "C"
    x = pr.sample(np.random.default_rng(0), 1000)
    assert x.min() >= 0.05 and x.max() <= 0.15
    fixed = P.prior("t_slurry", p).sample(np.random.default_rng(0), 5)
    assert np.all(fixed == 298.15)
    lu = P.prior("c_bulk_slurry", p).sample(np.random.default_rng(1), 4000)
    assert 0.1 <= lu.min() and lu.max() <= 10.0 and abs(np.median(np.log10(lu))) < 0.1


def test_unsampled_key_raises(root):
    p = P.load_params(write(root, base_doc()), root)
    with pytest.raises(P.NotSampled):
        P.prior("gamma_sl_organic", p)
    with pytest.raises(KeyError):
        P.prior("absent", p)


def test_priors_tuple_works_with_screen_code(root):
    p = P.load_params(write(root, base_doc()), root)
    keys = ["gamma_nl_calcite", "log10_ksp_calcite", "log10_ksp_acc", "v_m_calcite"]
    ps = P.priors(keys, p)
    assert ps.keys == keys and ps.groups == {"solubility": ["log10_ksp_calcite", "log10_ksp_acc"]}
    assert ps.correlation[1, 2] == 0.6 and ps.correlation[0, 1] == 0.0
    draws = sample_inputs(ps, 50, np.random.default_rng(2))
    assert set(draws) == set(keys)
    a, b, names = saltelli_design(ps, 8, np.random.default_rng(3))
    assert a.shape == (8, 4) and names == keys


def test_prior_set_per_regime(root):
    p = P.load_params(write(root, base_doc()), root)
    ps = P.prior_set("R-slurry", p)
    assert isinstance(ps, PriorSet) and ps.mock is False
    assert "gamma_sl_organic" not in ps.names("R-slurry") and "gamma_nl_calcite" in ps.names("R-slurry")


def test_correlated_sampling_reproduces_rank_correlation(root):
    p = P.load_params(write(root, base_doc()), root)
    ps = P.priors(["log10_ksp_calcite", "log10_ksp_acc"], p)
    d = P.sample_correlated(ps, 20000, np.random.default_rng(4))
    ra = np.argsort(np.argsort(d["log10_ksp_calcite"]))
    rb = np.argsort(np.argsort(d["log10_ksp_acc"]))
    assert abs(np.corrcoef(ra, rb)[0, 1] - 0.6) < 0.03
    assert d["log10_ksp_acc"].min() >= -6.5 and d["log10_ksp_acc"].max() <= -6.3


def mutate(fn):
    doc = base_doc()
    fn(doc)
    return doc


@pytest.mark.parametrize("change, fragment", [
    (lambda d: d["params"]["gamma_nl_calcite"].update(value=0.2), "does not contain value"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(sources=["TC-999", "TC-002"]), "not in the evidence table"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(best_grade="B"), "best_grade"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(unit="J mol^-1"), "does not match the unit"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(unit="mJ m^-2"), "coherent SI"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(unit="blorps"), "does not parse"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(range=None), "range_reason"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(prior={"family": "uniform", "low": 0.05, "high": 0.14}),
     "equal the range"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(rule="N1"), "does not produce"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(
        prior={"family": "normal", "mean": 0.1, "sd": 0.01}, rule="N1"), "grade A or B"),
    (lambda d: d["params"]["v_m_calcite"].update(prior={"family": "normal", "mean": 3.69e-5, "sd": 1e-5}),
     "within 4 sd"),
    (lambda d: d["params"]["v_m_calcite"].update(prior={"family": "normal", "mean": 3.69e-5, "sd": 0.0}), "sd > 0"),
    (lambda d: d["params"]["v_m_calcite"].update(value=3.695e-5), "normal mean"),
    (lambda d: d["params"]["c_bulk_slurry"].update(prior={"family": "uniform", "low": 0.1, "high": 10.0}, rule="U1"),
     "L1"),
    (lambda d: d["params"]["c_bulk_slurry"].update(range={"min": 0.5, "max": 2.0}, value=1.0,
                                                   prior={"family": "loguniform", "low": 0.5, "high": 2.0}),
     "high/low > 10"),
    (lambda d: d["params"]["t_slurry"].update(prior={"family": "fixed", "value": 300.0}), "fixed prior value"),
    (lambda d: d["params"]["t_slurry"].update(sources=["TC-002", "TC-003"]), "exactly one source"),
    (lambda d: d["params"]["gamma_sl_organic"].update(range={"min": 0.0, "max": 1.0}), "X1"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(status="maybe"), "status"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(regimes=["R-moon"]), "regimes"),
    (lambda d: d["params"]["gamma_nl_calcite"].pop("notes"), "missing fields"),
    (lambda d: d["params"]["gamma_nl_calcite"].update(correlation_group="nowhere"), "not defined"),
    (lambda d: d["correlation_groups"]["solubility"].update(members=["log10_ksp_calcite"]), "differ"),
    (lambda d: d["correlation_groups"]["solubility"].update(matrix=[[1.0, 0.6], [0.5, 1.0]]), "symmetric"),
    (lambda d: d["correlation_groups"]["solubility"].update(kind="assumed independent"), "identity"),
    (lambda d: d["correlation_groups"]["solubility"].update(sources=[]), "source rows"),
    (lambda d: d.update(mock=True), "mock"),
])
def test_validator_rejects(root, change, fragment):
    errs = problems(root, mutate(change))
    assert any(fragment in e for e in errs), errs


def test_group_matrix_must_be_psd(root):
    def change(d):
        for k in ("gamma_nl_calcite", "v_m_calcite"):
            d["params"][k]["correlation_group"] = "solubility"
        d["correlation_groups"]["solubility"]["members"] = ["log10_ksp_calcite", "log10_ksp_acc",
                                                            "gamma_nl_calcite", "v_m_calcite"]
        d["correlation_groups"]["solubility"]["matrix"] = [[1, 0.9, 0.9, -0.9], [0.9, 1, 0.9, 0.9],
                                                           [0.9, 0.9, 1, 0.9], [-0.9, 0.9, 0.9, 1]]
    assert any("positive semi-definite" in e for e in problems(root, mutate(change)))


def test_log10_key_needs_unit_one(root):
    errs = problems(root, mutate(lambda d: d["params"]["log10_ksp_calcite"].update(unit="K")))
    assert any("unit 1" in e for e in errs)


@pytest.mark.skipif(not (REPO / "lit" / "params.yaml").exists(), reason="lit/params.yaml not written yet")
def test_committed_params_validate():
    p = P.load_params(REPO / "lit" / "params.yaml", REPO, strict=False)
    assert p.errors == []
    for regime in ("R-slurry", "R-cell"):
        ps = P.prior_set(regime, p)
        draws = sample_inputs(ps.parameters(regime), 64, np.random.default_rng(0))
        assert all(np.all(np.isfinite(v)) for v in draws.values())


def with_alias(doc):
    leaf = {"key": "gamma_nl_calcite", **copy.deepcopy(doc["params"]["gamma_nl_calcite"])}
    doc["regimes"] = {"R-slurry": {"parameters": {"gamma_nl": leaf}}}
    return doc


def test_alias_resolves_and_must_match(root):
    p = P.load_params(write(root, with_alias(base_doc())), root)
    assert P.resolve("regimes.R-slurry.parameters.gamma_nl", p) == "gamma_nl_calcite"
    assert P.resolve("params.v_m_calcite", p) == "v_m_calcite"
    assert P.prior("regimes.R-slurry.parameters.gamma_nl", p).key == "gamma_nl_calcite"
    assert P.priors(["regimes.R-slurry.parameters.gamma_nl"], p).keys == ["gamma_nl_calcite"]
    doc = with_alias(base_doc())
    doc["regimes"]["R-slurry"]["parameters"]["gamma_nl"]["value"] = 0.11
    assert any("differs" in e for e in problems(root, doc))
    doc = with_alias(base_doc())
    doc["regimes"]["R-slurry"]["parameters"]["gamma_nl"]["key"] = "nope"
    assert any("not in params" in e for e in problems(root, doc))
