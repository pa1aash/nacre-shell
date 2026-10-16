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
             enrichment factor E_enr and the Langmuir local concentration c_local (C2
             reporting quantities, which never feed Omega under contract v2), the site
             occupancy Theta, the Gibbs surface excess Gamma_Ca and the adsorption change of
             the template-liquid energy Delta_gamma_ads.
  nucleate   C3, contract v2 (uniform chemical potential): Omega = Omega_bulk; Young's
             cos(theta) on the template with gamma_sl = gamma_sl0 + Delta_gamma_ads when the
             table supplies the Ca-free gamma_sl0, or the supplied gamma_sl unchanged when it
             is already at the regime activities (never both: that is refused as ambiguous);
             the shape factor f; both barriers in k_B T, the homogeneous barrier in the bulk
             (no template) and the heterogeneous barrier on the template, f(theta)
             Delta_G*_hom(Omega_bulk); the critical radius. With J0_het, t_proc and N_req in
             the table also the largest accessible barrier B_acc, the margin B_acc - DG_het
             and the expected areal density of nuclei N_nuc.
"""
from dataclasses import dataclass

import numpy as np

from nacre.physics import adhesion, conformality, nucleation, sequestration, template, wetting
from nacre.physics import supersaturation as sat
from nacre.physics.constants import BOLTZMANN, GAS_CONSTANT
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
        "Theta_occ": Output("Theta_occ", "1"),
        "Gamma_Ca": Output("Gamma_Ca", "mol m^-2"),
        "Delta_gamma_ads": Output("Delta_gamma_ads", "J m^-2"),
    },
    "nucleate": {
        "Omega_bulk": Output("Omega_bulk", "1", "log10"),
        "gamma_sl_insitu": Output("gamma_sl (at the regime activities)", "J m^-2"),
        "cos_theta": Output("cos(theta) (clipped to [-1, 1])", "1"),
        "f_theta": Output("f(theta)", "1"),
        "barrier_hom_bulk_kT": Output("Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", "log10"),
        "barrier_het_template_kT": Output("f(theta) Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", "log10"),
        "r_star": Output("r*(Omega_bulk)", "m", "log10"),
        "S_spread": Output("S_spread", "J m^-2"),
        "B_acc_kT": Output("B_acc / k_B T", "k_B T"),
        "accessibility_margin_kT": Output("(B_acc - Delta_G*_het) / k_B T", "k_B T"),
        "N_nuc": Output("N_nuc", "m^-2", "log10"),
    },
}

ANCHOR_INPUTS = ("gamma_ow", "gamma_pw", "gamma_op")
SEQ_CYCLE_INPUTS = ("Delta_G_site", "pKa", "pH", "T")
SEQ_LOCAL_INPUTS = ("T", "c_bulk", "Gamma_s", "delta_s")
NUC_BASE = ("a_Ca", "a_CO3", "K_sp", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T")
ACCESS_INPUTS = ("J0_het", "t_proc", "N_req")


class AmbiguousTemplateEnergy(ValueError):
    """Both gamma_sl0 (Ca-free) and gamma_sl (at the regime activities) were supplied."""


def template_energy_mode(symbols):
    """'ca_free' (gamma_sl0: add Delta_gamma_ads once), 'in_situ' (gamma_sl: add nothing) or None."""
    s = set(symbols)
    if "gamma_sl0" in s and "gamma_sl" in s:
        raise AmbiguousTemplateEnergy("the table supplies both gamma_sl0 and gamma_sl; contract v2 adds "
                                      "Delta_gamma_ads to the Ca-free energy only, so exactly one may be given")
    return "ca_free" if "gamma_sl0" in s else ("in_situ" if "gamma_sl" in s else None)


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
    mode = template_energy_mode(s)
    if s >= set(NUC_BASE) and (mode == "in_situ" or (mode == "ca_free" and seq)):
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
    ok_l = ok & (c_bulk > 0) & (gs > 0) & (ds > 0)
    c_max = _apply(sequestration.binding_layer_saturation_concentration, ok_l, n, gs, ds)
    ok_e = ok_l & np.isfinite(e)
    c_local = _apply(sequestration.local_calcium_concentration, ok_e, n, e, c_bulk, c_max)
    occ = _apply(sequestration.site_occupancy, ok_l, n, dg, t, c_bulk, gs, ds)
    excess = _apply(sequestration.calcium_surface_excess, ok_l, n, dg, t, c_bulk, gs, ds)
    d_ads = _apply(sequestration.adsorption_interfacial_energy_change, ok_l, n, dg, t, c_bulk, gs, ds)
    return {"Delta_G_seq": dg, "Delta_G_seq_RT": dg / (GAS_CONSTANT * t), "E_enr": e,
            "c_local": c_local, "enrichment_realised": c_local / c_bulk, "Theta_occ": occ,
            "Gamma_Ca": excess, "Delta_gamma_ads": d_ads}


def nucleate(x, seq=None):
    """Nucleation link (contract v2); seq is the sequester output when gamma_sl0 is supplied."""
    n = _shape(x)
    a_ca, a_co3, ksp, sn0, dw, nl, vm, t = (_arr(x, k, n) for k in NUC_BASE)
    if template_energy_mode(x) == "ca_free":
        sl = _arr(x, "gamma_sl0", n) + np.asarray(seq["Delta_gamma_ads"], dtype=float)   # added once
    else:
        sl = np.array(_arr(x, "gamma_sl", n), dtype=float)                                  # nothing added
    ok = _finite(a_ca, a_co3, ksp) & (a_ca > 0) & (a_co3 > 0) & (ksp > 0)
    om = _apply(sat.saturation_ratio_bulk, ok, n, a_ca, a_co3, ksp)     # uniform chemical potential
    ok_y = _finite(sl, sn0, dw, nl) & (nl > 0)
    ratio = _apply(wetting.contact_angle_cosine_young, ok_y, n, sl, sn0, dw, nl)
    cos_t, mass = clip_cos_theta(ratio)
    f = _apply(wetting.shape_factor_from_cos, np.isfinite(cos_t), n, cos_t)
    base = _finite(nl, vm, t) & (nl > 0) & (vm > 0) & (t > 0) & (om > 1)   # NaN compares False
    hom = _apply(nucleation.homogeneous_barrier_from_saturation, base, n, nl, vm, om, t)
    r = _apply(nucleation.critical_radius_from_saturation, base, n, nl, vm, om, t)
    het = _apply(nucleation.heterogeneous_barrier, base & np.isfinite(f), n, f, hom)
    hom_kt = _apply(nucleation.barrier_in_kT, base, n, hom, t)
    het_kt = _apply(nucleation.barrier_in_kT, np.isfinite(het), n, het, t)
    spread = _apply(conformality.spreading_coefficient, ok_y, n, sl, sn0, dw, nl)
    out = {"Omega_bulk": om, "gamma_sl_insitu": sl, "cos_theta": cos_t, "f_theta": f,
           "barrier_hom_bulk_kT": hom_kt, "barrier_het_template_kT": het_kt, "r_star": r, "S_spread": spread,
           "B_acc_kT": np.full(n, np.nan), "accessibility_margin_kT": np.full(n, np.nan), "N_nuc": np.full(n, np.nan)}
    if has(x, ACCESS_INPUTS):
        j0, tp, nr = (_arr(x, k, n) for k in ACCESS_INPUTS)
        ok_a = _finite(j0, tp, nr, t) & (j0 > 0) & (tp > 0) & (nr > 0) & (t > 0)
        b_acc = _apply(nucleation.accessible_barrier, ok_a, n, j0, tp, nr, t)
        out["B_acc_kT"] = b_acc / (BOLTZMANN * t)          # negative when J0 t_proc < N_req
        out["accessibility_margin_kT"] = out["B_acc_kT"] - het_kt
        out["N_nuc"] = _apply(nucleation.nucleus_areal_density, ok_a & np.isfinite(het), n, j0, tp, het, t)
        # a state with Omega_bulk <= 1 forms no nuclei (thresholds, C3 accessibility)
        out["N_nuc"][ok_a & np.isfinite(om) & (om <= 1)] = 0.0
    return out, {"cos_theta": mass}


def evaluate(x, links=None):
    """Evaluate the chain on sampled inputs x ({symbol: array}).

    Returns (outputs, masses): outputs {link: {quantity: array}} for every evaluable link
    (or the requested subset), masses {link: {quantity: BoundaryMass}}.
    """
    links = evaluable_links(x) if links is None else list(links)
    out, masses = {}, {}
    if "anchor" in links:
        out["anchor"], masses["anchor"] = anchor(x), {}
    need_seq = "sequester" in links or ("nucleate" in links and template_energy_mode(x) == "ca_free")
    seq = sequester(x) if need_seq else None
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
