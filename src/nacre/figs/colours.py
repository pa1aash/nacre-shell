"""Colour choices that must stay distinct under colour-vision deficiency.

Distance and simulation follow figures/style/palette.yaml: colorspacious CAM02-UCS deltaE, CVD
simulated at severity 100 for deuteranopia, protanopia and tritanopia, threshold delta_e_min.
"""
import itertools
import warnings

import numpy as np

from nacre.figs import style

_CONDITIONS = (None, "deuteranomaly", "protanomaly", "tritanomaly")
# Okabe-Ito colours usable as area fills (black and gray carry boundaries and text).
FILL_CANDIDATES = ("blue", "vermillion", "bluishgreen", "orange", "reddishpurple", "skyblue", "yellow")
_LIGHTEN_STEPS = tuple(round(x, 2) for x in np.arange(0.5, -0.001, -0.05))


def _cs():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", SyntaxWarning)
        from colorspacious import cspace_convert, deltaE
    return cspace_convert, deltaE


def _sim(rgb, cond):
    cspace_convert, _ = _cs()
    if cond is None:
        return np.asarray(rgb, dtype=float)
    space = {"name": "sRGB1+CVD", "cvd_type": cond, "severity": 100}
    return np.clip(cspace_convert(np.asarray(rgb, dtype=float), space, "sRGB1"), 0.0, 1.0)


def lighten(rgb, f):
    rgb = np.asarray(rgb, dtype=float)
    return rgb + (1.0 - rgb) * f


def min_delta_e(colours):
    """Smallest pairwise CAM02-UCS distance over normal vision and the three simulations."""
    _, deltaE = _cs()
    best = float("inf")
    for cond in _CONDITIONS:
        sims = [_sim(c, cond) for c in colours]
        for a, b in itertools.combinations(sims, 2):
            best = min(best, float(deltaE(a, b, input_space="sRGB1")))
    return best


def distinct_fills(n, root=None):
    """n fill colours (sRGB tuples) clearing palette delta_e_min in every condition.

    Picks the subset of FILL_CANDIDATES with the largest worst-case distance, at the largest
    lightening (towards white, so strokes stay legible over the fill) that still clears the
    threshold. Returns (colours, names, lighten_factor, min_delta_e).
    """
    pal = style.palette(root)
    threshold = float(pal["delta_e_min"])
    base = {k: np.asarray(pal["categorical"]["okabe_ito"][k]["srgb"], dtype=float) for k in FILL_CANDIDATES}
    for f in _LIGHTEN_STEPS:
        best = None
        for combo in itertools.combinations(FILL_CANDIDATES, n):
            d = min_delta_e([lighten(base[k], f) for k in combo])
            if best is None or d > best[0] + 1e-9:
                best = (d, combo)
        if best[0] >= threshold:
            names = best[1]
            fills = [tuple(round(float(x), 4) for x in lighten(base[k], f)) for k in names]
            return fills, list(names), float(f), best[0]
    raise ValueError("no set of %d fills clears delta_e_min %.1f" % (n, threshold))
