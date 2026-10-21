"""The K1 reader on rows copied verbatim from W5's ladder_v3.csv (PH-W5.2): wide layout, pending E_lb, symbolic margins."""
import csv
from pathlib import Path

import pytest
import yaml

from nacre.screen import kscreen

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "fixtures" / "ladder_v3_real_rows.csv"
CA_GLASS = "Ca(PO3)2 / Ca-polyphosphate glass"
TSINGHUA = "baked aluminophosphate (Tsinghua)"


@pytest.fixture(scope="module")
def table():
    return kscreen.read_k1(FIXTURE)


def test_layout_is_detected_and_classes_follow_block_v6(table):
    assert table.layout == "v3"
    block = yaml.safe_load((ROOT / "configs/preprint/thresholds.yaml").read_text(encoding="utf-8"))
    cls = _find(block, "cutoff_classes")
    assert [c for c, v in cls.items() if isinstance(v, dict) and "E_c_V" in v] == [c for _, c in kscreen.V3_CLASS_COLUMNS]
    assert table.classes("HAp") == ["C_lo", "C_mid", "C_hi"] and table.low_cutoff_class("HAp") == "C_lo"


def test_inconclusive_row_has_upper_bound_and_pending_lower_bound(table):
    r = table.row("HAp", "C_lo", "crystalline")
    assert r.verdict == "inconclusive" and r.E_ub == pytest.approx(4.0674) and r.E_lb is None and r.margin == pytest.approx(0.1244)
    assert r.bracket() == {"E_ub": 4.0674, "E_lb": None, "E_lb_status": "pending", "E_ub_status": "sourced"}
    assert table.verdicts("HAp", "crystalline") == {"C_lo": "inconclusive", "C_mid": "falsified", "C_hi": "falsified"}
    assert table.row("HAp", "C_mid", "crystalline").overall == "inconclusive"   # falsified at every class only is falsified
    assert kscreen.proceeds({"by_class": table.verdicts("HAp", "crystalline")})["proceeds"]


def test_falsified_at_every_class_does_not_proceed(table):
    assert set(table.verdicts("Ca2SiO4", "crystalline").values()) == {"falsified"}
    assert not kscreen.proceeds({"by_class": table.verdicts("Ca2SiO4", "crystalline")})["proceeds"]


def test_undetermined_rows_have_no_bound_and_no_margin(table):
    for phase in ("AlPO4", TSINGHUA):
        r = table.row(phase, "C_lo", "crystalline")
        assert r.verdict == "undetermined" and r.E_ub is None and r.margin is None and r.budget_status == "incomplete"
        assert r.bracket()["E_ub_status"] == "pending"
        assert kscreen.proceeds({"by_class": table.verdicts(phase, "crystalline")})["proceeds"]


def test_symbolic_margin_is_kept_as_status_never_a_number(table):
    sym = [d for d in table.reactions if d["budget_status"].startswith("symbolic")]
    assert sym and all(d["margin"] is None and d["E_lb"] is None for d in sym)
    assert {d["phase"] for d in sym} == {"AlPO4", TSINGHUA}


def test_amorphous_gap_row_is_undetermined(table):
    r = table.row("brushite", "C_lo", "amorphous")
    assert r.verdict == "undetermined" and r.budget_status == "gap" and r.E_ub is None


def test_glass_row_uses_its_own_margin(table):
    r = table.row(CA_GLASS, "C_mid", "amorphous")
    assert r.verdict == "inconclusive" and r.margin == pytest.approx(0.1348) and r.E_ub == pytest.approx(4.8929)


def test_both_framings_row_and_skipped_rows(table):
    assert {table.row("Ca-modified aluminophosphate", "C_lo", f).verdict for f in kscreen.FRAMINGS} == {"undetermined"}
    kinds = {s["why"] for s in table.skipped}
    assert kinds == {"conversion step (no K1 verdict)", "tier 2 only (no tier-1 K1 row)"}
    assert not any(p == "chitosan" for p in table.phases())


def test_a_phase_without_a_row_is_undetermined_and_proceeds(table):
    class M:
        k1_phase, name, phase_state = "not in the ladder", "x", "crystalline"
    rec = kscreen.k1_for(table, M())
    assert rec["by_class"] == {} and "undetermined" in rec["note"] and kscreen.proceeds(rec)["proceeds"]


def test_overall_verdict_rule():
    f, i, u, p = "falsified", "inconclusive", "undetermined", "feasible"
    assert kscreen.overall_verdict({"a": f, "b": f}) == f
    assert kscreen.overall_verdict({"a": f, "b": p}) == p
    assert kscreen.overall_verdict({"a": u, "b": i}) == u
    assert kscreen.overall_verdict({"a": u, "b": f}) == i
    assert kscreen.overall_verdict({"a": i, "b": f}) == i


def test_known_readme_disagreement_is_reported_not_hidden(table):
    # Ca2SiO4 (comparator): budget 'incomplete' yet falsified at every class; the README says a partial margin cannot falsify
    bad = table.inconsistencies
    assert len(bad) == 1 and bad[0]["phase"] == "Ca2SiO4" and "partial margin" in bad[0]["problem"]


def test_unknown_stage_and_empty_class_cell_are_refused(tmp_path):
    text = FIXTURE.read_text(encoding="utf-8")
    p = tmp_path / "l.csv"
    p.write_text(text.replace(",comparator,", ",flange,"), encoding="utf-8")
    with pytest.raises(kscreen.K1Error, match="stage"):
        kscreen.read_k1(p)
    rows = list(csv.reader(text.splitlines()))
    col = rows[0].index("k1_class_lfp")
    rows[1][col] = ""
    with p.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)
    with pytest.raises(kscreen.K1Error, match="empty class"):
        kscreen.read_k1(p)


def test_verdicts_follow_the_edge_rule_against_the_blocks_cutoffs():
    # falsified at a class exactly when E_ub + m < inf(class), for every complete-budget row of the fixture
    block = yaml.safe_load((ROOT / "configs/preprint/thresholds.yaml").read_text(encoding="utf-8"))
    cls = _find(block, "cutoff_classes")
    inf = {c: min(v["E_c_V"]) for c, v in cls.items() if isinstance(v, dict) and "E_c_V" in v}
    assert list(inf) == ["C_lo", "C_mid", "C_hi"]
    t = kscreen.read_k1(FIXTURE)
    checked = 0
    for (phase, c, fr), r in t.rows.items():
        if r.budget_status == "complete" and r.E_ub is not None and r.margin is not None:
            assert (r.verdict == "falsified") == (r.E_ub + r.margin < inf[c]), (phase, c, fr)
            checked += 1
    assert checked >= 6


def _find(node, key):
    if isinstance(node, dict):
        if isinstance(node.get(key), dict) and "C_lo" in node[key]:
            return node[key]
        for v in node.values():
            r = _find(v, key)
            if r is not None:
                return r
    return None
