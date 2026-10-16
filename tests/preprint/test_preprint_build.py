"""Draft build, the release guard (Python layer) and the release stops (LaTeX layer)."""
import shutil
import subprocess

import pytest

from nacre.preprint import build, paths
from preprint_helpers import REPO, copy_tree, write

HAVE_LATEX = shutil.which("latexmk") is not None and shutil.which("pdflatex") is not None
HAVE_TEMPLATE = paths.template_dir(REPO) is not None
BUILD_SH = paths.paper(REPO) / "build.sh"


def _clean_manuscript(root):
    """Replace every placeholder source with clean text and clean generated files."""
    paper = paths.paper(root)
    for f in (paper / "sections").glob("*.tex"):
        f.write_text("\\section{Heading}\nPlain text.\n", encoding="utf-8")
    write(paper / "si" / "main_si.tex", "\\section{Heading}\nPlain text.\n")
    for f in paths.generated(root).glob("*.tex"):
        if f.name != "numbers.tex":
            f.write_text("\\newcommand{\\nacreX}{done}\n", encoding="utf-8")


def test_guard_requires_the_ai_disclosure(tmp_path):
    root = copy_tree(tmp_path)
    problems = build.guard(root)
    assert any("AI-use disclosure missing" in p for p in problems)
    write(paths.ai_ack(root), "Disclosure.\n")
    assert not any("AI-use disclosure missing" in p for p in build.guard(root))


def test_guard_refuses_placeholders_and_tbd(tmp_path):
    root = copy_tree(tmp_path)
    problems = build.guard(root)
    assert any("nacrePlaceholder remains" in p for p in problems)
    assert any("nacrePending remains" in p for p in problems)
    assert any("TBD remains" in p for p in problems)


def test_guard_passes_a_clean_manuscript_and_refuses_mock_use(tmp_path):
    root = copy_tree(tmp_path)
    write(paths.ai_ack(root), "Disclosure.\n")
    _clean_manuscript(root)
    assert build.guard(root) == []
    write(paths.paper(root) / "sections" / "results.tex", "The median is \\NumThetaMedian.\n")
    problems = build.guard(root)
    assert problems == ["preprint/paper/sections/results.tex:1: mock macro \\NumThetaMedian used"]


def test_guard_runs_both_linters(tmp_path):
    root = copy_tree(tmp_path)
    write(paths.ai_ack(root), "Disclosure.\n")
    _clean_manuscript(root)
    write(paths.paper(root) / "sections" / "results.tex", "We used 12 draws. The device is stable.\n")
    problems = build.guard(root)
    assert any(p.startswith("lint-numbers:") for p in problems)
    assert any(p.startswith("lint-scope:") for p in problems)


# --- LaTeX layer: the preamble stops a release build where a marker is used -------------------

def _tex(tmp_path, mode, body):
    d = tmp_path / ("tex_" + mode)
    d.mkdir(exist_ok=True)
    shutil.copy2(paths.paper(REPO) / "nacre-preamble.tex", d / "nacre-preamble.tex")
    write(d / "build" / "mode.tex", "\\nacrerelease%s\n" % ("true" if mode == "release" else "false"))
    write(d / "t.tex", "\\input{nacre-preamble}\n\\documentclass{article}\n\\usepackage{xcolor}\n"
                       "\\newcommand{\\NumX}{\\nacreMockNum{NumX}{1.0}{}}\n"
                       "\\begin{document}\n%s\n\\end{document}\n" % body)
    p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "t.tex"],
                       cwd=d, capture_output=True, text=True)
    return p.returncode, p.stdout


@pytest.mark.skipif(not HAVE_LATEX, reason="pdflatex not installed")
@pytest.mark.parametrize("body", ["\\nacrePlaceholder{x}", "\\nacrePending{x}", "\\nacreMissing{x}", "\\NumX"])
def test_latex_release_stops_on_markers(tmp_path, body):
    rc, out = _tex(tmp_path, "release", body)
    assert rc != 0 and "NACRE release guard" in out
    rc, out = _tex(tmp_path, "draft", body)
    assert rc == 0, out[-2000:]


@pytest.mark.skipif(not HAVE_LATEX, reason="pdflatex not installed")
def test_latex_release_accepts_real_numbers(tmp_path):
    rc, out = _tex(tmp_path, "release", "Value \\nacreNum{1.5}{\\mathrm{J}}.")
    assert rc == 0, out[-2000:]


# --- the real build script -----------------------------------------------------------------------

@pytest.mark.skipif(not (HAVE_LATEX and HAVE_TEMPLATE and shutil.which("zsh")),
                    reason="needs zsh, latexmk and the local-only template")
def test_release_build_fails_while_placeholders_or_the_ai_file_are_missing():
    p = subprocess.run(["zsh", str(BUILD_SH), "release"], capture_output=True, text=True)
    out = p.stdout + p.stderr
    assert p.returncode != 0
    assert "release guard" in out
    assert "nacrePlaceholder remains" in out or "AI-use disclosure missing" in out
    assert not (paths.build(REPO) / "release" / "main.pdf").exists()


@pytest.mark.skipif(not (HAVE_LATEX and HAVE_TEMPLATE and shutil.which("zsh")),
                    reason="needs zsh, latexmk and the local-only template")
def test_draft_build_compiles():
    p = subprocess.run(["zsh", str(BUILD_SH), "draft"], capture_output=True, text=True)
    assert p.returncode == 0, (p.stdout + p.stderr)[-3000:]
    assert (paths.build(REPO) / "draft" / "main.pdf").is_file()
    assert (paths.build(REPO) / "draft" / "si" / "main_si.pdf").is_file()
    assert "lint-numbers: PASS" in p.stdout and "lint-scope: PASS" in p.stdout
