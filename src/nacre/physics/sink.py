"""Dilute-electrolyte sink term m_sink at the registered concentration, and the edge rule (contract v7; PH-W3.8 ruling 2).

Pure functions over inputs. No value is bound here: the solubility and the activity coefficients are W1 keys
(liclo4_solubility_pc, liclo4_activity_coefficient_pc) and arrive as arguments. A gap (None or NaN) never gives zero:
sink_margin_checked raises SinkInputUnbound and rigorous_sink_margin returns UNDETERMINED.
"""
import math

from nacre.physics.bindings import UNDETERMINED
from nacre.physics.constants import STANDARD_CONCENTRATION
from nacre.physics.stability import sink_margin


class SinkInputUnbound(ValueError):
    """An input of m_sink is a gap (None or NaN); the dilute-electrolyte exclusion is undetermined."""


def _gap(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def mean_activity(gamma_pm, c_salt):
    """a_pm = gamma_pm c_salt / c_std on the molar scale; c_salt in mol m^-3, c_std from the constants module."""
    return gamma_pm * c_salt / STANDARD_CONCENTRATION


def sink_margin_checked(nu_salt, T, a_pm_sat, a_pm):
    """m_sink in V, raising SinkInputUnbound when nu_salt, T or either activity is a gap."""
    for name, v in (("nu_salt", nu_salt), ("T", T), ("a_pm_sat", a_pm_sat), ("a_pm", a_pm)):
        if _gap(v):
            raise SinkInputUnbound("m_sink input %s is a gap; the dilute-electrolyte exclusion is undetermined, "
                                   "not zero" % name)
    return sink_margin(nu_salt, T, a_pm_sat, a_pm)


def _ends(x):
    return tuple(x) if isinstance(x, (tuple, list)) else (x, x)


def rigorous_sink_margin(nu_salt, T, c_salt, c_salt_sat, gamma_pm, gamma_pm_sat):
    """Largest m_sink over the input intervals, V, or UNDETERMINED when any input is a gap.

    c_salt is the registered concentration (a point); c_salt_sat, gamma_pm and gamma_pm_sat are (low, high) pairs or
    scalars. The evaluation takes the upper end of c_salt_sat and gamma_pm_sat and the lower end of gamma_pm, so it is
    never smaller than the central evaluation. An electrolyte above saturation is outside the one-sided margin.
    """
    c_sat, g, g_sat = _ends(c_salt_sat), _ends(gamma_pm), _ends(gamma_pm_sat)
    if any(_gap(v) for v in (nu_salt, T, c_salt, *c_sat, *g, *g_sat)):
        return UNDETERMINED
    a_sat = mean_activity(max(g_sat), max(c_sat))
    a = mean_activity(min(g), c_salt)
    if a > a_sat:
        raise ValueError("a_pm exceeds a_pm_sat: the electrolyte is above saturation and m_sink is not defined there")
    return float(sink_margin(nu_salt, T, a_sat, a))


def edge_rule(crossover, edges, tolerance):
    """Inputs of the edge rule of the prose (screen_ph.sink_v10.edge_rule), in one unit (V) for all arguments.

    crossover is E_x- (the falsifying crossover), edges the registered class edges, tolerance the registered tolerance.
    Returns the near edge, its signed distance (edge - crossover), whether it lies within the tolerance, and the robust
    threshold: the lowest registered edge that clears the crossover by at least the tolerance (None if there is none).
    A gap in the crossover or the tolerance is UNDETERMINED.
    """
    if _gap(crossover) or _gap(tolerance):
        return {"status": UNDETERMINED}
    es = sorted(edges)
    near = min(es, key=lambda e: abs(e - crossover))
    robust = next((e for e in es if e - crossover >= tolerance), None)
    return {"status": "ok", "near_edge": near, "distance": near - crossover,
            "within_tolerance": abs(near - crossover) < tolerance, "robust_threshold": robust}
