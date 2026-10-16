"""uv run python -m nacre.lit <command> ...

Thread retrieval (every call is logged under lit/corpus/<thread>/):
  search   <thread> --route R --query Q [--limit N]
  meta     <thread> <doi>                 Crossref metadata plus Unpaywall OA locations
  abstract <thread> <doi>                 abstract text, cached under .local/lit/<thread>/abstracts/
  fulltext <thread> <doi|arXiv id>        open full text via Unpaywall, OpenAlex, Europe PMC or arXiv
  url      <thread> <url> [--doi D]       a direct PDF location found by search
  related  <thread> <doi> [--refs]        works citing (default) or cited by a DOI (OpenAlex)
  grep     <thread> <regex> [--doi D]     search extracted texts; prints file, pdf page/label, line
Evidence table:
  validate <csv>...                       validate rows.csv or the merged table
  merge                                   merge thread rows, write evidence_table.csv and coverage.yaml
  trace    <csv>...                       local audit: is each value printed in the cached text of its DOI?
"""
import argparse
import json
import sys

from nacre import _util
from nacre.lit import evidence as E
from nacre.lit import merge as M
from nacre.lit import trace as T
from nacre.lit.thread import SEARCH_ROUTES, THREADS, ThreadSession


def _line(r):
    first = (r["authors"][0]["family"] + " et al.") if r.get("authors") else "-"
    return "%-5s %-34s %s | %s | %s" % (r.get("year") or "?", r.get("doi") or r.get("arxiv_id") or "-",
                                        (r.get("title") or "")[:90], first, r.get("venue") or "")


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m nacre.lit", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("thread", choices=THREADS)
    s.add_argument("--route", required=True, choices=SEARCH_ROUTES)
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=10)
    for name in ("meta", "abstract", "fulltext"):
        x = sub.add_parser(name)
        x.add_argument("thread", choices=THREADS)
        x.add_argument("ident")
    u = sub.add_parser("url")
    u.add_argument("thread", choices=THREADS)
    u.add_argument("url")
    u.add_argument("--doi")
    r = sub.add_parser("related")
    r.add_argument("thread", choices=THREADS)
    r.add_argument("ident")
    r.add_argument("--refs", action="store_true")
    r.add_argument("--limit", type=int, default=25)
    g = sub.add_parser("grep")
    g.add_argument("thread", choices=THREADS)
    g.add_argument("pattern")
    g.add_argument("--doi")
    g.add_argument("--context", type=int, default=1)
    v = sub.add_parser("validate")
    v.add_argument("paths", nargs="+")
    sub.add_parser("merge")
    t = sub.add_parser("trace")
    t.add_argument("paths", nargs="+")
    a = p.parse_args(argv)

    if a.cmd == "validate":
        root, rc = _util.repo_root(), 0
        for path in a.paths:
            errs = E.validate_file(path, root)
            print("%s: %s" % (path, "OK" if not errs else "%d problem(s)" % len(errs)))
            for e in errs:
                print("  " + e)
            rc |= bool(errs)
        return rc
    if a.cmd == "merge":
        return M.run(_util.repo_root())
    if a.cmd == "trace":
        rc = 0
        for path in a.paths:
            counts = {}
            for rid, status, detail in T.audit(_util.repo_root(), E.read_csv(path)[1]):
                counts[status] = counts.get(status, 0) + 1
                if status in ("untraced", "derived"):
                    print("%s %-9s %s" % (rid, status, detail))
            print("%s: %s" % (path, counts))
            rc |= bool(counts.get("untraced"))
        return rc

    ts = ThreadSession(a.thread)
    if a.cmd == "search":
        recs = ts.search(a.route, a.query, a.limit)
        for rec in recs:
            print(_line(rec))
        print("-- %s: %d result(s)" % (a.route, len(recs)))
    elif a.cmd == "meta":
        print(json.dumps(ts.metadata(a.ident), indent=2, ensure_ascii=False))
    elif a.cmd == "abstract":
        path, text = ts.abstract(a.ident)
        if not path:
            print("no abstract found for %s (logged)" % a.ident)
            return 1
        print("cached %s\n\n%s" % (path, text))
    elif a.cmd == "fulltext":
        txt, how = ts.fulltext(a.ident)
        if not txt:
            print("no full text for %s: %s (logged)" % (a.ident, how))
            return 1
        print("cached %s via %s" % (txt, how))
    elif a.cmd == "url":
        txt = ts.url(a.url, a.doi)
        if not txt:
            print("not retrieved (logged)")
            return 1
        print("cached %s" % txt)
    elif a.cmd == "related":
        recs = ts.related(a.ident, "refs" if a.refs else "cites", a.limit)
        for rec in recs:
            print(_line(rec))
        print("-- %d result(s)" % len(recs))
    elif a.cmd == "grep":
        n = 0
        for f, page, no, text in ts.grep(a.pattern, a.doi, a.context):
            print("%s  p%s  L%d: %s" % (f, page, no, text[:400]))
            n += 1
        print("-- %d match(es)" % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
