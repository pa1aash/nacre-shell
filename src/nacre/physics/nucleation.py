"""Classical nucleation theory (CNT) for a spherical nucleus.

For a nucleus of interfacial free energy gamma (J m^-2), molar volume V_m (m^3 mol^-1)
and molar driving force Delta_mu_m > 0 (J mol^-1), CNT gives

    critical radius        r* = 2 gamma V_m / Delta_mu_m                       (m)
    homogeneous barrier    Delta_G*_hom = 16 pi gamma^3 V_m^2 / (3 Delta_mu_m^2)  (J per nucleus)
    heterogeneous barrier  Delta_G*_het = f(theta) Delta_G*_hom

The molar forms equal the per-molecule forms (molecular volume v = V_m / N_A and
Delta_mu = Delta_mu_m / N_A) because only the ratio V_m / Delta_mu_m enters.
"""
import numpy as np

from nacre.physics._domain import closed_interval, positive, scalar_or_array
from nacre.physics.constants import BOLTZMANN
from nacre.physics.supersaturation import driving_force_molar
from nacre.physics.wetting import shape_factor


def _driving_force(delta_mu_molar):
    try:
        return positive("delta_mu_molar (driving force)", delta_mu_molar)
    except ValueError as exc:
        raise ValueError(
            "%s: no finite nucleation barrier exists without a positive driving force "
            "(supersaturation)" % exc) from None


def critical_radius(gamma, molar_volume, delta_mu_molar):
    """Critical nucleus radius r* = 2 gamma V_m / Delta_mu_m, in m."""
    g = positive("gamma (interfacial free energy)", gamma)
    vm = positive("molar_volume", molar_volume)
    dmu = _driving_force(delta_mu_molar)
    return scalar_or_array(2.0 * g * vm / dmu)


def homogeneous_barrier(gamma, molar_volume, delta_mu_molar):
    """Homogeneous nucleation barrier 16 pi gamma^3 V_m^2 / (3 Delta_mu_m^2), J per nucleus."""
    g = positive("gamma (interfacial free energy)", gamma)
    vm = positive("molar_volume", molar_volume)
    dmu = _driving_force(delta_mu_molar)
    return scalar_or_array(16.0 * np.pi * g ** 3 * vm ** 2 / (3.0 * dmu ** 2))


def heterogeneous_barrier(shape_factor, homogeneous):
    """Heterogeneous barrier f(theta) Delta_G*_hom, in the units of the homogeneous barrier.

    shape_factor in [0, 1]; homogeneous barrier > 0.
    """
    f = closed_interval("shape_factor", shape_factor, 0.0, 1.0)
    hom = positive("homogeneous barrier", homogeneous)
    return scalar_or_array(f * hom)


def barrier_in_kT(barrier, temperature):
    """A free-energy barrier in J expressed in units of k_B T at temperature T (K)."""
    b = closed_interval("barrier", barrier, 0.0, np.inf)
    t = positive("temperature", temperature)
    return scalar_or_array(b / (BOLTZMANN * t))


def _supersaturated(omega):
    om = positive("omega (saturation ratio)", omega)
    if np.any(om <= 1.0):
        raise ValueError("omega (saturation ratio) must exceed 1: the nucleation barrier "
                         "is undefined without supersaturation")
    return om


def homogeneous_barrier_from_saturation(gamma, molar_volume, omega, temperature):
    """Homogeneous barrier (J per nucleus) at saturation state Omega and temperature T.

    Omega must exceed 1: at Omega <= 1 there is no driving force and no finite barrier,
    so such inputs are rejected. The barrier diverges as Omega -> 1+ like 1 / (ln Omega)^2.
    """
    dmu = driving_force_molar(_supersaturated(omega), temperature)
    return homogeneous_barrier(gamma, molar_volume, dmu)


def critical_radius_from_saturation(gamma, molar_volume, omega, temperature):
    """Critical radius r* = 2 gamma V_m / (R T ln Omega), in m, for Omega > 1."""
    dmu = driving_force_molar(_supersaturated(omega), temperature)
    return critical_radius(gamma, molar_volume, dmu)


def heterogeneous_barrier_from_saturation(theta, gamma, molar_volume, omega, temperature):
    """Heterogeneous barrier f(theta) Delta_G*_hom (J per nucleus) at Omega > 1.

    theta is the contact angle through the nucleus in [0, pi]; gamma is the bare
    nucleus-liquid energy (contract: the bare gamma_nl, never gamma_eff).
    """
    hom = homogeneous_barrier_from_saturation(gamma, molar_volume, omega, temperature)
    return heterogeneous_barrier(shape_factor(theta), hom)
