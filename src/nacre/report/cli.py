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


def register(subparsers):
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
