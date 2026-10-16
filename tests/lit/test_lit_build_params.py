"""The parameter-table builder applies the prior rule of lit/corpus/params_README.md to evidence rows."""
import pytest
import yaml

from lit_helpers import good_row
from nacre.lit import build_params as B
from nacre.lit import evidence as E
from nacre.lit import params as P

SYMBOLS = {"symbols": [
    {"id": "gamma_nl", "unit": "J m^-2", "interval": "(0, oo)"},
    {"id": "K_sp", "unit": "1", "interval": "(0, oo)"},
    {"id": "T", "unit": "K", "interval": "(0, oo)"},
    {"id": "c_bulk", "unit": "mol m^-3", "interval": "(0, oo)"},
]}

ROWS = [
    good_row(row_id="TC-001", doi="10.1/a", value="100", unit="mJ m^-2", range_or_uncertainty="±5", grade="A"),
    good_row(row_id="TC-002", doi="10.1/b", value="104", unit="mJ m^-2", range_or_uncertainty="±4", grade="B"),
    good_row(row_id="TC-003", doi="10.1/c", value="150", unit="mJ m^-2", range_or_uncertainty="±5", grade="B"),
    good_row(row_id="TC-004", doi="10.1/d", value="", unit="mJ m^-2", range_or_uncertainty="60..90", grade="C"),
    good_row(row_id="TC-005", doi="10.1/e", value="3.3e-9", unit="1", range_or_uncertainty="", grade="C"),
    good_row(row_id="TC-006", doi="10.1/f", value="-8.48", unit="1", range_or_uncertainty="±0.02", grade="A"),
    good_row(row_id="TC-007", doi="10.1/g", value="25", unit="degC", range_or_uncertainty="", grade="B"),
    good_row(row_id="TC-008", doi="10.1/h", value="0.1", unit="mmol L^-1", range_or_uncertainty="", grade="B"),
    good_row(row_id="TC-009", doi="10.1/i", value="20", unit="mmol L^-1", range_or_uncertainty="", grade="B"),
    good_row(row_id="TC-010", doi="10.1/a", value="101", unit="mJ m^-2", range_or_uncertainty="±6", grade="C"),
    good_row(row_id="TC-011", doi="10.1/j", value="5", unit="mJ m^-2", range_or_uncertainty="±10", grade="A"),
]


@pytest.fixture
def root(tmp_path):
    (tmp_path / "theory").mkdir()
    (tmp_path / "theory" / "symbols.yaml").write_text(yaml.safe_dump(SYMBOLS))
    (tmp_path / "lit" / "corpus").mkdir(parents=True)
    (tmp_path / "lit" / "corpus" / "params_README.md").write_text("rule\n")
    E.write_csv(tmp_path / "lit" / "evidence_table.csv", ROWS)
    return tmp_path


def spec(**params):
    base = {"symbol": "gamma_nl", "unit": "J m^-2", "regimes": ["R-slurry"], "conditions": "T=298 K"}
    return {"params": {k: {**base, **v} for k, v in params.items()}}


def build(root, s):
    path = root / "spec.yaml"
    path.write_text(yaml.safe_dump(s))
    doc = B.build(root, path)
    (root / "lit" / "params.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    errs = P.load_params(root / "lit" / "params.yaml", root, strict=False).errors
    assert errs == [], errs
    return doc["params"]


def test_n1_concordant_ab_sources_give_a_normal_in_si(root):
    e = build(root, spec(k={"admit": [{"row": "TC-001"}, {"row": "TC-002"}]}))["k"]
    assert e["rule"] == "N1" and e["prior"]["family"] == "normal"
    assert 0.100 < e["prior"]["mean"] < 0.104 and e["value"] == e["prior"]["mean"]
    assert e["prior"]["sd"] >= 0.004 * 0.5 and e["best_grade"] == "A"


def test_discordant_sources_give_uniform_over_the_span(root):
    e = build(root, spec(k={"admit": [{"row": "TC-001"}, {"row": "TC-003"}]}))["k"]
    assert e["rule"] == "U1" and e["prior"] == {"family": "uniform", "low": 0.09, "high": 0.16}
    assert e["range"] == {"min": 0.09, "max": 0.16}


def test_grade_c_or_range_forces_uniform(root):
    e = build(root, spec(k={"admit": [{"row": "TC-001"}, {"row": "TC-004"}]}))["k"]
    assert e["prior"]["family"] == "uniform" and e["prior"]["low"] == 0.06 and e["prior"]["high"] == 0.11


def test_same_original_counts_once(root):
    e = build(root, spec(k={"admit": [{"row": "TC-001"}, {"row": "TC-010"}]}))["k"]
    assert e["status"] == "single-source" and e["rule"] == "N2"


def test_n2_and_log10_key(root):
    e = build(root, spec(k={"symbol": "K_sp", "transform": "log10", "unit": "1",
                            "admit": [{"row": "TC-006"}]}))["k"]
    assert e["rule"] == "N2" and e["prior"] == {"family": "normal", "mean": -8.48, "sd": 0.02}


def test_log10_op_and_l1(root):
    e = build(root, spec(k={"symbol": "c_bulk", "unit": "mol m^-3", "admit": [{"row": "TC-008"}, {"row": "TC-009"}]}))["k"]
    assert e["rule"] == "L1" and e["prior"]["low"] == pytest.approx(0.1) and e["prior"]["high"] == pytest.approx(20)
    e2 = build(root, spec(k={"symbol": "K_sp", "transform": "log10", "unit": "1",
                             "admit": [{"row": "TC-005", "op": "log10"}, {"row": "TC-006"}]}))["k"]
    assert e2["rule"] == "U1" and e2["prior"]["high"] == pytest.approx(-8.44)


def test_p1_single_point_and_offset_unit(root):
    e = build(root, spec(k={"symbol": "T", "unit": "K", "admit": [{"row": "TC-007"}]}))["k"]
    assert e["rule"] == "P1" and e["prior"] == {"family": "fixed", "value": 298.15}


def test_n3_normal_cut_to_the_domain(root):
    e = build(root, spec(k={"admit": [{"row": "TC-011"}]}))["k"]
    assert e["rule"] == "N3" and e["prior"]["family"] == "uniform" and e["prior"]["low"] == 0.0


def test_x1_x2_x3(root):
    d = build(root, spec(
        gap={"status": "gap", "reason": "no admitted row"},
        pmf={"status": "computed", "reason": "computed by the study"},
        salt={"symbol": "salt", "unit": "1", "categorical": [{"label": "LiBOB", "sources": ["TC-001"]}]},
        t0={"symbol": "T", "unit": "K", "fixed_from": "TC-007"},
    ))
    assert d["gap"]["rule"] == "X1" and d["gap"]["range"] is None
    assert d["pmf"]["rule"] == "X2" and d["pmf"]["status"] == "computed"
    assert d["salt"]["prior"]["family"] == "categorical" and d["salt"]["best_grade"] == "A"
    assert d["t0"]["prior"] == {"family": "fixed", "value": 298.15}


def test_groups_collect_members(root):
    s = spec(a={"admit": [{"row": "TC-001"}], "correlation_group": "g"},
             b={"admit": [{"row": "TC-003"}], "correlation_group": "g"})
    s["correlation_groups"] = {"g": {"kind": "assumed independent", "reason": "Young energies (N2)"}}
    path = root / "spec.yaml"
    path.write_text(yaml.safe_dump(s))
    doc = B.build(root, path)
    assert doc["correlation_groups"]["g"]["members"] == ["a", "b"]
    assert doc["correlation_groups"]["g"]["matrix"] == [[1.0, 0.0], [0.0, 1.0]]


def test_missing_row_and_missing_reason_fail(root):
    with pytest.raises(B.SpecError):
        B.build_entry("k", spec(k={"admit": [{"row": "TC-999"}]})["params"]["k"], {}, {})
    with pytest.raises(B.SpecError):
        B.build_entry("k", spec(k={"status": "gap"})["params"]["k"], {}, {})
