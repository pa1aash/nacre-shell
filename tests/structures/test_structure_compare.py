"""Tolerance comparison of a fresh build with a committed structure (nacre.structures.compare)."""
from __future__ import annotations

import numpy as np
import pytest

from nacre.structures import compare, ion, slab


@pytest.fixture(scope="module")
def periodic():
    return slab.build({"nx": 1, "ny": 1, "n_o_layers": 2, "vacuum": 6.0}, seed=0)


@pytest.fixture(scope="module")
def molecule():
    return ion.build({"cn": 6, "r_ca_o": 2.4}, seed=3)


def test_identical_structures_agree(molecule, periodic):
    assert compare.compare(molecule, molecule.copy()) == []
    assert compare.compare(periodic, periodic.copy()) == []


def test_tolerance_is_a_hundredth_of_an_angstrom():
    assert compare.POSITION_TOL == 1e-2


def test_small_displacement_passes_and_large_fails(molecule):
    b = molecule.copy()
    b.positions[4] += [0.6e-2, 0.0, 0.0]
    assert compare.compare(molecule, b) == []
    b.positions[4] += [0.6e-2, 0.0, 0.0]
    (msg,) = compare.compare(molecule, b)
    assert "max displacement" in msg and "atom 4" in msg


def test_periodic_wrap_is_not_a_displacement(periodic):
    b = periodic.copy()
    b.positions[0] += np.asarray(periodic.cell)[0]
    assert compare.compare(periodic, b) == []


def test_order_species_and_count_are_exact(molecule):
    swapped = molecule[[0, 2, 1] + list(range(3, len(molecule)))]
    assert any("order" in m for m in compare.compare(molecule, swapped))
    assert any("count" in m for m in compare.compare(molecule, molecule[:-1]))


def test_metadata_is_exact(molecule):
    b = molecule.copy()
    b.info["seed"] = 4
    assert any("metadata seed" in m for m in compare.compare(molecule, b))
    c = molecule.copy()
    del c.info["label"]
    assert any("label" in m for m in compare.compare(molecule, c))


def test_geometry_derived_floats_use_relative_tolerance(molecule):
    a, b = molecule.copy(), molecule.copy()
    a.info["ff_energy_kcal_mol"], b.info["ff_energy_kcal_mol"] = 100.0, 100.0 + 1e-4
    assert compare.compare(a, b) == []
    b.info["ff_energy_kcal_mol"] = 101.0
    assert any("ff_energy" in m for m in compare.compare(a, b))


def test_component_array_is_exact(molecule):
    b = molecule.copy()
    comp = b.arrays["component"].copy()
    comp[1] = "ion"
    b.arrays["component"] = comp
    assert any("component" in m for m in compare.compare(molecule, b))


def test_cell_and_pbc(periodic):
    b = periodic.copy()
    b.set_cell(np.asarray(periodic.cell) * [[1.01], [1.0], [1.0]], scale_atoms=False)
    assert any("cell" in m for m in compare.compare(periodic, b))
    c = periodic.copy()
    c.pbc = (True, True, True)
    assert any("pbc" in m for m in compare.compare(periodic, c))
