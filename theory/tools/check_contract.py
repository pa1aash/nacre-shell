"""Check theory/contract.yaml against theory/symbols.yaml.

Run from the repository root:

    uv run python theory/tools/check_contract.py

What is checked
  1. symbols.yaml: every entry has the required fields, a parsable unit and interval.
  2. Every contract expression parses with sympy and uses only registered symbol ids
     (aux_* reparametrisation variables, pi and the elementary functions excepted).
  3. Dimensions: every expression is dimensionally consistent (sums of like terms,
     dimensionless arguments of exp, log and the trigonometric functions) and has the
     declared SI unit.
  4. Limit cases are evaluated exactly (substitution or sympy limits).
  5. Identities and derivative identities simplify to zero difference.
  6. Bounds: exact extrema of univariate expressions over the stated interval.
  7. Inequalities and monotonicity: the sign of the difference or derivative is proven
     symbolically from the symbol intervals where possible; a statement that cannot be
     proven symbolically is checked on an exact rational grid and labelled "grid".
  8. Sign-flip tests: SF1 (water displacement), SF2 (the channel through which Delta_G_seq
     reaches the barrier, registered against the local-ideal alternative), SF3 (lane note
     N3: the direction in which gamma_nl moves f, for both signs of gamma_sl - gamma_sn) and
     SF4 (D27: the admissible set gamma_sl >= 0 is an upper set in Delta_G_seq, and the
     clipped and floored alternatives put a non-existent interface on the bad side of C3 (a)).
  9. The no-double-counting condition of contract v2: every template input enters the theta
     channel only, the Omega channel holds bulk inputs only, the Ca2+ binding inputs reach the
     composite only through Delta_gamma_ads, and the named demonstrations reduce to the
     composites they are built from.
 10. The version changelog names only functions that exist (added, changed) or are gone
     (removed).
 11. theory/thresholds.md: its fenced `thresholds` block parses, every edge uses registered ids
     and has the unit of its quantity, every registration constant has a params key, every
     params key appears in the file's key table, a non-gating link is a descriptor with no
     verdict test, and the study rule and deletion test name only gating links; each C5 R-cell
     margin route names the params path its test uses, and a route formula has its margin's unit;
     the admissibility rule (D27) holds a contract quantity against an edge of its unit, and an
     analog route names only contract functions and registered params symbols.
 12. theory/ignorance_priors.md: its fenced `ignorance` block parses, every bound has the unit of
     its quantity, and the branch masses of the gamma_sn prior are the exact integrals of the
     uniform density over the three Young branches and sum to one; the favourable (C3 (a)) mass
     is the integral up to its cut, and the admissibility condition has the unit of an energy per
     area.
 13. No literature number in theory/** sources (decimals, exponent notation or integers of
     three or more digits outside an allowlist).

Exit status 0 when every check passes, 1 otherwise.
"""

import itertools
import re
import sys
from pathlib import Path

import sympy as sp
import yaml
from sympy.calculus.util import maximum, minimum

ROOT = Path(__file__).resolve().parents[2]
THEORY = ROOT / "theory"

FUNCS = {
    "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "cos": sp.cos, "sin": sp.sin,
    "tan": sp.tan, "acos": sp.acos, "asin": sp.asin, "atan": sp.atan, "pi": sp.pi,
    "oo": sp.oo,
}

# ----------------------------------------------------------------------------- units

BASE = ("kg", "m", "s", "A", "K", "mol")
UNITS = {
    "1": (0, 0, 0, 0, 0, 0), "rad": (0, 0, 0, 0, 0, 0),
    "kg": (1, 0, 0, 0, 0, 0), "m": (0, 1, 0, 0, 0, 0), "s": (0, 0, 1, 0, 0, 0),
    "A": (0, 0, 0, 1, 0, 0), "K": (0, 0, 0, 0, 1, 0), "mol": (0, 0, 0, 0, 0, 1),
    "J": (1, 2, -2, 0, 0, 0), "C": (0, 0, 1, 1, 0, 0), "V": (1, 2, -3, -1, 0, 0),
    "Ohm": (1, 2, -3, -2, 0, 0),
}
DIMLESS = tuple(sp.Integer(0) for _ in BASE)


def parse_unit(text):
    dim = [sp.Integer(0)] * len(BASE)
    for tok in str(text).split():
        name, _, power = tok.partition("^")
        if name not in UNITS:
            raise ValueError("unknown unit %r in %r" % (name, text))
        p = sp.Rational(power) if power else sp.Integer(1)
        dim = [d + p * u for d, u in zip(dim, UNITS[name])]
    return tuple(dim)


def fmt_dim(dim):
    parts = ["%s^%s" % (b, e) if e != 1 else b for b, e in zip(BASE, dim) if e != 0]
    return " ".join(parts) or "1"


class DimError(Exception):
    pass


def dimension(expr, dims):
    """Dimension vector of a sympy expression; raises DimError on inconsistency."""
    if expr.is_Symbol:
        if expr.name.startswith("aux_"):
            raise DimError("aux symbol %s inside a dimensional expression" % expr.name)
        return dims[expr.name]
    if expr.is_Number or expr in (sp.pi, sp.E, sp.oo, -sp.oo, sp.zoo):
        return DIMLESS
    if expr.is_Add:
        ds = [dimension(a, dims) for a in expr.args]
        for d in ds[1:]:
            if d != ds[0]:
                raise DimError("sum of unlike terms in %s: %s vs %s" % (expr, fmt_dim(ds[0]), fmt_dim(d)))
        return ds[0]
    if expr.is_Mul:
        out = list(DIMLESS)
        for a in expr.args:
            out = [x + y for x, y in zip(out, dimension(a, dims))]
        return tuple(out)
    if expr.is_Pow:
        b, e = expr.args
        db = dimension(b, dims)
        if e.is_Number:
            return tuple(x * e for x in db)
        if dimension(e, dims) != DIMLESS or db != DIMLESS:
            raise DimError("non-numeric exponent needs dimensionless base and exponent: %s" % expr)
        return DIMLESS
    if isinstance(expr, sp.Function):
        for a in expr.args:
            if dimension(a, dims) != DIMLESS:
                raise DimError("argument of %s is not dimensionless: %s" % (expr.func, a))
        return DIMLESS
    raise DimError("cannot take the dimension of %s" % expr)


# ----------------------------------------------------------------------------- intervals

def parse_interval(text):
    m = re.fullmatch(r"\s*([\[(])\s*(.+?)\s*,\s*(.+?)\s*([\])])\s*", str(text))
    if not m:
        raise ValueError("bad interval %r" % text)
    lo, hi = sp.sympify(m.group(2), locals=FUNCS), sp.sympify(m.group(3), locals=FUNCS)
    return lo, hi, m.group(1) == "(", m.group(4) == ")"


def assumptions_for(interval):
    lo, hi, lo_open, _ = interval
    if lo == 0 and hi == sp.oo:
        return {"positive": True} if lo_open else {"nonnegative": True}
    return {"real": True}


# ----------------------------------------------------------------------------- context

class Context:
    def __init__(self, symbols_doc, contract):
        self.entries = {e["id"]: e for e in symbols_doc["symbols"]}
        self.dims = {k: parse_unit(e["unit"]) for k, e in self.entries.items()}
        self.intervals = {k: parse_interval(e["interval"]) for k, e in self.entries.items()}
        self.syms = {k: sp.Symbol(k, **assumptions_for(iv)) for k, iv in self.intervals.items()}
        self.functions = {f["name"]: f for f in contract["functions"]}
        self._expanded = {}

    def local_dict(self, extra=()):
        d = dict(FUNCS)
        d.update(self.syms)
        for name in extra:
            d.setdefault(name, sp.Symbol(name, real=True))
        return d

    def expand_refs(self, text, stack=()):
        def repl(m):
            name = m.group(1)
            if name not in self.functions:
                raise KeyError("unknown function reference @%s" % name)
            if name in stack:
                raise ValueError("circular function reference @%s" % name)
            return "(" + self.expand_refs(str(self.functions[name]["expression"]), stack + (name,)) + ")"
        return re.sub(r"@([A-Za-z_][A-Za-z0-9_]*)", repl, str(text))

    def parse(self, text):
        text = self.expand_refs(text)
        names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
        unknown = sorted(n for n in names if n not in FUNCS and n not in self.syms and not n.startswith("aux_"))
        if unknown:
            raise KeyError("unregistered symbol(s): " + ", ".join(unknown))
        aux = {n: sp.Symbol(n, positive=True) for n in names if n.startswith("aux_")}
        d = self.local_dict()
        d.update(aux)
        return sp.parse_expr(text, local_dict=d, evaluate=True)

    def subs_map(self, mapping):
        return {self.syms[k]: self.parse(v) for k, v in (mapping or {}).items()}

    def domain_symbols(self, expr, overrides=None):
        """Replace symbols by fresh ones that carry the interval as an assumption.

        Returns (expr', bounded) where bounded maps fresh symbol -> (lo, hi) for
        symbols on a finite or shifted interval, which need interval reasoning.
        """
        overrides = {k: parse_interval(v) for k, v in (overrides or {}).items()}
        rep, bounded = {}, {}
        for s in expr.free_symbols:
            if s.name.startswith("aux_"):
                continue
            lo, hi, lo_open, hi_open = overrides.get(s.name, self.intervals[s.name])
            if lo == 0 and hi == sp.oo:
                rep[s] = sp.Symbol(s.name + "_d", positive=True) if lo_open else sp.Symbol(s.name + "_d", nonnegative=True)
            elif hi == sp.oo and lo != -sp.oo:
                u = sp.Symbol(s.name + "_u", positive=True) if lo_open else sp.Symbol(s.name + "_u", nonnegative=True)
                rep[s] = lo + u
            elif lo == -sp.oo and hi == sp.oo:
                rep[s] = sp.Symbol(s.name + "_d", real=True)
            elif lo == -sp.oo:
                # a half-line below a finite end, for example a binding free energy below zero
                u = sp.Symbol(s.name + "_u", positive=True) if hi_open else sp.Symbol(s.name + "_u", nonnegative=True)
                rep[s] = hi - u
            else:
                t = sp.Symbol(s.name + "_d", real=True)
                rep[s] = t
                bounded[t] = (lo, hi, lo_open, hi_open)
        return expr.xreplace(rep), bounded


# ----------------------------------------------------------------------------- sign proofs

def _sign_of(expr, bounded):
    """Return one of 'pos', 'nonneg', 'neg', 'nonpos', 'zero' or None."""
    e = sp.factor(sp.simplify(expr))
    if e == 0:
        return "zero"
    if e.is_positive:
        return "pos"
    if e.is_negative:
        return "neg"
    if e.is_nonnegative:
        return "nonneg"
    if e.is_nonpositive:
        return "nonpos"
    free = [s for s in e.free_symbols if s in bounded]
    if len(free) == 1 and e.free_symbols == set(free):
        t = free[0]
        lo, hi, lo_open, hi_open = bounded[t]
        iv = sp.Interval(lo, hi, lo_open, hi_open)
        mn, mx = minimum(e, t, iv), maximum(e, t, iv)
        if mn.is_nonnegative:
            return "pos" if (mn.is_positive or (lo_open and hi_open and mn == 0 and _attained_only_at_ends(e, t, lo, hi))) else "nonneg"
        if mx.is_nonpositive:
            return "neg" if mx.is_negative else "nonpos"
        return None
    if e.is_Mul or e.is_Pow:
        factors = sp.Mul.make_args(e) if e.is_Mul else (e,)
        signs = []
        for fct in factors:
            if fct.is_Pow and fct.exp.is_Integer and fct.exp % 2 == 0:
                s = _sign_of(fct.base, bounded)
                signs.append("pos" if s in ("pos", "neg") else "nonneg")
                continue
            if fct.is_Pow and fct.exp.is_Integer:
                s = _sign_of(fct.base, bounded)
                signs.append(s)
                continue
            if fct.is_Mul or fct is e:
                return None
            signs.append(_sign_of(fct, bounded))
        if None in signs:
            return None
        if "zero" in signs:
            return "zero"
        neg = sum(s in ("neg", "nonpos") for s in signs) % 2 == 1
        strict = all(s in ("pos", "neg") for s in signs)
        return ("neg" if strict else "nonpos") if neg else ("pos" if strict else "nonneg")
    return None


def _attained_only_at_ends(e, t, lo, hi):
    crit = sp.solveset(e, t, sp.Interval.open(lo, hi))
    return crit == sp.S.EmptySet


def _grid_sign(expr, bounded):
    vals = []
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    def samples(s):
        if s in bounded:
            lo, hi, _, _ = bounded[s]
            return [lo + (hi - lo) * sp.Rational(k, 8) for k in range(1, 8)]
        if s.is_positive or s.is_nonnegative:
            return [sp.Rational(1, 3), sp.Rational(1), sp.Rational(5, 2), sp.Integer(7)]
        return [sp.Rational(-5, 2), sp.Rational(-1, 3), sp.Rational(1, 2), sp.Integer(3)]
    for combo in itertools.product(*[samples(s) for s in syms]):
        v = sp.N(expr.subs(dict(zip(syms, combo))), 30)
        if v.is_real:
            vals.append(v)
    if not vals:
        return None
    if all(v > 0 for v in vals):
        return "pos"
    if all(v >= 0 for v in vals):
        return "nonneg"
    if all(v < 0 for v in vals):
        return "neg"
    if all(v <= 0 for v in vals):
        return "nonpos"
    return "mixed"


ACCEPT = {
    "positive": {"pos"}, "nonnegative": {"pos", "nonneg", "zero"},
    "negative": {"neg"}, "nonpositive": {"neg", "nonpos", "zero"},
}


def prove_sign(ctx, expr, want, domains=None):
    e, bounded = ctx.domain_symbols(expr, domains)
    s = _sign_of(e, bounded)
    if s is not None:
        return s in ACCEPT[want], "symbolic (%s)" % s
    g = _grid_sign(e, bounded)
    return g in ACCEPT[want], "grid (%s)" % g


# ----------------------------------------------------------------------------- checks

class Report:
    def __init__(self):
        self.lines, self.failures, self.counts = [], 0, {}

    def add(self, ok, kind, what, detail=""):
        self.counts.setdefault(kind, [0, 0])
        self.counts[kind][0 if ok else 1] += 1
        if not ok:
            self.failures += 1
        self.lines.append("%s  %-13s %s%s" % ("PASS" if ok else "FAIL", kind, what, ("  [" + detail + "]") if detail else ""))


def zero(expr):
    for f in (sp.simplify, lambda x: sp.simplify(sp.expand_log(x, force=True)),
              lambda x: sp.simplify(sp.trigsimp(sp.expand_trig(x))), lambda x: sp.nsimplify(sp.simplify(x)),
              lambda x: sp.simplify(x.replace(lambda e: e.is_Pow and e.exp == sp.Rational(1, 2),
                                              lambda e: sp.sqrt(sp.factor(e.base))))):
        try:
            if f(expr) == 0:
                return True
        except Exception:
            pass
    return False


TINY = float(sp.Integer(10) ** -20)


def numeric_zero(expr, points=6):
    """Fast equality test: the expression vanishes at exact rational points (no simplify).

    Every free symbol gets a positive rational value; the check fails on the first point
    whose value is not zero to 30 digits. Used where a symbolic simplification of a wrong
    identity can run for minutes.
    """
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    vals = [sp.Rational(2 + k, 3 + 2 * k) for k in range(points)]
    for i in range(points):
        sub = {s: vals[(i + j) % points] + 1 + j for j, s in enumerate(syms)}
        v = sp.N(expr.subs(sub), 30)
        if not (v.is_number and abs(complex(v)) < TINY):
            return False
    return True


def check_symbols(doc, rep):
    need = ("id", "latex", "meaning", "unit", "sign", "interval", "domain", "regimes", "kind")
    seen = set()
    for e in doc["symbols"]:
        miss = [k for k in need if k not in e]
        ok = not miss and e["id"] not in seen
        try:
            parse_unit(e["unit"])
            parse_interval(e["interval"])
        except Exception as exc:
            ok, miss = False, miss + [str(exc)]
        bad_reg = [r for r in e.get("regimes", []) if r not in ("R-slurry", "R-cell", "both")]
        ok = ok and not bad_reg
        seen.add(e.get("id"))
        if not ok:
            rep.add(False, "symbol", e.get("id", "?"), "; ".join(map(str, miss + bad_reg)))
    rep.add(True, "symbols", "%d entries with id, latex, meaning, unit, sign, interval, domain, regimes, kind" % len(seen))


def check_function(ctx, f, rep):
    name = f["name"]
    try:
        expr = ctx.parse(f["expression"])
    except Exception as exc:
        rep.add(False, "parse", name, str(exc))
        return
    rep.add(True, "parse", name, str(expr) if len(str(expr)) < 90 else "")
    # dimensions
    try:
        d = dimension(expr, ctx.dims)
        want = parse_unit(f["unit"])
        rep.add(d == want, "dimension", name, "%s, declared %s" % (fmt_dim(d), f["unit"]))
    except DimError as exc:
        rep.add(False, "dimension", name, str(exc))
    domains = f.get("domains")

    for lim in f.get("limits", []):
        try:
            e = expr
            if "at" in lim:
                e = e.subs(ctx.subs_map(lim["at"]))
            expected = ctx.parse(lim["expected"])
            if "limit" in lim:
                L = lim["limit"]
                var = ctx.syms[L["var"]]
                to = ctx.parse(str(L["to"]))
                val = sp.limit(e, var, to, L.get("dir", "+") if to not in (sp.oo, -sp.oo) else "+")
                expected2 = expected
                ok = (val == expected2) if expected2 in (sp.oo, -sp.oo) else zero(val - expected2)
                rep.add(ok, "limit", name, "%s -> %s%s: %s (expected %s)" % (
                    L["var"], L["to"], L.get("dir", ""), val, lim["expected"]))
            else:
                ok = zero(e - expected)
                rep.add(ok, "limit", name, "at %s: %s (expected %s)" % (lim["at"], sp.simplify(e), lim["expected"]))
        except Exception as exc:
            rep.add(False, "limit", name, "%s: %s" % (lim, exc))

    for idt in f.get("identities", []):
        try:
            e = expr.subs(ctx.subs_map(idt.get("subs")))
            d = e - ctx.parse(idt["equals"])
            ok = numeric_zero(d) if idt.get("numeric") else zero(d)
            rep.add(ok, "identity", name, idt.get("note", idt["equals"]))
        except Exception as exc:
            rep.add(False, "identity", name, str(exc))

    for idt in f.get("derivative_identities", []):
        ok = zero(sp.diff(expr, ctx.syms[idt["wrt"]]) - ctx.parse(idt["equals"]))
        rep.add(ok, "identity", name, "d/d%s = %s" % (idt["wrt"], idt["equals"]))

    for b in f.get("bounds", []):
        try:
            e = sp.simplify(sp.cancel(ctx.parse(b["expr"])))
            t = ctx.syms[b["var"]]
            free = e.free_symbols - {t}
            if free:
                raise ValueError("not univariate in %s: %s" % (b["var"], free))
            lo, hi, lo_open, hi_open = parse_interval(b["interval"])
            iv = sp.Interval(lo, hi, lo_open, hi_open)
            mn, mx = sp.simplify(minimum(e, t, iv)), sp.simplify(maximum(e, t, iv))
            ok = zero(mn - ctx.parse(b["min"])) and zero(mx - ctx.parse(b["max"]))
            rep.add(ok, "bound", name, "%s on %s: min %s, max %s" % (b["expr"], b["interval"], mn, mx))
        except Exception as exc:
            rep.add(False, "bound", name, str(exc))

    for q in f.get("inequalities", []):
        lhs, rhs = ctx.parse(q["expr"]), ctx.parse(q["rhs"])
        if q.get("subs"):
            # restrict the domain by reparametrisation, as for monotonicity
            lhs, rhs = lhs.subs(ctx.subs_map(q["subs"])), rhs.subs(ctx.subs_map(q["subs"]))
        diff, want = (rhs - lhs, "nonnegative") if q["relation"] in ("<=", "<") else (lhs - rhs, "nonnegative")
        if q["relation"] in ("<", ">"):
            want = "positive"
        ok, how = prove_sign(ctx, diff, want, q.get("domains", domains))
        rep.add(ok, "inequality", name, "%s %s %s, %s" % (q["expr"], q["relation"], q["rhs"], how))

    for m in f.get("monotonicity", []):
        e = expr.subs(ctx.subs_map(m.get("subs"))) if m.get("subs") else expr
        der = sp.diff(e, ctx.syms[m["wrt"]])
        want = {"increasing": "positive", "nondecreasing": "nonnegative",
                "decreasing": "negative", "nonincreasing": "nonpositive"}[m["direction"]]
        dom = dict(domains or {})
        dom.update(m.get("domains") or {})
        ok, how = prove_sign(ctx, der, want, dom)
        rep.add(ok, "monotonicity", name, "%s in %s, %s" % (m["direction"], m["wrt"], how))


def check_constants(ctx, contract, rep):
    for c in contract.get("constant_relations", []):
        try:
            ok = dimension(ctx.parse(c["lhs"]), ctx.dims) == dimension(ctx.parse(c["rhs"]), ctx.dims)
        except DimError as exc:
            ok = False
        rep.add(ok, "constant", "%s = %s" % (c["lhs"], c["rhs"]), "dimensions agree" if ok else "dimension mismatch")


def _fcos(c):
    return (2 + c) * (1 - c) ** 2 / 4


def check_sign_flips(ctx, contract, rep):
    for sf in contract.get("sign_flips", []):
        kind = sf.get("kind", "young_cos")
        if kind == "young_cos":
            _sf_young_cos(ctx, sf, rep)
        elif kind == "channel":
            _sf_channel(ctx, sf, rep)
        elif kind == "gamma_nl":
            _sf_gamma_nl(ctx, sf, rep)
        elif kind == "admissibility":
            _sf_admissibility(ctx, sf, rep)
        else:
            rep.add(False, "sign-flip", sf["id"], "unknown kind %r" % kind)


def _sf_young_cos(ctx, sf, rep):
    sid, par = sf["id"], ctx.syms[sf["parameter"]]
    d = sf["df_dcos"]
    c = sp.Symbol(d["var"], real=True)
    e = sp.parse_expr(d["expr"], local_dict={d["var"]: c})
    der = sp.factor(sp.diff(e, c))
    lo, hi, a, b = parse_interval(d["interval"])
    mx = maximum(der, c, sp.Interval(lo, hi, a, b))
    ok = mx.is_nonpositive
    rep.add(bool(ok), "sign-flip", sid, "df/dcos = %s, max on %s = %s" % (der, d["interval"], mx))
    fcos = lambda cc: e.subs(c, cc)
    for side in ("registered", "alternative"):
        spec = sf[side]
        cexpr = ctx.parse("@" + spec["cos_function"])
        dc = sp.diff(cexpr, par)
        if spec.get("reparam"):
            # differentiate first, then restrict the domain by reparametrisation
            dc = dc.subs(ctx.subs_map(spec["reparam"]))
        dc = sp.simplify(dc)
        ok, how = prove_sign(ctx, dc, spec["expected_sign"])
        rep.add(ok, "sign-flip", sid, "%s: dcos/d%s = %s is %s, %s" % (
            side, sf["parameter"], dc, spec["expected_sign"], how))
    w = sf["witness"]
    vals = ctx.subs_map(w["values"])
    dp, dm = ctx.parse(str(w["delta_plus"])), ctx.parse(str(w["delta_minus"]))
    reg = ctx.parse("@" + sf["registered"]["cos_function"]).subs(vals)
    alt = ctx.parse("@" + sf["alternative"]["cos_function"]).subs(vals)
    fr = [sp.nsimplify(fcos(reg.subs(par, x))) for x in (dp, 0, dm)]
    fa = [sp.nsimplify(fcos(alt.subs(par, x))) for x in (dp, 0)]
    ok = fr[0] > fr[1] > fr[2] and fa[0] < fa[1]
    rep.add(ok, "sign-flip", sid, "witness registered f(+,0,-) = %s; alternative f(+,0) = %s" % (fr, fa))


def _sf_channel(ctx, sf, rep):
    """SF2: Delta_G_seq reaches the barrier through gamma_sl (registered) or Omega (alternative)."""
    sid, par = sf["id"], ctx.syms[sf["parameter"]]
    reg = sf["registered"]
    cexpr = ctx.parse("@" + reg["cos_function"])
    dc = sp.diff(cexpr, par)
    rep.add(zero(dc - ctx.parse(reg["dcos_equals"])), "sign-flip", sid,
            "registered: dcos/d%s = %s" % (sf["parameter"], reg["dcos_equals"]))
    ok, how = prove_sign(ctx, dc, reg["expected_sign"])
    rep.add(ok, "sign-flip", sid, "registered: dcos/d%s is %s, %s" % (sf["parameter"], reg["expected_sign"], how))
    om = ctx.parse("@" + reg["omega_function"])
    rep.add(sp.diff(om, par) == 0, "sign-flip", sid, "registered: d%s/d%s = 0" % (reg["omega_function"], sf["parameter"]))
    # registered barrier: f(cos) times the homogeneous barrier at Omega_bulk
    B_reg = _fcos(cexpr) * ctx.parse("@DG_hom").subs(ctx.syms["Omega"], ctx.syms["Omega_bulk"])
    # the local-ideal alternative (contract v1)
    alt = sf["alternative"]
    B_alt = ctx.parse(alt["barrier"]).subs(ctx.syms["Omega"], ctx.parse(alt["omega_subs"]))
    der = sp.diff(B_alt, par)
    expect = ctx.parse(alt["derivative_equals"]).subs(sp.Symbol("aux_B", positive=True), B_alt)
    rep.add(zero(der - expect), "sign-flip", sid, "alternative: dB/d%s = 2B/(R T ln Omega_local), positive" % sf["parameter"])
    w = sf["witness"]
    vals = ctx.subs_map(w["values"])
    out = {}
    for side, B in (("registered", B_reg), ("alternative", B_alt)):
        Bw = B.subs(vals)
        Bw = Bw.subs({s: 1 for s in Bw.free_symbols if s != par})
        out[side] = [sp.N(Bw.subs(par, ctx.parse(str(x))), 30) for x in (w["delta_plus"], 0, w["delta_minus"])]
    r, a = out["registered"], out["alternative"]
    ok = r[0] < r[1] < r[2] and a[0] > a[1] > a[2]
    rep.add(ok, "sign-flip", sid, "witness registered B(+,0,-) = %s; alternative B(+,0,-) = %s" % (
        ["%.6g" % float(x) for x in r], ["%.6g" % float(x) for x in a]))


def _sf_gamma_nl(ctx, sf, rep):
    """SF3 (N3): sign of df/dgamma_nl follows the sign of gamma_sl - gamma_sn."""
    sid = sf["id"]
    g = ctx.syms["gamma_nl"]
    cexpr = ctx.parse("@" + sf["cos_function"])
    f = _fcos(cexpr)
    B = f * g ** 3
    for case in sf["cases"]:
        sub = ctx.subs_map(case["reparam"])
        df = sp.simplify(sp.diff(f, g).subs(sub))
        if case["df_sign"] == "zero":
            ok, how = zero(df), "identically zero"
        else:
            ok, how = prove_sign(ctx, df, case["df_sign"])
        rep.add(ok, "sign-flip", sid, "%s: df/dgamma_nl is %s, %s" % (case["name"], case["df_sign"], how))
        if case.get("barrier_sign"):
            dB = sp.simplify(sp.diff(B, g).subs(sub))
            ok, how = prove_sign(ctx, dB, case["barrier_sign"])
            rep.add(ok, "sign-flip", sid, "%s: d(f gamma_nl^3)/dgamma_nl is %s, %s" % (case["name"], case["barrier_sign"], how))
    w = sf["witness"]
    base = ctx.subs_map(w["values"])
    res = []
    for ex in w["excess"]:
        fs = []
        for gn in w["gamma_nl"]:
            sub = dict(base)
            sub[ctx.syms["gamma_sl"]] = ctx.parse("gamma_sn0 + Delta_gamma_w + (%s)" % ex).subs(base)
            sub[g] = ctx.parse(gn)
            fs.append(sp.nsimplify(f.subs(sub)))
        res.append(fs)
    ok = res[0][0] < res[0][1] and res[1][0] > res[1][1]
    rep.add(ok, "sign-flip", sid, "witness f at gamma_nl = %s: excess %s -> %s; excess %s -> %s" % (
        w["gamma_nl"], w["excess"][0], res[0], w["excess"][1], res[1]))


def _sf_admissibility(ctx, sf, rep):
    """SF4 (D27): the admissible set gamma_sl >= 0 is an upper set in Delta_G_seq, so conditioning on it
    removes the strongest binders only and cannot reverse SF2; the rejected forms put a draw whose
    interface does not exist on the bad side of C3 (a)."""
    sid, par = sf["id"], ctx.syms[sf["parameter"]]
    g = ctx.parse("@" + sf["function"])
    dg = sp.diff(g, par)
    rep.add(zero(dg - ctx.parse(sf["dgamma_equals"])), "sign-flip", sid,
            "d%s/d%s = %s" % (sf["function"], sf["parameter"], sf["dgamma_equals"]))
    ok, how = prove_sign(ctx, dg, "positive")
    rep.add(ok, "sign-flip", sid, "the admissible set is an upper set in %s (derivative positive, %s)" % (sf["parameter"], how))
    lim = sp.limit(g, par, -sp.oo)
    rep.add(lim == ctx.parse(str(sf["limit_strong_binding"])), "sign-flip", sid,
            "%s -> %s as %s -> -oo: every gamma_sl0 is overshot by strong enough binding" % (sf["function"], lim, sf["parameter"]))
    w = sf["witness"]
    vals = ctx.subs_map(w["values"])
    gw = g.subs(vals)
    weak, strong = (sp.N(gw.subs(par, ctx.parse(str(w[k]))), 30) for k in ("weak", "strong"))
    sn = (ctx.syms["gamma_sn0"] + ctx.syms["Delta_gamma_w"]).subs(vals)
    nl = ctx.syms["gamma_nl"].subs(vals)
    cos = lambda gsl: max(-1, min(1, (gsl - sn) / nl))
    f_clip, f_floor = sp.nsimplify(_fcos(cos(strong))), sp.nsimplify(_fcos(cos(sp.Integer(0))))
    ok = weak >= 0 and strong < 0 and f_clip == 1 and sp.Rational(1, 2) < f_floor < 1
    rep.add(ok, "sign-flip", sid, "witness gamma_sl %.4g (weak, admitted), %.4g (strong, refused); rejected forms give "
            "f = %.4g (clipped) and %.4g (floored) for a refused draw" % (float(weak), float(strong), float(f_clip), float(f_floor)))


def _resolve(ctx, text, channels, keep=()):
    """Substitute channel definitions (which may refer to each other) into text."""
    names = {k: sp.Symbol(k, real=True) for k in channels}
    d = ctx.local_dict()
    d.update(names)
    expr = sp.parse_expr(" ".join(str(text).split()), local_dict=d)
    for _ in range(len(channels) + 1):
        expr = expr.subs({names[k]: sp.parse_expr(" ".join(str(v).split()), local_dict=d)
                          for k, v in channels.items() if k not in keep})
    return expr


def _input_names(expr):
    return {s.name for s in expr.free_symbols}


def check_no_double_counting(ctx, contract, rep):
    ndc = contract["no_double_counting"]
    th, om = ndc["channel_theta"], ndc["channel_omega"]
    td, ti = set(ndc["template_dependent"]), set(ndc["template_independent"])
    theta_in = _input_names(_resolve(ctx, "c_young", th))
    omega_in = _input_names(_resolve(ctx, "Om", om))
    in_omega = sorted(td & omega_in)
    missing = sorted(td - theta_in)
    unknown = sorted((theta_in | omega_in) - td - ti)
    ok = not in_omega and not missing and not unknown
    rep.add(ok, "no-double", "template inputs partitioned",
            "theta: %s | Omega: %s%s" % (sorted(td & theta_in), sorted(omega_in),
                                         "" if ok else "; template inputs in Omega: %s; not in theta: %s; unclassified: %s"
                                         % (in_omega, missing, unknown)))
    channels = dict(th)
    channels.update(om)
    comp = _resolve(ctx, ndc["composite_expression"], channels)
    rep.add(dimension(comp, ctx.dims) == parse_unit("J"), "no-double", "composite barrier", "dimension J")
    c_y, Om = _resolve(ctx, "c_young", th), _resolve(ctx, "Om", om)
    cross = [sp.diff(Om, ctx.syms[s]) for s in td]
    rep.add(all(c == 0 for c in cross), "no-double", "Omega channel",
            "d Omega/d(every template input) = 0: the driving force is the bulk one")
    se = ndc.get("single_entry")
    if se:
        frozen = _resolve(ctx, "c_young", th, keep=(se["via"],))
        der = [sp.diff(frozen, ctx.syms[s]) for s in se["inputs"]]
        free = _input_names(frozen) & set(se["inputs"])
        rep.add(all(d == 0 for d in der) and not free, "no-double", "single entry",
                "%s reach the barrier only through %s" % (", ".join(se["inputs"]), se["via"]))
    composites = {ndc["composite"]: comp}
    for demo in contract.get("demonstrations", []):
        try:
            composites[demo["name"]] = _resolve(ctx, demo["composite_expression"], demo["channels"])
            rep.add(dimension(composites[demo["name"]], ctx.dims) == parse_unit("J"), "demonstration",
                    demo["name"], "dimension J; never used for a verdict")
        except Exception as exc:
            rep.add(False, "demonstration", demo["name"], str(exc))
    for demo in contract.get("demonstrations", []):
        for red in demo.get("reduces_to", []):
            keep = tuple(red["subs"])
            part = _resolve(ctx, demo["composite_expression"], demo["channels"], keep=keep)
            d = ctx.local_dict()
            part = part.subs({sp.Symbol(k, real=True): sp.parse_expr(str(v), local_dict=d) for k, v in red["subs"].items()})
            part = _resolve(ctx, str(part), {k: v for k, v in demo["channels"].items() if k not in keep})
            ok = red["equals"] in composites and numeric_zero(part - composites[red["equals"]])
            rep.add(ok, "demonstration", demo["name"], "with %s it equals %s" % (red["subs"], red["equals"]))
    # the local-ideal credit is exactly the binding free energy (dilute limit)
    if "DG_het_local_ideal" in composites:
        E = sp.exp(-ctx.syms["Delta_G_seq"] / (ctx.syms["R_gas"] * ctx.syms["T"]))
        Om_li = E * ctx.parse("@Omega_bulk")
        credit = sp.expand_log(sp.log(Om_li) - sp.log(ctx.parse("@Omega_bulk")), force=True)
        rep.add(zero(credit + ctx.syms["Delta_G_seq"] / (ctx.syms["R_gas"] * ctx.syms["T"])), "demonstration",
                "local-ideal credit", "ln Omega_local - ln Omega_bulk = -Delta_G_seq/(R T) in the dilute limit")


def check_thresholds(ctx, contract, rep):
    """The machine-readable block of theory/thresholds.md: ids, units and params keys."""
    path = THEORY / "thresholds.md"
    if not path.exists():
        rep.add(True, "thresholds", "theory/thresholds.md", "absent (not yet written)")
        return
    text = path.read_text(encoding="utf-8")
    m = re.search(r"```thresholds\n(.*?)```", text, re.S)
    if not m:
        rep.add(False, "thresholds", "machine block", "no fenced block tagged thresholds")
        return
    doc = yaml.safe_load(m.group(1))
    ok = doc.get("written_before_screen_output") is True and bool(doc.get("base_commit"))
    rep.add(ok, "thresholds", "header", "written before screen output, base commit %s" % doc.get("base_commit"))
    rep.add(doc.get("contract_version") == contract.get("version"), "thresholds", "contract version",
            "block %s, contract %s" % (doc.get("contract_version"), contract.get("version")))
    dec = doc["decision"]
    rep.add(dec.get("omega") == "Omega_bulk", "thresholds", "driving force", "verdicts use %s" % dec.get("omega"))
    fnames = {f["name"]: f for f in contract["functions"]}
    demo = {d["name"] for d in contract.get("demonstrations", [])}
    bad = [n for n in dec.get("forbidden_in_verdicts", []) if n not in fnames and n not in demo]
    rep.add(not bad, "thresholds", "forbidden in verdicts", "unknown names: %s" % bad if bad else
            "%d demonstration or reporting names" % len(dec.get("forbidden_in_verdicts", [])))
    keys = set()

    def qdim(name):
        if name in fnames:
            return parse_unit(fnames[name]["unit"])
        return ctx.dims[name]

    def check_edge(link, tid, quantity, edge, params):
        e = ctx.parse(str(edge))
        try:
            dq = qdim(quantity)
            de = dq if e == 0 else dimension(e, ctx.dims)  # a zero edge carries the unit of its quantity
        except DimError as exc:
            rep.add(False, "thresholds", "%s %s" % (link, tid), "%s %s: %s" % (quantity, edge, exc))
            return
        thr = [s.name for s in e.free_symbols if ctx.entries[s.name].get("kind") == "threshold"]
        missing = [n for n in thr if n not in (params or {})]
        ok = dq == de and not missing
        rep.add(ok, "thresholds", "%s %s" % (link, tid), "%s %s; unit %s%s" % (
            quantity, edge, fmt_dim(de), (" vs %s" % fmt_dim(dq)) if dq != de else "") +
            ("; no params key for %s" % missing if missing else ""))

    for link, spec in doc["links"].items():
        if spec.get("gating") is False:
            ok = not spec.get("tests") and spec.get("role") == "descriptor"
            rep.add(ok, "thresholds", "%s descriptor" % link,
                    "reported, no verdict test" if ok else "a non-gating link must be a descriptor without tests")
            fnd = spec.get("finding")
            if fnd:
                ctx.parse(fnd["quantity"])
        for test in (spec.get("tests") or []) + (spec.get("sensitivities") or []):
            params = test.get("params") or {}
            keys.update(v for v in params.values())
            for k in params:
                if k in ctx.entries or k in ("pH", "E_SHE", "schemes", "salts"):
                    continue
                rep.add(False, "thresholds", "%s %s" % (link, test["id"]), "params symbol %s is not registered" % k)
            if test.get("mixture"):
                keys.add(test["mixture"]["weights"])
            if "edge" in test:
                check_edge(link, test["id"], test["quantity"], test["edge"], params)
            for fr, edge in (test.get("edge_by_framing") or {}).items():
                check_edge(link, "%s[%s]" % (test["id"], fr), test["quantity"], edge, params)
            fal = test.get("falsify")
            if isinstance(fal, dict) and "edge" in fal:
                check_edge(link, test["id"] + " falsify", fal["quantity"], fal["edge"], params)
            miss = test.get("where_expt_missing")
            if isinstance(miss, dict):
                for k in ("edge_pass", "edge_falsify"):
                    if k in miss:
                        check_edge(link, "%s %s (no expt route)" % (test["id"], k), test["quantity"], miss[k], params)
            mbr = test.get("margin_by_route")
            if isinstance(mbr, dict):
                # cp3b A1: each deciding route names its margin symbol and the params path the test uses
                # for it; a route formula has the unit of its margin
                for route, rs in mbr.items():
                    if not isinstance(rs, dict) or "symbol" not in rs:
                        continue
                    sym = rs["symbol"]
                    ok = params.get(sym) == rs.get("params")
                    rep.add(ok, "thresholds", "%s %s margin %s" % (link, test["id"], route),
                            "%s from %s%s" % (sym, rs.get("params"), "" if ok else "; test params give %s" % params.get(sym)))
                    if rs.get("formula"):
                        try:
                            d = dimension(ctx.parse(str(rs["formula"])), ctx.dims)
                            rep.add(d == ctx.dims[sym], "thresholds", "%s %s margin formula" % (link, test["id"]),
                                    "%s = %s; unit %s" % (sym, rs["formula"], fmt_dim(d)))
                        except DimError as exc:
                            rep.add(False, "thresholds", "%s %s margin formula" % (link, test["id"]), str(exc))
                        keys.update((rs.get("formula_params") or {}).values())
            eq = test.get("equivalent_single_state")
            if eq:
                check_edge(link, test["id"] + " single state", eq["quantity"], eq["edge"], params)
                if test["quantity"] == "N_nuc":
                    s = ctx.syms
                    want = s["k_B"] * s["T"] * sp.log(s["J0_het"] * s["t_proc"] / ctx.parse(str(test["edge"])))
                    rep.add(numeric_zero(ctx.parse(str(eq["edge"])) - want), "thresholds", "%s %s" % (link, test["id"]),
                            "single-state edge = k_B T ln(J0_het t_proc / N_req) at the registered N_req")
            for q in test.get("report", []) + spec.get("report", []):
                ctx.parse(str(q))
            if test.get("cos_function") and test["cos_function"] not in fnames:
                rep.add(False, "thresholds", "%s %s" % (link, test["id"]), "unknown cos_function")
        p0 = spec.get("p0_inputs")
        if p0:
            # cp3b A4: the registered route and every side-by-side estimate compute the link's quantity,
            # and a Dupre support has the unit of that quantity
            q = (spec.get("tests") or [{}])[0].get("quantity")
            reg = p0["registered_route"]
            ok = reg["quantity"] in fnames and parse_unit(fnames[reg["quantity"]]["unit"]) == qdim(q)
            for name, est in p0["side_by_side"].items():
                ok = ok and est["quantity"] == q and (not est.get("function") or est["function"] in fnames)
                if est.get("params"):
                    keys.add(est["params"])
                sup = est.get("support")
                if isinstance(sup, dict):
                    try:
                        ok = ok and all(dimension(ctx.parse(str(sup[k])), ctx.dims) == qdim(q) for k in ("low", "high"))
                    except DimError:
                        ok = False
            rep.add(bool(ok) and p0.get("both_reported") is True, "thresholds", "%s P0 inputs" % link,
                    "registered route %s (%s); side by side %s" % (reg["quantity"], reg.get("verdict"), sorted(p0["side_by_side"])))
        ar = spec.get("analog_route")
        if ar:
            # D27 (A3): an analog solution constant reaches Delta_G_seq only through named contract functions
            fns = [ar[k]["function"] for k in ("Delta_G_site", "cycle") if k in ar] + [ar.get("x_bind")]
            bad = [n for n in fns if n not in fnames]
            prm = {}
            for k in ("Delta_G_site", "cycle"):
                prm.update(ar.get(k, {}).get("params") or {})
            bad += [k for k in prm if k not in ctx.entries]
            keys.update(prm.values())
            rep.add(not bad, "thresholds", "%s analog route" % link,
                    "functions %s; params %s%s" % (fns, sorted(prm), "" if not bad else "; unknown %s" % bad))
    adm = dec.get("admissibility")
    if adm:
        # D27: the admissibility condition is a contract quantity held against an edge of its own unit
        cond = adm["condition"]
        if cond["quantity"] in fnames:
            check_edge("decision", "admissibility", cond["quantity"], cond["edge"], adm.get("params"))
        else:
            rep.add(False, "thresholds", "decision admissibility", "unknown quantity %s" % cond["quantity"])
        bad = [k for k in (adm.get("params") or {}) if k not in ctx.entries]
        bad += [k for k in adm.get("joint_over", []) if k not in ctx.entries]
        keys.update((adm.get("params") or {}).values())
        need = ("draws_outside", "verdicts", "report", "retained_mass_rule", "unrestricted")
        miss = [k for k in need if k not in adm]
        rep.add(not bad and not miss, "thresholds", "admissibility rule",
                "joint over %s; draws outside %s%s" % (adm.get("joint_over"), adm.get("draws_outside"),
                                                       "" if not (bad or miss) else "; unknown %s, missing %s" % (bad, miss)))
    keys.add(dec["credible_level"]["params"])
    keys.update(((dec.get("drying_states") or {}).get("params") or {}).values())
    keys.update((doc["study"]["deletion_test"].get("params") or {}).values())
    conv = dec.get("conventions")
    if conv:
        pc, pd, mc = conv["p_cred"], conv["p_deg"], conv["m_cos"]
        q = lambda x: sp.nsimplify(str(x))
        ok = (sp.Rational(1, 2) < q(pc["primary"]) < 1 and all(sp.Rational(1, 2) < q(x) < 1 for x in pc["sweep"])
              and q(pc["primary"]) in [q(x) for x in pc["sweep"]]
              and q(pd["primary"]) == 1 - q(pc["primary"]) and pd["rule"] == "1 - p_cred"
              and 0 <= q(mc["primary"]) < 1 and all(0 <= q(x) < 1 for x in mc["sweep"])
              and all(conv[k].get("set_by") == "W1" for k in ("m_W", "m_S", "m_E")))
        rep.add(ok, "thresholds", "conventions", "p_cred %s (sweep %s), p_deg = 1 - p_cred = %s, m_cos %s (sweeps %s)" % (
            pc["primary"], pc["sweep"], pd["primary"], mc["primary"], mc["sweep"]))
        keys.update(conv[k]["params"] for k in ("p_cred", "p_deg", "m_cos", "m_W", "m_S", "m_E"))
    sz = doc["decision"].get("sizing")
    if sz:
        ok = all(k in sz for k in ("band_mass_half_width_max", "sobol_total_order_half_width_max", "draw_cap",
                                   "wall_clock_cap", "chunk", "on_cap"))
        rep.add(ok, "thresholds", "sizing rule", "band half-width <= %s, Sobol half-width <= %s, caps: %s; %s" % (
            sz.get("band_mass_half_width_max"), sz.get("sobol_total_order_half_width_max"), sz.get("draw_cap"),
            sz.get("wall_clock_cap")))
    study = doc["study"]
    gating = [k for k, s in doc["links"].items() if s.get("gating", True)]
    descr = [k for k, s in doc["links"].items() if not s.get("gating", True)]
    named = lambda rule: re.findall(r"C\d", rule)
    ok = (study.get("gating_links") == gating and study.get("descriptor_links", []) == descr
          and named(study["falsified"]) == gating and named(study["feasible"]) == gating
          and set(study["deletion_test"]["links"]) <= set(gating))
    rep.add(ok, "thresholds", "study rule", "gating %s, descriptors %s, deletion links %s" % (
        gating, descr, study["deletion_test"]["links"]))
    table = re.search(r"^## 4\. Params keys$(.*?)^## 5\.", text, re.S | re.M)
    table = table.group(1) if table else ""
    rows = {r.split("|")[1].strip().strip("`") for r in table.splitlines() if r.startswith("| `")}
    unlisted = sorted(k for k in keys if k not in rows)
    rep.add(not unlisted, "thresholds", "params keys", ("%d keys, all in the table of Section 4" % len(keys))
            if not unlisted else "%d keys; missing from the table of Section 4: %s" % (len(keys), unlisted))
    return sorted(keys)


def check_ignorance(ctx, rep):
    """The machine block of theory/ignorance_priors.md: bound units, branch masses, geometry."""
    path = THEORY / "ignorance_priors.md"
    if not path.exists():
        rep.add(True, "ignorance", "theory/ignorance_priors.md", "absent (not yet written)")
        return
    m = re.search(r"```ignorance\n(.*?)```", path.read_text(encoding="utf-8"), re.S)
    if not m:
        rep.add(False, "ignorance", "machine block", "no fenced block tagged ignorance")
        return
    doc = yaml.safe_load(m.group(1))
    rep.add(doc.get("written_before_screen_output") is True, "ignorance", "header", "written before screen output")

    def same_unit(name, exprs, what):
        want = ctx.dims[name]
        try:
            got = [dimension(ctx.parse(str(e)), ctx.dims) for e in exprs if str(e).strip() != "0"]
        except DimError as exc:
            rep.add(False, "ignorance", "%s %s" % (name, what), str(exc))
            return
        ok = all(g == want for g in got)
        rep.add(ok, "ignorance", "%s %s" % (name, what), "unit %s%s" % (fmt_dim(want), "" if ok else "; got %s" % [fmt_dim(g) for g in got]))

    for name, q in doc["quantities"].items():
        bounds = [q[k] for k in ("low", "high") if k in q]
        same_unit(name, bounds, "bounds")
    for name, q in doc["geometry"].items():
        exprs = [q[k] for k in ("low", "high", "equals") if k in q] + q.get("high_min_of", []) + q.get("low_max_of", [])
        exprs += q.get("high_min_of_expanded", [])
        same_unit(name, exprs, "geometric bounds")
        if q.get("N_req_range"):
            same_unit("N_req", [q["N_req_range"][k] for k in ("low", "high")], "range from %s" % name)
    ev = doc.get("evaluable_now")
    if ev:
        listed = {str(x).split(" (")[0] for x in ev.get("evaluable", []) + ev.get("gap", [])}
        statuses = {name: str(q.get("status", "")) for name, q in doc["geometry"].items()}
        bad = [n for n, s in statuses.items() if s and n in listed and
               (s.startswith("gap") != any(str(x).startswith(n) for x in ev.get("gap", [])))]
        rep.add(not bad, "ignorance", "evaluable now", "evaluable %s; gap %s%s" % (
            ev.get("evaluable"), ev.get("gap"), "" if not bad else "; status disagrees for %s" % bad))
    br = doc["branches"]
    G = ctx.parse(br["span"])
    a, b = ctx.parse(br["cuts"]["complete"]), ctx.parse(br["cuts"]["non"])
    u = sp.Symbol("u_sn", real=True)
    exact = {"complete": sp.integrate(1 / G, (u, 0, a)), "partial": sp.integrate(1 / G, (u, a, b)),
             "non": sp.integrate(1 / G, (u, b, G))}
    masses = {k: ctx.parse(v) for k, v in br["masses_interior"].items()}
    dims_ok = all(dimension(v, ctx.dims) == DIMLESS for v in masses.values())
    ok = dims_ok and all(zero(masses[k] - exact[k]) for k in exact) and zero(sum(masses.values()) - 1)
    rep.add(ok, "ignorance", "branch masses", "uniform gamma_sn on [0, %s]: complete + partial + non = 1, each the "
            "integral of the density over its Young branch" % br["span"])
    ok = zero(ctx.parse(br["cuts"]["non"]) - ctx.parse(br["cuts"]["complete"]) - 2 * ctx.syms["gamma_nl"])
    rep.add(ok, "ignorance", "partial-wetting width", "b - a = 2 gamma_nl > 0")
    fav = br.get("favourable")
    if fav:
        # D27 (A5): the C3 (a) good side of the gamma_sn axis is [0, gamma_sl - m_cos gamma_nl]
        cut = ctx.parse(fav["cut"])
        ok = (dimension(cut, ctx.dims) == ctx.dims["gamma_sn"]
              and zero(ctx.parse(fav["mass_interior"]) - sp.integrate(1 / G, (u, 0, cut))))
        rep.add(ok, "ignorance", "favourable mass", "gamma_sn uniform on [0, %s]: mass of gamma_sn <= %s" % (br["span"], fav["cut"]))
    adm = doc.get("admissibility")
    if adm:
        try:
            ok = dimension(ctx.parse(adm["condition"]["expr"]), ctx.dims) == parse_unit("J m^-2")
        except (DimError, KeyError) as exc:
            ok = False
        ok = ok and adm.get("draws_outside", "").startswith("refused") and "retained_mass" in adm
        rep.add(ok, "ignorance", "admissibility", "%s %s 0; draws outside %s" % (
            adm["condition"].get("expr"), adm["condition"].get("relation"), adm.get("draws_outside")))
    ss = doc["single_source_binding"]["widen_half_width_to_at_least"]
    ok = (dimension(ctx.parse(ss["free_energy"]), ctx.dims) == parse_unit("J mol^-1")
          and dimension(ctx.parse(ss["log10_constant"]), ctx.dims) == DIMLESS)
    rep.add(ok, "ignorance", "single-source widening", "free energy in J mol^-1, log10 constant dimensionless")
    rep.add(doc["reporting"]["probability_under_ignorance_is_finding"] is False, "ignorance", "reporting rule",
            "P(feasible) under an ignorance prior is never a finding")


def check_changes(contract, rep):
    names = {f["name"] for f in contract["functions"]}
    other = {"no_double_counting"} | {s["id"] for s in contract.get("sign_flips", [])}
    other |= {"conventions." + k for k in contract.get("conventions", {})}
    cur = [c for c in contract.get("changes", []) if c.get("version") == contract.get("version")]
    if not cur:
        rep.add(False, "changes", "version %s" % contract.get("version"), "no changelog entry for the current version")
        return
    c = cur[0]
    bad = [n for n in c.get("added", []) if n not in names]
    bad += [x["name"] for x in c.get("changed", []) if x["name"] not in names | other]
    bad += [x["name"] for x in c.get("removed", []) if x["name"] in names]
    bad += [x["replaced_by"] for x in c.get("removed", []) if x.get("replaced_by") and x["replaced_by"] not in names]
    rep.add(not bad, "changes", "version %s" % contract["version"],
            "added %d, changed %d, removed %d%s" % (len(c.get("added", [])), len(c.get("changed", [])),
                                                    len(c.get("removed", [])), ("; inconsistent: %s" % bad) if bad else ""))


LIT_ALLOW = {"P0-W3.1", "P0-W3.2", "P0-W3.3"}
# Method conventions set by the cp2 audit (credible level and its sweep, degradation mass with the
# swept values of 1 - p_cred, m_cos sweeps, sizing half-widths). They may appear only in these
# files, and only as these tokens; any other decimal there is still refused.
CONVENTION_FILES = {"thresholds.md", "cp2_fixes.md", "cp2_brief.md", "ignorance_priors.md", "check_contract.py"}
CONVENTION_TOKENS = {"0.9", "0.6", "0.99", "0.1", "0.2", "0.4", "0.01", "0.02"}
LIT_RX = [
    ("decimal", re.compile(r"(?<![\w.])\d+\.\d+(?![\w.])")),
    ("exponent", re.compile(r"(?<![\w.])\d+(\.\d+)?[eE][+-]?\d+\b")),
    ("3+ digits", re.compile(r"(?<![\w.#-])\d{3,}(?![\w.])")),
]


def check_literature_numbers(rep):
    hits = []
    for p in sorted(THEORY.rglob("*")):
        if not p.is_file() or "build" in p.parts or p.suffix not in (".tex", ".yaml", ".md", ".py"):
            continue
        for no, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            text = re.sub(r"P0-W\d+\.\d+|P0-I\d+|\b\d{4}-\d{2}-\d{2}\b", "", line)
            text = re.sub(r"\b(?:Phase|item|items|slide|flag|section)s?\s+[\d, ]+", "", text)
            for kind, rx in LIT_RX:
                for m in rx.finditer(text):
                    if p.name in CONVENTION_FILES and m.group(0) in CONVENTION_TOKENS:
                        continue
                    hits.append("%s:%d %s %r" % (p.relative_to(ROOT), no, kind, m.group(0)))
    rep.add(not hits, "no-lit-num", "theory/** sources", "; ".join(hits[:8]) if hits else "no decimal, exponent or 3+ digit literal")


def main():
    symbols_doc = yaml.safe_load((THEORY / "symbols.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((THEORY / "contract.yaml").read_text(encoding="utf-8"))
    rep = Report()
    check_symbols(symbols_doc, rep)
    ctx = Context(symbols_doc, contract)
    for f in contract["functions"]:
        check_function(ctx, f, rep)
    check_constants(ctx, contract, rep)
    check_sign_flips(ctx, contract, rep)
    check_no_double_counting(ctx, contract, rep)
    check_changes(contract, rep)
    check_thresholds(ctx, contract, rep)
    check_ignorance(ctx, rep)
    check_literature_numbers(rep)
    print("\n".join(rep.lines))
    print()
    for kind, (p, f) in rep.counts.items():
        print("%-13s %3d pass %3d fail" % (kind, p, f))
    print("functions: %d   result: %s" % (len(contract["functions"]), "PASS" if rep.failures == 0 else "FAIL (%d)" % rep.failures))
    return 0 if rep.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
