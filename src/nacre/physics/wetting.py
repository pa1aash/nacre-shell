"""Wetting geometry of a spherical-cap nucleus on a flat substrate.

The heterogeneous-nucleation shape factor f(theta) is the ratio of the volume of a
spherical cap with contact angle theta to the volume of the full sphere of the same
radius; in classical nucleation theory it is also the ratio of the heterogeneous to the
homogeneous barrier, Delta_G*_het = f(theta) Delta_G*_hom.

The contact angle itself (Young's relation) is not computed here: its sign convention is
fixed by the theory contract and lives in the contract-wired module.
"""
import numpy as np

from nacre.physics._domain import closed_interval, scalar_or_array


def shape_factor_from_cos(cos_theta):
    """Shape factor f = (2 + cos theta)(1 - cos theta)^2 / 4 from cos theta in [-1, 1].

    Dimensionless. f = 0 for complete wetting (cos theta = 1, no barrier), f = 1/2 at
    theta = 90 deg and f = 1 for complete non-wetting (cos theta = -1, the substrate
    gives no help and the homogeneous barrier is recovered).
    """
    c = closed_interval("cos_theta", cos_theta, -1.0, 1.0)
    f = (2.0 + c) * (1.0 - c) ** 2 / 4.0
    return scalar_or_array(f)


def shape_factor(theta):
    """Shape factor f(theta) of a spherical-cap nucleus with contact angle theta (radians).

    theta is the contact angle measured through the nucleus, in [0, pi]. Dimensionless,
    monotone increasing from f(0) = 0 to f(pi) = 1.
    """
    t = closed_interval("theta", theta, 0.0, np.pi)
    return shape_factor_from_cos(np.cos(t))
