"""Parameter-table adapter: W1's layout (lit/corpus/params_README.md) into joint priors."""
import importlib
import importlib.util
from pathlib import Path

import numpy as np
import pytest
import yaml

from nacre.screen import params_adapter as pa
from nacre.screen.priors import MockPriorsRefused, PriorFileError

ROOT = Path(__file__).resolve().parents[2]
MOCK = ROOT / "configs" / "preprint" / "mock_params.yaml"
PRODUCTION = ROOT / "lit" / "params.yaml"


def _table(tmp_path, doc):
    p = tmp_path / "params.yaml"
    p.write_text(yaml.safe_dump(doc), encoding="utf-8")
    return p


def _entry(symbol, prior, regimes=("shared",), group=None, transform="none", unit=None):
    unit = unit if unit is not None else (pa.symbol_units().get(symbol, "1") if transform == "none" else "1")
    return {"symbol": symbol, "transform": transform, "unit": unit, "regimes": list(regimes),
            "status": "sourced", "prior": prior, "sources": [], "correlation_group": group}


U = {"family": "uniform", "low": 0.0, "high": 1.0}


def test_mock_table_is_refused_without_the_flag():
    with pytest.raises(MockPriorsRefused):
        pa.regime_priors(MOCK, "R-slurry")


def test_mock_table_reads_into_a_correlated_joint_prior():
    rp = pa.regime_priors(MOCK, "R-slurry", allow_mock=True)
    assert rp.mock and rp.sha256.startswith("sha256:")
    assert rp.unsampled == {"Delta_F_pmf": "prior family none: computed in the study (mock)"}
    sym = rp.joint.symbols
    rs = rp.joint.spearman
    assert rs[sym.index("gamma_sl0"), sym.index("gamma_sn0")] == 0.6
    assert rs[sym.index("gamma_nl"), sym.index("gamma_sn0")] == 0.3
    assert rs[sym.index("gamma_ow"), sym.index("gamma_pw")] == 0.0      # assumed independent
    assert rp.joint.dependence_record()["method"] == "gaussian_copula"
    ksp = rp.joint.priors[sym.index("K_sp")]
    assert ksp.transform == "log10" and ksp.distribution == "normal"


def test_regime_filter_keeps_shared_and_own_keys(tmp_path):
    doc = {"mock": False, "params": {"a": _entry("a", U, ["R-slurry"]), "b": _entry("b", U, ["R-cell"]),
                                     "c": _entry("c", U, ["shared"])}}
    p = _table(tmp_path, doc)
    assert pa.regime_priors(p, "R-slurry").joint.symbols == ["a", "c"]
    assert pa.regime_priors(p, "R-cell").joint.symbols == ["b", "c"]


def test_fixed_categorical_and_none_families(tmp_path):
    doc = {"mock": False, "params": {
        "a": _entry("a", U),
        "f": _entry("f", {"family": "fixed", "value": 298.15}),
        "c": _entry("c", {"family": "categorical", "options": ["x", "y"]}),
        "g": dict(_entry("g", {"family": "none"}), range=None, range_reason="gap")}}
    rp = pa.regime_priors(_table(tmp_path, doc), "R-slurry")
    assert rp.joint.symbols == ["a", "f"]
    assert rp.joint.priors[1].is_fixed
    assert set(rp.unsampled) == {"c", "g"}
    assert "gap" in rp.unsampled["g"]


@pytest.mark.parametrize("doc, match", [
    ({"mock": False, "params": {"a": _entry("a", U, group="g1")}}, "not defined"),
    ({"mock": False, "params": {"a": _entry("a", U, group="g1")},
      "correlation_groups": {"g1": {"members": ["b"], "kind": "rank", "matrix": [[1.0]]}}}, "does not list"),
    ({"mock": False, "params": {"a": _entry("a", U), "b": _entry("a", U)}}, "twice"),
    ({"mock": False, "params": {"a": _entry("a", {"family": "beta"})}}, "unknown prior family"),
    ({"mock": False, "params": {"a": _entry("a", {"family": "uniform", "low": 1.0, "high": 0.0})}}, "low < high"),
    ({"params": {"a": _entry("a", U)}}, "mock"),
    ({"mock": False, "params": {"a": _entry("a", {"family": "none"})}}, "no sampled"),
])
def test_malformed_tables_are_rejected(tmp_path, doc, match):
    with pytest.raises(PriorFileError, match=match):
        pa.regime_priors(_table(tmp_path, doc), "R-slurry")


def test_rank_group_needs_a_valid_matrix(tmp_path):
    doc = {"mock": False, "params": {"a": _entry("a", U, group="g"), "b": _entry("b", U, group="g")},
           "correlation_groups": {"g": {"members": ["a", "b"], "kind": "rank", "matrix": [[1.0, 1.5], [1.5, 1.0]]}}}
    with pytest.raises(ValueError):
        pa.regime_priors(_table(tmp_path, doc), "R-slurry")


def test_samples_follow_the_table(tmp_path):
    doc = {"mock": False, "params": {"k": _entry("k", {"family": "uniform", "low": -7.0, "high": -5.0},
                                                 transform="log10")}}
    rp = pa.regime_priors(_table(tmp_path, doc), "R-slurry")
    x = rp.joint.sample(np.random.default_rng(0), 10_000)[:, 0]
    assert 1e-7 <= x.min() and x.max() <= 1e-5


@pytest.mark.skipif(importlib.util.find_spec("nacre.lit.params") is None or not PRODUCTION.exists(),
                    reason="W1's loader (nacre.lit.params) and lit/params.yaml are not on this branch yet")
def test_adapter_agrees_with_the_parameter_table_loader():
    lp = importlib.import_module("nacre.lit.params")
    for regime in pa.REGIMES:
        try:
            rp = pa.regime_priors(PRODUCTION, regime)
        except PriorFileError:
            continue
        assert pa.cross_check(rp, lp) == []


def _w1_like(tmp_path, framing_value=None):
    e = lambda sym, prior, regimes=("R-slurry",): dict(_entry(sym, prior, regimes), value=None)
    doc = {"mock": False, "params": {
        "gnl_a": e("gamma_nl", U), "gnl_b": e("gamma_nl", {"family": "uniform", "low": 2.0, "high": 3.0}),
        "t_one": e("T", {"family": "uniform", "low": 280.0, "high": 290.0}),
        "t_two": e("T", {"family": "uniform", "low": 300.0, "high": 310.0}),
        "gap": e("gamma_sn0", {"family": "none"}),
        "framing": dict(e("framing", {"family": "none"}), value=framing_value)},
        "regimes": {"R-slurry": {"parameters": {"framing": {"key": "framing", "prior": {"family": "none"},
                                                            "value": framing_value}}}}}
    return _table(tmp_path, doc)


CFG = {"bindings": {"R-slurry": {"common": {"gamma_sn0": "gap"},
                                 "by_framing": {"A": {"gamma_nl": "gnl_a"}, "B": {"gamma_nl": "gnl_b"}},
                                 "states": {"one": {"T": "t_one"}, "two": {"T": "t_two"}}}}}


def test_bindings_select_one_key_per_symbol_by_framing_and_state(tmp_path):
    from nacre.screen import run
    p = _w1_like(tmp_path, framing_value="B")
    with pytest.raises(PriorFileError, match="twice"):
        pa.regime_priors(p, "R-slurry")                     # alternatives need a binding
    states = run.load_states(p, "R-slurry", CFG, allow_mock=False, dry_run=False)
    assert [s for s, _ in states] == ["one", "two"]
    one = dict(states)["one"].joint
    assert one.names == ["gnl_b", "t_one"] and dict(states)["one"].unsampled["gamma_sn0"].startswith("prior family none")
    assert dict(states)["two"].joint.names == ["gnl_b", "t_two"]


def test_unregistered_framing_refuses_production_and_needs_an_explicit_dry_run_choice(tmp_path):
    from nacre.screen import run
    p = _w1_like(tmp_path, framing_value=None)
    with pytest.raises(run.ProductionRefused, match="framing"):
        run.load_states(p, "R-slurry", CFG, allow_mock=False, dry_run=False)
    with pytest.raises(run.ProductionRefused, match="dry run"):
        run.load_states(p, "R-slurry", CFG, allow_mock=False, dry_run=True)
    states = run.load_states(p, "R-slurry", CFG, allow_mock=False, framing="A", dry_run=True)
    assert dict(states)["one"].joint.names == ["gnl_a", "t_one"]


def test_binding_errors_are_named(tmp_path):
    p = _w1_like(tmp_path)
    with pytest.raises(PriorFileError, match="not in the table"):
        pa.regime_priors(p, "R-slurry", bindings={"gamma_nl": "missing"})
    with pytest.raises(PriorFileError, match="symbol differs"):
        pa.regime_priors(p, "R-slurry", bindings={"V_m": "gnl_a"})


def test_screen_bindings_name_only_contract_symbols():
    from nacre.screen import chain, run
    known = set(chain.SEQ_CYCLE_INPUTS + chain.SEQ_LOCAL_INPUTS + chain.NUC_BASE + chain.ACCESS_INPUTS
                + chain.ANCHOR_INPUTS + chain.SPECIATION_INPUTS + chain.PMF_INPUTS
                + ("gamma_sl0", "gamma_sl", "Delta_G_seq"))
    b = run.load_config(ROOT)["bindings"]["R-slurry"]
    syms = set(b["common"]) | {s for f in b["by_framing"].values() for s in f} | \
        {s for st in b["states"].values() for s in st if not s.startswith("_")} | \
        {s for st in b["states"].values() for s in (st.get("_fixed") or {})}
    assert syms <= known, syms - known


def test_priors_are_converted_to_the_si_unit_of_their_symbol(tmp_path):
    doc = {"mock": False, "params": {"g": _entry("gamma_nl", {"family": "uniform", "low": 10.0, "high": 20.0},
                                                 unit="mJ m^-2")}}
    p = pa.regime_priors(_table(tmp_path, doc), "R-slurry").joint.priors[0]
    assert p.units == "J m^-2" and p.params == pytest.approx({"low": 0.01, "high": 0.02}, rel=1e-15)


@pytest.mark.parametrize("unit,match", [("furlong", "unknown unit"), ("J mol^-1", "cannot convert")])
def test_unknown_or_wrong_dimension_units_are_refused(tmp_path, unit, match):
    doc = {"mock": False, "params": {"g": _entry("gamma_nl", U, unit=unit)}}
    with pytest.raises(PriorFileError, match=match):
        pa.regime_priors(_table(tmp_path, doc), "R-slurry")


def test_truncation_confines_draws_and_reports_the_kept_mass(tmp_path):
    doc = {"mock": False, "params": {"g": _entry("gamma_sl0", {"family": "uniform", "low": -0.03, "high": 0.01})}}
    rp = pa.regime_priors(_table(tmp_path, doc), "R-slurry", truncate={"gamma_sl0": (0.0, None)})
    pr = rp.joint.priors[0]
    x = pr.sample(np.random.default_rng(1), 20000)
    assert x.min() >= 0.0 and x.max() <= 0.01
    assert pr.truncated_mass() == pytest.approx(0.25)
    n = {"family": "normal", "mean": 0.0, "sd": 1.0}
    doc = {"mock": False, "params": {"g": _entry("gamma_sl0", n)}}
    pr = pa.regime_priors(_table(tmp_path, doc), "R-slurry", truncate={"gamma_sl0": (0.0, None)}).joint.priors[0]
    assert pr.truncated_mass() == pytest.approx(0.5) and pr.sample(np.random.default_rng(2), 5000).min() >= 0


def test_states_share_their_draws_except_the_state_specific_inputs(tmp_path):
    from nacre.screen import propagate
    doc = {"mock": False, "params": {"a": _entry("gamma_nl", U), "t1": _entry("T", {"family": "uniform", "low": 280.0,
                                                                                   "high": 300.0}),
                                     "t2": _entry("T", {"family": "uniform", "low": 330.0, "high": 350.0})}}
    p = _table(tmp_path, doc)
    s1 = pa.regime_priors(p, "R-slurry", bindings={"gamma_nl": "a", "T": "t1"})
    s2 = pa.regime_priors(p, "R-slurry", bindings={"gamma_nl": "a", "T": "t2"})
    ev = lambda x: ({"l": {"g": np.asarray(x["gamma_nl"]), "T": np.asarray(x["T"])}}, {})
    o1, _ = propagate.propagate_chain(ev, s1.joint, 4000, 9, 1024, redraw=("T",), redraw_seed=1)
    o2, _ = propagate.propagate_chain(ev, s2.joint, 4000, 9, 1024, redraw=("T",), redraw_seed=2)
    assert np.array_equal(o1["l"]["g"], o2["l"]["g"])                       # common random numbers
    u1, u2 = (o1["l"]["T"] - 280.0) / 20.0, (o2["l"]["T"] - 330.0) / 20.0
    assert abs(np.corrcoef(u1, u2)[0, 1]) < 0.05                            # state-specific inputs independent
