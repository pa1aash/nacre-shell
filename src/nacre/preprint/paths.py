"""Locations used by the preprint tooling. Every function takes the repository root.

The publisher template is local-only and git-ignored, so a lane worktree may not hold a
copy. It is looked up in order: $NACRE_RSC_TEMPLATE, <worktree>/paper/rsc_template, then
<main checkout>/paper/rsc_template (the main checkout is the parent of the common git dir).
"""
import os
import subprocess
from pathlib import Path

TEMPLATE_ENV = "NACRE_RSC_TEMPLATE"
MODES = ("draft", "release")


def preprint(root):
    return Path(root) / "preprint"


def paper(root):
    return preprint(root) / "paper"


def generated(root):
    return preprint(root) / "generated"


def build(root):
    return paper(root) / "build"


def lint_dir(root):
    return paper(root) / "lint"


def sources_yaml(root):
    return generated(root) / "sources.yaml"


def numbers_tex(root):
    return generated(root) / "numbers.tex"


def claims_yaml(root):
    return preprint(root) / "claims.yaml"


def declarations_yaml(root):
    return paper(root) / "declarations.yaml"


def authors_yaml(root):
    return Path(root) / "ops" / "tracks" / "p0_authors.yaml"


def track_yaml(root):
    return Path(root) / "ops" / "tracks" / "p0.yaml"



def scope_guard(root):
    return Path(root) / "charter" / "scope_guard.md"


def ai_ack(root):
    """The local-only AI-use disclosure, included in the Acknowledgements as
    <repo-root>/.local/p0/ai_ack.tex (the same path sections/declarations.tex inputs)."""
    return Path(root) / ".local" / "p0" / "ai_ack.tex"


def main_checkout(root):
    p = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    return Path(p.stdout.strip()).parent


def template_candidates(root):
    out = []
    if os.environ.get(TEMPLATE_ENV):
        out.append(Path(os.environ[TEMPLATE_ENV]))
    out.append(Path(root) / "paper" / "rsc_template")
    main = main_checkout(root)
    if main is not None:
        out.append(main / "paper" / "rsc_template")
    seen, uniq = set(), []
    for c in out:
        key = str(c.resolve()) if c.exists() else str(c)
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return uniq


def template_dir(root):
    for c in template_candidates(root):
        if (c / "main.tex").is_file():
            return c
    return None
