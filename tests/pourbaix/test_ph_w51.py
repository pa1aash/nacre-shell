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


# ---------------------------------------------------------------- steps 3 to 7: ladder v2
from nacre.pourbaix import ph_k1 as k1  # noqa: E402
from nacre.pourbaix import ph_w51_ladder as lad  # noqa: E402


@pytest.fixture(scope="module")
def doc():
    return json.loads((W51 / "ph_w51.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ladder():
    with open(W51 / "ladder_v2.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(r for r in fh if not r.startswith("#")))


def test_vitrification_bound_excludes_the_unphysical_pair():
    v = lad.vitrification_bound()
    assert [x["glass_row"] for x in v["excluded"]] == ["TT-044"]
    assert v["h_max_kJ_per_PO3"] == pytest.approx((-296.2 + 300.0) * 4.184, abs=0.01)


def test_ca_metaphosphate_crystal_lies_below_its_glass(doc):
    v = doc["staged_products"]["values"]
    assert v["Ca(PO3)2"]["dfG_kJ"] < v["Ca(PO3)2-glass"]["dfG_kJ"]
    assert v["Ca(PO3)2"]["u_kJ"] > v["Ca(PO3)2"]["u_vit_kJ"]  # inflated correction is carried in the budget


def test_extra_reactions_balance():
    lad.install()
    for sid, reactions in lad.EXTRA_REACTIONS.items():
        for _, _, extra, products in reactions:
            r = k1.build_reaction(sid, extra, products)
            assert r[sid] == pytest.approx(-1.0) and r["Li"] > 0


def test_every_ladder_row_has_stage_and_framing(ladder):
    for r in ladder:
        assert r["row_type"] in ("phase", "baseline", "control", "matrix", "conversion")
        if r["row_type"] != "conversion":
            assert r["stage"] and r["framing"]


def test_stage_assignment_follows_f4(ladder):
    stage = {r["phase"]: r["stage"] for r in ladder if r["row_type"] == "phase"}
    for p in ("brushite", "ACP", "HAp"):
        assert stage[p] == "slurry"
    for p in ("Ca2P2O7", "Ca(PO3)2 / Ca-polyphosphate glass", "AlPO4", "Al(PO3)3"):
        assert stage[p] == "cell"


def test_matrix_rungs_never_carry_a_tier1_number(ladder):
    for r in ladder:
        if r["row_type"] == "matrix":
            assert r["E_ub_V"] == "" and r["label"].startswith("gap, matrix-risk flag")


def test_al_pmeta3_stays_undetermined_whatever_the_dft_says(ladder):
    for r in ladder:
        if r["phase"] in ("Al(PO3)3", "Al-polyphosphate (R1 gel)"):
            assert r["E_ub_V"] == ""
            assert r["status_4.2-4.3 V"] == "undetermined"


def test_no_upper_bound_is_reported_as_a_pass(ladder):
    for r in ladder:
        for c in ("status_LFP-class", "status_4.2-4.3 V", "status_4.4-4.5 V"):
            assert r.get(c, "") != "pass"


def test_bracket_is_pending_without_the_anion_key(doc, ladder):
    if doc["bracket"]["computed"]:
        pytest.skip("bracket computed")
    assert "hydration_free_energy_clo4" in doc["bracket"]["missing"]
    assert all(r["E_lb_V"] == "pending PH-W1.3" for r in ladder if r["row_type"] in ("phase", "control")
               and r["E_ub_V"])


def test_carbonate_control_stays_frozen_and_f7_comparator_is_labelled(doc):
    f7 = doc["carbonate_f7"]
    assert f7["expt_V"] == pytest.approx(k1.FROZEN_INVENTORY_V, abs=1e-3)
    assert set(f7["dft_2026_09_28_V"]) == {"janaf", "mp"}


def test_aw_star_is_one_when_dg_is_zero():
    star, rng = lad._aw_star(0.0, 1.0, 2)
    assert star == pytest.approx(1.0) and rng[0] < 1.0 < rng[1]


def test_report_respects_the_line_limit():
    assert len((W51 / "ph_w51.md").read_text(encoding="utf-8").splitlines()) <= 60
