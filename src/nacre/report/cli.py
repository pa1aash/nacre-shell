"""Commands of the report package: venue (now), paper and bib (S03)."""
from nacre import _util


def _venue_fetch(args):
    from nacre.report import venue
    from nacre.report.fetch import Fetcher
    root = _util.repo_root()
    lines, changed = venue.refresh(root, Fetcher(venue_dir=venue.venue_dir(root)))
    print("\n".join(lines))
    print("venue fetch: %d difference(s)" % changed)
    return 1 if changed else 0


def _venue_show(args):
    from nacre.report import venue
    root = _util.repo_root()
    for row in venue.show(root, args.file, args.prefix):
        print(row)
    for name, (found, total) in venue.coverage(root).items():
        print("%s: %d/%d fields found" % (name, found, total))
    return 0


def _venue_check(args):
    from nacre.report import venue
    problems = venue.consistency(_util.repo_root())
    for p in problems:
        print("problem: " + p)
    print("venue check: %s" % ("FAIL (%d)" % len(problems) if problems else "PASS"))
    return 1 if problems else 0


def _paper_template(args):
    from nacre.report import template
    if not args.ensure:
        print("nothing to do; pass --ensure")
        return 2
    try:
        template.ensure(_util.repo_root())
    except template.TemplateError as exc:
        print("template: FAIL\n" + str(exc))
        return 1
    return 0


def _paper_build(args):
    from nacre.report import build, template
    try:
        return build.build(_util.repo_root(), si=args.si, check=args.check)
    except template.TemplateError as exc:
        print("template: FAIL\n" + str(exc))
        return 1


def _bib_add(args):
    from nacre.report import bib
    try:
        return bib.add(_util.repo_root(), args.doi, dry_run=args.dry_run)
    except bib.BibError as exc:
        print("bib add: " + str(exc))
        return 1


def _bib_check(args):
    from nacre.report import bib
    return bib.check(_util.repo_root())


def register(subparsers):
    paper = subparsers.add_parser("paper", help="manuscript template and build")
    psub = paper.add_subparsers(dest="paper_command", metavar="<action>")
    psub.required = True
    p = psub.add_parser("template", help="verify or provision the publisher template")
    p.add_argument("--ensure", action="store_true", help="verify files, or download, verify and unpack")
    p.set_defaults(func=_paper_template)
    p = psub.add_parser("build", help="build the manuscript (and SI) with latexmk")
    p.add_argument("--si", action="store_true", help="also build the supplementary information")
    p.add_argument("--check", action="store_true", help="fail on undefined references, digits in text, scope words")
    p.set_defaults(func=_paper_build)

    bib = subparsers.add_parser("bib", help="DOI-only bibliography")
    bsub = bib.add_subparsers(dest="bib_command", metavar="<action>")
    bsub.required = True
    p = bsub.add_parser("add", help="fetch a BibTeX entry by DOI")
    p.add_argument("doi")
    p.add_argument("--dry-run", action="store_true", help="print the entry; write nothing")
    p.set_defaults(func=_bib_add)
    p = bsub.add_parser("check", help="every entry has provenance and every record has an entry")
    p.set_defaults(func=_bib_check)

    venue = subparsers.add_parser("venue", help="venue constraints (RSC Advances)")
    sub = venue.add_subparsers(dest="venue_command", metavar="<action>")
    sub.required = True
    p = sub.add_parser("fetch", help="re-fetch sources and diff against the committed yaml")
    p.set_defaults(func=_venue_fetch)
    p = sub.add_parser("show", help="print the recorded constraints")
    p.add_argument("--file", choices=["manuscript", "artwork"], help="limit to one file")
    p.add_argument("--prefix", default="", help="only fields whose name starts with this")
    p.set_defaults(func=_venue_show)
    p = sub.add_parser("check", help="consistency checks on the committed yaml")
    p.set_defaults(func=_venue_check)
