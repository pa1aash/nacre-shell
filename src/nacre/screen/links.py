"""Per-link physical models of the screen, evaluated draw by draw.

A link model maps a dict of sampled input arrays (SI units) to a dict of output arrays.
Draws outside the physical domain of an output (for example Omega <= 1, where no
nucleation barrier exists) yield NaN for that draw instead of aborting the whole run;
the summary reports how many draws were valid.

Day 1 provides the nucleation link in a sign-independent form: the contact angle enters
as cos(theta) directly. Once the theory contract is wired, cos(theta) comes from Young's
relation and the template's enrichment enters Omega (P0-W4.2).
"""
from dataclasses import dataclass

import numpy as np

from nacre.physics.nucleation import (
    barrier_in_kT,
    critical_radius,
    heterogeneous_barrier,
    homogeneous_barrier,
)
from nacre.physics.supersaturation import driving_force_molar
from nacre.physics.wetting import shape_factor_from_cos


@dataclass(frozen=True)
class Output:
    symbol: str
    units: str


NUCLEATE_INPUTS = ("gamma_nuc_liq", "molar_volume", "omega", "temperature", "cos_theta")
NUCLEATE_OUTPUTS = {
    "shape_factor": Output("f(theta)", "1"),
    "barrier_hom_kT": Output("Delta_G*_hom / k_B T", "k_B T"),
    "barrier_het_kT": Output("Delta_G*_het / k_B T", "k_B T"),
    "critical_radius": Output("r*", "m"),
}


def nucleate(x):
    """Nucleation link: shape factor, homogeneous and heterogeneous barriers (k_B T), r*.

    Inputs: gamma_nuc_liq (J m^-2), molar_volume (m^3 mol^-1), omega (saturation state),
    temperature (K), cos_theta (dimensionless, in [-1, 1]).
    """
    missing = [k for k in NUCLEATE_INPUTS if k not in x]
    if missing:
        raise KeyError("nucleation link needs inputs %s" % missing)
    n = np.broadcast(*[np.asarray(x[k]) for k in NUCLEATE_INPUTS]).shape
    arr = {k: np.broadcast_to(np.asarray(x[k], dtype=float), n) for k in NUCLEATE_INPUTS}
    ok = ((arr["omega"] > 1) & (arr["gamma_nuc_liq"] > 0) & (arr["molar_volume"] > 0)
          & (arr["temperature"] > 0) & (np.abs(arr["cos_theta"]) <= 1))
    out = {k: np.full(n, np.nan) for k in NUCLEATE_OUTPUTS}
    if np.any(ok):
        g, vm, t = arr["gamma_nuc_liq"][ok], arr["molar_volume"][ok], arr["temperature"][ok]
        dmu = driving_force_molar(arr["omega"][ok], t)
        f = shape_factor_from_cos(arr["cos_theta"][ok])
        hom = homogeneous_barrier(g, vm, dmu)
        out["shape_factor"][ok] = f
        out["barrier_hom_kT"][ok] = barrier_in_kT(hom, t)
        out["barrier_het_kT"][ok] = barrier_in_kT(heterogeneous_barrier(f, hom), t)
        out["critical_radius"][ok] = critical_radius(g, vm, dmu)
    return out


LINKS = {"nucleate": (nucleate, NUCLEATE_INPUTS, NUCLEATE_OUTPUTS)}
