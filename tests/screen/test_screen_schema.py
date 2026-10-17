"""The screen results schema is a valid JSON Schema and rejects malformed summaries."""
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "configs" / "preprint" / "results_schema.json"


@pytest.fixture(scope="module")
def schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _minimal():
    est = {"estimate": 0.5, "ci_low": 0.4, "ci_high": 0.6}
    return {
        "schema_version": "1",
        "mock": True,
        "generated_utc": "2000-01-01T00:00:00Z",
        "provenance": {"git_sha": "0" * 40, "git_dirty": False, "config_hash": "sha256:" + "a" * 64,
                       "prior_file": "p.yaml", "prior_file_hash": "sha256:" + "b" * 64},
        "regimes": {"R-slurry": {
            "draws": 1, "seed": 0,
            "sobol_design": {"method": "m", "base_samples": 1, "evaluations": 1,
                             "bootstrap_resamples": 0, "confidence_level": 0.95},
            "links": {"nucleate": {
                "quantities": {"q": {"symbol": "q", "units": "1", "n_valid": 1, "mean": 0.0,
                                     "sd": 0.0, "quantiles": {"0.5": 0.0}}},
                "sobol": {"q": {"x": {"first_order": est, "total_order": est}}},
                "threshold_evaluation": None}}}},
    }


def test_schema_is_valid_draft_2020_12(schema):
    jsonschema.Draft202012Validator.check_schema(schema)


def test_minimal_summary_validates(schema):
    jsonschema.validate(_minimal(), schema)


@pytest.mark.parametrize("mutate", [
    lambda d: d["regimes"].update({"R-unknown": d["regimes"]["R-slurry"]}),
    lambda d: d["regimes"]["R-slurry"]["links"].update({"corrosion": {}}),
    lambda d: d["provenance"].pop("prior_file_hash"),
    lambda d: d["regimes"]["R-slurry"].pop("seed"),
    lambda d: d["regimes"]["R-slurry"]["links"]["nucleate"]["sobol"]["q"]["x"].pop("total_order"),
    lambda d: d["regimes"]["R-slurry"]["links"]["nucleate"]["quantities"]["q"]["quantiles"].update({"median": 0}),
    lambda d: d.update({"verdict": "feasible"}),
])
def test_malformed_summaries_are_rejected(schema, mutate):
    doc = _minimal()
    mutate(doc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema)


# ---------------------------------------------------------------- v2 (P0-W4.2)

BM = {"n_finite": 10, "n_clipped_theta_0": 1, "n_clipped_theta_180": 2, "fraction_theta_0": 0.1,
      "fraction_theta_180": 0.2, "fraction_total": 0.3}


def _v2_screen():
    doc = _minimal()
    doc["schema_version"] = "2"
    doc["regimes"]["R-slurry"]["boundary_mass"] = {"nucleate": {"cos_theta": dict(BM)}}
    return doc


def _limit(status, value, reason=""):
    return {"status": status, "value_V": value, "reaction": "A + Li -> B" if value is not None else "",
            "reason": reason}


def _v2_stability():
    grid = [[0, 1], [1, 1], [0, -1]]
    state = {"conditions": {"a_Ca": 1e-3, "a_CO3": 1e-4},
             "phases": [{"index": 0, "label": "X(s)", "kind": "solid",
                         "components": [{"species": "X", "kind": "solid"}]},
                        {"index": 1, "label": "Y[2+] + X(s)", "kind": "mixed",
                         "components": [{"species": "Y[2+]", "kind": "aqueous"}, {"species": "X", "kind": "solid"}]}],
             "domains": {"index_grid": grid},
             "decomposition_energy": {"X": {"units": "eV/atom", "grid": [[0.0, 0.1], [0.2, 0.3], [0.0, None]]}}}
    return {"schema_version": "2", "mock": True, "generated_utc": "2000-01-01T00:00:00Z",
            "provenance": {"git_sha": "0" * 40, "git_dirty": False, "config_hash": "sha256:" + "a" * 64},
            "stability": {
                "R-slurry": {"kind": "pourbaix", "reference_electrode": "SHE", "temperature_K": 300.0,
                             "axes": {"pH": [1.0, 2.0], "E_V": [-1.0, 0.0, 1.0]},
                             "states": {"bulk": state, "enriched": json.loads(json.dumps(state))}},
                "R-cell": {"kind": "window", "reference_electrode": "Li+/Li", "temperature_K": 300.0,
                           "sink_assumption": {"active": "s", "statement": "cation leaves as the salt"},
                           "windows": {"X": {"reduction": _limit("ok", 1.0), "oxidation": _limit("ok", 4.0)},
                                       "Z": {"reduction": _limit("ok", 1.2),
                                             "oxidation": _limit("undetermined", None, "sink phase missing")}}}},
            "extensions": {"p0-w5": {"session": "x"}}}


def test_day1_mock_summary_still_validates(schema):
    summary = ROOT / "results" / "preprint" / "screen" / "mock" / "summary.json"
    jsonschema.validate(json.loads(summary.read_text(encoding="utf-8")), schema)


def test_v2_screen_and_stability_documents_validate(schema):
    jsonschema.validate(_v2_screen(), schema)
    jsonschema.validate(_v2_stability(), schema)
    both = _v2_screen()
    both["stability"] = _v2_stability()["stability"]
    jsonschema.validate(both, schema)


@pytest.mark.parametrize("mutate", [
    lambda d: d["regimes"]["R-slurry"].pop("boundary_mass"),                     # N2: required in v2
    lambda d: d["regimes"]["R-slurry"]["boundary_mass"]["nucleate"]["cos_theta"].update(fraction_total=1.5),
    lambda d: d["regimes"]["R-slurry"]["boundary_mass"].update({"corrosion": {}}),
    lambda d: d["provenance"].pop("prior_file"),                                  # screen needs its prior file
    lambda d: d["regimes"]["R-slurry"].update(dependence={"method": "vine"}),
])
def test_malformed_v2_screen_documents_are_rejected(schema, mutate):
    doc = _v2_screen()
    mutate(doc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema)


def _cell(d):
    return d["stability"]["R-cell"]


def _slurry(d):
    return d["stability"]["R-slurry"]


@pytest.mark.parametrize("mutate", [
    lambda d: _cell(d)["windows"]["Z"]["oxidation"].update(value_V=4.5),          # undetermined with a value
    lambda d: _cell(d)["windows"]["Z"]["oxidation"].update(reason=""),            # undetermined without a reason
    lambda d: _cell(d)["windows"]["X"]["oxidation"].update(value_V=None),         # ok without a value
    lambda d: _cell(d)["windows"]["X"]["oxidation"].update(status="finite"),      # status is ok | undetermined
    lambda d: _cell(d)["windows"]["X"].pop("oxidation"),                         # both limits per phase
    lambda d: _cell(d).pop("sink_assumption"),
    lambda d: _cell(d).update(reference_electrode="SHE"),
    lambda d: _slurry(d)["states"].pop("enriched"),                               # F2: both states
    lambda d: _slurry(d)["states"]["bulk"]["phases"][0].update(kind="liquid"),
    lambda d: _slurry(d)["states"]["bulk"]["decomposition_energy"]["X"].update(units="eV"),
    lambda d: _slurry(d)["states"]["bulk"]["conditions"].pop("a_CO3"),
    lambda d: _slurry(d).update(reference_electrode="Li+/Li"),
    lambda d: d["stability"].update({"R-other": {}}),
    lambda d: d.pop("stability"),                                                 # neither section
    lambda d: d.update(schema_version="1"),                                       # v1 has no stability
    lambda d: d.update(extensions={"someone": {}}),
])
def test_malformed_stability_documents_are_rejected(schema, mutate):
    doc = _v2_stability()
    mutate(doc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema)


# ------------------------------------------------------------------ schema v3 (P0-W4.3a)

def _v3():
    doc = _v2_screen()
    doc["schema_version"] = "3"
    reg = doc["regimes"]["R-slurry"]
    reg["prior_set"] = "ignorance"
    reg["barrier_prefactor"] = {"reference_gamma_nl": 0.1, "V_m": 3.7e-5, "T": 298.0, "B_kT": 1.0e4}
    reg["refused"] = {"speciation": {"activity_model": {"n_evaluated": 10, "n_refused": 1, "fraction_refused": 0.1}}}
    pt = {"axes": {"Ca_T": "1e-3 mol dm^-3"}, "P_good": 0.95, "P_bad": 0.05, "verdict": "feasible", "a_Ca_median": 1e-4}
    doc["claims"] = {
        "C1": {"verdict": "inconclusive", "tests": {"C1": {"verdict": "inconclusive", "gap": "key m_W unset",
                                                           "by_termination": {"t1": {"verdict": "feasible"}}}},
               "falsified_mass": None, "prior_set": "ignorance", "finding_eligible": True},
        "C2": {"verdict": "descriptor", "tests": {}, "falsified_mass": None, "role": "descriptor",
               "finding": {"statement": "the sequestration premise holds"}},
        "C5": {"verdict": "inconclusive", "tests": {"C5c_ox": {"verdict": "inconclusive", "scheme_table": [
            {"phase": "CaCO3", "sink": "LiClO4", "scheme": "expt", "role": "governing", "status": "ok", "value_V": 3.9}],
            "cutoff_axis": {"LFP": {"bound_V": 3.6, "verdict": "feasible"}}}},
               "dose_window": {"feasible_points": ["p"], "falsified_points": [], "inconclusive_points": [],
                               "points": {"p": pt}},
               "omega_controls": {"undersaturated": dict(pt, verdict="falsified", must="falsified")},
               "falsified_mass": None, "design_dependent": True}}
    doc["study"] = {"verdict": "inconclusive", "links": {"C1": "inconclusive"}, "deletion_test": None,
                    "gating_links": ["C1", "C3", "C4", "C5"], "framings": ["calcite", "ACC"], "prior_set": "ignorance",
                    "finding_eligible": False, "gaps": {"C1": ["m_W"]}, "truncation": None}
    return doc


def test_v3_documents_with_the_cp3_records_validate(schema):
    jsonschema.validate(_v3(), schema)
    st = _v2_stability()
    st["schema_version"] = "3"
    st["stability"]["R-slurry"]["water_lines"] = {"hydrogen": {"E_V": [-0.6, -0.7]}, "oxygen": {"E_V": [0.6, 0.5]},
                                                  "source": "params key"}
    jsonschema.validate(st, schema)


@pytest.mark.parametrize("mutate", [
    lambda d: d["claims"]["C1"].update({"verdict": "descriptor-ish"}),
    lambda d: d["regimes"]["R-slurry"].update({"prior_set": "guess"}),
    lambda d: d["regimes"]["R-slurry"]["barrier_prefactor"].pop("B_kT"),
    lambda d: d["claims"]["C5"]["tests"]["C5c_ox"]["scheme_table"][0].update({"role": "decisive"}),
    lambda d: d["claims"]["C5"]["dose_window"].pop("points"),
    lambda d: d["study"].update({"gating_links": ["C2"]}),
])
def test_malformed_v3_documents_are_rejected(schema, mutate):
    doc = _v3()
    mutate(doc)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema)
