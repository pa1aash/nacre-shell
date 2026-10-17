"""Validate preprint/retrodiction/cases.yaml against preprint/retrodiction/SCHEMA.md.

Checks that every outcome and input carries a DOI and a locator (or a lit/params.yaml key), that
each outcome's relation agrees with its observable and values, that no usable input is derived
from the outcome it is compared with, that assumptions say what they rest on, that every usable
input names the interface it acts on (cp2 interface mapping, decision D17) with no Omega_local
mapping (contract v3), and that there are at least MIN_USABLE usable cases. It also computes the pass threshold k of criterion.md from the
number of usable cases and checks that criterion.md states the same N and k.
"""
import math
import re
from pathlib import Path

import yaml

MIN_USABLE = 8
ALPHA = 0.05
SCHEMA_ID = "retro-cases/v1"

DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$")
USABLE_ID = re.compile(r"^RC\d{2}$")
EXCLUDED_ID = re.compile(r"^RX\d{2}$")
STUDY_ID = re.compile(r"^S-[A-Z0-9-]+$")
ROW_ID = re.compile(r"^T[A-E]-\d{3}$")

TERMINATIONS = {"carboxyl", "hydroxyl", "methyl", "amine", "catechol", "thiol", "phosphate", "mixed",
                "polysaccharide", "peptoid", "polypeptide", "metal", "mineral"}
TEMPLATED = {"none", "chitosan", "polysaccharide", "polypeptide", "peptoid", "pda"}
OBSERVABLES = {"cnt_slope_B", "nucleation_rate", "induction_time", "onset_supersaturation",
               "presence_absence", "deposit_mass"}
RELATIONS = {"test_higher_barrier", "test_lower_barrier"}
CHANNELS = {"theta", "omega"}
ROLES = {"test", "reference", "shared"}
DISTRIBUTIONS = {"normal": {"mean", "sd"}, "uniform": {"low", "high"}, "loguniform": {"low", "high"},
                 "uniform_log": {"low_sigma", "high_sigma"}}

CASE_KEYS = {"id", "study", "termination", "templated", "test", "reference", "mineral", "polymorph",
             "conditions", "outcome", "channel", "inputs", "assumptions", "evidence_rows",
             "link_reported_in_source", "negative", "status", "exclusion_reason"}
OUTCOME_KEYS = {"comparison", "observable", "test_value", "reference_value", "unit", "relation",
                "reading", "doi", "locator"}
INPUT_KEYS = {"symbol", "role", "interface", "interface_mapping", "value", "distribution", "unit", "doi", "locator",
              "params_key", "evidence_row", "evidence_rows", "maps_to", "assumption", "basis", "derived_from_outcome"}

# Interfaces an input may act on (SCHEMA.md section 4): the three Young energies, the net energy of a
# simulated nucleus, the bulk state of the pair, and the shared Young ratio of a nuisance contact.
INTERFACES = {"gamma_sn", "gamma_sl", "gamma_nl", "net", "bulk", "young"}
# A surface input's mapping and the interface it reaches.
MAPPING_INTERFACE = {"dupre": "gamma_sn", "gibbs_langmuir": "gamma_sl", "owrk": "gamma_sl", "net": "net"}
SYMBOL_MAPPING = {"dG_bind": "dupre", "E_int": "dupre", "W_adh": "dupre", "c_local": "gibbs_langmuir",
                  "Delta_G_seq": "gibbs_langmuir", "gamma_s_owrk": "owrk", "gamma_net_sim": "net"}
REFUSED_MAPS = ("Omega_local",)

# The required coverage (P0-W2.2 task A): five terminations plus templated mineralisation.
REQUIRED_TERMINATIONS = ("carboxyl", "hydroxyl", "methyl", "amine", "catechol")
TEMPLATED_COVERAGE = ("chitosan", "polysaccharide", "polypeptide")


def default_path(root=None):
    from nacre import _util
    return Path(root or _util.repo_root()) / "preprint" / "retrodiction" / "cases.yaml"


def load(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _check_source(where, obj, errors, allow_params=False):
    if allow_params and not _blank(obj.get("params_key")):
        return
    doi = obj.get("doi")
    if _blank(doi) or not DOI_RE.match(str(doi)):
        errors.append("%s: missing or malformed DOI %r" % (where, doi))
    if _blank(obj.get("locator")):
        errors.append("%s: missing locator" % where)


def implied_relation(observable, test_value, reference_value):
    """Barrier relation an observation implies, or None when it cannot be read from the values."""
    if observable == "presence_absence":
        pair = (test_value, reference_value)
        if pair == ("absent", "present"):
            return "test_higher_barrier"
        if pair == ("present", "absent"):
            return "test_lower_barrier"
        return None
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (test_value, reference_value)):
        return None
    if test_value == reference_value:
        return None
    if observable == "cnt_slope_B":
        return "test_higher_barrier" if abs(test_value) > abs(reference_value) else "test_lower_barrier"
    if observable in ("induction_time", "onset_supersaturation"):
        return "test_higher_barrier" if test_value > reference_value else "test_lower_barrier"
    if observable in ("nucleation_rate", "deposit_mass"):
        return "test_higher_barrier" if test_value < reference_value else "test_lower_barrier"
    return None


def _check_outcome(cid, out, usable, errors):
    where = "%s.outcome" % cid
    if not isinstance(out, dict):
        errors.append("%s: missing" % where)
        return
    for k in sorted(set(out) - OUTCOME_KEYS):
        errors.append("%s: unknown key %r" % (where, k))
    if out.get("comparison") != "pairwise":
        errors.append("%s: comparison must be 'pairwise', got %r" % (where, out.get("comparison")))
    obs = out.get("observable")
    if obs not in OBSERVABLES:
        errors.append("%s: unknown observable %r" % (where, obs))
    if out.get("relation") not in RELATIONS:
        errors.append("%s: relation must be one of %s" % (where, sorted(RELATIONS)))
    _check_source(where, out, errors)
    if not usable:
        return
    if _blank(out.get("reading")):
        errors.append("%s: a usable outcome needs a reading" % where)
    implied = implied_relation(obs, out.get("test_value"), out.get("reference_value"))
    if implied is None:
        errors.append("%s: values %r / %r do not give a direction for observable %r"
                      % (where, out.get("test_value"), out.get("reference_value"), obs))
    elif implied != out.get("relation"):
        errors.append("%s: relation %r contradicts the values (they imply %r)" % (where, out.get("relation"), implied))


def _check_input(where, inp, errors):
    for k in sorted(set(inp) - INPUT_KEYS):
        errors.append("%s: unknown key %r" % (where, k))
    if _blank(inp.get("symbol")):
        errors.append("%s: missing symbol" % where)
    if inp.get("role") not in ROLES:
        errors.append("%s: role must be one of %s" % (where, sorted(ROLES)))
    has_value, dist = "value" in inp, inp.get("distribution")
    if has_value == (dist is not None):
        errors.append("%s: give exactly one of value or distribution" % where)
    if dist is not None:
        kind = dist.get("type") if isinstance(dist, dict) else None
        if kind not in DISTRIBUTIONS:
            errors.append("%s: unknown distribution %r" % (where, kind))
        else:
            missing = DISTRIBUTIONS[kind] - set(dist)
            if missing:
                errors.append("%s: distribution %s lacks %s" % (where, kind, sorted(missing)))
            if kind == "normal" and not dist.get("sd", 0) > 0:
                errors.append("%s: normal sd must be positive" % where)
            for lo, hi in (("low", "high"), ("low_sigma", "high_sigma")):
                if lo in dist and hi in dist and not dist[lo] < dist[hi]:
                    errors.append("%s: %s must be below %s" % (where, lo, hi))
    _check_source(where, inp, errors, allow_params=True)
    if inp.get("assumption") is True and _blank(inp.get("basis")):
        errors.append("%s: an assumed input needs a basis" % where)
    if inp.get("assumption") not in (True, False):
        errors.append("%s: assumption must be true or false" % where)
    if inp.get("derived_from_outcome") is not False:
        errors.append("%s: derived_from_outcome must be false for a usable case (SCHEMA.md rule 6)" % where)
    row = inp.get("evidence_row")
    if row is not None and not ROW_ID.match(str(row)):
        errors.append("%s: malformed evidence_row %r" % (where, row))
    _check_interface(where, inp, errors)


def _check_interface(where, inp, errors):
    """The input names its interface; a surface input also names the mapping that reaches it."""
    iface, mapping, sym = inp.get("interface"), inp.get("interface_mapping"), inp.get("symbol")
    if iface not in INTERFACES:
        errors.append("%s: interface must be one of %s, got %r" % (where, sorted(INTERFACES), iface))
    if any(r in str(inp.get("maps_to", "")) for r in REFUSED_MAPS):
        errors.append("%s: maps through Omega_local, which contract v3 refuses" % where)
    if sym in SYMBOL_MAPPING:
        if inp.get("role") not in ("test", "reference"):
            errors.append("%s: %s is a surface input; its role must be test or reference" % (where, sym))
        if mapping != SYMBOL_MAPPING[sym]:
            errors.append("%s: %s maps by %r, got interface_mapping %r" % (where, sym, SYMBOL_MAPPING[sym], mapping))
        elif iface != MAPPING_INTERFACE[mapping]:
            errors.append("%s: mapping %s reaches %s, got interface %r" % (where, mapping, MAPPING_INTERFACE[mapping], iface))
    elif mapping is not None:
        errors.append("%s: interface_mapping is only for surface inputs (%s)" % (where, ", ".join(sorted(SYMBOL_MAPPING))))


def validate(data, evidence_rows=None):
    """Return (errors, summary). evidence_rows: optional set of row_ids in lit/evidence_table.csv."""
    errors = []
    if not isinstance(data, dict):
        return ["cases file is not a mapping"], {}
    if data.get("schema") != SCHEMA_ID:
        errors.append("schema must be %r" % SCHEMA_ID)
    if data.get("fixed_before_run") is not True:
        errors.append("fixed_before_run must be true")
    for name, prior in sorted((data.get("shared_priors") or {}).items()):
        _check_source("shared_priors.%s" % name, prior, errors, allow_params=True)
        if prior.get("interface") not in INTERFACES:
            errors.append("shared_priors.%s: interface must be one of %s" % (name, sorted(INTERFACES)))
        if not _blank(prior.get("params_key")) and not prior.get("evidence_rows"):
            errors.append("shared_priors.%s: a pending params key must list its evidence rows" % name)

    studies = {}
    for s in data.get("studies") or []:
        sid = s.get("id")
        if not STUDY_ID.match(str(sid)):
            errors.append("study id %r malformed" % sid)
        if sid in studies:
            errors.append("duplicate study %s" % sid)
        studies[sid] = s
        _check_source("study %s" % sid, dict(s, locator="study record"), errors)
        if _blank(s.get("reference")):
            errors.append("study %s: no reference surface stated" % sid)
        if s.get("read") is None:
            errors.append("study %s: say what was read" % sid)

    seen, usable, excluded = set(), [], []
    for c in data.get("cases") or []:
        cid = c.get("id")
        if cid in seen:
            errors.append("duplicate case id %s" % cid)
        seen.add(cid)
        for k in sorted(set(c) - CASE_KEYS):
            errors.append("%s: unknown key %r" % (cid, k))
        status = c.get("status")
        if status not in ("usable", "excluded"):
            errors.append("%s: status must be usable or excluded" % cid)
            continue
        is_usable = status == "usable"
        if is_usable and not USABLE_ID.match(str(cid)):
            errors.append("%s: usable case ids are RC<nn>" % cid)
        if not is_usable and not EXCLUDED_ID.match(str(cid)):
            errors.append("%s: excluded case ids are RX<nn>" % cid)
        if c.get("termination") not in TERMINATIONS:
            errors.append("%s: unknown termination %r" % (cid, c.get("termination")))
        if c.get("templated") not in TEMPLATED:
            errors.append("%s: unknown templated value %r" % (cid, c.get("templated")))
        if c.get("channel") not in CHANNELS:
            errors.append("%s: channel must be theta or omega" % cid)
        for side in ("test", "reference"):
            if _blank((c.get(side) or {}).get("label")):
                errors.append("%s: %s surface needs a label" % (cid, side))
        for flag in ("negative", "link_reported_in_source"):
            if c.get(flag) not in (True, False):
                errors.append("%s: %s must be true or false" % (cid, flag))
        for row in c.get("evidence_rows") or []:
            if not ROW_ID.match(str(row)):
                errors.append("%s: malformed evidence row %r" % (cid, row))
            elif evidence_rows is not None and row not in evidence_rows:
                errors.append("%s: evidence row %s not in lit/evidence_table.csv" % (cid, row))
        _check_outcome(cid, c.get("outcome"), is_usable, errors)
        if is_usable:
            usable.append(c)
            if c.get("study") not in studies:
                errors.append("%s: study %r is not described under studies" % (cid, c.get("study")))
            inputs = c.get("inputs") or []
            roles = {i.get("role") for i in inputs}
            if not {"test", "reference"} <= roles:
                errors.append("%s: needs at least one test and one reference input" % cid)
            for n, inp in enumerate(inputs):
                _check_input("%s.inputs[%d]" % (cid, n), inp, errors)
            maps = {i.get("role"): set() for i in inputs}
            for i in inputs:
                if i.get("symbol") in SYMBOL_MAPPING:
                    maps[i.get("role")].add(i.get("interface_mapping"))
            if maps.get("test") != maps.get("reference") or len(maps.get("test") or ()) != 1:
                errors.append("%s: test and reference need one and the same interface mapping, got %s and %s"
                              % (cid, sorted(maps.get("test") or ()), sorted(maps.get("reference") or ())))
            if c.get("channel") != "theta":
                errors.append("%s: under contract v3 every template input acts through theta (Omega is the bulk value)"
                              % cid)
            ids = set()
            for a in c.get("assumptions") or []:
                if _blank(a.get("text")) or not re.match(r"^A-%s-\d+$" % re.escape(str(cid)), str(a.get("id"))):
                    errors.append("%s: assumption %r needs an id A-%s-<n> and a text" % (cid, a.get("id"), cid))
                if a.get("id") in ids:
                    errors.append("%s: duplicate assumption %s" % (cid, a.get("id")))
                ids.add(a.get("id"))
            if any(i.get("assumption") for i in inputs) and not ids:
                errors.append("%s: assumed inputs but no assumptions listed" % cid)
            if not _blank(c.get("exclusion_reason")):
                errors.append("%s: a usable case has no exclusion reason" % cid)
        else:
            excluded.append(c)
            if _blank(c.get("exclusion_reason")):
                errors.append("%s: an excluded case needs its reason" % cid)

    if len(usable) < MIN_USABLE:
        errors.append("only %d usable cases; at least %d are required" % (len(usable), MIN_USABLE))
    summary = summarise(usable, excluded)
    return errors, summary


def summarise(usable, excluded):
    n = len(usable)
    k = threshold_k(n) if n else None
    terms = sorted({c["termination"] for c in usable})
    templated = sorted({c["templated"] for c in usable} - {"none"})
    return {
        "usable": n,
        "excluded": len(excluded),
        "terminations": terms,
        "templated": templated,
        "missing_terminations": [t for t in REQUIRED_TERMINATIONS if t not in terms],
        "templated_covered": any(t in templated for t in TEMPLATED_COVERAGE),
        "negatives": sum(1 for c in usable if c.get("negative")),
        "k": k,
        "chance_probability": tail_probability(n, k) if n else None,
    }


def tail_probability(n, k, p=0.5):
    """Exact P(X >= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k, n + 1))


def threshold_k(n, alpha=ALPHA):
    """Smallest k with P(X >= k | n, 1/2) <= alpha, or None if no k in 0..n reaches it."""
    for k in range(n + 1):
        if tail_probability(n, k) <= alpha:
            return k
    return None


def check_criterion(text, summary):
    """criterion.md must state the N and k that follow from the cases file."""
    errors = []
    n_m = re.search(r"^N = (\d+)\b", text, re.M)
    k_m = re.search(r"^k = (\d+)\b", text, re.M)
    if not n_m or not k_m:
        return ["criterion.md: lines 'N = <n>' and 'k = <k>' not found"]
    if int(n_m.group(1)) != summary.get("usable"):
        errors.append("criterion.md: N = %s but cases.yaml has %s usable cases" % (n_m.group(1), summary.get("usable")))
    if int(k_m.group(1)) != summary.get("k"):
        errors.append("criterion.md: k = %s but the exact binomial rule gives k = %s" % (k_m.group(1), summary.get("k")))
    return errors


def evidence_row_ids(root):
    import csv
    path = Path(root) / "lit" / "evidence_table.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as fh:
        return {r["row_id"] for r in csv.DictReader(fh)}


def check(root=None):
    """Validate the repository's cases.yaml and criterion.md. Returns (errors, summary)."""
    from nacre import _util
    root = Path(root or _util.repo_root())
    path = default_path(root)
    errors, summary = validate(load(path), evidence_row_ids(root))
    crit = path.with_name("criterion.md")
    if crit.exists():
        errors += check_criterion(crit.read_text(encoding="utf-8"), summary)
    else:
        errors.append("criterion.md missing")
    return errors, summary
