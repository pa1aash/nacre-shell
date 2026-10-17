"""Per-link evaluators and the study-level decision rule (configs/preprint/thresholds.yaml).

The rule is W3's (theory/thresholds.md, cp2 block), with the cp3 rulings of the planning chat
(2026-10-17) applied where the block does not yet carry them. Each ruling is marked CP3-Rn in
the code; ops/reports/P0-W4.3a.md lists how each one was implemented and how it was reconciled
with W3's cp3 block.

  * Statistic: band mass. For a test with decisive quantity X, comparator c and edge e,
    P_good is the prior-weighted fraction of draws with X c e and P_bad = 1 - P_good.
    Verdict at credible level p (p > 1/2): feasible if P_good >= p, falsified if P_bad >= p,
    inconclusive otherwise; order feasible < inconclusive < falsified.
  * Edges are the registered expressions in contract symbols, every number resolved by the
    table key the block names; a registration convention of the block (p_cred, p_deg, m_cos)
    is used when the table key is still unset, and its source is recorded. A key that is
    missing or unset makes the test an explicit gap (inconclusive, the key named).
  * Units: every quantity with a unit string is converted by nacre.screen.units (R7(3)).
  * Aggregation: worst_state (worst verdict over the registered states), path_sum (C3b,
    nuclei summed over the states draw by draw), worst_point (Pourbaix region). The states
    share their draws (common random numbers), so per-draw indicators combine across states.
  * Link falsified-side mass (CP3-R7(1)): computed jointly, draw by draw: P(any test bad)
    for 'A and B' links, P(C4 bad and C4s bad) for C4; never a max or min of marginals.
  * C1 (CP3-R8): per-termination verdicts and the ignorance mixture over the termination
    weights: the mixture verdict is the one that holds for every weight vector of the simplex.
  * C2 is a descriptor (cp2 F3): the sequestration finding and a labelled sensitivity.
  * C3: (a) f <= f_e worst state; (b) N_nuc >= N_req path sum with N_req = ln(1/q0)/A_patch,
    q0 = 1 - p_cred (CP3-R5). C3(b) cannot be falsified unless every registered state was
    evaluated; with a state missing a shortfall is inconclusive and a pass stands (CP3-R7(4)).
  * C4 (CP3-R3): feasible if P(S_spread >= m_S) >= p OR P(N_nuc >= N_s,closure) >= p;
    falsified only if both fail at p; inconclusive otherwise. P(gamma_sl > gamma_nl) is
    reported. The d_max keys are propagated through their priors (CP3-R7(2)).
  * C5 R-slurry (CP3-R1): dissolution is decided by Omega_bulk >= 1 (sourced calcite K_sp,
    speciated activities), reported over the design axes as the dose window; the Omega test
    needs its falsifiability control to fail where it must. The Pourbaix competing-phase test
    at fixed C(IV) keeps its DFT tolerance.
  * C5 R-cell (CP3-R2): the all-experimental route governs wherever its inputs exist; the
    DFT schemes are comparators. Falsified if E_ox(expt) + m_expt < E_cell_max; a solid-salt
    sink bounds the onset from above (a falsification with it stands, a pass needs the
    solvated sink). Reported over the E_cell_max cutoff axis with every scheme in a table.
  * Design axes: a verdict that is the same at every design point is the verdict; otherwise
    it is design-dependent, inconclusive at the headline, and reported point by point.
  * Framings (CP3-R6): falsified only if falsified under every framing; feasible if feasible
    under at least one, naming it and reporting the other beside it.
  * Study: gating links C1, C3, C4, C5; falsified if any is falsified; feasible only if all
    are feasible and the deletion test holds (each gating control degrades C3 or C4).
"""
import re

import numpy as np
import sympy as sp

from nacre.physics import film
from nacre.physics.constants import AVOGADRO, BOLTZMANN, ELEMENTARY_CHARGE, FARADAY, GAS_CONSTANT
from nacre.screen import units

ORDER = ("feasible", "inconclusive", "falsified")
COMPARATORS = {">": np.greater, ">=": np.greater_equal, "<": np.less, "<=": np.less_equal}
#: Decisive quantities and the link and output of the screen chain that carry them.
QUANTITY_SOURCE = {"W_adh_wet": ("anchor", "W_adh_wet"), "Delta_G_seq": ("sequester", "Delta_G_seq"),
                   "f_theta": ("nucleate", "f_theta"), "N_nuc": ("nucleate", "N_nuc"),
                   "S_spread": ("nucleate", "S_spread")}
CONSTANTS = {"k_B": BOLTZMANN, "N_A": AVOGADRO, "R_gas": GAS_CONSTANT, "F_c": FARADAY, "q_e": ELEMENTARY_CHARGE}
_FUNCS = {"tan": sp.tan, "log": sp.log, "exp": sp.exp, "sqrt": sp.sqrt, "cos": sp.cos, "sin": sp.sin,
          "acos": sp.acos, "pi": sp.pi}
#: R-cell schemes: the governing all-experimental route and the DFT comparators (CP3-R2).
GOVERNING_SCHEME = "expt"


class RuleError(ValueError):
    """The thresholds block cannot be applied as written to the given inputs."""


class Gap(KeyError):
    """A parameter-table key the rule needs is missing or unset (a registration pending)."""

    def __str__(self):
        return str(self.args[0]) if self.args else "gap"


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


def public(record):
    """A record without its internal per-draw arrays (keys starting with an underscore)."""
    if isinstance(record, dict):
        return {k: public(v) for k, v in record.items() if not str(k).startswith("_")}
    if isinstance(record, list):
        return [public(v) for v in record]
    return record


# ------------------------------------------------------------------ parameters


class Resolver:
    """Numbers of the rule by parameter-table key or alias path.

    values: {key: value, (value, unit[, range]) or {"value", "unit", "range", "prior"}}. A key
    whose value is null (a registration not yet made) is treated as missing.
    """

    def __init__(self, values):
        self._values, self._priors = {}, {}
        for k, v in dict(values).items():
            if isinstance(v, dict) and "value" in v:
                self._values[k] = (v["value"], v.get("unit", ""), v.get("range"))
                if v.get("prior") is not None:
                    self._priors[k] = v["prior"]
            elif isinstance(v, tuple):
                self._values[k] = (v[0], v[1] if len(v) > 1 else "", v[2] if len(v) > 2 else None)
            else:
                self._values[k] = (v, "", None)

    @classmethod
    def from_table(cls, doc):
        """Keys of lit/params.yaml and the alias paths of its views (regimes.*, thresholds.*)."""
        vals = {}
        entries = doc.get("params") or {}

        def rec(e):
            return {"value": e.get("value"), "unit": e.get("unit", ""), "range": e.get("range"),
                    "prior": {**(e.get("prior") or {}), "transform": e.get("transform", "none"),
                              "symbol": e.get("symbol")} if isinstance(e.get("prior"), dict) else None}
        for key, entry in entries.items():
            if isinstance(entry, dict):
                vals[key] = rec(entry)

        def walk(node, path):
            if isinstance(node, dict) and "key" in node and "prior" in node:
                vals[".".join(path)] = rec(entries.get(node["key"], node))
            elif isinstance(node, dict):
                for k, v in node.items():
                    walk(v, path + [str(k)])
        for root in ("regimes", "thresholds"):
            if root in doc:
                walk(doc[root], [root])
        return cls(vals)

    def has(self, key):
        return key in self._values and self._values[key][0] is not None

    def get(self, key):
        """(value, unit) of a key; Gap names a missing or unset key."""
        if key not in self._values:
            raise Gap("the thresholds need parameter-table key %r, which is not in the table" % key)
        if self._values[key][0] is None:
            raise Gap("parameter-table key %r has no value yet (registration pending)" % key)
        return self._values[key][:2]

    def value(self, key):
        return self.get(key)[0]

    def si(self, key, unit):
        """Value of a key converted to ``unit`` (the key's own unit string must be known)."""
        value, u = self.get(key)
        return units.convert(float(value), u or "1", unit)

    def range(self, key):
        """The sourced span {min, max} of a key (or its value, when that is itself a range)."""
        if key not in self._values:
            raise Gap("the thresholds need parameter-table key %r, which is not in the table" % key)
        value, _, rng = self._values[key]
        if isinstance(value, dict) and {"min", "max"} <= set(value):
            return value
        if isinstance(rng, dict) and rng.get("min") is not None and rng.get("max") is not None:
            return rng
        raise Gap("parameter-table key %r has no range" % key)

    def prior(self, key):
        """The sampled prior of a key ({family, ..., transform}), or None for a fixed or unset key."""
        pr = self._priors.get(key)
        if pr and pr.get("family") in ("uniform", "loguniform", "normal"):
            return pr
        return None


def _convention(rule, name):
    return ((rule.get("decision") or {}).get("conventions") or {}).get(name) or {}


def credible_level(rule, resolver):
    """p_cred: the table key if set, else the block's registered primary convention (cp2)."""
    key = rule["decision"]["credible_level"]["params"]
    if resolver.has(key):
        return float(resolver.value(key))
    primary = _convention(rule, "p_cred").get("primary")
    if primary is None:
        raise Gap("parameter-table key %r has no value yet and the block has no primary convention" % key)
    return float(primary)


def degrade_mass(rule, resolver, p):
    """p_deg: the block's rule 1 - p_cred (it moves with p in the sweep), else the table key."""
    conv = _convention(rule, "p_deg")
    if str(conv.get("rule", "")).replace(" ", "") == "1-p_cred":
        return 1.0 - p
    return float(resolver.value(rule["study"]["deletion_test"]["params"]["p_deg"]))


def _param(rule, resolver, name, key):
    """A margin: the table key if set, else the block's primary convention for that margin."""
    if resolver.has(key):
        return float(resolver.value(key))
    primary = _convention(rule, name).get("primary")
    if primary is not None:
        return float(primary)
    resolver.get(key)                                     # raises the Gap naming the key


def _edge(expr, params, resolver, extra=None, rule=None):
    """Value of a registered edge expression: params map its symbols to table keys."""
    local = dict(_FUNCS)
    names = {str(s) for s in sp.sympify(str(expr), locals={**_FUNCS, **{k: sp.Symbol(k) for k in (params or {})},
                                                           **{k: sp.Symbol(k) for k in (extra or {})}}).free_symbols}
    subs = {}
    for name in names:
        if extra and name in extra:
            subs[name] = extra[name]
        elif params and name in params:
            subs[name] = _param(rule or {}, resolver, name, params[name])
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


def indicator(values, comparator, edge):
    """Per-draw good indicator as floats: 1 good, 0 bad, NaN where the draw is excluded."""
    v = np.asarray(values, dtype=float)
    e = np.broadcast_to(np.asarray(edge, dtype=float), v.shape)
    used = np.isfinite(v) & ~np.isnan(e)
    out = np.full(v.shape, np.nan)
    out[used] = COMPARATORS[comparator](v[used], e[used]).astype(float)
    return out


def mass_of(good, weights=None):
    """P_good, P_bad and the draw counts of a per-draw indicator (NaN draws excluded)."""
    g = np.asarray(good, dtype=float)
    used = np.isfinite(g)
    if not np.any(used):
        return {"P_good": None, "P_bad": None, "n_used": 0, "n_excluded": int(g.size)}
    w = np.ones(g.shape) if weights is None else np.asarray(weights, dtype=float)
    pg = float(np.sum(w[used] * g[used]) / np.sum(w[used]))
    return {"P_good": pg, "P_bad": 1.0 - pg, "n_used": int(used.sum()), "n_excluded": int((~used).sum())}


def band_mass(values, comparator, edge, weights=None):
    """P_good and P_bad of a sample against an edge (scalar or per-draw); NaN draws excluded."""
    return mass_of(indicator(values, comparator, edge), weights)


def half_width(p_good, n):
    """Half-width of a band mass: twice its binomial Monte Carlo standard error."""
    if p_good is None or not n:
        return None
    return float(2.0 * np.sqrt(p_good * (1.0 - p_good) / n))


def _record(test, good, edge, p, notes=()):
    e = np.asarray(edge, dtype=float)
    m = mass_of(good)
    return {"quantity": test["quantity"], "comparator": test["comparator"], "edge_expression": str(test["edge"]),
            "edge": float(e) if e.ndim == 0 else "per_draw", **m, "half_width": half_width(m["P_good"], m["n_used"]),
            "verdict": verdict_from_mass(m["P_good"], p), "notes": list(notes), "_good": good}


def gap_record(test, exc):
    return {"quantity": test.get("quantity"), "comparator": test.get("comparator"), "edge_expression": str(test.get("edge")),
            "edge": None, "P_good": None, "P_bad": None, "verdict": "inconclusive", "gap": str(exc), "notes": []}


def _forbidden(rule, quantity):
    if quantity in (rule["decision"].get("forbidden_in_verdicts") or []):
        raise RuleError("%s is forbidden in verdicts (thresholds decision.forbidden_in_verdicts)" % quantity)


def mixture_verdict(per, p):
    """CP3-R8: the ignorance mixture over termination weights, never a point weight.

    The band mass of a weighted mixture is the weighted mean of the per-termination masses,
    so over the whole simplex it ranges over [min, max] of them. The mixture is feasible only
    if it is feasible for every weight vector (min P_good >= p) and falsified only if it is
    falsified for every one (min P_bad >= p).
    """
    goods = [r["P_good"] for r in per.values() if r.get("P_good") is not None]
    if len(goods) < len(per) or not goods:
        return {"P_good_range": None, "verdict": "inconclusive"}
    lo, hi = min(goods), max(goods)
    v = "feasible" if lo >= p else ("falsified" if 1.0 - hi >= p else "inconclusive")
    return {"P_good_range": [lo, hi], "verdict": v}


def evaluate_test(rule, test, samples, resolver, p=None, mixture=None, extra=None):
    """Evaluate one test of C1 to C4 on one state's screen samples.

    samples: {quantity: array} for the state (from the chain; also "cos_theta").
    mixture: {termination: samples} for a test with ``mixture`` (C1): per-termination
    records and the ignorance mixture over the weights (CP3-R8).
    extra: per-draw values of symbols the edge names (d_max, an N_req).
    """
    _forbidden(rule, test["quantity"])
    p = credible_level(rule, resolver) if p is None else p
    params = test.get("params") or {}
    extra = dict(extra or {})

    def theta_of(s):
        return np.arccos(np.clip(np.asarray(s["cos_theta"], float), -1.0, 1.0))

    if test.get("mixture") and mixture:
        per = {}
        for t, s in mixture.items():
            ex = dict(extra, **({"theta": theta_of(s)} if "theta" in str(test["edge"]) else {}))
            edge = _edge(test["edge"], params, resolver, ex, rule)
            per[t] = _record(test, indicator(s[test["quantity"]], test["comparator"], edge), edge, p)
        mix = mixture_verdict(per, p)
        rec = {"quantity": test["quantity"], "comparator": test["comparator"], "edge_expression": str(test["edge"]),
               "by_termination": per, "mixture": "ignorance over the termination weights (cp3 R8)",
               "P_good_range": mix["P_good_range"], "verdict": mix["verdict"], "notes": []}
        rec["P_good"] = mix["P_good_range"][0] if mix["P_good_range"] else None
        rec["P_bad"] = 1.0 - mix["P_good_range"][1] if mix["P_good_range"] else None
        # the joint indicator: a draw counts bad only where it is bad for every termination
        goods = [r["_good"] for r in per.values()]
        if len({g.shape for g in goods}) == 1:
            rec["_good"] = np.max(np.vstack(goods), axis=0)
        return rec
    if "theta" in str(test["edge"]):
        extra["theta"] = theta_of(samples)
    edge = _edge(test["edge"], params, resolver, extra, rule)
    notes = ["single termination: the bindings register no termination dimension"] if test.get("mixture") else []
    return _record(test, indicator(samples[test["quantity"]], test["comparator"], edge), edge, p, notes)


# ------------------------------------------------------------------ C3b and C4s edges


def required_density(rule, test, resolver, p):
    """CP3-R5: N_req = ln(1/q0) / A_patch with q0 = 1 - p_cred, m^-2.

    The expected number of nuclei under a contact patch of area A_patch must be at least
    ln(1/q0), so that the Poisson probability of a patch with no nucleus is at most q0.
    """
    key = (test.get("params") or {}).get("A_patch") or "regimes.R-slurry.parameters.patch_area"
    a_patch = resolver.si(key, "m^2")
    if not a_patch > 0:
        raise RuleError("patch area must be positive")
    return float(np.log(1.0 / (1.0 - p)) / a_patch)


def _prior_draws(pr, unit_from, unit_to, n, rng):
    """Draws of a table prior ({family, low, high | mean, sd, transform}) in unit_to."""
    fam, u = pr["family"], rng.random(n)
    if fam == "uniform":
        y = pr["low"] + u * (pr["high"] - pr["low"])
    elif fam == "loguniform":
        y = np.exp(np.log(pr["low"]) + u * (np.log(pr["high"]) - np.log(pr["low"])))
    else:
        from scipy import special
        y = pr["mean"] + pr["sd"] * special.ndtri(u)
    if pr.get("transform") == "log10":
        return 10.0 ** y
    return units.convert(y, unit_from or "1", unit_to)


D_MAX_UNITS = {"rho_e": "Ohm m", "phi_B": "J", "m_e": "kg", "j_0": "A m^-2", "R_A_max": "Ohm m^2", "j_req": "A m^-2"}
D_MAX_DESIGN = ("R_A_max", "j_req")


def d_max_draws(test, resolver, n, rng, design=None):
    """CP3-R7(2): d_max = max(d_max_ohm, d_max_tun) per draw, m, and the keys used at a point.

    The material keys (rho_e, phi_B, m_eff, j_0) are propagated through their priors; a key
    without a prior enters at its central value and is flagged. R_A_max and j_req are design
    axes: their values come from ``design`` (a design point), else the table's registration.
    """
    k = test["params"]
    vals, flags = {}, []
    for name, unit in D_MAX_UNITS.items():
        if name in D_MAX_DESIGN and design and name in design:
            vals[name] = float(design[name])
            continue
        pr = resolver.prior(k[name])
        if pr is not None and name not in D_MAX_DESIGN:
            vals[name] = _prior_draws(pr, resolver._values[k[name]][1], unit, n, rng)
        else:
            vals[name] = resolver.si(k[name], unit)
            flags.append("%s at its central value (no prior)" % name if name not in D_MAX_DESIGN
                         else "%s at its registered value (design axis)" % name)
    with np.errstate(all="ignore"):
        ohm = film.ohmic_thickness_bound(vals["R_A_max"], vals["rho_e"])
        kappa = film.tunnelling_decay_constant(vals["phi_B"], effective_mass=vals["m_e"])
        tun = film.tunnelling_thickness_bound(vals["j_0"], vals["j_req"], kappa)
    d = np.maximum(np.broadcast_to(ohm, (n,)), np.broadcast_to(tun, (n,)))
    return np.asarray(d, float), flags


def admissible_thickness(test, resolver, design=None):
    """d_max at the central values of every key (reported beside the propagated draws), m."""
    d, _ = d_max_draws(test, _CentralResolver(resolver), 1, np.random.default_rng(0), design)
    return float(d[0])


class _CentralResolver:
    def __init__(self, r):
        self._r, self._values = r, r._values

    def prior(self, key):
        return None

    def __getattr__(self, name):
        return getattr(self._r, name)


# ------------------------------------------------------------------ links C1, C3, C4


def _aggregate(test, per, agg, registered, present):
    """Combine per-state records of a test; per-draw goods are combined draw by draw."""
    missing = sorted(set(registered or present) - set(present))
    if agg == "worst_state":
        sid = max(per, key=lambda k: ORDER.index(per[k]["verdict"]))
        rec = dict(per[sid])
        rec["aggregation"] = "worst_state (%s of %d)" % (sid, len(per))
        rec["by_state"] = {s: public({k: v for k, v in r.items() if k in ("P_good", "P_bad", "verdict", "gap")})
                           for s, r in per.items()}
        goods = [r.get("_good") for r in per.values()]
        if all(g is not None for g in goods) and len({np.shape(g) for g in goods}) == 1:
            rec["_good"] = np.min(np.vstack(goods), axis=0)        # bad at any state is bad
        if missing and rec["verdict"] == "feasible":
            rec["verdict"] = "inconclusive"
            rec["notes"] = rec.get("notes", []) + ["registered state(s) %s not evaluated: a pass cannot stand" % missing]
    else:
        rec = per
    rec["states_missing"] = missing
    return rec


def _states_good(states, fn):
    """fn(state samples) for every state; None when any state lacks a quantity."""
    return {sid: fn(s) for sid, s in states.items()}


def evaluate_link(rule, claim, states, resolver, registered_states=None, mixtures=None, d_max=None,
                  path_states=None):
    """Verdict of C1, C3 or C4 over the registered states (CP3-R3, R5, R7(1), R7(2), R7(4)).

    states: {state id: {quantity: array}} of screen samples sharing their draws.
    registered_states: the state ids the registration names (default: those given).
    d_max: per-draw admissible thickness for C4s (d_max_draws); computed at the central values
    when not given. A missing or unset key makes its test an explicit gap.
    """
    link = rule["links"][claim]
    p = credible_level(rule, resolver)
    registered = list(registered_states or states)
    present = [s for s in registered if s in states] if registered_states else list(states)
    records = {}
    for test in link["tests"]:
        agg = test.get("aggregation", link.get("aggregation", "worst_state"))
        try:
            if agg == "path_sum":
                records[test["id"]] = _path_sum(rule, test, states, resolver, p, registered, present)
                continue
            extra = {}
            if test["id"] == "C4s":
                if d_max is None:
                    d_max = admissible_thickness(test, resolver)
                extra["d_max"] = d_max
                total = _nuclei_sum(states)                         # the upper-estimate N_nuc of C3(b)
                per = {sid: evaluate_test(rule, test, dict(s, N_nuc=total), resolver, p, extra=extra)
                       for sid, s in states.items()}
            else:
                per = {sid: evaluate_test(rule, test, s, resolver, p, (mixtures or {}).get(sid), extra)
                       for sid, s in states.items()}
            records[test["id"]] = _aggregate(test, per, agg, registered, present)
        except Gap as exc:
            records[test["id"]] = gap_record(test, exc)
    out = {"verdict": combine(claim, link["combine"], records), "tests": records,
           "falsified_mass": joint_falsified_mass(claim, link["combine"], records), "role": "gating"}
    if claim == "C4":
        sl = [np.asarray(s["gamma_sl_minus_nl"], float) for s in states.values() if "gamma_sl_minus_nl" in s]
        if sl:
            m = mass_of(indicator(np.concatenate(sl), ">", 0.0))
            out["P_gamma_sl_gt_gamma_nl"] = m["P_good"]
        out["rule"] = "cp3 R3: C4 feasible or C4s feasible; falsified only if both falsified"
    return out


def _nuclei_sum(states):
    arrays = [np.asarray(s["N_nuc"], float) for s in states.values()]
    if len({a.shape for a in arrays}) != 1:
        raise RuleError("path sum needs the states to share their draws")
    return np.sum(arrays, axis=0)


def _path_sum(rule, test, states, resolver, p, registered, present):
    """C3b: nuclei summed over the states draw by draw against N_req (CP3-R5, R7(4))."""
    n_req = required_density(rule, test, resolver, p)
    total = _nuclei_sum({s: states[s] for s in present})
    rec = _record(dict(test, edge="log(1/(1 - p_cred))/A_patch"), indicator(total, test["comparator"], n_req), n_req, p)
    rec["N_req"] = n_req
    rec["N_req_rule"] = "cp3 R5: ln(1/q0)/A_patch, q0 = 1 - p_cred"
    rec["aggregation"] = "path_sum over %d state(s)" % len(present)
    missing = sorted(set(registered) - set(present))
    rec["states_missing"] = missing
    if missing and rec["verdict"] == "falsified":
        rec["verdict"] = "inconclusive"
        rec["notes"].append("registered state(s) %s not evaluated: a shortfall cannot falsify (cp3 R7(4))" % missing)
    return rec


def combine(claim, rule_combine, records):
    """Link verdict from its tests' verdicts.

    'A and B' is feasible when every test is feasible and falsified when any is. C4 follows
    the cp3 ruling R3 (feasible if either test is feasible, falsified only if both are).
    """
    v = {t: r["verdict"] for t, r in records.items()}
    if claim == "C4":
        if "feasible" in (v.get("C4"), v.get("C4s")):
            return "feasible"
        if v.get("C4") == "falsified" and v.get("C4s") == "falsified":
            return "falsified"
        return "inconclusive"
    ids = [c.strip() for c in str(rule_combine).split(" and ")]
    vs = [v[i] for i in ids]
    if all(x == "feasible" for x in vs):
        return "feasible"
    if any(x == "falsified" for x in vs):
        return "falsified"
    return "inconclusive"


def joint_falsified_mass(claim, rule_combine, records):
    """CP3-R7(1): the link's falsified-side mass, draw by draw.

    For an 'A and B' link a draw is on the falsified side when any test is bad on it; for C4
    when both C4 and C4s are bad on it. Deterministic tests (C5) carry mass 0 or 1 on every
    draw. Draws excluded by any test are excluded from the joint mass.
    """
    ids = ["C4", "C4s"] if claim == "C4" else [c.strip() for c in str(rule_combine).split(" and ")]
    goods = []
    for i in ids:
        r = records.get(i) or {}
        g = r.get("_good")
        if g is None:
            if r.get("P_bad") in (0.0, 1.0):                         # deterministic test
                goods.append(float(r["P_bad"] == 0.0))
                continue
            return None
        goods.append(g)
    arrays = [np.asarray(g, float) for g in goods if np.ndim(g)]
    n = arrays[0].shape if arrays else ()
    if any(a.shape != n for a in arrays):
        return None
    stack = np.vstack([np.broadcast_to(np.asarray(g, float), n) for g in goods]) if n else np.array(goods, float)[:, None]
    ok = np.all(np.isfinite(stack), axis=0)
    if not np.any(ok):
        return None
    bad = stack[:, ok] < 0.5
    joint = np.all(bad, axis=0) if claim == "C4" else np.any(bad, axis=0)
    return float(joint.mean())


# ------------------------------------------------------------------ C2 (descriptor)


def evaluate_c2(rule, states, resolver):
    """C2: the sequestration finding and its labelled sensitivity; never a gate (cp2 F3)."""
    link = rule["links"]["C2"]
    p = credible_level(rule, resolver)
    finding = link["finding"]
    dg = np.concatenate([np.asarray(s["Delta_G_seq"], float) for s in states.values()])
    m = band_mass(dg, "<", 0.0)
    if m["P_good"] is None:
        text = "premise_undecided"
    elif m["P_bad"] >= p:
        text = finding["text_on_fail"]
    elif m["P_good"] >= p:
        text = "the sequestration premise holds"
    else:
        text = "the sequestration premise is undecided"
    sens = {}
    for t in link.get("sensitivities") or []:
        try:
            edge = _edge(t["edge"], t.get("params"), resolver, rule=rule)
            r = _record(t, indicator(dg, t["comparator"], edge), edge, p, ["labelled sensitivity, not gating"])
        except Gap as exc:
            r = gap_record(t, exc)
        sens[t["id"]] = r
    return {"verdict": "descriptor", "role": "descriptor", "tests": sens, "falsified_mass": None,
            "finding": {"quantity": "Delta_G_seq", "P_Delta_G_seq_ge_0": m["P_bad"], "statement": text}}


# ------------------------------------------------------------------ design axes and framings


def over_design(verdicts):
    """Headline verdict over a design axis: the common verdict, or design-dependent (inconclusive)."""
    vs = list(verdicts.values()) if isinstance(verdicts, dict) else list(verdicts)
    if not vs:
        return {"verdict": "inconclusive", "design_dependent": False}
    if len(set(vs)) == 1:
        return {"verdict": vs[0], "design_dependent": False}
    return {"verdict": "inconclusive", "design_dependent": True}


def combine_framings(by_framing):
    """CP3-R6: falsified only under every framing; feasible under at least one (named)."""
    vs = {f: (r["verdict"] if isinstance(r, dict) else r) for f, r in by_framing.items()}
    feas = sorted(f for f, v in vs.items() if v == "feasible")
    if feas:
        return {"verdict": "feasible", "governing_framing": feas[0], "by_framing": vs}
    if vs and all(v == "falsified" for v in vs.values()):
        return {"verdict": "falsified", "governing_framing": None, "by_framing": vs}
    return {"verdict": "inconclusive", "governing_framing": None, "by_framing": vs}


# ------------------------------------------------------------------ C5 R-slurry (CP3-R1)


def evaluate_omega_point(omega, p):
    """Band mass of Omega_bulk >= 1 at one design point: feasible = CaCO3 does not dissolve."""
    m = mass_of(indicator(omega, ">=", 1.0))
    return {**m, "half_width": half_width(m["P_good"], m["n_used"]), "verdict": verdict_from_mass(m["P_good"], p)}


def evaluate_c5_slurry_omega(by_design, p, control=None, sensitivities=None):
    """CP3-R1: dissolution decided by Omega_bulk >= 1 over the design axes (the dose window).

    by_design: {point id: {"axes": {...}, "Omega_bulk": draws}} with the sourced calcite K_sp
    and speciated activities. control: {"axes", "Omega_bulk"} at W5's sourced dissolving
    condition; the test can pass only if the control is falsified there (it must report
    dissolution). sensitivities: {label: by_design} reported beside (ACC Omega, never gating).
    """
    points = {pid: {"axes": d["axes"], **evaluate_omega_point(d["Omega_bulk"], p)} for pid, d in by_design.items()}
    ctl = None
    if control is not None:
        ctl = {"axes": control["axes"], **evaluate_omega_point(control["Omega_bulk"], p)}
        ctl["fails_where_it_must"] = ctl["verdict"] == "falsified"
    sens = {lab: {pid: {"axes": d["axes"], **evaluate_omega_point(d["Omega_bulk"], p)} for pid, d in bd.items()}
            for lab, bd in (sensitivities or {}).items()}
    return omega_window(points, p, ctl, sens)


def omega_window(points, p, control=None, sensitivities=None):
    """The CP3-R1 record from per-point Omega records ({pid: {"axes", P_good, ..., verdict}})."""
    window = sorted(pid for pid, r in points.items() if r["verdict"] == "feasible")
    head = over_design({k: r["verdict"] for k, r in points.items()})
    notes = []
    verdict = head["verdict"]
    if verdict == "feasible" and not (control and control.get("fails_where_it_must")):
        verdict = "inconclusive"
        notes.append("falsifiability control not shown to fail where it must (no pass without it)")
    rec = {"quantity": "Omega_bulk", "comparator": ">=", "edge": 1.0, "edge_expression": "1",
           "verdict": verdict, "P_good": None, "P_bad": None, "design_dependent": head["design_dependent"],
           "dose_window": {"feasible_points": window, "points": points}, "control": control,
           "rule": "cp3 R1: Omega_bulk >= 1 with the sourced calcite K_sp and speciated activities",
           "notes": notes}
    if len(points) == 1:
        only = next(iter(points.values()))
        rec["P_good"], rec["P_bad"] = only["P_good"], only["P_bad"]
    if sensitivities:
        rec["sensitivities"] = sensitivities
    return rec


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


def _deterministic(verdict):
    return {"P_good": 1.0 if verdict == "feasible" else (0.0 if verdict == "falsified" else None),
            "P_bad": 0.0 if verdict == "feasible" else (1.0 if verdict == "falsified" else None)}


def evaluate_c5_slurry_phase(test, pourbaix, resolver, framing):
    """Competing-phase test at fixed C(IV): worst point of the framing phase's Pourbaix decomposition
    energy over the registered region against the DFT tolerance (n_at e_f [+ Delta_ACC]) / n_M.

    The bulk state is used; an enriched evaluation is a labelled sensitivity, never a verdict.
    Under CP3-R1 dissolution is the Omega test's; this test keeps the DFT tolerance and needs
    no control of its own (the control applies to the Omega test).
    """
    state = pourbaix["states"]["bulk"]
    if framing not in state["decomposition_energy"]:
        raise RuleError("no decomposition energy for the framing phase %r" % framing)
    entry = state["decomposition_energy"][framing]
    n_all, n_m = formula_counts(entry.get("formula") or "CaCO3")
    ph = np.asarray(pourbaix["axes"]["pH"], float)
    e = np.asarray(pourbaix["axes"]["E_V"], float)
    k = test["params"]
    ph_r, e_r = resolver.range(k["pH"]), resolver.range(k["E_SHE"])
    in_ph = (ph >= float(ph_r["min"])) & (ph <= float(ph_r["max"]))
    in_e = (e >= float(e_r["min"])) & (e <= float(e_r["max"]))
    grid = np.array([[np.nan if v is None else v for v in row] for row in entry["grid"]], float)
    region = grid[np.ix_(in_e, in_ph)]
    if region.size == 0 or not np.any(np.isfinite(region)):
        return {**_deterministic("inconclusive"), "verdict": "inconclusive", "notes": ["no grid point in the region"]}
    per = entry.get("units", "eV/atom")
    worst_atom = units.convert(float(np.nanmax(region)), per, "eV/atom")
    e_form = resolver.si(k["e_form"], "eV/atom")
    edge = n_all * e_form / n_m                                       # eV per non-O, non-H atom
    if str(framing).upper() == "ACC":
        edge = (n_all * e_form + resolver.si(k["Delta_ACC"], "eV/f.u.")) / n_m
    value = worst_atom * n_all / n_m
    verdict = "feasible" if value <= edge else "falsified"
    return {**_deterministic(verdict), "verdict": verdict, "quantity": "Delta_G_pbx", "value": value, "edge": edge,
            "units": "eV per non-O, non-H atom", "role": "competing-phase test at fixed C(IV) (cp3 R1)",
            "notes": ["worst point %.6g eV per non-O, non-H atom against edge %.6g" % (value, edge)]}


# ------------------------------------------------------------------ C5 R-cell (CP3-R2)


def _limit(window, side, scheme):
    by = window.get(side + "_by_scheme") or {}
    lim = by.get(scheme) if by else (window.get(side) if scheme == GOVERNING_SCHEME else None)
    if not lim:
        return "absent", None
    if lim.get("status") != "ok":
        return "undetermined", None
    return "ok", float(lim["value_V"])


def scheme_table(cells, gated_phases, side):
    """Every (phase, sink, scheme) limit: the expt route governs, janaf and mp are comparators."""
    rows = []
    for sink, cell in cells.items():
        kind = (cell.get("sink_assumption") or {}).get("kind", "other")
        bench = ((cell.get("schemes") or {}))
        for phase in gated_phases:
            w = (cell.get("windows") or {}).get(phase)
            schemes = sorted(set((w or {}).get(side + "_by_scheme") or {}) | {GOVERNING_SCHEME})
            for sc in schemes:
                status, val = _limit(w or {}, side, sc) if w else ("absent", None)
                rows.append({"phase": phase, "sink": sink, "sink_kind": kind, "scheme": sc,
                             "role": "governing" if sc == GOVERNING_SCHEME else "comparator",
                             "status": status, "value_V": val,
                             "benchmark_error_V": (bench.get(sc) or {}).get("benchmark_error_V")})
    return rows


def cell_verdict(value, status, kind, bound, margin, side):
    """One governing limit against one cutoff: falsified if beyond the edge by the margin."""
    if status != "ok":
        return "inconclusive", "governing limit %s: never a pass" % status
    if margin is None:
        return "inconclusive", "experimental margin m_expt not registered"
    if side == "oxidation":
        if value + margin < bound:
            return "falsified", "E_ox + m_expt < E_cell_max"
        if value - margin >= bound:
            if kind != "solvated":
                return "inconclusive", "pass under a %s sink: an upper bound on the onset, needs the solvated sink" % kind
            return "feasible", "E_ox - m_expt >= E_cell_max"
        return "inconclusive", "within the margin"
    if value - margin > bound:
        return "falsified", "E_red - m_expt > E_cell_min"
    if value + margin <= bound:
        return ("feasible", "E_red + m_expt <= E_cell_min") if kind == "solvated" else \
            ("inconclusive", "pass under a %s sink needs the solvated sink" % kind)
    return "inconclusive", "within the margin"


def evaluate_c5_cell(cells, resolver, gated_phases, side, cutoffs, margin_key, never_pass_sinks=()):
    """CP3-R2: the R-cell window limit of every gated phase against the cutoff design axis.

    cells: {sink: stability R-cell section} (one per registered salt plus the solvated sink).
    cutoffs: {label: potential in V} of E_cell_max (oxidation) or E_cell_min (reduction).
    A phase falsifies a cutoff if its governing limit falls beyond it under any sink (a
    solid-salt falsification stands); a pass needs every registered electrolyte to pass with
    the solvated sink. Sinks in never_pass_sinks stay undetermined (never a pass).
    """
    try:
        margin = resolver.si(margin_key, "V")
    except Gap:
        margin = None
    table = scheme_table(cells, gated_phases, side)
    by_cut = {}
    for label, bound in cutoffs.items():
        per_phase = {}
        for phase in gated_phases:
            sinks = {}
            for sink, cell in cells.items():
                rows = [r for r in table if r["phase"] == phase and r["sink"] == sink and r["role"] == "governing"]
                st, val = (rows[0]["status"], rows[0]["value_V"]) if rows else ("absent", None)
                if sink in never_pass_sinks and st == "ok":
                    st = "undetermined"
                sinks[sink] = cell_verdict(val, st, rows[0]["sink_kind"] if rows else "other", bound, margin, side)
            solv = [v for s, (v, _) in sinks.items() if cells[s].get("sink_assumption", {}).get("kind") == "solvated"]
            if any(v == "falsified" for v, _ in sinks.values()):
                vp = "falsified"
            elif solv and all(v == "feasible" for v in solv):
                vp = "feasible"                  # the solvated sink passes and no sink falsifies
            else:
                vp = "inconclusive"
            per_phase[phase] = {"verdict": vp, "sinks": {s: {"verdict": v, "note": n} for s, (v, n) in sinks.items()}}
        by_cut[label] = {"bound_V": float(bound), "verdict": worst([r["verdict"] for r in per_phase.values()]),
                         "phases": per_phase}
    head = over_design({k: r["verdict"] for k, r in by_cut.items()})
    return {**_deterministic(head["verdict"]), "verdict": head["verdict"], "design_dependent": head["design_dependent"],
            "quantity": "E_ox" if side == "oxidation" else "E_red", "scheme_table": table,
            "cutoff_axis": by_cut, "margin_V": margin, "governing_scheme": GOVERNING_SCHEME,
            "rule": "cp3 R2: all-experimental route governs; DFT schemes are comparators", "notes": []}


def evaluate_c5(rule, resolver, omega=None, pourbaix=None, cells=None, framing="calcite", gated_phases=None,
                cutoffs=None, margin_key="thresholds.C5.margin_expt", never_pass_sinks=()):
    """C5 = Omega test and competing-phase test (R-slurry) and both R-cell limits.

    omega: the evaluate_c5_slurry_omega record; pourbaix: the stability R-slurry section;
    cells: {sink: R-cell section}. A part with no input is an explicit gap.
    """
    p = credible_level(rule, resolver)
    recs = {}
    recs["C5s_omega"] = omega if omega is not None else \
        {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no Omega_bulk draws (speciation inputs)"}
    test = next(t for t in rule["links"]["C5"]["tests"] if t["id"] == "C5s")
    if pourbaix is None:
        recs["C5s"] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no R-slurry stability section"}
    else:
        try:
            recs["C5s"] = evaluate_c5_slurry_phase(test, pourbaix, resolver, framing)
        except Gap as exc:
            recs["C5s"] = gap_record(test, exc)
    for tid, side, key in (("C5c_ox", "oxidation", "regimes.R-cell.parameters.E_max"),
                           ("C5c_red", "reduction", "regimes.R-cell.parameters.E_min")):
        if not cells:
            recs[tid] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no R-cell window"}
            continue
        cuts = (cutoffs or {}).get(side)
        if not cuts:
            try:
                cuts = {"registered": resolver.si(key, "V")}
            except Gap as exc:
                recs[tid] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": str(exc)}
                continue
        recs[tid] = evaluate_c5_cell(cells, resolver, gated_phases or ["CaCO3"], side, cuts, margin_key,
                                     never_pass_sinks)
    vs = [r["verdict"] for r in recs.values()]
    verdict = "falsified" if "falsified" in vs else ("feasible" if all(v == "feasible" for v in vs) else "inconclusive")
    mass = 1.0 if verdict == "falsified" else (0.0 if verdict == "feasible" else None)
    return {"verdict": verdict, "tests": recs, "falsified_mass": mass, "role": "gating", "credible_level": p}


# ------------------------------------------------------------------ study


def deletion_test(rule, template_claims, control_claims, resolver):
    """The F1 deletion test: each gating control must degrade at least one of the deletion links."""
    dt = rule["study"]["deletion_test"]
    p_deg = degrade_mass(rule, resolver, credible_level(rule, resolver))
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
    return {"holds": holds, "controls": per, "p_deg": p_deg, "on_failure": None if holds else dt["on_failure"]}


def study_verdict(rule, claims, deletion=None):
    """Study-level verdict from the gating links and the deletion test (C2 is reported beside)."""
    gating = rule["study"].get("gating_links") or ["C1", "C3", "C4", "C5"]
    vs = [claims[c]["verdict"] for c in gating]
    if any(v == "falsified" for v in vs):
        verdict = "falsified"
    elif all(v == "feasible" for v in vs) and deletion is not None and deletion["holds"]:
        verdict = "feasible"
    else:
        verdict = "inconclusive"
    return {"verdict": verdict, "links": {c: claims[c]["verdict"] for c in gating},
            "deletion_test": deletion, "gating_links": list(gating),
            "sequestration_premise": ((claims.get("C2") or {}).get("finding") or {}).get("statement"),
            "framing": "generic adhesion study" if deletion is not None and not deletion["holds"] else None}
