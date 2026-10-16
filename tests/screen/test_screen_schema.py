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
