"""Stage rows, conversion rows, the presentation rule and the F5 panel (cp4 F1, F4, F5; PH-W4.2a); schema v5; the
route-layer dry runs (R1, R2, R3, one baseline) on mock priors."""
import copy
import json
import shutil

import jsonschema
import pytest

from nacre.screen import kscreen, ph_route_dry, ph_rows, routes, run, summary
from nacre.screen.mineral import Mineral

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _k1(by_class, framing, bracket=None):
    return {"phase": "P", "framing": framing, "by_class": by_class, "passes_at": [],
            "bracket": bracket or {c: {"E_ub": 4.0, "E_lb": None, "E_ub_status": "sourced", "E_lb_status": "pending"}
                                   for c in by_class}, "source": "mock"}


def _cell(fid="f", phase="Ca(PO3)2", route="R2", cr=None, am=None, baked=False):
    cr = cr or {"C_lo": "feasible", "C_hi": "feasible"}
    am = am or {"C_lo": "falsified", "C_hi": "falsified"}
    return ph_rows.k1_cell_row(fid, phase, {"crystalline": _k1(cr, "crystalline"), "amorphous": _k1(am, "amorphous")},
                               "route" if route else "baseline", route=route, baked=baked)


def _slurry(fid="f", phase="Ca(PO3)2", gate=None):
    return ph_rows.slurry_row(fid, phase, "route", "amorphous", {"verdict": "feasible", "evidence": {"k": "mock"}},
                              {"verdict": "not excluded", "evidence": {}}, {"verdict": "undetermined", "evidence": {}},
                              K2h={"verdict": "not gating", "evidence": {}}, route="R2", gate=gate)


# ------------------------------------------------------------------ cell rows and the framing rule
def test_route_cell_row_amorphous_governs_and_labels_requires_crystallisation():
    c = _cell()
    assert c["stage"] == "cell" and c["framing"] == "amorphous"
    assert c["K1"]["by_class"]["C_lo"]["verdict"] == "falsified"
    assert "requires crystallisation" in c["labels"]
    assert c["K1"]["by_class"]["C_lo"]["framings"]["crystalline"]["verdict"] == "feasible"
    assert not c["proceeds"]["proceeds"]                     # amorphous falsified at every class (F1)


def test_baseline_cell_row_reports_both_framings():
    c = _cell(route=None, baked=True)
    assert c["framing"] == "structure unspecified" and c["K1"]["by_class"]["C_lo"]["verdict"] is None
    assert "structure unspecified" in c["labels"]


def test_bracket_pending_is_carried():
    e = _cell()["K1"]["by_class"]["C_lo"]["framings"]["amorphous"]
    assert e["E_ub"] == 4.0 and e["E_lb"] is None and e["E_lb_status"] == "pending"


# ------------------------------------------------------------------ slurry rows and F1
def test_slurry_row_skips_k3_k4_only_when_k1_is_falsified_everywhere():
    gate = _cell()["proceeds"]
    s = _slurry(gate=gate)
    assert s["K3"]["verdict"] == "not run" and s["K4"]["verdict"] == "not run" and s["K2"]["verdict"] == "feasible"
    gate = _cell(am={"C_lo": "inconclusive", "C_hi": "falsified"})["proceeds"]
    s = _slurry(gate=gate)
    assert s["K3"]["verdict"] == "not excluded" and s["gate"]["proceeds"]


# ------------------------------------------------------------------ presentation rule
def test_used_as_formed_film_is_accepted():
    assert ph_rows.check_presentation([_slurry(), _cell()]) == []


def test_condensed_k1_with_orthophosphate_k2_k4_is_refused():
    rows = [_slurry(phase="HAp"), _cell(phase="Ca2P2O7")]
    assert any("without the conversion chain" in p for p in ph_rows.check_presentation(rows))


def test_the_chain_through_conversion_rows_is_accepted():
    rows = [_slurry(fid="b", phase="brushite"), _cell(fid="b", phase="Ca2P2O7"),
            ph_rows.conversion_row("b", "brushite", "monetite", T_conv_lit=473.0, T_cure=(373.0, 623.0)),
            ph_rows.conversion_row("b", "monetite", "Ca2P2O7", T_conv_lit=None, T_cure=(373.0, 623.0))]
    assert ph_rows.check_presentation(rows) == []
    s = ph_rows.chain_summary(rows, "b")
    assert s["weakest"] == "conversion monetite -> Ca2P2O7: undetermined"
    broken = rows[:3]
    assert ph_rows.check_presentation(broken)


def test_a_row_never_carries_both_stages():
    c = _cell()
    c["K2"] = {"verdict": "feasible", "evidence": {}}
    s = _slurry()
    s["K1"] = {"by_class": {}}
    probs = ph_rows.check_presentation([c, s])
    assert any("cell-stage row carries K2" in p for p in probs) and any("slurry-stage row carries K1" in p for p in probs)


def test_conversion_status():
    cure = (373.0, 623.0)
    assert ph_rows.conversion_status(473.0, cure) == "feasible within the baseline cure range"
    assert ph_rows.conversion_status(300.0, cure) == "feasible within the baseline cure range"
    assert ph_rows.conversion_status(800.0, cure) == "requires a higher temperature"
    assert ph_rows.conversion_status(None, cure) == "undetermined"
    assert ph_rows.conversion_status(473.0, None) == "undetermined"
    r = ph_rows.conversion_row("b", "brushite", "monetite", a_w_star=None, T_conv_lit=300.0, T_cure=cure)
    assert r["T_conv_position"] == "below" and "K1" not in r and r["stage"] == "conversion"


# ------------------------------------------------------------------ F5 panel
def test_ca_orthophosphate_low_cutoff_rows(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("phase,class,cutoff_inf_V,status,note\nHAp,C_hi,4.4,below,x\nHAp,C_lo,3.6,above,upper bound only\n",
                 encoding="utf-8")
    t = kscreen.read_k1(p)
    m = Mineral("hap", "Ca5(PO4)3OH", 5, 3, "k", "v", "apatite", nu_y=1, k1_phase="HAp")
    rec = {"K2": {"verdict": "feasible"}, "K3": {"verdict": "inconclusive", "admissibility": {"0.0": {"M_adm": 0.9}}},
           "K4": {"verdict": "inconclusive", "admissibility": {"0.0": {"M_adm": 0.8}}}}
    rows = ph_rows.ortho_low_cutoff_rows("hap_as_formed", "HAp", rec, t, m)
    slurry, cell = rows
    assert cell["scope_class"] == "C_lo" and slurry["retained_mass"]["M_adm"] == 0.8
    assert ph_rows.check_presentation(rows) == []


def test_lipo3_comparator_and_baselines():
    k1 = {"crystalline": _k1({"C_lo": "inconclusive"}, "crystalline"), "amorphous": _k1({"C_lo": "undetermined"}, "amorphous")}
    rows = ph_rows.comparator_lipo3_rows("lipo3", k1)
    assert rows[0]["K2"]["row"] == "L3" and rows[0]["role"] == "comparator" and "K3" not in rows[0]
    assert rows[1]["framing"] == "structure unspecified"
    hq = ph_rows.baseline_rows("hq", "Hydro-Quebec", "(LiPO3)n", k1, routes.baseline_k2("hq", hydro_quebec=True),
                               ph_rows.baseline_k4(None, 1e-9), hydro_quebec=True)
    assert hq[0]["K4"]["verdict"] == "undetermined" and "inference from chemistry" in " ".join(hq[0]["labels"])
    assert "K3" not in hq[0] and ph_rows.check_presentation(hq + rows) == []
    assert ph_rows.baseline_k4(2e-8, 1e-9)["verdict"] == "falsified"
    assert ph_rows.baseline_k4(1e-10, 1e-9)["verdict"] == "feasible"


# ------------------------------------------------------------------ schema v5
def _doc(rows):
    return {"schema_version": "5", "mock": True, "generated_utc": "2026-10-21T00:00:00Z",
            "provenance": {"git_sha": "0" * 40, "git_dirty": False, "config_hash": "sha256:" + "0" * 64}, "ph_rows": rows}


def test_schema_v5_accepts_the_rows():
    rows = [_slurry(), _cell(), ph_rows.conversion_row("f2", "brushite", "monetite", T_conv_lit=None, T_cure=None)]
    rows[0]["retained_mass"] = None
    summary.validate(json.loads(json.dumps(_doc(rows))))


@pytest.mark.parametrize("mutate", [
    lambda r: r[1].__setitem__("K3", {"verdict": "feasible", "evidence": {}}),          # K3 on a cell row
    lambda r: r[0].__setitem__("K1", {"by_class": {}}),                                 # K1 on a slurry row
    lambda r: r[0].__setitem__("stage", "kiln"),
    lambda r: r[0]["K2"].__setitem__("verdict", "passed"),
    lambda r: r[0]["K2"].__setitem__("evidence", {"k": "rumour"}),
    lambda r: r[0]["K2"].pop("evidence"),
    lambda r: r[1]["K1"]["by_class"]["C_lo"]["framings"]["amorphous"].__setitem__("E_lb", 3.9),   # pending with a value
    lambda r: r[0].pop("retained_mass"),
])
def test_schema_v5_rejects_malformed_rows(mutate):
    rows = [_slurry(), _cell()]
    rows[0]["retained_mass"] = None
    rows = json.loads(json.dumps(rows))
    mutate(rows)
    with pytest.raises(jsonschema.ValidationError):
        summary.validate(_doc(rows))


def test_ph_rows_need_schema_version_5():
    rows = json.loads(json.dumps([dict(_slurry(), retained_mass=None), _cell()]))
    doc = _doc(rows)
    doc["schema_version"] = "4"
    with pytest.raises(jsonschema.ValidationError):
        summary.validate(doc)


# ------------------------------------------------------------------ route-layer dry runs
@pytest.fixture(scope="module")
def out_dir():
    d = ROOT / run.DRYRUN_PH_DIR / "_pytest_routes"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("cls", ph_route_dry.CLASSES)
def test_route_dry_run_validates(cls, out_dir):
    path, doc, stats = ph_route_dry.run_route(ROOT, cls, out_dir / cls / "summary.json", allow_mock=True, draws_n=1024)
    summary.validate(json.loads(path.read_text(encoding="utf-8")))
    stages = sorted(r["stage"] for r in doc["ph_rows"])
    assert stages == ["cell", "slurry"] and len({r["film_id"] for r in doc["ph_rows"]}) == 1
    slurry = next(r for r in doc["ph_rows"] if r["stage"] == "slurry")
    for k in ("K2", "K4"):
        assert isinstance(slurry[k]["evidence"], dict)
    if cls != "baseline":
        assert slurry["route"] == cls and "K2h" in slurry and "K3" in slurry
        assert all(v == "mock" for v in slurry["K3"]["evidence"].values())
    else:
        assert "K3" not in slurry and slurry["role"] == "baseline"
    assert stats["seconds"] > 0


def test_route_dry_run_refusals(tmp_path, out_dir):
    with pytest.raises(ph_route_dry.DryRunRefused):
        ph_route_dry.run_route(ROOT, "R1", tmp_path / "s.json", allow_mock=True, draws_n=64)
    with pytest.raises(Exception):
        ph_route_dry.run_route(ROOT, "R1", out_dir / "x" / "s.json", params_path=ROOT / "lit" / "params.yaml",
                               allow_mock=True, draws_n=64)
    with pytest.raises(ph_route_dry.DryRunRefused):
        ph_route_dry.run_route(ROOT, "R4", out_dir / "y" / "s.json", allow_mock=True, draws_n=64)


def test_k1_ladder_input_path_is_w5s_v3_file():
    from nacre.screen.run import load_config
    k = kscreen.k_config(load_config(ROOT))
    assert k["k1_ladder"] == "results/preprint/pourbaix/ph_w52/ladder_v3.csv" == kscreen.LADDER.as_posix()
