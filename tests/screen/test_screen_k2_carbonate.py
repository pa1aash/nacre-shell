"""K2 framings of carbonate, the label field and the per-polymorph falsifiability control (PH-W4.2e)."""
import json

import pytest

from nacre._util import repo_root
from nacre.screen import k2_carbonate as k2
from nacre.screen import run

ROOT = repo_root()
REQUIRED = {"calcite": True, "aragonite": True, "ACC": False}
OK = {"calcite": True, "aragonite": True, "ACC": True}


def test_registered_framings_and_keys():
    cfg = run.load_config(ROOT)
    assert k2.registered_framings(cfg) == REQUIRED
    keys = k2.ksp_keys(cfg)
    assert keys["aragonite"] == "log10_ksp_aragonite_25c_i0"          # the key with a width, never the older one
    assert keys["calcite"] == "log10_ksp_calcite" and keys["ACC"] == "log10_ksp_acc"
    assert "log10_ksp_aragonite" not in keys.values()
    assert cfg["bindings"]["R-slurry"]["by_framing"]["aragonite"]["V_m"] == "v_m_aragonite"
    assert (cfg["registrations"]["framings"]) == ["calcite", "ACC"]    # the chain framings are unchanged


REGION = "R-slurry K2 grid g1: 40 of 324 cells"
WINDOW = "Ca_T 0.0001 to 0.1 mol dm^-3"


def test_label_texts_are_exact_and_there_is_no_nacre_type_label():
    assert k2.polymorph_label("calcite", "feasible", REGION) == \
        "calcite (suitable against dissolution, a necessary condition, in [%s])" % REGION
    assert k2.polymorph_label("aragonite", "feasible", REGION) == \
        "aragonite (dissolution stability only; formation unsupported at slurry pH and room temperature)"
    assert k2.polymorph_label("ACC", "falsified", REGION, WINDOW) == \
        "ACC (reported beside calcite and aragonite; dose window [%s]; not required to pass)" % WINDOW
    assert not hasattr(k2, "LABEL_NACRE_TYPE") and not hasattr(k2, "carbonate_label")
    rec = k2.k2_record({"calcite": "feasible", "aragonite": "feasible", "ACC": "feasible"}, OK, REQUIRED,
                       {"calcite": REGION}, {"ACC": WINDOW})
    assert "carbonate_label" not in rec and set(rec) == {"polymorphs"}
    assert "nacre-type" not in json.dumps(rec) and "nacre" not in json.dumps(rec).lower()


@pytest.mark.parametrize("verdict, word, text", [
    ("falsified", "excluded", "calcite (excluded in [%s])" % REGION),
    ("inconclusive", "open", "calcite (open in [%s])" % REGION),
    (None, "undetermined", "calcite (undetermined in [%s])" % REGION),
])
def test_calcite_that_does_not_pass_carries_its_regime_word(verdict, word, text):
    rec = k2.k2_record({"calcite": verdict, "aragonite": "feasible", "ACC": None}, OK, REQUIRED, {"calcite": REGION})
    assert rec["polymorphs"]["calcite"]["label"] == text and rec["polymorphs"]["calcite"]["regime"] in (word, "open")
    assert "suitable" not in rec["polymorphs"]["calcite"]["label"]


def test_aragonite_label_never_claims_formation_and_names_its_regime_when_it_fails():
    rec = k2.k2_record({"calcite": "feasible", "aragonite": "falsified", "ACC": None}, OK, REQUIRED)
    lab = rec["polymorphs"]["aragonite"]["label"]
    assert lab.startswith("aragonite (excluded; dissolution stability only") and "formation unsupported" in lab


def test_regime_vocabulary_is_the_registered_one():
    assert set(k2.REGIME.values()) == {"suitable against dissolution", "excluded", "open", "undetermined"}


def test_failed_control_makes_the_polymorph_inconclusive():
    v = {"calcite": "feasible", "aragonite": "feasible", "ACC": "feasible"}
    rec = k2.k2_record(v, dict(OK, aragonite=False), REQUIRED, {"calcite": REGION})
    assert rec["polymorphs"]["aragonite"]["verdict"] == "inconclusive"
    assert rec["polymorphs"]["aragonite"]["raw_verdict"] == "feasible"
    assert rec["polymorphs"]["aragonite"]["regime"] == "open"
    assert rec["polymorphs"]["calcite"]["verdict"] == "feasible"
    # ACC is reported beside the two and its control failing does not touch their labels
    rec = k2.k2_record(v, dict(OK, ACC=False), REQUIRED, {"calcite": REGION})
    assert rec["polymorphs"]["ACC"]["verdict"] == "inconclusive"
    assert rec["polymorphs"]["calcite"]["label"].startswith("calcite (suitable against dissolution")


@pytest.fixture(scope="module")
def controls():
    return k2.run_controls(ROOT, draws=2 ** 12)


def test_control_states_are_the_low_dose_corner(controls):
    cfg = run.load_config(ROOT)
    assert controls["corner"]["axes"]["Ca_T"].startswith("%g" % min(cfg["design_axes"]["Ca_T"]["values"]))
    assert controls["corner"]["axes"]["C_T"] == "dic_slurry@min"


@pytest.mark.parametrize("polymorph", ["calcite", "aragonite", "ACC"])
def test_omega_test_flags_undersaturation_at_the_low_dose_corner(controls, polymorph):
    r = controls["polymorphs"][polymorph]
    assert r["undersaturated"]["verdict"] == "falsified" and r["flags_undersaturation"]
    assert r["undersaturated"]["P_bad"] >= controls["p_cred"]
    assert r["supersaturated"]["verdict"] == "feasible" and r["supersaturated_reports_stability"]


def test_aragonite_reads_the_new_key_and_the_solubility_order_is_printed(controls):
    assert controls["polymorphs"]["aragonite"]["ksp_key"] == "log10_ksp_aragonite_25c_i0"
    order = controls["solubility_order"]
    assert order["more_soluble"] == max(order["log10_ksp"], key=order["log10_ksp"].get)


def test_the_dry_run_output_stays_under_dryrun_ph():
    with pytest.raises(SystemExit):
        k2.main(["--out", "results/preprint/screen/k2_carbonate_controls.json"])


def test_the_older_aragonite_key_is_superseded_and_not_read(monkeypatch):
    cfg = run.load_config(ROOT)
    assert k2.superseded_keys(cfg) == {"log10_ksp_aragonite": "superseded, not read (replaced by log10_ksp_aragonite_25c_i0, which carries a width)"}
    from nacre.screen import decision, params_adapter, study
    seen = set()
    real = params_adapter.regime_priors

    def spy(path, regime, allow_mock=False, bindings=None, **kw):
        seen.update((bindings or {}).values())
        rp = real(path, regime, allow_mock, bindings=bindings, **kw)
        seen.update(rp.joint.names)
        return rp
    monkeypatch.setattr(params_adapter, "regime_priors", spy)
    asked = []
    for name in ("value", "get", "range", "has"):
        orig = getattr(decision.Resolver, name)
        monkeypatch.setattr(decision.Resolver, name, (lambda o: lambda self, key, *a, **k: (asked.append(key), o(self, key, *a, **k))[1])(orig))
    doc, _ = params_adapter.read_table(ROOT / params_adapter.PRODUCTION_PARAMS, False)
    resolver = decision.Resolver.from_table(doc)
    pts = study.control_points(cfg, resolver)
    vals, _ = pts["undersaturated"]
    out = study._control(ROOT / params_adapter.PRODUCTION_PARAMS, cfg, False, "table", True, 2 ** 10, 2 ** 10, 1, 0.9, vals, {},
                         framing="aragonite")
    assert out.get("verdict") in ("falsified", "inconclusive")
    assert "log10_ksp_aragonite_25c_i0" in seen
    assert "log10_ksp_aragonite" not in seen and "log10_ksp_aragonite" not in asked


def test_second_control_is_the_same_corner_in_the_unmodified_slurry_and_shows_where_undersaturation_sets_in(controls):
    cfg = run.load_config(ROOT)
    spec = cfg["omega_control_unmodified"]
    assert spec["Ca_T"] == cfg["omega_control"]["states"]["undersaturated"]["Ca_T"]           # the same low-dose corner
    assert spec["C_T"] == cfg["omega_control"]["states"]["undersaturated"]["C_T"]
    for pol in ("calcite", "aragonite", "ACC"):
        sc = controls["polymorphs"][pol]["second_control"]
        assert sc["label"].startswith("low-dose corner in the unmodified alkaline slurry (pH 10 to 13)")
        phs = sorted(float(x) for x in sc["scan"])
        assert phs[0] == 10.0 and phs[-1] == 13.0 and len(phs) == 13
        assert sc["undersaturation"]["pattern"] in ("undersaturated throughout the scan", "verdict changes along the scan",
                                                    "not undersaturated anywhere in the scan")
        # the gating control is the modified-pH corner, and it is distinct from the unmodified scan
        assert controls["polymorphs"][pol]["undersaturated"]["axes"]["pH"] == "ph_slurry_modified@min"
