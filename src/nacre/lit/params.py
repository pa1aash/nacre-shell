"""Loader and validator of the parameter table lit/params.yaml.

The format and the prior-construction rule are in lit/corpus/params_README.md; the clause ids used
here (X1, X2, X3, N1, N2, N3, U1, L1, P1, C4, and from rule version 2 T1, W1, A1, I1, D1, R1, G1, M0)
are the ones defined there.

Sampling API, matching the screen's prior-file interface (nacre.screen.priors):

    prior(key)            -> ParamPrior, a nacre.screen.priors.Prior with the key's grade, sources and
                             correlation group
    priors(keys)          -> PriorTuple, a tuple of ParamPrior with `.correlation` (Spearman matrix over
                             the keys) and `.groups`
    prior_set(regime)     -> nacre.screen.priors.PriorSet of every sampled primary key of one regime
                             (sensitivity and analog keys are read by name, README 7.1)
    sample_correlated(ps, n, rng) -> {key: array}, draws with the rank correlation of `ps`

Nothing here invents a value: a key without a prior (family none or categorical) raises instead of
being sampled.
"""
import hashlib
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from nacre import _util
from nacre.lit import evidence as E
from nacre.screen.priors import Prior, PriorSet

PARAMS = Path("lit") / "params.yaml"
TABLE = Path("lit") / "evidence_table.csv"
SYMBOLS = Path("theory") / "symbols.yaml"

FAMILIES = {"normal": ("mean", "sd"), "uniform": ("low", "high"), "loguniform": ("low", "high"),
            "fixed": ("value",), "categorical": ("options",), "none": ()}
SAMPLED = ("normal", "uniform", "loguniform", "fixed")
RULES = {"normal": ("N1", "N2"), "uniform": ("U1", "N3", "T1", "W1"), "loguniform": ("L1", "T1"),
         "fixed": ("X3", "P1", "R1", "D1", "M0"), "categorical": ("X3", "G1"), "none": ("X1", "X2", "I1", "D1")}
ROLES = ("primary", "sensitivity", "analog", "design-axis")
FLAGS = ("single_source", "analog", "truncated", "widened", "ionic_strength", "registered")
RULE_FIELD = {"T1": "truncation", "W1": "widening", "I1": "ignorance", "D1": "derived", "R1": "registered"}
STATUSES = ("sourced", "single-source", "gap", "computed", "registered", "design-input", "definitional")
REGIMES = ("R-slurry", "R-cell", "shared")
TRANSFORMS = ("none", "log10")
REQUIRED = ("symbol", "transform", "unit", "regimes", "status", "value", "range", "prior", "rule", "sources",
            "best_grade", "method", "conditions", "correlation_group", "notes")
GROUP_KINDS = ("rank", "assumed independent")
VIEW_ROOTS = ("regimes", "thresholds")  # alias views addressed by dotted paths (theory/thresholds.md)


class ParamsError(ValueError):
    """lit/params.yaml does not follow lit/corpus/params_README.md."""


class NotSampled(KeyError):
    """The key has no samplable prior (family none or categorical)."""


@dataclass(frozen=True)
class ParamPrior(Prior):
    """A screen Prior built from one parameter-table entry."""
    key: str = ""
    grade: str = None
    sources: tuple = ()
    correlation_group: str = None
    transform: str = "none"
    regimes: tuple = ()
    rule: str = ""

    def sample(self, rng, n):
        if self.distribution == "fixed":
            return np.full(n, float(self.params["value"]))
        return super().sample(rng, n)

    def ppf(self, u):
        """Inverse CDF of the marginal (used for correlated sampling)."""
        p, u = self.params, np.asarray(u, dtype=float)
        if self.distribution == "uniform":
            return p["low"] + u * (p["high"] - p["low"])
        if self.distribution == "loguniform":
            return np.exp(np.log(p["low"]) + u * (np.log(p["high"]) - np.log(p["low"])))
        if self.distribution == "normal":
            from statistics import NormalDist

            nd = NormalDist(p["mean"], p["sd"])
            return np.vectorize(nd.inv_cdf)(np.clip(u, 1e-12, 1 - 1e-12))
        if self.distribution == "fixed":
            return np.full(u.shape, float(p["value"]))
        raise NotSampled(self.key)


class PriorTuple(tuple):
    """A tuple of ParamPrior (usable wherever the screen takes a sequence of priors) plus the rank
    correlation over its keys: `.correlation` (Spearman, member order) and `.groups` ({group: keys})."""

    def __new__(cls, items, correlation, groups):
        obj = super().__new__(cls, items)
        obj.correlation = correlation
        obj.groups = groups
        return obj

    @property
    def keys(self):
        return [p.key for p in self]


@dataclass
class Params:
    path: str
    sha256: str
    doc: dict
    errors: list = field(default_factory=list)

    @property
    def entries(self):
        return self.doc.get("params") or {}

    @property
    def groups(self):
        return self.doc.get("correlation_groups") or {}


# ---- helpers ---------------------------------------------------------------------------------
def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _unit_base(unit):
    if unit in ("1", "dimensionless"):
        return 1.0, "dimensionless"
    q = E.ureg().Quantity(1, unit.replace("Ohm", "ohm")).to_base_units()
    return float(q.magnitude), str(q.dimensionality)


def _interval(text):
    """'(0, oo)', '[0, pi]', '(-oo, oo)' -> (lo, hi, lo_open, hi_open)."""
    t = (text or "(-oo, oo)").strip()
    lo_s, hi_s = [s.strip() for s in t[1:-1].split(",")]
    conv = {"oo": math.inf, "-oo": -math.inf, "pi": math.pi}
    lo = conv.get(lo_s, None)
    hi = conv.get(hi_s, None)
    lo = float(lo_s) if lo is None else lo
    hi = float(hi_s) if hi is None else hi
    return lo, hi, t[0] == "(", t[-1] == ")"


def _inside(x, iv):
    lo, hi, lo_open, hi_open = iv
    return (x > lo if lo_open else x >= lo) and (x < hi if hi_open else x <= hi)


def _close(a, b, rel=1e-9):
    return abs(a - b) <= rel * max(1.0, abs(a), abs(b))


def load_symbols(root):
    path = Path(root) / SYMBOLS
    if not path.exists():
        return {}
    return {s["id"]: s for s in (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("symbols", [])}


def load_grades(root):
    path = Path(root) / TABLE
    if not path.exists():
        return {}
    _, rows = E.read_csv(path)
    return {r["row_id"]: r["grade"] for r in rows}


# ---- validation ------------------------------------------------------------------------------
def _check_prior(key, e, grades, symbols, bad):
    pr = e.get("prior")
    if not isinstance(pr, dict) or pr.get("family") not in FAMILIES:
        bad("prior.family must be one of %s" % sorted(FAMILIES))
        return
    fam, rule = pr["family"], e.get("rule")
    for k in FAMILIES[fam]:
        if k not in pr:
            bad("%s prior needs %r" % (fam, k))
            return
    if rule not in RULES[fam]:
        bad("rule %r does not produce a %s prior (allowed: %s)" % (rule, fam, ", ".join(RULES[fam])))
    srcs = e.get("sources") or []
    src_grades = [grades.get(s) for s in srcs]
    value, rng, transform = e.get("value"), e.get("range"), e.get("transform")
    sym = symbols.get(e.get("symbol"))
    iv = _interval(sym.get("interval")) if sym and transform == "none" else None
    if fam in ("normal", "uniform", "loguniform"):
        if not all(_num(pr[k]) for k in FAMILIES[fam]):
            bad("%s prior parameters must be finite numbers" % fam)
            return
    if fam == "normal":
        if not pr["sd"] > 0:
            bad("normal prior needs sd > 0")
        if not all(g in ("A", "B") for g in src_grades):
            bad("a normal prior needs grade A or B sources only (N1, N2)")
        if rule == "N1" and len(srcs) < 2:
            bad("rule N1 needs at least two independent sources")
        if rule == "N2" and (len(srcs) != 1 or src_grades != ["A"]):
            bad("rule N2 needs exactly one grade-A source")
        if _num(value) and not _close(value, pr["mean"]):
            bad("value must equal the normal mean")
        if iv and pr["sd"] > 0 and not (_inside(pr["mean"] - 4 * pr["sd"], iv) and _inside(pr["mean"] + 4 * pr["sd"], iv)):
            bad("normal prior leaves the admissible interval of %s within 4 sd (N3)" % e.get("symbol"))
    elif fam in ("uniform", "loguniform"):
        lo, hi = pr["low"], pr["high"]
        if not lo < hi:
            bad("%s prior needs low < high" % fam)
        if not isinstance(rng, dict) or not (_close(rng.get("min"), lo) and _close(rng.get("max"), hi)):
            bad("%s prior bounds must equal the range (U1, L1)" % fam)
        decade = lo > 0 and hi / lo > 10
        if fam == "loguniform" and not decade:
            bad("log-uniform needs 0 < low and high/low > 10 (L1)")
        if fam == "uniform" and decade and transform == "none":
            bad("span exceeds a decade with positive bounds: rule L1 requires log-uniform")
        if iv:
            lo_ok = _inside(lo, iv) or lo == iv[0]
            hi_ok = _inside(hi, iv) or hi == iv[1]
            if not (lo_ok and hi_ok):
                bad("prior bounds leave the admissible interval of %s" % e.get("symbol"))
    elif fam == "fixed":
        if not _num(pr["value"]) or not (_num(value) and _close(value, pr["value"])):
            bad("fixed prior value must equal value")
        if rule == "P1" and not srcs:
            bad("rule P1 needs its source rows")
    elif fam == "categorical":
        opts = pr["options"]
        if not isinstance(opts, list) or not opts:
            bad("categorical prior needs a non-empty options list")
        else:
            for o in opts:
                for s in (o.get("sources") or []) if isinstance(o, dict) else []:
                    if s not in grades:
                        bad("option source %s not in the evidence table" % s)
    elif fam == "none":
        if rule in ("X1", "X2") and rng is not None:
            bad("rule %s (no admitted row) needs range null" % rule)
    if rule in RULE_FIELD and not isinstance(e.get(RULE_FIELD[rule]), dict):
        bad("rule %s needs the field %r (README 7.2)" % (rule, RULE_FIELD[rule]))
    if rule == "G1":
        for o in pr.get("options") or []:
            if not isinstance(o, dict) or not o.get("key"):
                bad("rule G1 options name their per-class key")
    if rule == "M0" and not (e.get("margin_case") == "zero" and value == 0 and str(e.get("margin_reason") or "").strip()):
        bad("rule M0 needs value 0, margin_case zero and margin_reason")
    if rule == "W1" and isinstance(e.get("widening"), dict):
        u = e["widening"].get("unwidened") or {}
        if not (_num(u.get("min")) and _num(u.get("max")) and pr["low"] <= u["min"] <= u["max"] <= pr["high"]):
            bad("rule W1: the widened prior must contain the unwidened span")
        if "single_source" not in (e.get("flags") or []):
            bad("rule W1 needs the flag single_source")
    if rule == "T1" and isinstance(e.get("truncation"), dict):
        t = e["truncation"]
        edge = pr.get("low") if t.get("side") == "min" else pr.get("high")
        if not (_num(edge) and _num(t.get("bound")) and _close(edge, t["bound"])):
            bad("rule T1: the prior must end at the truncation bound")


def validate(params, root=None):
    """Return a list of problems; empty means the file follows lit/corpus/params_README.md."""
    root = Path(root) if root else _util.repo_root()
    doc, errs = params.doc, []
    grades, symbols = load_grades(root), load_symbols(root)
    if doc.get("mock") is not False:
        errs.append("top level: 'mock' must be false")
    entries = doc.get("params")
    if not isinstance(entries, dict) or not entries:
        return errs + ["top level: 'params' must be a non-empty mapping"]
    for key, e in entries.items():
        def bad(msg, key=key):
            errs.append("%s: %s" % (key, msg))

        if not isinstance(e, dict):
            bad("entry must be a mapping")
            continue
        missing = [f for f in REQUIRED if f not in e]
        if missing:
            bad("missing fields %s" % missing)
            continue
        if e["transform"] not in TRANSFORMS:
            bad("transform must be none or log10")
        if e["status"] not in STATUSES:
            bad("status %r not in %s" % (e["status"], STATUSES))
        if not e["regimes"] or any(r not in REGIMES for r in e["regimes"]):
            bad("regimes must be a non-empty subset of %s" % (REGIMES,))
        unit = str(e["unit"])
        try:
            mag, dim = _unit_base(unit)
            if not _close(mag, 1.0):
                bad("unit %r is not a coherent SI unit" % unit)
            sym = symbols.get(e["symbol"])
            if e["transform"] == "log10" and dim != "dimensionless":
                bad("a log10 key has unit 1")
            elif sym and e["transform"] == "none" and _unit_base(sym["unit"])[1] != dim:
                bad("unit %r does not match the unit of symbol %s (%s)" % (unit, e["symbol"], sym["unit"]))
        except Exception as exc:
            bad("unit %r does not parse: %s" % (unit, exc))
        value, rng = e["value"], e["range"]
        if value is not None and not _num(value):
            bad("value must be a number or null")
        if rng is None:
            if not str(e.get("range_reason") or "").strip():
                bad("a null range needs range_reason")
        elif not (isinstance(rng, dict) and _num(rng.get("min")) and _num(rng.get("max"))
                  and rng["min"] <= rng["max"]):
            bad("range must be {min, max} with min <= max, or null")
        elif _num(value) and not rng["min"] <= value <= rng["max"]:
            bad("range [%g, %g] does not contain value %g" % (rng["min"], rng["max"], value))
        srcs = e["sources"] or []
        unknown = [s for s in srcs if s not in grades]
        if unknown:
            bad("source rows not in the evidence table: %s" % unknown)
        known = sorted(grades[s] for s in srcs if s in grades)
        if (known[0] if known else None) != e["best_grade"]:
            bad("best_grade %r is not the best grade of the sources (%r)" % (e["best_grade"], known[0] if known else None))
        _check_prior(key, e, grades, symbols, bad)
        role = e.get("role", "primary")
        if role not in ROLES:
            bad("role %r not in %s" % (role, ROLES))
        if role in ("sensitivity", "analog") and e.get("of") not in entries:
            bad("a %s key names an existing key in 'of'" % role)
        unknown_flags = [f for f in (e.get("flags") or []) if f not in FLAGS]
        if unknown_flags:
            bad("unknown flags %s" % unknown_flags)
        if role == "analog" and "analog" not in (e.get("flags") or []):
            bad("an analog key carries the flag analog (A1)")
        if e.get("rule") == "T1" and isinstance(e.get("truncation"), dict):
            sk = e["truncation"].get("sensitivity_key")
            if sk not in entries or entries[sk].get("role") != "sensitivity" or entries[sk].get("of") != key:
                bad("rule T1: the uncut prior is kept as a sensitivity key of this key")
        if e.get("rule") == "R1" and isinstance(e.get("registered"), dict):
            _check_registered(root, e, bad)
        if e.get("rule") == "D1" and isinstance(e.get("derived"), dict):
            _check_derived(e, entries, bad)
        if e.get("rule") == "G1":
            for o in e["prior"].get("options") or []:
                k = o.get("key") if isinstance(o, dict) else None
                if k and (k not in entries or entries[k].get("value") != o.get("value")
                          or entries[k].get("range") != o.get("range")):
                    bad("rule G1: option %s differs from params.%s" % (o.get("label"), k))
        g = e["correlation_group"]
        if g is not None and g not in (doc.get("correlation_groups") or {}):
            bad("correlation_group %r is not defined" % g)
    for gid, grp in (doc.get("correlation_groups") or {}).items():
        def gbad(msg, gid=gid):
            errs.append("group %s: %s" % (gid, msg))

        members = grp.get("members") or []
        naming = [k for k, e in entries.items() if isinstance(e, dict) and e.get("correlation_group") == gid]
        if sorted(members) != sorted(naming) or len(set(members)) != len(members):
            gbad("members %s differ from the keys that name the group %s" % (members, naming))
        if grp.get("kind") not in GROUP_KINDS:
            gbad("kind must be one of %s" % (GROUP_KINDS,))
        m = np.asarray(grp.get("matrix"), dtype=float)
        n = len(members)
        if m.shape != (n, n):
            gbad("matrix must be %d x %d" % (n, n))
            continue
        if not (np.allclose(m, m.T) and np.allclose(np.diag(m), 1.0) and np.all(np.abs(m) <= 1.0)):
            gbad("matrix must be symmetric with unit diagonal and entries in [-1, 1]")
        elif np.linalg.eigvalsh(m).min() < -1e-9:
            gbad("matrix is not positive semi-definite")
        if grp.get("kind") == "assumed independent" and not np.allclose(m, np.eye(n)):
            gbad("an assumed-independent group has the identity matrix")
        if grp.get("kind") == "rank":
            srcs = grp.get("sources") or []
            if not srcs or any(s not in grades for s in srcs):
                gbad("a rank-correlated group needs source rows that exist")
        if not str(grp.get("reason") or "").strip():
            gbad("reason missing")
    for path, leaf in _view_leaves(doc):
        k = leaf.get("key")
        if k not in entries:
            errs.append("alias %s: key %r is not in params" % (path, k))
        elif {f: v for f, v in leaf.items() if f != "key"} != entries[k]:
            errs.append("alias %s: differs from params.%s" % (path, k))
    return errs


def _check_registered(root, e, bad):
    from nacre.lit import build_params as B

    r = e["registered"]
    try:
        node = B.registered_node(root, r)
    except Exception as exc:  # the authority file is absent or unreadable
        bad("rule R1: %s" % exc)
        return
    if node is None or not _close(float(node.get("primary")), float(e["value"])):
        bad("rule R1: value differs from %s %s" % (r.get("file"), r.get("path")))


def _check_derived(e, entries, bad):
    from nacre.lit import build_params as B

    d = e["derived"]
    try:
        params = {k.partition(".")[0]: entries[k.partition(".")[0]] for k in d["inputs"].values()}
        value, _, _ = B.envelope(d["expr"], d["inputs"], params)
    except Exception as exc:
        bad("rule D1: cannot evaluate %r: %s" % (d.get("expr"), exc))
        return
    if (value is None) != (e["value"] is None) or (value is not None and not _close(value, e["value"], 1e-9)):
        bad("rule D1: value differs from the formula at the input values")


def _view_leaves(doc, roots=VIEW_ROOTS):
    """(dotted path, leaf) for every alias leaf under the view roots; a leaf is a mapping with `key`."""
    def walk(node, path):
        if isinstance(node, dict) and "key" in node and "prior" in node:
            yield ".".join(path), node
        elif isinstance(node, dict):
            for k, v in node.items():
                yield from walk(v, path + [str(k)])
    for r in roots:
        if r in doc:
            yield from walk(doc[r], [r])


def resolve(path, params=None):
    """The key behind a dotted path: `params.<key>`, `<key>` or an alias such as
    `regimes.R-slurry.parameters.J0_het`."""
    p = _params(params)
    if path in p.entries:
        return path
    if path.startswith("params.") and path[7:] in p.entries:
        return path[7:]
    for alias, leaf in _view_leaves(p.doc):
        if alias == path:
            return leaf["key"]
    raise KeyError("lit/params.yaml has no key or alias %r" % path)


def load_params(path=None, root=None, strict=True):
    """Read lit/params.yaml (or `path`), validate it, and return Params.

    strict=True raises ParamsError on any problem; strict=False records them in `.errors`.
    """
    root = Path(root) if root else _util.repo_root()
    path = Path(path) if path else root / PARAMS
    raw = path.read_bytes()
    doc = yaml.safe_load(raw) or {}
    if not isinstance(doc, dict):
        raise ParamsError("%s: top level must be a mapping" % path)
    p = Params(str(path), "sha256:" + hashlib.sha256(raw).hexdigest(), doc)
    p.errors = validate(p, root)
    if strict and p.errors:
        raise ParamsError("%s: %d problem(s):\n  %s" % (path, len(p.errors), "\n  ".join(p.errors)))
    return p


_DEFAULT = {}


def _params(params):
    if params is not None:
        return params
    if "p" not in _DEFAULT:
        _DEFAULT["p"] = load_params()
    return _DEFAULT["p"]


# ---- sampling API ----------------------------------------------------------------------------
def prior(key, params=None):
    """The prior of one key as a screen Prior (ParamPrior)."""
    p = _params(params)
    key = resolve(key, p)
    e = p.entries[key]
    pr = e["prior"]
    fam = pr["family"]
    if fam not in SAMPLED:
        raise NotSampled("%s has prior family %r and is not sampled (%s)"
                         % (key, fam, e.get("range_reason") or e.get("notes") or e["status"]))
    pars = {k: float(pr[k]) for k in FAMILIES[fam]}
    return ParamPrior(name=key, symbol=str(e["symbol"]), units=str(e["unit"]), distribution=fam, params=pars,
                      source=",".join(e["sources"] or []), key=key, grade=e["best_grade"],
                      sources=tuple(e["sources"] or []), correlation_group=e["correlation_group"],
                      transform=e["transform"], regimes=tuple(e["regimes"]), rule=e["rule"])


def correlation_matrix(keys, params=None):
    """Spearman rank-correlation matrix over `keys` from the declared groups (zero across groups)."""
    p = _params(params)
    n = len(keys)
    m = np.eye(n)
    for i, a in enumerate(keys):
        for j, b in enumerate(keys):
            if i == j:
                continue
            ga, gb = p.entries[a]["correlation_group"], p.entries[b]["correlation_group"]
            if ga is not None and ga == gb:
                grp = p.groups[ga]
                mem = grp["members"]
                m[i, j] = float(np.asarray(grp["matrix"], dtype=float)[mem.index(a), mem.index(b)])
    return m


def priors(keys, params=None):
    """Priors of several keys with their rank correlation (PriorTuple)."""
    p = _params(params)
    keys = [resolve(k, p) for k in keys]
    items = [prior(k, p) for k in keys]
    groups = {}
    for it in items:
        if it.correlation_group:
            groups.setdefault(it.correlation_group, []).append(it.key)
    return PriorTuple(items, correlation_matrix(list(keys), p), groups)


def prior_set(regime, params=None):
    """A screen PriorSet with every sampled key of `regime` (keys marked shared are included)."""
    if regime not in ("R-slurry", "R-cell"):
        raise ValueError("regime must be R-slurry or R-cell")
    p = _params(params)
    keys = [k for k, e in p.entries.items()
            if e["prior"]["family"] in SAMPLED and e.get("role", "primary") == "primary"
            and (regime in e["regimes"] or "shared" in e["regimes"])]
    return PriorSet(p.path, p.sha256, False, {regime: tuple(prior(k, p) for k in keys)})


def sample_correlated(ps, n, rng):
    """Draw n samples of a PriorTuple with its rank correlation (Gaussian copula).

    Spearman rho_s is mapped to the Pearson correlation of the copula by 2 sin(pi rho_s / 6). With the
    identity matrix this reduces to independent draws.
    """
    from statistics import NormalDist

    k = len(ps)
    rho = 2.0 * np.sin(np.pi * np.asarray(ps.correlation, dtype=float) / 6.0)
    np.fill_diagonal(rho, 1.0)
    w, v = np.linalg.eigh(rho)
    chol = v @ np.diag(np.sqrt(np.clip(w, 0.0, None)))
    z = rng.standard_normal((n, k)) @ chol.T
    u = np.vectorize(NormalDist().cdf)(z) if k else z
    return {pp.key: pp.ppf(u[:, j]) for j, pp in enumerate(ps)}


def main(argv=None):
    """`python -m nacre.lit.params [path]`: validate and print a summary."""
    import sys

    argv = sys.argv[1:] if argv is None else argv
    p = load_params(argv[0] if argv else None, strict=False)
    fams = {}
    for e in p.entries.values():
        fams[e["prior"]["family"]] = fams.get(e["prior"]["family"], 0) + 1
    print("%s: %d keys; families %s; groups %d" % (p.path, len(p.entries), fams, len(p.groups)))
    for e in p.errors:
        print("  " + e)
    print("validate: %s" % ("PASS" if not p.errors else "%d problem(s)" % len(p.errors)))
    return 1 if p.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
