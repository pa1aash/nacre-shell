"""SI defining constants used by the physics core.

The values are exact by the definition of the SI. They are read from sympy's unit
system at import time rather than typed here, so no constant appears as a literal in
this repository.
"""
from sympy.physics import units as _u
from sympy.physics.units import convert_to as _convert


def _si(quantity, unit):
    return float(_convert(quantity, unit) / unit)


#: Boltzmann constant k_B in J K^-1.
BOLTZMANN = _si(_u.boltzmann_constant, _u.joule / _u.kelvin)
#: Avogadro constant N_A in mol^-1.
AVOGADRO = _si(_u.avogadro_constant, 1 / _u.mol)
#: Molar gas constant R = N_A k_B in J mol^-1 K^-1.
GAS_CONSTANT = BOLTZMANN * AVOGADRO
