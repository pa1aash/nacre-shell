"""Trace audit: does each row's number appear in the locally cached text of its DOI?

Local-only (it reads .local/lit), so it is an orchestrator check, not part of the committed validator.
A row is `traced` when its value (or both ends of its lo..hi range) occurs in a cached full text or
abstract of the same DOI, after normalising minus signs, dashes and spacing; `derived` when it is a
grade-C row whose notes declare a derivation; `qualitative` rows are not checked; everything else is
`untraced`.
"""
import json
import re
from pathlib import Path

from nacre.lit import evidence as E

_MINUS = dict.fromkeys(map(ord, "−‒–—‐‑˗"), "-")
_SPACE = re.compile(r"[\s   ]+")


def norm(text):
    return _SPACE.sub(" ", (text or "").translate(_MINUS))


def number_forms(value):
    """Search forms of a printed number: as written, without sign/comparator, and e-notation split."""
    v = value.strip().lstrip("<>=≤≥ ").strip()
    forms = {v, v.lstrip("+-")}
    m = re.match(r"^([-+]?\d*\.?\d+)[eE]([-+]?\d+)$", v)
    if m:
        mant, exp = m.group(1), str(int(m.group(2)))
        forms = {mant.lstrip("+-") + "|" + exp}
    return {f for f in forms if f}


def _found(form, text):
    if "|" in form:
        mant, exp = form.split("|")
        rx = r"%s\s*(?:[x×*·]|×)\s*10\s*(?:\^|\*\*)?\s*\(?\s*%s\b" % (re.escape(mant), re.escape(exp).replace("-", r"-\s*"))
        return re.search(rx, text) is not None or re.search(r"%s\s*[eE]\s*%s\b" % (re.escape(mant), re.escape(exp)), text) is not None
    return re.search(r"(?<![\d.])%s(?![\d])" % re.escape(form), text) is not None


def texts_for(root, thread_dirs, doi):
    """Cached text files (full text .txt and abstracts) logged for `doi` in any thread's sources.jsonl."""
    out = []
    for d in thread_dirs:
        src = d / "sources.jsonl"
        if not src.exists():
            continue
        for line in src.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            s = json.loads(line)
            if (s.get("doi") or "").lower() != doi.lower() or not s.get("local_path"):
                continue
            p = Path(root) / s["local_path"]
            p = p if p.suffix == ".txt" else p.with_suffix(".txt")
            if p.exists():
                out.append(p)
    return sorted(set(out))


def audit(root, rows):
    root = Path(root)
    dirs = [root / "lit" / "corpus" / t for t in E.THREADS]
    cache = {}
    results = []
    for r in rows:
        if r["unit"] == E.QUALITATIVE:
            results.append((r["row_id"], "qualitative", ""))
            continue
        doi = r["doi"].lower()
        if doi not in cache:
            cache[doi] = " ".join(norm(p.read_text(encoding="utf-8", errors="replace")) for p in texts_for(root, dirs, doi))
        text = cache[doi]
        if not text:
            results.append((r["row_id"], "untraced", "no cached text for DOI"))
            continue
        wanted = []
        if r["value"].strip():
            wanted.append(r["value"])
        else:
            lo, hi = r["range_or_uncertainty"].split("..")
            wanted += [lo, hi]
        missing = [w for w in wanted if not any(_found(f, text) for f in number_forms(norm(w)))]
        if not missing:
            results.append((r["row_id"], "traced", ""))
        elif r["grade"] == "C" and re.search(r"deriv|computed from|calculated from|converted", r["notes"], re.I):
            results.append((r["row_id"], "derived", "not printed: %s" % ", ".join(missing)))
        else:
            results.append((r["row_id"], "untraced", "not found: %s" % ", ".join(missing)))
    return results
