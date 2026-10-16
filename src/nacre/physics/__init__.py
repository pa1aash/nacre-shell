"""Physics core of the preprint screen.

Pure, vectorised functions in SI units. Every function validates its inputs against
the physical domain of the quantity it computes and raises ValueError outside it.

Modules
    constants        SI defining constants, taken from sympy's unit system (not typed)
    wetting          heterogeneous-nucleation shape factor f(theta)
    nucleation       classical nucleation theory barriers and critical radius
    supersaturation  chemical-potential driving force from the saturation state Omega
"""
from nacre.physics.constants import AVOGADRO, BOLTZMANN, GAS_CONSTANT
from nacre.physics.nucleation import (
    barrier_in_kT,
    critical_radius,
    heterogeneous_barrier,
    homogeneous_barrier,
    homogeneous_barrier_from_saturation,
)
from nacre.physics.supersaturation import driving_force_molar, driving_force_per_formula_unit
from nacre.physics.wetting import shape_factor, shape_factor_from_cos

__all__ = [
    "AVOGADRO", "BOLTZMANN", "GAS_CONSTANT",
    "barrier_in_kT", "critical_radius", "heterogeneous_barrier", "homogeneous_barrier",
    "homogeneous_barrier_from_saturation",
    "driving_force_molar", "driving_force_per_formula_unit",
    "shape_factor", "shape_factor_from_cos",
]
