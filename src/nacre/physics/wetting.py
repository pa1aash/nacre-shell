"""Wetting geometry of a spherical-cap nucleus on a flat substrate.

The heterogeneous-nucleation shape factor f(theta) is the ratio of the volume of a
spherical cap with contact angle theta to the volume of the full sphere of the same
radius; in classical nucleation theory it is also the ratio of the heterogeneous to the
homogeneous barrier, Delta_G*_het = f(theta) Delta_G*_hom.

The contact angle itself (Young's relation) is not computed here: its sign convention is
fixed by the theory contract and lives in the contract-wired module.
"""
import numpy as np

from nacre.physics._domain import closed_interval, positive, real, scalar_or_array


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


# ---------------------------------------------------------------- Young's relation (contract)
#
# Registered convention (theory contract, P0-W3.1): theta is measured through the nucleus and
#
#     cos(theta) = (gamma_sl - gamma_sn) / gamma_nl,   gamma_sn = gamma_sn0 + Delta_gamma_w,
#
# with the bare nucleus-liquid energy gamma_nl in the denominator. Delta_gamma_w > 0 is the
# cost of displacing the template's bound water when the nucleus contacts it; it belongs to
# the substrate-nucleus term only, raises theta and f, and is zero by definition when
# gamma_sn is supplied as a full in-water interfacial energy (it must then not be added).


#: Floating-point allowance at |cos theta| = 1 (the exact limits theta = 0 and theta = pi).
_ROUNDING = 8 * np.finfo(float).eps


def contact_angle_cosine_young(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    """Young ratio (gamma_sl - gamma_sn0 - Delta_gamma_w) / gamma_nl (dimensionless).

    Returned unclipped: a value above 1 means the nucleus phase spreads on the template
    (S_spread >= 0, no finite contact angle); below -1 means no wetting at all. Only values
    in [-1, 1] correspond to a contact angle (see contact_angle_young).
    """
    sl = real("gamma_sl (template-liquid energy)", gamma_sl)
    sn0 = real("gamma_sn0 (template-nucleus energy, reference)", gamma_sn0)
    dw = real("Delta_gamma_w (water-displacement correction)", Delta_gamma_w)
    nl = positive("gamma_nl (nucleus-liquid energy)", gamma_nl)
    return scalar_or_array((sl - sn0 - dw) / nl)


def contact_angle_cosine_young_uncorrected(gamma_sl, gamma_sn0, gamma_nl):
    """Young ratio (gamma_sl - gamma_sn0) / gamma_nl with no water-displacement correction."""
    return contact_angle_cosine_young(gamma_sl, gamma_sn0, 0.0, gamma_nl)


def contact_angle_young(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl):
    """Contact angle theta (rad, in [0, pi]) of the nucleus on the template from Young.

    Raises ValueError where the Young ratio leaves [-1, 1]: there is then no finite
    contact angle (complete spreading above 1, complete non-wetting below -1).
    """
    c = np.asarray(contact_angle_cosine_young(gamma_sl, gamma_sn0, Delta_gamma_w, gamma_nl))
    if np.any(np.abs(c) > 1.0 + _ROUNDING):
        raise ValueError("Young ratio outside [-1, 1]: no finite contact angle (the nucleus "
                         "phase spreads when the ratio exceeds 1)")
    return scalar_or_array(np.arccos(np.clip(c, -1.0, 1.0)))


# ---------------------------------------------------------------- deck forms (audit only)


def effective_nucleus_liquid_energy_deck(gamma_nl, Delta_gamma_w):
    """Deck form gamma_eff = gamma_nl - Delta_gamma_w, J m^-2. AUDIT ONLY.

    Recorded for the audit and the double-counting demonstration (C3 item 13). With a
    displacement cost (Delta_gamma_w > 0) it is below gamma_nl, the wrong-way effect of
    design flag 3. Neither Young nor the homogeneous barrier uses it.
    """
    nl = positive("gamma_nl (nucleus-liquid energy)", gamma_nl)
    dw = real("Delta_gamma_w (water-displacement correction)", Delta_gamma_w)
    return scalar_or_array(nl - dw)


def contact_angle_cosine_deck(gamma_sl, gamma_sn0, gamma_nl, Delta_gamma_w):
    """Rejected deck Young ratio (gamma_sl - gamma_sn0) / (gamma_nl - Delta_gamma_w). AUDIT ONLY.

    Implemented only to demonstrate the sign reversal and the double-counting error.
    Requires gamma_eff = gamma_nl - Delta_gamma_w > 0.
    """
    sl = real("gamma_sl (template-liquid energy)", gamma_sl)
    sn0 = real("gamma_sn0 (template-nucleus energy, reference)", gamma_sn0)
    eff = positive("gamma_eff (deck effective energy)",
                   effective_nucleus_liquid_energy_deck(gamma_nl, Delta_gamma_w))
    return scalar_or_array((sl - sn0) / eff)
