"""Evaluators K1 to K4 for solid-like nuclei, as registered in theory/claims_redirect.md (PH-W4.1).

K1 is READ from W5's ladder file (results/preprint/pourbaix/ph_k1/ladder.csv); it is never recomputed here.
K2, K3 and K4 are evaluated on the draws of the screen chain (nacre.screen.chain with a Mineral object):

    K2  Omega_bulk >= 1                     worst registered state, shared band-mass rule at p_cred
    K3  accessible dose window              DG_het(D) <= B_acc and DG_hom(D) > B_acc, with C3a: cos(theta) >= m_cos;
                                            the dose where bulk precipitation takes over is stated with every row
    K4  S_spread >= m_S OR closure          closure: N_nuc >= tan^2(theta/2)/(2 d_max^2); falsified only if both fail
                                            on the same draw

Rules shared with the carbonate links (nacre.screen.decision): the band-mass verdict at p_cred, the worst-state
combination, the framing rule (falsified only under every framing, feasible under at least one, named), and the
admissibility restriction (D27: gamma_sl_insitu >= 0 at every registered state; refused draws counted, never
clipped; the retained mass M_adm printed beside every verdict that uses gamma_sl). The deletion test applies to
K3 and K4 only; a pass that does not degrade without the template is labelled ``generic``.

Margins and decision constants come from configs/preprint/screen.yaml, block ``k_screen``, whose values are
PROVISIONAL placeholders (PH-W3.2 sets the numbers; they are frozen at cp5). Nothing here sets a prior, a
threshold or a verdict rule.

K3 and K4 run only for a phase that passes K1 at some registered cutoff class (claims_redirect.md 2d). The route
layer (liquid precursor, in-situ formation, hydrolysis) is not evaluated here: its evaluators are the named
extension points of nacre.screen.routes, which raise NotImplementedError.
"""
import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from nacre.screen import admissibility, decision, routes

LADDER = Path("results") / "preprint" / "pourbaix" / "ph_k1" / "ladder.csv"
FRAMINGS = ("crystalline", "amorphous")
STATES_OF_K1 = ("feasible", "falsified", "inconclusive")
REQUIRED_COLUMNS = ("phase", "class", "status", "note")


class K1Error(ValueError):
    """The K1 ladder file does not have the registered layout."""


class KConfigError(ValueError):
    """configs/preprint/screen.yaml k_screen is missing or incomplete."""


# ------------------------------------------------------------------ configuration
def k_config(cfg):
    """The k_screen block of screen.yaml; refuses a block that does not mark itself provisional."""
    block = (cfg or {}).get("k_screen")
    if not isinstance(block, dict):
        raise KConfigError("configs/preprint/screen.yaml has no k_screen block")
    if block.get("provisional") is not True:
        raise KConfigError("k_screen must be marked provisional: true until the cp5 freeze")
    for key in ("p_cred", "p_deg", "m_cos", "m_S", "ln_dose_axis"):
        if key not in block:
            raise KConfigError("k_screen.%s is required" % key)
    if not 0.5 < float(block["p_cred"]) < 1:
        raise KConfigError("k_screen.p_cred must lie in (1/2, 1)")
    return block


# ------------------------------------------------------------------ K1: read, never recomputed
def k1_verdict(status, note):
    """K1 verdict of one ladder row at its cutoff class (claims_redirect.md 2c).

    'below' falsifies at tier 1. 'above' passes only when the row does not say it is an upper bound (the
    solid-salt sink bounds the onset from above: a falsification stands, a pass is inconclusive). Every other
    status (within budget, undetermined) is inconclusive: undetermined never passes.
    """
    s = (status or "").strip().lower()
    if s == "below":
        return "falsified"
    if s == "above":
        n = (note or "").lower()
        return "inconclusive" if ("upper bound" in n or "not a pass" in n) else "feasible"
    return "inconclusive"


@dataclass(frozen=True)
class K1Row:
    phase: str
    role: str
    cls: str
    framing: str
    onset_V: object
    status: str
    note: str
    verdict: str


class K1Table:
    """The ladder rows by (phase, cutoff class, framing); at most two rows (framings) per phase and class."""

    def __init__(self, rows, path=""):
        self.rows = {}
        self.path = str(path)
        for r in rows:
            key = (r.phase, r.cls, r.framing)
            if key in self.rows:
                raise K1Error("%s: two rows for phase %r, class %r and framing %r" % (path, *key))
            self.rows[key] = r
        for (phase, cls), n in _counts(self.rows).items():
            if n > len(FRAMINGS):
                raise K1Error("%s: %d rows for phase %r and class %r (at most %d, one per framing)"
                              % (path, n, phase, cls, len(FRAMINGS)))

    def phases(self):
        return sorted({k[0] for k in self.rows})

    def classes(self, phase):
        seen = []
        for (p, c, _), _r in self.rows.items():
            if p == phase and c not in seen:
                seen.append(c)
        return seen

    def framings(self, phase):
        return sorted({f for (p, _, f) in self.rows if p == phase})

    def verdicts(self, phase, framing):
        """{cutoff class: K1 verdict} of one phase and framing; empty when the ladder has no such row."""
        return {c: self.rows[(phase, c, framing)].verdict for c in self.classes(phase) if (phase, c, framing) in self.rows}

    def passing_classes(self, phase, framing):
        return [c for c, v in self.verdicts(phase, framing).items() if v == "feasible"]


def _counts(rows):
    out = {}
    for phase, cls, _ in rows:
        out[(phase, cls)] = out.get((phase, cls), 0) + 1
    return out


def read_k1(path):
    """Read W5's ladder. Comment lines start with '#'. A ``framing`` column (crystalline or amorphous) selects
    the framing of a row and defaults to crystalline; two rows per phase and class are accepted, one per framing."""
    path = Path(path)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]
    reader = csv.DictReader(lines)
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise K1Error("%s: ladder columns missing: %s" % (path, missing))
    rows = []
    for rec in reader:
        framing = (rec.get("framing") or "crystalline").strip() or "crystalline"
        if framing not in FRAMINGS:
            raise K1Error("%s: framing %r of phase %r is not one of %s" % (path, framing, rec["phase"], FRAMINGS))
        rows.append(K1Row(rec["phase"], rec.get("role", ""), rec["class"], framing, rec.get("tier1_onset_V", ""),
                          rec["status"], rec["note"], k1_verdict(rec["status"], rec["note"])))
    return K1Table(rows, path)


def mineral_framing(mineral):
    """The ladder framing of a mineral's phase state; None for a liquid precursor (the ladder has no such row)."""
    return {"crystalline": "crystalline", "amorphous": "amorphous"}.get(mineral.phase_state)


def k1_for(table, mineral):
    """K1 record of a mineral from the ladder: verdicts per cutoff class and the classes it passes at."""
    phase = mineral.k1_phase or mineral.name
    framing = mineral_framing(mineral)
    verdicts = table.verdicts(phase, framing) if framing else {}
    passing = [c for c, v in verdicts.items() if v == "feasible"]
    note = None
    if not verdicts:
        note = "no K1 row for phase %r, framing %r: K1 undetermined" % (phase, framing)
    return {"phase": phase, "framing": framing, "by_class": verdicts, "passes_at": passing,
            "source": table.path, "note": note,
            "label": "tier 1 read from the ladder file; not recomputed"}


def proceeds(k1, override=False):
    """Does the phase go on to K3 and K4? Only if K1 passes at any registered class (2d); a dry run may override."""
    if k1["passes_at"]:
        return {"proceeds": True, "classes": list(k1["passes_at"]), "overridden": False}
    if override:
        return {"proceeds": True, "classes": [], "overridden": True,
                "note": "K1 gate overridden: dry run only, never reported"}
    return {"proceeds": False, "classes": [], "overridden": False,
            "note": "K1 does not pass at any registered cutoff class: K3 and K4 are not run"}


# ------------------------------------------------------------------ samples
def samples(outputs):
    """Decision samples of one (dose, state) from the chain outputs {link: {quantity: array}}."""
    s = {}
    nuc = outputs.get("nucleate") or {}
    for q in ("Omega_bulk", "f_theta", "cos_theta", "barrier_hom_bulk_kT", "barrier_het_template_kT", "B_acc_kT",
              "N_nuc", "S_spread", "gamma_sl_insitu", "Pi_ads", "gamma_sl_floor", "r_ads", "gamma_sl_minus_nl",
              "branch_favourable"):
        if q in nuc:
            s[q] = np.asarray(nuc[q], dtype=float)
    if "Omega_bulk" not in s and "Omega_bulk" in (outputs.get("speciation") or {}):
        s["Omega_bulk"] = np.asarray(outputs["speciation"]["Omega_bulk"], dtype=float)
    return s


def _mass(good):
    m = decision.mass_of(good)
    return m, decision.half_width(m["P_good"], m["n_used"])


def _verdict_record(good, p, **extra):
    m, hw = _mass(good)
    return {**m, "half_width": hw, "verdict": decision.verdict_from_mass(m["P_good"], p), **extra}


def _worst_over_states(per_state):
    return decision.worst([r["verdict"] for r in per_state.values()])


# ------------------------------------------------------------------ K2
def k2_at_dose(states, p_cred):
    """K2 at one dose: Omega_bulk >= 1 at every registered state (a pass needs every state; a falsification stands).

    states: {state: {"Omega_bulk": draws}} sharing their draws.
    """
    per = {}
    for sid, s in states.items():
        if "Omega_bulk" not in s:
            continue
        good = decision.indicator(s["Omega_bulk"], ">=", 1.0)
        per[sid] = _verdict_record(good, p_cred, _good=good)
    if not per:
        return None
    joint = np.vstack([r["_good"] for r in per.values()])
    both = np.where(np.all(np.isfinite(joint), axis=0), np.min(joint, axis=0), np.nan)
    j = _verdict_record(both, p_cred)
    verdict = j["verdict"]
    if any(r["verdict"] == "falsified" for r in per.values()):
        verdict = "falsified"
    elif verdict == "feasible" and not all(r["verdict"] == "feasible" for r in per.values()):
        verdict = "inconclusive"
    return {"verdict": verdict, "P_good": j["P_good"], "P_bad": j["P_bad"], "joint": j,
            "by_state": decision.public(per)}


def k2(states_by_dose, p_cred, controls=None):
    """K2 over the dose axis: Omega_bulk >= 1 (insoluble at the processing state), from sourced K_sp and speciation.

    The dose window of K2 is the set of doses where Omega_bulk >= 1 (claims_redirect.md 3a). feasible: some dose
    is feasible; falsified: every dose is falsified; inconclusive otherwise. controls: optional
    {"undersaturated": draws, "supersaturated": draws}: the first must report dissolution and the second stability,
    else K2 is inconclusive.
    """
    points = {d: r for d, r in ((d, k2_at_dose(st, p_cred)) for d, st in states_by_dose.items()) if r is not None}
    if not points:
        return {"verdict": "inconclusive", "gap": "no state supplies Omega_bulk", "points": {}}
    sets = {v: sorted(d for d, r in points.items() if r["verdict"] == v) for v in decision.ORDER}
    if sets["feasible"]:
        verdict = "feasible"
    elif len(sets["falsified"]) == len(points):
        verdict = "falsified"
    else:
        verdict = "inconclusive"
    ctl = {}
    for k, vals in (controls or {}).items():
        rec = _verdict_record(decision.indicator(vals, ">=", 1.0), p_cred)
        ctl[k] = dict(rec, must=decision.CONTROL_MUST[k], fails_where_it_must=rec["verdict"] == decision.CONTROL_MUST[k])
    notes = []
    if controls is not None and not (set(decision.CONTROL_MUST) <= set(ctl) and all(c["fails_where_it_must"] for c in ctl.values())):
        verdict = "inconclusive"
        notes.append("falsifiability controls did not come out as they must: K2 is inconclusive")
    return {"verdict": verdict, "quantity": "Omega_bulk", "comparator": ">=", "edge": 1.0,
            "window": sets["feasible"], "falsified_doses": sets["falsified"], "inconclusive_doses": sets["inconclusive"],
            "points": {str(d): {k: v for k, v in r.items()} for d, r in points.items()},
            "controls": ctl or None, "notes": notes,
            "rule": "claims_redirect.md 3a: worst registered state, per dose; Omega_bulk of contract v5"}


# ------------------------------------------------------------------ admissibility (D27) on K3 and K4
def _admissible(states, p_cred, enabled):
    """(restricted states, record) under the D27 rule; (states, None) when the rule is off or gamma_sl is absent."""
    if not enabled:
        return states, None
    m = admissibility.mask(states)
    if m is None:
        return states, None
    return admissibility.restrict(states, m), admissibility.summary(states, m, p_cred)


def _label_inadmissible(rec, adm):
    if adm is not None and adm["inadmissible_inputs"] and rec["verdict"] != "inconclusive":
        rec["verdict_restricted"] = rec["verdict"]
        rec["verdict"] = "inconclusive"
        rec["notes"] = list(rec.get("notes", [])) + ["inadmissible inputs: 1 - M_adm >= p_cred"]
    return rec


# ------------------------------------------------------------------ K3
def _k3_good(s, m_cos):
    """Per-draw K3 indicator at one (dose, state): het meets the criterion, hom does not, and C3a."""
    om, het, hom, b, cos = (s[k] for k in ("Omega_bulk", "barrier_het_template_kT", "barrier_hom_bulk_kT",
                                           "B_acc_kT", "cos_theta"))
    used = np.isfinite(om) & np.isfinite(b) & np.isfinite(cos)
    sup = om > 1.0
    with np.errstate(invalid="ignore"):
        ok = sup & (het <= b) & (hom > b) & (cos >= m_cos)
    return np.where(used, ok.astype(float), np.nan)


def k3_at_dose(states, p_cred, m_cos):
    """K3 at one dose: the band mass per state, the worst state, and the competing bulk precipitation."""
    per = {}
    for sid, s in states.items():
        need = {"Omega_bulk", "barrier_het_template_kT", "barrier_hom_bulk_kT", "B_acc_kT", "cos_theta"}
        if not need <= set(s):
            continue
        good = _k3_good(s, m_cos)
        hom, b = s["barrier_hom_bulk_kT"], s["B_acc_kT"]
        with np.errstate(invalid="ignore"):
            bulk = np.where(np.isfinite(s["Omega_bulk"]) & np.isfinite(b), (hom <= b).astype(float), np.nan)
        per[sid] = _verdict_record(good, p_cred, notes=[], P_bulk_precipitation=decision.mass_of(bulk)["P_good"],
                                   P_het_meets=decision.mass_of(_mask_nan(s, "barrier_het_template_kT", "<=", "B_acc_kT"))["P_good"],
                                   _good=good)
    if not per:
        return None
    return {"verdict": _worst_over_states(per), "by_state": per}


def _mask_nan(s, left, cmp_, right):
    a, b = s[left], s[right]
    with np.errstate(invalid="ignore"):
        return np.where(np.isfinite(a) & np.isfinite(b), decision.COMPARATORS[cmp_](a, b).astype(float), np.nan)


def k3(states_by_dose, p_cred, m_cos, admissible=True, competing=None):
    """K3 over the dose axis: the accessible window W_3 along D.

    states_by_dose: {ln D: {state: samples}} (dose scaled at fixed ratio, shared draws). feasible: some dose has
    P_good >= p_cred (the window is the set of feasible doses); falsified: every dose has P_bad >= p_cred;
    inconclusive otherwise. The dose where bulk precipitation takes over (P(DG_hom <= B_acc) >= 1/2) is stated.
    competing: optional {phase: {ln D: Omega draws}} of competing phases (Li3PO4, AlPO4, other calcium
    phosphates); their saturation at doses inside W_3 is reported. Prior masses are never findings.
    """
    points, adm_by_dose = {}, {}
    for d, states in states_by_dose.items():
        restricted, adm = _admissible(states, p_cred, admissible)
        r = k3_at_dose(restricted, p_cred, m_cos)
        u = k3_at_dose(states, p_cred, m_cos)
        if r is None:
            continue
        rec = _label_inadmissible({"verdict": r["verdict"], "notes": [], "by_state": decision.public(r["by_state"]),
                                   "unrestricted_verdict": u["verdict"] if u else None,
                                   "P_good": _min_good(r["by_state"]), "P_bad": _max_bad(r["by_state"]),
                                   "P_bulk_precipitation": _max_key(r["by_state"], "P_bulk_precipitation")}, adm)
        points[d] = rec
        adm_by_dose[d] = adm
    if not points:
        return {"verdict": "inconclusive", "gap": "K3 inputs are not evaluable (needs Omega, both barriers, B_acc)",
                "points": {}}
    sets = {v: sorted(d for d, r in points.items() if r["verdict"] == v) for v in decision.ORDER}
    if sets["feasible"]:
        verdict = "feasible"
    elif len(sets["falsified"]) == len(points):
        verdict = "falsified"
    else:
        verdict = "inconclusive"
    closes = [d for d, r in sorted(points.items()) if r["P_bulk_precipitation"] is not None and r["P_bulk_precipitation"] >= 0.5]
    window = sets["feasible"]
    comp = None
    if competing:
        comp = {ph: {str(d): _comp_mass(arrs.get(d)) for d in window or list(points)} for ph, arrs in competing.items()}
    ref = (window[0] if window else max(points, key=lambda d: points[d]["P_good"] or 0.0))
    return {"verdict": verdict, "window": window, "falsified_doses": sets["falsified"],
            "inconclusive_doses": sets["inconclusive"], "bulk_precipitation_takes_over_at": closes[0] if closes else None,
            "competing_phases": comp if comp else {"note": "none registered: no K_sp for Li3PO4, AlPO4 or another calcium phosphate"},
            "reference_dose": ref, "falsified_mass": points[ref]["P_bad"], "points": {str(d): r for d, r in points.items()},
            "admissibility": {str(d): _adm_brief(a) for d, a in adm_by_dose.items()},
            "rule": "claims_redirect.md 3b: DG_het <= B_acc < DG_hom and cos(theta) >= m_cos, inside K2"}


def _comp_mass(arr):
    if arr is None:
        return None
    return decision.mass_of(decision.indicator(arr, ">=", 1.0))["P_good"]


def _min_good(per):
    v = [r["P_good"] for r in per.values() if r["P_good"] is not None]
    return min(v) if v else None


def _max_bad(per):
    v = [r["P_bad"] for r in per.values() if r["P_bad"] is not None]
    return max(v) if v else None


def _max_key(per, key):
    v = [r[key] for r in per.values() if r.get(key) is not None]
    return max(v) if v else None


def _adm_brief(adm):
    if adm is None:
        return None
    return {k: adm[k] for k in ("M_adm", "n_evaluable", "n_refused", "inadmissible_inputs", "label", "note")}


# ------------------------------------------------------------------ K4
def closure_edge(cos_theta, d_max):
    """N_s_closure = tan^2(theta/2)/(2 d_max^2) per draw (thresholds C4s edge); 0 at theta = 0, huge at theta = pi."""
    c = np.clip(np.asarray(cos_theta, dtype=float), -1.0, 1.0)
    theta = np.arccos(c)
    with np.errstate(invalid="ignore"):
        return np.tan(theta / 2.0) ** 2 / (2.0 * np.asarray(d_max, dtype=float) ** 2)


def k4_at_dose(states, p_cred, m_S, d_max):
    per = {}
    for sid, s in states.items():
        if "S_spread" not in s:
            continue
        spread = decision.indicator(s["S_spread"], ">=", m_S)
        closure = np.full(spread.shape, np.nan)
        if d_max is not None and {"N_nuc", "cos_theta"} <= set(s):
            closure = decision.indicator(s["N_nuc"], ">=", closure_edge(s["cos_theta"], d_max))
        route = np.where(np.isfinite(spread), np.where(np.isfinite(closure), np.maximum(spread, closure), spread), np.nan)
        rec = _verdict_record(route, p_cred, P_spread=decision.mass_of(spread)["P_good"],
                              P_closure=decision.mass_of(closure)["P_good"], notes=[])
        if d_max is None:
            rec["notes"].append("closure route not evaluated: no insulating-thickness bound d_max supplied; "
                                "a falsification cannot be stated (both routes must fail)")
            if rec["verdict"] == "falsified":
                rec["verdict"] = "inconclusive"
        rec["P_both_fail"] = decision.mass_of(route)["P_bad"]
        per[sid] = rec
    if not per:
        return None
    return {"verdict": _worst_over_states(per), "by_state": per}


def k4(states_by_dose, p_cred, m_S, d_max, admissible=True):
    """K4 over the dose axis: S_spread >= m_S OR credible closure; falsified only if both fail on the same draw.

    A pass through closure is optimistic (square-lattice, no exclusion zones) and labelled.
    """
    points, adm_by_dose = {}, {}
    for d, states in states_by_dose.items():
        restricted, adm = _admissible(states, p_cred, admissible)
        r = k4_at_dose(restricted, p_cred, m_S, d_max)
        u = k4_at_dose(states, p_cred, m_S, d_max)
        if r is None:
            continue
        rec = _label_inadmissible({"verdict": r["verdict"], "notes": [], "by_state": r["by_state"],
                                   "unrestricted_verdict": u["verdict"] if u else None,
                                   "P_good": _min_good(r["by_state"]), "P_bad": _max_key(r["by_state"], "P_both_fail")}, adm)
        points[d] = rec
        adm_by_dose[d] = adm
    if not points:
        return {"verdict": "inconclusive", "gap": "K4 inputs are not evaluable (needs S_spread)", "points": {}}
    sets = {v: sorted(d for d, r in points.items() if r["verdict"] == v) for v in decision.ORDER}
    if sets["feasible"]:
        verdict = "feasible"
    elif len(sets["falsified"]) == len(points):
        verdict = "falsified"
    else:
        verdict = "inconclusive"
    ref = sets["feasible"][0] if sets["feasible"] else max(points, key=lambda d: points[d]["P_good"] or 0.0)
    via = None
    if verdict == "feasible":
        st = points[ref]["by_state"]
        via = "closure only (optimistic)" if all(r["P_spread"] is not None and r["P_spread"] < p_cred for r in st.values()) \
            else "S_spread"
    return {"verdict": verdict, "feasible_doses": sets["feasible"], "falsified_doses": sets["falsified"],
            "inconclusive_doses": sets["inconclusive"], "reference_dose": ref, "falsified_mass": points[ref]["P_bad"],
            "route": via, "d_max": None if d_max is None else float(np.max(d_max)),
            "points": {str(d): r for d, r in points.items()},
            "admissibility": {str(d): _adm_brief(a) for d, a in adm_by_dose.items()},
            "rule": "claims_redirect.md 3c: S_spread >= m_S OR N_nuc >= N_s_closure(theta, d_max)"}


# ------------------------------------------------------------------ deletion test and framing rule
def deletion_test(template, control, p_deg):
    """Deletion test on K3 and K4: each must degrade without the template for the pass to count as template-specific.

    template, control: {"K3": record, "K4": record} at the reference dose. A K that is not feasible with the template
    has nothing to delete. A feasible K that does not degrade is labelled ``generic``. The test holds if at least one
    of K3, K4 degrades (the rule of nacre.screen.decision.deletion_test).
    """
    per, degraded = {}, []
    for k in ("K3", "K4"):
        t, c = template.get(k), (control or {}).get(k)
        if t is None or c is None:
            per[k] = {"degraded": False, "label": "not run", "note": "no template or control record"}
            continue
        worse = decision.ORDER.index(c["verdict"]) > decision.ORDER.index(t["verdict"])
        mt, mc = t.get("falsified_mass"), c.get("falsified_mass")
        more = mt is not None and mc is not None and mc - mt >= p_deg
        deg = bool(worse or more)
        label = None
        if t["verdict"] == "feasible":
            label = "template-specific" if deg else "generic"
        per[k] = {"degraded": deg, "template_verdict": t["verdict"], "control_verdict": c["verdict"],
                  "template_falsified_mass": mt, "control_falsified_mass": mc, "label": label}
        if deg:
            degraded.append(k)
    return {"holds": bool(degraded), "degraded": degraded, "p_deg": p_deg, "per": per,
            "applies_to": ["K3", "K4"], "note": "K1 and K2 do not depend on the template"}


def framing_rule(by_framing):
    """A phase is falsified only if falsified under every registered framing; feasible under at least one (named)."""
    return decision.combine_framings(by_framing)


# ------------------------------------------------------------------ the phase record
def evaluate_mineral(mineral, k1_table, doses, p, controls=None, control_doses=None, d_max=None,
                     k1_override=False, competing=None, omega_controls=None):
    """K1 to K4 and the deletion test for one mineral (one framing).

    doses: {ln D: {state: samples}} of the template run; control_doses: the same for the bare-oxide control.
    Routes outside the solid-like nucleus are reported as pending extension points, never evaluated.
    """
    k1 = k1_for(k1_table, mineral)
    gate = proceeds(k1, k1_override)
    pending = routes.pending_for(mineral)
    rec = {"mineral": mineral.describe(), "K1": k1, "gate": gate, "route_extension_points_pending": pending,
           "provisional": True}
    rec["K2"] = k2(doses, p["p_cred"], omega_controls)
    if mineral.phase_state == "liquid_precursor":
        rec["K3"] = rec["K4"] = {"verdict": "inconclusive",
                                 "gap": "liquid precursor: wetting is evaluated by the route evaluator "
                                        "routes.liquid_precursor_wetting (not implemented)"}
        rec["deletion_test"] = None
        return rec
    if not gate["proceeds"]:
        rec["K3"] = rec["K4"] = {"verdict": "not run", "note": gate["note"]}
        rec["deletion_test"] = None
        return rec
    rec["K3"] = k3(doses, p["p_cred"], p["m_cos"], p.get("admissible", True), competing)
    rec["K4"] = k4(doses, p["p_cred"], p["m_S"], d_max, p.get("admissible", True))
    if control_doses:
        c3 = k3(control_doses, p["p_cred"], p["m_cos"], p.get("admissible", True), None)
        c4 = k4(control_doses, p["p_cred"], p["m_S"], d_max, p.get("admissible", True))
        rec["control"] = {"K3": {k: c3[k] for k in ("verdict", "falsified_mass", "window")},
                          "K4": {k: c4[k] for k in ("verdict", "falsified_mass", "feasible_doses")}}
        rec["deletion_test"] = deletion_test({"K3": rec["K3"], "K4": rec["K4"]}, {"K3": c3, "K4": c4}, p["p_deg"])
    else:
        rec["deletion_test"] = {"holds": False, "note": "no bare-oxide control supplied: the deletion test is not run"}
    return rec
