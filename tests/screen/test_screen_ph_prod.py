"""Production screen of the phosphate films (PH-W4.2): rows, gaps, route layer, refusals."""
import json
import shutil

import pytest

from nacre._util import repo_root
from nacre.screen import kscreen, ph_prod, ph_prov, ph_rows, run

ROOT = repo_root()
OUT = ROOT / "results/preprint/screen/dryrun_ph/test_ph_prod/summary.json"


@pytest.fixture(scope="module")
def doc():
    shutil.rmtree(OUT.parent, ignore_errors=True)
    path, d, stats = ph_prod.run_phosphate(ROOT, OUT, dry=True, stride=90)
    yield d
    shutil.rmtree(OUT.parent, ignore_errors=True)


def test_rows_follow_the_stage_rules(doc):
    assert ph_rows.check_presentation(doc["ph_rows"]) == []
    for r in doc["ph_rows"]:
        if r["stage"] == "slurry":
            assert "K1" not in r and "K2" in r
        if r["stage"] == "cell":
            assert not any(k in r for k in ("K2", "K3", "K4"))


def test_every_slurry_stage_phase_of_the_ladder_has_a_row_and_proceeds_under_f1(doc):
    t = kscreen.read_k1(ROOT / ph_prov.LADDER)
    slurry_phases = {p for (p, _, _), r in t.rows.items() if r.stage == "slurry"}
    rows = {r["phase"] for r in doc["ph_rows"] if r["stage"] == "slurry" and r["row_id"].endswith("_as_formed:slurry")}
    assert slurry_phases == rows
    gates = doc["extensions"]["p0-w4"]["ph_production"]["f1_gate"]
    assert gates and all(g["proceeds"] for g in gates.values())               # no phase is falsified at every cutoff class


def test_k3_and_k4_of_the_nucleus_framings_are_undetermined_with_the_missing_keys_named(doc):
    rows = {r["row_id"]: r for r in doc["ph_rows"]}
    for film, keys in (("hap_as_formed", {"gamma_nl_hap", "gamma_nv_hap"}), ("acp_as_formed", {"gamma_nl_acp", "gamma_nv_acp", "v_m_acp"})):
        r = rows[film + ":slurry"]
        for k in ("K3", "K4"):
            assert r[k]["verdict"] == "undetermined"
            assert keys <= set(r[k]["missing_keys"]) | {"v_m_acp"} and keys & set(r[k]["missing_keys"])
            assert r[k]["priors"]["ignorance"] == "none registered"
        assert r["deletion_test"]["verdict"] == "not run"
        assert r["retained_mass"] is None


def test_no_nacre_type_label_anywhere(doc):
    assert "nacre-type" not in json.dumps(doc)


def test_route_layer_is_report_only_and_undetermined_at_both_ends_of_f_min(doc):
    rl = doc["extensions"]["p0-w4"]["ph_production"]["route_layer"]
    ends = rl["f_min_interval"]["ends"]
    assert set(ends) == {"low_2D_square", "high_3D_sc"} and ends["low_2D_square"] < ends["high_3D_sc"]
    for end in ends:
        for st in rl["K2h"][end]["states"]:
            assert st["verdict"] == "undetermined" and st["gates"] is False
    for k in ("R1", "R2", "liquid_wetting"):
        assert rl[k]["verdict"] == "undetermined" and rl[k]["gating"] is False


def test_baselines_and_silicates_go_through_k1_k2_and_k4_only(doc):
    by = {r["row_id"]: r for r in doc["ph_rows"]}
    for film in ("baseline_hq_lipo3n", "baseline_tsinghua", "comparator_casio3", "comparator_li2sio3", "comparator_ca2sio4"):
        s = by[film + ":slurry"]
        assert "K3" not in s and s["K2"]["verdict"] == "undetermined" and s["K4"]["verdict"] == "undetermined"
        assert by[film + ":cell"]["K1"]["by_class"]


def test_production_refusals():
    with pytest.raises(run.ProductionRefused):                    # not a "_ph" run directory
        ph_prod.run_phosphate(ROOT, ROOT / "results/preprint/screen/no_such_run/summary.json")
    taken = ROOT / "results/preprint/screen/zz_taken_ph/summary.json"      # an existing document is never overwritten
    taken.parent.mkdir(parents=True)
    taken.write_text("{}")
    try:
        with pytest.raises(run.ProductionRefused):
            ph_prod.run_phosphate(ROOT, taken)
        assert taken.read_text() == "{}"
    finally:
        shutil.rmtree(taken.parent, ignore_errors=True)
    with pytest.raises(run.ProductionRefused):                    # a production run covers the whole grid
        ph_prod.run_phosphate(ROOT, ROOT / "results/preprint/screen/no_such_run_ph/summary.json", stride=3)
    with pytest.raises(run.ProductionRefused):
        ph_prod.run_phosphate(ROOT, ROOT / "results/preprint/screen/k2_dry/summary.json", dry=True)
