"""Thresholds and the decision rule of the screen (rule R-thr).

theory/thresholds.md (lane p0-w3, set at cp2) is the threshold authority. Its fenced
``thresholds`` block is copied verbatim into configs/preprint/thresholds.yaml under a
comment header naming the source commit; equal() checks the two agree (as parsed YAML and
as text), against the working tree or against a commit of W3's branch. After tag p0-cp3
both files change only through a dated entry in ops/tracks/p0_deviations.md.

The per-link evaluators and the study-level decision rule (nacre.screen.decision)
implement the rule as written in that block; load_thresholds raises ThresholdsNotFrozen
while the copy is missing, so no verdict can come from an unfrozen rule.
"""
import re
import subprocess
from pathlib import Path

import yaml

THEORY = Path("theory") / "thresholds.md"
COPY = Path("configs") / "preprint" / "thresholds.yaml"
_FENCE = re.compile(r"^(?P<fence>```+|~~~+)[ \t]*(?P<info>[^\n`]*)\n(?P<body>.*?)^(?P=fence)[ \t]*$",
                    re.MULTILINE | re.DOTALL)
_SHA = re.compile(r"^# source-sha: ([0-9a-f]{40})$", re.MULTILINE)


class ThresholdsNotFrozen(RuntimeError):
    """Raised by every evaluator call until configs/preprint/thresholds.yaml exists."""


class ThresholdsMismatch(ValueError):
    """The copy and theory/thresholds.md disagree, or the source has no unique block."""


_MESSAGE = ("per-link thresholds are not frozen: configs/preprint/thresholds.yaml is copied from "
            "theory/thresholds.md once W3 marks it ready (cp2)")


def extract_block(markdown):
    """Text of the single fenced code block whose info string names ``thresholds``."""
    blocks = [m.group("body") for m in _FENCE.finditer(markdown)
              if "thresholds" in m.group("info").replace(",", " ").split()]
    if len(blocks) != 1:
        raise ThresholdsMismatch("theory/thresholds.md must hold exactly one fenced `thresholds` block, found %d"
                                 % len(blocks))
    return blocks[0]


def header(source_sha):
    return ("# Machine-readable copy of the fenced `thresholds` block of theory/thresholds.md.\n"
            "# Copied verbatim; the authority is theory/thresholds.md (rule R-thr). Do not edit:\n"
            "# after tag p0-cp3 a change goes through a dated entry in ops/tracks/p0_deviations.md.\n"
            "# source: theory/thresholds.md\n"
            "# source-sha: %s\n" % source_sha)


def make_copy(markdown, source_sha):
    """Contents of configs/preprint/thresholds.yaml for the given source text and commit."""
    if not re.fullmatch(r"[0-9a-f]{40}", source_sha or ""):
        raise ValueError("source sha must be a full 40-character commit id")
    block = extract_block(markdown)
    yaml.safe_load(block)                      # the block must be valid YAML
    return header(source_sha) + block


def split_copy(text):
    """(source sha, block text) of a thresholds.yaml copy."""
    m = _SHA.search(text)
    if not m:
        raise ThresholdsMismatch("thresholds.yaml has no '# source-sha:' header")
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and lines[i].startswith("#"):
        i += 1
    return m.group(1), "".join(lines[i:])


def equal(markdown, copy_text):
    """Raise ThresholdsMismatch unless the copy's block equals the source block (text and YAML)."""
    block = extract_block(markdown)
    _, body = split_copy(copy_text)
    if body != block:
        raise ThresholdsMismatch("thresholds.yaml text differs from the fenced block of theory/thresholds.md")
    if yaml.safe_load(body) != yaml.safe_load(block):
        raise ThresholdsMismatch("thresholds.yaml parses differently from the fenced block")
    return True


def source_at(root, ref):
    """theory/thresholds.md at a git ref, and the commit that last changed it there."""
    head = subprocess.run(["git", "-C", str(root), "rev-parse", ref + "^{commit}"], capture_output=True, text=True,
                          check=True).stdout.strip()
    sha = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%H", head, "--", THEORY.as_posix()],
                         capture_output=True, text=True, check=True).stdout.strip()
    if not sha:
        raise FileNotFoundError("%s is not present at %s" % (THEORY, ref))
    text = subprocess.run(["git", "-C", str(root), "show", "%s:%s" % (head, THEORY.as_posix())],
                          capture_output=True, text=True, check=True).stdout
    return text, sha


def load_thresholds(path=COPY):
    """Parsed thresholds block with its source commit: {"source_sha": ..., "rule": {...}}."""
    path = Path(path)
    if not path.exists():
        raise ThresholdsNotFrozen(_MESSAGE)
    text = path.read_text(encoding="utf-8")
    sha, body = split_copy(text)
    return {"source_sha": sha, "rule": yaml.safe_load(body)}

