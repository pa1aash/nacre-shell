"""Build lit/params.yaml from the evidence table and a key specification, by the rule of
lit/corpus/params_README.md.

The specification (lit/corpus/params_spec.yaml) says, per key, which evidence rows are admitted, how a
row's printed number maps to the key (unit conversion through pint, log10, negation) and which rows
share an original determination. It holds no numbers of its own: every value, bound and prior
parameter in the output is computed here from the rows, so the parameter table cannot carry a typed
value.

    uv run python -m nacre.lit.build_params [--ledger SESSION]

Specification per key:

    <key>:
      symbol, unit, regimes, conditions, notes      as in the output (README section 1)
      transform: none | log10                        default none
      distinct: true                                 each admitted row is its own determination unless it
                                                     names an `original` (several facets, surfaces or
                                                     ligands in one paper or one compilation)
      status: computed | registered | design-input | gap | definitional   (only for X1-X3 keys)
      reason: <text>                                 range_reason for keys without admitted rows
      admit:                                         admitted rows (E1-E5)
        - row: TC-033
          op: none | log10 | neglog10 | negate | exp  applied to the row's number before unit conversion
          unit: <unit>                               override the row's unit (for example "kJ mol^-1")
          uncertainty: sd | se | pm | range | none   how to read range_or_uncertainty (default: pm for ±,
                                                     range for lo..hi)
          original: <id>                             rows with one original id count once (E3; default: doi)
          offset_row: <row_id>                       add that row's value (a reference-electrode potential
                                                     vs SHE) to convert the scale; the row becomes a source
          take: uncertainty | last_digit             read the printed ± (or one unit of the printed value's last
                                                     decimal place) as the number (rule version 2, D1 inputs)
      fixed_from: <row_id>                           X3: a definitional value printed in that row
      categorical: [{label, sources: [...]}]         X3 categorical input
      comparators: [<row_id>, ...]                   named in notes, never admitted (E2)
      correlation_group: <group id>
    correlation_groups:
      <group>: {kind, reason, sources, matrix}       members are collected from the keys

Rule version 2 (README section 7, cp3), per key:

      role: primary | sensitivity | analog | design-axis   default primary; `of: <key>` for sensitivity/analog
      flags: [...]                                   extra flags (single_source, truncated, widened and analog
                                                     are also set automatically)
      same_rows_as: <key>                            reuse that key's admit list (an uncut or analog twin)
      truncate: {min|max: <bound>, ruling, sensitivity_key}                     T1
      widen: {by: <key>, scale: free_energy | log10_constant}                   W1 (after the first pass)
      derive: {expr, inputs: {name: key | key.min | key.max}, as: fixed | none}  D1
      ignorance: {low, high, inputs: {name: key}, authority}                    I1
      registered: {file, block, path, ruling}                                   R1
      axis: {classes: [{label, key}]}                                           G1
      margin_zero: {reason}                                                     M0 (margin zero, README 7.3)
      margin_case: evidence | zero                   copied to the entry

Post-cp3 supplements (README section 8, P0-W1.4), per key:

      added_in: <session>                            the session that added the key after tag p0-cp3
      fills: <gap key>                               the cp3 gap key this key supplies a prior for; the gap
                                                     key itself is left as it was at the tag
"""
import argparse
import ast
import datetime as dt
import hashlib
import itertools
import math
import re
import statistics
from pathlib import Path

import numpy as np
import yaml
from scipy import constants as SC

from nacre import _util
from nacre.lit import evidence as E
from nacre.lit import ledger as L
from nacre.lit import params as P

SPEC = Path("lit") / "corpus" / "params_spec.yaml"
RULE_FILE = Path("lit") / "corpus" / "params_README.md"
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


STANDARD_T = 298.15  # K, the IUPAC standard temperature (a definition, README 7.2 W1)
PASS_THROUGH = ("role", "of", "margin_case", "ionic_strength", "fills", "added_in")
DEFERRED = ("derive", "ignorance", "registered", "axis", "margin_zero")
# exact SI constants only (README section 1)
EXPR_CONSTANTS = {"N_A": SC.N_A, "k_B": SC.k, "e": SC.e, "F": SC.N_A * SC.e, "R": SC.N_A * SC.k,
                  "T0": STANDARD_T, "pi": math.pi}
EXPR_FUNCS = {"abs": abs, "max": max, "min": min, "log": math.log, "log10": math.log10, "exp": math.exp,
              "sqrt": math.sqrt}


class SpecError(ValueError):
    pass


def eval_expr(expr, names):
    """Evaluate an arithmetic formula over named numbers (no attribute access, no other calls)."""
    tree = ast.parse(str(expr), mode="eval")
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Call, ast.Name, ast.Load, ast.Constant, ast.Add,
               ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise SpecError("formula %r: %s not allowed" % (expr, type(node).__name__))
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name) and node.func.id in EXPR_FUNCS):
            raise SpecError("formula %r: only %s may be called" % (expr, sorted(EXPR_FUNCS)))
        if isinstance(node, ast.Name) and node.id not in names and node.id not in EXPR_CONSTANTS \
                and node.id not in EXPR_FUNCS:
            raise SpecError("formula %r: unknown name %r" % (expr, node.id))
    return float(eval(compile(tree, "<formula>", "eval"), {"__builtins__": {}},
                      {**EXPR_FUNCS, **EXPR_CONSTANTS, **names}))


def _input_value(ref, params, which="value"):
    """'key' -> value (or a corner bound), 'key.min' / 'key.max' -> that range bound."""
    key, _, bound = ref.partition(".")
    e = params.get(key)
    if e is None:
        raise KeyError(key)
    if bound:
        return None if e.get("range") is None else float(e["range"][bound])
    if which == "value":
        return None if e.get("value") is None else float(e["value"])
    rng = e.get("range")
    return None if rng is None else float(rng[which])


def envelope(expr, inputs, params):
    """Value at the input values and the envelope over every corner of the input ranges (README 7.2 D1).
    Returns (value, lo, hi); None where an input lacks a value or a range."""
    vals = {n: _input_value(r, params) for n, r in inputs.items()}
    value = None if any(v is None for v in vals.values()) else eval_expr(expr, vals)
    corners = []
    for n, r in inputs.items():
        if "." in r:
            corners.append([_input_value(r, params)])
        else:
            lo, hi = _input_value(r, params, "min"), _input_value(r, params, "max")
            if lo is None or hi is None:
                return value, None, None
            corners.append(sorted({lo, hi}))
    outs = [eval_expr(expr, dict(zip(inputs, c))) for c in itertools.product(*corners)]
    return value, min(outs), max(outs)


def _sig(x, n=12):
    """Round away binary noise from unit conversion (12 significant digits)."""
    if x == 0 or not math.isfinite(x):
        return float(x)
    return float(f"{x:.{n - 1}e}")


def _parse_number(text):
    t = text.strip()
    cmp = ""
    for c in ("<=", ">=", "≤", "≥", "<", ">"):
        if t.startswith(c):
            cmp, t = c, t[len(c):].strip()
            break
    return float(t), cmp


def _convert(x, from_unit, to_unit):
    if from_unit in ("1", "dimensionless") and to_unit in ("1", "dimensionless"):
        return x
    u = E.ureg()
    q = u.Quantity(x, from_unit.replace("Ohm", "ohm"))
    to = "dimensionless" if to_unit in ("1", "dimensionless") else to_unit.replace("Ohm", "ohm")
    return float(q.to(to).magnitude)


def _apply_op(x, op):
    if op in (None, "none"):
        return x
    if op == "log10":
        return math.log10(x)
    if op == "neglog10":
        return -math.log10(x)
    if op == "negate":
        return -x
    if op == "exp":
        return math.exp(x)
    raise SpecError("unknown op %r" % op)


def _take(row, adm, key_unit):
    """README 7.2 D1 inputs read from a row's printed text: `take: uncertainty` is the printed ± as a point;
    `take: last_digit` is one unit of the printed value's last decimal place, as a point."""
    unit = adm.get("unit") or row["unit"]
    take = adm["take"]
    if take == "uncertainty":
        rng = (row.get("range_or_uncertainty") or "").strip()
        if not rng.startswith("±") or rng.endswith("%"):
            raise SpecError("%s: take uncertainty needs a printed ±x" % row["row_id"])
        x = float(rng[1:])
    elif take == "last_digit":
        v = (row.get("value") or "").strip().lstrip("<>=≤≥+-")
        if "e" in v.lower() or not v:
            raise SpecError("%s: take last_digit needs a plain decimal value" % row["row_id"])
        decimals = len(v.split(".")[1]) if "." in v else 0
        x = 10.0 ** -decimals
    else:
        raise SpecError("%s: unknown take %r" % (row["row_id"], take))
    y = abs(_convert(x, unit, key_unit) - _convert(0.0, unit, key_unit)) if unit not in ("1", "dimensionless") else x
    return {"row": row["row_id"], "grade": row["grade"], "original": adm.get("original") or row["doi"].lower(),
            "u": None, "cmp": "", "point": y, "lo": y, "hi": y}


def admitted_value(row, adm, key_unit):
    """One admitted row -> dict(point, lo, hi, u, kind, grade, original, row)."""
    if adm.get("take"):
        return _take(row, adm, key_unit)
    unit = adm.get("unit") or row["unit"]
    op = adm.get("op", "none")
    rng = (row.get("range_or_uncertainty") or "").strip()
    how = adm.get("uncertainty")
    value = (row.get("value") or "").strip()

    def conv(x):
        y = _apply_op(x, op)
        return y if op in ("log10", "neglog10") else _convert(y, unit, key_unit)  # exp: unit is that of A

    out = {"row": row["row_id"], "grade": row["grade"], "original": adm.get("original") or row["doi"].lower(),
           "u": None, "cmp": ""}
    if value:
        x, cmp = _parse_number(value)
        out["cmp"] = cmp
        out["point"] = conv(x)
    else:
        out["point"] = None
    if rng and (how in (None, "range") and ".." in rng):
        lo, hi = E.number_range(rng)
        a, b = sorted((conv(lo), conv(hi)))
        out["lo"], out["hi"] = a, b
        if out["point"] is None:
            out["mid"] = (a + b) / 2
    elif rng and how != "none" and out["point"] is not None:
        if op not in (None, "none", "negate"):
            raise SpecError("%s: an uncertainty with op %s needs explicit interval handling" % (row["row_id"], op))
        x0, _ = _parse_number(value)
        def cu(x):
            return abs(_convert(x, unit, key_unit) - _convert(0.0, unit, key_unit)) \
                if unit not in ("1", "dimensionless") else abs(x)

        if rng.startswith("±"):
            body = rng[1:].strip()
            up = dn = cu(abs(x0) * float(body[:-1]) / 100 if body.endswith("%") else float(body))
        elif rng.startswith("+"):
            a, b = rng[1:].split("/-")
            up, dn = cu(float(a)), cu(float(b))
        else:
            raise SpecError("%s: cannot read uncertainty %r" % (row["row_id"], rng))
        out["u"] = max(up, dn)
        sign = -1 if op == "negate" else 1
        if sign < 0:
            up, dn = dn, up
        out["lo"], out["hi"] = out["point"] - 2 * dn, out["point"] + 2 * up
    if out["point"] is not None and "lo" not in out:
        out["lo"] = out["hi"] = out["point"]
    if out["point"] is None and "lo" not in out:
        raise SpecError("%s: no number" % row["row_id"])
    return out


def _interval(sym):
    return P._interval(sym.get("interval")) if sym else (-math.inf, math.inf, True, True)


def _clip(a, b, iv):
    lo, hi = iv[0], iv[1]
    return max(a, lo), min(b, hi)


def _build_entry_core(key, spec, rows, symbols):
    unit = str(spec["unit"])
    transform = spec.get("transform", "none")
    sym = symbols.get(spec["symbol"]) if transform == "none" else None
    iv = P._interval(spec["interval"]) if spec.get("interval") else _interval(sym)
    adm_specs = spec.get("admit") or []
    vals = []
    for adm in adm_specs:
        r = rows.get(adm["row"])
        if r is None:
            raise SpecError("%s: row %s not in the evidence table" % (key, adm["row"]))
        if spec.get("distinct") and not adm.get("original"):
            adm = {**adm, "original": "%s#%s" % (r["doi"].lower(), r["row_id"])}
        v = admitted_value(r, adm, unit)
        if adm.get("offset_row"):
            # potential against a reference electrode + that reference's potential printed in another row
            o = rows.get(adm["offset_row"])
            if o is None:
                raise SpecError("%s: offset row %s not in the evidence table" % (key, adm["offset_row"]))
            off = admitted_value(o, {"row": o["row_id"], "uncertainty": "none"}, unit)["point"]
            for f in ("point", "lo", "hi", "mid"):
                if v.get(f) is not None:
                    v[f] += off
            v["offset_rows"] = [o["row_id"]]
        vals.append(v)
    # E5: grade D only when no A-C row is admitted
    if any(v["grade"] in "ABC" for v in vals) and any(v["grade"] == "D" for v in vals):
        raise SpecError("%s: grade-D rows are admitted only when no grade A-C row exists (E5)" % key)
    base = {"symbol": spec["symbol"], "transform": transform, "unit": unit, "regimes": spec["regimes"]}
    sources = [v["row"] for v in vals] + sorted({o for v in vals for o in v.get("offset_rows", [])})
    best = min((rows[x]["grade"] for x in sources), key=GRADE_ORDER.get) if sources else None
    notes = str(spec.get("notes") or "").strip()
    comps = spec.get("comparators") or []
    if comps:
        notes = (notes + " " if notes else "") + "Comparators (not admitted, E2): %s." % ", ".join(comps)
    common = {"sources": sources, "best_grade": best, "conditions": str(spec.get("conditions") or "n.s."),
              "correlation_group": spec.get("correlation_group"), "notes": notes}

    if "categorical" in spec:
        srcs = sorted({s for o in spec["categorical"] for s in o.get("sources", [])})
        for s in srcs:
            if s not in rows:
                raise SpecError("%s: option source %s not in the evidence table" % (key, s))
        cbest = min((rows[s]["grade"] for s in srcs), key=GRADE_ORDER.get) if srcs else None
        return {**base, "status": spec.get("status", "sourced"), "value": None, "range": None,
                "range_reason": "categorical input; options listed in the prior",
                "prior": {"family": "categorical", "options": spec["categorical"]}, "rule": "X3",
                **common, "sources": srcs, "best_grade": cbest,
                "method": "options and their source rows; not sampled (X3)"}
    if "fixed_from" in spec:
        r = rows[spec["fixed_from"]]
        v = admitted_value(r, {"row": r["row_id"], "uncertainty": "none", **(spec.get("fixed_op") or {})}, unit)
        x = _sig(v["point"])
        return {**base, "status": spec.get("status", "definitional"), "value": x, "range": {"min": x, "max": x},
                "prior": {"family": "fixed", "value": x}, "rule": "X3", **common,
                "sources": [r["row_id"]], "best_grade": r["grade"],
                "method": "definitional value printed in %s (X3)" % r["row_id"]}
    if not vals:
        status = spec.get("status", "gap")
        rule = "X2" if status in ("computed", "registered") else "X1"
        reason = str(spec.get("reason") or "").strip()
        if not reason:
            raise SpecError("%s: a key without admitted rows needs a reason" % key)
        return {**base, "status": status, "value": None, "range": None, "range_reason": reason,
                "prior": {"family": "none"}, "rule": rule, **common,
                "method": "no admitted row (%s)" % rule}

    # one value per original determination (E3): the best-graded row stands for it
    by_orig = {}
    for v in vals:
        cur = by_orig.get(v["original"])
        if cur is None or GRADE_ORDER[v["grade"]] < GRADE_ORDER[cur["grade"]]:
            by_orig[v["original"]] = v
    indep = list(by_orig.values())
    shadowed = [v["row"] for v in vals if v not in indep]
    if shadowed:
        # E3: only the row standing for each original is a source; the others are named in notes
        vals = indep
        common["sources"] = [v["row"] for v in indep] + sorted({o for v in indep for o in v.get("offset_rows", [])})
        common["best_grade"] = min((rows[x]["grade"] for x in common["sources"]), key=GRADE_ORDER.get)
        common["notes"] = (common["notes"] + " " if common["notes"] else "") + \
            "Same original as an admitted row, not counted again (E3): %s." % ", ".join(shadowed)
    ends = [x for v in vals for x in (v["lo"], v["hi"])]
    span = (min(ends), max(ends))
    points = [v["point"] for v in vals if v["point"] is not None]
    n_orig = len(indep)
    method = []
    # independent sources: named originals count separately; row-level determinations of one paper count once
    n_src = len({v["original"].split("#")[0] for v in indep})
    status = "sourced" if n_src >= 2 else "single-source"
    if spec.get("status") in ("sourced", "single-source"):
        status = spec["status"]  # e.g. several determinations from one paper: single-source

    def normal_ok(group):
        return all(v["grade"] in "AB" and v["u"] and v["point"] is not None and not v["cmp"] for v in group)

    prior = rule = None
    if n_orig >= 2 and normal_ok(indep):
        conc = all(abs(a["point"] - b["point"]) <= 2 * math.hypot(a["u"], b["u"])
                   for i, a in enumerate(indep) for b in indep[i + 1:])
        if conc:
            w = [1 / v["u"] ** 2 for v in indep]
            m = sum(wi * v["point"] for wi, v in zip(w, indep)) / sum(w)
            uw = sum(w) ** -0.5
            sx = statistics.stdev([v["point"] for v in indep])
            prior, rule = {"family": "normal", "mean": _sig(m), "sd": _sig(max(uw, sx))}, "N1"
            method.append("N1: %d concordant independent grade A/B values; inverse-variance mean, sd = max(u_w, s_x)"
                          % n_orig)
        else:
            method.append("not concordant within 2 combined standard uncertainties, so U1")
    elif n_orig == 1 and indep[0]["grade"] == "A" and indep[0]["u"] and not indep[0]["cmp"]:
        v = indep[0]
        prior, rule = {"family": "normal", "mean": _sig(v["point"]), "sd": _sig(v["u"])}, "N2"
        method.append("N2: one grade-A value with a stated uncertainty")
    if prior and prior["family"] == "normal" and transform == "none":
        m, s = prior["mean"], prior["sd"]
        if not (P._inside(m - 4 * s, iv) and P._inside(m + 4 * s, iv)):
            a, b = _clip(m - 2 * s, m + 2 * s, iv)
            method.append("N3: the normal prior left the admissible interval within 4 sd; uniform on mean +- 2 sd")
            prior, rule = {"family": "uniform", "low": _sig(a), "high": _sig(b)}, "N3"
            span = (min(span[0], a), max(span[1], b))
    if prior is None:
        if n_orig == 1 and len({(v["lo"], v["hi"]) for v in vals}) == 1 and vals[0]["lo"] == vals[0]["hi"]:
            x = _sig(vals[0]["point"])
            out = {**base, "status": "single-source", "value": x, "range": {"min": x, "max": x},
                   "prior": {"family": "fixed", "value": x}, "rule": "P1", **common,
                   "method": "P1: one point value without uncertainty; the width is not sourced"}
            return out
        a, b = _clip(span[0], span[1], iv)
        trunc = spec.get("truncate")
        if trunc:
            a0, b0 = a, b
            a, b = max(a, float(trunc.get("min", -math.inf))), min(b, float(trunc.get("max", math.inf)))
            if not a < b:
                raise SpecError("%s: the truncation leaves no span" % key)
            points = [x for x in points if a <= x <= b]
            method.append("T1: sourced span %s to %s cut at %s by %s" % (_sig(a0), _sig(b0), _sig(a if a != a0 else b),
                                                                         trunc["ruling"]))
        if a == b and all(v["lo"] == v["hi"] == a for v in vals):
            x = _sig(a)
            return {**base, "status": status, "value": x, "range": {"min": x, "max": x},
                    "prior": {"family": "fixed", "value": x}, "rule": "P1", **common,
                    "method": "P1: %d independent sources print the same point without uncertainty; the width is "
                              "not sourced" % n_orig}
        if a == b:
            raise SpecError("%s: degenerate span; P1 does not apply" % key)
        if a > 0 and b / a > 10 and transform == "none":
            prior, rule = {"family": "loguniform", "low": _sig(a), "high": _sig(b)}, "T1" if trunc else "L1"
            method.append("L1: span exceeds a decade")
        else:
            prior, rule = {"family": "uniform", "low": _sig(a), "high": _sig(b)}, "T1" if trunc else "U1"
            method.append("U1: uniform over the sourced span")
        span = (a, b)
    if prior["family"] in ("uniform", "loguniform"):
        rng = {"min": prior["low"], "max": prior["high"]}
        if points:
            value = statistics.median(points)
        else:
            mids = [v["mid"] for v in vals if "mid" in v]
            value = (statistics.median([math.log(x) for x in mids]) if prior["family"] == "loguniform" else
                     statistics.median(mids))
            value = math.exp(value) if prior["family"] == "loguniform" else value
        value = min(max(_sig(value), rng["min"]), rng["max"])
    else:
        rng = {"min": _sig(min(span[0], prior["mean"])), "max": _sig(max(span[1], prior["mean"]))}
        value = prior["mean"]
    method.append("%d admitted row(s), %d independent original(s)" % (len(vals), n_orig))
    return {**base, "status": status, "value": value, "range": rng, "prior": prior, "rule": rule, **common,
            "method": "; ".join(method)}


def build_entry(key, spec, rows, symbols):
    e = _build_entry_core(key, spec, rows, symbols)
    if spec.get("truncate"):
        if e["rule"] != "T1":
            raise SpecError("%s: truncate applies only to a uniform or log-uniform span (T1)" % key)
        t = spec["truncate"]
        side = "min" if "min" in t else "max"
        e["truncation"] = {"side": side, "bound": float(t[side]), "ruling": t["ruling"],
                           "sensitivity_key": t["sensitivity_key"]}
    return decorate(e, spec)


def decorate(e, spec):
    """Role, `of`, flags and the pass-through fields of rule version 2 (README 7.1)."""
    for f in PASS_THROUGH:
        if f in spec:
            e[f] = spec[f]
    e.setdefault("role", "primary")
    flags = list(spec.get("flags") or [])
    auto = {"single_source": e.get("status") == "single-source", "truncated": e.get("rule") == "T1",
            "analog": e.get("role") == "analog", "widened": bool(e.get("widening", {}).get("applied")),
            "registered": e.get("rule") == "R1"}
    flags += [f for f, on in auto.items() if on and f not in flags]
    e["flags"] = flags
    return e


def _no_prior(spec, status, reason, rule="X1", extra=None):
    base = {"symbol": spec["symbol"], "transform": spec.get("transform", "none"), "unit": str(spec["unit"]),
            "regimes": spec["regimes"], "status": status, "value": None, "range": None, "range_reason": reason,
            "prior": {"family": "none"}, "rule": rule, "sources": [], "best_grade": None,
            "method": "no admitted row (%s)" % rule, "conditions": str(spec.get("conditions") or "n.s."),
            "correlation_group": spec.get("correlation_group"), "notes": str(spec.get("notes") or "").strip()}
    return {**base, **(extra or {})}


def _sources_of(keys, params, rows):
    srcs = []
    for k in keys:
        for s in params[k]["sources"]:
            if s not in srcs:
                srcs.append(s)
    best = min((rows[x]["grade"] for x in srcs), key=GRADE_ORDER.get) if srcs else None
    return srcs, best


def apply_widening(key, spec, e, params):
    """W1: widen a single-source Ca2+ binding or transfer free energy (or log10 constant) to a half-width of
    at least m (README 7.2)."""
    w = spec["widen"]
    if e["status"] != "single-source":
        raise SpecError("%s: widening applies to single-source keys only (W1)" % key)
    m_key = w["by"]
    m = params[m_key]["value"]
    if w["scale"] == "log10_constant":
        m = m / (EXPR_CONSTANTS["R"] * STANDARD_T * math.log(10))
    elif w["scale"] != "free_energy":
        raise SpecError("%s: widen.scale must be free_energy or log10_constant" % key)
    rng = e["range"]
    lo, hi = float(rng["min"]), float(rng["max"])
    mid, half = (lo + hi) / 2, (hi - lo) / 2
    applied = half < m
    half = max(half, m)
    a, b = _sig(mid - half), _sig(mid + half)
    e["prior"] = {"family": "uniform", "low": a, "high": b}
    e["range"] = {"min": a, "max": b}
    e["rule"] = "W1"
    e["widening"] = {"by": m_key, "m": _sig(m), "scale": w["scale"], "unwidened": {"min": lo, "max": hi},
                     "applied": applied, "sources": list(params[m_key]["sources"])}
    e["method"] += "; W1: %s to a half-width of at least m = %s (%s%s)" % (
        "widened about the midpoint" if applied else "sourced half-width already exceeds m, not widened",
        _sig(m), m_key, ", divided by R T ln 10 at 298.15 K" if w["scale"] == "log10_constant" else "")
    return e


def build_deferred(key, spec, params, rows, root):
    """D1, I1, R1, G1 and M0 entries, which depend on other keys or on an authority file."""
    unit = str(spec["unit"])
    if "registered" in spec:
        r = spec["registered"]
        node = registered_node(root, r)
        if node is None:
            raise SpecError("%s: %s has no path %s" % (key, r["file"], r["path"]))
        x = float(node["primary"])
        reg = {"file": r["file"], "block": r.get("block", "thresholds"), "path": r["path"], "ruling": r["ruling"]}
        if "sweep" in node:
            reg["sweep"] = [float(v) for v in node["sweep"]]
        if "rule" in node:
            reg["rule"] = str(node["rule"])
            dep = r.get("sweep_from")
            if dep:
                src = registered_node(root, {**r, "path": dep["path"]})
                reg["sweep"] = [_sig(eval_expr(node["rule"], {dep["name"]: float(v)})) for v in src["sweep"]]
        e = {"symbol": spec["symbol"], "transform": "none", "unit": unit, "regimes": spec["regimes"],
             "status": "registered", "value": x, "range": {"min": x, "max": x}, "prior": {"family": "fixed", "value": x},
             "rule": "R1", "sources": [], "best_grade": None,
             "method": "R1: registered value read from %s (%s), path %s" % (r["file"], reg["block"], r["path"]),
             "conditions": str(spec.get("conditions") or "registration convention"),
             "correlation_group": spec.get("correlation_group"), "notes": str(spec.get("notes") or "").strip(),
             "registered": reg}
        return decorate(e, spec)
    if "margin_zero" in spec:
        e = {"symbol": spec["symbol"], "transform": "none", "unit": unit, "regimes": spec["regimes"],
             "status": "registered", "value": 0.0, "range": {"min": 0.0, "max": 0.0},
             "prior": {"family": "fixed", "value": 0.0}, "rule": "M0", "sources": [], "best_grade": None,
             "method": "M0: margin zero because the prior carries the method error (README 7.3)",
             "conditions": str(spec.get("conditions") or "threshold margin"),
             "correlation_group": spec.get("correlation_group"),
             "notes": str(spec.get("notes") or "").strip(), "margin_case": "zero",
             "margin_reason": str(spec["margin_zero"]["reason"]).strip()}
        return decorate(e, spec)
    if "axis" in spec:
        opts = []
        for c in spec["axis"]["classes"]:
            k = c["key"]
            if k not in params:
                raise SpecError("%s: axis class key %s not built" % (key, k))
            ce = params[k]
            opts.append({"label": c["label"], "key": k, "value": ce["value"], "range": ce["range"],
                         "sources": list(ce["sources"])})
        srcs, best = _sources_of([c["key"] for c in spec["axis"]["classes"]], params, rows)
        e = {"symbol": spec["symbol"], "transform": "none", "unit": unit, "regimes": spec["regimes"],
             "status": "design-input", "value": None, "range": None,
             "range_reason": "design axis keyed to class (G1); each option names its per-class key",
             "prior": {"family": "categorical", "options": opts}, "rule": "G1", "sources": srcs, "best_grade": best,
             "method": "G1: one option per class, each built from that class's rows; not sampled as one prior",
             "conditions": str(spec.get("conditions") or "n.s."), "correlation_group": spec.get("correlation_group"),
             "notes": str(spec.get("notes") or "").strip()}
        return decorate(e, spec)
    if "ignorance" in spec:
        ig = spec["ignorance"]
        inputs = ig["inputs"]
        _, lo_a, lo_b = envelope(ig["low"], inputs, params)
        _, hi_a, hi_b = envelope(ig["high"], inputs, params)
        keys = [r.partition(".")[0] for r in inputs.values()]
        ign = {"low": str(ig["low"]), "high": str(ig["high"]), "inputs": dict(inputs), "authority": ig["authority"]}
        if None in (lo_a, hi_b):
            return decorate(_no_prior(spec, "gap", "ignorance prior (I1) whose bound inputs lack a range: %s"
                                      % ", ".join(keys), "X1", {"ignorance": ign}), spec)
        e = {"symbol": spec["symbol"], "transform": "none", "unit": unit, "regimes": spec["regimes"],
             "status": "gap", "value": None, "range": {"min": _sig(lo_a), "max": _sig(hi_b)},
             "prior": {"family": "none"}, "rule": "I1", "sources": [], "best_grade": None,
             "method": "I1: uniform between %s and %s, drawn per draw of the inputs; the range is the envelope over "
                       "the input ranges (information only)" % (ig["low"], ig["high"]),
             "conditions": str(spec.get("conditions") or "n.s."), "correlation_group": spec.get("correlation_group"),
             "notes": str(spec.get("notes") or "").strip(), "ignorance": ign}
        return decorate(e, spec)
    if "derive" in spec:
        d = spec["derive"]
        inputs = d["inputs"]
        keys = list(dict.fromkeys(r.partition(".")[0] for r in inputs.values()))
        der = {"expr": str(d["expr"]), "inputs": dict(inputs)}
        missing = [k for k in keys if params[k]["value"] is None and params[k]["range"] is None]
        if missing:
            return decorate(_no_prior(spec, spec.get("status", "gap"),
                                      "derived (D1) from %s; no value for %s" % (", ".join(keys), ", ".join(missing)),
                                      "X1", {"derived": der}), spec)
        value, lo, hi = envelope(d["expr"], inputs, params)
        srcs, best = _sources_of(keys, params, rows)
        fam = d.get("as", "fixed")
        status = spec.get("status", "computed")
        e = {"symbol": spec["symbol"], "transform": spec.get("transform", "none"), "unit": unit,
             "regimes": spec["regimes"], "status": status, "value": None if value is None else _sig(value),
             "range": None if lo is None else {"min": _sig(lo), "max": _sig(hi)},
             "prior": {"family": "fixed", "value": _sig(value)} if fam == "fixed" else {"family": "none"},
             "rule": "D1", "sources": srcs, "best_grade": best,
             "method": "D1: %s with %s; range is the envelope over the input ranges" % (
                 d["expr"], ", ".join("%s = %s" % kv for kv in inputs.items())),
             "conditions": str(spec.get("conditions") or "n.s."), "correlation_group": spec.get("correlation_group"),
             "notes": str(spec.get("notes") or "").strip(), "derived": der}
        if e["range"] is None:
            e["range_reason"] = "an input has no range"
        if fam == "fixed" and value is None:
            raise SpecError("%s: a fixed derived key needs every input value" % key)
        return decorate(e, spec)
    raise SpecError("%s: nothing to defer" % key)


def registered_node(root, r):
    """The node at a dotted path of the machine-readable block of an authority file."""
    text = (Path(root) / r["file"]).read_text(encoding="utf-8")
    m = re.search(r"```%s\n(.*?)```" % re.escape(r.get("block", "thresholds")), text, re.S)
    if not m:
        raise SpecError("%s has no ```%s block" % (r["file"], r.get("block", "thresholds")))
    node = yaml.safe_load(m.group(1))
    for part in r["path"].split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def build(root, spec_path=None):
    root = Path(root)
    spec_path = Path(spec_path) if spec_path else root / SPEC
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    _, rows = E.read_csv(root / P.TABLE)
    rows = {r["row_id"]: r for r in rows}
    symbols = P.load_symbols(root)
    params = {}
    specs = spec.get("params") or {}
    for key, ks in specs.items():
        if "same_rows_as" in ks:
            twin = specs[ks["same_rows_as"]]
            ks = {**ks, "admit": twin.get("admit") or [], "distinct": twin.get("distinct", False)}
            specs[key] = ks
    for key, ks in specs.items():
        if any(f in ks for f in DEFERRED):
            params[key] = None  # keeps the specification order
            continue
        params[key] = build_entry(key, ks, rows, symbols)
    for key, ks in specs.items():
        if "widen" in ks:
            params[key] = decorate(apply_widening(key, ks, params[key], params), ks)
    pending = [k for k, v in params.items() if v is None]
    while pending:
        progress = []
        for key in pending:
            ks = specs[key]
            deps = [r.partition(".")[0] for r in ((ks.get("derive") or ks.get("ignorance") or {}).get("inputs") or {}).values()]
            deps += [c["key"] for c in (ks.get("axis") or {}).get("classes", [])]
            if any(params.get(d) is None for d in deps):
                continue
            params[key] = build_deferred(key, ks, params, rows, root)
            progress.append(key)
        if not progress:
            raise SpecError("unresolved derived keys (missing or circular inputs): %s" % pending)
        pending = [k for k in pending if k not in progress]
    groups = {}
    for gid, g in (spec.get("correlation_groups") or {}).items():
        members = [k for k, e in params.items() if e.get("correlation_group") == gid]
        kind = g.get("kind", "assumed independent")
        matrix = g.get("matrix") if kind == "rank" else np.eye(len(members)).tolist()
        groups[gid] = {"members": members, "kind": kind, "matrix": matrix, "sources": g.get("sources") or [],
                       "reason": str(g.get("reason") or "").strip()}
    views = {}
    for path, key in (spec.get("aliases") or {}).items():
        if key not in params:
            raise SpecError("alias %s names unknown key %s" % (path, key))
        parts = path.split(".")
        if parts[0] not in P.VIEW_ROOTS:
            raise SpecError("alias %s must start with %s" % (path, " or ".join(P.VIEW_ROOTS)))
        cur = views
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = {"key": key, **params[key]}
    table_sha = hashlib.sha256((root / P.TABLE).read_bytes()).hexdigest()
    rule_sha = hashlib.sha256((root / RULE_FILE).read_bytes()).hexdigest()
    meta = {"generated_by": "uv run python -m nacre.lit.build_params", "spec": str(SPEC),
            "rule": str(RULE_FILE), "rule_sha256": rule_sha, "evidence_table_sha256": table_sha,
            "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            **(spec.get("meta") or {})}
    return {"mock": False, "meta": meta, "params": params, "correlation_groups": groups, **views}


HEADER = """# Parameter table of the P0 screen (lane p0-w1). GENERATED by `uv run python -m nacre.lit.build_params`
# from lit/evidence_table.csv and lit/corpus/params_spec.yaml under the rule in
# lit/corpus/params_README.md; do not edit by hand. After tag p0-cp3 any change needs a dated entry in
# ops/tracks/p0_deviations.md. Read it with nacre.lit.params (prior, priors, prior_set).
"""


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.lit.build_params")
    ap.add_argument("--spec")
    ap.add_argument("--out")
    ap.add_argument("--ledger", metavar="SESSION")
    a = ap.parse_args(argv)
    root = _util.repo_root()
    doc = build(root, a.spec)
    out = Path(a.out) if a.out else root / P.PARAMS
    out.write_text(HEADER + yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
    p = P.load_params(out, root, strict=False)
    fams = {}
    for e in p.entries.values():
        fams[e["prior"]["family"]] = fams.get(e["prior"]["family"], 0) + 1
    print("wrote %s: %d keys, families %s, %d groups" % (out, len(p.entries), fams, len(p.groups)))
    for e in p.errors:
        print("  " + e)
    print("validate: %s" % ("PASS" if not p.errors else "%d problem(s)" % len(p.errors)))
    if a.ledger and not p.errors and not a.out:
        L.record(root, "lit-params", a.ledger, "uv run python -m nacre.lit.build_params --ledger %s" % a.ledger,
                 [P.TABLE, SPEC, RULE_FILE], [P.PARAMS])
        print("ledger: record appended to %s" % L.LEDGER)
    return 1 if p.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
