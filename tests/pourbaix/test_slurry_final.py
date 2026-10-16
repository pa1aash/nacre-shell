"""Final R-slurry construction (P0-W5.2): C(IV) constraint, exact speciation, F6, controls and
the committed schema v2 documents (offline)."""
import json

import numpy as np
import pytest
from pourbaix_helpers import offline  # noqa: F401

from nacre.pourbaix import final as F
from nacre.pourbaix import inputs, provenance
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

PARAMS_SHA = "680a44b2efdb94694b25f5317ddc3d73db2f117c"
FINAL = POURBAIX_RESULTS / "final"


@pytest.fixture(scope="module")
def S():
    return F.setup()


@pytest.fixture(scope="module")
def consts(S):
    return F.implied_constants(S["all"])


@pytest.fixture(scope="module")
def params():
    return inputs.Params(inputs.load_snapshot(PARAMS_SHA, check_git=False))


def test_carbon_oxidation_state_filter(offline, S):
    names = {e.name: e for e in S["all"] if e.phase_type == "Ion"}
    assert F.carbon_oxidation_state(names["CO3[2-]"]) == pytest.approx(4)
    assert F.carbon_oxidation_state(names["HCO3[-]"]) == pytest.approx(4)
    assert F.carbon_oxidation_state(names["CH4(aq)"]) == pytest.approx(-4)
    assert not F.is_c4_or_c_free(names["HCOO[-]"])
    assert F.is_c4_or_c_free(names["Ca[2+]"])
    pool = F.subsystem(S["solids"], ("Ca", "C"))
    assert all(F.is_c4_or_c_free(e) for e in pool)
    assert "C(s)" not in {e.name for e in pool}


def test_implied_acid_constants_close_to_sourced(offline, consts, params):
    assert consts["pKa1"] == pytest.approx(params.value("pk1_carbonic"), abs=0.1)
    assert consts["pKa2"] == pytest.approx(params.value("pk2_carbonic"), abs=0.1)


def test_alpha2_limits():
    a = F.alpha2(np.array([2.0, 14.0]), 6.3, 10.3)
    assert a[0] < 1e-9 and a[1] > 0.99


def test_exact_speciation_moves_the_boundary_by_ln_alpha(offline, S, consts):
    # find a_Ca where calcite just dissolves at pH 11 under the proxy's own constants:
    # Omega_proxy = a_Ca a2 C_T / Ksp_proxy = 1
    ph, c_t = 11.0, 1e-2
    a2 = float(F.alpha2(ph, consts["pKa1"], consts["pKa2"]))
    a_star = 10 ** consts["log10_ksp_calcite"] / (a2 * c_t)
    E = np.array([-1.0])
    above = F.ca_c_exact(S, a_star * 10, c_t, np.array([ph]), E, 0.0, consts)
    below = F.ca_c_exact(S, a_star / 10, c_t, np.array([ph]), E, 0.0, consts)
    assert above.max() == pytest.approx(0.0, abs=1e-9)
    # one decade below saturation: kT ln 10 per formula unit, 5 atoms
    assert below.max() == pytest.approx(consts["nernst_prefactor_eV"] / 5, rel=1e-6)


def test_acc_is_calcite_plus_offset_per_atom_where_calcite_is_stable(offline, S, consts):
    ph, E = np.array([12.0]), np.array([-1.0, -0.6])
    off = 0.1
    cal = F.ca_c_exact(S, 1e-2, 1e-2, ph, E, off, consts)
    acc = F.ca_c_exact(S, 1e-2, 1e-2, ph, E, off, consts, target="ACC")
    assert np.allclose(cal, 0.0) and np.allclose(acc, off / 5)


def test_f6_acc_edge_test_equals_the_calcite_test(params):
    from nacre.pourbaix import final_run as R

    e_cal = R.edge_ev_per_atom(params, "formation_energy_mae")
    for off in (0.05, 0.12, 0.2):
        e_acc = R.edge_ev_per_atom(params, "formation_energy_mae", off)
        for d_cal in (0.0, 0.03, 0.06):
            assert (d_cal + off / 5 <= e_acc) == (d_cal <= e_cal)


def test_native_oxide_attacked_at_alkaline_end(offline, S):
    dec, labels, idx = F.al_baseline(S, 1e-6, np.array([13.0]), np.array([-1.0]))
    assert dec["corundum"].min() > 0 and labels[int(idx[0, 0])] == "Al(OH)4[-]"


def _summary():
    path = FINAL / "slurry_summary.json"
    if not path.is_file():
        pytest.skip("final R-slurry not generated yet")
    return json.loads(path.read_text(encoding="utf-8"))


def test_summary_exposes_design_axes_and_params_sha():
    s = _summary()
    assert s["provenance"]["params_sha"] == PARAMS_SHA
    assert s["design_axes"]["a_Ca"]["status"] == "provisional"
    assert len(s["points"]) == len(s["design_axes"]["a_Ca"]["grid"]) * len(s["design_axes"]["C_T"])
    assert s["F7"]["a_w_per_state"]["drying"]["a_w"] is None
    assert "derivation_body.tex section 7" in s["enriched_state"]


def test_documents_conform_to_schema_v2_and_enriched_equals_bulk():
    s = _summary()
    doc = json.loads((REPO / s["points"][0]["document"]).read_text(encoding="utf-8"))
    if provenance.git_object(*provenance.W4_SCHEMA_V2) is None:
        pytest.skip("schema v2 commit not in the local object store")
    assert provenance.validate_against(provenance.W4_SCHEMA_V2, doc)["valid"]
    st = doc["stability"]["R-slurry"]["states"]
    b, e = st["bulk"], st["enriched"]
    assert e["decomposition_energy"] == b["decomposition_energy"] and e["domains"] == b["domains"]
    assert "section 7" in e["conditions"]["state_note"]


def test_control_is_recorded_with_its_consequence():
    c = _summary()["falsifiability_control"]
    assert c["native_oxide_alkaline"]["fails_where_it_must"] is True
    assert c["calcite_supersaturated"]["proxy_reports_stability"] is True
    # the calcite control's outcome is reported, not assumed
    assert isinstance(c["control_fails_where_it_must"], bool)
    assert c["calcite_undersaturated"]["experimental_log10_omega"] < 0
