"""nacre retrieve: search, doi, fulltext, gaps, stats."""
import json
import sys
from pathlib import Path

from nacre.retrieval import gaps as _gaps
from nacre.retrieval import record as R
from nacre.retrieval.arxiv import Arxiv
from nacre.retrieval.chemrxiv import ChemRxiv
from nacre.retrieval.config import Config
from nacre.retrieval.crossref import Crossref
from nacre.retrieval.http import Http, HttpError
from nacre.retrieval.lens import Lens
from nacre.retrieval.openaire import OpenAire
from nacre.retrieval.semanticscholar import SemanticScholar
from nacre.retrieval.store import Store, sha256_file
from nacre.retrieval.unpaywall import Unpaywall, best_pdf_url, parse_item
from nacre.retrieval.wayback import Wayback
from nacre.retrieval.zenodo import Zenodo

CLIENTS = {c.name: c for c in (Crossref, Unpaywall, SemanticScholar, Arxiv, ChemRxiv, OpenAire,
                               Zenodo, Wayback, Lens)}
NOT_SEARCHABLE = {"unpaywall", "wayback"}
SEARCHABLE = [n for n in CLIENTS if n not in NOT_SEARCHABLE]


def build(config=None):
    config = config or Config()
    ledger = _gaps.GapLedger(config.gaps_path)
    http = Http(config)
    return config, ledger, {n: c(http, config, ledger) for n, c in CLIENTS.items()}


def _line(rec):
    first = (rec["authors"][0]["family"] + " et al.") if rec.get("authors") else "-"
    return "%-15s %-5s %-28s %s | %s" % (rec["source"], rec.get("year") or "?",
                                         rec.get("doi") or rec.get("arxiv_id") or rec["source_id"],
                                         (rec.get("title") or "")[:70], first)


def cmd_search(args):
    config, ledger, clients = build()
    names = SEARCHABLE if args.source == "all" else [args.source]
    for n in names:
        if n not in CLIENTS or n in NOT_SEARCHABLE:
            print("unknown or non-searchable source %r; choose from: all, %s" % (n, ", ".join(SEARCHABLE)),
                  file=sys.stderr)
            return 2
    store = Store(config.records_path)
    for n in names:
        recs = clients[n].search(args.query, args.limit)
        for rec in recs:
            store.upsert(rec)
            print(_line(rec))
        print("-- %s: %d result(s)" % (n, len(recs)))
    store.save()
    return 0


def cmd_doi(args):
    doi = R.normalize_doi(args.doi)
    if not doi:
        print("not a DOI: %r" % args.doi, file=sys.stderr)
        return 2
    config, ledger, clients = build()
    store = Store(config.records_path)
    merged = None
    for n in ("crossref", "unpaywall", "semanticscholar"):
        rec = clients[n].lookup(doi)
        if rec:
            merged, _ = store.upsert(rec)
    store.save()
    if merged is None:
        print("no source returned %s (see lit/instrument_gaps.csv)" % doi, file=sys.stderr)
        return 1
    print(json.dumps(merged, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def fulltext_doi(config, ledger, clients, store, doi):
    unp = clients["unpaywall"]
    data, resp = unp.lookup_raw(doi)
    if data is None:
        return None, "Unpaywall has no record"
    rec = parse_item(data, unp.now(), resp.cache_key)
    store.upsert(rec)
    if not data.get("is_oa"):
        ledger.log("unpaywall", doi, "paywalled", "not open access; full text not fetched")
        return None, "not open access"
    url = best_pdf_url(data)
    if not url:
        ledger.log("unpaywall", doi, "not_indexed", "OA location has no direct PDF url")
        return None, "no direct PDF url"
    dest = Path(config.fulltext_dir) / (doi.replace("/", "_") + ".pdf")
    try:
        clients["unpaywall"].http.download("unpaywall", url, dest)
    except HttpError as exc:
        ledger.log("unpaywall", doi, exc.kind, exc.detail)
        return None, exc.detail
    if dest.read_bytes()[:5] != b"%PDF-":
        dest.unlink()
        ledger.log("unpaywall", doi, "parse_error", "downloaded file is not a PDF: %s" % url)
        return None, "not a PDF"
    return dest, rec["licence"]


def cmd_fulltext(args):
    config, ledger, clients = build()
    store = Store(config.records_path)
    doi, arx = R.normalize_doi(args.ident), R.normalize_arxiv(args.ident)
    if doi:
        path, licence = fulltext_doi(config, ledger, clients, store, doi)
        key = doi
    elif arx:
        rec = clients["arxiv"].lookup(arx)
        if rec:
            store.upsert(rec)
        path, licence = clients["arxiv"].fetch_fulltext(arx), None
        s2 = clients["semanticscholar"].lookup(arx)
        if s2:
            store.upsert(s2)
            licence = s2.get("licence")
        key = arx
    else:
        print("not a DOI or arXiv id: %r" % args.ident, file=sys.stderr)
        return 2
    if path is None:
        store.save()
        print("no full text cached for %s (%s); logged in lit/instrument_gaps.csv" % (key, licence))
        return 1
    digest = store.attach_fulltext(key, path, licence)
    store.save()
    print("cached %s\nsha256 %s\nlicence %s" % (path, digest, licence or "not stated"))
    return 0


def cmd_gaps(args):
    config = Config()
    rows = _gaps.GapLedger(config.gaps_path).read(args.since)
    for r in rows:
        print("%s  %-15s %-13s %s  [%s]" % (r["utc"], r["source"], r["failure_kind"],
                                            r["query_or_id"][:50], r["detail"][:80]))
    print("%d gap row(s)" % len(rows))
    return 0


def cmd_stats(args):
    config = Config()
    st = Store(config.records_path).stats()
    rows = _gaps.GapLedger(config.gaps_path).read()
    by = {}
    for r in rows:
        k = "%s/%s" % (r["source"], r["failure_kind"])
        by[k] = by.get(k, 0) + 1
    st["gaps"] = len(rows)
    st["gaps_by_source_kind"] = dict(sorted(by.items()))
    print(json.dumps(st, indent=2))
    return 0


def register(subparsers):
    p = subparsers.add_parser("retrieve", help="headless literature retrieval")
    sub = p.add_subparsers(dest="retrieve_command", metavar="<subcommand>", required=True)
    s = sub.add_parser("search", help="search one source or all")
    s.add_argument("--source", default="all", help="all or one of: " + ", ".join(SEARCHABLE))
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)
    d = sub.add_parser("doi", help="merge Crossref, Unpaywall and Semantic Scholar for a DOI")
    d.add_argument("doi")
    d.set_defaults(func=cmd_doi)
    f = sub.add_parser("fulltext", help="cache an open-access full text locally")
    f.add_argument("ident", help="DOI or arXiv id")
    f.set_defaults(func=cmd_fulltext)
    g = sub.add_parser("gaps", help="print the instrument-gap ledger")
    g.add_argument("--since", help="UTC timestamp, e.g. 2026-10-07T00:00:00Z")
    g.set_defaults(func=cmd_gaps)
    t = sub.add_parser("stats", help="corpus and gap statistics")
    t.set_defaults(func=cmd_stats)
