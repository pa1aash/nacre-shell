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
      fixed_from: <row_id>                           X3: a definitional value printed in that row
      categorical: [{label, sources: [...]}]         X3 categorical input
      comparators: [<row_id>, ...]                   named in notes, never admitted (E2)
      correlation_group: <group id>
    correlation_groups:
      <group>: {kind, reason, sources, matrix}       members are collected from the keys
"""
import argparse
import datetime as dt
import hashlib
import math
import statistics
from pathlib import Path

import numpy as np
import yaml

from nacre import _util
from nacre.lit import evidence as E
from nacre.lit import ledger as L
from nacre.lit import params as P

SPEC = Path("lit") / "corpus" / "params_spec.yaml"
RULE_FILE = Path("lit") / "corpus" / "params_README.md"
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}


class SpecError(ValueError):
    pass


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


def admitted_value(row, adm, key_unit):
    """One admitted row -> dict(point, lo, hi, u, kind, grade, original, row)."""
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


def build_entry(key, spec, rows, symbols):
    unit = str(spec["unit"])
    transform = spec.get("transform", "none")
    sym = symbols.get(spec["symbol"]) if transform == "none" else None
    iv = _interval(sym)
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
        if a == b:
            raise SpecError("%s: degenerate span from several identical points; P1 does not apply" % key)
        if a > 0 and b / a > 10 and transform == "none":
            prior, rule = {"family": "loguniform", "low": _sig(a), "high": _sig(b)}, "L1"
            method.append("L1: span exceeds a decade")
        else:
            prior, rule = {"family": "uniform", "low": _sig(a), "high": _sig(b)}, "U1"
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


def build(root, spec_path=None):
    root = Path(root)
    spec_path = Path(spec_path) if spec_path else root / SPEC
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8")) or {}
    _, rows = E.read_csv(root / P.TABLE)
    rows = {r["row_id"]: r for r in rows}
    symbols = P.load_symbols(root)
    params = {}
    for key, ks in (spec.get("params") or {}).items():
        params[key] = build_entry(key, ks, rows, symbols)
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
