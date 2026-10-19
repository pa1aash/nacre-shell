"""Admissibility of the template-liquid energy in the decision layer (decision D27; gap table AM3).

theory/thresholds.md block v4, decision.admissibility: the joint prior of (gamma_sl0, Delta_G_seq,
Gamma_s, delta_s) is restricted to gamma_sl_insitu = gamma_sl0 + Delta_gamma_ads >= 0 at every
registered R-slurry state of a design point. The states share their draws (common random numbers),
so a draw is admitted only if the condition holds at every state: the same film meets all of them.
Draws outside the set are refused and counted, never clipped and never floored at zero.

  M_adm        fraction of the evaluable draws that are admitted (joint over the states), also per
               state; a property of the prior, printed beside every verdict that uses gamma_sl
               (C3, C4, the deletion test) and never renormalised silently;
  verdicts     C3 and C4 on the admitted draws, labelled "conditional on admissibility";
  inadmissible 1 - M_adm >= p_cred: the link verdict is inconclusive ("inadmissible inputs") with
               the restricted verdict printed beside it (a statement about the inputs);
  reported     P(gamma_sl_floor >= 0), the r_ads quantiles over the admitted draws, the unrestricted
               verdict on the same draws (a labelled sensitivity, never a verdict) and whether it differs;
  sizing       (gap table AM4) every mass that decides a verdict is sized: M_adm, which decides the
               inadmissible-inputs test, enters the sizing rule with its half-width on the evaluable
               draws; the restricted band masses enter it on the admitted draws, except where the inputs
               are inadmissible, where they decide nothing and are printed unsized (half_width_unsized).

A surface supplied at the regime activities (the bare-oxide control) has gamma_sl >= 0 by its bound;
its M_adm = 1 is computed, not assumed.
"""
import numpy as np

QUANTITY = "gamma_sl_insitu"
LABEL = "conditional on admissibility (gamma_sl_insitu >= 0 at every registered state; D27)"
LEVELS = (0.05, 0.5, 0.95)
SENSITIVITY_NOTE = ("nucleate link on the admitted draws (gamma_sl_insitu >= 0 at the analysed state; AM3): the "
                    "restriction makes (gamma_sl0, Delta_G_seq, Gamma_s, delta_s) dependent (lane note N2); the Shapley "
                    "double loop samples the restricted conditionals by rejection and carries the ranking; the Sobol "
                    "indices of independent marginals over the admitted draws are approximate")


def _q(v, levels=LEVELS):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    if not v.size:
        return None
    return {"q%02d" % round(100 * lv): float(np.quantile(v, lv)) for lv in levels}


def _mean(v):
    v = np.asarray(v, dtype=float)
    v = v[np.isfinite(v)]
    return float(v.mean()) if v.size else None


def mask(states):
    """Admissibility over the registered states ({state: samples}); None without gamma_sl.

    Returns {"admitted", "evaluable", "by_state": {state: (evaluable, ok)}, "coupled"}. When the
    states do not share their draws the condition can only be applied state by state (recorded).
    """
    arrays = {sid: np.asarray(s[QUANTITY], dtype=float) for sid, s in states.items() if QUANTITY in s}
    if not arrays:
        return None
    by_state = {sid: (np.isfinite(a), np.isfinite(a) & (a >= 0)) for sid, a in arrays.items()}
    coupled = len({a.shape for a in arrays.values()}) == 1
    if coupled:
        evaluable = np.all(np.vstack([e for e, _ in by_state.values()]), axis=0)
        admitted = evaluable & np.all(np.vstack([ok for _, ok in by_state.values()]), axis=0)
    else:
        evaluable = admitted = None
    return {"admitted": admitted, "evaluable": evaluable, "by_state": by_state, "coupled": coupled}


def restrict(states, m):
    """The samples with every refused draw set to NaN (the decision layer excludes NaN draws)."""
    out = {}
    for sid, s in states.items():
        keep = m["admitted"] if m["coupled"] else m["by_state"].get(sid, (None, None))[1]
        if keep is None:
            out[sid] = s
            continue
        out[sid] = {q: (np.where(keep, np.asarray(v, dtype=float), np.nan)
                        if np.shape(v) == keep.shape else v) for q, v in s.items()}
    return out


def _m_adm(evaluable, admitted):
    n = int(np.sum(evaluable))
    return (float(np.sum(admitted) / n) if n else None), n, int(n - np.sum(admitted))


def summary(states, m, p):
    """The retained-mass record of one (design point, framing) and its reported quantities."""
    by_state = {}
    for sid, (ev, ok) in m["by_state"].items():
        s = states[sid]
        mass, n, refused = _m_adm(ev, ok)
        rec = {"M_adm": mass, "n_evaluable": n, "n_refused": refused}
        if "gamma_sl_floor" in s:
            fl = np.asarray(s["gamma_sl_floor"], dtype=float)
            fin = np.isfinite(fl)
            rec["P_gamma_sl_floor_ge_0"] = float(np.mean(fl[fin] >= 0)) if fin.any() else None
        if "r_ads" in s:
            rec["r_ads_admitted"] = _q(np.asarray(s["r_ads"], dtype=float)[ok])
        rec["gamma_sl_admitted"] = _q(np.asarray(s[QUANTITY], dtype=float)[ok])
        rec["gamma_sl_all"] = _q(s[QUANTITY])
        if "branch_favourable" in s:
            # mass of gamma_sn <= gamma_sl under the gamma_sn ignorance prior (ignorance_priors.md 2a, m_cos = 0)
            rec["P_gamma_sn_le_gamma_sl_admitted"] = _mean(np.asarray(s["branch_favourable"], dtype=float)[ok])
        if "gamma_sl_minus_nl" in s:
            d = np.asarray(s["gamma_sl_minus_nl"], dtype=float)[ok]
            d = d[np.isfinite(d)]
            rec["P_gamma_sl_gt_gamma_nl_admitted"] = float(np.mean(d > 0)) if d.size else None
        by_state[sid] = rec
    if m["coupled"]:
        mass, n, refused = _m_adm(m["evaluable"], m["admitted"])
        note = "joint over the registered states (common random numbers)"
    else:
        ms = [r["M_adm"] for r in by_state.values() if r["M_adm"] is not None]
        mass, n, refused = (min(ms) if ms else None), None, None
        note = "states do not share their draws: the condition is applied state by state; M_adm is the smallest"
    inadmissible = mass is not None and (1.0 - mass) >= p
    hw = float(2.0 * np.sqrt(mass * (1.0 - mass) / n)) if mass is not None and n else None
    return {"label": LABEL, "M_adm": mass, "half_width": hw, "n_evaluable": n, "n_refused": refused, "by_state": by_state,
            "inadmissible_inputs": bool(inadmissible), "rule": "1 - M_adm >= p_cred: inconclusive (inadmissible inputs)",
            "p_cred": float(p), "note": note}


def _unsized(record):
    """The record with every half_width renamed half_width_unsized (printed, not entering the sizing rule)."""
    if isinstance(record, dict):
        return {("half_width_unsized" if k == "half_width" else k): _unsized(v) for k, v in record.items()}
    if isinstance(record, list):
        return [_unsized(v) for v in record]
    return record


def apply(restricted_record, unrestricted_record, adm):
    """The link record under the rule: the restricted verdict, or inconclusive for inadmissible inputs."""
    rec = dict(restricted_record)
    v_r, v_u = restricted_record["verdict"], unrestricted_record["verdict"]
    block = dict(adm, verdict_restricted=v_r, verdict_unrestricted=v_u,
                 unrestricted={"label": "unrestricted joint prior on the same draws (labelled sensitivity, never a verdict)",
                               "verdict": v_u, "P_good": unrestricted_record.get("P_good"),
                               "P_bad": unrestricted_record.get("P_bad"),
                               "falsified_mass": unrestricted_record.get("falsified_mass")})
    if adm["inadmissible_inputs"]:
        rec = _unsized(rec)
        rec["verdict"] = "inconclusive"
        rec["falsified_mass"] = None          # a mass computed from the admissible remainder is not credited
        rec["notes"] = list(rec.get("notes") or []) + [
            "inadmissible inputs: 1 - M_adm = %.4g >= p_cred = %.4g; the restricted verdict (%s) is printed beside"
            % (1.0 - adm["M_adm"], adm["p_cred"], v_r)]
    block["verdict"] = rec["verdict"]
    block["differs_from_unrestricted"] = rec["verdict"] != v_u
    rec["admissibility"] = block
    rec["_unrestricted"] = unrestricted_record
    return rec


def descriptor(states, m):
    """C2 (a descriptor on the joint prior as registered): its quantities over the admitted draws beside."""
    out = {}
    for sid, s in states.items():
        ok = m["admitted"] if m["coupled"] else m["by_state"].get(sid, (None, None))[1]
        if ok is None or "Delta_G_seq" not in s:
            continue
        dg = np.asarray(s["Delta_G_seq"], dtype=float)
        out[sid] = {"Delta_G_seq_all": _q(dg), "Delta_G_seq_admitted": _q(dg[ok]),
                    "Delta_G_seq_refused": _q(dg[~ok & np.isfinite(dg)])}
    return {"label": "C2 stays on the joint prior as registered; quantiles over the admitted and refused draws beside",
            "by_state": out}


def mechanism(states, m):
    """Admitted versus refused draws: what the rule removes (report-only diagnostic)."""
    out = {}
    for sid, s in states.items():
        if QUANTITY not in s:
            continue
        ev, ok = m["by_state"][sid]
        joint = m["admitted"] if m["coupled"] else ok
        sl = np.asarray(s[QUANTITY], dtype=float)
        rec = {}
        sel = {"admitted": joint, "refused": ev & ~joint}
        pi = np.asarray(s["Pi_ads"], dtype=float) if "Pi_ads" in s else None
        for name, k in sel.items():
            r = {"n": int(np.sum(k)), "gamma_sl": _q(sl[k])}
            if pi is not None:
                r["Pi_ads"] = _q(pi[k])
                r["gamma_sl0"] = _q((sl + pi)[k])
            for q in ("Delta_G_seq", "gamma_sl_floor", "r_ads", "Theta_occ"):
                if q in s:
                    r[q] = _q(np.asarray(s[q], dtype=float)[k])
            rec[name] = r
        out[sid] = rec
    return out
