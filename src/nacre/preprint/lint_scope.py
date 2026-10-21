"""lint-scope: no claim that the barrier works and no rate, capacity, cycling, device or performance wording.

Patterns come from two places, both applied case-insensitively to sentences:
  - the forbidden-claim block of charter/scope_guard.md (SG01..), the charter's list;
  - preprint/paper/lint/scope_patterns.txt (PS..), the preprint's additions (rule R6).

Scanned: every .tex file under preprint/paper (text, captions and comments; not build/),
every .md file under preprint/paper (outline and briefs), and the `statement` and `notes`
fields of preprint/claims.yaml.

The charter's second block, scope-guard-warn (SG17W..), holds warn patterns: a match is a warning
that fails only when the same sentence lacks the rule's exemption word (see WARN_EXEMPT): "thermodynamic"
for SG17W, "audit" for SG26W, "hypothesis" or "criterion" for SG27W, "aragonite" for SG29W. SG30W has no
exemption word: its own pattern already matches only when "for", "in" or "under" does not follow within six words.

A line or paragraph carrying the marker `<!-- sg:allow nacre -->` (or `% sg:allow nacre` in .tex) is skipped by the
patterns that match the word nacre, and by no other pattern.

The only exempt sentences are the explicit "does not claim" sentences listed verbatim in
preprint/paper/lint/scope_allowlist.txt. An allowlist line without "does not claim" is an error.
"""
import re
from pathlib import Path

import yaml

from nacre.preprint import paths, texscan

ALLOWLIST = "scope_allowlist.txt"
PATTERNS = "scope_patterns.txt"
_BLOCK = re.compile(r"```scope-guard\n(.*?)```", re.S)
_WARN_BLOCK = re.compile(r"```scope-guard-warn\n(.*?)```", re.S)
WARN_EXEMPT = {
    "SG17W": re.compile(r"\bthermodynamic", re.I),
    "SG26W": re.compile(r"\baudit", re.I),
    "SG27W": re.compile(r"\b(hypothes[ie]s|criteri(on|a))\b", re.I),
    "SG29W": re.compile(r"\baragonite\b", re.I),
    "SG30W": re.compile(r"(?!)"),
}
WARN_LABEL = {"SG17W": "thermodynamic", "SG26W": "audit", "SG27W": "hypothesis' or 'criterion",
              "SG29W": "aragonite", "SG30W": "for' / 'in' / 'under' within six words after it"}
WARN_WORD = WARN_EXEMPT["SG17W"]
ALLOW_NACRE = re.compile(r"sg:allow nacre", re.I)
_MD_START = re.compile(r"^\s*(#+\s|[-*+]\s|\d+[.)]\s|>\s)")
_SENT = re.compile(r"(?<=[.!?])\s+")


class ScopeConfigError(Exception):
    pass


def charter_rules(root):
    text = paths.scope_guard(root).read_text(encoding="utf-8")
    m = _BLOCK.search(text)
    if not m:
        raise ScopeConfigError("charter/scope_guard.md has no scope-guard block")
    rules = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            rid, rx = s.split(None, 1)
            rules.append((rid, re.compile(rx, re.I)))
    return rules


def warn_rules(root):
    """Patterns of the charter's scope-guard-warn block; none when the charter has no such block."""
    m = _WARN_BLOCK.search(paths.scope_guard(root).read_text(encoding="utf-8"))
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            rid, rx = s.split(None, 1)
            out.append((rid, re.compile(rx, re.I)))
    return out


def rules(root):
    return charter_rules(root) + texscan.load_rules(paths.lint_dir(root) / PATTERNS, "PS")


def normalise(sentence):
    s = re.sub(r"[*`]", "", sentence)
    return " ".join(s.split()).strip(" \"'")


def allowlist(root):
    path = paths.lint_dir(root) / ALLOWLIST
    allowed = set()
    for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "does not claim" not in s.lower():
            raise ScopeConfigError("%s:%d: allowlisted sentences must be explicit 'does not claim' sentences"
                                   % (texscan.rel(root, path), no))
        allowed.add(normalise(s))
    return allowed


def _blocks_tex(lines):
    """Paragraphs of a .tex file as [[(line_no, text)]]. Comment text is kept, and a run of
    comment lines is its own paragraph."""
    blocks, cur, prev_comment = [], [], None
    for no, raw in enumerate(lines, 1):
        is_comment = raw.lstrip().startswith("%")
        line = re.sub(r"(?<!\\)%+", " ", raw)
        if not line.strip() or (cur and is_comment != prev_comment):
            if cur:
                blocks.append(cur)
            cur = []
        if line.strip():
            cur.append((no, line))
        prev_comment = is_comment
    if cur:
        blocks.append(cur)
    return blocks


def _blocks_md(lines):
    """Paragraphs, list items, headings and table cells of a .md file as [[(line_no, text)]]."""
    blocks, cur = [], []

    def flush():
        if cur:
            blocks.append(list(cur))
        cur.clear()

    for no, raw in enumerate(lines, 1):
        s = raw.strip()
        if not s or s.startswith("```"):
            flush()
        elif s.startswith("|"):
            flush()
            blocks.extend([[(no, cell)] for cell in s.strip("|").split("|") if cell.strip()])
        elif _MD_START.match(raw):
            flush()
            cur.append((no, _MD_START.sub(" ", raw, count=1)))
        else:
            cur.append((no, raw))
    flush()
    return blocks


def _sentences(block):
    """Split a block into sentences; each sentence carries the line number of its offsets."""
    text, marks = "", []
    for no, line in block:
        marks.append((len(text), no))
        text += line.strip() + " "
    out, pos = [], 0
    for part in _SENT.split(text):
        start = text.find(part, pos)
        pos = start + len(part)
        out.append((part, start, marks))
    return out


def _line_at(marks, offset):
    no = marks[0][1]
    for off, n in marks:
        if off <= offset:
            no = n
    return no


def check_text_blocks(blocks, label, rs, allowed, warn=()):
    problems = []
    for block in blocks:
        marked = any(ALLOW_NACRE.search(line) for _, line in block)
        for sentence, start, marks in _sentences(block):
            for rid, rx in warn:
                exempt = WARN_EXEMPT.get(rid, WARN_WORD)
                m = rx.search(sentence)
                if m and not exempt.search(sentence):
                    problems.append("%s:%d: %s (warn) %r without %s in: %s" % (
                        label, _line_at(marks, start + m.start()), rid, m.group(0),
                        "'%s'" % WARN_LABEL.get(rid, "thermodynamic"), normalise(sentence)[:120]))
            for rid, rx in rs:
                m = rx.search(sentence)
                if not m:
                    continue
                if marked and "nacre" in rx.pattern:
                    continue
                if normalise(sentence) in allowed:
                    break
                problems.append("%s:%d: %s %r in: %s" % (label, _line_at(marks, start + m.start()), rid,
                                                         m.group(0), normalise(sentence)[:120]))
    return problems


def scanned_files(root):
    p = paths.paper(root)
    skip = p / "build"
    out = [f for f in sorted(p.rglob("*")) if f.suffix in (".tex", ".md") and f.is_file()
           and skip not in f.parents]
    return out


def lint(root, files=None):
    rs, allowed, warn = rules(root), allowlist(root), warn_rules(root)
    problems = []
    targets = files if files is not None else scanned_files(root)
    for f in targets:
        lines = Path(f).read_text(encoding="utf-8").splitlines()
        blocks = _blocks_md(lines) if Path(f).suffix == ".md" else _blocks_tex(lines)
        problems += check_text_blocks(blocks, texscan.rel(root, f), rs, allowed, warn)
    if files is None and paths.claims_yaml(root).is_file():
        problems += lint_claims(root, rs, allowed, warn=warn)
    return problems


def lint_claims(root, rs=None, allowed=None, path=None, warn=None):
    rs = rs if rs is not None else rules(root)
    warn = warn if warn is not None else warn_rules(root)
    allowed = allowed if allowed is not None else allowlist(root)
    path = Path(path) if path else paths.claims_yaml(root)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    problems = []
    for c in data.get("claims") or []:
        for field in ("statement", "notes"):
            value = c.get(field)
            if not value:
                continue
            block = [(0, line) for line in str(value).splitlines()]
            label = "%s[%s].%s" % (texscan.rel(root, path), c.get("id"), field)
            for p in check_text_blocks([block], label, rs, allowed, warn):
                problems.append(p.replace(":0:", ":", 1))
    return problems
