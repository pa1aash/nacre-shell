"""Read the parameter table (lit/params.yaml, lane p0-w1) into the screen's joint priors.

The layout and the prior-construction rule are W1's (lit/corpus/params_README.md). This
adapter reads that layout into nacre.screen.priors.Prior objects keyed by the theory
symbol id (the argument names of the contract functions) and couples them by the stated
correlation groups (nacre.screen.sampling.JointPrior):

  * family normal, uniform, loguniform: sampled; ``transform: log10`` means the family
    describes log10 of the quantity and the physical value is 10**y;
  * family fixed: a constant (not sampled, no sensitivity index);
  * family categorical or none (gaps, computed or registered inputs): not sampled; they
    are returned as unsampled with the table's reason, and a link that needs one cannot be
    evaluated from the table alone;
  * correlation groups of kind ``rank`` enter as their Spearman matrix; ``assumed
    independent`` groups enter as the identity, and the group exists so that the screen
    can test its sensitivity to that assumption (Task 4e).

W1's own loader (nacre.lit.params: load_params, validate, prior, priors, prior_set) checks
the table against the rule; when it is importable, cross_check() compares its priors with
this adapter's on every sampled key. Nothing here invents, widens or narrows a prior.
"""
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import yaml

from nacre.screen.priors import MockPriorsRefused, Prior, PriorFileError
from nacre.screen.sampling import JointPrior

PRODUCTION_PARAMS = Path("lit") / "params.yaml"
REGIMES = ("R-slurry", "R-cell")
SAMPLED = {"normal": ("mean", "sd"), "uniform": ("low", "high"), "loguniform": ("low", "high")}
UNSAMPLED = ("categorical", "none")


@dataclass(frozen=True, eq=False)
class RegimePriors:
    """Everything the screen takes from the parameter table for one regime."""
    regime: str
    joint: JointPrior                      # sampled and fixed inputs, keyed by symbol
    unsampled: dict = field(default_factory=dict)   # symbol -> reason (family none/categorical)
    path: str = ""
    sha256: str = ""
    mock: bool = False


def _family_params(prior, where):
    fam = prior.get("family")
    if fam in SAMPLED:
        params = {}
        for key in SAMPLED[fam]:
            if key not in prior:
                raise PriorFileError("%s: %s prior needs %r" % (where, fam, key))
            params[key] = float(prior[key])
        if fam in ("uniform", "loguniform") and not params["low"] < params["high"]:
            raise PriorFileError("%s: needs low < high" % where)
        if fam == "loguniform" and params["low"] <= 0:
            raise PriorFileError("%s: loguniform needs low > 0" % where)
        if fam == "normal" and not params["sd"] > 0:
            raise PriorFileError("%s: normal needs sd > 0" % where)
        return fam, params
    if fam == "fixed":
        if "value" not in prior:
            raise PriorFileError("%s: fixed prior needs 'value'" % where)
        return fam, {"value": float(prior["value"])}
    if fam in UNSAMPLED:
        return fam, None
    raise PriorFileError("%s: unknown prior family %r" % (where, fam))


def _in_regime(entry, regime):
    regimes = entry.get("regimes") or []
    return regime in regimes or "shared" in regimes


def read_table(path, allow_mock=False):
    """Parse the parameter table; returns (doc, sha256). Refuses a mock table without the flag."""
    path = Path(path)
    raw = path.read_bytes()
    doc = yaml.safe_load(raw) or {}
    if not isinstance(doc, dict):
        raise PriorFileError("%s: top level must be a mapping" % path)
    mock = doc.get("mock")
    if not isinstance(mock, bool):
        raise PriorFileError("%s: 'mock' must be stated explicitly as true or false" % path)
    if mock and not allow_mock:
        raise MockPriorsRefused("%s is a mock parameter table; pass --mock (allow_mock=True) to use "
                                "it, and never for production results" % path)
    if not isinstance(doc.get("params"), dict) or not doc["params"]:
        raise PriorFileError("%s: 'params' must be a non-empty mapping" % path)
    return doc, "sha256:" + hashlib.sha256(raw).hexdigest()


def regime_priors(path, regime, allow_mock=False):
    """Joint prior of one regime's inputs from the parameter table at path."""
    if regime not in REGIMES:
        raise PriorFileError("unknown regime %r" % regime)
    doc, sha = read_table(path, allow_mock)
    priors, unsampled, group_of = [], {}, {}
    for key, entry in doc["params"].items():
        if not isinstance(entry, dict) or not _in_regime(entry, regime):
            continue
        where = "%s:params.%s" % (path, key)
        symbol = entry.get("symbol")
        if not isinstance(symbol, str) or not symbol:
            raise PriorFileError("%s: 'symbol' is required" % where)
        prior = entry.get("prior")
        if not isinstance(prior, dict):
            raise PriorFileError("%s: 'prior' must be a mapping" % where)
        fam, params = _family_params(prior, where)
        if params is None:
            unsampled[symbol] = "prior family %s: %s" % (fam, entry.get("range_reason") or entry.get("status", ""))
            continue
        if symbol in {p.symbol for p in priors}:
            raise PriorFileError("%s: symbol %s appears twice in regime %s" % (where, symbol, regime))
        transform = entry.get("transform", "none")
        if transform not in ("none", "log10"):
            raise PriorFileError("%s: transform must be none or log10" % where)
        unit = entry.get("unit")
        if not isinstance(unit, str):
            raise PriorFileError("%s: 'unit' is required" % where)
        priors.append(Prior(key, symbol, unit, fam, params, ",".join(entry.get("sources") or []), transform))
        if entry.get("correlation_group"):
            group_of[key] = entry["correlation_group"]
    if not priors:
        raise PriorFileError("%s: regime %s has no sampled or fixed inputs" % (path, regime))
    rs, pairs = _spearman(doc.get("correlation_groups") or {}, priors, group_of, path)
    return RegimePriors(regime, JointPrior(tuple(priors), rs, tuple(pairs)), unsampled,
                        str(path), sha, bool(doc["mock"]))


def _spearman(groups, priors, group_of, path):
    keys = [p.name for p in priors]
    index = {k: i for i, k in enumerate(keys)}
    rs = np.eye(len(keys))
    pairs = []
    for gid in sorted(set(group_of.values())):
        g = groups.get(gid)
        if not isinstance(g, dict):
            raise PriorFileError("%s: correlation group %s is not defined" % (path, gid))
        members = list(g.get("members") or [])
        named = sorted(k for k, v in group_of.items() if v == gid)
        if not set(named) <= set(members):
            raise PriorFileError("%s: group %s does not list %s" % (path, gid, sorted(set(named) - set(members))))
        kind = g.get("kind")
        if kind == "assumed independent":
            continue
        if kind != "rank":
            raise PriorFileError("%s: group %s kind must be 'rank' or 'assumed independent'" % (path, gid))
        m = np.asarray(g.get("matrix"), dtype=float)
        if m.shape != (len(members), len(members)):
            raise PriorFileError("%s: group %s matrix must be square in member order" % (path, gid))
        source = ",".join(g.get("sources") or [])
        for a, ka in enumerate(members):
            for b, kb in enumerate(members):
                if a < b and ka in index and kb in index and m[a, b] != 0.0:
                    rs[index[ka], index[kb]] = rs[index[kb], index[ka]] = m[a, b]
                    pairs.append({"a": priors[index[ka]].symbol, "b": priors[index[kb]].symbol,
                                  "spearman_rho": float(m[a, b]), "source": source or gid})
    return rs, pairs


def cross_check(regime_priors_obj, loader_module):
    """Compare this adapter's priors with W1's loader (nacre.lit.params) key by key.

    Returns a list of discrepancy strings (empty when they agree). Used by the test suite
    once W1's loader is on the branch.
    """
    issues = []
    rp = regime_priors_obj
    for p in rp.joint.priors:
        other = loader_module.prior(p.name)
        for attr in ("distribution", "transform"):
            if getattr(other, attr, None) != getattr(p, attr):
                issues.append("%s: %s %r != %r" % (p.name, attr, getattr(other, attr, None), getattr(p, attr)))
        op = getattr(other, "params", {})
        for k, v in p.params.items():
            if k not in op or not np.isclose(op[k], v, rtol=1e-12, atol=0):
                issues.append("%s: parameter %s %r != %r" % (p.name, k, op.get(k), v))
    return issues
