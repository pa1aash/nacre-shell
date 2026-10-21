"""PH-W5.2: ladder v3 (committed outputs and the verdict rule)."""
import csv

import pytest
import yaml

from nacre.pourbaix import ph_w52 as w52
from nacre.pourbaix.paths import POURBAIX_RESULTS

W52 = POURBAIX_RESULTS / "ph_w52"

COLUMNS = ["phase", "framing", "stage", "reaction_id", "route", "E_ub_V", "E_lb_V", "margin_V", "budget_status",
           "benchmark_status", "k1_class_lfp", "k1_class_42_43", "k1_class_44_45", "k1_verdict", "row_ids", "notes"]


@pytest.fixture(scope="module")
def rows():
    with (W52 / "ladder_v3.csv").open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return reader.fieldnames, list(reader)


def _row(rows, phase, framing, rid):
    return next(r for r in rows[1] if r["phase"].startswith(phase) and r["framing"] == framing and r["reaction_id"] == rid)


def test_column_list_and_order(rows):
    assert rows[0] == COLUMNS == w52.COLUMNS


def test_e_lb_is_pending_so_no_row_passes(rows):
    for r in rows[1]:
        assert r["E_lb_V"] in ("pending", "")
        assert r["k1_verdict"] != "pass"


def test_ca_po3_2_crystal_row_moves_to_4_982_and_the_glass_row_does_not(rows):
    cr = _row(rows, "Ca(PO3)2", "crystalline", "r1")
    assert float(cr["E_ub_V"]) == pytest.approx(4.9818, abs=5e-5)
    assert float(cr["margin_V"]) == pytest.approx(0.190, abs=5e-4)
    assert "ruling (b)" in cr["notes"]
    gl = _row(rows, "Ca(PO3)2", "amorphous", "r1")
    assert float(gl["E_ub_V"]) == pytest.approx(4.8929, abs=5e-5)
    assert float(gl["margin_V"]) == pytest.approx(0.1348, abs=5e-5)


def test_margins_equal_the_committed_block_copy(rows):
    block = yaml.safe_load((W52 / "margins_v6_block.yaml").read_text(encoding="utf-8"))["margins_v6"]
    cr = block["m_K1_amorphous"]["ruling_b"]["crystalline_reference_row"]
    r = _row(rows, "Ca(PO3)2", "crystalline", "r1")
    assert float(r["E_ub_V"]) == pytest.approx(cr["E_ub_V"], abs=5e-5) and float(r["margin_V"]) == pytest.approx(cr["m_V"], abs=5e-5)
    for b in block["m_K1"]["rows"]:
        if b["status"] != "set" or b["phase"].startswith("Ca(PO3)2") and b["framing"] == "crystalline":
            continue
        r = _row(rows, b["phase"], b["framing"], b["reaction"])
        assert float(r["E_ub_V"]) == pytest.approx(b["E_ub_V"], abs=5e-5)
        assert float(r["margin_V"]) == pytest.approx(b["m_V"], abs=5e-5)


def test_falsified_example(rows):
    hap = _row(rows, "HAp", "crystalline", "ALL")
    assert (hap["k1_class_lfp"], hap["k1_class_42_43"], hap["k1_class_44_45"]) == ("inconclusive", "falsified", "falsified")
    assert hap["k1_verdict"] == "inconclusive"


def test_inconclusive_example(rows):
    r = _row(rows, "Ca(PO3)2", "amorphous", "ALL")
    assert (r["k1_class_lfp"], r["k1_class_42_43"], r["k1_class_44_45"], r["k1_verdict"]) == ("inconclusive",) * 4


def test_undetermined_examples(rows):
    r = _row(rows, "AlPO4", "crystalline", "ALL")
    assert r["k1_verdict"] == "undetermined" and r["margin_V"] == ""
    assert _row(rows, "AlPO4", "crystalline", "r4")["budget_status"] == "incomplete"
    am = _row(rows, "HAp", "amorphous", "-")
    assert am["k1_verdict"] == "undetermined" and "symbolic" in am["notes"]


def test_rule_unit():
    assert w52.class_verdict(4.0, 0.1, True, 4.2, 4.3) == "falsified"
    assert w52.class_verdict(4.3, 0.1, True, 4.2, 4.3) == "inconclusive"
    assert w52.class_verdict(4.0, 0.1, False, 4.2, 4.3) == "undetermined"
    assert w52.class_verdict(4.0, None, True, 4.2, 4.3) == "undetermined"
    assert w52.class_verdict(5.0, 0.1, True, 4.2, 4.3, e_lb=4.45) == "pass"
    assert w52.overall(["falsified"] * 3) == "falsified"
    assert w52.overall(["inconclusive", "falsified", "falsified"]) == "inconclusive"
    assert w52.overall(["undetermined", "falsified", "falsified"]) == "inconclusive"
    assert w52.overall(["undetermined", "undetermined", "inconclusive"]) == "undetermined"
    assert w52.overall(["inconclusive", "pass", "falsified"]) == "pass"


def test_passivation_window_rows():
    with (W52 / "passivation_window_v3.csv").open(encoding="utf-8", newline="") as fh:
        wr = list(csv.DictReader(fh))
    am = {r["al_level_M"]: r for r in wr if r["solid"] == "Al(OH)3 am"}
    assert am["0.0001"]["ph_lower"] == "4.98" and am["0.0001"]["ph_upper"] == "8.29"
    assert am["1e-06"]["window"] == "none"
    assert any(r["solid"] == "boehmite" and r["role"].startswith("reference") for r in wr)


def test_incomplete_budget_row_cannot_falsify(rows):
    assert w52.gate_incomplete(["falsified", "inconclusive", "falsified"], False) == ["undetermined", "inconclusive", "undetermined"]
    assert w52.gate_incomplete(["falsified"] * 3, True) == ["falsified"] * 3
    for r in rows[1]:
        if r["budget_status"] == "incomplete":
            for c in ("k1_class_lfp", "k1_class_42_43", "k1_class_44_45", "k1_verdict"):
                assert r[c] != "falsified", (r["phase"], r["reaction_id"], c)
    r = _row(rows, "Ca2SiO4", "crystalline", "ALL")
    assert (r["k1_class_lfp"], r["k1_class_42_43"], r["k1_class_44_45"], r["k1_verdict"]) == ("undetermined",) * 4
    assert "cannot falsify" in r["notes"]


def test_acp_is_amorphous_slurry_undetermined_with_labelled_reference(rows):
    am = [r for r in rows[1] if r["phase"] == "ACP" and r["framing"] == "amorphous"]
    assert len(am) == 1 and am[0]["stage"] == "slurry" and am[0]["k1_verdict"] == "undetermined"
    assert "no amorphous ACP thermochemistry" in am[0]["notes"]
    ref = [r for r in rows[1] if r["phase"] == "ACP" and r["framing"] == "crystalline"]
    assert ref and all("reference" in r["route"] and "reference only" in r["notes"] for r in ref)
