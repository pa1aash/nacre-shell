"""Screen-layer treatment of contact-angle cosines outside [-1, 1] (lane note N2).

Young's ratio (gamma_sl - gamma_sn) / gamma_nl is a cosine only inside [-1, 1]. Outside it
there is no finite contact angle: above 1 the nucleus phase spreads on the template
(complete wetting, theta = 0, f = 0, no barrier) and below -1 the template is not wetted at
all (theta = 180 deg, f = 1, the homogeneous barrier). Independent prior draws of the three
interfacial energies land outside [-1, 1] with finite probability.

The physics functions (nacre.physics.wetting) keep raising on such input. Only the screen
clips, and it always counts what it clipped: the boundary mass is the fraction of prior
draws placed at theta = 0 or theta = 180 deg by the clip, reported per regime in the
results summary so that a verdict carried by clipped mass is visible.
"""
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BoundaryMass:
    """Counts of draws whose Young ratio left [-1, 1], out of the draws with a finite ratio."""
    n_finite: int
    n_spread: int        # ratio > 1: clipped to theta = 0 (f = 0)
    n_nonwetting: int    # ratio < -1: clipped to theta = 180 deg (f = 1)

    @property
    def spread_fraction(self):
        return self.n_spread / self.n_finite if self.n_finite else float("nan")

    @property
    def nonwetting_fraction(self):
        return self.n_nonwetting / self.n_finite if self.n_finite else float("nan")

    @property
    def total_fraction(self):
        return (self.n_spread + self.n_nonwetting) / self.n_finite if self.n_finite else float("nan")

    def __add__(self, other):
        return BoundaryMass(self.n_finite + other.n_finite, self.n_spread + other.n_spread,
                            self.n_nonwetting + other.n_nonwetting)

    def as_dict(self):
        """Entry of the results summary (schema $defs/boundary_mass)."""
        return {"n_finite": self.n_finite, "n_clipped_theta_0": self.n_spread,
                "n_clipped_theta_180": self.n_nonwetting,
                "fraction_theta_0": float(self.spread_fraction) if self.n_finite else 0.0,
                "fraction_theta_180": float(self.nonwetting_fraction) if self.n_finite else 0.0,
                "fraction_total": float(self.total_fraction) if self.n_finite else 0.0}


EMPTY = BoundaryMass(0, 0, 0)


@dataclass(frozen=True)
class RefusedMass:
    """Draws refused because an input left the registered validity range of a model
    (for example the Davies activity model above I_val); refused draws are NaN, never
    extrapolated, and are counted here."""
    n_evaluated: int
    n_refused: int
    reason: str = ""

    def __add__(self, other):
        return RefusedMass(self.n_evaluated + other.n_evaluated, self.n_refused + other.n_refused,
                           self.reason or other.reason)

    def as_dict(self):
        return {"n_evaluated": self.n_evaluated, "n_refused": self.n_refused,
                "fraction_refused": self.n_refused / self.n_evaluated if self.n_evaluated else 0.0,
                "reason": self.reason}


def clip_cos_theta(ratio):
    """Clip a Young ratio to a contact-angle cosine in [-1, 1] and count the clipped draws.

    Returns (cos_theta, BoundaryMass). Non-finite ratios pass through as NaN and are not
    counted. A ratio above 1 becomes cos theta = 1 (theta = 0, f = 0); below -1 becomes
    cos theta = -1 (theta = 180 deg, f = 1).
    """
    r = np.asarray(ratio, dtype=float)
    finite = np.isfinite(r)
    high = finite & (r > 1.0)
    low = finite & (r < -1.0)
    c = np.where(finite, np.clip(r, -1.0, 1.0), np.nan)
    return c, BoundaryMass(int(finite.sum()), int(high.sum()), int(low.sum()))
