"""Draft build, the release guard (Python layer) and the release stops (LaTeX layer)."""
import csv
import re
import shutil
import subprocess

import pytest

from nacre.preprint import build, paths
from preprint_helpers import REPO, copy_tree, write

HAVE_LATEX = shutil.which("latexmk") is not None and shutil.which("pdflatex") is not None
HAVE_TEMPLATE = paths.template_dir(REPO) is not None
HAVE_PDFTOTEXT = shutil.which("pdftotext") is not None
BUILD_SH = paths.paper(REPO) / "build.sh"
NEEDS_BUILD = pytest.mark.skipif(not (HAVE_LATEX and HAVE_TEMPLATE and shutil.which("zsh")),
                                 reason="needs zsh, latexmk and the local-only template")


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
    assert not any("CRediT" in p for p in problems)          # ChemRxiv needs no CRediT statement
    write(paths.generated(root) / "declarations.tex", "\\newcommand{\\nacreFunding}{TBD}\n")
    assert any("declarations.tex:1: TBD remains" in p for p in build.guard(root))


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


@pytest.fixture(scope="module")
def draft_build():
    """One draft build for every test that reads the built PDFs."""
    gen = paths.generated(REPO)
    for f in ("numbers", "front", "authors", "declarations"):
        (gen / (f + ".tex")).unlink(missing_ok=True)       # the build must regenerate them itself
    return subprocess.run(["zsh", str(BUILD_SH), "draft"], capture_output=True, text=True)


def _pdf_pages(pdf, layout=True):
    """The text of each page of a built PDF (pdftotext), in layout mode or in reading order."""
    out = subprocess.run(["pdftotext"] + (["-layout"] if layout else []) + [str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    return out.split("\f")


@NEEDS_BUILD
def test_draft_build_compiles(draft_build):
    gen = paths.generated(REPO)
    p = draft_build
    assert p.returncode == 0, (p.stdout + p.stderr)[-3000:]
    assert all((gen / (f + ".tex")).is_file() for f in ("numbers", "front", "authors", "declarations"))
    assert (paths.build(REPO) / "draft" / "main.pdf").is_file()
    assert (paths.build(REPO) / "draft" / "si" / "main_si.pdf").is_file()
    assert "lint-numbers: PASS" in p.stdout and "lint-scope: PASS" in p.stdout


def test_build_script_prepares_before_compiling():
    text = BUILD_SH.read_text(encoding="utf-8")
    assert text.index("nacre preprint prepare") < text.index("latexmk -pdf")
    assert "nacre preprint prepare --mode" in BUILD_SH.read_text(encoding="utf-8")


def test_generate_replaces_stale_files(tmp_path):
    root = copy_tree(tmp_path)
    gen = paths.generated(root)
    fresh = {f.name: f.read_text(encoding="utf-8") for f in gen.glob("*.tex")}
    assert set(fresh) == {"numbers.tex", "front.tex", "authors.tex", "declarations.tex"}
    for f in gen.glob("*.tex"):
        f.write_text("stale\n", encoding="utf-8")
    (gen / "front.tex").unlink()
    build.generate(root)
    assert {f.name: f.read_text(encoding="utf-8") for f in gen.glob("*.tex")} == fresh


def test_main_and_si_load_theory_macros_before_any_theory_input():
    load = "\\IfFileExists{../../theory/macros.tex}{\\input{../../theory/macros.tex}}{}"
    for rel in ("main.tex", "si/main_si.tex"):
        text = (paths.paper(REPO) / rel).read_text(encoding="utf-8")
        assert load in text, rel
        for later in ("\\input{sections/introduction}", "\\section{Full derivation}"):
            if later in text:
                assert text.index(load) < text.index(later), rel
        for theory_input in ("theory/derivation_body", "theory/si_derivation"):
            if theory_input in text:
                assert text.index(load) < text.index(theory_input), rel


# --- the built text (cp6 F1, F22) --------------------------------------------------------------------

def _label_on_its_row(label, tag):
    """A regex for one regime-table row as pdftotext lays it out: the label (its words before a long
    parenthesis, which wraps) and then, on the same line, the stage tag. Whitespace is dropped on both sides,
    since subscripts come out with spaces (Ca2 P2 O7)."""
    label = label.replace("beta-", "\u03b2-").replace("alpha-", "\u03b1-")
    if " (" in label and len(label) > 25:
        label = label[:label.index(" (")]
    return re.compile(re.escape(re.sub(r"\s+", "", label)) + r".*" + re.escape(tag))


@NEEDS_BUILD
@pytest.mark.skipif(not HAVE_PDFTOTEXT, reason="needs pdftotext")
def test_every_regime_table_row_is_in_the_built_pdf(draft_build):
    assert draft_build.returncode == 0
    rows = {}
    with (paths.generated(REPO) / "regime_table.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            rows.setdefault(r["row_id"], (r["row_label"], r["stage_tag"]))
    pages = [p for p in _pdf_pages(paths.build(REPO) / "draft" / "main.pdf")
             if "Regime map of the thermodynamic screen" in p]
    assert pages, "no page carries the regime table"
    lines = [re.sub(r"\s+", "", line) for p in pages for line in p.splitlines()]
    missing = [rid for rid, (label, tag) in rows.items()
               if not any(_label_on_its_row(label, tag).search(line) for line in lines)]
    assert not missing, "regime-table rows absent from the built PDF: %s" % ", ".join(missing)
    assert len(rows) == 19



@pytest.mark.skipif(not HAVE_TEMPLATE, reason="needs the local-only template")
def test_the_head_carries_no_journal_front_matter():
    from nacre.report import template
    head = build.strip_journal_front(template.render_head(paths.template_dir(REPO)))
    assert "head_foot/" not in head
    assert "\\nacreTitle" in head and "\\nacreAuthors" in head and "\\nacreAbstract" in head
    with pytest.raises(build.PrepareError):
        build.strip_journal_front(head)          # a head without the journal block is refused, not passed through
