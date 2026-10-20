"""The gap-resolution table of the production screen (configs/preprint/gap_resolution.yaml).

For every input the screen needs that has no sourced prior in lit/params.yaml, the table registers
one treatment: ignorance (bounds from theory/ignorance_priors.md), analog (a flagged W1 analog key),
design_axis (a registered grid) or unresolved (the test reports a gap and counts as inconclusive).
It is committed before any production output (rule R7), and every production document records the
commit that last changed it.
"""
from pathlib import Path

import yaml

GAP_TABLE = Path("configs") / "preprint" / "gap_resolution.yaml"
TREATMENTS = ("ignorance", "analog", "design_axis", "unresolved")
#: Table sections that account for unsourced keys without a treatment (they are not screen gaps).
ACCOUNTED = ("not_screen_inputs", "computed_or_registered")


class GapTableError(ValueError):
    """The gap-resolution table is incomplete or names a treatment the rule does not allow."""


def load(path=GAP_TABLE):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def unsourced_keys(params_doc):
    """Primary keys of the parameter table with no sampled or fixed prior (gaps, computed, registered)."""
    out = []
    for key, e in (params_doc.get("params") or {}).items():
        if not isinstance(e, dict) or e.get("role", "primary") != "primary":
            continue
        fam = (e.get("prior") or {}).get("family")
        if e.get("status") == "gap" or fam in (None, "none", "categorical"):
            out.append(key)
    return out


def check(table, params_doc):
    """Problems of the table against the parameter table (empty when it is complete and valid)."""
    problems = []
    entries = table.get("gaps") or {}
    covered = set(entries)
    for sec in ACCOUNTED:
        covered |= set(table.get(sec) or {})
    for key in unsourced_keys(params_doc):
        if key not in covered:
            problems.append("%s: no registered treatment" % key)
    params = params_doc.get("params") or {}
    for key, e in entries.items():
        t = e.get("treatment")
        if t not in TREATMENTS:
            problems.append("%s: treatment %r is not one of %s" % (key, t, TREATMENTS))
        if t == "analog":
            a = e.get("analog")
            if a not in params:
                problems.append("%s: analog key %r is not in the table" % (key, a))
            elif params[a].get("role") != "analog" and "analog" not in (params[a].get("flags") or []) \
                    and not str(a).startswith("log10_k_"):
                problems.append("%s: %r is not a flagged analog or a literature binding key" % (key, a))
        if t == "ignorance" and "prior" in e and "bound_from" in e and "ignorance_priors.md" not in str(e["bound_from"]):
            problems.append("%s: ignorance bounds must come from theory/ignorance_priors.md" % key)
    return problems


def analog_keys(table):
    """{gap key: analog key} of the analog treatments (the C1 side-by-side analog included)."""
    out = {k: e["analog"] for k, e in (table.get("gaps") or {}).items() if e.get("treatment") == "analog"}
    c1 = ((table.get("c1") or {}).get("side_by_side") or {}).get("C1_analog")
    if c1:
        out["W_adh_wet"] = c1["analog"]
    return out


# ------------------------------------------------------------------ phosphate skeleton (PH-W4.1)
PH_TABLE = Path("configs") / "preprint" / "gap_resolution_ph.yaml"
PENDING = "to register at cp5 freeze"


def load_ph(path=PH_TABLE):
    return load(path)


def _walk(node, trail=()):
    if isinstance(node, dict):
        if "treatment" in node:
            yield trail, node["treatment"]
        for k, v in node.items():
            yield from _walk(v, trail + (str(k),))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, trail + (str(i),))


def treatments_ph(table):
    """[(path, treatment)] of every entry of the phosphate skeleton that has a treatment slot."""
    return [(".".join(t), v) for t, v in _walk(table)]


def awaiting(table):
    """Keys of the phosphate skeleton whose treatment is not yet registered (to register at the cp5 freeze)."""
    return sorted(p for p, v in treatments_ph(table) if v == PENDING)


def check_ph(table):
    """Problems of the phosphate skeleton: a treatment that is neither allowed nor the pending label."""
    return ["%s: treatment %r is not one of %s or %r" % (p, v, TREATMENTS, PENDING)
            for p, v in treatments_ph(table) if v not in TREATMENTS and v != PENDING]
