"""Physics core of the preprint screen.

Pure, vectorised functions in SI units. Every function validates its inputs against
the physical domain of the quantity it computes and raises ValueError outside it.

The functions of the theory contract (theory/contract.yaml, lane p0-w3) are registered
in nacre.physics.contract and checked against it by nacre.physics.devtools.

Modules
    constants        physical constants, taken from sympy's unit system (not typed)
    wetting          shape factor f(theta); Young's relation under the registered convention;
                     the deck forms (audit only)
    nucleation       classical nucleation theory barriers and critical radius
    supersaturation  saturation ratio (bulk and with Ca2+ enrichment) and driving force
    adhesion         Dupre work of adhesion in water (C1)
    sequestration    Ca2+ transfer free energy, enrichment and its saturation bound (C2)
    template         the barrier on the template through its two channels (C2 + C3)
    conformality     spreading coefficient, coalescence and closure thickness (C4)
    stability        Pourbaix and Li-open grand potentials (C5)
    film             electronic thickness bounds of an insulating film (C4 item 18)
    contract         registry: contract function name -> implementation
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
