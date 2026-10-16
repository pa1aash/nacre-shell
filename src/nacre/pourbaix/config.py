"""Run configurations for the Pourbaix and window code.

Every physical input in a run configuration is a mapping with a `source`:

- `charter`: the bound is read from charter/regimes.yaml (`charter_key` names the input and
  `bound` the side, min or max). The charter value must be non-null.
- `lit/params.yaml`: the value is read from W1's parameter file under `key` (published by
  P0-W1.2, Day 2). A missing file or key is an error, never a silent default.
- `mock`: a placeholder for pipeline checks. Allowed only when the caller passes
  allow_mock=True (the `--mock` flag); the configuration must then also say `mock: true`.
- `choice`: a method choice made and justified in the configuration (no number involved).

The pH axis of an R-slurry run is never read from the charter: the charter's pH range may be
null (7 is neutral, not an alkaline bound). The run configuration must carry an explicit grid
`pH: {min, max}` whose bounds are `lit/params.yaml` (with its key) or `mock` (the grid then
also says `mock: true`). A `charter` source for the pH axis is refused.

Numerical settings (grid sizes, tolerances) live under `numerics` and carry no source.
"""
import hashlib
import json
from pathlib import Path

import yaml

from nacre.pourbaix.paths import CHARTER_REGIMES, LIT_PARAMS, REPO

SOURCES = {"charter", "lit/params.yaml", "mock", "choice"}


class MockRefused(RuntimeError):
    """A mock value was found while mock values are not allowed."""


class ConfigError(ValueError):
    pass


def canonical_hash(obj):
    """sha256 of the canonical JSON (sorted keys, no whitespace), the W4 config_hash rule."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _is_input(node):
    return isinstance(node, dict) and "source" in node


def _walk(node, path=()):
    if _is_input(node):
        yield path, node
        return
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk(v, path + (str(i),))


def _charter_value(regime, node, charter):
    key, bound = node.get("charter_key"), node.get("bound")
    try:
        rng = charter["regimes"][regime]["inputs"][key]["range"]
    except KeyError as exc:
        raise ConfigError("charter has no input %s in regime %s" % (key, regime)) from exc
    value = None if rng is None else rng.get(bound)
    if value is None:
        raise ConfigError("charter %s.%s.%s is null; it cannot be the source" % (regime, key, bound))
    return value


def _lit_value(node, lit_params):
    if lit_params is None:
        raise ConfigError("lit/params.yaml is not available (published by P0-W1.2); "
                          "value %s cannot be resolved" % node.get("key"))
    cur = lit_params
    for part in str(node["key"]).split("."):
        if not isinstance(cur, dict) or part not in cur:
            raise ConfigError("lit/params.yaml has no key %s" % node["key"])
        cur = cur[part]
    return cur["value"] if isinstance(cur, dict) and "value" in cur else cur


def _set(tree, path, value):
    cur = tree
    for k in path[:-1]:
        cur = cur[int(k)] if isinstance(cur, list) else cur[k]
    last = path[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    else:
        cur[last] = value


def _check_ph_axis(raw):
    """The R-slurry pH axis must be an explicit run-config grid, never a charter range."""
    ph = raw.get("regimes", {}).get("R-slurry", {}).get("pH")
    if not isinstance(ph, dict) or not all(_is_input(ph.get(b)) for b in ("min", "max")):
        raise ConfigError("R-slurry needs an explicit pH grid in the run configuration: "
                          "pH: {min: {...}, max: {...}} with sourced bounds")
    srcs = {ph[b]["source"] for b in ("min", "max")}
    if "charter" in srcs:
        raise ConfigError("the pH axis cannot come from the charter; give a grid sourced from "
                          "lit/params.yaml (or mock under --mock)")
    if not srcs <= {"mock", "lit/params.yaml"}:
        raise ConfigError("pH grid bounds must be sourced from lit/params.yaml or mock, not %s"
                          % sorted(srcs))
    for b in ("min", "max"):
        if ph[b]["source"] == "lit/params.yaml" and not ph[b].get("key"):
            raise ConfigError("pH.%s: a lit/params.yaml bound must cite its key" % b)
    if "mock" in srcs and ph.get("mock") is not True:
        raise ConfigError("a mock pH grid must be marked mock: true")


def load(path, allow_mock=False, charter_path=CHARTER_REGIMES, lit_params_path=LIT_PARAMS):
    """Load and resolve a run configuration.

    Returns (resolved, meta). `resolved` has every input node replaced by its value; `meta`
    holds the raw configuration, its hashes and the source of every input.
    """
    path = Path(path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or "regimes" not in raw:
        raise ConfigError("%s: not a run configuration" % path)
    is_mock = bool(raw.get("mock"))
    if is_mock and not allow_mock:
        raise MockRefused("%s is a mock configuration (mock: true); pass --mock to run it" % path)

    _check_ph_axis(raw)

    charter = yaml.safe_load(Path(charter_path).read_text(encoding="utf-8"))
    lit_params = None
    if Path(lit_params_path).is_file():
        lit_params = yaml.safe_load(Path(lit_params_path).read_text(encoding="utf-8"))

    resolved = json.loads(json.dumps(raw))
    sources = []
    for p, node in _walk(raw):
        src = node["source"]
        if src not in SOURCES:
            raise ConfigError("%s: unknown source %r" % ("/".join(p), src))
        regime = p[1] if len(p) > 1 and p[0] == "regimes" else None
        if src == "mock":
            if not allow_mock:
                raise MockRefused("%s is a mock value; pass --mock to use it" % "/".join(p))
            if not is_mock:
                raise MockRefused("%s is a mock value in a configuration without mock: true"
                                  % "/".join(p))
            value = node["value"]
        elif src == "charter":
            value = _charter_value(regime, node, charter)
            if "value" in node and node["value"] != value:
                raise ConfigError("%s: %r disagrees with the charter (%r)"
                                  % ("/".join(p), node["value"], value))
        elif src == "lit/params.yaml":
            value = _lit_value(node, lit_params)
        else:
            value = node["value"]
        if "unit" in node:
            # keep the unit (and basis) next to the value so the consumer can check it
            value = {"value": value, "unit": node["unit"],
                     **({"basis": node["basis"]} if "basis" in node else {})}
        _set(resolved, p, value)
        sources.append({"input": "/".join(p), "source": src, "value": value,
                        **({"charter_key": node.get("charter_key")} if src == "charter" else {}),
                        **({"key": node.get("key")} if src == "lit/params.yaml" else {}),
                        **({"note": node["note"]} if "note" in node else {})})

    meta = {"path": path.resolve().relative_to(REPO).as_posix() if path.resolve().is_relative_to(REPO)
            else str(path), "file_hash": file_hash(path), "config_hash": canonical_hash(raw),
            "mock": is_mock, "sources": sources}
    return resolved, meta
