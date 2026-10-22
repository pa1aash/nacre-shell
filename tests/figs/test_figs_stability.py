"""PH-W6.3: the per-pH K2 states and the stability map (fig17)."""
import pytest
from figs_helpers import REPO

from nacre.figs import build, k2ph, paths, upstream


def _real_states():
    return k2ph.states(upstream.load("k2_perph_ph2", REPO), upstream.load("k2_grid_ph", REPO),
                       upstream.load("k2_acid_ph2", REPO), upstream.load("k2_alkaline_ph2", REPO))


def _mod(fid):
    return build.load_template(paths(REPO)["src"] / (fid + ".py"))


def test_pins_are_the_committed_files():
    for key in ("k2_perph_ph2", "k2_acid_ph2", "k2_alkaline_ph2"):
        upstream.snapshot_bytes(key, REPO)
        assert upstream.entry(key, REPO)["merged_tree"]["same_bytes"] is True


def test_states_cover_every_candidate_at_every_ph():
    st = _real_states()
    assert sorted(st) == sorted(k2ph.CARBONATES + k2ph.PHOSPHATES)
    for phase, by in st.items():
        assert sorted(by["acid"]) == [4.5, 5.5, 6.5, 7.5, 8.5] and sorted(by["alkaline"]) == [10.0, 12.0, 13.0]


def test_first_pass_ph_and_doses_agree_with_the_w45_report():
    st = _real_states()

    def first(p):
        return min(ph for ph, s in st[p]["acid"].items() if s.n_pass)
    assert {p: first(p) for p in ("HAp", "ACP", "b-TCP", "OCP", "brushite", "calcite", "aragonite", "ACC")} == {
        "HAp": 4.5, "ACP": 5.5, "b-TCP": 4.5, "OCP": 4.5, "brushite": 4.5, "calcite": 6.5, "aragonite": 6.5, "ACC": 8.5}
    assert all(st[p]["acid"][first(p)].high for p in ("HAp", "ACP", "b-TCP", "OCP", "brushite", "calcite", "aragonite", "ACC"))
    assert not st["HAp"]["acid"][6.5].high
    assert all(s.n_pass == 0 for p in ("a-TCP", "Li3PO4") for s in st[p]["acid"].values())
    assert {s.word for s in st["a-TCP"]["acid"].values()} == {"undetermined"}


def test_a_count_mismatch_is_refused():
    doc = upstream.load("k2_perph_ph2", REPO)
    bad = {"columns": doc["columns"], "rows": [dict(r) for r in doc["rows"]]}
    for r in bad["rows"]:
        if r["phase"] == "HAp" and r["grid"] == "acid" and r["pH"] == "4.5":
            r["n_passing"] = "6"
    with pytest.raises(ValueError, match="cells pass"):
        k2ph.states(bad, upstream.load("k2_grid_ph", REPO), upstream.load("k2_acid_ph2", REPO),
                    upstream.load("k2_alkaline_ph2", REPO))


def test_processing_state_takes_the_lowest_passing_dose():
    st = _real_states()
    assert k2ph.processing(st["HAp"]["alkaline"]).high is False
    assert k2ph.processing(st["ACP"]["alkaline"]).high is True
    assert k2ph.processing(st["a-TCP"]["alkaline"]).word == "undetermined"


def test_stability_map_rows_and_bars():
    f17 = _mod("fig17")
    ladder, st = upstream.load("ladder_v3", REPO), _real_states()
    ub = f17.upper_bounds(ladder)
    assert ub["HAp"] == (4.0674, True) and ub["AlPO4"] == (5.2105, False) and "OCP" not in ub and "Li3PO4" not in ub
    rows = f17.map_rows(ladder, st)
    assert [r[0] for r in rows] == ["calcite", "a-TCP", "ACP", "b-TCP", "HAp", "brushite"]
    off = f17.offsets(rows)
    assert off["ACP"] < off["b-TCP"] and off["HAp"] == 0.0
    bars = [p for p, _e, _c in f17.bar_rows(ladder, {r[0] for r in rows})]
    assert "AlPO4" in bars and "Ca2P2O7" in bars and len(bars) == 8
