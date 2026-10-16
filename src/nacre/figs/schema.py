"""A small JSON Schema subset validator for figure inputs (standard library only).

Supported keywords: type, required, properties, additionalProperties (false), items, enum,
const, minItems, maxItems, minimum, maximum. Enough for figures/src/schemas/*.json; the
schemas declare draft 2020-12 so a full validator can replace this one without edits.
"""
_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "integer": int,
    "number": (int, float),
    "null": type(None),
}


def _type_ok(value, name):
    if name in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, _TYPES[name])


def validate(value, schema, path="$"):
    """Return a list of error strings (empty when value conforms)."""
    errs = []
    t = schema.get("type")
    if t is not None:
        names = t if isinstance(t, list) else [t]
        if not any(_type_ok(value, n) for n in names):
            return ["%s: expected %s, got %s" % (path, "|".join(names), type(value).__name__)]
    if "const" in schema and value != schema["const"]:
        errs.append("%s: must equal %r" % (path, schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errs.append("%s: %r not in %r" % (path, value, schema["enum"]))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append("%s: %r < minimum %r" % (path, value, schema["minimum"]))
        if "maximum" in schema and value > schema["maximum"]:
            errs.append("%s: %r > maximum %r" % (path, value, schema["maximum"]))
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errs.append("%s: missing %r" % (path, key))
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs.extend(validate(value[key], sub, "%s.%s" % (path, key)))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errs.append("%s: unexpected %r" % (path, key))
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append("%s: fewer than %d items" % (path, schema["minItems"]))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append("%s: more than %d items" % (path, schema["maxItems"]))
        if "items" in schema:
            for i, item in enumerate(value):
                errs.extend(validate(item, schema["items"], "%s[%d]" % (path, i)))
    return errs
