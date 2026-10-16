"""Axis titles from the symbol table.

Until lane p0-w3's theory/symbols.yaml reaches this branch, titles come from
figures/src/schemas/symbols_assumed.yaml (status: assumed), reconciled on Day 2.
"""
from functools import lru_cache
from pathlib import Path

import yaml

from nacre.figs import paths


@lru_cache(maxsize=4)
def _table(src_dir):
    return yaml.safe_load((Path(src_dir) / "schemas" / "symbols_assumed.yaml").read_text())["symbols"]


def entry(key, root):
    table = _table(str(paths(root)["src"]))
    if key not in table:
        raise KeyError("symbol %r not in the symbol table" % key)
    return table[key]


def symbol(key, root):
    return entry(key, root)["label"]


def axis_title(key, root):
    """'label (unit)', or the bare label when the quantity has no unit."""
    e = entry(key, root)
    unit = e.get("unit")
    if not unit or unit == "relative":
        return e["label"]
    return "%s (%s)" % (e["label"], unit)
