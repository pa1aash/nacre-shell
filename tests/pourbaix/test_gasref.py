"""Gas-reference benchmark, the literature-input snapshot and the open-table sink salts (offline)."""
import json

import pytest
from pourbaix_helpers import offline  # noqa: F401

from nacre.pourbaix import cache, gasref, inputs, provenance, salts
from nacre.pourbaix.paths import POURBAIX_RESULTS

PARAMS_SHA = "680a44b2efdb94694b25f5317ddc3d73db2f117c"


@pytest.fixture(scope="module")
def params():
    return inputs.Params(inputs.load_snapshot(PARAMS_SHA, check_git=False))


@pytest.fixture(scope="module")
def bench(params):
    return {b["id"]: b for b in gasref.run_benchmark(params)["benchmarks"]}


def test_snapshot_matches_the_git_objects():
    snap = json.loads(inputs.snapshot_path(PARAMS_SHA).read_text(encoding="utf-8"))
    if provenance.git_object(PARAMS_SHA, inputs.PARAMS_PATH) is None:
        pytest.skip("params commit not in the local object store")
    assert inputs.verify_snapshot(snap) == []


def test_snapshot_refuses_a_tampered_entry():
    snap = json.loads(inputs.snapshot_path(PARAMS_SHA).read_text(encoding="utf-8"))
    if provenance.git_object(PARAMS_SHA, inputs.PARAMS_PATH) is None:
        pytest.skip("params commit not in the local object store")
    snap["entries"]["acc_offset"] = dict(snap["entries"]["acc_offset"], value=0.0)
    assert any("acc_offset" in p for p in inputs.verify_snapshot(snap))


def test_acc_offset_is_in_joule_per_mole(params):
    # W1 report: the offset is J mol^-1 (the Day 1 mock used kJ/mol)
    assert params.unit("acc_offset") == "J mol^-1"


def test_b1_experiment_is_the_w1_key_and_its_rows(offline, params, bench):
    b1 = bench["B1"]
    assert b1["experiment"]["value_J_per_mol"] == pytest.approx(params.value("drg_caco3_decomposition"))
    rows = {r["row_id"]: r for r in b1["experiment"]["rows"]}
    assert set(rows) == {"TI-010", "TI-051"}
    # TI-051 is printed as the formation from the oxides: the sign is reversed for decomposition
    assert rows["TI-051"]["sign_applied"] == -1 and rows["TI-051"]["value_J_per_mol"] > 0
    lo, hi = params.range("drg_caco3_decomposition")["min"], params.range("drg_caco3_decomposition")["max"]
    assert all(lo <= r["value_J_per_mol"] <= hi for r in rows.values())


def test_every_scheme_is_carried_and_none_chosen(offline, bench):
    for b in bench.values():
        assert set(b["schemes"]) == set(gasref.SCHEMES)


def test_schemes_bracket_the_co2_releasing_reactions(offline, bench):
    # janaf overestimates and mp underestimates every reaction that releases CO2
    for bid in ("B1", "B2", "B5", "B6", "B7"):
        assert bench[bid]["schemes"]["janaf"]["error_J_per_mol"] > 0 > bench[bid]["schemes"]["mp"]["error_J_per_mol"]


def test_reactions_without_co2_do_not_depend_on_the_co2_scheme(offline, bench):
    for bid in ("B3", "B4"):
        e = {s: v["dG_J_per_mol"] for s, v in bench[bid]["schemes"].items()}
        assert e["janaf"] == pytest.approx(e["mp"])


def test_b6_equilibrium_potential_lies_below_the_measured_onset(offline, bench):
    c = bench["B6"]["comparator"]
    # the measured onset includes an overpotential: it can only lie above equilibrium
    assert c["experimental_equilibrium_V"] <= c["range"]["max"]


def test_nbs_rows_parse_by_column(offline):
    ca = salts.nbs_row("Ca(ClO4)2")
    assert ca["dfH_kJ"] < 0 and ca["dfG_kJ"] is None and ca["S_J_per_K"] is None
    al = salts.nbs_row("AlCl3")
    assert al["dfG_kJ"] is not None
    # two independent fetched tables agree on AlCl3(cr) within a few kJ/mol
    assert abs(al["dfG_kJ"] - salts.janaf("AlCl3", 298.15)["dfG_kJ_per_mol"]) < 3.0


def test_committed_benchmark_reproduces(offline, params):
    path = POURBAIX_RESULTS / "gas_reference.json"
    if not path.is_file():
        pytest.skip("benchmark not generated yet")
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["provenance"]["params_sha"] == PARAMS_SHA
    fresh = gasref.run_benchmark(params)
    old = {b["id"]: b for b in doc["result"]["benchmarks"]}
    for b in fresh["benchmarks"]:
        for s, v in b["schemes"].items():
            assert v["dG_J_per_mol"] == pytest.approx(old[b["id"]]["schemes"][s]["dG_J_per_mol"], abs=1e-6)


def test_cache_extension_kept_the_day1_files():
    files = {f["file"]: f for f in cache.manifest()["files"]}
    assert "mp_entries_slurry_Al-C-Ca-H-Na-O.json" in files and "added_by" not in files["mp_entries_slurry_Al-C-Ca-H-Na-O.json"]
    assert all(f.get("added_by") == "P0-W5.2" for n, f in files.items()
               if n.startswith("janaf_") and n not in ("janaf_O2.json", "janaf_CO2.json"))
    assert cache.verify() == []
