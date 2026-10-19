"""Validate the ChemRxiv package in preprint/package/ (P0-W2.4a).

Checks preprint/package/metadata.yaml against the track ledger and the author register, and the
package's markdown files against the policy sources:
  - the working title equals ops/tracks/p0.yaml meta.title_working;
  - the authors match ops/tracks/p0_authors.yaml in order, names, ORCID iDs and the corresponding
    flag, each has an affiliation, exactly one is corresponding, every ORCID iD passes the
    ISO 7064 MOD 11-2 checksum, and CRediT roles are a placeholder or names from
    charter/credit_taxonomy.md;
  - every cited requirement id resolves in ops/policy/p0/index.yaml or preprint/package/fetch_index.yaml,
    every sourced item is marked `recheck_live: true`, and every cited id appears in
    requirements_recheck.md;
  - every checklist item cites a source, and every item citing a captured page says "re-check live";
  - no email address and no result number appears anywhere in the package, and no sentence trips
    the scope linter (charter/scope_guard.md and the preprint's patterns).

A string starting with "TBD" is a placeholder. Placeholders are listed and allowed; with
release=True each one is an error.
"""
import re
from pathlib import Path

import yaml

from nacre.preprint import lint_scope

SCHEMA_ID = "chemrxiv-package/v1"
PACKAGE = Path("preprint/package")
METADATA = PACKAGE / "metadata.yaml"
CHECKLIST = PACKAGE / "submission_checklist.md"
RECHECK = PACKAGE / "requirements_recheck.md"
FETCH_INDEX = PACKAGE / "fetch_index.yaml"
POLICY_INDEX = Path("ops/policy/p0/index.yaml")
LEDGER = Path("ops/tracks/p0.yaml")
REGISTER = Path("ops/tracks/p0_authors.yaml")
TAXONOMY = Path("charter/credit_taxonomy.md")

SOURCE_KEYS = {"source", "offered_source", "rule_source"}
PLACEHOLDER = "TBD"
RECHECK_MARK = "re-check live"

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
ORCID = re.compile(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")
CAPTURE_ID = re.compile(r"^[TP]\d+(-\d+)?$")
CITATION = re.compile(r"\[([A-Z][A-Za-z0-9-]*(?:,\s*[A-Z][A-Za-z0-9-]*)*)\]")
CHECKBOX = re.compile(r"^\s*- \[[ xX]\]\s")
TAXONOMY_ROW = re.compile(r"^\| ([^|]+?) \| https://credit\.niso\.org/contributor-roles/")
# Tokens that carry digits but are not results: licence versions, ORCID iDs, DOIs, session ids,
# requirement ids, dates, hashes and the hash name.
NOT_RESULTS = [re.compile(p) for p in (
    r"CC[- ]BY(?:-NC)?(?:-ND)? \d\.\d", r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", r"\b10\.\d{4,9}/\S+",
    r"\b(?:P0-)?[WI]\d+(?:\.\d+)+[a-z]?\b",
    r"\b[TP]\d+-\d+\b", r"\b\d{4}-\d{2}-\d{2}\b", r"\b[0-9a-f]{40,64}\b", r"SHA-256")]
RESULT_NUMBER = re.compile(r"\d+\.\d+|\d+(?:\.\d+)?\s*(?:%|eV|kJ|kcal|mV|V|K|nm|µm|Å|mol|mM|M)(?![\w])")


def orcid_checksum_ok(orcid):
    """ISO 7064 MOD 11-2 check digit of an ORCID iD in 0000-0000-0000-000X form."""
    if not isinstance(orcid, str) or not ORCID.match(orcid):
        return False
    digits = orcid.replace("-", "")
    total = 0
    for ch in digits[:-1]:
        total = (total + int(ch)) * 2
    result = (12 - total % 11) % 11
    return digits[-1] == ("X" if result == 10 else str(result))


def is_placeholder(value):
    return isinstance(value, str) and value.strip().startswith(PLACEHOLDER)


def placeholders(node, path=""):
    """(dotted path, value) for every placeholder string in a parsed YAML tree."""
    out = []
    if isinstance(node, dict):
        for k, v in node.items():
            out += placeholders(v, "%s.%s" % (path, k) if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += placeholders(v, "%s[%d]" % (path, i))
    elif is_placeholder(node):
        out.append((path, node))
    return out


def _strings(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, "%s.%s" % (path, k) if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, "%s[%d]" % (path, i))
    elif isinstance(node, str):
        yield path, node


def _sourced(node, path=""):
    """(path, dict) for every mapping that carries a source key."""
    if isinstance(node, dict):
        if SOURCE_KEYS & set(node):
            yield path, node
        for k, v in node.items():
            yield from _sourced(v, "%s.%s" % (path, k) if path else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _sourced(v, "%s[%d]" % (path, i))


def result_numbers(text):
    for rx in NOT_RESULTS:
        text = rx.sub(" ", text)
    return [m.group(0) for m in RESULT_NUMBER.finditer(text)]


def known_ids(root):
    """Requirement ids from the policy index (pages and reused entries) and the package fetch index."""
    ids = set()
    for rel in (POLICY_INDEX, FETCH_INDEX):
        path = root / rel
        if path.is_file():
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            ids |= {e["id"] for e in (data.get("pages") or []) + (data.get("reused") or [])}
    return ids


def decision_ids(root):
    data = yaml.safe_load((root / LEDGER).read_text(encoding="utf-8")) or {}
    return {d["id"] for d in data.get("decisions") or []}


def credit_roles(root):
    names = set()
    for line in (root / TAXONOMY).read_text(encoding="utf-8").splitlines():
        m = TAXONOMY_ROW.match(line)
        if m:
            names.add(m.group(1).strip())
    return names


def _check_authors(meta, register, roles):
    errors = []
    authors = meta.get("authors") or []
    reg = register.get("authors") or []
    if not authors:
        return ["authors: none listed"]
    if len(authors) != len(reg):
        errors.append("authors: %d listed, the register has %d" % (len(authors), len(reg)))
    if sum(1 for a in authors if a.get("corresponding") is True) != 1:
        errors.append("authors: exactly one corresponding author is required")
    for i, a in enumerate(authors):
        label = "authors[%d] %s" % (i, a.get("family_name") or "?")
        for key in ("given_name", "family_name"):
            if not isinstance(a.get(key), str) or not a[key].strip() or is_placeholder(a[key]):
                errors.append("%s: %s missing" % (label, key))
        aff = a.get("affiliations")
        if not isinstance(aff, list) or not aff or not all(isinstance(x, str) and x.strip() for x in aff):
            errors.append("%s: affiliations must be a non-empty list" % label)
        if not isinstance(a.get("corresponding"), bool):
            errors.append("%s: corresponding must be true or false" % label)
        orcid = a.get("orcid")
        if not is_placeholder(orcid) and not orcid_checksum_ok(orcid):
            errors.append("%s: ORCID iD %r fails the format or MOD 11-2 checksum" % (label, orcid))
        cr = a.get("credit_roles")
        if not is_placeholder(cr):
            if not isinstance(cr, list) or not cr:
                errors.append("%s: credit_roles must be a placeholder or a non-empty list" % label)
            else:
                errors += ["%s: %r is not a CRediT role" % (label, r) for r in cr if r not in roles]
        if i < len(reg):
            r = reg[i]
            for key in ("given_name", "family_name"):
                if a.get(key) != r.get(key):
                    errors.append("%s: %s %r differs from the register's %r" % (label, key, a.get(key), r.get(key)))
            if r.get("affiliation") not in (aff or []):
                errors.append("%s: register affiliation %r is not listed" % (label, r.get("affiliation")))
            reg_orcid = r.get("orcid")
            if is_placeholder(orcid) != is_placeholder(reg_orcid) or (not is_placeholder(orcid) and orcid != reg_orcid):
                errors.append("%s: ORCID iD %r differs from the register's %r" % (label, orcid, reg_orcid))
            if bool(a.get("corresponding")) != bool(r.get("corresponding")):
                errors.append("%s: corresponding flag differs from the register" % label)
    return errors


def _check_sources(meta, ids, recheck_text):
    errors, cited = [], set()
    for path, node in _sourced(meta):
        for key in SOURCE_KEYS & set(node):
            vals = node[key]
            if not isinstance(vals, list) or not vals:
                errors.append("%s.%s: must be a non-empty list of requirement ids" % (path, key))
                continue
            for v in vals:
                cited.add(v)
                if v not in ids:
                    errors.append("%s.%s: unknown requirement id %r" % (path, key, v))
        if node.get("recheck_live") is not True:
            errors.append("%s: sourced from a capture but not marked recheck_live: true" % path)
    for v in sorted(cited):
        if not re.search(r"\b%s\b" % re.escape(v), recheck_text):
            errors.append("requirements_recheck.md: cited id %s is not listed" % v)
    return errors


def _check_checklist(text, ids, decisions):
    errors = []
    for no, line in enumerate(text.splitlines(), 1):
        if not CHECKBOX.match(line):
            continue
        cites = [c.strip() for m in CITATION.finditer(line) for c in m.group(1).split(",")]
        if not cites:
            errors.append("submission_checklist.md:%d: item cites no requirement" % no)
            continue
        for c in cites:
            if c not in ids and c not in decisions:
                errors.append("submission_checklist.md:%d: unknown requirement id %r" % (no, c))
        if any(CAPTURE_ID.match(c) for c in cites) and RECHECK_MARK not in line:
            errors.append("submission_checklist.md:%d: cites a captured page but is not marked %r" % (no, RECHECK_MARK))
    return errors


def check(root, release=False):
    """Return (errors, info). info: placeholders [(path, value)], credit_missing [names], files [paths]."""
    root = Path(root)
    errors = []
    missing = [str(p) for p in (METADATA, CHECKLIST, RECHECK, FETCH_INDEX) if not (root / p).is_file()]
    if missing:
        return ["missing package file: %s" % m for m in missing], {"placeholders": [], "credit_missing": [], "files": []}
    meta_text = (root / METADATA).read_text(encoding="utf-8")
    meta = yaml.safe_load(meta_text) or {}
    checklist = (root / CHECKLIST).read_text(encoding="utf-8")
    recheck = (root / RECHECK).read_text(encoding="utf-8")
    ledger = yaml.safe_load((root / LEDGER).read_text(encoding="utf-8")) or {}
    register = yaml.safe_load((root / REGISTER).read_text(encoding="utf-8")) or {}
    ids = known_ids(root)

    if meta.get("schema") != SCHEMA_ID:
        errors.append("metadata.yaml: schema must be %r" % SCHEMA_ID)
    title = meta.get("title") or {}
    if title.get("working") != (ledger.get("meta") or {}).get("title_working"):
        errors.append("metadata.yaml: title.working differs from ops/tracks/p0.yaml meta.title_working")
    if not isinstance(title.get("final"), str) or not title["final"].strip():
        errors.append("metadata.yaml: title.final must be set or a placeholder")

    errors += _check_authors(meta, register, credit_roles(root))
    errors += _check_sources(meta, ids, recheck)
    errors += _check_checklist(checklist, ids, decision_ids(root))

    texts = {METADATA: meta_text, CHECKLIST: checklist, RECHECK: recheck,
             FETCH_INDEX: (root / FETCH_INDEX).read_text(encoding="utf-8")}
    for rel, text in texts.items():
        for m in EMAIL.finditer(text):
            errors.append("%s: email address %r; the package holds none (rule R9)" % (rel, m.group(0)))
    for rel in (METADATA, CHECKLIST, RECHECK):
        for no, line in enumerate(texts[rel].splitlines(), 1):
            for n in result_numbers(line):
                errors.append("%s:%d: number %r; numbers reach the text only through macros (rule R5)" % (rel, no, n))

    rs, allowed = lint_scope.rules(root), lint_scope.allowlist(root)
    errors += lint_scope.lint(root, files=[root / CHECKLIST, root / RECHECK])
    for path, s in _strings(meta):
        errors += lint_scope.check_text_blocks([[(0, s)]], "%s %s" % (METADATA, path), rs, allowed)

    found = placeholders(meta)
    if release:
        errors += ["release: placeholder at %s: %s" % (p, v) for p, v in found]
    credit_missing = ["%s %s" % (a.get("given_name"), a.get("family_name")) for a in meta.get("authors") or []
                      if is_placeholder(a.get("credit_roles"))]
    info = {"placeholders": found, "credit_missing": credit_missing,
            "files": [str(p) for p in (METADATA, CHECKLIST, RECHECK, FETCH_INDEX)]}
    return errors, info
