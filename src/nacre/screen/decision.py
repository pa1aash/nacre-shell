"""Per-link evaluators and the study-level decision rule (configs/preprint/thresholds.yaml).

The rule is W3's (theory/thresholds.md, cp2), implemented as written in its fenced block:

  * Statistic: band mass. For a test with decisive quantity X, comparator c and edge e,
    P_good is the prior-weighted fraction of draws with X c e and P_bad = 1 - P_good.
  * Verdict at credible level p (p > 1/2): feasible if P_good >= p, falsified if
    P_bad >= p, inconclusive otherwise; order feasible < inconclusive < falsified.
  * Edges are the registered expressions in contract symbols, with every number taken from
    the parameter table by key (resolver); nothing is typed here.
  * Clipping (N2) is the screen's (nacre.screen.boundary): f(theta) of a clipped draw is 0 or 1.
  * Omega is Omega_bulk; the quantities in decision.forbidden_in_verdicts are refused.
  * Aggregation: worst_state (worst verdict over the registered states), path_sum (C3b:
    nuclei summed over the states of the R-slurry path), worst_point (C5 Pourbaix region).
  * Link combination as registered: 'A and B' is feasible when every test is feasible and
    falsified when any is; C4 is falsified only when C4 and its supporting closure test
    C4s are both falsified.
  * C5 limits are deterministic: band mass 1 or 0. An undetermined window limit never
    passes; a pass under a solid-salt sink is conditional on cp2 decision 5.
  * Study: falsified if any link is falsified; feasible only if all links are feasible and
    the deletion test holds; inconclusive otherwise. The deletion test reruns the screen
    with each gating control (bare_oxide, PVDF) in place of the template and holds when, for
    each control, at least one of C2, C3, C4 degrades (strictly worse verdict, or
    falsified-side mass up by at least p_deg); C1 alone does not count.

Interpretations where the block is silent are marked INTERPRETATION in the code and listed
in the session report for the cp2 audit.
"""
import re

import numpy as np
import sympy as sp

from nacre.physics import film
from nacre.physics.constants import AVOGADRO, BOLTZMANN, ELEMENTARY_CHARGE, FARADAY, GAS_CONSTANT

ORDER = ("feasible", "inconclusive", "falsified")
COMPARATORS = {">": np.greater, ">=": np.greater_equal, "<": np.less, "<=": np.less_equal}
#: Decisive quantities of C1 to C4 and the link and output of the screen chain that carry them.
QUANTITY_SOURCE = {"W_adh_wet": ("anchor", "W_adh_wet"), "Delta_G_seq": ("sequester", "Delta_G_seq"),
                   "f_theta": ("nucleate", "f_theta"), "N_nuc": ("nucleate", "N_nuc"),
                   "S_spread": ("nucleate", "S_spread")}
CONSTANTS = {"k_B": BOLTZMANN, "N_A": AVOGADRO, "R_gas": GAS_CONSTANT, "F_c": FARADAY, "q_e": ELEMENTARY_CHARGE}
_FUNCS = {"tan": sp.tan, "log": sp.log, "exp": sp.exp, "sqrt": sp.sqrt, "cos": sp.cos, "sin": sp.sin,
          "acos": sp.acos, "pi": sp.pi}


class RuleError(ValueError):
    """The thresholds block cannot be applied as written to the given inputs."""


def worst(verdicts):
    """The worst verdict of a list (feasible < inconclusive < falsified)."""
    return max(verdicts, key=ORDER.index)


def verdict_from_mass(p_good, p):
    """Verdict of the band-mass rule at credible level p."""
    if not 0.5 < p < 1:
        raise RuleError("the credible level must lie in (1/2, 1), got %r" % p)
    if p_good is None or not np.isfinite(p_good):
        return "inconclusive"
    if p_good >= p:
        return "feasible"
    if 1.0 - p_good >= p:
        return "falsified"
    return "inconclusive"


# ------------------------------------------------------------------ parameters


class Resolver:
    """Numbers of the rule by parameter-table key. values: {key: value or (value, unit)}."""

    def __init__(self, values):
        self._values = dict(values)

    @classmethod
    def from_table(cls, doc):
        """Keys of lit/params.yaml: each params entry by its key (value and unit)."""
        vals = {}
        for key, entry in (doc.get("params") or {}).items():
            if isinstance(entry, dict) and "value" in entry:
                vals[key] = (entry["value"], entry.get("unit", ""))
        return cls(vals)

    def has(self, key):
        return key in self._values

    def get(self, key):
        """(value, unit) of a key; KeyError names the missing key."""
        if key not in self._values:
            raise KeyError("the thresholds need parameter-table key %r, which is not in the table" % key)
        v = self._values[key]
        return v if isinstance(v, tuple) else (v, "")

    def value(self, key):
        return self.get(key)[0]


def credible_level(rule, resolver):
    return float(resolver.value(rule["decision"]["credible_level"]["params"]))


def _edge(expr, params, resolver, extra=None):
    """Value of a registered edge expression: params map its symbols to table keys."""
    local = dict(_FUNCS)
    names = {str(s) for s in sp.sympify(str(expr), locals={**_FUNCS, **{k: sp.Symbol(k) for k in (params or {})},
                                                           **{k: sp.Symbol(k) for k in (extra or {})}}).free_symbols}
    subs = {}
    for name in names:
        if extra and name in extra:
            subs[name] = extra[name]
        elif params and name in params:
            subs[name] = float(resolver.value(params[name]))
        elif name in CONSTANTS:
            subs[name] = CONSTANTS[name]
        else:
            raise RuleError("edge %r names %s, which has no parameter key" % (expr, name))
    syms = sorted(subs)
    local.update({k: sp.Symbol(k) for k in syms})
    f = sp.lambdify([sp.Symbol(k) for k in syms], sp.sympify(str(expr), locals=local), "numpy")
    with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
        return f(*[subs[k] for k in syms])


# ------------------------------------------------------------------ band mass


def band_mass(values, comparator, edge, weights=None):
    """P_good and P_bad of a sample against an edge (scalar or per-draw); NaN draws excluded."""
    v = np.asarray(values, dtype=float)
    e = np.broadcast_to(np.asarray(edge, dtype=float), v.shape)
    used = np.isfinite(v) & ~np.isnan(e)
    w = np.ones(v.shape) if weights is None else np.asarray(weights, dtype=float)
    if not np.any(used):
        return {"P_good": None, "P_bad": None, "n_used": 0, "n_excluded": int(v.size)}
    good = COMPARATORS[comparator](v[used], e[used])
    pg = float(np.sum(w[used] * good) / np.sum(w[used]))
    return {"P_good": pg, "P_bad": 1.0 - pg, "n_used": int(used.sum()), "n_excluded": int((~used).sum())}


def _record(test, mass, edge, p, notes=()):
    e = np.asarray(edge, dtype=float)
    return {"quantity": test["quantity"], "comparator": test["comparator"], "edge_expression": str(test["edge"]),
            "edge": float(e) if e.ndim == 0 else "per_draw", **mass,
            "verdict": verdict_from_mass(mass["P_good"], p), "notes": list(notes)}


def _forbidden(rule, quantity):
    if quantity in (rule["decision"].get("forbidden_in_verdicts") or []):
        raise RuleError("%s is forbidden in verdicts (thresholds decision.forbidden_in_verdicts)" % quantity)


def evaluate_test(rule, test, samples, resolver, p=None, mixture=None):
    """Evaluate one test of C1 to C4 on one state's screen samples.

    samples: {quantity: array} for the state (from the chain; also "cos_theta").
    mixture: for a test with ``mixture`` (C1 over terminations), {termination: samples}
    and the weights come from the table key named in the test.
    """
    _forbidden(rule, test["quantity"])
    p = credible_level(rule, resolver) if p is None else p
    params = test.get("params") or {}
    extra = {}
    if "theta" in str(test["edge"]):
        extra["theta"] = np.arccos(np.clip(np.asarray(samples["cos_theta"], float), -1.0, 1.0))
    if "d_max" in str(test["edge"]):
        extra["d_max"] = admissible_thickness(test, resolver)
    if test.get("mixture") and mixture:
        w = resolver.value(test["mixture"]["weights"])
        masses = [band_mass(mixture[t][test["quantity"]], test["comparator"],
                            _edge(test["edge"], params, resolver, extra)) for t in mixture]
        weights = np.array([float(w[t]) for t in mixture])
        pg = float(np.sum(weights * [m["P_good"] for m in masses]) / weights.sum())
        mass = {"P_good": pg, "P_bad": 1.0 - pg, "n_used": sum(m["n_used"] for m in masses),
                "n_excluded": sum(m["n_excluded"] for m in masses)}
        return _record(test, mass, _edge(test["edge"], params, resolver, extra), p, ["population-weighted mixture"])
    edge = _edge(test["edge"], params, resolver, extra)
    return _record(test, band_mass(samples[test["quantity"]], test["comparator"], edge), edge, p)


def admissible_thickness(test, resolver):
    """d_max = max(d_max_ohm, d_max_tun) from the R-cell keys of the test (C4s), m."""
    k = test["params"]
    v = lambda name: float(resolver.value(k[name]))
    ohm = film.ohmic_thickness_bound(v("R_A_max"), v("rho_e"))
    kappa = film.tunnelling_decay_constant(v("phi_B"), effective_mass=v("m_e"))
    tun = film.tunnelling_thickness_bound(v("j_0"), v("j_req"), kappa)
    return max(ohm, tun)


# ------------------------------------------------------------------ links C1 to C4


def _combine(combine, verdicts):
    """Link verdict from its tests' verdicts by the registered combine rule."""
    if isinstance(combine, dict):                       # C4: explicit conditions
        def holds(cond):
            parts = [c.strip() for c in cond.split(" and ")]
            return all(verdicts[t] == v for t, v in (part.split() for part in parts))
        if holds(combine["feasible"]):
            return "feasible"
        if holds(combine["falsified"]):
            return "falsified"
        return "inconclusive"
    ids = [c.strip() for c in str(combine).split(" and ")]
    vs = [verdicts[i] for i in ids]
    if all(v == "feasible" for v in vs):
        return "feasible"
    if any(v == "falsified" for v in vs):
        return "falsified"
    return "inconclusive"


def _falsified_mass(combine, records):
    """INTERPRETATION: falsified-side mass of a link, for the deletion test.

    'A and B' links are falsified when any test is, so their mass is the largest P_bad;
    C4 is falsified only when both of its conditions hold, so its mass is the smaller.
    """
    vals = {t: r["P_bad"] for t, r in records.items() if r.get("P_bad") is not None}
    if not vals:
        return None
    if isinstance(combine, dict):
        ids = [part.split()[0] for part in combine["falsified"].split(" and ")]
        return min(vals[i] for i in ids if i in vals) if any(i in vals for i in ids) else None
    ids = [c.strip() for c in str(combine).split(" and ")]
    return max(vals[i] for i in ids if i in vals)


def evaluate_link(rule, claim, states, resolver, mixtures=None):
    """Verdict of one of C1 to C4 over the registered states.

    states: {state id: {quantity: array}} of screen samples. Tests with worst_state
    aggregation are evaluated per state and the worst verdict kept; C3b (path_sum) sums
    N_nuc over the states draw by draw (states with Omega_bulk <= 1 carry zero nuclei).
    """
    link = rule["links"][claim]
    p = credible_level(rule, resolver)
    records = {}
    for test in link["tests"]:
        agg = test.get("aggregation", link.get("aggregation", "worst_state"))
        if agg == "path_sum":
            arrays = [np.asarray(s[test["quantity"]], float) for s in states.values()]
            total = np.sum(arrays, axis=0)
            rec = evaluate_test(rule, test, {test["quantity"]: total}, resolver, p)
            rec["aggregation"] = "path_sum over %d state(s)" % len(states)
        else:
            per = {sid: evaluate_test(rule, test, s, resolver, p, (mixtures or {}).get(sid)) for sid, s in states.items()}
            sid = max(per, key=lambda k: ORDER.index(per[k]["verdict"]))
            rec = dict(per[sid])
            rec["aggregation"] = "worst_state (%s of %d)" % (sid, len(per))
        records[test["id"]] = rec
    verdict = _combine(link["combine"], {t: r["verdict"] for t, r in records.items()})
    return {"verdict": verdict, "tests": records, "falsified_mass": _falsified_mass(link["combine"], records)}


# ------------------------------------------------------------------ C5 (deterministic)

_ELEMENT = re.compile(r"([A-Z][a-z]?)(\d*\.?\d*)")


def formula_counts(formula):
    """(all atoms, atoms other than O and H) per formula unit of a simple formula like CaCO3."""
    n_all = n_m = 0.0
    for el, num in _ELEMENT.findall(formula):
        k = float(num) if num else 1.0
        n_all += k
        if el not in ("O", "H"):
            n_m += k
    if n_all == 0:
        raise RuleError("cannot read formula %r" % formula)
    return n_all, n_m


def _to_ev(value, unit, per):
    """Energy to eV (per atom or per formula unit, as `per` says the source is)."""
    u = (unit or "").replace(" ", "").lower()
    if u in ("ev", "ev/atom", "ev/f.u.", "ev/fu"):
        return float(value)
    if u in ("j", "j/atom"):
        return float(value) / ELEMENTARY_CHARGE
    if u in ("jmol^-1", "j/mol", "jmol-1"):
        return float(value) / FARADAY
    if u in ("kjmol^-1", "kj/mol", "kjmol-1"):
        return 1e3 * float(value) / FARADAY
    raise RuleError("unknown energy unit %r for %s" % (unit, per))


def _deterministic(verdict):
    return {"P_good": 1.0 if verdict == "feasible" else (0.0 if verdict == "falsified" else None),
            "P_bad": 0.0 if verdict == "feasible" else (1.0 if verdict == "falsified" else None)}


def evaluate_c5_slurry(test, pourbaix, resolver, framing, control_fails_where_it_must=None):
    """C5s: worst point of the framing phase's Pourbaix decomposition energy over the region.

    pourbaix: the schema's stability.R-slurry entry; the bulk state is used (an enriched
    evaluation is a labelled sensitivity, never a verdict).
    """
    state = pourbaix["states"]["bulk"]
    phase = framing if framing in state["decomposition_energy"] else None
    if phase is None:
        raise RuleError("no decomposition energy for the framing phase %r" % framing)
    entry = state["decomposition_energy"][phase]
    n_all, n_m = formula_counts(entry.get("formula") or "CaCO3")
    ph = np.asarray(pourbaix["axes"]["pH"], float)
    e = np.asarray(pourbaix["axes"]["E_V"], float)
    k = test["params"]
    ph_r = resolver.value(k["pH"])
    e_r = resolver.value(k["E_SHE"])
    in_ph = (ph >= float(ph_r["min"])) & (ph <= float(ph_r["max"]))
    in_e = (e >= float(e_r["min"])) & (e <= float(e_r["max"]))
    grid = np.array([[np.nan if v is None else v for v in row] for row in entry["grid"]], float)
    region = grid[np.ix_(in_e, in_ph)]
    if region.size == 0 or not np.any(np.isfinite(region)):
        return {**_deterministic("inconclusive"), "verdict": "inconclusive", "notes": ["no grid point in the region"]}
    worst_ev_atom = float(np.nanmax(region))
    e_form = _to_ev(*resolver.get(k["e_form"]), per="e_form per atom")
    edge_ev_m = n_all * e_form / n_m                                  # per non-O, non-H atom
    if str(framing).upper() == "ACC":
        edge_ev_m = (n_all * e_form + _to_ev(*resolver.get(k["Delta_ACC"]), per="Delta_ACC per formula unit")) / n_m
    value_ev_m = worst_ev_atom * n_all / n_m
    verdict = "feasible" if value_ev_m <= edge_ev_m else "falsified"
    notes = ["worst point %.6g eV per non-O, non-H atom against edge %.6g" % (value_ev_m, edge_ev_m)]
    if verdict == "feasible" and control_fails_where_it_must is not True:
        verdict = "inconclusive"
        notes.append("falsifiability control (item 21) not shown to fail where it must")
    return {**_deterministic(verdict), "verdict": verdict, "quantity": "Delta_G_pbx", "value": value_ev_m,
            "edge": edge_ev_m, "units": "eV per non-O, non-H atom", "notes": notes}


def _scheme_limit(window, side, reduce):
    """The limit of one side over the reference schemes: (status, value V)."""
    limits = list((window.get(side + "_by_scheme") or {}).values()) or [window[side]]
    if any(l["status"] != "ok" for l in limits):
        return "undetermined", None
    vals = [float(l["value_V"]) for l in limits]
    return "ok", (min(vals) if reduce.startswith("min") else max(vals))


def evaluate_c5_cell(test, cell, resolver, gated_phases, solid_salt_registered=False):
    """C5c_ox or C5c_red over the gated phases (worst phase); undetermined never passes."""
    k = test["params"]
    m_e = float(_to_volts(*resolver.get(k["m_E"])))
    ox = test["quantity"] == "E_ox"
    bound_key = k["E_cell_max"] if ox else k["E_cell_min"]
    if not resolver.has(bound_key):
        return {**_deterministic("inconclusive"), "verdict": "inconclusive", "notes": ["%s not registered" % bound_key]}
    bound = float(_to_volts(*resolver.get(bound_key)))
    solid = (cell["sink_assumption"].get("kind") == "solid_salt")
    per_phase = {}
    for phase in gated_phases:
        w = cell["windows"].get(phase)
        if w is None:
            per_phase[phase] = ("inconclusive", "no window computed")
            continue
        status, val = _scheme_limit(w, "oxidation" if ox else "reduction", test.get("reduce", "min"))
        if status != "ok":
            per_phase[phase] = ("inconclusive", "limit undetermined: never passes")
            continue
        if ox:
            v = "feasible" if val >= bound + m_e else ("falsified" if val < bound - m_e else "inconclusive")
        else:
            v = "feasible" if val <= bound - m_e else ("falsified" if val > bound + m_e else "inconclusive")
        note = "%s = %.4g V against %.4g V (margin %.3g V)" % (test["quantity"], val, bound, m_e)
        if v == "feasible" and ox and solid and not solid_salt_registered:
            v, note = "inconclusive", note + "; pass conditional on the solid-salt sink (cp2 decision 5)"
        per_phase[phase] = (v, note)
    verdict = worst([v for v, _ in per_phase.values()]) if per_phase else "inconclusive"
    return {**_deterministic(verdict), "verdict": verdict, "quantity": test["quantity"],
            "phases": {ph: {"verdict": v, "note": n} for ph, (v, n) in per_phase.items()}, "notes": []}


def _to_volts(value, unit):
    u = (unit or "V").replace(" ", "")
    if u in ("V", "Vvs.Li+/Li", "VvsLi+/Li", "J/C", "JC^-1"):
        return float(value)
    raise RuleError("unknown potential unit %r" % unit)


def evaluate_c5(rule, stability, resolver, control_fails_where_it_must=None, solid_salt_registered=False):
    """C5 verdict from the deterministic stability section (schema $defs/stability)."""
    link = rule["links"]["C5"]
    framing = resolver.value("regimes.R-slurry.parameters.framing")
    al = resolver.value("regimes.R-cell.parameters.al_phases") if resolver.has("regimes.R-cell.parameters.al_phases") else []
    records = {}
    for test in link["tests"]:
        if test["regime"] == "R-slurry":
            if "R-slurry" not in stability:
                records[test["id"]] = {**_deterministic("inconclusive"), "verdict": "inconclusive", "notes": ["no R-slurry stability"]}
                continue
            records[test["id"]] = evaluate_c5_slurry(test, stability["R-slurry"], resolver, framing, control_fails_where_it_must)
        else:
            if "R-cell" not in stability:
                records[test["id"]] = {**_deterministic("inconclusive"), "verdict": "inconclusive", "notes": ["no R-cell window"]}
                continue
            records[test["id"]] = evaluate_c5_cell(test, stability["R-cell"], resolver, ["CaCO3"] + list(al),
                                                   solid_salt_registered)
    verdict = _combine(link["combine"], {t: r["verdict"] for t, r in records.items()})
    return {"verdict": verdict, "tests": records, "falsified_mass": _falsified_mass(link["combine"], records)}


# ------------------------------------------------------------------ study


def deletion_test(rule, template_claims, control_claims, resolver):
    """The F1 deletion test: each gating control must degrade at least one of C2, C3, C4."""
    dt = rule["study"]["deletion_test"]
    p_deg = float(resolver.value(dt["params"]["p_deg"]))
    per = {}
    for control in dt["gating_controls"]:
        claims = control_claims.get(control)
        if claims is None:
            per[control] = {"degraded": [], "holds": False, "note": "control not run"}
            continue
        degraded = []
        for link in dt["links"]:
            t, c = template_claims[link], claims[link]
            worse = ORDER.index(c["verdict"]) > ORDER.index(t["verdict"])
            mt, mc = t.get("falsified_mass"), c.get("falsified_mass")
            more = mt is not None and mc is not None and mc - mt >= p_deg
            if worse or more:
                degraded.append(link)
        per[control] = {"degraded": degraded, "holds": bool(degraded)}
    holds = all(v["holds"] for v in per.values())
    return {"holds": holds, "controls": per,
            "on_failure": None if holds else dt["on_failure"]}


def study_verdict(rule, claims, deletion=None):
    """Study-level verdict from the five link verdicts and the deletion test."""
    vs = [claims[c]["verdict"] for c in ("C1", "C2", "C3", "C4", "C5")]
    if any(v == "falsified" for v in vs):
        verdict = "falsified"
    elif all(v == "feasible" for v in vs) and deletion is not None and deletion["holds"]:
        verdict = "feasible"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "links": {c: claims[c]["verdict"] for c in claims},
            "deletion_test": deletion,
            "framing": "generic adhesion study" if deletion is not None and not deletion["holds"] else None}

