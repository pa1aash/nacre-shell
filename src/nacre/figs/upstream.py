"""The owners' contracts the figure templates conform to, read from their pinned copies.

figures/src/schemas/upstream.yaml (written by figures/src/schemas/pin_upstream.py) names, for
each contract, the owner lane, the owner's path, the commit it was pinned at and the sha256 of
the byte copy in figures/src/schemas/upstream/. Inputs are validated against the pinned copy,
so a figure always states which version of an owner's contract it was built against. When the
owner's file is present in this tree and differs from the pin, drift() reports it.
"""
import csv
import hashlib
import io
import json
from functools import lru_cache
from pathlib import Path

import yaml

from nacre.figs import paths

REGISTRY = "upstream.yaml"


class UpstreamError(Exception):
    pass


def _sha(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=4)
def _registry(schemas_dir):
    return yaml.safe_load((Path(schemas_dir) / REGISTRY).read_text())["entries"]


def registry(root):
    return _registry(str(paths(root)["schemas"]))


def entry(key, root):
    reg = registry(root)
    if key not in reg:
        raise UpstreamError("no pinned contract %r in %s" % (key, REGISTRY))
    return reg[key]


def snapshot_bytes(key, root):
    """The pinned bytes, refused if they do not match the registry hash."""
    e = entry(key, root)
    data = (Path(root) / e["snapshot"]).read_bytes()
    if _sha(data) != e["sha256"]:
        raise UpstreamError("%s: %s does not match its pinned sha256" % (key, e["snapshot"]))
    return data


def parse_csv(text):
    """{"columns": [...], "rows": [{column: text}, ...]} of a CSV output file.

    Lines starting with '#' are comments (the benchmark file opens with one). Every cell stays
    a string; a template converts the columns it plots and refuses what it cannot read.
    """
    lines = [ln for ln in text.splitlines() if not ln.startswith("#")]
    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return {"columns": list(reader.fieldnames), "rows": [dict(r) for r in reader]}


def load(key, root):
    """Parsed pinned file (JSON, YAML or CSV by extension; text for anything else).

    CSV is returned as parse_csv() does.
    """
    e = entry(key, root)
    data = snapshot_bytes(key, root)
    suffix = Path(e["snapshot"]).suffix
    if suffix == ".csv":
        return parse_csv(data.decode("utf-8"))
    if suffix == ".json":
        return json.loads(data)
    if suffix in (".yaml", ".yml"):
        return yaml.safe_load(data)
    return data.decode("utf-8")


def cite(key, root):
    """'path@commit7 (owner)' for manifests and reports."""
    e = entry(key, root)
    return "%s@%s (%s)" % (e["path"], e["commit"][:7], e["owner"])


def drift(root):
    """[(key, message)] for every owner file present in this tree that differs from its pin."""
    out = []
    for key, e in sorted(registry(root).items()):
        p = Path(root) / e["path"]
        if p.exists() and _sha(p.read_bytes()) != e["sha256"]:
            out.append((key, "%s in this tree differs from the pin %s@%s; re-pin after integration"
                        % (e["path"], e["owner"], e["commit"][:7])))
    return out


@lru_cache(maxsize=4)
def _symbols(schemas_dir, sha):
    root = Path(schemas_dir).parents[2]
    return {s["id"]: s for s in load("symbols", root)["symbols"]}


def symbols(root):
    """theory/symbols.yaml (W3) as {id: entry}."""
    return _symbols(str(paths(root)["schemas"]), entry("symbols", root)["sha256"])
