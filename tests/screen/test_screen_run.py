"""Screen runner: production guards (rule R7, decision B3) and a tiny dry run on mock priors."""
import json
from pathlib import Path

import jsonschema
import numpy as np
import pytest

from nacre.screen import params_adapter, run, summary

ROOT = Path(__file__).resolve().parents[2]
MOCK = ROOT / "configs" / "preprint" / "mock_params.yaml"
TINY = {"propagation": {"draws_per_regime": 4096, "chunk": 1024},
        "sobol": {"target_ci_half_width": 0.2, "pilot_base": 128, "bootstrap": 20, "max_base": 1024},
        "shapley": {"n_var": 1000, "n_outer": 40, "n_inner": 3, "n_perm": 8, "bootstrap": 10,
                    "max_players_for_subsets": 8}}


def test_screen_config_states_the_required_design():
    cfg = run.load_config(ROOT)
    assert cfg["propagation"]["draws_per_regime"] >= 10 ** 6
    assert cfg["sobol"]["target_ci_half_width"] > 0
    rows = cfg["propagation"]["chunk"] * 32 * 8           # bytes of one chunk of up to 32 inputs
    assert rows < 500 * 2 ** 20


def test_dry_run_output_must_live_under_dryrun(tmp_path):
    with pytest.raises(run.ProductionRefused, match="dryrun"):
        run.run(ROOT, ROOT / "results" / "preprint" / "screen" / "x.json", params_path=MOCK, allow_mock=True,
                overrides=TINY)


def test_production_is_refused_for_mock_priors_and_before_cp3():
    rps = [params_adapter.regime_priors(MOCK, "R-slurry", allow_mock=True)]
    with pytest.raises(run.ProductionRefused, match="mock"):
        run.production_guard(ROOT, rps, ROOT / "results" / "preprint" / "screen" / "s.json")
    real = [params_adapter.RegimePriors("R-slurry", rps[0].joint, {}, str(ROOT / "lit" / "params.yaml"), "", False)]
    with pytest.raises(run.ProductionRefused, match="thresholds|p0-cp3"):
        run.production_guard(ROOT, real, ROOT / "results" / "preprint" / "screen" / "s.json")


def test_production_refuses_a_dryrun_destination(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "_git", lambda root, *a: "p0-cp3")
    th = tmp_path / "configs" / "preprint"
    th.mkdir(parents=True)
    (th / "thresholds.yaml").write_text("x: 1\n", encoding="utf-8")
    (tmp_path / "lit").mkdir()
    rps = [params_adapter.RegimePriors("R-slurry", None, {}, str(tmp_path / "lit" / "params.yaml"), "", False)]
    with pytest.raises(run.ProductionRefused, match="outside"):
        run.production_guard(tmp_path, rps, tmp_path / "results" / "preprint" / "screen" / "dryrun" / "s.json")
    run.production_guard(tmp_path, rps, tmp_path / "results" / "preprint" / "screen" / "s.json")


def test_tiny_dry_run_writes_a_schema_conforming_mock_document():
    out = ROOT / "results" / "preprint" / "screen" / "dryrun" / "test" / "summary.json"
    path, doc = run.run(ROOT, out, params_path=MOCK, regimes=("R-slurry",), allow_mock=True, overrides=TINY)
    jsonschema.validate(json.loads(path.read_text(encoding="utf-8")), summary.load_schema())
    assert doc["mock"] is True and doc["schema_version"] == "2"
    reg = doc["regimes"]["R-slurry"]
    assert set(reg["links"]) == {"anchor", "sequester", "nucleate"}
    assert reg["dependence"]["method"] == "gaussian_copula"
    bm = reg["boundary_mass"]["nucleate"]["cos_theta"]
    assert bm["n_finite"] == 4096 and bm["fraction_total"] > 0
    shap = reg["links"]["nucleate"]["shapley"]["barrier_het_template_kT"]
    assert sum(v["estimate"] for v in shap.values()) == pytest.approx(1.0, abs=1e-9)
    assert reg["links"]["nucleate"]["sensitivity_scale"]["barrier_het_template_kT"] == "log10"
    assert doc["provenance"]["params_sha"] is None
    assert reg["dependence_check"]["alternative"] == "independent"


def test_independence_option_samples_without_correlations():
    rp = params_adapter.regime_priors(MOCK, "R-slurry", allow_mock=True)
    cfg = run.load_config(ROOT)
    for k, v in TINY.items():
        cfg[k] = {**cfg[k], **v}
    reg = run.run_regime(rp, cfg, seed=1, links=["anchor"], dependence_check=False, independence=True)
    assert reg["dependence"] == {"method": "independent"}
    assert reg["dependence_check"] is None
    assert np.isfinite(reg["links"]["anchor"]["quantities"]["W_adh_wet"]["mean"])


def test_claims_and_study_from_screen_outputs_conform_to_the_schema():
    from nacre.screen import decision, thresholds as thr
    from screen_helpers import synthetic_resolver as _resolver
    rule = thr.load_thresholds(ROOT / thr.COPY)["rule"]
    rp = params_adapter.regime_priors(MOCK, "R-slurry", allow_mock=True)
    cfg = run.load_config(ROOT)
    for k, v in TINY.items():
        cfg[k] = {**cfg[k], **v}
    reg, outputs = run.run_regime(rp, cfg, seed=2, dependence_check=False, return_outputs=True)
    claims = run.evaluate_claims(rule, {"slurry": outputs}, _resolver())
    assert set(claims) == {"C1", "C2", "C3", "C4", "C5"}
    assert claims["C5"]["verdict"] == "inconclusive"               # no stability section given
    regimes = {"R-slurry": reg}
    run._attach_link_records(regimes, claims)
    assert "C3.C3a" in reg["links"]["nucleate"]["threshold_evaluation"]
    study = decision.study_verdict(rule, claims, None)
    doc = summary.build(regimes, {"git_sha": "0" * 40, "git_dirty": False, "config_hash": "sha256:" + "a" * 64,
                                  "prior_file": "p", "prior_file_hash": "sha256:" + "b" * 64},
                        mock=True, claims={c: {k: v for k, v in r.items()} for c, r in claims.items()}, study=study)
    jsonschema.validate(json.loads(json.dumps(doc, default=float)), summary.load_schema())
    assert study["verdict"] in ("inconclusive", "falsified")       # no deletion test: never feasible
