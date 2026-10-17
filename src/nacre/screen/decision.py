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

    def override(self, values):
        """A copy with some keys set to other values (a sweep of registered conventions; labelled)."""
        new = Resolver({})
        new._values, new._priors = dict(self._values), dict(self._priors)
        for k, v in values.items():
            unit = self._values[k][1] if k in self._values else ""
            new._values[k] = (v, unit, None)
            new._priors.pop(k, None)
        return new

    def alias(self, names):
        """A copy in which each key of names also answers for the table key it maps to (gap table key_aliases)."""
        new = self.override({})
        for k, src in (names or {}).items():
            if src in self._values and k not in self._values:
                new._values[k] = self._values[src]
                if src in self._priors:
                    new._priors[k] = self._priors[src]
        return new

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
    """A parameter of an edge in SI units: the table key if set (converted from its unit string
    to the SI unit of the symbol), else the block's primary convention for that margin."""
    if resolver.has(key):
        value, unit = resolver.get(key)
        from nacre.screen.params_adapter import symbol_units
        si = symbol_units().get(name)
        if unit and si:
            return units.convert(float(value), unit, si)
        return float(value)
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


def mixture_record(test, per, p, rng, values=None, edge=None):
    """C1 over the registered terminations (thresholds block v3, cp3b A2).

    The weights w ~ Dirichlet(1, ..., 1) (flat: uniform on the simplex) are drawn once per draw,
    independently of every other input, and the mixture quantity is the area-weighted work
    W_mix = sum_k w_k W_k, to which the C1 edge applies. A point weight is never used. The
    per-termination verdicts are reported beside, a termination falsified on its own is named,
    and the weight-free masses P(min_k W_k > edge) <= P_good(mix) <= P(max_k W_k > edge) are
    printed: if the lower is at least p the verdict holds for every weighting (feasible), if the
    upper is at most 1 - p it is falsified for every weighting; otherwise the mixture verdict is
    conditional on the termination ignorance mixture (never a finding).
    values: {termination: per-draw W_k}; edge: the C1 edge (scalar or per draw).
    """
    if values is None:
        raise RuleError("the cp3b A2 mixture needs the per-termination values")
    ws = [np.asarray(v, float) for v in values.values()]
    if len({v.shape for v in ws}) != 1:
        raise RuleError("the terminations must share their draws")
    w = rng.dirichlet(np.ones(len(ws)), size=ws[0].shape[0]).T
    g = np.vstack(ws)
    ok = np.all(np.isfinite(g), axis=0)
    mix = np.full(ws[0].shape, np.nan)
    mix[ok] = np.sum(w[:, ok] * g[:, ok], axis=0)
    rec = _record(test, indicator(mix, test["comparator"], edge), edge, p,
                  ["W_mix = sum_k w_k W_k, w ~ Dirichlet(1, ..., 1) drawn with the other inputs; never a point weight"])
    lo = mass_of(indicator(np.where(ok, g.min(axis=0), np.nan), test["comparator"], edge))["P_good"]
    hi = mass_of(indicator(np.where(ok, g.max(axis=0), np.nan), test["comparator"], edge))["P_good"]
    if lo is not None and lo >= p:
        weighting = "feasible for every weighting"
    elif hi is not None and hi <= 1.0 - p:
        weighting = "falsified for every weighting"
    else:
        weighting = "conditional on the termination ignorance mixture (not a finding)"
    rec.update({"by_termination": per, "weight_free": {"P_min_good": lo, "P_max_good": hi, "reading": weighting},
                "falsified_alone": sorted(t for t, r in per.items() if r["verdict"] == "falsified")})
    return rec


def _edge_value(per):
    e = next(iter(per.values())).get("edge")
    return 0.0 if e in (None, "per_draw") else e


def evaluate_test(rule, test, samples, resolver, p=None, mixture=None, extra=None, rng=None):
    """Evaluate one test of C1 to C4 on one state's screen samples.

    samples: {quantity: array} for the state (from the chain; also "cos_theta").
    mixture: {termination: samples} for a test with ``mixture`` (C1): per-termination
    records and the flat-Dirichlet mixture over the weights (cp3 R8).
    extra: per-draw values of symbols the edge names (d_max, p_cred).
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
            per[t] = {k: v for k, v in _record(test, indicator(s[test["quantity"]], test["comparator"], edge), edge,
                                               p).items() if k != "_good"}
        return mixture_record(test, per, p, rng if rng is not None else np.random.default_rng(0),
                              {t: s[test["quantity"]] for t, s in mixture.items()}, edge)
    if "theta" in str(test["edge"]):
        extra["theta"] = theta_of(samples)
    edge = _edge(test["edge"], params, resolver, extra, rule)
    notes = ["single termination: the bindings register no termination dimension"] if test.get("mixture") else []
    return _record(test, indicator(samples[test["quantity"]], test["comparator"], edge), edge, p, notes)


# ------------------------------------------------------------------ C3b and C4s edges


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


def _aggregate(per, label):
    """Report record of one test over the states: the worst state, and every state's masses."""
    sid = max(per, key=lambda k: (ORDER.index(per[k]["verdict"]), per[k].get("P_bad") or 0.0))
    rec = {k: v for k, v in per[sid].items() if k != "_good"}
    rec["aggregation"] = "%s (%s of %d)" % (label, sid, len(per))
    rec["by_state"] = {s: public({k: v for k, v in r.items() if k in ("P_good", "P_bad", "verdict")})
                       for s, r in per.items()}
    rec["_by_state"] = {s: r["_good"] for s, r in per.items()}
    return rec


#: How a link's tests form its per-draw indicator (thresholds block v2, decision.link_mass).
OR_LINKS = {"C4"}           # good on a draw if either route is good; every other link: all tests good


def evaluate_link(rule, claim, states, resolver, registered_states=None, mixtures=None, d_max=None, rng=None):
    """Verdict of C1, C3 or C4 over the registered states (thresholds block v2).

    states: {state id: {quantity: array}} of screen samples sharing their draws (common
    random numbers). Within each state the link has one indicator per draw: every test good
    (C1, C3) or either route good (C4, cp3 R3), with C3(b) and C4's closure route reading the
    path-summed N_nuc. The link's band masses at a state are those of the indicator (cp3 R7(1));
    the verdict is the worst over the states and the falsified-side mass the largest. A missing
    registered state (cp3 R7(4)) bounds the verdict: a worst-state pass needs every state, and a
    path-sum shortfall cannot falsify. A missing or unset key makes its test an explicit gap;
    the link is then decided only where the remaining tests decide it.
    """
    link = rule["links"][claim]
    p = credible_level(rule, resolver)
    registered = list(registered_states or states)
    present = [s for s in registered if s in states] if registered_states else list(states)
    missing = sorted(set(registered) - set(present))
    states = {s: states[s] for s in present}
    records, goods = {}, {}                     # goods: test id -> {state: per-draw indicator}
    for test in link["tests"]:
        agg = test.get("aggregation", link.get("aggregation", "worst_state"))
        try:
            if agg == "path_sum":
                rec = _path_sum(rule, test, states, resolver, p, missing)
                goods[test["id"]] = {s: rec["_good"] for s in states}
                records[test["id"]] = {k: v for k, v in rec.items() if k != "_good"}
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
                per = {sid: evaluate_test(rule, test, s, resolver, p, (mixtures or {}).get(sid), extra, rng)
                       for sid, s in states.items()}
            rec = _aggregate(per, agg)
            goods[test["id"]] = rec.pop("_by_state")
            records[test["id"]] = rec
        except Gap as exc:
            records[test["id"]] = gap_record(test, exc)
    out = _link_verdict(claim, link, records, goods, states, p, missing)
    out.update({"tests": records, "role": "gating", "states_missing": missing})
    if claim == "C4":
        out["P_gamma_sl_gt_gamma_nl"] = {sid: mass_of(indicator(s["gamma_sl_minus_nl"], ">", 0.0))["P_good"]
                                         for sid, s in states.items() if "gamma_sl_minus_nl" in s}
        out["route_masses"] = {t: records[t].get("P_good") for t in ("C4", "C4s") if t in records}
    return public(out)


def _joint(claim, tests, goods, sid, override=None):
    """Per-draw indicator of a link at one state (override: test id -> constant indicator)."""
    n = next(len(goods[t][sid]) for t in tests if t not in (override or {}))  if any(
        t not in (override or {}) for t in tests) else len(goods[tests[0]][sid])
    g = np.vstack([np.full(n, float(override[t])) if override and t in override else np.asarray(goods[t][sid], float)
                   for t in tests])
    ok = np.all(np.isfinite(g), axis=0)
    out = np.full(n, np.nan)
    out[ok] = (np.max if claim in OR_LINKS else np.min)(g[:, ok], axis=0)
    return out


def _link_verdict(claim, link, records, goods, states, p, missing):
    """The joint-mass verdict of a link (block v2, link_mass and states)."""
    tests = [t["id"] for t in link["tests"]]
    have = [t for t in tests if t in goods]
    path_tests = [t["id"] for t in link["tests"] if t.get("aggregation") == "path_sum" or t["id"] == "C4s"]
    rule_text = ("good per draw if either route is good" if claim in OR_LINKS else "good per draw if every test is good")
    if not have or not states:
        return {"verdict": "inconclusive", "P_good": None, "P_bad": None, "falsified_mass": None,
                "joint_rule": rule_text, "notes": ["no test of the link could be evaluated"]}

    def masses(override=None):
        per = {}
        for sid in states:
            m = mass_of(_joint(claim, have, goods, sid, override))
            per[sid] = {**m, "verdict": verdict_from_mass(m["P_good"], p)}
        return per

    per = masses()
    worst_sid = max(per, key=lambda k: (ORDER.index(per[k]["verdict"]), per[k]["P_bad"] or 0.0))
    verdict = per[worst_sid]["verdict"]
    notes = []
    complete = len(have) == len(tests)
    if not complete:
        gap_t = sorted(set(tests) - set(have))
        if claim in OR_LINKS and verdict == "falsified":
            verdict = "inconclusive"
            notes.append("route(s) %s not evaluable: a falsification needs both routes" % gap_t)
        if claim not in OR_LINKS and verdict == "feasible":
            verdict = "inconclusive"
            notes.append("test(s) %s not evaluable: a pass needs every test" % gap_t)
    if missing:
        notes.append("registered state(s) %s not evaluated (cp3 R7(4))" % missing)
        if verdict == "feasible":
            # a worst-state pass needs every state; a pass carried by the path-sum route alone stands
            alt = masses({t: 0.0 for t in have if t not in path_tests}) if claim in OR_LINKS else None
            if alt is None or not all(r["verdict"] == "feasible" for r in alt.values()):
                verdict = "inconclusive"
                notes.append("a pass needs every registered state")
        elif verdict == "falsified":
            # a falsification at an evaluated state stands only without the path-sum shortfall
            alt = masses({t: 1.0 for t in have if t in path_tests})
            if claim in OR_LINKS or not any(r["verdict"] == "falsified" for r in alt.values()):
                verdict = "inconclusive"
                notes.append("a path-sum shortfall cannot falsify while a state is missing")
    jm = per[worst_sid]
    return {"verdict": verdict, "P_good": jm["P_good"], "P_bad": jm["P_bad"],
            "falsified_mass": max((r["P_bad"] for r in per.values() if r["P_bad"] is not None), default=None),
            "half_width": half_width(jm["P_good"], jm["n_used"]), "joint_rule": rule_text,
            "joint_by_state": {sid: {k: r[k] for k in ("P_good", "P_bad", "verdict")} for sid, r in per.items()},
            "worst_state": worst_sid, "notes": notes}


def _nuclei_sum(states):
    arrays = [np.asarray(s["N_nuc"], float) for s in states.values()]
    if len({a.shape for a in arrays}) != 1:
        raise RuleError("path sum needs the states to share their draws")
    return np.sum(arrays, axis=0)


def _path_sum(rule, test, states, resolver, p, missing):
    """C3b: nuclei summed over the evaluated states draw by draw against N_req (cp3 R5, R7(4))."""
    n_req = float(_edge(test["edge"], test.get("params"), resolver, {"p_cred": p}, rule))
    total = _nuclei_sum(states)
    rec = _record(test, indicator(total, test["comparator"], n_req), n_req, p)
    rec.update({"N_req": n_req, "N_req_rule": "cp3 R5: ln(1/q0)/A_patch, q0 = 1 - p_cred",
                "aggregation": "path_sum over %d state(s)" % len(states), "states_missing": missing})
    if missing and rec["verdict"] == "falsified":
        rec["verdict"] = "inconclusive"
        rec["notes"].append("registered state(s) %s not evaluated: a shortfall cannot falsify (cp3 R7(4))" % missing)
    return rec


def required_density(rule, test, resolver, p):
    """N_req of the block's C3b edge, log(1/(1 - p_cred)) / A_patch (cp3 R5), m^-2."""
    return float(_edge(test["edge"], test.get("params"), resolver, {"p_cred": p}, rule))


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


def evaluate_c5_slurry_omega(by_design, p, controls=None, sensitivities=None):
    """C5s (block v2): dissolution decided by Omega_bulk >= 1 over the design axes (the dose window).

    by_design: {point id: {"axes": {...}, "Omega_bulk": draws}} with the calcite K_sp under
    every framing and the speciated activities. controls: {"undersaturated": {"axes",
    "Omega_bulk"}, "supersaturated": {...}} at W5's registered control states: the Omega test
    must report dissolution at the first and stability at the second, else C5s is inconclusive.
    sensitivities: {label: by_design} reported beside (C5s_ACC, never gating).
    """
    points = {pid: {"axes": d["axes"], **evaluate_omega_point(d["Omega_bulk"], p)} for pid, d in by_design.items()}
    ctl = {k: {"axes": c["axes"], **evaluate_omega_point(c["Omega_bulk"], p)} for k, c in (controls or {}).items()}
    sens = {lab: {pid: {"axes": d["axes"], **evaluate_omega_point(d["Omega_bulk"], p)} for pid, d in bd.items()}
            for lab, bd in (sensitivities or {}).items()}
    return omega_window(points, p, control_outcomes(ctl), sens)


#: What each falsifiability control must report (block v2, C5s.control).
CONTROL_MUST = {"undersaturated": "falsified", "supersaturated": "feasible"}


def control_outcomes(controls):
    """Mark each control record with whether it came out as it must."""
    out = {}
    for k, c in (controls or {}).items():
        if c is None:
            continue
        out[k] = dict(c, must=CONTROL_MUST[k], fails_where_it_must=c.get("verdict") == CONTROL_MUST[k])
    return out


def omega_window(points, p, controls=None, sensitivities=None):
    """The C5s record from per-point Omega records ({pid: {"axes", P_good, ..., verdict}}).

    The verdict at a design point is its band-mass verdict; it is inconclusive unless both
    controls came out as they must (block v2: on_failure inconclusive). The dose window is the
    set of points where C5s is feasible, with the falsified and inconclusive sets beside it.
    """
    controls = controls or {}
    ok = all(k in controls and controls[k]["fails_where_it_must"] for k in CONTROL_MUST)
    notes = [] if ok else ["falsifiability controls %s did not all come out as they must: C5s is inconclusive"
                           % sorted(CONTROL_MUST)]
    points = {pid: dict(r) for pid, r in points.items()}
    for pid, r in points.items():
        r["verdict_before_control"] = r.get("verdict_before_control", r["verdict"])
        r["verdict"] = r["verdict_before_control"] if ok else "inconclusive"
    sets = {v: sorted(pid for pid, r in points.items() if r["verdict"] == v) for v in ORDER}
    head = over_design({k: r["verdict"] for k, r in points.items()})
    rec = {"quantity": "Omega_bulk", "comparator": ">=", "edge": 1.0, "edge_expression": "1",
           "verdict": head["verdict"], "P_good": None, "P_bad": None, "design_dependent": head["design_dependent"],
           "dose_window": {"feasible_points": sets["feasible"], "falsified_points": sets["falsified"],
                           "inconclusive_points": sets["inconclusive"], "points": points},
           "controls": controls, "controls_pass": ok, "role": "dissolution",
           "rule": "block v2 C5s: Omega_bulk >= 1, calcite K_sp under every framing, speciated activities",
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
    """Every (phase, sink, scheme) limit: expt governs; each DFT scheme and each benchmark-corrected
    DFT scheme is a comparator (a corrected value equals expt by construction, never a confirmation)."""
    rows = []
    for sink, cell in cells.items():
        kind = (cell.get("sink_assumption") or {}).get("kind", "other")
        bench = cell.get("schemes") or {}
        for phase in gated_phases:
            w = (cell.get("windows") or {}).get(phase) or {}
            schemes = sorted(set(w.get(side + "_by_scheme") or {}) | {GOVERNING_SCHEME})
            for sc in schemes:
                status, val = _limit(w, side, sc) if w else ("absent", None)
                err = (bench.get(sc) or {}).get("benchmark_error_V")
                rows.append({"phase": phase, "sink": sink, "sink_kind": kind, "scheme": sc,
                             "role": "governing" if sc == GOVERNING_SCHEME else "comparator",
                             "status": status, "value_V": val, "benchmark_error_V": err})
                if sc != GOVERNING_SCHEME and err is not None and val is not None:
                    rows.append({"phase": phase, "sink": sink, "sink_kind": kind, "scheme": sc + "_corrected",
                                 "role": "comparator", "status": status, "value_V": val - err,
                                 "benchmark_error_V": err})
    return rows


def cell_verdict(value, status, kind, bound, margin, side):
    """One limit against one cutoff: falsified beyond the edge by the margin (either sink); a pass
    needs the solvated sink (a solid-salt onset is an upper bound on the true onset)."""
    if status != "ok":
        return "inconclusive", "limit %s: never a pass" % status
    if margin is None:
        return "inconclusive", "margin not registered"
    if side == "oxidation":
        if value + margin < bound:
            return "falsified", "E_ox + m < E_cell_max"
        if value - margin >= bound:
            if kind != "solvated":
                return "inconclusive", "pass under a %s sink: an upper bound on the onset, needs the solvated sink" % kind
            return "feasible", "E_ox - m >= E_cell_max"
        return "inconclusive", "within the margin"
    if value - margin > bound:
        return "falsified", "E_red - m > E_cell_min"
    if value + margin <= bound:
        return "feasible", "E_red + m <= E_cell_min"
    return "inconclusive", "within the margin"


def _dft_decided(rows, kind, bound, m_e, side):
    """cp2 fix F5 over the DFT schemes where the expt route is missing: a pass under the
    lowest-onset scheme, a falsification under every scheme, margin m_E (labelled DFT-decided)."""
    dft = [r for r in rows if r["role"] == "comparator" and not r["scheme"].endswith("_corrected")]
    if not dft or any(r["status"] != "ok" for r in dft):
        return "inconclusive", "expt route missing and a DFT scheme undetermined: never a pass"
    vs = [cell_verdict(r["value_V"], "ok", kind, bound, m_e, side)[0] for r in dft]
    if all(v == "falsified" for v in vs):
        return "falsified", "DFT-decided (F5): falsified under every scheme"
    low = min(dft, key=lambda r: r["value_V"]) if side == "oxidation" else max(dft, key=lambda r: r["value_V"])
    v, n = cell_verdict(low["value_V"], "ok", kind, bound, m_e, side)
    return ("feasible", "DFT-decided (F5): passes under the lowest-onset scheme") if v == "feasible" else         ("inconclusive", "DFT-decided (F5): " + n)


def _route_applies(routes, route, phase, sink, side):
    """cp3b A1: whether a route's margin is registered for (phase, sink, side); routes None = everywhere."""
    if routes is None:
        return True
    return any(r.get("phase") == phase and r.get("sink") == sink and r.get("side") == side
               for r in ((routes.get(route) or {}).get("applies_to") or []))


def evaluate_c5_cell(cells, resolver, gated_phases, side, cutoffs, margin_key, never_pass_sinks=(),
                     dft_margin_key="thresholds.C5.window_margin", margin_routes=None):
    """C5c_ox or C5c_red (block v2, cp3 R2) for the gated phases over the cutoff design axis.

    cells: {sink: stability R-cell section}; cutoffs: {cathode class or label: V}. The expt route
    governs with margin m_expt; where it is missing the limit is DFT-decided under F5 with m_E.
    A phase falsifies a cutoff if any sink falsifies it; it passes only if the solvated sink
    passes and no sink falsifies. Sinks in never_pass_sinks are undetermined (never a pass).
    The crossover cutoffs E_ox - m_expt (feasible at or below, solvated sink) and E_ox + m_expt
    (falsified above) are printed per phase and sink. margin_routes (cp3b A1, screen.yaml
    R-cell.margin_by_route): one margin per reaction and sink; a limit whose route has no
    registered margin for its (phase, sink, side) is undetermined (never passes, never falsifies).
    """
    def margin(key):
        try:
            return resolver.si(key, "V")
        except Gap:
            return None
    m_expt, m_e = margin(margin_key), margin(dft_margin_key)
    table = scheme_table(cells, gated_phases, side)
    crossovers = {}
    for r in table:
        if r["role"] == "governing" and r["status"] == "ok" and m_expt is not None \
                and _route_applies(margin_routes, "expt", r["phase"], r["sink"], side):
            lo, hi = (r["value_V"] - m_expt, r["value_V"] + m_expt)
            crossovers.setdefault(r["phase"], {})[r["sink"]] = (
                {"feasible_at_or_below_V": lo if r["sink_kind"] == "solvated" else None, "falsified_above_V": hi}
                if side == "oxidation" else {"feasible_at_or_above_V": hi, "falsified_below_V": lo})
    by_cut = {}
    for label, bound in cutoffs.items():
        per_phase = {}
        for phase in gated_phases:
            sinks = {}
            for sink, cell in cells.items():
                rows = [r for r in table if r["phase"] == phase and r["sink"] == sink]
                gov = [r for r in rows if r["role"] == "governing"]
                kind = (cell.get("sink_assumption") or {}).get("kind", "other")
                st, val = (gov[0]["status"], gov[0]["value_V"]) if gov else ("absent", None)
                if st == "ok":
                    m = m_expt if _route_applies(margin_routes, "expt", phase, sink, side) else None
                    v, n = cell_verdict(val, st, kind, bound, m, side)
                    n = "expt: " + (n if m is not None else "undetermined: no budget key for this reaction and sink "
                                    "(cp3b A1); never a pass, never a falsification")
                else:
                    m = m_e if _route_applies(margin_routes, "dft_where_expt_missing", phase, sink, side) else None
                    v, n = _dft_decided(rows, kind, bound, m, side)
                if sink in never_pass_sinks and v == "feasible":
                    v, n = "inconclusive", "sink thermochemistry undetermined: never a pass"
                sinks[sink] = (v, n, kind)
            solv = [v for v, _, k in sinks.values() if k == "solvated"]
            if any(v == "falsified" for v, _, _ in sinks.values()):
                vp = "falsified"
            elif solv and all(v == "feasible" for v in solv) and side == "oxidation":
                vp = "feasible"
            elif side == "reduction" and sinks and all(v == "feasible" for v, _, _ in sinks.values()):
                vp = "feasible"
            else:
                vp = "inconclusive"
            per_phase[phase] = {"verdict": vp, "sinks": {s: {"verdict": v, "note": n} for s, (v, n, _) in sinks.items()}}
        by_cut[label] = {"bound_V": float(bound), "verdict": worst([r["verdict"] for r in per_phase.values()]),
                         "phases": per_phase}
    head = over_design({k: r["verdict"] for k, r in by_cut.items()})
    return {**_deterministic(head["verdict"]), "verdict": head["verdict"], "design_dependent": head["design_dependent"],
            "quantity": "E_ox" if side == "oxidation" else "E_red", "scheme_table": table, "crossovers": crossovers,
            "cutoff_axis": by_cut, "margin_V": m_expt, "dft_margin_V": m_e, "governing_scheme": GOVERNING_SCHEME,
            "rule": "block v2 C5c: expt governs with m_expt; F5 over the DFT schemes where expt is missing",
            "disclosure": "the CaCO3/LiClO4 scheme values were seen before this rule (cp3 R2; packet p0-3 decision 3)",
            "notes": []}


def evaluate_c5(rule, resolver, omega=None, pourbaix=None, cells=None, framing="calcite", cutoffs=None,
                never_pass_sinks=(), margin_routes=None):
    """C5 = C5s (Omega dissolution) and C5s_phase and C5c_ox and C5c_red (block v2).

    omega: the C5s record (omega_window); pourbaix: the stability R-slurry section; cells:
    {sink: R-cell section}; cutoffs: {"oxidation": {label: V}, "reduction": {label: V}}. A part
    with no input is an explicit gap. The gated phases and margin keys are the block's.
    """
    p = credible_level(rule, resolver)
    link = rule["links"]["C5"]
    tests = {t["id"]: t for t in link["tests"] + (link.get("sensitivities") or [])}
    recs = {}
    recs["C5s"] = omega if omega is not None else         {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no Omega_bulk draws (speciation inputs)"}
    if pourbaix is None:
        recs["C5s_phase"] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no R-slurry stability section"}
    else:
        try:
            recs["C5s_phase"] = evaluate_c5_slurry_phase(tests["C5s_phase"], pourbaix, resolver, framing)
        except Gap as exc:
            recs["C5s_phase"] = gap_record(tests["C5s_phase"], exc)
    gated = (link.get("gated_phases") or {}).get("R-cell") or ["CaCO3"]
    for tid, side, bound_sym in (("C5c_ox", "oxidation", "E_cell_max"), ("C5c_red", "reduction", "E_cell_min")):
        t = tests[tid]
        if not cells:
            recs[tid] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": "no R-cell window"}
            continue
        cuts = (cutoffs or {}).get(side)
        if not cuts:
            try:
                cuts = {"registered": resolver.si(t["params"][bound_sym], "V")}
            except Gap as exc:
                recs[tid] = {"verdict": "inconclusive", "P_good": None, "P_bad": None, "gap": str(exc)}
                continue
        recs[tid] = evaluate_c5_cell(cells, resolver, gated, side, cuts, t["params"]["m_expt"], never_pass_sinks,
                                     t["params"].get("m_E", "thresholds.C5.window_margin"), margin_routes)
    vs = [recs[t]["verdict"] for t in [c.strip() for c in str(link["combine"]).split(" and ")]]
    verdict = "falsified" if "falsified" in vs else ("feasible" if all(v == "feasible" for v in vs) else "inconclusive")
    mass = 1.0 if verdict == "falsified" else (0.0 if verdict == "feasible" else None)
    if omega is not None and omega.get("P_bad") is not None and verdict != "falsified":
        mass = max(mass or 0.0, omega["P_bad"]) if mass is not None else None
    return {"verdict": verdict, "tests": recs, "falsified_mass": mass, "role": "gating", "credible_level": p,
            "gated_phases": {"R-cell": gated}}


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
        if claims.get("_gap"):
            per[control] = {"degraded": [], "holds": False, "note": "control not evaluable: %s" % claims["_gap"]}
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
