"""Rule version 2 of lit/corpus/params_README.md (section 7, cp3): roles, T1, W1, A1, I1, D1, R1, G1, M0."""
import math

import pytest
import yaml

from lit_helpers import good_row
from nacre.lit import build_params as B
from nacre.lit import evidence as E
from nacre.lit import params as P

SYMBOLS = {"symbols": [
    {"id": "gamma_nl", "unit": "J m^-2", "interval": "(-oo, oo)"},
    {"id": "dG", "unit": "J mol^-1", "interval": "(-oo, oo)"},
    {"id": "logK", "unit": "1", "interval": "(-oo, oo)"},
    {"id": "p_cred", "unit": "1", "interval": "(0, 1)"},
    {"id": "E", "unit": "V", "interval": "(-oo, oo)"},
]}

ROWS = [
    good_row(row_id="TK-001", doi="10.1/a", value="-27", unit="mJ m^-2", range_or_uncertainty="", grade="C"),
    good_row(row_id="TK-002", doi="10.1/b", value="2.0", unit="mJ m^-2", range_or_uncertainty="", grade="C"),
    good_row(row_id="TK-003", doi="10.1/b", value="3.4", unit="mJ m^-2", range_or_uncertainty="", grade="C"),
    good_row(row_id="TK-004", doi="10.1/c", value="-9.5", unit="kJ/mol", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-005", doi="10.1/c", value="-4.4", unit="kJ/mol", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-006", doi="10.1/d", value="1.4", unit="kcal/mol", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-007", doi="10.1/d", value="1.9", unit="kcal/mol", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-008", doi="10.1/e", value="4.24", unit="1", range_or_uncertainty="±0.05", grade="B"),
    good_row(row_id="TK-009", doi="10.1/f", value="3.6", unit="V", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-010", doi="10.1/g", value="3.65", unit="V", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-011", doi="10.1/h", value="4.3", unit="V", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-012", doi="10.1/i", value="4.2", unit="V", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-013", doi="10.1/j", value="50", unit="mJ m^-2", range_or_uncertainty="", grade="B"),
    good_row(row_id="TK-014", doi="10.1/k", value="80", unit="mJ m^-2", range_or_uncertainty="", grade="B"),
]

THRESHOLDS = """# t

```thresholds
decision:
  conventions:
    p_cred: {primary: 0.9, sweep: [0.6, 0.9, 0.99]}
    p_deg: {rule: 1 - p_cred, primary: 0.1}
```
"""


@pytest.fixture
def root(tmp_path):
    (tmp_path / "theory").mkdir()
    (tmp_path / "theory" / "symbols.yaml").write_text(yaml.safe_dump(SYMBOLS))
    (tmp_path / "theory" / "thresholds.md").write_text(THRESHOLDS)
    (tmp_path / "lit" / "corpus").mkdir(parents=True)
    (tmp_path / "lit" / "corpus" / "params_README.md").write_text("rule\n")
    E.write_csv(tmp_path / "lit" / "evidence_table.csv", ROWS)
    return tmp_path


def entry(symbol="gamma_nl", unit="J m^-2", **kw):
    return {"symbol": symbol, "unit": unit, "regimes": ["R-slurry"], "conditions": "T=298 K", **kw}


def build(root, params, expect_errors=False):
    path = root / "spec.yaml"
    path.write_text(yaml.safe_dump({"params": params}))
    doc = B.build(root, path)
    out = root / "lit" / "params.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False))
    p = P.load_params(out, root, strict=False)
    if not expect_errors:
        assert p.errors == [], p.errors
    return doc["params"], p


SL0 = {"admit": [{"row": "TK-001"}, {"row": "TK-002"}, {"row": "TK-003"}], "distinct": True}


def test_t1_cuts_the_span_and_keeps_the_uncut_twin_as_sensitivity(root):
    e, _ = build(root, {
        "g": entry(**SL0, truncate={"min": 0, "ruling": "cp3 R8", "sensitivity_key": "g_uncut"}),
        "g_uncut": entry(same_rows_as="g", role="sensitivity", of="g"),
    })
    g, u = e["g"], e["g_uncut"]
    assert g["rule"] == "T1" and g["prior"] == {"family": "uniform", "low": 0.0, "high": 0.0034}
    assert g["value"] == pytest.approx(0.0027) and "truncated" in g["flags"]
    assert g["truncation"] == {"side": "min", "bound": 0.0, "ruling": "cp3 R8", "sensitivity_key": "g_uncut"}
    assert u["rule"] == "U1" and u["prior"]["low"] == pytest.approx(-0.027) and u["role"] == "sensitivity"


def test_t1_without_its_sensitivity_twin_fails_validation(root):
    _, p = build(root, {"g": entry(**SL0, truncate={"min": 0, "ruling": "R8", "sensitivity_key": "nope"})},
                 expect_errors=True)
    assert any("sensitivity key" in x for x in p.errors)


def test_prior_set_returns_primary_keys_only(root):
    build(root, {
        "g": entry(**SL0, truncate={"min": 0, "ruling": "cp3 R8", "sensitivity_key": "g_uncut"}),
        "g_uncut": entry(same_rows_as="g", role="sensitivity", of="g"),
    })
    p = P.load_params(root / "lit" / "params.yaml", root)
    ps = P.prior_set("R-slurry", p)
    assert [x.key for x in ps.regimes["R-slurry"]] == ["g"]


def m_seq():
    return entry(symbol="dG", unit="J mol^-1", admit=[{"row": "TK-006"}, {"row": "TK-007"}],
                 status="single-source", distinct=True)


def test_w1_widens_a_free_energy_to_the_method_error(root):
    e, _ = build(root, {"m": m_seq(),
                        "b": entry(symbol="dG", unit="J mol^-1", admit=[{"row": "TK-004"}, {"row": "TK-005"}],
                                   distinct=True, status="single-source", widen={"by": "m", "scale": "free_energy"})})
    m, b = e["m"]["value"], e["b"]
    mid = (-9500 - 4400) / 2
    assert b["rule"] == "W1" and b["prior"]["low"] == pytest.approx(mid - m) and b["prior"]["high"] == pytest.approx(mid + m)
    assert b["widening"]["unwidened"] == {"min": -9500.0, "max": -4400.0} and b["widening"]["applied"]
    assert {"single_source", "widened"} <= set(b["flags"])
    assert set(e["m"]["sources"]) <= set(b["sources"])


def test_w1_converts_the_method_error_for_a_log10_constant(root):
    e, _ = build(root, {"m": m_seq(),
                        "k": entry(symbol="logK", unit="1", transform="log10", admit=[{"row": "TK-008"}],
                                   widen={"by": "m", "scale": "log10_constant"})})
    half = e["m"]["value"] / (B.EXPR_CONSTANTS["R"] * 298.15 * math.log(10))
    assert (e["k"]["prior"]["high"] - e["k"]["prior"]["low"]) / 2 == pytest.approx(half)


def test_w1_keeps_a_span_wider_than_the_method_error(root):
    e, _ = build(root, {"m": m_seq(),
                        "b": entry(symbol="dG", unit="J mol^-1", admit=[{"row": "TK-004"}, {"row": "TK-005"}],
                                   distinct=True, status="single-source", widen={"by": "m", "scale": "free_energy"})})
    # m is about 6.9 kJ/mol here; the span half-width 2.55 kJ/mol is widened; a span of 2m would not be
    assert e["b"]["widening"]["m"] > 2550


def test_w1_refuses_a_sourced_key(root):
    with pytest.raises(B.SpecError):
        build(root, {"m": m_seq(), "b": entry(symbol="dG", unit="J mol^-1", admit=[{"row": "TK-004"}, {"row": "TK-006"}],
                                                   widen={"by": "m", "scale": "free_energy"})})


def test_a1_analog_is_flagged_and_points_at_its_key(root):
    e, _ = build(root, {"gsn": entry(status="gap", reason="unmeasured"),
                        "gsn_analog": entry(admit=[{"row": "TK-013"}, {"row": "TK-014"}], role="analog", of="gsn")})
    a = e["gsn_analog"]
    assert a["rule"] == "U1" and a["role"] == "analog" and a["of"] == "gsn" and "analog" in a["flags"]


def test_i1_ignorance_envelope_and_d1_derived_margin(root):
    e, _ = build(root, {
        "gp": entry(admit=[{"row": "TK-013"}, {"row": "TK-014"}]),
        "gsn": entry(ignorance={"low": "0", "high": "gp + gp", "inputs": {"gp": "gp"}, "authority": "1a"}),
        "e1": entry(symbol="E", unit="V", admit=[{"row": "TK-009"}, {"row": "TK-010"}]),
        "m": entry(symbol="E", unit="V", derive={"expr": "(hi - lo) / 2", "inputs": {"hi": "e1.max", "lo": "e1.min"}},
                   margin_case="evidence"),
    })
    assert e["gsn"]["rule"] == "I1" and e["gsn"]["range"] == {"min": 0.0, "max": pytest.approx(0.16)}
    assert e["gsn"]["prior"] == {"family": "none"}
    assert e["m"]["rule"] == "D1" and e["m"]["value"] == pytest.approx(0.025) and e["m"]["prior"]["family"] == "fixed"
    assert e["m"]["sources"] == ["TK-009", "TK-010"] and e["m"]["margin_case"] == "evidence"


def test_d1_value_is_rechecked_by_the_validator(root):
    build(root, {"e1": entry(symbol="E", unit="V", admit=[{"row": "TK-009"}, {"row": "TK-010"}]),
                 "m": entry(symbol="E", unit="V", derive={"expr": "x * 2", "inputs": {"x": "e1"}})})
    path = root / "lit" / "params.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["params"]["m"]["value"] = doc["params"]["m"]["prior"]["value"] = 1.0
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    errs = P.load_params(path, root, strict=False).errors
    assert any("D1" in x for x in errs)


def test_d1_with_a_gap_input_becomes_a_gap(root):
    e, _ = build(root, {"a": entry(status="gap", reason="none found"),
                        "n": entry(derive={"expr": "1 / a", "inputs": {"a": "a"}, "as": "none"})})
    assert e["n"]["status"] == "gap" and e["n"]["rule"] == "X1" and e["n"]["derived"]["expr"] == "1 / a"


def test_formulas_refuse_anything_but_arithmetic(root):
    with pytest.raises(B.SpecError):
        B.eval_expr("__import__('os')", {})
    with pytest.raises(B.SpecError):
        B.eval_expr("x.real", {"x": 1.0})


def test_r1_reads_the_registered_value_and_sweep(root):
    reg = {"file": "theory/thresholds.md", "block": "thresholds", "ruling": "cp2 ruling (D14)"}
    e, _ = build(root, {
        "p_cred": entry(symbol="p_cred", unit="1", registered={**reg, "path": "decision.conventions.p_cred"}),
        "p_deg": entry(symbol="p_cred", unit="1", registered={**reg, "path": "decision.conventions.p_deg",
                                                             "sweep_from": {"name": "p_cred",
                                                                            "path": "decision.conventions.p_cred"}}),
    })
    assert e["p_cred"]["value"] == 0.9 and e["p_cred"]["registered"]["sweep"] == [0.6, 0.9, 0.99]
    assert e["p_deg"]["value"] == 0.1 and e["p_deg"]["registered"]["sweep"] == pytest.approx([0.4, 0.1, 0.01])
    assert e["p_cred"]["rule"] == "R1" and "registered" in e["p_cred"]["flags"]


def test_r1_value_must_match_the_authority(root):
    reg = {"file": "theory/thresholds.md", "block": "thresholds", "ruling": "cp2", "path": "decision.conventions.p_cred"}
    build(root, {"p_cred": entry(symbol="p_cred", unit="1", registered=reg)})
    (root / "theory" / "thresholds.md").write_text(THRESHOLDS.replace("primary: 0.9", "primary: 0.95"))
    errs = P.load_params(root / "lit" / "params.yaml", root, strict=False).errors
    assert any("R1" in x for x in errs)


def test_g1_design_axis_by_class(root):
    e, _ = build(root, {
        "e_lfp": entry(symbol="E", unit="V", admit=[{"row": "TK-009"}, {"row": "TK-010"}]),
        "e_nmc": entry(symbol="E", unit="V", admit=[{"row": "TK-011"}, {"row": "TK-012"}]),
        "e_max": entry(symbol="E", unit="V", role="design-axis",
                       axis={"classes": [{"label": "LFP", "key": "e_lfp"}, {"label": "NMC", "key": "e_nmc"}]}),
    })
    ax = e["e_max"]
    assert ax["rule"] == "G1" and ax["prior"]["family"] == "categorical" and ax["status"] == "design-input"
    assert [o["label"] for o in ax["prior"]["options"]] == ["LFP", "NMC"]
    assert ax["prior"]["options"][1]["range"] == {"min": 4.2, "max": 4.3}


def test_m0_margin_zero_needs_its_reason(root):
    e, _ = build(root, {"m_s": entry(margin_zero={"reason": "the interfacial-energy priors carry the error"})})
    assert e["m_s"]["rule"] == "M0" and e["m_s"]["value"] == 0.0 and e["m_s"]["margin_case"] == "zero"
    path = root / "lit" / "params.yaml"
    doc = yaml.safe_load(path.read_text())
    doc["params"]["m_s"]["margin_reason"] = ""
    path.write_text(yaml.safe_dump(doc, sort_keys=False))
    assert any("M0" in x for x in P.load_params(path, root, strict=False).errors)
