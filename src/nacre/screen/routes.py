"""Route layer of the redirected screen (in-situ polyphosphate films): the decision tables of theory/claims_redirect.md
Section 9 (contract v6; rulings C1 to C6), implemented in PH-W4.2a.

Routes: R1 interfacial gelation of a soluble polyphosphate by Al3+ released at the oxide; R2 a Ca-polyphosphate
coacervate that wets the foil and dries to a glass; R3 dry-trapped Ca-polyphosphate. The three extension points named
in PH-W4.1 are filled here:

    hydrolysis_descriptor      K2h, table H1 to H4 (ruling C1): a CONDITIONAL gate, it ends a row only through H2
    formation_accessibility    K3 route forms: R1 table F1r to F4r (falsifying only), R2 table B1 to B4; R3 has none
    liquid_precursor_wetting   K4 route form (ruling C3): S_coac >= m_S with both gamma_nl limits; the closure route is
                               the alternative and a falsification needs both to fail on the same draw

and beside them the framing rule of the route products (9d), the matrix rungs M1 to M4 and the baseline rows L1 to
L5 (9e), and the symbolic thresholds structure (9f). Each table is evaluated in its registered order; its rows are
exhaustive. Verdict words are the tables' own: feasible, falsified, inconclusive, undetermined, plus "not excluded"
(F3r, B3: never a pass) and "not gating" (H3).

Every record carries the evidence grade of each input it used (`single-source`, `sourced`, `computed`, `analog`,
`gap`, `mock`). Nothing here sets a prior, a threshold or a margin: numbers come from the parameter table (route keys
of Section 9g) and the provisional k_screen block of configs/preprint/screen.yaml.
"""
import math

import numpy as np

from nacre.physics import coacervate, gelation, hydrolysis
from nacre.screen import decision

NAMES = ("liquid_precursor_wetting", "formation_accessibility", "hydrolysis_descriptor")
ROUTES = ("R1", "R2", "R3")
GRADES = ("single-source", "sourced", "computed", "analog", "gap", "mock")
#: Labels of the decision tables (claims_redirect.md 9a to 9c), printed verbatim.
LABELS = {
    "H1": "hydrolysis: outside data",
    "H2": "hydrolysed even at the slowest plausible rate",
    "H3": "condensed fraction kept at the fastest plausible rate",
    "H4": "inconclusive: flip value t_wet* printed at k_slow and k_fast",
    "F1r": "K_sp,AlPP is a gap: flip value K_sp* = IAP_AlPP printed",
    "F2r": "gel cannot form (thermodynamic accessibility)",
    "F3r": "not excluded by thermodynamic accessibility",
    "F4r": "inconclusive",
    "B1": "state outside the covered region of the binodal map",
    "B2": "no liquid precursor",
    "B3": "a liquid precursor exists; K4 route form next",
    "B4": "inconclusive",
}
KINETIC_HYPOTHESIS = "the kinetic race of gelation against hydrolysis is a labelled hypothesis (ruling C2), not evaluated"


class RouteInputError(ValueError):
    """A route evaluator was given inputs that do not have the registered form."""


# ------------------------------------------------------------------ evidence grades
def grade_of(entry, mock=False):
    """Evidence grade of one parameter-table entry: `mock` for a mock table, the entry's own `evidence_grade` when
    stated, `gap` for an unsampled prior family, else the entry's status (sourced, single-source, computed, analog)."""
    if entry is None:
        return "gap"
    if mock:
        return "mock"
    if entry.get("evidence_grade") in GRADES:
        return entry["evidence_grade"]
    fam = ((entry.get("prior") or {}).get("family") or "").lower()
    if fam in ("none", "categorical", ""):
        return "gap"
    status = str(entry.get("status", "")).lower()
    if status in GRADES:
        return status
    if status in ("registered", "design-input"):
        return "sourced"
    return "gap"


def _evidence(grades, keys):
    return {k: (grades or {}).get(k, "gap") for k in keys}


# ------------------------------------------------------------------ K2h: hydrolysis descriptor (9a, ruling C1)
def _interval(v, name):
    if v is None:
        return None
    lo, hi = (float(v), float(v)) if np.isscalar(v) else (float(v[0]), float(v[1]))
    if not (lo > 0 and hi >= lo and math.isfinite(hi)):
        raise RouteInputError("%s must be a positive interval (lo <= hi), got %r" % (name, v))
    return lo, hi


def coverage(state, rows, t_tol):
    """(covered, reason, bracketing rows) of a state against the measured rows (claims_redirect.md 9a, I11).

    Covered iff not a drying or pit state, the temperature equals each row's within t_tol, the Ca2+ level is
    bracketed by the with- and without-Ca rows (with Ca2+ present only the Ca rows bracket it), and the pH lies within
    the measured pH set (interpolation between the measured values only). The bracketing rows are those at the
    measured pH values adjacent to (or equal to) the state pH, from the Ca or no-Ca set.
    """
    if state.get("drying") or state.get("pit"):
        return False, "drying and pit states are never covered", []
    if not rows:
        return False, "no measured rate", []
    if t_tol is None:
        return False, "temperature tolerance is a gap", []
    ca = float(state.get("ca_mM", 0.0))
    ca_levels = sorted({float(r["ca_mM"]) for r in rows})
    if ca < ca_levels[0] or ca > ca_levels[-1]:
        return False, "Ca2+ level %g mM outside the measured levels %s" % (ca, ca_levels), []
    use = [r for r in rows if (float(r["ca_mM"]) > 0) == (ca > 0)]
    if not use:
        return False, "no row at the Ca2+ condition of the state", []
    if any(abs(float(state["T"]) - float(r["T"])) > float(t_tol) for r in use):
        return False, "temperature %g K outside the data temperature within %g K" % (float(state["T"]), float(t_tol)), []
    phs = sorted({float(r["pH"]) for r in use})
    ph = float(state["pH"])
    if ph < phs[0] or ph > phs[-1]:
        return False, "pH %g outside the measured pH set %s" % (ph, phs), []
    below = max(p for p in phs if p <= ph)
    above = min(p for p in phs if p >= ph)
    return True, "covered", [r for r in use if float(r["pH"]) in (below, above)]


def hydrolysis_descriptor(state, rows, tau, t_wet, f_min, t_tol, grades=None, route=None):
    """K2h at one state: table H1 to H4 of claims_redirect.md 9a.

    state: {pH, T, ca_mM, drying, pit}. rows: measured rates [{key, pH, ca_mM, T, k: (k_lo, k_hi) plausible range}].
    tau: (tau_lo, tau_hi) transfer factor; t_wet: the route's wet residence time (s); f_min: smallest admissible
    condensed fraction; t_tol: temperature tolerance (K). A missing tau, t_wet or f_min leaves a covered state
    undetermined (named gap). Only H2 gates the row.
    """
    keys = [r["key"] for r in rows or []] + ["hydrolysis_transfer_factor", "hydrolysis_t_wet_%s" % (route or "").lower(),
                                            "hydrolysis_f_min", "hydrolysis_temperature_tolerance"]
    rec = {"test": "K2h", "route": route, "state": dict(state), "evidence": _evidence(grades, keys),
           "gates": False, "rule": "claims_redirect.md 9a, table H1 to H4"}
    covered, why, bracket = coverage(state, rows or [], t_tol)
    rec["coverage"] = {"covered": covered, "reason": why, "rows": [r["key"] for r in bracket]}
    if not covered:
        return dict(rec, row="H1", verdict="undetermined", label=LABELS["H1"])
    tau = _interval(tau, "tau_k")
    missing = [n for n, v in (("hydrolysis_transfer_factor", tau), ("t_wet", t_wet), ("f_min", f_min)) if v is None]
    if missing:
        return dict(rec, row=None, verdict="undetermined", label="covered, but %s is a gap" % ", ".join(missing))
    ks = [_interval(r["k"], r["key"]) for r in bracket]
    k_slow = tau[0] * min(k[0] for k in ks)
    k_fast = tau[1] * max(k[1] for k in ks)
    th_slow, th_fast = math.log(2.0) / k_slow, math.log(2.0) / k_fast
    f_slow = float(hydrolysis.condensed_fraction(t_wet, th_slow))
    f_fast = float(hydrolysis.condensed_fraction(t_wet, th_fast))
    rec.update(k_slow=k_slow, k_fast=k_fast, t_half_slow=th_slow, t_half_fast=th_fast, f_cond_slow=f_slow,
               f_cond_fast=f_fast, t_wet=float(t_wet), f_min=float(f_min))
    if f_slow < f_min:
        return dict(rec, row="H2", verdict="falsified", gates=True, label=LABELS["H2"])
    if f_fast >= f_min:
        return dict(rec, row="H3", verdict="not gating", label=LABELS["H3"])
    return dict(rec, row="H4", verdict="inconclusive", label=LABELS["H4"],
                t_wet_max_slow=float(hydrolysis.wet_time_flip(th_slow, f_min)),
                t_wet_max_fast=float(hydrolysis.wet_time_flip(th_fast, f_min)))


# ------------------------------------------------------------------ K3 route forms (9b, ruling C2)
def _quantiles(x):
    v = np.asarray(x, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return None
    return {"q05": float(np.quantile(v, 0.05)), "median": float(np.median(v)), "q95": float(np.quantile(v, 0.95))}


def r1_at_state(a_Al, a_PP_tot, nu_Al, nu_PP, p_cred, K_sp_AlPP=None, beta_AlPP=None, a_al_state="oxide-equilibrium"):
    """R1 at one labelled a(Al3+) state: table F1r to F4r on per-draw Omega_AlPP (falsifying only).

    a_al_state: 'oxide-equilibrium' (slurry stage) or 'pit-state' (cell stage); the two are never combined.
    beta_AlPP None (a gap): evaluated at beta = 0, the upper bound on a_PP, flagged `complexation gap`; a falsification
    there stands and a not-excluded there is labelled optimistic. K_sp_AlPP None (a gap): F1r with the flip value.
    """
    if a_al_state not in ("oxide-equilibrium", "pit-state"):
        raise RouteInputError("a(Al3+) state must be oxide-equilibrium or pit-state, got %r" % a_al_state)
    flags = []
    beta = beta_AlPP
    if beta is None:
        beta = 0.0
        flags.append("complexation gap")
    a_pp = gelation.free_chain_unit_activity(a_PP_tot, beta, a_Al)
    iap = np.asarray(gelation.ion_activity_product_alpp(a_Al, a_pp, nu_Al, nu_PP), dtype=float)
    rec = {"a_Al_state": a_al_state, "flags": flags, "IAP_AlPP": _quantiles(iap)}
    if K_sp_AlPP is None:
        return dict(rec, row="F1r", verdict="undetermined", label=LABELS["F1r"], flip_K_sp=_quantiles(iap))
    om = np.asarray(gelation.saturation_ratio_alpp(a_Al, a_pp, nu_Al, nu_PP, K_sp_AlPP), dtype=float)
    below = decision.mass_of(decision.indicator(om, "<", 1.0))
    above = decision.mass_of(decision.indicator(om, ">", 1.0))
    rec.update(Omega_AlPP=_quantiles(om), P_below=below["P_good"], P_above=above["P_good"], n_used=below["n_used"])
    if below["P_good"] is not None and below["P_good"] >= p_cred:
        return dict(rec, row="F2r", verdict="falsified", label=LABELS["F2r"])
    if above["P_good"] is not None and above["P_good"] >= p_cred:
        label = LABELS["F3r"] + (" (optimistic: complexation gap)" if "complexation gap" in flags else "")
        return dict(rec, row="F3r", verdict="not excluded", label=label)
    return dict(rec, row="F4r", verdict="inconclusive", label=LABELS["F4r"])


def r2_at_state(state_draws, binodal_map, p_cred):
    """R2 at one state: table B1 to B4 against the coacervate binodal map.

    state_draws: {Ca_T, P_T, pH, I} arrays (or scalars) of the slurry state. binodal_map: None (a gap) or
    {covered: {var: [lo, hi]}, two_phase: {var: [lo, hi]}} in the units of the state. The state is covered only if
    every draw lies in the covered region (a partly covered state is B1: the map does not decide it).
    """
    if not binodal_map:
        return {"row": "B1", "verdict": "undetermined", "label": LABELS["B1"] + " (coacervate_binodal_map is a gap)"}
    cov, two = binodal_map.get("covered") or {}, binodal_map.get("two_phase") or {}
    n = max(np.size(v) for v in state_draws.values())
    inside_cov = np.ones(n, dtype=bool)
    for var, (lo, hi) in cov.items():
        x = np.broadcast_to(np.asarray(state_draws[var], dtype=float), (n,))
        inside_cov &= (x >= lo) & (x <= hi)
    if not np.all(inside_cov):
        return {"row": "B1", "verdict": "undetermined", "label": LABELS["B1"],
                "fraction_covered": float(inside_cov.mean())}
    inside = np.ones(n, dtype=bool)
    for var, (lo, hi) in two.items():
        x = np.broadcast_to(np.asarray(state_draws[var], dtype=float), (n,))
        inside &= (x >= lo) & (x <= hi)
    p_in = float(inside.mean())
    rec = {"P_two_phase": p_in, "n_used": int(n)}
    if 1.0 - p_in >= p_cred:
        return dict(rec, row="B2", verdict="falsified", label=LABELS["B2"])
    if p_in >= p_cred:
        return dict(rec, row="B3", verdict="not excluded", label=LABELS["B3"])
    return dict(rec, row="B4", verdict="inconclusive", label=LABELS["B4"])


def formation_accessibility(route, p_cred, grades=None, r1=None, r2=None):
    """K3 route form of one route at one slurry state.

    R1: r1 = {"states": {label: {a_Al, a_PP_tot, nu_Al, nu_PP, K_sp_AlPP, beta_AlPP}}} with labels oxide-equilibrium
    and/or pit-state; each labelled state is evaluated and printed on its own (never combined). The row's K3 verdict
    is the oxide-equilibrium one (the slurry stage); the pit state is printed beside it. R2: r2 = {state, map}.
    R3: no formation criterion (decided by K2h and the K1 amorphous row).
    """
    if route not in ROUTES:
        raise RouteInputError("route must be one of %s, got %r" % (ROUTES, route))
    rule = "claims_redirect.md 9b"
    if route == "R3":
        return {"test": "K3", "route": "R3", "verdict": "not applicable", "rule": rule, "evidence": {},
                "label": "R3 has no formation criterion: decided by K2h and the K1 amorphous row"}
    if route == "R1":
        if not r1 or not r1.get("states"):
            raise RouteInputError("R1 needs at least one labelled a(Al3+) state")
        per = {lab: r1_at_state(p_cred=p_cred, a_al_state=lab, **s) for lab, s in r1["states"].items()}
        gov = per.get("oxide-equilibrium") or next(iter(per.values()))
        keys = ["polyp_log10_ksp_al", "polyp_al_log_k_oxide", "polyp_al_activity_pit", "polyp_al_log_beta1_linear"]
        return {"test": "K3", "route": "R1", "verdict": gov["verdict"], "row": gov["row"], "label": gov["label"],
                "by_a_Al_state": per, "governing_state": gov["a_Al_state"], "falsifying_only": True,
                "hypothesis": KINETIC_HYPOTHESIS, "evidence": _evidence(grades, keys), "rule": rule + ", table F1r to F4r"}
    r = r2_at_state(r2["state"], r2.get("map"), p_cred)
    return dict(r, test="K3", route="R2", evidence=_evidence(grades, ["coacervate_binodal_map"]),
                rule=rule + ", table B1 to B4")


# ------------------------------------------------------------------ K4 route form (9c, ruling C3)
def liquid_precursor_wetting(p_cred, m_S, gamma_al_l0=None, gamma_al_n0=None, gamma_nl_c=None, cos_theta_meas=None,
                             site=None, closure_good=None, grades=None):
    """K4 route form of the coacervate (R2): S_coac = Dgamma - gamma_nl >= m_S, with both gamma_nl limits.

    Dgamma = gamma_sl0 - gamma_sn0, the site-free contact difference (the adsorption terms cancel at coexistence); or
    gamma_nl cos(theta) from a measured contact angle. Neither available: undetermined, flip value Dgamma* = gamma_nl + m_S.
    site: {T, Gamma_P, K_P, a_P, delta_P, Pi_osm} for the admissibility rule (gamma_sl >= 0 and gamma_sn >= 0, each with
    its adsorption term, before the difference; refused draws counted, M_adm printed). gamma_nl_c None: only the
    negligible-gamma_nl limit is evaluated and labelled. closure_good: per-draw closure indicator (the alternative
    route); without it a falsification cannot be stated. theta < pi/2 is reported, never gating.
    """
    keys = ["coacervate_gamma_s0_dilute", "coacervate_gamma_s0_dense", "coacervate_gamma_nl",
            "coacervate_contact_angle_alumina", "polyp_ads_alumina_gamma_max", "polyp_ads_alumina_k_langmuir",
            "polyp_ads_alumina_layer_thickness"]
    rec = {"test": "K4", "route": "R2", "evidence": _evidence(grades, keys), "m_S": m_S,
           "rule": "claims_redirect.md 9c: S_coac >= m_S OR closure; falsified only if both fail on the same draw",
           "notes": ["neutral-solute machinery: the double-layer term does not cancel and is unmodelled (stated limitation)"]}
    adm = None
    if cos_theta_meas is not None and gamma_nl_c is not None:
        dg = np.asarray(gamma_nl_c, dtype=float) * np.asarray(cos_theta_meas, dtype=float)
        rec["Dgamma_source"] = "measured contact angle x gamma_nl"
    elif gamma_al_l0 is not None and gamma_al_n0 is not None:
        dg = np.asarray(coacervate.dense_phase_preference(gamma_al_l0, gamma_al_n0), dtype=float)
        rec["Dgamma_source"] = "site-free contact difference"
        if site is not None:
            gl = np.asarray(coacervate.substrate_dilute_energy(gamma_al_l0, **site), dtype=float)
            gn = np.asarray(coacervate.substrate_dense_energy(gamma_al_n0, **site), dtype=float)
            ok = (gl >= 0) & (gn >= 0)
            adm = {"M_adm": float(np.mean(ok)), "n_evaluable": int(ok.size), "n_refused": int((~ok).sum()),
                   "inadmissible_inputs": bool(1.0 - float(np.mean(ok)) >= p_cred),
                   "label": "conditional on admissibility (M_adm printed beside)",
                   "rule": "gamma_sl >= 0 and gamma_sn >= 0 with their adsorption terms (D27 form)"}
            dg = np.where(ok, dg, np.nan)
    else:
        flip = None if gamma_nl_c is None else _quantiles(np.asarray(gamma_nl_c, dtype=float) + m_S)
        return dict(rec, verdict="undetermined", retained_mass=None,
                    label="site-free contact difference is a gap and no contact angle exists",
                    flip_Dgamma=flip if flip is not None else "gamma_nl + m_S (gamma_nl is a gap)")
    rec["Dgamma"] = _quantiles(dg)
    rec["retained_mass"] = adm
    # limit gamma_nl negligible: S -> Dgamma; Dgamma = 0 is decided by gamma_nl (inconclusive)
    s0 = decision.indicator(dg, ">=", m_S)
    lim0 = decision.mass_of(s0)
    rec["limit_gamma_nl_negligible"] = {"P_good": lim0["P_good"], "P_Dgamma_positive":
                                        decision.mass_of(decision.indicator(dg, ">", 0.0))["P_good"]}
    if gamma_nl_c is None:
        s = dg
        rec["limit_used"] = "gamma_nl negligible (ruling C3; coacervate_gamma_nl is a gap)"
    else:
        gnl = np.asarray(gamma_nl_c, dtype=float)
        s = np.asarray(coacervate.spreading_coefficient(np.where(np.isfinite(dg), dg, 0.0), 0.0, gnl), dtype=float)
        s = np.where(np.isfinite(dg), s, np.nan)
        with np.errstate(invalid="ignore", divide="ignore"):
            c = dg / gnl
        fin = np.isfinite(c)
        rec["limit_used"] = "gamma_nl as sampled (comparable limit)"
        rec["branches"] = {"complete_wetting": float(np.mean(c[fin] >= 1)) if fin.any() else None,
                           "partial_theta_below_pi_2": float(np.mean((c[fin] > 0) & (c[fin] < 1))) if fin.any() else None,
                           "non_wetting": float(np.mean(c[fin] <= 0)) if fin.any() else None,
                           "note": "theta < pi/2 alone is reported, not gating"}
        rec["S_coac"] = _quantiles(s)
    spread = decision.indicator(s, ">=", m_S)
    if closure_good is None:
        route = spread
        rec["notes"].append("closure route not evaluated for the coacervate: a falsification cannot be stated")
    else:
        cl = np.asarray(closure_good, dtype=float)
        route = np.where(np.isfinite(spread), np.where(np.isfinite(cl), np.maximum(spread, cl), spread), np.nan)
    m = decision.mass_of(route)
    verdict = decision.verdict_from_mass(m["P_good"], p_cred)
    if verdict == "falsified" and closure_good is None:
        verdict = "inconclusive"
    if adm is not None and adm["inadmissible_inputs"] and verdict != "inconclusive":
        rec["verdict_restricted"] = verdict
        verdict = "inconclusive"
        rec["notes"].append("inadmissible inputs: 1 - M_adm >= p_cred")
    return dict(rec, verdict=verdict, P_good=m["P_good"], P_bad=m["P_bad"], n_used=m["n_used"],
                P_spread=decision.mass_of(spread)["P_good"],
                design_result="spreading coefficient of the coacervate on alumina (reported with its flip value)",
                flip_Dgamma=_quantiles(np.asarray(gamma_nl_c, dtype=float) + m_S) if gamma_nl_c is not None else m_S)


# ------------------------------------------------------------------ framings of the route products (9d, ruling C4)
def route_framing(crystalline, amorphous, baked=False):
    """Governing verdict of a route product from its crystalline and amorphous verdicts.

    In-situ routes: the amorphous framing governs; the crystalline one is the optimistic upper reference. Crystalline
    pass with amorphous fail is labelled `requires crystallisation` (a label, not a verdict). Baked baselines: both
    reported, neither governs, `structure unspecified`.
    """
    labels = []
    if baked:
        return {"verdict": None, "governing_framing": None, "by_framing": {"crystalline": crystalline,
                "amorphous": amorphous}, "labels": ["structure unspecified"]}
    if crystalline == "feasible" and amorphous == "falsified":
        labels.append("requires crystallisation")
    if crystalline == "falsified" and amorphous == "falsified":
        labels.append("falsified under the governing framing")
    return {"verdict": amorphous, "governing_framing": "amorphous",
            "by_framing": {"crystalline": crystalline, "amorphous": amorphous}, "labels": labels,
            "note": "the crystalline framing is an optimistic upper reference"}


# ------------------------------------------------------------------ matrix and baseline rules (9e, rulings C5, C6)
def matrix_entry(rung, records, E_c, m_svc, thermal_budget=False):
    """Matrix K1 entry of one organic rung (table M1 to M4). Never gates; never changes the mineral's verdict.

    records: tier-2 records [{class: A|B|C, E_svc}] (empty: a gap). The matrix has no tier 1.
    """
    ab = [r for r in records or [] if r.get("class") in ("A", "B")]
    out = {"rung": rung, "gates": False, "tier1": "none (organic polymer: no meaningful thermodynamic onset)"}
    if ab:
        low = min(ab, key=lambda r: r["E_svc"])
        if low["E_svc"] < E_c - m_svc:
            out.update(row="M1", ceiling=low["E_svc"], label="matrix ceiling, class %s" % low["class"])
        else:
            out.update(row="M2", ceiling=None, label="no ceiling from the matrix (class A or B at or above the cutoff)")
    else:
        out.update(row="M3", ceiling=None, label="matrix-risk flag (class C only, or no record)")
    if thermal_budget:
        out["variants"] = ["with matrix", "without matrix"]
        out["row_thermal"] = "M4"
    if rung == "pda":
        out["stated_risk"] = "polydopamine carries the stated K1 risk (contrary B4)"
    return out


def baseline_k2(baseline, solubility=None, hydro_quebec=False, grade=None):
    """K2 of a baseline row (table L1 to L3): a literature solubility for the COMPOSITION, else undetermined."""
    if solubility is not None:
        return {"test": "K2", "row": "L1", "verdict": solubility["verdict"], "label": "composition-based",
                "evidence": {"composition_solubility": grade or "sourced"}, "baseline": baseline}
    rec = {"test": "K2", "row": "L2", "verdict": "undetermined", "label": "no film solubility for the composition",
           "evidence": {"composition_solubility": "gap"}, "baseline": baseline}
    if hydro_quebec:
        rec.update(row="L3", label="inference from chemistry (water-soluble Li polyphosphate); never a patent statement")
    return rec


# ------------------------------------------------------------------ thresholds structure (9f; numbers at PH-W3.2)
THRESHOLDS_STRUCTURE = {
    "K2": {"edge": "Omega >= 1 per framing", "governing": "amorphous for the route products", "margin": None},
    "K2h": {"table": "H1 to H4", "edge": "f_cond >= f_min", "margin": "none beyond tau_k (the transfer range)",
            "keys": ["hydrolysis_f_min", "hydrolysis_transfer_factor"]},
    "K3_R1": {"table": "F1r to F4r", "edge": "Omega_AlPP against 1, falsifying side only", "margin": "p_cred"},
    "K3_R2": {"table": "B1 to B4", "edge": "two-phase region of the binodal map", "margin": "p_cred"},
    "K4_route": {"edge": "S_coac >= m_S", "alternative": "closure route (3c); falsified only if both fail on one draw",
                 "margin": "m_S"},
    "K1_amorphous": {"edges": ["E_lb_glass >= E_c + m_1", "E_ub_glass < E_c - m_1"], "margins": ["m_1", "m_svc"]},
}


def thresholds_ph(k_cfg):
    """The 9f structure with each margin slot resolved from the provisional k_screen block, or 'pending'."""
    out = {}
    for test, spec in THRESHOLDS_STRUCTURE.items():
        s = dict(spec)
        slots = {}
        for m in ("m_S", "m_1", "m_svc", "p_cred"):
            if m in str(spec):
                slots[m] = (k_cfg or {}).get(m, "pending")
        s["slots"] = slots
        out[test] = s
    out["provisional"] = True
    return out


ROUTE_EVALUATORS = {"liquid_precursor_wetting": liquid_precursor_wetting,
                    "formation_accessibility": formation_accessibility,
                    "hydrolysis_descriptor": hydrolysis_descriptor}


def pending_for(mineral):
    """The route evaluators a mineral's rows use (empty for a solid-like nucleus). All three are implemented
    (PH-W4.2a); the list names which ones apply, beside every result."""
    out = []
    if mineral.phase_state == "liquid_precursor":
        out += ["liquid_precursor_wetting", "formation_accessibility"]
    if mineral.chain_length_n is not None:
        if "formation_accessibility" not in out:
            out.append("formation_accessibility")
        out.append("hydrolysis_descriptor")
    return out
