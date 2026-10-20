"""The chain of the screen, evaluated draw by draw through the contract functions.

Inputs are keyed by theory symbol id (theory/symbols.yaml), SI units. Each link computes
its physical quantities from the contract implementations in nacre.physics; a draw outside
a quantity's physical domain yields NaN for that quantity (the summary counts valid draws)
instead of aborting the run. The one screen-layer intervention is the clip of Young's ratio
to [-1, 1] (lane note N2, nacre.screen.boundary), which is always counted.

Before the links (derived inputs, contract v3 and the cp3 gap policy)
  speciation free-ion activities a_Ca, a_CO3 and the free Ca2+ concentration c_bulk from pH,
             C_T, Ca_T and the ionic strength (nacre.physics.speciation), when the table
             supplies the totals instead of the activities; a draw with I_ionic > I_val is
             refused (NaN) and counted, never extrapolated.
  ignorance  the ignorance priors of theory/ignorance_priors.md: gamma_sn0 = u (gamma_p +
             gamma_nv) with Delta_gamma_w = 0, gamma_ow = u (gamma_o + gamma_w) and gamma_op =
             u (gamma_o + gamma_p), each u uniform on [0, 1] (the bound moves with its inputs).
             On a deletion control the oxide carries the contact (gamma_p is not bound):
             gamma_sn0 = u (gamma_o + gamma_nv) and the in-situ gamma_sl = u (gamma_o + gamma_w).
  geometry   delta_s loguniform on [Gamma_s V_m, d_layer] (ignorance_priors.md 4, 4a.4: the 2 r_Ca
             term only when r_Ca is bound, the labelled analog sensitivity); a draw whose interval
             is empty is refused and counted. The analog caps of Gamma_s (rho_L d_layer, and
             1/(2 sqrt(3) N_A r_Ca^2) with r_Ca) flag draws and never refuse them (4a, analog_bounds).
  analog     Delta_G_site from a solution binding constant K of the catecholate (contract v4
             Delta_G_site_from_K: -R T ln(K Gamma_s / (delta_s c_std)), the site-volume standard
             state); with pKa2 bound the cycle charges both protons (Delta_G_seq_cycle_2H, thresholds
             C2.analog_route, AM3), so that the Langmuir odds are x_bind_K; gamma_pw = gamma_sl0
             (ignorance_priors.md 1d). configs/preprint/gap_resolution.yaml registers each step.

Links
  anchor     C1: wet work of adhesion of the anchoring group on the oxide. The decisive
             W_adh,wet is the PMF route, Delta_F_pmf / A_c; the interfacial-energy route
             gamma_ow + gamma_pw - gamma_op is the comparator (W_adh_wet_comparator), and a
             sampled W_adh_wet is a flagged analog (W_adh_wet_analog), both run beside it.
  sequester  C2: Ca2+ transfer free energy bulk -> binding layer Delta_G_seq (from the
             site free energy and the protonation correction of one proton, or of two protons
             when pKa2 is bound (contract v4), or sampled directly), the
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
             and the expected areal density of nuclei N_nuc. With gamma_sl0 also the quantities of
             the admissibility rule (contract v4, D27): Pi_ads, the floor gamma_sl0 - Pi_ads_max (gamma_sl0
             where Delta_G_seq >= 0: such a template lowers nothing) and the validity ratio r_ads.
             The chain itself never refuses an inadmissible gamma_sl: the restriction is applied by
             the decision layer over the registered states (nacre.screen.admissibility), and by
             sensitivity_model(..., admissible=True) for the sensitivity analysis.
"""
from dataclasses import dataclass

import numpy as np

from nacre.physics import adhesion, conformality, nucleation, sequestration, speciation, template, wetting
from nacre.physics import supersaturation as sat
from nacre.physics.constants import AVOGADRO, BOLTZMANN, GAS_CONSTANT, STANDARD_CONCENTRATION
from nacre.screen.boundary import EMPTY, RefusedMass, clip_cos_theta
from nacre.screen.mineral import CALCITE


@dataclass(frozen=True)
class Output:
    """A link quantity; ``scale`` is the scale its sensitivity indices are computed on.

    Positive multiplicative quantities (saturation ratios, enrichment, concentrations,
    barriers, radii) are analysed as log10: their priors span orders of magnitude, and the
    barriers diverge like 1 / ln^2(Omega) as Omega -> 1+, so on the linear scale a few
    near-saturation draws carry the variance and the indices do not converge. Scale "none"
    marks a reported quantity that gets quantiles but no sensitivity index.
    """
    symbol: str
    units: str
    scale: str = "linear"


OUTPUTS = {
    "anchor": {
        "W_adh_wet": Output("W_adh,wet (PMF route)", "J m^-2"),
        "W_adh_wet_comparator": Output("gamma_ow + gamma_pw - gamma_op (comparator)", "J m^-2"),
        "W_adh_wet_analog": Output("W_adh,wet (flagged analog)", "J m^-2"),
    },
    "speciation": {
        "a_Ca": Output("a_Ca (free Ca2+ activity)", "1", "log10"),
        "a_CO3": Output("a_CO3 (free carbonate activity)", "1", "log10"),
        "c_Ca_free": Output("c_Ca_free (free Ca2+ concentration, c_bulk)", "mol m^-3", "log10"),
        "a_PO4": Output("a_PO4 (free phosphate activity; phosphate minerals)", "1", "log10"),
        "a_HPO4": Output("a_HPO4 (free hydrogen phosphate activity; phosphate minerals)", "1", "log10"),
        "a_OH": Output("a_OH (hydroxide activity; minerals with an OH- ion)", "1", "log10"),
        "Omega_bulk": Output("Omega_bulk from the speciated activities (C5s; no template input)", "1", "log10"),
    },
    "sequester": {
        "Delta_G_seq": Output("Delta_G_seq", "J mol^-1"),
        "delta_s": Output("delta_s (geometric ignorance prior)", "m", "none"),
        "V_site": Output("V_site = delta_s / (N_A Gamma_s) (derived)", "m^3", "none"),
        "Gamma_s_above_rho_L_cap": Output("flag: Gamma_s above the analog cap rho_L d_layer (never refused)", "1", "none"),
        "Gamma_s_above_a_site_cap": Output("flag: Gamma_s above the analog cap 1/(2 sqrt(3) N_A r_Ca^2) (never refused)", "1",
                                           "none"),
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
        "Pi_ads": Output("Pi_ads = -Delta_gamma_ads (lowering by adsorption)", "J m^-2", "none"),
        "gamma_sl_floor": Output("gamma_sl0 - Pi_ads_max (lowest gamma_sl at any dose)", "J m^-2", "none"),
        "r_ads": Output("r_ads = -Delta_gamma_ads / gamma_sl0 (validity ratio)", "1", "none"),
        "cos_theta": Output("cos(theta) (clipped to [-1, 1])", "1"),
        "f_theta": Output("f(theta)", "1"),
        "barrier_hom_bulk_kT": Output("Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", "log10"),
        "barrier_het_template_kT": Output("f(theta) Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", "log10"),
        "r_star": Output("r*(Omega_bulk)", "m", "log10"),
        "S_spread": Output("S_spread", "J m^-2"),
        "B_acc_kT": Output("B_acc / k_B T", "k_B T"),
        # report only: B_acc - Delta_G*_het inherits the 1/ln^2(Omega) divergence of the barrier and
        # takes both signs, so no scale gives it a finite variance; C3b is analysed through N_nuc
        "accessibility_margin_kT": Output("(B_acc - Delta_G*_het) / k_B T", "k_B T", "none"),
        "N_nuc": Output("N_nuc", "m^-2", "log10"),
        "gamma_sl_minus_nl": Output("gamma_sl - gamma_nl (complete wetting needs > 0)", "J m^-2", "none"),
        "branch_complete": Output("complete-wetting mass of the gamma_sn ignorance prior", "1", "none"),
        "branch_partial": Output("partial-wetting mass of the gamma_sn ignorance prior", "1", "none"),
        "branch_non": Output("non-wetting mass of the gamma_sn ignorance prior", "1", "none"),
        "branch_favourable": Output("mass of gamma_sn <= gamma_sl under the gamma_sn ignorance prior", "1", "none"),
    },
}

ANCHOR_INPUTS = ("gamma_ow", "gamma_pw", "gamma_op")
PMF_INPUTS = ("Delta_F_pmf", "A_c")
SPECIATION_INPUTS = ("pH", "C_T", "Ca_T", "I_ionic", "rho_water", "pK1_carbonic", "pK2_carbonic", "K_CaCO3_aq",
                     "K_CaHCO3", "K_CaOH", "a_w", "A_DH", "b_D", "I_val")
#: Phosphate speciation (contract v5): the same closed-solution inputs with the phosphate acid-base and pair constants.
PHOSPHATE_SPECIATION_INPUTS = ("pH", "P_T", "Ca_T", "I_ionic", "rho_water", "pK1_phosphoric", "pK2_phosphoric",
                               "pK3_phosphoric", "K_CaHPO4_aq", "K_CaH2PO4", "K_CaPO4", "K_CaOH", "a_w", "A_DH",
                               "b_D", "I_val")
#: Symbols the speciation of each kind computes (c_bulk is the free Ca2+ concentration of the C2 relations).
SPECIATION_OUTPUTS = {"carbonate": ("a_Ca", "a_CO3", "c_bulk"), "phosphate": ("a_Ca", "a_PO4", "a_HPO4", "c_bulk")}
#: Ignorance priors: target symbol -> (auxiliary uniform, the two energies whose sum bounds it).
IGNORANCE = {"gamma_sn0": ("u_gamma_sn", ("gamma_p", "gamma_nv")),
             "gamma_ow": ("u_gamma_ow", ("gamma_o", "gamma_w")),
             "gamma_op": ("u_gamma_op", ("gamma_o", "gamma_p"))}
#: The same bound rule on a deletion control, where the oxide carries the contact (gamma_p not bound).
CONTROL_IGNORANCE = {"gamma_sn0": ("u_gamma_sn", ("gamma_o", "gamma_nv")),
                     "gamma_sl": ("u_gamma_sl", ("gamma_o", "gamma_w"))}
#: delta_s geometric ignorance prior (ignorance_priors.md 4, 4a.4): auxiliary uniform and its inputs;
#: r_Ca enters the lower bound only when it is bound (the analog sensitivity).
GEOMETRY = ("u_delta_s", ("d_layer", "Gamma_s", "V_m"))
#: Analog of Delta_G_site from a solution binding constant (gap_resolution.yaml, delta_g_site).
SITE_ANALOG = ("K_Ca_catecholate", ("Gamma_s", "delta_s", "T"))
#: Standard concentration of a solution binding constant, 1 mol dm^-3 in mol m^-3 (exact by definition).
C_STANDARD = STANDARD_CONCENTRATION


def ignorance_pairs(symbols):
    """{target: (u, pair)} of the ignorance priors the symbols can form (template or control surface)."""
    s = set(symbols)
    out = {}
    for target, (u, pair) in IGNORANCE.items():
        if u in s and s >= set(pair):
            out[target] = (u, pair)
    for target, (u, pair) in CONTROL_IGNORANCE.items():
        if target not in out and u in s and "gamma_p" not in s and s >= set(pair):
            out[target] = (u, pair)
    return out
SEQ_CYCLE_INPUTS = ("Delta_G_site", "pKa", "pH", "T")
#: The second proton of a catecholate (contract v4 Delta_G_seq_cycle_2H; bound only on the analog route).
SEQ_CYCLE_2H = "pKa2"
SEQ_LOCAL_INPUTS = ("T", "c_bulk", "Gamma_s", "delta_s")
NUC_BASE = ("a_Ca", "a_CO3", "K_sp", "gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T")
NUC_TAIL = ("gamma_sn0", "Delta_gamma_w", "gamma_nl", "V_m", "T")


def speciation_inputs(mineral=CALCITE):
    """Inputs of the free-ion speciation that suits the mineral (empty: its activities are supplied)."""
    return {"carbonate": SPECIATION_INPUTS, "phosphate": PHOSPHATE_SPECIATION_INPUTS}.get(mineral.speciation, ())


def nuc_base(mineral=CALCITE):
    """Inputs of the nucleation link for the mineral (NUC_BASE for calcite in the carbonate form)."""
    if mineral.is_carbonate_form:
        return NUC_BASE
    return mineral.omega_symbols + NUC_TAIL


def omega_of(x, n, mineral=CALCITE):
    """Omega of the mineral per draw (contract v5), NaN where an input is outside its domain.

    Calcite in the carbonate form uses saturation_ratio_bulk, as before; every other mineral takes
    Omega_nu = IAP/K_sp with the stoichiometric exponents and a_w^n.
    """
    if mineral.is_carbonate_form:
        a_ca, a_co3, ksp = (_arr(x, k, n) for k in ("a_Ca", "a_CO3", "K_sp"))
        ok = _finite(a_ca, a_co3, ksp) & (a_ca > 0) & (a_co3 > 0) & (ksp > 0)
        return _apply(sat.saturation_ratio_bulk, ok, n, a_ca, a_co3, ksp)
    a_ca, a_x, ksp = (_arr(x, k, n) for k in ("a_Ca", mineral.x_symbol, "K_sp"))
    a_y = _arr(x, mineral.y_symbol, n) if mineral.nu_y > 0 else np.ones(n)
    a_w = _arr(x, "a_w", n) if mineral.hydrated else np.ones(n)
    n_hyd = _arr(x, "n_hyd", n) if mineral.n_hyd_key is not None else np.full(n, float(mineral.n_hyd))
    ok = (_finite(a_ca, a_x, a_y, a_w, n_hyd, ksp) & (a_ca > 0) & (a_x > 0) & (a_y > 0) & (a_w > 0) & (n_hyd >= 0)
          & (ksp > 0))
    st = [np.full(n, v) for v in (mineral.nu_ca, mineral.nu_x, mineral.nu_y)]
    return _apply(sat.saturation_ratio_mineral, ok, n, a_ca, a_x, a_y, *st, a_w, n_hyd, ksp)
ACCESS_INPUTS = ("J0_het", "t_proc", "N_req")
NUCLEI_INPUTS = ("J0_het", "t_proc")


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


def derived_symbols(symbols, mineral=CALCITE):
    """The symbols available after the speciation, ignorance, geometry and analog steps."""
    s = set(symbols)
    for target in ignorance_pairs(s):
        s.add(target)
        if target == "gamma_sn0":
            s.add("Delta_gamma_w")
    if "gamma_sl0" in s:
        s.add("gamma_pw")
    if GEOMETRY[0] in s and s >= set(GEOMETRY[1]):
        s.add("delta_s")
    spec_in = speciation_inputs(mineral)
    if spec_in and s >= set(spec_in):
        s |= set(SPECIATION_OUTPUTS[mineral.speciation])
        if mineral.speciation == "phosphate" and "pKw" in s:
            s.add("a_OH")
    if SITE_ANALOG[0] in s and s >= set(SITE_ANALOG[1]):
        s.add("Delta_G_site")
    return s


def derive(x, mineral=CALCITE):
    """Inputs with the speciation and ignorance steps applied; also the speciation outputs and
    the boundary mass of the activity model (draws refused above I_val)."""
    x = dict(x)
    n = _shape(x)
    for target, (u, (a, b)) in ignorance_pairs(x).items():
        x[target] = _arr(x, u, n) * (_arr(x, a, n) + _arr(x, b, n))
        if target == "gamma_sn0":
            x["Delta_gamma_w"] = np.zeros(n)
    if "gamma_sl0" in x and "gamma_pw" not in x:
        x["gamma_pw"] = _arr(x, "gamma_sl0", n)            # the same quantity (ignorance_priors.md 1d)
    geo = {}
    flags = {}
    if has(x, ("Gamma_s", "d_layer")) and "rho_L" in x:          # analog cap: flagged, never refused
        gs = _arr(x, "Gamma_s", n)
        flags["Gamma_s_above_rho_L_cap"] = np.where(np.isfinite(gs), (gs > _arr(x, "rho_L", n) * _arr(x, "d_layer", n))
                                                    .astype(float), np.nan)
    if "Gamma_s" in x and "r_Ca" in x:
        gs, r = _arr(x, "Gamma_s", n), _arr(x, "r_Ca", n)
        flags["Gamma_s_above_a_site_cap"] = np.where(np.isfinite(gs), (gs > 1.0 / (2.0 * np.sqrt(3.0) * AVOGADRO * r ** 2))
                                                     .astype(float), np.nan)
    if GEOMETRY[0] in x and has(x, GEOMETRY[1]):
        u, d, gs, vm = (_arr(x, k, n) for k in (GEOMETRY[0],) + GEOMETRY[1])
        lo = gs * vm
        if "r_Ca" in x:
            lo = np.maximum(2.0 * _arr(x, "r_Ca", n), lo)
        ok = _finite(lo, d) & (lo > 0) & (lo < d)
        ds = np.full(n, np.nan)
        ds[ok] = np.exp(np.log(lo[ok]) + u[ok] * (np.log(d[ok]) - np.log(lo[ok])))
        x["delta_s"] = ds
        geo["delta_s_interval"] = RefusedMass(int(np.isfinite(gs).sum()), int((np.isfinite(gs) & ~ok).sum()),
                                              "empty delta_s interval: lower bound (Gamma_s V_m%s) >= d_layer"
                                              % (", 2 r_Ca" if "r_Ca" in x else ""))
    x["_geometry_flags"] = flags
    if SITE_ANALOG[0] in x and has(x, SITE_ANALOG[1]) and "Delta_G_site" not in x:
        k, gs, ds, t = (_arr(x, s, n) for s in (SITE_ANALOG[0],) + SITE_ANALOG[1])
        ok = _finite(k, gs, ds, t) & (k > 0) & (gs > 0) & (ds > 0) & (t > 0)
        x["Delta_G_site"] = _apply(sequestration.site_free_energy_from_solution_constant, ok, n, k, gs, ds, t)
    spec, mass = None, None
    spec_in = speciation_inputs(mineral)
    produced = SPECIATION_OUTPUTS.get(mineral.speciation, ())
    if spec_in and has(x, spec_in) and not all(k in x for k in produced if k != "c_bulk"):
        v = {k: _arr(x, k, n) for k in spec_in}
        total = "C_T" if mineral.speciation == "carbonate" else "P_T"
        ok = _finite(*v.values()) & (v["I_ionic"] <= v["I_val"]) & (v[total] > 0) & (v["Ca_T"] > 0)
        out = {k: np.full(n, np.nan) for k in produced if k != "c_bulk"}
        out["c_Ca_free"] = np.full(n, np.nan)
        if np.any(ok):
            fn = speciation.speciate if mineral.speciation == "carbonate" else speciation.speciate_phosphate
            r = fn(**{k: a[ok] for k, a in v.items()})
            for k in out:
                out[k][ok] = r[k]
        for k in produced:
            x[k] = out["c_Ca_free"] if k == "c_bulk" else out[k]
        if mineral.speciation == "phosphate" and "pKw" in x and "a_OH" not in x:
            pkw, a_w = _arr(x, "pKw", n), _arr(x, "a_w", n)
            ok_h = _finite(v["pH"], pkw, a_w) & (a_w > 0)
            out["a_OH"] = _apply(sat.hydroxide_activity, ok_h, n, a_w, v["pH"], pkw)
            x["a_OH"] = out["a_OH"]
        refused = int((_finite(*v.values()) & (v["I_ionic"] > v["I_val"])).sum())
        spec = out
        mass = RefusedMass(int(_finite(*v.values()).sum()), refused, "I_ionic above I_val (Davies validity)")
    x["_geometry_masses"] = geo
    return x, spec, mass


def evaluable_links(symbols, mineral=CALCITE):
    """Links whose inputs are all available from the given symbols (after derive)."""
    s = derived_symbols(symbols, mineral)
    links = []
    if s >= set(ANCHOR_INPUTS) or s >= set(PMF_INPUTS) or "W_adh_wet" in s:
        links.append("anchor")
    if speciation_inputs(mineral) and s >= set(speciation_inputs(mineral)):
        links.append("speciation")
    seq = (s >= set(SEQ_CYCLE_INPUTS) or "Delta_G_seq" in s) and s >= set(SEQ_LOCAL_INPUTS)
    if seq:
        links.append("sequester")
    mode = template_energy_mode(s)
    if s >= set(nuc_base(mineral)) and (mode == "in_situ" or (mode == "ca_free" and seq)):
        links.append("nucleate")
    return links


def anchor(x):
    n = _shape(x)
    out = {"W_adh_wet": np.full(n, np.nan), "W_adh_wet_comparator": np.full(n, np.nan),
           "W_adh_wet_analog": np.full(n, np.nan)}
    if "W_adh_wet" in x:                                   # a flagged analog, never the PMF route
        out["W_adh_wet_analog"] = np.array(_arr(x, "W_adh_wet", n), dtype=float)
    if has(x, ANCHOR_INPUTS):
        ow, pw, op = (_arr(x, k, n) for k in ANCHOR_INPUTS)
        out["W_adh_wet_comparator"] = _apply(adhesion.work_of_adhesion_wet, _finite(ow, pw, op), n, ow, pw, op)
    if has(x, PMF_INPUTS):
        df, ac = (_arr(x, k, n) for k in PMF_INPUTS)
        out["W_adh_wet"] = _apply(adhesion.work_of_adhesion_from_pmf, _finite(df, ac) & (ac > 0), n, df, ac)
    return out


def sequester(x):
    n = _shape(x)
    t = _arr(x, "T", n)
    if has(x, SEQ_CYCLE_INPUTS) and SEQ_CYCLE_2H in x:
        site, pka, pka2, ph = (_arr(x, k, n) for k in ("Delta_G_site", "pKa", SEQ_CYCLE_2H, "pH"))
        ok = _finite(site, pka, pka2, ph, t) & (t > 0)
        dg = _apply(sequestration.sequestration_free_energy_two_proton, ok, n, site, pka, pka2, ph, t)
    elif has(x, SEQ_CYCLE_INPUTS):
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
    with np.errstate(divide="ignore", invalid="ignore"):
        v_site = np.where((gs > 0) & (ds > 0), ds / (AVOGADRO * gs), np.nan)
    return {"Delta_G_seq": dg, "delta_s": np.array(ds, dtype=float), "V_site": v_site,
            "Delta_G_seq_RT": dg / (GAS_CONSTANT * t), "E_enr": e,
            "c_local": c_local, "enrichment_realised": c_local / c_bulk, "Theta_occ": occ,
            "Gamma_Ca": excess, "Delta_gamma_ads": d_ads}


def nucleate(x, seq=None, mineral=CALCITE):
    """Nucleation link (contract v2; v5 stoichiometry for a mineral other than calcite).

    seq is the sequester output when gamma_sl0 is supplied.
    """
    n = _shape(x)
    sn0, dw, nl, vm, t = (_arr(x, k, n) for k in NUC_TAIL)
    adm = {q: np.full(n, np.nan) for q in ("Pi_ads", "gamma_sl_floor", "r_ads")}
    if template_energy_mode(x) == "ca_free":
        sl0 = _arr(x, "gamma_sl0", n)
        sl = sl0 + np.asarray(seq["Delta_gamma_ads"], dtype=float)                          # added once
        adm = admissibility_quantities(sl0, seq["Delta_gamma_ads"], seq["Delta_G_seq"], _arr(x, "Gamma_s", n),
                                       _arr(x, "T", n))
    else:
        sl = np.array(_arr(x, "gamma_sl", n), dtype=float)                                  # nothing added
    om = omega_of(x, n, mineral)                                         # uniform chemical potential
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
           "B_acc_kT": np.full(n, np.nan), "accessibility_margin_kT": np.full(n, np.nan), "N_nuc": np.full(n, np.nan),
           "gamma_sl_minus_nl": sl - nl, **adm}
    for b in ("branch_complete", "branch_partial", "branch_non", "branch_favourable"):
        out[b] = np.full(n, np.nan)
    if has(x, ("gamma_p", "gamma_nv")) and "u_gamma_sn" in x:
        # conditional branch masses of gamma_sn ~ U[0, G], G = gamma_p + gamma_nv (properties of the prior)
        g = _arr(x, "gamma_p", n) + _arr(x, "gamma_nv", n)
        with np.errstate(divide="ignore", invalid="ignore"):
            out["branch_complete"] = np.clip((sl - nl) / g, 0.0, 1.0)
            out["branch_non"] = np.clip(1.0 - (sl + nl) / g, 0.0, 1.0)
        out["branch_partial"] = 1.0 - out["branch_complete"] - out["branch_non"]
        with np.errstate(divide="ignore", invalid="ignore"):
            out["branch_favourable"] = np.clip(sl / g, 0.0, 1.0)     # ignorance_priors.md 2a at m_cos = 0
    if has(x, NUCLEI_INPUTS):
        j0, tp = (_arr(x, k, n) for k in NUCLEI_INPUTS)
        ok_n = _finite(j0, tp, t) & (j0 > 0) & (tp > 0) & (t > 0)
        out["N_nuc"] = _apply(nucleation.nucleus_areal_density, ok_n & np.isfinite(het), n, j0, tp, het, t)
        # a state with Omega_bulk <= 1 forms no nuclei (thresholds, C3 accessibility)
        out["N_nuc"][ok_n & np.isfinite(om) & (om <= 1)] = 0.0
    if has(x, ACCESS_INPUTS):
        j0, tp, nr = (_arr(x, k, n) for k in ACCESS_INPUTS)
        ok_a = _finite(j0, tp, nr, t) & (j0 > 0) & (tp > 0) & (nr > 0) & (t > 0)
        b_acc = _apply(nucleation.accessible_barrier, ok_a, n, j0, tp, nr, t)
        out["B_acc_kT"] = b_acc / (BOLTZMANN * t)          # negative when J0 t_proc < N_req
        out["accessibility_margin_kT"] = out["B_acc_kT"] - het_kt
    return out, {"cos_theta": mass}


def admissibility_quantities(gamma_sl0, Delta_gamma_ads, Delta_G_seq, Gamma_s, T):
    """Pi_ads, gamma_sl_floor and r_ads per draw (contract v4); NaN where a draw is outside their domain.

    gamma_sl_floor is gamma_sl0 - Pi_ads_max for a binding template (Delta_G_seq < 0) and gamma_sl0
    otherwise: a template with Delta_G_seq >= 0 lowers nothing at any dose (contract Pi_ads_max note).
    """
    sl0, d_ads, dg, gs, t = (np.asarray(a, dtype=float) for a in (gamma_sl0, Delta_gamma_ads, Delta_G_seq, Gamma_s, T))
    n = sl0.shape
    ok = _finite(sl0, dg, gs, t) & (gs > 0) & (t > 0)
    floor = np.full(n, np.nan)
    floor[ok & (dg >= 0)] = sl0[ok & (dg >= 0)]
    floor_b = _apply(template.template_liquid_energy_floor, ok & (dg < 0), n, sl0, gs, dg, t)
    floor[ok & (dg < 0)] = floor_b[ok & (dg < 0)]
    pi = -d_ads
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(np.isfinite(sl0) & (sl0 > 0) & np.isfinite(d_ads), pi / np.where(sl0 > 0, sl0, 1.0), np.nan)
    return {"Pi_ads": pi, "gamma_sl_floor": floor, "r_ads": r}


ADMISSIBILITY_QUANTITY = "gamma_sl_insitu"


def admissible_mask(outputs):
    """Per-draw admissibility of one state's nucleate outputs: gamma_sl_insitu >= 0 (NaN draws: False)."""
    sl = np.asarray(outputs["nucleate"][ADMISSIBILITY_QUANTITY], dtype=float)
    return np.isfinite(sl) & (sl >= 0)


def evaluate(x, links=None, mineral=CALCITE):
    """Evaluate the chain on sampled inputs x ({symbol: array}).

    Returns (outputs, masses): outputs {link: {quantity: array}} for every evaluable link
    (or the requested subset), masses {link: {quantity: BoundaryMass}}.
    """
    links = evaluable_links(x, mineral) if links is None else list(links)
    x, spec, spec_mass = derive(x, mineral)
    geo = x.pop("_geometry_masses", {})
    flags = x.pop("_geometry_flags", {})
    out, masses = {}, {}
    if "speciation" in links and spec is not None:
        spec = dict(spec)
        n = _shape(x)
        if "K_sp" in x:                      # C5s needs only the speciation and K_sp (thresholds C5s)
            spec["Omega_bulk"] = omega_of(x, n, mineral)
        else:
            spec["Omega_bulk"] = np.full(n, np.nan)
        out["speciation"], masses["speciation"] = spec, {"activity_model": spec_mass}
    if "anchor" in links:
        out["anchor"], masses["anchor"] = anchor(x), {}
    need_seq = "sequester" in links or ("nucleate" in links and template_energy_mode(x) == "ca_free")
    seq = sequester(x) if need_seq else None
    if "sequester" in links:
        n = _shape(x)
        for f in ("Gamma_s_above_rho_L_cap", "Gamma_s_above_a_site_cap"):
            seq[f] = flags.get(f, np.full(n, np.nan))
        out["sequester"], masses["sequester"] = seq, {}
    if geo and ("sequester" in links or "nucleate" in links):
        masses["geometry"] = geo
    if "nucleate" in links:
        out["nucleate"], masses["nucleate"] = nucleate(x, seq, mineral)
    return out, masses


def sensitivity_model(link, admissible=False, mineral=CALCITE):
    """The link as a model {symbol: array} -> {quantity: array on its sensitivity scale}.

    admissible: on the nucleate link, a draw with gamma_sl_insitu < 0 has no output (NaN), so the
    analysis describes the joint prior restricted to the admissible set (AM3; the Shapley double
    loop then samples the restricted conditionals by rejection).
    """
    scales = {q: o.scale for q, o in OUTPUTS[link].items()}

    def model(x):
        full = evaluate(x, [link], mineral)[0]
        out = full[link]
        if admissible and link == "nucleate":
            keep = admissible_mask(full)
            out = {q: np.where(keep, np.asarray(v, dtype=float), np.nan) for q, v in out.items()}
        res = {}
        for q, v in out.items():
            if scales[q] == "log10":
                with np.errstate(divide="ignore", invalid="ignore"):
                    v = np.where(v > 0, np.log10(np.where(v > 0, v, 1.0)), np.nan)
            res[q] = v
        return res
    return model


def flat_model(links=None, mineral=CALCITE):
    """The chain as a model {symbol: array} -> {"link.quantity": array}, for sensitivity analysis."""
    def model(x):
        out, _ = evaluate(x, links, mineral)
        return {"%s.%s" % (link, q): v for link, d in out.items() for q, v in d.items()}
    return model


__all__ = ["OUTPUTS", "evaluate", "evaluable_links", "flat_model", "EMPTY"]
