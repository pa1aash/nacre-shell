"""cp5a rulings on the symbol bindings (PH-W4.2d): rows 1, 6, 7, 8 and 9."""
import hashlib
import re
from pathlib import Path

import pytest
import yaml

from nacre.physics import bindings as bd
from nacre.physics.constants import FARADAY

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "configs" / "preprint" / "symbol_bindings.yaml"
AQ_KEYS = ("dfg_ca2_aq", "dfg_co3_aq", "dfg_hco3_aq", "dfg_co2_aq", "dfg_al3_aq", "dfg_al_oh4_aq", "dfg_li_aq",
           "dfg_liclo4_aq", "dfg_po4_aq", "dfg_hpo4_aq", "dfg_h2po4_aq", "dfg_h3po4_aq")


@pytest.fixture(scope="module")
def table():
    return bd.load_bindings()


def _row(table, bid):
    return next(b for b in table["bindings"] if b["id"] == bid)


def test_header_records_the_body_hash():
    lines = TABLE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = [i for i, ln in enumerate(lines) if ln.startswith("# sha256 of this file with this line removed: ")]
    body = "".join(lines[:idx[0]] + lines[idx[0] + 1:])
    assert re.fullmatch(r"[0-9a-f]{64}", lines[idx[0]].rsplit(": ", 1)[1].strip())
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == lines[idx[0]].rsplit(": ", 1)[1].strip()


# ---- row 1
def test_row1_unresolved_no_cyclic_proxy(table):
    row = _row(table, "b01")
    assert row["status"] == "unresolved" and row["proxy_forbidden"] is True
    for k in ("polyp_al_log_beta1_cyclo_p3", "polyp_al_log_beta1_cyclo_p4", "polyp_al_log_beta1_cyclo_p6",
              "polyp_al_log_beta1_cyclo_p8"):
        r = bd.bind(k, 2.96, table=table)
        assert r.status == bd.UNDETERMINED and r.value is None and "proxy" in r.reason


def test_row1_indicative_input_never_gates():
    r = bd.indicative_beta(1.0e3)
    assert r.status == bd.INDICATIVE and not r.ok and r.notes == {"gates": False}
    assert bd.indicative_beta(-1.0).status == bd.UNDETERMINED


# ---- row 6
def _ion(v, scale="ferrocene", solvent="PC", source="m1"):
    return bd.single_ion_bound(v, scale, solvent, source=source)


def test_row6_relative_quantity_cancels_the_scale():
    base = bd.delta_g_tr_rel(_ion(40000.0), _ion(10000.0), 2)
    shifted = bd.delta_g_tr_rel(_ion(40000.0 + 2 * 7000.0), _ion(10000.0 + 7000.0), 2)  # one common scale shift
    assert base.ok and base.value == pytest.approx(20000.0) and shifted.value == pytest.approx(base.value)


def test_row6_mixed_scale_is_rejected():
    r = bd.delta_g_tr_rel(_ion(40000.0, "ferrocene"), _ion(10000.0, "TATB"), 2)
    assert r.status == bd.UNDETERMINED and r.value is None and "mismatch" in r.reason


def test_row6_mixed_source_and_unnamed_scale_are_rejected():
    assert "source" in bd.delta_g_tr_rel(_ion(1.0, source="a"), _ion(1.0, source="b"), 1).reason
    assert not bd.single_ion_bound(1.0, None, "PC").ok
    assert not bd.single_ion_bound(1.0, "ferrocene", None).ok
    assert not bd.delta_g_tr_rel(bd.salt_bound(1.0, "PC"), bd.salt_bound(1.0, "PC"), 1, form="A").ok


def test_row6_salt_forms_and_mixing_forms():
    ok = bd.delta_g_tr_rel(None, None, 3, form="B", salt=bd.salt_bound(70000.0, "PC", source="s"),
                           li_salt=bd.salt_bound(10000.0, "PC", source="s"))
    assert ok.ok and ok.value == pytest.approx(40000.0)
    assert not bd.delta_g_tr_rel(None, None, 3, form="B", salt=bd.salt_bound(1.0, "PC", source="s"),
                                 li_salt=bd.salt_bound(1.0, "PC", source="t")).ok
    assert not bd.delta_g_tr_rel(None, None, 3, form="B", salt=_ion(1.0), li_salt=bd.salt_bound(1.0, "PC")).ok


def test_row6_binding_row_resolved_but_key_inputs_still_unusable(table):
    assert _row(table, "b06")["status"] == "resolved"
    assert not bd.bind("transfer_free_energy_li_water_pc", 23800.0, table=table).ok
    assert not bd.bind("transfer_free_energy_ca_water_pc", None, table=table).ok


# ---- row 7
@pytest.mark.parametrize("key", AQ_KEYS)
def test_row7_each_aq_key_binds_on_one_scale(table, key):
    r = bd.bind(key, -123456.0, table=table)
    assert r.ok and r.symbol == "G_phase" and r.scale == bd.AQ_SCALE and r.notes["role"] == "e_lb_input"
    assert r.notes["uncertainty"] in ("tabulated", "none")
    assert not bd.bind(key, None, table=table).ok


def test_row7_aq_keys_exist_in_w1_with_their_uncertainty_class(table):
    params = yaml.safe_load((ROOT / "lit" / "params.yaml").read_text(encoding="utf-8"))["params"]
    for key in AQ_KEYS:
        tab = params[key]["prior"]["family"] in ("normal", "uniform")
        assert _row(table, "b07")["keys"][key]["uncertainty"] == ("tabulated" if tab else "none")


def test_row7_e_lb_uses_only_dfg_aq_keys(table):
    terms = [("dfg_li_aq", 1, -293298.4), ("dfg_ca2_aq", -1, -553600.0)]
    g = bd.delta_g_r_aq(terms, table)
    assert g.ok and g.value == pytest.approx(-293298.4 + 553600.0) and g.scale == bd.AQ_SCALE
    e = bd.e_lb(terms, 1.0, table)
    assert e.ok and e.value == pytest.approx(g.value / FARADAY)
    for bad in ("hydration_free_energy_li", "hydration_free_energy_li_tissandier_scale", "dg_hyd_ca_marcus",
                "dfg_caco3_calcite", "window_margin"):
        r = bd.delta_g_r_aq(terms + [(bad, 1, -1.0)], table)
        assert r.status == bd.UNDETERMINED, bad
        assert bd.e_lb(terms + [(bad, 1, -1.0)], 1.0, table).status == bd.UNDETERMINED


def test_row7_e_pc_lower_bound_flag(table):
    e = bd.e_lb([("dfg_li_aq", 1, -293298.4), ("dfg_ca2_aq", -1, -553600.0)], 1.0, table)
    pos = bd.delta_g_tr_rel(_ion(30000.0), _ion(10000.0), 1)
    r = bd.e_pc(e, pos, 1)
    assert r.ok and r.value == pytest.approx(e.value + 20000.0 / FARADAY) and r.notes["lower_bound"] is True
    neg = bd.delta_g_tr_rel(_ion(5000.0), _ion(10000.0), 1)
    assert bd.e_pc(e, neg, 1).notes["lower_bound"] is False
    assert not bd.e_pc(e, bd.delta_g_tr_rel(_ion(1.0, "a"), _ion(1.0, "b"), 1), 1).ok


def test_row7_hydration_keys_only_for_born_comparison(table):
    for k, rec in _row(table, "b07")["keys"].items():
        if k.startswith(("hydration_free_energy", "dg_hyd")):
            assert rec["role"] == "born_comparison_only"
    r = bd.bind("hydration_free_energy_li_tissandier_scale", -537225.6, table=table)
    assert r.ok and r.symbol == "Delta_G_hyd" and r.notes == {"role": "born_comparison_only"}


# ---- row 8
def test_row8_window_margin_never_reaches_a_phosphate_row(table):
    row = _row(table, "b08")
    assert row["carbonate_control_only"] is True and row["status"] == "unresolved"
    for k in row["keys"]:
        r = bd.bind(k, 0.2, table=table)
        assert r.status == bd.UNDETERMINED and r.value is None and "m_K1" in r.reason, k
    for b in table["bindings"]:
        if b["id"] != "b08":
            assert not any(k.startswith("window_margin") for k in b["keys"])
            assert "margin" not in str(b["contract_symbol"])


# ---- row 9
def test_row9_stays_unresolved_until_w1_5(table):
    row = _row(table, "b09")
    assert row["status"] == "unresolved" and "PH-W1.5" in row["reason"]
    for k in row["keys"]:
        assert not bd.bind(k, 1.0, table=table, unit="1").ok
