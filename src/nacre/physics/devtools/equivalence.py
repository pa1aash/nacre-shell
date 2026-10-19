"""Numerical equivalence of the physics implementation with the theory contract.

For each contract function, random points are sampled in its input domains (the symbol
intervals of theory/symbols.yaml, overridden by the function's ``domains``); the numpy
implementation (nacre.physics.contract) is compared with ``sympy.lambdify`` of the
contract expression at every point, with relative tolerance 1e-12. The contract's exact
limit cases are reproduced numerically, and its monotonicity statements are checked on
the implementation by finite perturbation.

The contract and symbol files are passed in as text so the same code serves the unit test
(working-tree files) and the devtools script (files read from another lane's branch).
"""
import math
import re
from dataclasses import dataclass, field

import numpy as np
import sympy as sp
import yaml

from nacre.physics import constants as C
from nacre.physics.contract import CONSTANT_IDS, FUNCTIONS

RTOL = 1e-12
HP_DIGITS = 40          # working precision of the high-precision reference
CONDITIONING = 4.0      # allowance factor, see check_function
FUNCS = {"exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "cos": sp.cos, "sin": sp.sin,
         "tan": sp.tan, "acos": sp.acos, "asin": sp.asin, "atan": sp.atan, "pi": sp.pi,
         "oo": sp.oo}
CONSTANT_VALUES = {"k_B": C.BOLTZMANN, "N_A": C.AVOGADRO, "R_gas": C.GAS_CONSTANT,
                   "F_c": C.FARADAY, "q_e": C.ELEMENTARY_CHARGE, "hbar": C.HBAR,
                   "m_e": C.ELECTRON_MASS, "m_std": C.STANDARD_MOLALITY,
                   "c_std": C.STANDARD_CONCENTRATION}
_INTERVAL = re.compile(r"^\s*([\[\(])\s*(.+?)\s*,\s*(.+?)\s*([\]\)])\s*$")


@dataclass
class Result:
    name: str
    ok: bool = True
    points: int = 0
    max_rel_err: float = 0.0
    messages: list = field(default_factory=list)

    def fail(self, msg):
        self.ok = False
        self.messages.append(msg)


class Contract:
    def __init__(self, contract_text, symbols_text):
        self.doc = yaml.safe_load(contract_text)
        sym_doc = yaml.safe_load(symbols_text)
        self.entries = {e["id"]: e for e in sym_doc["symbols"]}
        self.syms = {k: sp.Symbol(k, real=True) for k in self.entries}
        self.functions = {f["name"]: f for f in self.doc["functions"]}

    # ------------------------------------------------------------ parsing
    def expand(self, text, stack=()):
        def repl(m):
            name = m.group(1)
            if name in stack:
                raise ValueError("circular reference @%s" % name)
            return "(" + self.expand(str(self.functions[name]["expression"]), stack + (name,)) + ")"
        return re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", repl, str(text))

    def parse(self, text):
        d = dict(FUNCS)
        d.update(self.syms)
        return sp.parse_expr(self.expand(text), local_dict=d, evaluate=True)

    def numeric(self, expr):
        return expr.subs({self.syms[k]: v for k, v in CONSTANT_VALUES.items() if k in self.syms})

    def interval(self, symbol, overrides=None):
        text = (overrides or {}).get(symbol) or self.entries[symbol]["interval"]
        m = _INTERVAL.match(str(text))
        if not m:
            raise ValueError("cannot parse interval %r of %s" % (text, symbol))
        lo = float(sp.sympify(m.group(2), locals=FUNCS))
        hi = float(sp.sympify(m.group(3), locals=FUNCS))
        return m.group(1), lo, hi, m.group(4)

    def inputs(self, name):
        expr = self.parse(self.functions[name]["expression"])
        return sorted(str(s) for s in expr.free_symbols if str(s) not in CONSTANT_IDS)


def sample(interval, n, rng):
    """Random points in an interval; unbounded sides use fixed synthetic scales."""
    left, lo, hi, right = interval
    if math.isinf(lo) and math.isinf(hi):
        return rng.uniform(-10.0, 10.0, n)
    if math.isinf(hi):
        # (lo, oo) or [lo, oo): log-uniform offset above lo, with lo itself for closed ends.
        x = lo + np.exp(rng.uniform(np.log(1e-3), np.log(1e3), n)) if lo > 0 or left == "(" else \
            rng.uniform(lo, lo + 10.0, n)
        if lo == 0 and left == "(":
            x = np.exp(rng.uniform(np.log(1e-2), np.log(1e2), n))
        return x
    if math.isinf(lo):
        return hi - np.exp(rng.uniform(np.log(1e-3), np.log(1e3), n))
    x = rng.uniform(lo, hi, n)
    if left == "(" or right == ")":
        x = np.clip(x, np.nextafter(lo, hi), np.nextafter(hi, lo))
    return x


def _draw(contract, name, n, rng):
    f = contract.functions[name]
    names = contract.inputs(name)
    pts = {s: sample(contract.interval(s, f.get("domains")), n, rng) for s in names}
    entry = FUNCTIONS[name]
    if entry.valid is not None:
        ok = np.asarray(entry.valid(**{a: pts[a] for a in entry.args}), dtype=bool)
        pts = {k: v[ok] for k, v in pts.items()}
        return pts, ok
    return pts, np.ones(n, dtype=bool)


def _reference(contract, expr, names):
    syms = [contract.syms[s] for s in names]
    return sp.lambdify(syms, contract.numeric(expr), "numpy")


def _reference_hp(contract, expr, names, pts):
    """The contract expression evaluated at the sampled float inputs with 40-digit arithmetic."""
    import mpmath
    f = sp.lambdify([contract.syms[s] for s in names], contract.numeric(expr), "mpmath")
    npts = len(next(iter(pts.values())))
    out = np.empty(npts)
    with mpmath.workdps(HP_DIGITS):
        for i in range(npts):
            try:
                v = mpmath.mpmathify(f(*[mpmath.mpf(float(pts[s][i])) for s in names]))
                out[i] = float(mpmath.re(v)) if abs(mpmath.im(v)) <= abs(v) * mpmath.mpf(10) ** -30 else np.nan
            except (ZeroDivisionError, OverflowError, ValueError):
                out[i] = np.nan
    return out


def _impl(name, pts):
    entry = FUNCTIONS[name]
    return np.asarray(entry.impl(*[pts[a] for a in entry.args]), dtype=float)


def check_function(contract, name, n=256, seed=0):
    """Compare implementation and contract expression of one function at n random points."""
    res = Result(name)
    if name not in FUNCTIONS:
        res.fail("no implementation registered")
        return res
    names = contract.inputs(name)
    if sorted(FUNCTIONS[name].args) != names:
        res.fail("argument set %s differs from contract inputs %s" % (sorted(FUNCTIONS[name].args), names))
        return res
    rng = np.random.default_rng([seed, sum(map(ord, name))])
    pts, mask = _draw(contract, name, n, rng)
    if len(next(iter(pts.values()))) < n // 4:
        res.fail("too few valid points (%d)" % len(next(iter(pts.values()))))
        return res
    expr = contract.parse(contract.functions[name]["expression"])
    ref = np.asarray(_reference(contract, expr, names)(*[pts[s] for s in names]), dtype=float)
    ref = np.broadcast_to(ref, next(iter(pts.values())).shape)
    got = _impl(name, pts)
    finite = np.isfinite(ref)
    if not np.all(finite):
        res.fail("contract expression not finite at %d sampled points" % int((~finite).sum()))
    # Accuracy is judged against the 40-digit evaluation of the contract expression. A point
    # passes when the implementation is within RTOL of it, or, where the expression itself is
    # ill-conditioned (cancellation between large terms), when the implementation is no less
    # accurate than the direct floating-point evaluation of the contract expression (within a
    # factor CONDITIONING). The second clause never excuses an implementation that is worse
    # than the contract's own formula.
    hp = _reference_hp(contract, expr, names, {k: np.asarray(v)[finite] for k, v in pts.items()})
    ok_hp = np.isfinite(hp)
    g, r, h = got[finite][ok_hp], ref[finite][ok_hp], hp[ok_hp]
    scale = np.maximum(np.abs(h), np.finfo(float).tiny)
    err_impl, err_float = np.abs(g - h), np.abs(r - h)
    passes = (err_impl <= RTOL * scale) | (err_impl <= CONDITIONING * err_float)
    res.points = int(ok_hp.sum())
    res.max_rel_err = float((err_impl / scale).max()) if g.size else 0.0
    conditioned = int(((err_impl > RTOL * scale) & passes).sum())
    if conditioned:
        res.messages.append("%d point(s) beyond rtol %.0e where the contract expression is ill-conditioned; "
                            "the implementation is at least as accurate as its direct evaluation "
                            "(max float-reference error %.3e)" % (conditioned, RTOL, float((err_float / scale).max())))
    if not np.all(passes):
        res.fail("max relative error %.3e exceeds %.0e against the high-precision reference" % (res.max_rel_err, RTOL))
    if not np.all(mask):
        # The points the implementation rejects must raise ValueError, never return a number.
        rng2 = np.random.default_rng([seed, 1, sum(map(ord, name))])
        bad = {s: sample(contract.interval(s, contract.functions[name].get("domains")), n, rng2) for s in names}
        keep = ~np.asarray(FUNCTIONS[name].valid(**{a: bad[a] for a in FUNCTIONS[name].args}), dtype=bool)
        for i in np.flatnonzero(keep)[:5]:
            try:
                _impl(name, {k: v[i] for k, v in bad.items()})
            except ValueError:
                continue
            res.fail("implementation returned a value outside its physical domain")
            break
    return res


# ------------------------------------------------------------------ limits and monotonicity
def _point(contract, name, rng, domains=None):
    f = contract.functions[name]
    over = dict(f.get("domains") or {})
    over.update(domains or {})
    for _ in range(200):
        p = {s: float(sample(contract.interval(s, over), 1, rng)[0]) for s in contract.inputs(name)}
        e = FUNCTIONS[name]
        if e.valid is None or bool(e.valid(**{a: p[a] for a in e.args})):
            return p
    raise RuntimeError("no valid point for %s" % name)


def _value(contract, text, p):
    expr = contract.numeric(contract.parse(text))
    if expr in (sp.oo, -sp.oo):
        return float(expr)
    return float(expr.subs({contract.syms[k]: v for k, v in p.items()}))


def _substitute_at(contract, at, p):
    p = dict(p)
    for k, v in at.items():
        p[k] = _value(contract, str(v), p)
    return p


def check_limits(contract, name, seed=0):
    """Reproduce the contract's limit cases numerically on the implementation.

    Divergent limits may overflow to inf (for example E_enr as Delta_G_seq -> -oo); that is
    the expected value, so floating-point overflow warnings are silenced here.
    """
    with np.errstate(over="ignore"):
        return _check_limits(contract, name, seed)


def _check_limits(contract, name, seed):
    res = Result(name)
    rng = np.random.default_rng([seed, 2, sum(map(ord, name))])
    for case in contract.functions[name].get("limits") or []:
        base = _point(contract, name, rng)
        # Symbols that the case's substitutions or expected value name but the function does
        # not take (N_nuc at DG_het = @B_acc brings in N_req) are drawn from their intervals.
        texts = [str(v) for v in (case.get("at") or {}).values()] + [str(case.get("expected", "0"))]
        extra = set()
        for t in texts:
            extra |= {str(x) for x in contract.parse(t).free_symbols}
        for sym in sorted(extra - set(base) - CONSTANT_IDS):
            base[sym] = float(sample(contract.interval(sym), 1, rng)[0])
        p = _substitute_at(contract, case.get("at") or {}, base)
        expected = _value(contract, str(case["expected"]), p) if "limit" not in case else None
        if "limit" not in case:
            got = float(_impl(name, p))
            if not math.isclose(got, expected, rel_tol=1e-9, abs_tol=1e-12 * max(1.0, abs(got))):
                res.fail("at %s: got %r, expected %r" % (case["at"], got, expected))
            res.points += 1
            continue
        lim = case["limit"]
        var, to = lim["var"], str(lim["to"])
        target = float(sp.sympify(to, locals=FUNCS))
        seq = []
        # Towards infinity the exponents double (10^4 ... 10^256) so that logarithmic
        # approaches such as 1 / ln(Omega) are resolved; towards a finite point the step
        # shrinks geometrically.
        for k in range(2, 9):
            q = dict(p)
            if math.isinf(target):
                q[var] = math.copysign(10.0 ** (2 ** k), target)
            else:
                step = 10.0 ** (-k) * max(1.0, abs(target))
                q[var] = target + (step if lim.get("dir", "+") == "+" else -step)
            seq.append((q, float(_impl(name, q))))
        exp_text = str(case["expected"])
        exp_val = _value(contract, exp_text, seq[-1][0]) if exp_text not in ("oo", "-oo") else float(exp_text.replace("oo", "inf"))
        vals = np.array([v for _, v in seq])
        if math.isinf(exp_val):
            if not (np.all(np.sign(vals[-3:]) == math.copysign(1, exp_val))
                    and (np.isinf(vals[-1]) or abs(vals[-1]) > 1e3 * abs(vals[0]))):
                res.fail("limit %s -> %s: values %s do not diverge" % (var, to, vals))
        else:
            err = np.abs(vals - np.array([_value(contract, exp_text, q) for q, _ in seq]))
            # The error to the expected value must shrink monotonically, by at least tenfold.
            # ... or every error already sits at the rounding floor of the expected value.
            floor = np.all(err <= 1e-12 * abs(exp_val)) if exp_val != 0 else False
            if not floor and not (np.all(np.diff(err) <= 1e-15 * max(1.0, abs(exp_val))) and err[-1] <= 0.1 * err[0] + 1e-300):
                res.fail("limit %s -> %s: error %s does not shrink to the expected value" % (var, to, err))
        res.points += 1
    return res


def check_monotonicity(contract, name, n=64, seed=0):
    """Check each monotonicity statement of the contract by finite perturbation."""
    res = Result(name)
    rng = np.random.default_rng([seed, 3, sum(map(ord, name))])
    for stmt in contract.functions[name].get("monotonicity") or []:
        if stmt.get("subs"):
            res.messages.append("skipped %s (reparametrised statement; proven by the theory checker)" % stmt["wrt"])
            continue
        wrt, direction = stmt["wrt"], stmt["direction"]
        for _ in range(n):
            p = _point(contract, name, rng, stmt.get("domains"))
            h = 1e-6 * max(1.0, abs(p[wrt]))
            q = dict(p)
            q[wrt] = p[wrt] + h
            e = FUNCTIONS[name]
            if e.valid is not None and not bool(e.valid(**{a: q[a] for a in e.args})):
                continue
            try:
                d = float(_impl(name, q)) - float(_impl(name, p))
            except ValueError:
                continue
            tol = 1e-12 * max(1.0, abs(float(_impl(name, p))))
            up = direction in ("increasing", "nondecreasing")
            if (up and d < -tol) or (not up and d > tol):
                res.fail("not %s in %s at %s" % (direction, wrt, p))
                break
            res.points += 1
    return res


def check_constants():
    """The contract's constant relations R = N_A k_B and F = N_A e hold for the constants used."""
    return (math.isclose(C.GAS_CONSTANT, C.AVOGADRO * C.BOLTZMANN, rel_tol=1e-15)
            and math.isclose(C.FARADAY, C.AVOGADRO * C.ELEMENTARY_CHARGE, rel_tol=1e-15))


def check_all(contract_text, symbols_text, n=256, seed=0):
    """Run every check; returns (ok, {function: [Result, ...]}, coverage messages)."""
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        return _check_all(contract_text, symbols_text, n, seed)


def _check_all(contract_text, symbols_text, n, seed):
    contract = Contract(contract_text, symbols_text)
    results = {}
    coverage = []
    missing = sorted(set(contract.functions) - set(FUNCTIONS))
    extra = sorted(set(FUNCTIONS) - set(contract.functions))
    if missing:
        coverage.append("contract functions without implementation: %s" % missing)
    if extra:
        coverage.append("registered functions not in the contract: %s" % extra)
    for name in contract.functions:
        if name not in FUNCTIONS:
            continue
        results[name] = [check_function(contract, name, n, seed), check_limits(contract, name, seed),
                         check_monotonicity(contract, name, seed=seed)]
    results["DG_het_template"] = [check_composite(contract, n, seed)]
    if not check_constants():
        coverage.append("constant relations R = N_A k_B, F = N_A e do not hold")
    ok = not coverage and all(r.ok for rs in results.values() for r in rs)
    return ok, results, coverage


def composite_expression(contract):
    """The contract's no_double_counting composite with its channel definitions substituted."""
    ndc = contract.doc["no_double_counting"]
    local = dict(FUNCS)
    local.update(contract.syms)
    aux = {}
    for chan in ("channel_omega", "channel_theta"):
        for k in ndc[chan]:
            aux.setdefault(k, sp.Symbol(k, real=True))
    local.update(aux)
    expr = sp.parse_expr(" ".join(str(ndc["composite_expression"]).split()), local_dict=local)
    for _ in range(4):  # channel definitions refer to each other (c_young -> D_ads -> x_b)
        for chan in ("channel_theta", "channel_omega"):
            for k, v in ndc[chan].items():
                expr = expr.subs(aux[k], sp.parse_expr(str(v), local_dict=local))
    return expr


def check_composite(contract, n=256, seed=0):
    """Compare template_heterogeneous_barrier with the contract composite at random points."""
    from nacre.physics.template import COMPOSITE_ARGS, template_heterogeneous_barrier
    res = Result("DG_het_template")
    expr = composite_expression(contract)
    names = sorted(str(s) for s in expr.free_symbols if str(s) not in CONSTANT_IDS)
    if sorted(COMPOSITE_ARGS) != names:
        res.fail("composite inputs %s differ from implementation %s" % (names, sorted(COMPOSITE_ARGS)))
        return res
    rng = np.random.default_rng([seed, 4])
    pts = {s: sample(contract.interval(s), 4 * n, rng) for s in names}
    from nacre.physics.supersaturation import saturation_ratio_bulk
    from nacre.physics.template import contact_angle_cosine_template
    # valid points: a finite contact angle on the template and a supersaturated bulk
    with np.errstate(all="ignore"):
        ratio = contact_angle_cosine_template(*[pts[a] for a in ("gamma_sl0", "gamma_sn0", "Delta_gamma_w", "gamma_nl",
                                                                 "Delta_G_seq", "T", "c_bulk", "Gamma_s", "delta_s")])
        om = saturation_ratio_bulk(pts["a_Ca"], pts["a_CO3"], pts["K_sp"])
    ok = np.isfinite(ratio) & (np.abs(ratio) <= 1) & np.isfinite(om) & (om > 1)
    pts = {k: v[ok][:n] for k, v in pts.items()}
    ref = np.asarray(_reference(contract, expr, names)(*[pts[s] for s in names]), dtype=float)
    got = np.asarray(template_heterogeneous_barrier(*[pts[a] for a in COMPOSITE_ARGS]), dtype=float)
    fin = np.isfinite(ref)
    rel = np.abs(got[fin] - ref[fin]) / np.maximum(np.abs(ref[fin]), np.finfo(float).tiny)
    res.points = int(fin.sum())
    res.max_rel_err = float(rel.max()) if rel.size else 0.0
    if res.points < n // 4:
        res.fail("too few valid composite points (%d)" % res.points)
    if res.max_rel_err > RTOL:
        res.fail("max relative error %.3e exceeds %.0e" % (res.max_rel_err, RTOL))
    return res
