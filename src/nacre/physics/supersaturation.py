"""Saturation state and the chemical-potential driving force for precipitation.

Convention (theory contract, P0-W3.1): one definition of the saturation ratio,

    Omega = IAP / K_sp = a_Ca a_CO3 / K_sp,

and the driving force per formula unit Delta_mu = k_B T ln Omega (molar form
R T ln Omega). Delta_mu > 0 means a supersaturated solution. The template enriches Ca2+
alone; carbonate stays at its bulk activity, so the local saturation ratio is

    Omega_local = (c_local / c_bulk) a_Ca a_CO3 / K_sp.
"""
import numpy as np

from nacre.physics._domain import positive, scalar_or_array
from nacre.physics.constants import BOLTZMANN, GAS_CONSTANT


def saturation_ratio_bulk(a_Ca, a_CO3, K_sp):
    """Bulk saturation ratio Omega_bulk = a_Ca a_CO3 / K_sp (dimensionless)."""
    a = positive("a_Ca (Ca2+ activity)", a_Ca)
    b = positive("a_CO3 (carbonate activity)", a_CO3)
    k = positive("K_sp (solubility product)", K_sp)
    return scalar_or_array(a * b / k)


def saturation_ratio_local(c_local, c_bulk, a_Ca, a_CO3, K_sp):
    """Saturation ratio in the template binding layer, (c_local / c_bulk) Omega_bulk.

    Only Ca2+ is enriched; the carbonate activity and the Ca2+ activity coefficient are
    taken at their bulk values (theory open questions Q2, Q3).
    """
    cl = positive("c_local (layer Ca2+ concentration)", c_local)
    cb = positive("c_bulk (bulk Ca2+ concentration)", c_bulk)
    return scalar_or_array(cl / cb * saturation_ratio_bulk(a_Ca, a_CO3, K_sp))


def driving_force_per_formula_unit(omega, temperature):
    """Driving force Delta_mu = k_B T ln Omega per formula unit, in J.

    Negative for undersaturation (Omega < 1), zero at saturation.
    """
    om = positive("omega (saturation ratio)", omega)
    t = positive("temperature", temperature)
    return scalar_or_array(BOLTZMANN * t * np.log(om))


def driving_force_molar(omega, temperature):
    """Molar driving force Delta_mu_m = R T ln Omega, in J mol^-1."""
    om = positive("omega (saturation ratio)", omega)
    t = positive("temperature", temperature)
    return scalar_or_array(GAS_CONSTANT * t * np.log(om))
