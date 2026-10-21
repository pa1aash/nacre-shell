"""W1-key to contract-symbol bindings (configs/preprint/symbol_bindings.yaml, nacre.physics.bindings)."""
import hashlib
import math
import re
from pathlib import Path

import pytest
import yaml

from nacre.physics import bindings as bd
from nacre.physics.constants import GAS_CONSTANT

ROOT = Path(__file__).resolve().parents[2]
TABLE_PATH = ROOT / "configs" / "preprint" / "symbol_bindings.yaml"
PARAMS = ROOT / "lit" / "params.yaml"
CONTRACT = ROOT / "theory" / "contract.yaml"
SYMBOLS = ROOT / "theory" / "symbols.yaml"
FAMILY = re.compile(r"^(polyp_al_log_beta1|polyp_log10_ksp|coacervate_gamma|glass_crystal_correction|hydrolysis_polyp_k|"
                    r"transfer_free_energy|hydration_|dg_hyd|window_margin|polyp_ads|polyp_chain|matrix_chitosan_polyp)")
RLN2 = GAS_CONSTANT * math.log(2.0)


@pytest.fixture(scope="module")
def table():
    return bd.load_bindings()


@pytest.fixture(scope="module")
def params():
    return yaml.safe_load(PARAMS.read_text(encoding="utf-8"))["params"]


def _keys(table):
    return {k: (b, r) for b in table["bindings"] for k, r in b["keys"].items()}


def test_eleven_bindings_each_complete(table):
    assert [b["id"] for b in table["bindings"]] == ["b%02d" % i for i in range(1, 12)]
    for b in table["bindings"]:
        for field in ("contract_symbol", "w1_symbol", "w1_unit", "conversion", "status", "default", "keys"):
            assert field in b, (b["id"], field)
        assert b["conversion"]["name"] and "formula" in b["conversion"]
        assert b["status"] in ("resolved", "unresolved")
        assert b["default"]["status"] == "undetermined"
        if b["status"] == "unresolved":
            assert b["reason"]


def test_header_hash_matches_body():
    lines = TABLE_PATH.read_text(encoding="utf-8").splitlines(keepends=True)
    idx = [i for i, ln in enumerate(lines) if ln.startswith("# sha256 of this file with this line removed: ")]
    assert len(idx) == 1
    recorded = lines[idx[0]].rsplit(": ", 1)[1].strip()
    body = "".join(lines[:idx[0]] + lines[idx[0] + 1:])
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == recorded


def test_every_family_key_has_a_binding_or_a_stated_exclusion(table, params):
    covered = set(_keys(table)) | set(table["not_bound"])
    missing = sorted(k for k in params if FAMILY.match(k) and k not in covered)
    assert missing == []


def test_bound_keys_exist_in_params_except_the_absent_adsorption_keys(table, params):
    absent = {k for k, (b, _r) in _keys(table).items() if k not in params}
    assert absent == {"polyp_ads_alumina_gamma_max", "polyp_ads_alumina_k_langmuir",
                      "polyp_ads_alumina_layer_thickness"}


def _contract_symbols():
    if not (CONTRACT.exists() and SYMBOLS.exists()):
        pytest.skip("theory/contract.yaml is not in the working tree")
    doc = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    if doc.get("version") != 6:
        pytest.skip("contract version %s, bindings target 6" % doc.get("version"))
    used = set()
    for f in doc["functions"]:
        used.update(re.findall(r"[A-Za-z_][A-Za-z_0-9]*", str(f.get("expression", ""))))
        used.update(f.get("inputs") or [])
    return doc, used


def test_every_contract_symbol_with_a_w1_key_has_a_binding_with_a_conversion(table):
    doc, used = _contract_symbols()
    symbols = {e["id"] for e in yaml.safe_load(SYMBOLS.read_text(encoding="utf-8")).get("symbols", [])}
    wanted = {"beta_AlPP", "K_sp_AlPP", "gamma_nl_c", "Delta_G_gc", "k_hyd", "Delta_G_tr_rel", "Delta_G_hyd",
              "Gamma_P", "K_P", "delta_P"}
    bound_symbols = set()
    for b in table["bindings"]:
        if b["contract_symbol"] in wanted:
            bound_symbols.add(b["contract_symbol"])
        for rec in b["keys"].values():
            if rec.get("symbol") in wanted:
                bound_symbols.add(rec["symbol"])
    assert bound_symbols == wanted
    assert wanted <= symbols
    for s in wanted - {"Delta_G_hyd"}:
        assert s in used, s
    for b in table["bindings"]:
        assert b["conversion"]["name"] in {"log10_to_linear", "identity", "enthalpy_plus_entropy_bound",
                                           "single_ion_transfer", "hydration_by_scale", "ads_unit", "slot"}


def test_slots_are_not_in_any_contract_formula(table):
    doc, used = _contract_symbols()
    for sym in ("n_chain", "K_complex"):
        assert sym not in used
    for b in table["bindings"]:
        if b["id"] in ("b10", "b11"):
            assert b["conversion"]["name"] == "slot" and b["contract_symbol"] == "none"
            for k in b["keys"]:
                r = bd.bind(k, 25.0, table=table)
                assert not r.ok and "slot" in r.reason


def test_every_unresolved_key_and_every_gap_is_undetermined(table, params):
    for k, (b, rec) in _keys(table).items():
        value = params.get(k, {}).get("value")
        if rec["status"] == "unresolved":
            r = bd.bind(k, 1.0, table=table, unit="1")
            assert r.status == bd.UNDETERMINED and r.value is None and r.reason.startswith("unresolved"), k
        elif value is None:
            assert bd.bind(k, None, table=table).status == bd.UNDETERMINED, k


def test_unknown_key_is_undetermined(table):
    assert bd.bind("no_such_key", 1.0, table=table).status == bd.UNDETERMINED


# ---- b01, b02: log10 to linear
def test_log10_to_linear_base_and_inverse():
    assert bd.log10_to_beta(0.0) == 1.0
    assert bd.log10_to_beta(2.0) == pytest.approx(100.0)
    assert bd.log10_to_beta(-3.5) == pytest.approx(10 ** -3.5)
    assert bd.beta_to_log10(bd.log10_to_beta(4.14)) == pytest.approx(4.14)
    with pytest.raises(ValueError):
        bd.beta_to_log10(0.0)


def test_beta_binding_cyclic_keys_are_unresolved_linear_is_resolved(table):
    assert not bd.bind("polyp_al_log_beta1_cyclo_p3", 2.96, table=table).ok
    r = bd.bind("polyp_al_log_beta1_linear", 3.0, table=table)
    assert r.ok and r.symbol == "beta_AlPP" and r.value == pytest.approx(1000.0) and r.unit == "1"
    assert bd.bind("polyp_al_log_beta1_linear", None, table=table).status == bd.UNDETERMINED


def test_ksp_binding(table):
    r = bd.bind("polyp_log10_ksp_al", -12.0, table=table)
    assert r.ok and r.symbol == "K_sp_AlPP" and r.value == pytest.approx(1e-12)
    assert bd.bind("polyp_log10_ksp_al", None, table=table).status == bd.UNDETERMINED


# ---- b03, b05: identities
def test_identity_bindings(table):
    r = bd.bind("coacervate_gamma_analog", 0.000311, table=table)
    assert r.ok and r.symbol == "gamma_nl_c" and r.unit == "J m^-2" and r.value == 0.000311
    assert r.notes == {"role": "analog"}
    assert not bd.bind("coacervate_gamma_analog", -1.0, table=table).ok
    k = bd.bind("hydrolysis_polyp_k_ph6", 4.83333333333e-08, table=table)
    assert k.ok and k.symbol == "k_hyd" and k.unit == "s^-1" and k.value == 4.83333333333e-08
    assert not bd.bind("hydrolysis_polyp_k_ph6", 0.0, table=table).ok
    assert not bd.bind("hydrolysis_polyp_k_ph6", float("nan"), table=table).ok


# ---- b04: enthalpy to free energy only through the entropy bound
def test_delta_g_gc_needs_the_entropy_input(table):
    r = bd.bind("glass_crystal_correction_cameta_calphad", 18872.0, table=table)
    assert r.status == bd.UNDETERMINED and "s_resid" in r.reason


def test_delta_g_gc_values_and_ends(table):
    h = 18872.0
    lo, hi = bd.delta_g_gc_ends(h, 2)
    assert lo == pytest.approx(h)
    assert hi == pytest.approx(h - 298.15 * 2 * RLN2)
    assert hi < lo
    r = bd.bind("glass_crystal_correction_cameta_calphad", h, table=table, s_resid=2 * RLN2)
    assert r.ok and r.symbol == "Delta_G_gc" and r.value == pytest.approx(hi)
    r0 = bd.bind("glass_crystal_correction_lipo3", 4393.2, table=table, s_resid=0.0, temperature=300.0)
    assert r0.ok and r0.value == pytest.approx(4393.2)


def test_delta_g_gc_bound_and_sign(table):
    with pytest.raises(ValueError):
        bd.delta_g_gc(1000.0, -0.1, 1)
    with pytest.raises(ValueError):
        bd.delta_g_gc(1000.0, RLN2 * 1.01, 1)
    # NaPO3 at the full entropy end stays >= 0; LiPO3 at 1000 J mol^-1 goes negative (T R ln 2 = 1.7 kJ) and is refused
    assert bd.bind("glass_crystal_correction_napo3", 13388.8, table=table, s_resid=RLN2).ok
    neg = bd.bind("glass_crystal_correction_lipo3", 1000.0, table=table, s_resid=RLN2)
    assert neg.status == bd.UNDETERMINED and "Delta_G_gc" in neg.reason
    out = bd.bind("glass_crystal_correction_cameta_calphad", 18872.0, table=table, s_resid=5 * RLN2)
    assert out.status == bd.UNDETERMINED


# ---- b06: transfer, forms A and B
def _ion(scale, solvent="PC", v=1000.0):
    return bd.Bound(bd.OK, "DG_tr_single_ion", v, "J mol^-1", scale=scale, form="A", solvent=solvent)


def test_form_a_same_scale():
    r = bd.delta_g_tr_rel(_ion("ferrocene", v=40000.0), _ion("ferrocene", v=10000.0), 2)
    assert r.ok and r.value == pytest.approx(20000.0) and r.form == "A" and r.scale == "ferrocene"


def test_form_a_mismatch_unnamed_and_solvent_are_undetermined():
    assert "mismatch" in bd.delta_g_tr_rel(_ion("ferrocene"), _ion("TATB"), 2).reason
    assert "not named" in bd.delta_g_tr_rel(_ion(None), _ion(None), 2).reason
    assert "solvent" in bd.delta_g_tr_rel(_ion("ferrocene", "PC"), _ion("ferrocene", "DMC"), 2).reason
    assert not bd.delta_g_tr_rel(_ion("ferrocene"), bd.bind("transfer_free_energy_li_water_pc", 23800.0), 2).ok


def test_form_b_salt_form_and_refusal_of_single_ions():
    ok = bd.delta_g_tr_rel(None, None, 2, form="B", salt=bd.salt_bound(60000.0, "PC"), li_salt=bd.salt_bound(10000.0, "PC"))
    assert ok.ok and ok.value == pytest.approx(40000.0) and ok.form == "B"
    bad = bd.delta_g_tr_rel(None, None, 2, form="B", salt=_ion("ferrocene"), li_salt=bd.salt_bound(1.0, "PC"))
    assert not bad.ok
    assert not bd.delta_g_tr_rel(None, None, 2, form="C").ok


def test_current_transfer_keys(table):
    li = bd.bind("transfer_free_energy_li_water_pc", 23800.0, table=table)
    assert li.status == bd.UNDETERMINED and "scale" in li.reason
    clo4 = bd.bind("transfer_free_energy_clo4_water_pc", -7700.0, table=table)
    assert clo4.ok and clo4.scale == "ferrocene" and clo4.solvent == "PC"
    for k in ("transfer_free_energy_ca_water_pc", "transfer_free_energy_al_water_pc"):
        assert not bd.bind(k, None, table=table).ok


# ---- b07: hydration scale per key
@pytest.mark.parametrize("key,value,scale", [
    ("hydration_free_energy_li", -475000.0, "marcus1991"),
    ("hydration_free_energy_ca", -1505000.0, "marcus1991"),
    ("hydration_free_energy_al_marcus", -4524996.0, "marcus1991"),
    ("hydration_free_energy_al_tissandier_scale", -4670599.2, "tissandier"),
    ("hydration_free_energy_li_tissandier_scale", -537225.6, "tissandier"),
    ("dg_hyd_ca_tissandier", -1602053.6, "tissandier"),
])
def test_hydration_scale_is_carried(table, key, value, scale):
    r = bd.bind(key, value, table=table)
    assert r.ok and r.scale == scale and r.symbol == "Delta_G_hyd" and r.unit == "J mol^-1"


def test_hydration_conventional_positive_and_unnamed_are_undetermined(table):
    conv = bd.bind("hydration_free_energy_li_conventional", 575300.0, table=table)
    assert conv.status == bd.UNDETERMINED and "negative" in conv.reason
    assert bd.bind("hydration_free_energy_clo4", -400000.0, table=table).status == bd.UNDETERMINED


def test_hydration_scales_are_never_mixed(table):
    a = bd.bind("hydration_free_energy_li", -475000.0, table=table)
    b = bd.bind("hydration_free_energy_ca", -1505000.0, table=table)
    c = bd.bind("hydration_free_energy_li_tissandier_scale", -537225.6, table=table)
    assert bd.require_one_hydration_scale(a, b)
    assert not bd.require_one_hydration_scale(a, c)
    assert not bd.require_one_hydration_scale(a, bd.bind("hydration_free_energy_clo4", -1.0, table=table))
    assert not bd.require_one_hydration_scale()


# ---- b09: adsorption units
def test_gamma_p_units():
    assert bd.gamma_p_to_mol_m2(2.0, "umol m^-2") == pytest.approx(2e-6)
    assert bd.gamma_p_to_mol_m2(2.0, "mol m^-2") == 2.0
    assert bd.gamma_p_to_mol_m2(7.897, "mg m^-2", molar_mass_g_mol=78.97) == pytest.approx(1e-4)
    with pytest.raises(ValueError):
        bd.gamma_p_to_mol_m2(1.0, "mg m^-2")
    with pytest.raises(ValueError):
        bd.gamma_p_to_mol_m2(1.0, "mg g^-1")


def test_k_p_and_delta_p_units():
    assert bd.k_p_activity_form(30.0, "1") == 30.0
    with pytest.raises(ValueError):
        bd.k_p_activity_form(30.0, "L mol^-1")
    assert bd.delta_p_to_m(2.0, "nm") == pytest.approx(2e-9)
    assert bd.delta_p_to_m(5.0, "angstrom") == pytest.approx(5e-10)
    with pytest.raises(ValueError):
        bd.delta_p_to_m(1.0, "mol m^-2")


def test_adsorption_keys_are_unresolved_until_a_w1_key_exists(table):
    for k in ("polyp_ads_alumina_gamma_max", "polyp_ads_alumina_k_langmuir", "polyp_ads_alumina_layer_thickness"):
        r = bd.bind(k, 1.0, table=table, unit="1")
        assert r.status == bd.UNDETERMINED and "absent" in r.reason
