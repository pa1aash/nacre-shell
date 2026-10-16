"""Chemical-potential driving force for precipitation from the saturation state.

PLACEHOLDER CONVENTION. The saturation state Omega is taken as the ratio of the ion
activity product to the solubility product, and the driving force per formula unit as

    Delta_mu = nu_eff k_B T ln Omega,

with nu_eff a convention factor that defaults to 1 (Delta_mu = k_B T ln Omega for the
whole formula unit). Conventions that define a mean-ion saturation ratio
S = Omega^(1/nu) recover the same Delta_mu with Delta_mu = nu k_B T ln S, i.e. they
differ only in what is called the saturation ratio. Until the theory contract fixes the
convention, every caller passes Omega (the activity-product ratio) and the factor stays
explicit. Delta_mu > 0 means a supersaturated solution (a driving force for growth).
"""
import numpy as np

from nacre.physics._domain import positive, scalar_or_array
from nacre.physics.constants import BOLTZMANN, GAS_CONSTANT

#: Marks the module's convention as provisional until the theory contract is wired.
CONVENTION_STATUS = "placeholder: pending theory contract"


def _log_saturation(omega):
    om = positive("omega (saturation state)", omega)
    return np.log(om)


def driving_force_per_formula_unit(omega, temperature, convention_factor=1.0):
    """Driving force Delta_mu = nu_eff k_B T ln Omega per formula unit, in J.

    omega: saturation state (ion activity product / solubility product), > 0.
    temperature: absolute temperature in K, > 0.
    convention_factor: nu_eff, > 0 (placeholder, see module docstring).
    Negative for undersaturation (Omega < 1), zero at saturation.
    """
    t = positive("temperature", temperature)
    nu = positive("convention_factor", convention_factor)
    return scalar_or_array(nu * BOLTZMANN * t * _log_saturation(omega))


def driving_force_molar(omega, temperature, convention_factor=1.0):
    """Molar driving force Delta_mu_m = nu_eff R T ln Omega, in J mol^-1."""
    t = positive("temperature", temperature)
    nu = positive("convention_factor", convention_factor)
    return scalar_or_array(nu * GAS_CONSTANT * t * _log_saturation(omega))
