"""Helpers shared by the preprint tests (no conftest here; see RUNBOOK section 7)."""
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _ignore(directory, names):
    """Skip build products and the git-ignored generated files; copy_tree regenerates them."""
    skip = {"build"}
    if Path(directory).name == "generated":
        skip |= {n for n in names if n.endswith(".tex")}
    return skip & set(names)


def copy_tree(tmp):
    """A throwaway repository root holding what the preprint tooling reads."""
    root = Path(tmp) / "repo"
    root.mkdir()
    shutil.copytree(REPO / "preprint", root / "preprint", ignore=_ignore)
    for rel in ("charter/scope_guard.md", "charter/credit_taxonomy.md", "charter/venue/template.yaml",
                "ops/tracks/p0.yaml", "ops/tracks/p0_authors.yaml"):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    from nacre.preprint import build
    build.generate(root)
    return root


def write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path
