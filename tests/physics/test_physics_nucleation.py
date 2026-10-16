"""Property tests of the CNT barriers and the driving force (synthetic inputs only)."""
import math

import numpy as np
import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from nacre.physics.constants import AVOGADRO, BOLTZMANN, GAS_CONSTANT
from nacre.physics.nucleation import (
    barrier_in_kT,
    critical_radius,
    heterogeneous_barrier,
    homogeneous_barrier,
    homogeneous_barrier_from_saturation,
)
from nacre.physics.supersaturation import driving_force_molar, driving_force_per_formula_unit
from nacre.physics.wetting import shape_factor

# Synthetic, dimensionally sensible ranges; they test mathematics, not materials.
gammas = st.floats(min_value=1e-3, max_value=10.0)
volumes = st.floats(min_value=1e-7, max_value=1e-3)
omegas = st.floats(min_value=1.0 + 1e-6, max_value=1e12)
temps = st.floats(min_value=1.0, max_value=5000.0)
driving = st.floats(min_value=1e-3, max_value=1e7)
factors = st.floats(min_value=1e-3, max_value=1e3)
angles = st.floats(min_value=0.0, max_value=math.pi)


def test_gas_constant_is_avogadro_times_boltzmann():
    assert GAS_CONSTANT == pytest.approx(AVOGADRO * BOLTZMANN, rel=1e-15)


@given(gammas, volumes, driving, factors)
def test_homogeneous_barrier_scales_as_gamma_cubed(g, vm, dmu, k):
    assert homogeneous_barrier(k * g, vm, dmu) == pytest.approx(
        k ** 3 * homogeneous_barrier(g, vm, dmu), rel=1e-12)


@given(gammas, volumes, driving, factors)
def test_homogeneous_barrier_scales_as_inverse_square_driving_force(g, vm, dmu, k):
    assert homogeneous_barrier(g, vm, k * dmu) == pytest.approx(
        homogeneous_barrier(g, vm, dmu) / k ** 2, rel=1e-12)


@given(gammas, volumes, omegas, omegas, temps)
def test_barrier_scales_as_inverse_square_log_saturation(g, vm, om1, om2, t):
    l1, l2 = math.log(om1), math.log(om2)
    assume(l1 > 1e-9 and l2 > 1e-9)
    b1 = homogeneous_barrier_from_saturation(g, vm, om1, t)
    b2 = homogeneous_barrier_from_saturation(g, vm, om2, t)
    assert b1 * l1 ** 2 == pytest.approx(b2 * l2 ** 2, rel=1e-9)


@given(gammas, volumes, temps)
def test_barrier_diverges_as_saturation_approaches_one(g, vm, t):
    eps = np.array([1e-1, 1e-2, 1e-3, 1e-4, 1e-5])
    b = homogeneous_barrier_from_saturation(g, vm, 1.0 + eps, t)
    assert np.all(np.diff(b) > 0)
    # ln(1 + eps) ~ eps, so b * eps^2 tends to a finite constant: divergence like 1/eps^2.
    lim = b * np.log1p(eps) ** 2
    assert np.allclose(lim, lim[0], rtol=1e-12)


@pytest.mark.parametrize("omega", [1.0, 0.5, 1e-9, 0.0, -1.0])
def test_barrier_is_rejected_without_supersaturation(omega):
    with pytest.raises(ValueError):
        homogeneous_barrier_from_saturation(1.0, 1e-5, omega, 300.0)


@pytest.mark.parametrize("dmu", [0.0, -1.0])
def test_barrier_is_rejected_for_non_positive_driving_force(dmu):
    with pytest.raises(ValueError):
        homogeneous_barrier(1.0, 1e-5, dmu)
    with pytest.raises(ValueError):
        critical_radius(1.0, 1e-5, dmu)


@given(gammas, volumes, driving, angles)
def test_heterogeneous_never_exceeds_homogeneous(g, vm, dmu, theta):
    hom = homogeneous_barrier(g, vm, dmu)
    het = heterogeneous_barrier(shape_factor(theta), hom)
    assert 0.0 <= het <= hom


@given(gammas, volumes, driving)
def test_barrier_equals_one_third_surface_term_at_the_critical_radius(g, vm, dmu):
    # At r*, Delta_G* = (4/3) pi r*^2 gamma (one third of the surface free energy).
    r = critical_radius(g, vm, dmu)
    assert homogeneous_barrier(g, vm, dmu) == pytest.approx(4 / 3 * math.pi * r ** 2 * g, rel=1e-12)


@given(gammas, volumes, driving)
def test_critical_radius_is_the_maximum_of_the_cluster_free_energy(g, vm, dmu):
    # Delta_G(r) = 4 pi r^2 gamma - (4/3) pi r^3 Delta_mu_m / V_m has its maximum at r*.
    r = critical_radius(g, vm, dmu)
    dg = lambda x: 4 * math.pi * x ** 2 * g - 4 / 3 * math.pi * x ** 3 * dmu / vm
    assert dg(r) >= dg(0.99 * r) and dg(r) >= dg(1.01 * r)
    assert dg(r) == pytest.approx(homogeneous_barrier(g, vm, dmu), rel=1e-9)


@given(omegas, temps, factors)
def test_molar_and_per_formula_unit_driving_forces_agree(om, t, nu):
    assert driving_force_molar(om, t, nu) == pytest.approx(
        AVOGADRO * driving_force_per_formula_unit(om, t, nu), rel=1e-12)


@given(st.floats(min_value=1e-12, max_value=1e12), temps)
def test_driving_force_sign_follows_saturation_state(om, t):
    dmu = driving_force_molar(om, t)
    if om > 1:
        assert dmu > 0
    elif om < 1:
        assert dmu < 0


@given(st.floats(min_value=0.0, max_value=1e-15), temps)
def test_barrier_in_kT_is_barrier_over_boltzmann_temperature(b, t):
    assert barrier_in_kT(b, t) == pytest.approx(b / (BOLTZMANN * t), rel=1e-15)


@pytest.mark.parametrize("args", [(-1.0, 1e-5, 1.0), (1.0, 0.0, 1.0), (float("nan"), 1e-5, 1.0)])
def test_non_physical_material_inputs_are_rejected(args):
    with pytest.raises(ValueError):
        homogeneous_barrier(*args)


def test_temperature_must_be_positive():
    with pytest.raises(ValueError):
        driving_force_molar(10.0, 0.0)
    with pytest.raises(ValueError):
        barrier_in_kT(1e-20, -1.0)


def test_vectorised_inputs_broadcast():
    g = np.array([1.0, 2.0, 3.0])
    b = homogeneous_barrier_from_saturation(g, 1e-5, np.array([2.0, 4.0, 8.0]), 300.0)
    assert b.shape == (3,)
    for i in range(3):
        assert b[i] == homogeneous_barrier_from_saturation(g[i], 1e-5, [2.0, 4.0, 8.0][i], 300.0)
