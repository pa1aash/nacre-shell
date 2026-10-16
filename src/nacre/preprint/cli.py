"""`nacre preprint`: macro pipeline, declarations, linters and build preparation for P0."""
from nacre import _util


def _macros(args):
    from nacre.preprint import macros, paths
    root = _util.repo_root()
    try:
        if args.check:
            current = paths.numbers_tex(root)
            fresh = macros.render(root)
            same = current.is_file() and current.read_text(encoding="utf-8") == fresh
            print("macros: %s" % ("up to date" if same else "STALE (run `nacre preprint macros`)"))
            return 0 if same else 1
        out, n = macros.write(root)
    except macros.MacroError as exc:
        print("macros: FAIL\n" + str(exc))
        return 1
    mocks = macros.mock_names(root)
    print("macros: %d written to %s (%d mock)" % (n, out.relative_to(root).as_posix(), len(mocks)))
    return 0


def _declarations(args):
    from nacre.preprint import declarations
    root = _util.repo_root()
    try:
        files = declarations.write_all(root)
    except declarations.DeclarationsError as exc:
        print("declarations: FAIL\n" + str(exc))
        return 1
    for f in files:
        print("wrote " + f.relative_to(root).as_posix())
    return 0


def _report(name, problems):
    for p in problems:
        print(p)
    print("%s: %s" % (name, "FAIL (%d)" % len(problems) if problems else "PASS"))
    return 1 if problems else 0


def _paths(root, given):
    from pathlib import Path
    return [Path(p).resolve() for p in given] if given else None


def _lint_numbers(args):
    from nacre.preprint import lint_numbers
    root = _util.repo_root()
    return _report("lint-numbers", lint_numbers.lint(root, _paths(root, args.files)))


def _lint_scope(args):
    from nacre.preprint import lint_scope
    root = _util.repo_root()
    try:
        problems = lint_scope.lint(root, _paths(root, args.files))
    except lint_scope.ScopeConfigError as exc:
        print("lint-scope: config error: %s" % exc)
        return 1
    return _report("lint-scope", problems)


def _prepare(args):
    from nacre.preprint import build, declarations, macros
    from nacre.report import template
    try:
        build.prepare(_util.repo_root(), args.mode)
    except (build.PrepareError, macros.MacroError, declarations.DeclarationsError, template.TemplateError) as exc:
        print("prepare (%s): FAIL\n%s" % (args.mode, exc))
        return 1
    return 0


def _guard(args):
    from nacre.preprint import build
    return _report("release guard", build.guard(_util.repo_root()))


def register(subparsers):
    p = subparsers.add_parser("preprint", help="preprint P0: number macros, declarations, linters, build")
    sub = p.add_subparsers(dest="preprint_command", metavar="<action>")
    sub.required = True
    q = sub.add_parser("macros", help="write preprint/generated/numbers.tex from sources.yaml")
    q.add_argument("--check", action="store_true", help="only report whether numbers.tex is up to date")
    q.set_defaults(func=_macros)
    q = sub.add_parser("declarations", help="write the generated title, author, CRediT and declaration files")
    q.set_defaults(func=_declarations)
    q = sub.add_parser("lint-numbers", help="fail on digits in prose and captions outside macros")
    q.add_argument("files", nargs="*", help="files to check (default: the manuscript sources)")
    q.set_defaults(func=_lint_numbers)
    q = sub.add_parser("lint-scope", help="fail on claims that the barrier works and out-of-scope wording")
    q.add_argument("files", nargs="*", help="files to check (default: preprint/paper and claims.yaml)")
    q.set_defaults(func=_lint_scope)
    q = sub.add_parser("prepare", help="template, head, mode, generated files; release mode runs the guard")
    q.add_argument("--mode", choices=["draft", "release"], default="draft")
    q.set_defaults(func=_prepare)
    q = sub.add_parser("guard", help="run the release guard only")
    q.set_defaults(func=_guard)
