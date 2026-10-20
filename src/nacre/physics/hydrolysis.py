"""Hydrolysis of a condensed phosphate during the wet period (contract v6; ruling C1, claims_redirect.md 9a).

The observable is the condensed fraction at the end of the wet period. P-O-P bonds hydrolyse toward orthophosphate;
oligophosphates still count as condensed, so only the orthophosphate fraction is lost. Loss is first order in the
condensed fraction with the rate constant k_eff = tau_k k_hyd (the measured constant times the registered transfer
factor from the data condition to the process state):

    f_cond = 2^(-t_wet / t_half),   t_half = ln 2 / k_eff.
"""
import numpy as np

from nacre.physics._domain import non_negative, positive, scalar_or_array

LN2 = np.log(2.0)


def effective_rate_constant(tau_k, k_hyd):
    """k_eff = tau_k k_hyd, s^-1: the rate constant at the process state."""
    t = positive("tau_k (transfer factor)", tau_k)
    k = positive("k_hyd (measured rate constant)", k_hyd)
    return scalar_or_array(t * k)


def half_life(tau_k, k_hyd):
    """t_half = ln 2 / (tau_k k_hyd), s: half-life of the condensed fraction."""
    return scalar_or_array(LN2 / np.asarray(effective_rate_constant(tau_k, k_hyd), dtype=float))


def condensed_fraction(t_wet, t_half_hyd):
    """f_cond = 2^(-t_wet / t_half): the condensed fraction at the end of the wet period (dimensionless).

    Decreasing in t_wet, increasing in t_half; 1 at t_wet = 0, 1/2 at t_wet = t_half.
    """
    t = non_negative("t_wet (wet residence time)", t_wet)
    h = positive("t_half_hyd (half-life of the condensed fraction)", t_half_hyd)
    return scalar_or_array(np.exp(-LN2 * t / h))


def wet_time_flip(t_half_hyd, f_min):
    """t_wet_max = t_half log2(1 / f_min), s: f_cond >= f_min iff t_wet <= t_wet_max (0 at f_min = 1)."""
    h = positive("t_half_hyd (half-life of the condensed fraction)", t_half_hyd)
    f = positive("f_min (smallest admissible condensed fraction)", f_min)
    if np.any(f > 1):
        raise ValueError("f_min must lie in (0, 1]")
    return scalar_or_array(-h * np.log(f) / LN2)
