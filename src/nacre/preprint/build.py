"""Build preparation and the release guard for the preprint.

`prepare(root, mode)` makes preprint/paper ready for latexmk:
  - locates the local-only publisher template (paths.template_dir), provisioning it with
    `nacre paper template --ensure` logic when no copy exists, and verifies every file
    against charter/venue/template.yaml;
  - renders build/rsc_head.tex from the template (nacre.report.template.render_head);
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
    (b / "rsc_head.tex").write_text(template.render_head(tdir), encoding="utf-8", newline="\n")
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
    derivation = root / "theory" / "derivation_body.tex"
    out("references: %d cited, all resolve in %s; %d without pages (marked in the build copy%s)"
        % (len(refs.cited(root)), texscan.rel(root, refs.source(root)), len(marked),
           ": " + ", ".join(marked) if marked else ""))
    out("derivation: %s" % ("present" if derivation.is_file() else "absent (W3 has not delivered it; SI shows a draft marker)"))
    if mode == "release":
        problems = guard(root)
        if problems:
            raise PrepareError("release guard: %d problem(s)\n  %s" % (len(problems), "\n  ".join(problems)))
        out("release guard: PASS")
    return tdir
