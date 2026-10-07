"""Structured venue data: loading, consistency checks, refresh and display.

charter/venue/manuscript.yaml and artwork.yaml hold `fields`, a mapping of field
name to {value, unit?, source_url, locator, retrieved_utc, via}. template.yaml
holds the template provenance. This module never writes those files; `refresh`
re-fetches the sources and reports differences.
"""
import json
import re
from pathlib import Path

import yaml

FIELD_FILES = ("manuscript.yaml", "artwork.yaml")
REQUIRED_KEYS = ("source_url", "locator", "retrieved_utc", "via")
MAX_PHRASE_WORDS = 15


def venue_dir(root):
    return Path(root) / "charter" / "venue"


def load_fields(path):
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return data.get("fields") or {}


def coverage(root):
    """{file: (found, total)} where found means value is not null."""
    out = {}
    for name in FIELD_FILES:
        path = venue_dir(root) / name
        if not path.exists():
            continue
        fields = load_fields(path)
        out[name] = (sum(1 for f in fields.values() if f.get("value") is not None), len(fields))
    return out


def _words(value):
    return len(str(value).split())


def consistency(root):
    """Return a list of problem strings; empty means consistent."""
    problems = []
    for name in FIELD_FILES:
        path = venue_dir(root) / name
        if not path.exists():
            problems.append("%s: missing" % name)
            continue
        for key, f in load_fields(path).items():
            where = "%s:%s" % (name, key)
            if not isinstance(f, dict) or "value" not in f:
                problems.append("%s: not a field object" % where)
                continue
            if f["value"] is None:
                continue
            for req in REQUIRED_KEYS:
                if not f.get(req):
                    problems.append("%s: value present but %s missing" % (where, req))
            if f.get("via") not in (None, "live", "wayback"):
                problems.append("%s: via must be live or wayback" % where)
            v = f["value"]
            if isinstance(v, str) and _words(v) > MAX_PHRASE_WORDS:
                problems.append("%s: string value over %d words (copied passage?)" % (where, MAX_PHRASE_WORDS))
            if isinstance(v, list) and any(isinstance(x, str) and _words(x) > MAX_PHRASE_WORDS for x in v):
                problems.append("%s: list item over %d words (copied passage?)" % (where, MAX_PHRASE_WORDS))
            loc = f.get("locator")
            if isinstance(loc, str) and _words(loc) > MAX_PHRASE_WORDS:
                problems.append("%s: locator over %d words" % (where, MAX_PHRASE_WORDS))
    tpl = venue_dir(root) / "template.yaml"
    if tpl.exists():
        t = yaml.safe_load(tpl.read_text(encoding="utf-8")) or {}
        for req in ("archive_url", "retrieved_utc", "archive_sha256", "files"):
            if not t.get(req):
                problems.append("template.yaml: %s missing" % req)
    else:
        problems.append("template.yaml: missing")
    return problems


def _norm(text):
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&nbsp;|&#160;", " ", text)
    return re.sub(r"\s+", " ", text).lower()


def _scalars(value):
    if isinstance(value, (list, tuple)):
        for v in value:
            yield from _scalars(v)
    elif isinstance(value, dict):
        for v in value.values():
            yield from _scalars(v)
    elif value is not None and not isinstance(value, bool):
        yield str(value)


def _last_hashes(log_path):
    hashes = {}
    if Path(log_path).exists():
        for line in Path(log_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row.get("sha256") and not row.get("error"):
                    hashes[row["url"]] = row["sha256"]
    return hashes


def refresh(root, fetcher):
    """Re-fetch every source URL. Returns (lines, n_changed).

    A page is "changed" when its sha256 differs from the last logged fetch of the
    same URL. A field is "stale?" when its value text no longer appears in the page.
    """
    lines, changed = [], 0
    previous = _last_hashes(fetcher.log_path)
    by_url = {}
    for name in FIELD_FILES:
        path = venue_dir(root) / name
        if path.exists():
            for key, f in load_fields(path).items():
                if f.get("value") is not None and f.get("source_url"):
                    by_url.setdefault(f["source_url"], []).append((name, key, f))
    for url, fields in sorted(by_url.items()):
        res = fetcher.get(url)
        if not res.ok:
            lines.append("UNREACHABLE %s (%s)" % (url, res.error))
            changed += 1
            continue
        status = "unchanged" if previous.get(url) == res.sha256 else ("new" if url not in previous else "CHANGED")
        if status == "CHANGED":
            changed += 1
        lines.append("%-9s %s (via %s)" % (status, url, res.via))
        text = _norm(res.text())
        for name, key, f in fields:
            vals = list(_scalars(f["value"]))
            missing = [v for v in vals if _norm(v) not in text]
            if missing:
                lines.append("  stale?    %s:%s value not found in page text: %s" % (name, key, ", ".join(missing[:3])))
    tpl = venue_dir(root) / "template.yaml"
    if tpl.exists():
        t = yaml.safe_load(tpl.read_text(encoding="utf-8")) or {}
        if t.get("archive_url"):
            res = fetcher.get(t["archive_url"])
            if not res.ok:
                lines.append("UNREACHABLE %s (%s)" % (t["archive_url"], res.error))
                changed += 1
            elif res.sha256 != t.get("archive_sha256"):
                lines.append("CHANGED   template archive sha256 differs from template.yaml")
                changed += 1
            else:
                lines.append("unchanged template archive (via %s)" % res.via)
    return lines, changed


def show(root, which=None, prefix=""):
    rows = []
    for name in FIELD_FILES:
        if which and which not in name:
            continue
        path = venue_dir(root) / name
        if not path.exists():
            continue
        for key, f in load_fields(path).items():
            if key.startswith(prefix):
                unit = f.get("unit") or ""
                rows.append("%-12s %-44s %s %s" % (name.split(".")[0], key,
                                                    "null" if f.get("value") is None else f["value"], unit))
    return rows
