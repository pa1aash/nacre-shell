"""Bookkeeping for the Ca2+ binding cycle (see README.md). No method choice is made here.

    [Ca(H2O)m]2+ + L^q-  ->  [Ca L (H2O)n]^(2+q) + (m - n) H2O
"""
import math

from scipy import constants

P_STANDARD_GAS = constants.atm  # 1 atm, Pa
C_STANDARD_SOLUTION = 1000.0  # 1 mol L^-1 in mol m^-3


def standard_state_correction(T):
    """Delta_G(1 atm -> 1 M) per solute species, J mol^-1: RT ln(c° R T / p°)."""
    return constants.R * T * math.log(C_STANDARD_SOLUTION * constants.R * T / P_STANDARD_GAS)


def stoichiometry(m, n, water_mode):
    """Species counts of the cycle for `water_mode` 'monomers' or 'cluster'.

    Returns {'reactants': k_r, 'products': k_p, 'released_waters': m - n}.
    """
    if not (isinstance(m, int) and isinstance(n, int)) or m < 0 or n < 0:
        raise ValueError("water counts must be non-negative integers")
    released = m - n
    if released < 0:
        raise ValueError("the complex holds more waters than the aqua ion (m < n)")
    if water_mode == "monomers":
        products = 1 + released
    elif water_mode == "cluster":
        products = 1 + (1 if released else 0)
    else:
        raise ValueError("water_mode must be 'monomers' or 'cluster'")
    return {"reactants": 2, "products": products, "released_waters": released}


def net_standard_state_correction(T, m, n, water_mode):
    """(products - reactants) x RT ln(c° R T / p°), J mol^-1. The separate RT ln([H2O]) term,
    which needs the density of water, is not included."""
    s = stoichiometry(m, n, water_mode)
    return (s["products"] - s["reactants"]) * standard_state_correction(T)
