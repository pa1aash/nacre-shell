"""Build preparation and the release guard for the preprint.

`prepare(root, mode)` makes preprint/paper ready for latexmk:
  - locates the local-only publisher template (paths.template_dir), provisioning it with
    `nacre paper template --ensure` logic when no copy exists, and verifies every file
    against charter/venue/template.yaml;
  - renders build/rsc_head.tex from the template (nacre.report.template.render_head), without the
    template's journal front matter (journal name, article-type bar, DOI, received and accepted dates,
    journal footer; cp6 F3), which a preprint does not carry;
  - writes build/mode.tex (draft or release), build/paths.tex (repository root and the
    AI-disclosure include) and build/template_dir.txt (read by build.sh);
  - regenerates numbers.tex and the declarations files in preprint/generated (git-ignored,
    build-time artefacts; see generate);
  - refuses a \\cite key with no entry in refs.bib, and writes build/bib/refs_build.bib, the copy
    bibtex reads (see nacre.preprint.refs);
  - in release mode, runs the release guard and refuses on any problem.

The release guard fails when the local-only AI disclosure is missing, when any placeholder,
pending marker or TBD remains in the manuscript or generated files, when a mock macro is
used, when a cited reference has no pages or article number, when a \\cite key is unresolved,
or when either linter fails. The LaTeX layer (nacre-preamble.tex) repeats the
placeholder, missing-input and mock checks at use time, so a release PDF cannot carry them.
"""
import re
from pathlib import Path

from nacre.preprint import declarations, lint_numbers, lint_scope, macros, paths, refs, texscan
from nacre.report import template

_SAFE_PATH = re.compile(r"^[A-Za-z0-9/._-]+$")
_MARKERS = re.compile(r"\\nacre(Placeholder|Pending)\b")
_TBD = re.compile(r"\bTBD\b")
# The template's journal artwork: name, logo and article-type bar (one block), the DOI and dates boxes of the
# title table, and the journal footer. Every \includegraphics of head_foot/ is journal front matter.
_JOURNAL_BLOCK = re.compile(r"\{\\includegraphics\[height=30pt\]\{head_foot/journal_name\}.*?\{head_foot/header_bar\}\}\\par", re.S)
_JOURNAL_ART = re.compile(r"\\includegraphics(\[[^\]]*\])?\{head_foot/[^}]*\}")


class PrepareError(Exception):
    pass


def resolve_template(root, out=print):
    spec = template.load_spec(root)
    tdir = paths.template_dir(root)
    if tdir is None:
        out("template: no local copy in %s; provisioning" % ", ".join(str(c) for c in paths.template_candidates(root)))
        template.ensure(root, out=out)
        tdir = paths.template_dir(root)
    problems = template.verify_dir(tdir, spec)
    if problems:
        raise PrepareError("template at %s does not match template.yaml:\n  %s" % (tdir, "\n  ".join(problems)))
    return tdir, len(spec["files"])


def _tex_path(p, what):
    s = Path(p).as_posix()
    if not _SAFE_PATH.match(s):
        raise PrepareError("%s path %r has characters TeX cannot take in a file name" % (what, s))
    return s


def strip_journal_front(head):
    """The rendered template head without the journal's front matter; refuses a head whose layout has changed."""
    out, n = _JOURNAL_BLOCK.subn("", head)
    if n != 1:
        raise PrepareError("template head: the journal name and article-type block was not found once (%d)" % n)
    # the dates box gave the abstract its space below the authors; the template's own spacer row replaces it
    out = out.replace("\\includegraphics{head_foot/dates} &", "\\vspace{0.3cm} & \\vspace{0.3cm} \\\\\n &", 1)
    out, n = _JOURNAL_ART.subn("", out)
    if n < 3:
        raise PrepareError("template head: expected the DOI box and the journal footer, found %d" % n)
    # the SI provenance tables (lane W1) are long tables; the template loads no package for them
    if out.count("\\begin{document}") != 1:
        raise PrepareError("template head: \\begin{document} not found once")
    return out.replace("\\begin{document}", "\\usepackage{longtable}\n\\begin{document}", 1)


def guard_files(root):
    files = texscan.manuscript_tex(root)
    gen = paths.generated(root)
    files += sorted(f for f in gen.glob("*.tex") if f.is_file())
    return files


def guard(root):
    """Release guard. Returns a list of problems; empty means release may proceed."""
    root = Path(root)
    problems = []
    ack = paths.ai_ack(root)
    if not ack.is_file():
        problems.append("AI-use disclosure missing: %s (local-only; wording by Palaash at P0-W8.5)" % ack)
    mocks = macros.mock_names(root)
    mock_rx = re.compile(r"\\(%s)(?![A-Za-z])" % "|".join(mocks)) if mocks else None
    for f in guard_files(root):
        rel = texscan.rel(root, f)
        is_numbers = f == paths.numbers_tex(root)
        for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            text = texscan.strip_comment(line)
            m = _MARKERS.search(text)
            if m:
                problems.append("%s:%d: \\nacre%s remains" % (rel, no, m.group(1)))
            if _TBD.search(text):
                problems.append("%s:%d: TBD remains" % (rel, no))
            if mock_rx and not is_numbers:
                for name in mock_rx.findall(text):
                    problems.append("%s:%d: mock macro \\%s used" % (rel, no, name))
    problems += ["refs: " + p for p in refs.unresolved(root)]
    problems += ["refs: %s has no pages or article number (the fetched entry lacks them)" % k
                 for k in refs.without_pages(root)]
    problems += ["lint-numbers: " + p for p in lint_numbers.lint(root)]
    problems += ["lint-scope: " + p for p in lint_scope.lint(root)]
    return problems


def generate(root):
    """Write every build-time file in preprint/generated from the ledger, register and result files.

    These files are git-ignored; this runs on every prepare, so a stale copy is never compiled."""
    _, nmacros = macros.write(root)
    declarations.write_all(root)
    return nmacros


def prepare(root, mode, out=print):
    root = Path(root)
    if mode not in paths.MODES:
        raise PrepareError("mode must be one of %s" % ", ".join(paths.MODES))
    tdir, nfiles = resolve_template(root, out)
    b = paths.build(root)
    b.mkdir(parents=True, exist_ok=True)
    (b / "rsc_head.tex").write_text(strip_journal_front(template.render_head(tdir)), encoding="utf-8", newline="\n")
    (b / "mode.tex").write_text("\\nacrerelease%s\n" % ("true" if mode == "release" else "false"),
                                encoding="utf-8", newline="\n")
    (b / "paths.tex").write_text(
        "\\def\\nacreRepoRoot{%s}\n" % _tex_path(root, "repository root"),
        encoding="utf-8", newline="\n")
    (b / "template_dir.txt").write_text(str(tdir) + "\n", encoding="utf-8", newline="\n")
    nmacros = generate(root)
    unresolved = refs.unresolved(root)
    if unresolved:
        raise PrepareError("citations: %d unresolved\n  %s" % (len(unresolved), "\n  ".join(unresolved)))
    _, marked = refs.write_build_copy(root)
    out("template: %s (%d files verified)" % (tdir, nfiles))
    out("macros: %d written to %s" % (nmacros, texscan.rel(root, paths.numbers_tex(root))))
    derivation = root / "theory" / "si_derivation.tex"
    out("references: %d cited, all resolve in %s; %d without pages (marked in the build copy%s)"
        % (len(refs.cited(root)), texscan.rel(root, refs.source(root)), len(marked),
           ": " + ", ".join(marked) if marked else ""))
    out("SI derivation: %s" % ("present" if derivation.is_file()
                               else "absent (theory/si_derivation.tex, P0-W3.4, not pushed; the SI shows a placeholder)"))
    if mode == "release":
        problems = guard(root)
        if problems:
            raise PrepareError("release guard: %d problem(s)\n  %s" % (len(problems), "\n  ".join(problems)))
        out("release guard: PASS")
    return tdir
