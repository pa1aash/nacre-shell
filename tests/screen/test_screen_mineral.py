"""The mineral object and the generalised chain (PH-W4.1): carbonate unchanged, contract v5 for the rest."""
import numpy as np
import pytest

from nacre.physics import supersaturation as sat
from nacre.screen import chain
from nacre.screen.mineral import CALCITE, Mineral, MineralError, from_config, registry
from nacre.screen.run import load_config

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _hap(**kw):
    base = dict(name="hap", formula_unit="Ca5(PO4)3OH", nu_ca=5, nu_x=3, nu_y=1, ksp_key="k", vm_key="v", framing="apatite",
                x_symbol="a_PO4", y_symbol="a_OH", speciation="phosphate")
    base.update(kw)
    return Mineral(**base)


def test_defaults_of_the_two_new_fields():
    m = _hap()
    assert m.phase_state == "crystalline" and m.chain_length_n is None
    assert m.nu == 9


@pytest.mark.parametrize("state", ["crystalline", "amorphous", "liquid_precursor"])
def test_phase_states_accepted(state):
    assert _hap(phase_state=state).phase_state == state


@pytest.mark.parametrize("kw", [dict(phase_state="glassy"), dict(chain_length_n=0), dict(chain_length_n=2.5),
                                dict(chain_length_n=True), dict(nu_x=0), dict(n_hyd=-1), dict(speciation="silicate")])
def test_inconsistent_mineral_refused(kw):
    with pytest.raises(MineralError):
        _hap(**kw)


def test_chain_length_is_an_integer_field():
    assert _hap(chain_length_n=12, speciation=None).chain_length_n == 12


def test_calcite_is_the_carbonate_form_and_apatite_is_not():
    assert CALCITE.is_carbonate_form and CALCITE.nu == 2
    assert not _hap().is_carbonate_form
    assert chain.nuc_base(CALCITE) == chain.NUC_BASE


def test_registry_reads_screen_yaml():
    cfg = load_config(ROOT)
    ms = registry(cfg)
    assert {"calcite", "hap", "acp", "capoly"} <= set(ms)
    assert ms["hap"].nu == 9 and ms["acp"].phase_state == "amorphous" and ms["acp"].n_hyd_key == "acp_hydration_n"
    assert ms["hap"].k1_phase == ms["acp"].k1_phase == "HAp"
    assert ms["capoly"].chain_length_n is not None and ms["capoly"].speciation is None


def test_from_config_requires_keys():
    with pytest.raises(MineralError):
        from_config("x", {"formula_unit": "X", "stoichiometry": {"nu_ca": 1, "nu_x": 1}, "keys": {"ksp": "k"}})


def _x(n=64):
    rng = np.random.default_rng(3)
    return {"a_Ca": rng.uniform(1e-4, 1e-2, n), "a_CO3": rng.uniform(1e-4, 1e-2, n), "K_sp": 10 ** rng.uniform(-8, -6, n),
            "gamma_sl": rng.uniform(0.5, 2, n), "gamma_sn0": rng.uniform(0, 1, n), "Delta_gamma_w": np.zeros(n),
            "gamma_nl": rng.uniform(0.5, 1, n), "V_m": np.full(n, 1e-6), "T": np.full(n, 298.15)}


def test_default_chain_equals_explicit_calcite():
    x = _x()
    a, _ = chain.evaluate(x)
    b, _ = chain.evaluate(x, mineral=CALCITE)
    for q in a["nucleate"]:
        assert np.array_equal(a["nucleate"][q], b["nucleate"][q], equal_nan=True)


def test_calcite_in_stoichiometric_form_matches_the_legacy_path():
    """The same nucleus written as a generic mineral (not the carbonate form) gives Omega and barriers to rounding."""
    generic = Mineral("calcite_generic", "CaCO3", 1, 1, "k", "v", "calcite", x_symbol="a_X")
    x = _x()
    x["a_X"] = x["a_CO3"]
    legacy, _ = chain.evaluate(x)
    got, _ = chain.evaluate(x, mineral=generic)
    for q in ("Omega_bulk", "barrier_hom_bulk_kT", "barrier_het_template_kT", "r_star", "cos_theta"):
        assert np.allclose(legacy["nucleate"][q], got["nucleate"][q], rtol=1e-12, equal_nan=True), q


def test_nucleate_for_apatite_uses_nu_nine():
    m = _hap()
    n = 32
    rng = np.random.default_rng(1)
    x = {"a_Ca": rng.uniform(1e-3, 1e-2, n), "a_PO4": rng.uniform(1e-6, 1e-5, n), "a_OH": rng.uniform(1e-4, 1e-2, n),
         "K_sp": np.full(n, 1e-50), "gamma_sl": np.full(n, 1.0), "gamma_sn0": np.full(n, 0.4), "Delta_gamma_w": np.zeros(n),
         "gamma_nl": np.full(n, 0.8), "V_m": np.full(n, 1e-6), "T": np.full(n, 298.15)}
    out, _ = chain.evaluate(x, mineral=m)
    expect = sat.saturation_ratio_mineral(x["a_Ca"], x["a_PO4"], x["a_OH"], 5, 3, 1, 1.0, 0, x["K_sp"])
    assert np.allclose(out["nucleate"]["Omega_bulk"], expect, rtol=1e-12)
    assert chain.evaluable_links(x, m) == ["nucleate"]


def test_phosphate_speciation_feeds_the_chain():
    m = _hap()
    n = 16
    x = {"pH": np.full(n, 11.0), "P_T": np.full(n, 2.0), "Ca_T": np.full(n, 20.0), "I_ionic": np.full(n, 0.05),
         "rho_water": np.full(n, 997.0), "pK1_phosphoric": np.full(n, 2.15), "pK2_phosphoric": np.full(n, 7.2),
         "pK3_phosphoric": np.full(n, 12.35), "K_CaHPO4_aq": np.full(n, 500.0), "K_CaH2PO4": np.full(n, 20.0),
         "K_CaPO4": np.full(n, 1e6), "K_CaOH": np.full(n, 2.5e-13), "a_w": np.full(n, 1.0), "A_DH": np.full(n, 0.509),
         "b_D": np.full(n, 0.3), "I_val": np.full(n, 0.5), "pKw": np.full(n, 14.0), "K_sp": np.full(n, 1e-30)}
    assert "speciation" in chain.evaluable_links(x, m)
    out, masses = chain.evaluate(x, mineral=m)
    s = out["speciation"]
    assert set(("a_Ca", "a_PO4", "a_HPO4", "a_OH", "Omega_bulk")) <= set(s)
    assert np.allclose(s["a_OH"], 10 ** (11.0 - 14.0))
    assert np.all(np.isfinite(s["Omega_bulk"]))


def test_ionic_strength_above_validity_is_refused_for_phosphate():
    m = _hap()
    n = 4
    x = {k: np.full(n, v) for k, v in dict(pH=11.0, P_T=2.0, Ca_T=20.0, I_ionic=0.9, rho_water=997.0, pK1_phosphoric=2.15,
         pK2_phosphoric=7.2, pK3_phosphoric=12.35, K_CaHPO4_aq=500.0, K_CaH2PO4=20.0, K_CaPO4=1e6, K_CaOH=2.5e-13,
         a_w=1.0, A_DH=0.509, b_D=0.3, I_val=0.5, pKw=14.0, K_sp=1e-30).items()}
    out, masses = chain.evaluate(x, mineral=m)
    assert np.all(np.isnan(out["speciation"]["a_PO4"]))
    assert masses["speciation"]["activity_model"].n_refused == n
