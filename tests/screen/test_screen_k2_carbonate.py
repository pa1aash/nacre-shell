"""K2 framings of carbonate, the label field and the per-polymorph falsifiability control (PH-W4.2e)."""
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


@pytest.mark.parametrize("v, label", [
    ({"calcite": "feasible", "aragonite": "feasible", "ACC": "falsified"}, k2.LABEL_NACRE_TYPE),
    ({"calcite": "feasible", "aragonite": "feasible", "ACC": None}, k2.LABEL_NACRE_TYPE),
    ({"calcite": "feasible", "aragonite": "falsified", "ACC": "feasible"}, k2.LABEL_CARBONATE),
    ({"calcite": "feasible", "aragonite": "inconclusive"}, k2.LABEL_CARBONATE),
    ({"calcite": "feasible", "aragonite": None}, k2.LABEL_CARBONATE),               # aragonite undetermined (data missing)
    ({"calcite": "feasible"}, k2.LABEL_CARBONATE),                                   # aragonite test not registered
    ({"calcite": "falsified", "aragonite": "feasible"}, k2.LABEL_CARBONATE),
])
def test_label_rule(v, label):
    assert k2.carbonate_label(v, OK, REQUIRED) == label
    assert label in k2.LABELS


def test_failed_control_makes_the_polymorph_inconclusive_and_blocks_the_label():
    v = {"calcite": "feasible", "aragonite": "feasible", "ACC": "feasible"}
    rec = k2.k2_record(v, dict(OK, aragonite=False), REQUIRED)
    assert rec["polymorphs"]["aragonite"]["verdict"] == "inconclusive"
    assert rec["polymorphs"]["aragonite"]["raw_verdict"] == "feasible"
    assert rec["carbonate_label"] == k2.LABEL_CARBONATE
    # ACC is reported beside the two and never required, even when its control fails
    rec = k2.k2_record(v, dict(OK, ACC=False), REQUIRED)
    assert rec["polymorphs"]["ACC"]["verdict"] == "inconclusive" and rec["carbonate_label"] == k2.LABEL_NACRE_TYPE


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
