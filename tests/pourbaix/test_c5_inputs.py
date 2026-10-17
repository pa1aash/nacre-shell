"""cp3 C5 inputs: the Omega test fixture and the R-cell governing-route rule (P0-W5.3)."""
import json

import pytest

from nacre.pourbaix import c5, inputs, omega_control
from nacre.pourbaix.paths import POURBAIX_RESULTS

PARAMS_SHA = "680a44b2efdb94694b25f5317ddc3d73db2f117c"


@pytest.fixture(scope="module")
def params():
    return inputs.Params(inputs.load_snapshot(PARAMS_SHA))


def test_fixture_dissolves_and_precipitates_where_it_must(params):
    doc = omega_control.build(params)
    by = {c["id"]: c for c in doc["cases"]}
    d = by["calcite_dissolves_after_acidification"]["reference_values"]
    p = by["calcite_supersaturated_alkaline_high_dic"]["reference_values"]
    assert d["log10_omega_ideal_central"] < 0 and d["sign_holds_for_all_reference_variants"]
    assert p["log10_omega_ideal_central"] > 0 and p["sign_holds_for_all_reference_variants"]


def test_reference_state_is_saturated(params):
    rs = omega_control.build(params)["reference_state"]
    lo = omega_control.log10_omega(rs["a_Ca_saturated"], rs["C_T"]["value_mol_kg"], rs["pH"]["value"],
                                   rs["pk1_carbonic"]["value"], rs["pk2_carbonic"]["value"],
                                   rs["log10_ksp_calcite"]["value"])
    assert lo == pytest.approx(0.0, abs=1e-12)


def test_fixture_inputs_are_keys_with_rows(params):
    for c in omega_control.build(params)["cases"]:
        for name in ("pH", "C_T"):
            ref = c["conditions"][name]
            assert ref["key"] and ref["row_ids"]
            assert ref["value"] == omega_control._pick(params, ref["key"], ref["from"])


def test_committed_fixture_matches_a_fresh_build(params):
    on_disk = json.loads((POURBAIX_RESULTS / "omega_control.json").read_text(encoding="utf-8"))
    fresh = json.loads(json.dumps(omega_control.build(params)))
    for d in (on_disk, fresh):
        d.pop("generated_utc")
    assert on_disk == fresh


def test_expt_governs_and_dft_is_corrected_only_without_it():
    b2 = {"janaf": 0.382, "mp": -0.233}
    lim = lambda v, r="CaCO3 + 2 LiA -> CaA2 + 0.5 O2 + CO2 + 2 Li": {"status": "ok", "value_V": v, "reaction": r}
    gov, corr = c5.governing({"expt": lim(3.9), "janaf": lim(4.3), "mp": lim(3.7)}, b2)
    assert gov["route"] == "expt" and gov["values_V"] == {"expt": 3.9}
    assert corr["janaf"] == pytest.approx(4.3 - 0.382) and corr["mp"] == pytest.approx(3.7 + 0.233)
    und = {"status": "undetermined", "value_V": None, "reaction": "", "reason": "x missing"}
    gov, _ = c5.governing({"expt": und, "janaf": lim(4.3), "mp": lim(3.7)}, b2)
    assert gov["route"] == "benchmark-corrected DFT"
    gov, _ = c5.governing({"expt": und, "janaf": und, "mp": und}, b2)
    assert gov["route"] is None and gov["values_V"] == {}


def test_verdict_rules():
    gov = {"values_V": {"expt": 3.94}}
    assert c5.verdict(gov, 4.3, 0.0, True, "feasible")[0] == "falsified"
    assert c5.verdict(gov, 3.6, 0.0, True, "feasible")[0] == "inconclusive"  # solid-salt pass
    assert c5.verdict(gov, 3.6, 0.0, False, "feasible")[0] == "feasible"
    assert c5.verdict({"values_V": {}}, 3.6, 0.0, False, "feasible")[0] == "inconclusive"


def test_every_e_cell_max_row_has_a_cathode_class(params):
    classes = c5.cathode_classes(params)
    rows = {r for c in classes.values() for r in c["rows"]}
    assert rows == set(params.entry("e_cell_max")["sources"])
    assert "other" not in classes
