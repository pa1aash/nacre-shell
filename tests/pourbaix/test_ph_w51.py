"""PH-W5.1: phosphate benchmark (committed outputs and the display rule)."""
import csv
import json

import pytest

from nacre.pourbaix import ph_w51_bench as bm
from nacre.pourbaix.paths import POURBAIX_RESULTS

W51 = POURBAIX_RESULTS / "ph_w51"


@pytest.fixture(scope="module")
def bench():
    return json.loads((W51 / "benchmark_w51.json").read_text(encoding="utf-8"))


def test_every_benchmark_row_carries_a_display_label_and_a_cause(bench):
    for r in bench["rows"]:
        assert r["display"].split(" ")[0] in ("dft-benchmarked", "dft-benchmark-failed", "dft-unbenchmarked")
        assert r["cause"]


def test_display_label_follows_the_registered_error_per_atom(bench):
    lim = bench["summary"]["e_form"]["max"]
    for r in bench["rows"]:
        e = r.get("dft_minus_dfH_kJ_per_atom")
        if e is None or r["glass"]:
            assert r["display"].startswith("dft-unbenchmarked")
        elif abs(e) <= lim:
            assert r["display"].startswith("dft-benchmarked")
        else:
            assert r["display"].startswith("dft-benchmark-failed")


def test_brushite_excess_over_monetite_is_one_oxide_correction_per_lattice_water(bench):
    by = {r["phase"]: r for r in bench["rows"]}
    corr = bench["summary"]["oxide_correction_kJ_per_O"]
    assert by["brushite"]["hydrate_excess_per_water_kJ"] == pytest.approx(corr, abs=1.0)


def test_spread_of_the_ph_k1_set_is_the_reported_47_to_210(bench):
    by = {r["phase"]: r for r in bench["rows"]}
    k1_set = ["P2O5", "HAp", "b-TCP", "a-TCP", "brushite", "monetite", "Ca2P2O7", "AlPO4"]
    errs = [abs(by[p]["dft_minus_dfH_kJ"]) for p in k1_set]
    assert min(errs) == pytest.approx(46.84, abs=0.05)
    assert max(errs) == pytest.approx(210.0, abs=0.05)


def test_onset_spread_on_one_reaction_is_the_reported_finding(bench):
    s = bench["summary"]["onset_spread"]
    assert s["min"]["dft_minus_expt_V"] == pytest.approx(-1.08, abs=0.005)
    assert s["max"]["dft_minus_expt_V"] == pytest.approx(0.60, abs=0.005)


def test_phosphate_benchmark_does_not_pass(bench):
    assert bench["summary"]["benchmark_passes_for_phosphates"] is False


def test_csv_matches_json_rows(bench):
    with open(W51 / "benchmark_w51.csv", newline="", encoding="utf-8") as fh:
        next(fh)
        rows = list(csv.DictReader(fh))
    assert [r["phase"] for r in rows] == [r["phase"] for r in bench["rows"]]


def test_cause_slots_are_filled_from_rows():
    rows = [{"phase": "brushite", "dft_minus_dfH_kJ": -210.0, "corr_per_O_kJ": -66.0, "material_id": "x",
             "space_group": "Cc", "n_sites": 1},
            {"phase": "monetite", "dft_minus_dfH_kJ": -77.0, "corr_per_O_kJ": -66.0, "material_id": "y",
             "space_group": "P1", "n_sites": 1, "raw_minus_dfH_per_O_kJ": 47.0}]
    bm._causes(rows)
    assert "-66.5 kJ/mol per water" in rows[0]["cause"]
    assert rows[0]["hydrate_excess_per_water_kJ"] == pytest.approx(-66.5)


# ---------------------------------------------------------------- step 2: Al-O-H window
from nacre.pourbaix import ph_w51_al as al  # noqa: E402


def test_speciation_slope_of_al3_is_minus_three_per_ph():
    s = al.speciation(8.0, [5.0, 6.0], al.log_betas())
    assert s["Al3+"][1] - s["Al3+"][0] == pytest.approx(-3.0)


def test_window_edges_bracket_the_threshold():
    betas = al.log_betas()
    wnd = al.window(10.578, betas, 1.0e-4)
    for ph in (wnd["lower"], wnd["upper"]):
        assert float(al.speciation(10.578, ph, betas)["total"]) == pytest.approx(-4.0, abs=1e-6)
    assert wnd["lower"] < wnd["ph_min"] < wnd["upper"]


def test_window_is_empty_when_the_minimum_exceeds_the_threshold():
    assert al.window(10.578, al.log_betas(), 1.0e-6)["passive"] is False


def test_committed_window_and_published_statements():
    d = json.loads((W51 / "al_window.json").read_text(encoding="utf-8"))
    assert d["primary"]["solid"] == "Al(OH)3 am"
    assert 4.5 < d["primary"]["lower"] < 5.5 and 8.0 < d["primary"]["upper"] < 8.5
    assert d["reference"]["solid"] == "boehmite" and d["reference"]["upper_clipped"]
    assert d["published"]["TR-090"]["lower"] == 4.5 and d["published"]["TR-091"]["lower"] == 4.0
    alu = d["benchmark"][0]
    assert abs(alu["diff_kJ"]) < 5.0  # the aluminate DfG agrees with the hydrolysis constant


def test_a_al3_csv_covers_ph_5_to_8_5():
    with open(W51 / "a_al3_oxide.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(r for r in fh if not r.startswith("#")))
    assert float(rows[0]["pH"]) == 5.0 and float(rows[-1]["pH"]) == 8.5
    assert all(float(r["log10_a_Al3_AlOH3_am"]) > float(r["log10_a_Al3_boehmite"]) for r in rows)
