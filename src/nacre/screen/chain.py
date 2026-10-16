"""The chain of the screen, evaluated draw by draw through the contract functions.

Inputs are keyed by theory symbol id (theory/symbols.yaml), SI units. Each link computes
its physical quantities from the contract implementations in nacre.physics; a draw outside
a quantity's physical domain yields NaN for that quantity (the summary counts valid draws)
instead of aborting the run. The one screen-layer intervention is the clip of Young's ratio
to [-1, 1] (lane note N2, nacre.screen.boundary), which is always counted.

Links
  anchor     C1: wet work of adhesion of the anchoring group on the oxide (Dupre),
             W_adh,wet = gamma_ow + gamma_pw - gamma_op.
  sequester  C2: Ca2+ transfer free energy bulk -> binding layer Delta_G_seq (from the
             site free energy and the protonation correction, or sampled directly), the
             enrichment factor E_enr = exp(-Delta_G_seq / RT) and the Langmuir-closed local
             concentration c_local.
  nucleate   C3: bulk and local saturation ratios, Young's cos(theta) on the template, the
             shape factor f, and both barriers in k_B T: the homogeneous barrier in the bulk
             (no template, Omega_bulk) and the heterogeneous barrier on the template,
             f(theta) Delta_G*_hom(Omega_local). The template enters only through theta and
             Omega_local (contract no_double_counting).
"""
from dataclasses import dataclass

import numpy as np

from nacre.physics import adhesion, nucleation, sequestration, wetting
from nacre.physics import supersaturation as sat
from nacre.physics.constants import GAS_CONSTANT
from nacre.screen.boundary import EMPTY, clip_cos_theta


@dataclass(frozen=True)
class Output:
    """A link quantity; ``scale`` is the scale its sensitivity indices are computed on.

    Positive multiplicative quantities (saturation ratios, enrichment, concentrations,
    barriers, radii) are analysed as log10: their priors span orders of magnitude, and the
    barriers diverge like 1 / ln^2(Omega) as Omega -> 1+, so on the linear scale a few
    near-saturation draws carry the variance and the indices do not converge.
    """
    symbol: str
    units: str
    scale: str = "linear"


OUTPUTS = {
    "anchor": {
        "W_adh_wet": Output("W_adh,wet", "J m^-2"),
    },
    "sequester": {
        "Delta_G_seq": Output("Delta_G_seq", "J mol^-1"),
        "Delta_G_seq_RT": Output("Delta_G_seq / R T", "1"),
        "E_enr": Output("E_enr", "1", "log10"),
        "c_local": Output("c_local", "mol m^-3", "log10"),
        "enrichment_realised": Output("c_local / c_bulk", "1", "log10"),
    },
    "nucleate": {
        "Omega_bulk": Output("Omega_bulk", "1", "log10"),
        "Omega_local": Output("Omega_local", "1", "log10"),
        "cos_theta": Output("cos(theta) (clipped to [-1, 1])", "1"),
        "f_theta": Output("f(theta)", "1"),
        "barrier_hom_bulk_kT": Output("Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", "log10"),
        "barrier_het_template_kT": Output("f(theta) Delta_G*_hom(Omega_local) / k_B T", "k_B T", "log10"),
        "r_star_local": Output("r*(Omega_local)", "m", "log10"),
    },
}

ANCHOR_INPUTS = ("gamma_ow", "gamma_pw", "gamma_op")
SEQ_CYCLE_INPUTS = ("Delta_G_site", "pKa", "pH", "T")
SEQ_LOCAL_INPUTS = ("T", "c_bulk", "Gamma_s", "delta_s")
NUC_INPUTS = ("a_Ca", "a_CO3", "K_sp", "gamma_sl", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T")


def _shape(x):
    return np.broadcast(*[np.asarray(v) for v in x.values()]).shape if x else (0,)


def _arr(x, key, n):
    return np.broadcast_to(np.asarray(x[key], dtype=float), n)


def _apply(fn, ok, n, *args):
    """fn on the draws where ok holds, NaN elsewhere (fn sees only in-domain draws)."""
    out = np.full(n, np.nan)
    if np.any(ok):
        out[ok] = fn(*[a[ok] for a in args])
    return out


def _finite(*arrays):
    ok = np.ones(np.shape(arrays[0]), dtype=bool)
    for a in arrays:
        ok &= np.isfinite(a)
    return ok


def has(x, keys):
    return all(k in x for k in keys)


def evaluable_links(symbols):
    """Links whose inputs are all available from the given symbols."""
    s = set(symbols)
    links = []
    if s >= set(ANCHOR_INPUTS):
        links.append("anchor")
    seq = (s >= set(SEQ_CYCLE_INPUTS) or "Delta_G_seq" in s) and s >= set(SEQ_LOCAL_INPUTS)
    if seq:
        links.append("sequester")
        if s >= set(NUC_INPUTS):
            links.append("nucleate")
    return links


def anchor(x):
    n = _shape(x)
    ow, pw, op = (_arr(x, k, n) for k in ANCHOR_INPUTS)
    ok = _finite(ow, pw, op)
    return {"W_adh_wet": _apply(adhesion.work_of_adhesion_wet, ok, n, ow, pw, op)}


def sequester(x):
    n = _shape(x)
    t = _arr(x, "T", n)
    if has(x, SEQ_CYCLE_INPUTS):
        site, pka, ph = (_arr(x, k, n) for k in ("Delta_G_site", "pKa", "pH"))
        ok = _finite(site, pka, ph, t) & (t > 0)
        dg = _apply(sequestration.sequestration_free_energy, ok, n, site, pka, ph, t)
    else:
        dg = np.array(_arr(x, "Delta_G_seq", n), dtype=float)
    c_bulk, gs, ds = (_arr(x, k, n) for k in ("c_bulk", "Gamma_s", "delta_s"))
    ok = _finite(dg, t) & (t > 0)
    e = _apply(sequestration.enrichment_factor, ok, n, dg, t)
    ok_l = ok & np.isfinite(e) & (c_bulk > 0) & (gs > 0) & (ds > 0)
    c_max = _apply(sequestration.binding_layer_saturation_concentration, ok_l, n, gs, ds)
    c_local = _apply(sequestration.local_calcium_concentration, ok_l, n, e, c_bulk, c_max)
    return {"Delta_G_seq": dg, "Delta_G_seq_RT": dg / (GAS_CONSTANT * t), "E_enr": e,
            "c_local": c_local, "enrichment_realised": c_local / c_bulk}


def nucleate(x, seq):
    """Nucleation link; seq is the output of the sequester link (c_local, enrichment)."""
    n = _shape(x)
    a_ca, a_co3, ksp, sl, sn0, dw, nl, vm, t = (_arr(x, k, n) for k in NUC_INPUTS)
    c_bulk = _arr(x, "c_bulk", n)
    ok = _finite(a_ca, a_co3, ksp) & (a_ca > 0) & (a_co3 > 0) & (ksp > 0)
    om_b = _apply(sat.saturation_ratio_bulk, ok, n, a_ca, a_co3, ksp)
    c_local = np.asarray(seq["c_local"], dtype=float)
    ok_l = ok & np.isfinite(c_local) & (c_local > 0) & (c_bulk > 0)
    om_l = _apply(sat.saturation_ratio_local, ok_l, n, c_local, c_bulk, a_ca, a_co3, ksp)
    ok_y = _finite(sl, sn0, dw, nl) & (nl > 0)
    ratio = _apply(wetting.contact_angle_cosine_young, ok_y, n, sl, sn0, dw, nl)
    cos_t, mass = clip_cos_theta(ratio)
    f = _apply(wetting.shape_factor_from_cos, np.isfinite(cos_t), n, cos_t)
    base = _finite(nl, vm, t) & (nl > 0) & (vm > 0) & (t > 0)
    ok_hb = base & (om_b > 1)                      # NaN compares False: invalid draws drop out
    hom_b = _apply(nucleation.homogeneous_barrier_from_saturation, ok_hb, n, nl, vm, om_b, t)
    ok_hl = base & (om_l > 1)
    hom_l = _apply(nucleation.homogeneous_barrier_from_saturation, ok_hl, n, nl, vm, om_l, t)
    r_l = _apply(nucleation.critical_radius_from_saturation, ok_hl, n, nl, vm, om_l, t)
    het = _apply(nucleation.heterogeneous_barrier, ok_hl & np.isfinite(f), n, f, hom_l)
    return ({"Omega_bulk": om_b, "Omega_local": om_l, "cos_theta": cos_t, "f_theta": f,
             "barrier_hom_bulk_kT": _apply(nucleation.barrier_in_kT, ok_hb, n, hom_b, t),
             "barrier_het_template_kT": _apply(nucleation.barrier_in_kT, np.isfinite(het), n, het, t),
             "r_star_local": r_l},
            {"cos_theta": mass})


def evaluate(x, links=None):
    """Evaluate the chain on sampled inputs x ({symbol: array}).

    Returns (outputs, masses): outputs {link: {quantity: array}} for every evaluable link
    (or the requested subset), masses {link: {quantity: BoundaryMass}}.
    """
    links = evaluable_links(x) if links is None else list(links)
    out, masses = {}, {}
    if "anchor" in links:
        out["anchor"], masses["anchor"] = anchor(x), {}
    if "sequester" in links or "nucleate" in links:
        seq = sequester(x)
        if "sequester" in links:
            out["sequester"], masses["sequester"] = seq, {}
        if "nucleate" in links:
            out["nucleate"], masses["nucleate"] = nucleate(x, seq)
    return out, masses


def sensitivity_model(link):
    """The link as a model {symbol: array} -> {quantity: array on its sensitivity scale}."""
    scales = {q: o.scale for q, o in OUTPUTS[link].items()}

    def model(x):
        out = evaluate(x, [link])[0][link]
        res = {}
        for q, v in out.items():
            if scales[q] == "log10":
                with np.errstate(divide="ignore", invalid="ignore"):
                    v = np.where(v > 0, np.log10(np.where(v > 0, v, 1.0)), np.nan)
            res[q] = v
        return res
    return model


def flat_model(links=None):
    """The chain as a model {symbol: array} -> {"link.quantity": array}, for sensitivity analysis."""
    def model(x):
        out, _ = evaluate(x, links)
        return {"%s.%s" % (link, q): v for link, d in out.items() for q, v in d.items()}
    return model


__all__ = ["OUTPUTS", "evaluate", "evaluable_links", "flat_model", "EMPTY"]
