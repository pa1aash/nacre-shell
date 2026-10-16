"""Validator for preprint/retrodiction/cases.yaml (lane p0-w2)."""
import copy
from fractions import Fraction

import pytest

from nacre.retro import cases as rc


@pytest.fixture(scope="module")
def committed():
    return rc.load(rc.default_path())


def _usable(data):
    return [c for c in data["cases"] if c["status"] == "usable"]


def _errors(data):
    errors, _ = rc.validate(data)
    return errors


def test_committed_cases_and_criterion_pass():
    errors, summary = rc.check()
    assert errors == []
    assert summary["usable"] >= rc.MIN_USABLE


def test_committed_cases_resolve_their_evidence_rows(committed):
    rows = rc.evidence_row_ids(rc.default_path().parents[2])
    assert rows, "lit/evidence_table.csv should be present on the lane"
    errors, _ = rc.validate(committed, rows)
    assert errors == []


def test_committed_coverage_summary(committed):
    _, s = rc.validate(committed)
    for term in ("carboxyl", "amine", "methyl", "catechol"):
        assert term in s["terminations"]
    assert "chitosan" in s["templated"]
    assert s["negatives"] >= 1


def test_threshold_k_is_exact_binomial():
    assert rc.threshold_k(12) == 10
    assert Fraction(rc.tail_probability(12, 10)).limit_denominator(4096) == Fraction(79, 4096)
    assert rc.tail_probability(12, 9) > rc.ALPHA
    assert rc.threshold_k(8) == 7          # P(X >= 7) = 9/256 = 0.035; P(X >= 6) = 37/256 = 0.145
    assert rc.threshold_k(4) is None       # even 4 of 4 has probability 1/16 > 0.05


@pytest.mark.parametrize("observable,test,ref,expected", [
    ("cnt_slope_B", -680, -572, "test_higher_barrier"),
    ("cnt_slope_B", 267, 397, "test_lower_barrier"),
    ("induction_time", 30, 10, "test_higher_barrier"),
    ("onset_supersaturation", 2.0, 3.0, "test_lower_barrier"),
    ("nucleation_rate", 1.0, 5.0, "test_higher_barrier"),
    ("deposit_mass", 0.30, 0.667, "test_higher_barrier"),
    ("presence_absence", "absent", "present", "test_higher_barrier"),
    ("presence_absence", "present", "absent", "test_lower_barrier"),
    ("presence_absence", "present", "present", None),
    ("cnt_slope_B", 5, 5, None),
    ("deposit_mass", "less", 0.5, None),
])
def test_implied_relation(observable, test, ref, expected):
    assert rc.implied_relation(observable, test, ref) == expected


def _first_usable(data):
    return _usable(data)[0]


def test_rejects_missing_outcome_doi(committed):
    d = copy.deepcopy(committed)
    _first_usable(d)["outcome"]["doi"] = None
    assert any("outcome: missing or malformed DOI" in e for e in _errors(d))


def test_rejects_missing_input_locator(committed):
    d = copy.deepcopy(committed)
    _first_usable(d)["inputs"][0].pop("locator")
    assert any("inputs[0]: missing locator" in e for e in _errors(d))


def test_params_key_stands_in_for_a_source(committed):
    d = copy.deepcopy(committed)
    inp = _first_usable(d)["inputs"][0]
    inp.pop("doi")
    inp.pop("locator")
    inp["params_key"] = "gamma_calcite_water"
    assert _errors(d) == []


def test_rejects_relation_contradicting_values(committed):
    d = copy.deepcopy(committed)
    _first_usable(d)["outcome"]["relation"] = "test_lower_barrier"
    assert any("contradicts the values" in e for e in _errors(d))


def test_rejects_non_directional_usable_outcome(committed):
    d = copy.deepcopy(committed)
    out = _first_usable(d)["outcome"]
    out["observable"], out["test_value"], out["reference_value"] = "presence_absence", "present", "present"
    assert any("do not give a direction" in e for e in _errors(d))


def test_rejects_input_derived_from_outcome(committed):
    d = copy.deepcopy(committed)
    _first_usable(d)["inputs"][0]["derived_from_outcome"] = True
    assert any("derived_from_outcome must be false" in e for e in _errors(d))


def test_rejects_assumption_without_basis(committed):
    d = copy.deepcopy(committed)
    inp = next(i for i in _first_usable(d)["inputs"] if i["assumption"])
    inp.pop("basis")
    assert any("needs a basis" in e for e in _errors(d))


def test_rejects_unknown_input_key(committed):
    # A comma inside an unquoted YAML flow value silently creates a key; the validator catches it.
    d = copy.deepcopy(committed)
    _first_usable(d)["inputs"][0]["Table 2"] = None
    assert any("unknown key 'Table 2'" in e for e in _errors(d))


def test_rejects_excluded_case_without_reason(committed):
    d = copy.deepcopy(committed)
    x = next(c for c in d["cases"] if c["status"] == "excluded")
    x["exclusion_reason"] = ""
    assert any("needs its reason" in e for e in _errors(d))


def test_rejects_too_few_usable_cases(committed):
    d = copy.deepcopy(committed)
    keep = _usable(d)[: rc.MIN_USABLE - 1]
    d["cases"] = keep
    assert any("usable cases; at least" in e for e in _errors(d))


def test_rejects_bad_distribution(committed):
    d = copy.deepcopy(committed)
    inp = next(i for i in _first_usable(d)["inputs"] if i.get("distribution", {}).get("type") == "uniform")
    inp["distribution"]["low"], inp["distribution"]["high"] = 0.6, 0.2
    assert any("low must be below high" in e for e in _errors(d))


def test_rejects_usable_case_without_reference_input(committed):
    d = copy.deepcopy(committed)
    c = _first_usable(d)
    c["inputs"] = [i for i in c["inputs"] if i["role"] != "reference"]
    assert any("one test and one reference input" in e for e in _errors(d))


def test_rejects_unfrozen_file(committed):
    d = copy.deepcopy(committed)
    d["fixed_before_run"] = False
    assert "fixed_before_run must be true" in _errors(d)


def test_rejects_unknown_evidence_row(committed):
    d = copy.deepcopy(committed)
    _first_usable(d)["evidence_rows"] = ["TC-999"]
    errors, _ = rc.validate(d, {"TC-061"})
    assert any("TC-999 not in lit/evidence_table.csv" in e for e in errors)


def test_criterion_must_state_matching_n_and_k():
    summary = {"usable": 12, "k": 10}
    assert rc.check_criterion("N = 12\nk = 10\n", summary) == []
    assert any("k = 9" in e for e in rc.check_criterion("N = 12\nk = 9\n", summary))
    assert any("N = 11" in e for e in rc.check_criterion("N = 11\nk = 10\n", summary))
    assert rc.check_criterion("no numbers here", summary)
