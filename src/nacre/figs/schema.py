"""Validate figure inputs against their owners' JSON Schemas (draft 2020-12).

A template names its schema in FIGURE["schema"]:
  "upstream:<key>"   a pinned owner contract (nacre.figs.upstream), e.g. upstream:results_schema
  "<path>.json"      a schema file in this repository, relative to the root
"""
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from nacre.figs import upstream

UPSTREAM = "upstream:"


def resolve(ref, root):
    """(schema dict, citation string) for a template's schema reference."""
    if ref.startswith(UPSTREAM):
        key = ref[len(UPSTREAM):]
        return upstream.load(key, root), upstream.cite(key, root)
    return json.loads((Path(root) / ref).read_text()), ref


def _where(err):
    return "$" + "".join("[%d]" % p if isinstance(p, int) else ".%s" % p for p in err.absolute_path)


def validate(value, schema):
    """Return a list of error strings (empty when value conforms)."""
    v = Draft202012Validator(schema)
    errs = sorted(v.iter_errors(value), key=lambda e: (list(map(str, e.absolute_path)), e.message))
    return ["%s: %s" % (_where(e), e.message) for e in errs]
