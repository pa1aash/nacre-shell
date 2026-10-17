"""Saturation state and the chemical-potential driving force for precipitation.

Convention (theory contract v2, P0-W3.2): one definition of the saturation ratio,

    Omega = IAP / K_sp = a_Ca a_CO3 / K_sp,

and the driving force per formula unit Delta_mu = k_B T ln Omega (molar form
R T ln Omega). Delta_mu > 0 means a supersaturated solution. At equilibrium the ion
chemical potentials are uniform, so the driving force at the template is the bulk one,
Omega = Omega_bulk. The local-ideal Omega_local = (c_local / c_bulk) Omega_bulk of
contract v1 credits the binding free energy to the driving force; it survives only in the
double-counting demonstration (nacre.physics.devtools.wrong_variants).
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
