"""Hydrated amorphous phases against their same-composition crystalline reference plus water (contract v8; I17a).

Pure functions over inputs; no value is bound here. Delta_G_gc_w = G(A) - G(C) - n_hyd mu_w(l, a_w = 1) >= 0 is the
free energy of a hydrated amorphous phase A above the crystalline phase or phases C of the same Ca:P (and OH, HPO4)
composition plus n_hyd liquid water at unit activity. The bound only falsifies: the amorphous row inherits the margin and
the sink reference state of its crystalline reference row and is excluded wherever that row is; it is never a pass.
A gap in any input other than Delta_G_gc_w gives UNDETERMINED; a gap in Delta_G_gc_w is evaluated at its sign bound zero
with the cell water at unit activity, which returns E_ub of the reference row and no other number.
"""
import math

from nacre.physics.bindings import UNDETERMINED
from nacre.physics.stability import onset_solid_salt_sink, onset_solid_salt_sink_hydrated_amorphous

#: Composition keys compared by the same-composition guard (per formula unit).
COMPOSITION_KEYS = ("Ca", "P", "OH", "HPO4")

#: Sign bound of Delta_G_gc_w (J mol^-1), the value used for a verdict while the quantity is a gap.
SIGN_BOUND = 0.0


def _gap(x):
    return x is None or (isinstance(x, float) and math.isnan(x))


def delta_G_gc_w(G_A, G_C, n_hyd, mu_w_liquid):
    """Delta_G_gc_w = G(A) - G(C) - n_hyd mu_w(l, a_w = 1), J mol^-1, or UNDETERMINED when an input is a gap.

    G_A and G_C per formula unit of A and of the reference C on one scale, mu_w_liquid the chemical potential of liquid
    water at unit activity on that scale. A negative result contradicts the bound (A metastable against C plus water) and
    is returned as computed so that the consumer rejects it.
    """
    if any(_gap(v) for v in (G_A, G_C, n_hyd, mu_w_liquid)):
        return UNDETERMINED
    return G_A - G_C - n_hyd * mu_w_liquid


def same_composition(reference, amorphous):
    """True when the reference carries the same Ca:P (and OH, HPO4) per formula unit as the amorphous phase.

    Both arguments are mappings over COMPOSITION_KEYS (a missing key counts as zero) of the formula unit of the
    reference and of the amorphous phase less its n_hyd water. A missing mapping is not a match.
    """
    if reference is None or amorphous is None:
        return False
    if any(_gap(reference.get(k, 0.0)) or _gap(amorphous.get(k, 0.0)) for k in COMPOSITION_KEYS):
        return False
    return all(math.isclose(reference.get(k, 0.0), amorphous.get(k, 0.0), rel_tol=1e-12, abs_tol=0.0)
               for k in COMPOSITION_KEYS)


def onset(reference, amorphous):
    """E_ub_hydrated_am in V for a verdict, or UNDETERMINED.

    reference: Delta_G_r_ss (J mol^-1), Delta_n_Li, composition. amorphous: composition (less its water), n_hyd, a_w, T and
    optionally Delta_G_gc_w. With Delta_G_gc_w a gap the evaluation is the sign bound Delta_G_gc_w = 0 at a_w = 1.
    A reference that does not carry the amorphous phase's composition is not evaluated.
    """
    if not same_composition(reference.get("composition"), amorphous.get("composition")):
        return UNDETERMINED
    g, dn = reference.get("Delta_G_r_ss"), reference.get("Delta_n_Li")
    if _gap(g) or _gap(dn):
        return UNDETERMINED
    gc = amorphous.get("Delta_G_gc_w")
    if _gap(gc):
        gc, n, aw = SIGN_BOUND, 0.0, 1.0
        T = amorphous.get("T", 298.15) if not _gap(amorphous.get("T")) else 298.15
    else:
        n, aw, T = amorphous.get("n_hyd"), amorphous.get("a_w"), amorphous.get("T")
        if any(_gap(v) for v in (n, aw, T)):
            return UNDETERMINED
    return float(onset_solid_salt_sink_hydrated_amorphous(g, gc, n, aw, T, dn))


def _excluded(E_ub, E_c, margin, m_sink):
    return E_ub + margin + m_sink < E_c


def k1_verdicts(reference, amorphous, E_c, margin, m_sink, label):
    """{"K1_falsify": word, "K1_falsify_dilute": word} of an amorphous row at one cutoff class E_c (V).

    The word is `label` where the crystalline reference row is excluded by that test with the reference's own margin
    (and m_sink for the dilute test) and the amorphous bound E_ub_hydrated_am agrees, and UNDETERMINED otherwise: a
    reference that is not excluded, a gap in the reference, the margin or m_sink, or a composition mismatch. The result is
    never a pass and never open.
    """
    ref_E = None
    if not _gap(reference.get("Delta_G_r_ss")) and not _gap(reference.get("Delta_n_Li")) and reference["Delta_n_Li"] != 0:
        ref_E = float(onset_solid_salt_sink(reference["Delta_G_r_ss"], reference["Delta_n_Li"]))
    am_E = onset(reference, amorphous)
    out = {}
    for test, ms in (("K1_falsify", 0.0), ("K1_falsify_dilute", m_sink)):
        if ref_E is None or am_E == UNDETERMINED or _gap(margin) or _gap(ms) or _gap(E_c):
            out[test] = UNDETERMINED
        elif _excluded(ref_E, E_c, margin, ms) and _excluded(am_E, E_c, margin, ms):
            out[test] = label
        else:
            out[test] = UNDETERMINED
    return out

