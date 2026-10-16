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
  8. Sign-flip tests and the syntactic no-double-counting condition.
  9. No literature number in theory/** sources (decimals, exponent notation or integers of
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
              lambda x: sp.simplify(sp.trigsimp(sp.expand_trig(x))), lambda x: sp.nsimplify(sp.simplify(x))):
        try:
            if f(expr) == 0:
                return True
        except Exception:
            pass
    return False


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
            ok = zero(e - ctx.parse(idt["equals"]))
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


def check_sign_flips(ctx, contract, rep):
    for sf in contract.get("sign_flips", []):
        sid, par = sf["id"], ctx.syms[sf["parameter"]]
        if "df_dcos" in sf:
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
        else:
            B = ctx.parse(sf["barrier"])
            om = ctx.syms["Omega"]
            Bd = B.subs(om, ctx.parse(sf["omega_subs"]))
            der = sp.diff(Bd, par)
            expect = ctx.parse(sf["derivative_equals"]).subs(sp.Symbol("aux_B", positive=True), Bd)
            ok = zero(der - expect)
            rep.add(ok, "sign-flip", sid, "dB/d%s identity" % sf["parameter"])
            w = sf["witness"]
            vals = ctx.subs_map(w["values"])
            Bw = Bd.subs(vals)
            rest = {s: 1 for s in Bw.free_symbols if s != par}
            Bw = Bw.subs(rest)
            b = [sp.N(Bw.subs(par, ctx.parse(str(x))), 30) for x in (w["delta_plus"], 0, w["delta_minus"])]
            ok = b[0] > b[1] > b[2]
            rep.add(ok, "sign-flip", sid, "witness barrier(+,0,-) = %s" % ["%.6g" % float(x) for x in b])


def check_no_double_counting(ctx, contract, rep):
    ndc = contract["no_double_counting"]
    theta_syms, omega_syms = set(), set()
    for k, v in ndc["channel_theta"].items():
        theta_syms |= {s.name for s in ctx.parse(v).free_symbols}
    for k, v in ndc["channel_omega"].items():
        names = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", str(v))) - set(FUNCS)
        omega_syms |= names
    omega_syms -= set(ndc["channel_omega"].keys())
    td = set(ndc["template_dependent"])
    both = td & theta_syms & omega_syms
    missing = td - theta_syms - omega_syms
    unknown = (theta_syms | omega_syms) - td - set(ndc["template_independent"])
    ok = not both and not missing and not unknown
    rep.add(ok, "no-double", "template inputs partitioned",
            "theta: %s | Omega: %s%s" % (sorted(td & theta_syms), sorted(td & omega_syms),
                                         ("; in both: %s; unused: %s; unclassified: %s" % (sorted(both), sorted(missing), sorted(unknown))) if not ok else ""))
    # composite parses, is a barrier in J, and the cross derivatives vanish
    text = ndc["composite_expression"]
    for k, v in ndc["channel_theta"].items():
        text = re.sub(r"\b%s\b" % k, "(" + v + ")", text)
    for k in ("Om_local", "E_enr", "c_max"):
        text = re.sub(r"\b%s\b" % k, "(" + ndc["channel_omega"][k] + ")", text)
    comp = ctx.parse(text)
    rep.add(dimension(comp, ctx.dims) == parse_unit("J"), "no-double", "composite barrier", "dimension J")
    c_y = ctx.parse(ndc["channel_theta"]["c_young"])
    om_text = ndc["channel_omega"]["Om_local"]
    for k in ("E_enr", "c_max"):
        om_text = re.sub(r"\b%s\b" % k, "(" + ndc["channel_omega"][k] + ")", om_text)
    om = ctx.parse(om_text)
    cross = [sp.diff(c_y, ctx.syms[s]) for s in td & omega_syms] + [sp.diff(om, ctx.syms[s]) for s in td & theta_syms]
    rep.add(all(c == 0 for c in cross), "no-double", "cross derivatives",
            "d theta/d(Omega-channel inputs) = 0 and d Omega/d(theta-channel inputs) = 0")


LIT_ALLOW = {"P0-W3.1", "P0-W3.2", "P0-W3.3"}
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
            text = re.sub(r"P0-W\d+\.\d+|P0-I\d+", "", line)
            text = re.sub(r"\b(?:Phase|item|items|slide|flag|section)s?\s+[\d, ]+", "", text)
            for kind, rx in LIT_RX:
                for m in rx.finditer(text):
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
    check_literature_numbers(rep)
    print("\n".join(rep.lines))
    print()
    for kind, (p, f) in rep.counts.items():
        print("%-13s %3d pass %3d fail" % (kind, p, f))
    print("functions: %d   result: %s" % (len(contract["functions"]), "PASS" if rep.failures == 0 else "FAIL (%d)" % rep.failures))
    return 0 if rep.failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
