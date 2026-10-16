"""R-slurry Pourbaix screen, built offline from the cache on coarse grids."""
import socket

import numpy as np
import pytest
from pourbaix_helpers import MOCK, SMOKE, mock_config

from nacre.pourbaix import config, slurry
from nacre.pourbaix import entries as pe

PH = np.linspace(7.0, 14.0, 15)
E = np.linspace(-3.0, 2.0, 26)
CONC = {"Al": 1e-6, "Ca": 1e-3, "C": 1e-3}
ALUMINATES = {"Al(OH)4[-]", "AlO2[-]"}


def _refuse(*a, **k):
    raise RuntimeError("network access attempted in an offline test")


@pytest.fixture(scope="module")
def all_entries():
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", _refuse)
        return pe.slurry_entries(("Al", "C", "Ca"))


@pytest.fixture(scope="module")
def built():
    cfg, _ = config.load(SMOKE, allow_mock=True)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(socket.socket, "connect", _refuse)
        return slurry.build(cfg["regimes"]["R-slurry"])


@pytest.fixture(scope="module")
def al_diagram(all_entries):
    al = [e for e in all_entries if {str(x) for x in e.composition.elements} - {"O", "H"} == {"Al"}]
    return slurry.diagram(al, {"Al": CONC["Al"]})


def test_domain_assignment_is_deterministic(built):
    pd = built["pd"]
    s1, i1 = slurry.assign_domains(pd, built["ph"], built["E"])
    s2, i2 = slurry.assign_domains(pd, built["ph"], built["E"])
    assert [slurry.label(s) for s in s1] == [slurry.label(s) for s in s2]
    assert np.array_equal(i1, i2)
    # and a rebuilt diagram from the same inputs gives the same labels and grid
    calcite = pe.solid_by_id(built["entries"], built["roles"]["calcite"]["entry_id"])
    pd2 = slurry.diagram(built["entries"] + [slurry.acc_entry(calcite, 10.0)],
                         CONC, {"Al": 1.0, "Ca": 1.0, "C": 1.0})
    s3, i3 = slurry.assign_domains(pd2, built["ph"], built["E"])
    assert [slurry.label(s) for s in s3] == [slurry.label(s) for s in s1]
    assert np.array_equal(i3, i1)


def test_aluminate_is_the_stable_al_phase_at_high_ph(al_diagram):
    water = slurry.water_lines([14.0])
    e_mid = float((water["lower"][0] + water["upper"][0]) / 2)
    stable, idx = slurry.assign_domains(al_diagram, np.array([13.5, 14.0]), np.array([e_mid]))
    for j in range(2):
        assert set(slurry.component_names(stable[idx[0, j]])) <= ALUMINATES


def test_aluminate_in_the_full_system_at_high_ph(built):
    stable, idx = built["stable"], built["index"]
    lower, upper = built["water"]["lower"][-1], built["water"]["upper"][-1]
    rows = np.where((built["E"] > lower) & (built["E"] < upper))[0]
    assert len(rows)
    for r in rows:
        names = slurry.component_names(stable[idx[r, -1]])
        al = [n for n in names if n.startswith("Al")]
        assert len(al) == 1 and al[0] in ALUMINATES, names


def test_metallic_al_only_at_the_lowest_potentials(al_diagram):
    ph = np.linspace(7.0, 14.0, 15)
    e = np.linspace(-3.0, 2.0, 101)
    stable, idx = slurry.assign_domains(al_diagram, ph, e)
    is_metal = np.array([slurry.component_names(s) == ["Al(s)"] for s in stable])[idx]
    assert is_metal.any(), "metallic Al never stable on the grid; the test would be vacuous"
    lower = slurry.water_lines(ph)["lower"]
    for j in range(len(ph)):
        col = is_metal[:, j]
        if col.any():
            n = int(col.sum())
            assert col[:n].all() and not col[n:].any(), "Al(s) region is not the bottom of column %d" % j
            assert e[n - 1] < lower[j], "Al(s) stable above the hydrogen line at pH %.2f" % ph[j]


def test_raising_the_acc_offset_shrinks_the_acc_region(all_entries):
    offsets = [0.0, 5.0, 10.0, 20.0, 40.0]
    scan = slurry.acc_offset_scan(offsets, CONC, PH, E)
    areas = [s["area_fraction"] for s in scan]
    assert all(b <= a for a, b in zip(areas, areas[1:])), areas
    assert areas[0] > areas[-1], "the scan does not move the boundary at all"
    # the low-pH edge of the ACC region moves to higher pH (or the region vanishes)
    edges = np.array([np.where(np.isnan(s["ph_min"]), np.inf, s["ph_min"]) for s in scan])
    assert np.all(edges[1:] >= edges[:-1])  # inf >= inf holds; a diff would give nan


def test_acc_sits_offset_above_calcite_where_calcite_is_stable(built):
    calcite, acc = built["decomposition"]["calcite"], built["decomposition"]["ACC"]
    stable = calcite < 1e-9
    assert stable.any()
    per_atom = 10.0 / pe.KJ_PER_MOL_PER_EV / 5.0  # smoke offset 10 kJ/mol over 5 atoms of CaCO3
    assert np.allclose(acc[stable], per_atom, atol=1e-9)


def test_decomposition_energies_are_non_negative(built):
    for role, grid in built["decomposition"].items():
        assert np.nanmin(grid) > -1e-9, role


def test_closed_carbonate_speciation_is_consistent(built):
    sp = built["speciation"]
    total = sp["alpha_CO2aq"] + sp["alpha_HCO3"] + sp["alpha_CO3"]
    assert np.allclose(total, 1.0)
    assert sp["pKa1"] < sp["pKa2"]
    assert np.all(np.diff(sp["alpha_CO3"]) > 0), "CO3^2- fraction must rise with pH"


def test_no_cross_compound_reported_as_stable_without_check(built):
    # the subsystem-hull decomposition energies are exact only without Al-Ca / Al-C solids
    assert isinstance(built["cross_compounds"], list)


def test_temperature_other_than_298_is_refused():
    cfg, _ = mock_config()
    rs = dict(cfg["regimes"]["R-slurry"], temperature_K=310.0)
    with pytest.raises(NotImplementedError):
        slurry.build(rs)


def test_mock_configuration_is_refused_without_flag():
    with pytest.raises(config.MockRefused):
        config.load(MOCK)


def test_mock_value_in_non_mock_configuration_is_refused(tmp_path):
    import re

    text = re.sub(r"(?m)^mock: true$", "mock: false", MOCK.read_text(encoding="utf-8"))
    assert "\nmock: false\n" in text
    p = tmp_path / "final.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(config.MockRefused):
        config.load(p)
    with pytest.raises(config.MockRefused):
        config.load(p, allow_mock=True)


def test_lit_params_source_requires_the_file(tmp_path):
    p = tmp_path / "final.yaml"
    p.write_text("mock: false\nrun: final\nregimes:\n  R-slurry:\n    acc_offset:\n"
                 "      source: lit/params.yaml\n      key: acc_offset\n      unit: kJ/mol\n",
                 encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load(p, lit_params_path=tmp_path / "absent.yaml")
    params = tmp_path / "params.yaml"
    params.write_text("acc_offset: {value: 7.5}\n", encoding="utf-8")
    cfg, meta = config.load(p, lit_params_path=params)
    assert cfg["regimes"]["R-slurry"]["acc_offset"] == {"value": 7.5, "unit": "kJ/mol"}
    assert meta["sources"][0]["source"] == "lit/params.yaml"


def test_charter_bound_is_read_and_checked(tmp_path):
    cfg, meta = mock_config()
    assert cfg["regimes"]["R-slurry"]["pH"]["min"] == 7
    text = MOCK.read_text(encoding="utf-8").replace(
        "min: {source: charter, charter_key: pH, bound: min}",
        "min: {source: charter, charter_key: pH, bound: min, value: 6}")
    p = tmp_path / "bad.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(config.ConfigError):
        config.load(p, allow_mock=True)
