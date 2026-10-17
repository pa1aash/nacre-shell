"""Physical constants used by the physics core, in SI units.

None is typed here: each is read from sympy's unit system at import time. k_B, N_A, e and
hbar are exact by the definition of the SI, and the standard molality is one mole per
kilogram by the definition of the molal scale; the electron mass is the value sympy carries
(it may be replaced by an effective tunnelling mass, theory open question Q10). The
contract's constant relations R = N_A k_B and F = N_A e define R and F.
"""
from sympy.physics import units as _u
from sympy.physics.units import convert_to as _convert


def _si(quantity, unit):
    return float(_convert(quantity, unit) / unit)


#: Boltzmann constant k_B in J K^-1.
BOLTZMANN = _si(_u.boltzmann_constant, _u.joule / _u.kelvin)
#: Avogadro constant N_A in mol^-1.
AVOGADRO = _si(_u.avogadro_constant, 1 / _u.mol)
#: Elementary charge e in C.
ELEMENTARY_CHARGE = _si(_u.elementary_charge, _u.coulomb)
#: Reduced Planck constant hbar in J s.
HBAR = _si(_u.hbar, _u.joule * _u.second)
#: Standard molality m0 of the molal activity scale, mol kg^-1 (exact by definition).
STANDARD_MOLALITY = _si(_u.mol / _u.kilogram, _u.mol / _u.kilogram)
#: Electron rest mass m_e in kg.
ELECTRON_MASS = _si(_u.electron_rest_mass, _u.kilogram)
#: Molar gas constant R = N_A k_B in J mol^-1 K^-1.
GAS_CONSTANT = BOLTZMANN * AVOGADRO
#: Faraday constant F = N_A e in C mol^-1.
FARADAY = AVOGADRO * ELEMENTARY_CHARGE
