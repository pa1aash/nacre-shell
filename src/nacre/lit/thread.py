"""Thread-scoped retrieval for the evidence threads (T-A to T-M).

A thread session wraps nacre.retrieval with paths of its own, so parallel threads never share a
writable file:

    lit/corpus/<thread>/queries.jsonl         one line per search (route, query, date, hits)
    lit/corpus/<thread>/sources.jsonl         one line per source read (doi, access route, sha256)
    lit/corpus/<thread>/instrument_gaps.csv   failures, in the nacre.retrieval gap format
    .local/lit/<thread>/                      full texts, extracted text, abstracts, metadata, cache

Everything under .local/ is excluded from git. Extracted PDF text carries one marker line per page,
"=== pdf page N (label L) ===", so that locators can name a page.
"""
import datetime as dt
import html
import json
import re
from pathlib import Path

from nacre import _util
from nacre.retrieval import record as R
from nacre.retrieval.arxiv import Arxiv
from nacre.retrieval.config import Config
from nacre.retrieval.crossref import Crossref
from nacre.retrieval.gaps import GapLedger
from nacre.retrieval.http import Http, HttpError
from nacre.retrieval.openaire import OpenAire
from nacre.retrieval.semanticscholar import SemanticScholar
from nacre.retrieval.store import Store, sha256_file
from nacre.retrieval.unpaywall import Unpaywall
from nacre.retrieval.zenodo import Zenodo
from nacre.lit import evidence as E
from nacre.lit import routes

THREADS = E.THREADS
SEARCH_ROUTES = ("crossref", "openalex", "europepmc", "pubmed", "semanticscholar", "arxiv", "openaire", "zenodo")
PAGE_MARK = "=== pdf page %d (label %s) ==="
WAYBACK_RAW = "https://web.archive.org/web/2026id_/"
PDF_HEADERS ={"Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5"}


def utcnow():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(ident):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", ident)[:150]


def pdf_to_text(pdf_path, txt_path):
    """Extract text with one marker line per page. Returns the page count."""
    import pymupdf

    out = []
    with pymupdf.open(pdf_path) as doc:
        for i, page in enumerate(doc, 1):
            label = page.get_label() or "-"
            out.append(PAGE_MARK % (i, label))
            out.append(page.get_text("text"))
        n = doc.page_count
    Path(txt_path).write_text("\n".join(out), encoding="utf-8")
    return n


_BLOCK = re.compile(r"</?(sec|title|p|table-wrap|table|tr|caption|label|fig|disp-formula|list-item|ref)\b[^>]*>", re.I)


def jats_to_text(xml, txt_path):
    """Europe PMC full-text XML to plain text with block-level line breaks (no page numbers)."""
    text = _BLOCK.sub("\n", xml)
    text = re.sub(r"</?(td|th)\b[^>]*>", " | ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = [" ".join(html.unescape(l).split()) for l in text.splitlines()]
    Path(txt_path).write_text("\n".join(l for l in lines if l), encoding="utf-8")


class ThreadSession:
    def __init__(self, thread, root=None, http=None, config=None):
        if thread not in THREADS:
            raise ValueError("unknown thread %r; choose from %s" % (thread, ", ".join(THREADS)))
        self.thread = thread
        self.root = Path(root) if root else _util.repo_root()
        self.dir = self.root / "lit" / "corpus" / thread
        self.local = self.root / ".local" / "lit" / thread
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.local / "abstracts").mkdir(parents=True, exist_ok=True)
        cfg = config or Config(self.root)
        cfg.records_path = self.local / "records.jsonl"
        cfg.cache_dir = self.root / ".local" / "lit" / "cache"
        cfg.fulltext_dir = self.local
        cfg.gaps_path = self.dir / "instrument_gaps.csv"
        for name, settings in routes.SOURCE_DEFAULTS.items():
            cfg.sources.setdefault(name, settings)
        self.config = cfg
        self.ledger = GapLedger(cfg.gaps_path)
        self.http = http or Http(cfg)
        h, c, l = self.http, cfg, self.ledger
        self.openalex = routes.OpenAlex(h, c, l)
        self.europepmc = routes.EuropePMC(h, c, l)
        self.clients = {
            "crossref": Crossref(h, c, l), "openalex": self.openalex, "europepmc": self.europepmc,
            "pubmed": routes.PubMed(h, c, l), "semanticscholar": SemanticScholar(h, c, l),
            "arxiv": Arxiv(h, c, l), "openaire": OpenAire(h, c, l), "zenodo": Zenodo(h, c, l),
        }
        self.unpaywall = Unpaywall(h, c, l)
        self.abstracts = routes.Abstracts(h, c, l, self.openalex, self.europepmc)
        self.store = Store(cfg.records_path)

    # ---- logs -------------------------------------------------------------------------------
    def _append(self, name, obj):
        with (self.dir / name).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")

    def log_query(self, route, query, hits, dois):
        self._append("queries.jsonl", {"route": route, "query": query, "date": utcnow(), "hits": hits,
                                       "dois": [d for d in dois if d][:25]})

    def log_source(self, doi, access_route, path=None, url=None, pages=None, licence=None, note=None):
        rel = str(Path(path).resolve().relative_to(self.root.resolve())) if path else None
        self._append("sources.jsonl", {
            "doi": doi, "access_route": access_route, "url": url, "local_path": rel,
            "sha256": sha256_file(path) if path else None, "pages": pages, "licence": licence,
            "retrieved_at": utcnow(), "note": note})

    # ---- search and metadata ----------------------------------------------------------------
    def search(self, route, query, limit=10):
        if route not in self.clients:
            raise ValueError("unknown route %r; choose from %s" % (route, ", ".join(SEARCH_ROUTES)))
        recs = self.clients[route].search(query, limit)
        for r in recs:
            self.store.upsert(r)
        self.store.save()
        self.log_query(route, query, len(recs), [r.get("doi") for r in recs])
        return recs

    def metadata(self, doi):
        doi = R.normalize_doi(doi)
        rec = self.clients["crossref"].lookup(doi)
        upw, _ = self.unpaywall.lookup_raw(doi)
        if rec:
            self.store.upsert(rec)
            self.store.save()
        locs = [{"pdf": l.get("url_for_pdf"), "url": l.get("url"), "version": l.get("version"),
                 "licence": l.get("license"), "host": l.get("host_type")} for l in (upw or {}).get("oa_locations") or []]
        return {"doi": doi, "title": (rec or {}).get("title"), "year": (rec or {}).get("year"),
                "venue": (rec or {}).get("venue"), "authors": [a["family"] for a in (rec or {}).get("authors") or []][:8],
                "is_oa": (upw or {}).get("is_oa"), "oa_status": (upw or {}).get("oa_status"), "oa_locations": locs}

    def related(self, doi, direction="cites", limit=25):
        """OpenAlex: works citing `doi` (cites) or works it references (refs)."""
        work = self.openalex.work(doi) or {}
        wid = (work.get("id") or "").rsplit("/", 1)[-1]
        if not wid:
            return []
        if direction == "cites":
            flt = "cites:%s" % wid
        else:
            ids = [w.rsplit("/", 1)[-1] for w in work.get("referenced_works") or []][:50]
            if not ids:
                return []
            flt = "openalex_id:%s" % "|".join(ids)
        resp = self.openalex.fetch(doi, routes.OPENALEX, params={"filter": flt, "per-page": limit,
                                                                  "sort": "cited_by_count:desc",
                                                                  "mailto": self.config.mailto})
        items = (self.openalex.json_or_gap(doi, resp) or {}).get("results") or []
        recs = [routes.openalex_record(i, utcnow(), resp.cache_key) for i in items]
        self.log_query("openalex-" + direction, doi, len(recs), [r.get("doi") for r in recs])
        return recs

    # ---- abstracts --------------------------------------------------------------------------
    def abstract(self, doi):
        doi = R.normalize_doi(doi)
        route, text = self.abstracts.get(doi)
        if not route:
            return None, ""
        path = self.local / "abstracts" / (slug(doi) + ".txt")
        path.write_text(text, encoding="utf-8")
        self.log_source(doi, "abstract:" + route, path=path)
        return path, text

    # ---- full text --------------------------------------------------------------------------
    def _candidates(self, doi):
        """Ordered candidate full-text locations: (route, kind, url)."""
        out = []
        upw, _ = self.unpaywall.lookup_raw(doi)
        locs = [(upw or {}).get("best_oa_location") or {}] + list((upw or {}).get("oa_locations") or [])
        for loc in locs:
            if loc.get("url_for_pdf"):
                out.append(("unpaywall", "pdf", loc["url_for_pdf"]))
        work = self.openalex.work(doi) or {}
        for u in routes.openalex_pdf_urls(work):
            out.append(("openalex", "pdf", u))
        epmc = self.europepmc.by_doi(doi) or {}
        pmcid = epmc.get("pmcid")
        if pmcid:
            out.append(("europepmc", "pdf", "https://europepmc.org/articles/%s?pdf=render" % pmcid))
            out.append(("europepmc", "xml", pmcid))
        seen, uniq = set(), []
        for c in out:
            if c[2] not in seen:
                seen.add(c[2])
                uniq.append(c)
        return uniq, upw

    def _try_pdf(self, ident, route, url):
        dest = self.local / (slug(ident) + ".pdf")
        try:
            self.http.download("publisher", url, dest, headers=PDF_HEADERS)
        except HttpError as exc:
            self.ledger.log(route, ident, exc.kind, exc.detail)
            return None
        if dest.read_bytes()[:5] != b"%PDF-":
            dest.unlink()
            self.ledger.log(route, ident, "parse_error", "not a PDF: %s" % url)
            return None
        return dest

    def fulltext(self, ident):
        """Cache a full text locally. Returns (txt_path, route) or (None, reason)."""
        doi, arx = R.normalize_doi(ident), R.normalize_arxiv(ident)
        if not doi and arx:
            pdf = self._try_pdf(arx, "arxiv", "https://arxiv.org/pdf/%s" % arx)
            if not pdf:
                return None, "arXiv PDF not retrieved"
            txt = pdf.with_suffix(".txt")
            pages = pdf_to_text(pdf, txt)
            self.log_source("10.48550/arxiv." + arx, "fulltext:arxiv", path=pdf, url="https://arxiv.org/abs/" + arx, pages=pages)
            return txt, "arxiv"
        if not doi:
            raise ValueError("not a DOI or arXiv id: %r" % ident)
        cands, upw = self._candidates(doi)
        licence = ((upw or {}).get("best_oa_location") or {}).get("license")
        pdfs = [(route, url) for route, kind, url in cands if kind == "pdf"]
        # Direct first, then the archived snapshot of the same open-access location (publisher
        # bot challenges block direct requests to some open copies).
        attempts = pdfs + [(route + "+wayback", WAYBACK_RAW + url) for route, url in pdfs]
        for route, url in attempts:
            pdf = self._try_pdf(doi, route, url)
            if pdf:
                txt = pdf.with_suffix(".txt")
                pages = pdf_to_text(pdf, txt)
                self.log_source(doi, "fulltext:" + route, path=pdf, url=url, pages=pages, licence=licence)
                return txt, route
        for route, kind, url in cands:
            if kind == "xml":
                xml = self.europepmc.fulltext_xml(url)
                if xml and "<article" in xml:
                    xml_path = self.local / (slug(doi) + ".xml")
                    xml_path.write_text(xml, encoding="utf-8")
                    txt = xml_path.with_suffix(".txt")
                    jats_to_text(xml, txt)
                    self.log_source(doi, "fulltext:europepmc-xml", path=xml_path, url=url, licence=licence,
                                    note="no page numbers; locate by section, table or figure")
                    return txt, "europepmc-xml"
        if upw is not None and not upw.get("is_oa"):
            self.ledger.log("unpaywall", doi, "paywalled", "no open copy on unpaywall, openalex or europepmc")
            return None, "paywalled: no open copy found"
        self.ledger.log("fulltext", doi, "not_indexed", "%d candidate location(s), none retrieved" % len(cands))
        return None, "no retrievable copy (%d candidate locations failed)" % len(cands)

    def url(self, url, doi=None):
        """Fetch a direct URL (PDF) found by search, e.g. a repository copy."""
        ident = doi or url
        for route, u in (("direct", url), ("direct+wayback", WAYBACK_RAW + url)):
            pdf = self._try_pdf(ident, route, u)
            if pdf:
                txt = pdf.with_suffix(".txt")
                pages = pdf_to_text(pdf, txt)
                self.log_source(R.normalize_doi(doi) if doi else None, "fulltext:" + route, path=pdf, url=u,
                                pages=pages)
                return txt
        return None

    # ---- reading ----------------------------------------------------------------------------
    def grep(self, pattern, ident=None, context=1):
        """Regex search over the thread's extracted texts; yields (file, page, line_no, text)."""
        rx = re.compile(pattern, re.I)
        files = sorted(self.local.glob("*.txt"))
        if ident:
            files = [f for f in files if f.stem == slug(R.normalize_doi(ident) or ident)]
        for f in files:
            page = "-"
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, line in enumerate(lines):
                m = re.match(r"^=== pdf page (\d+) \(label (.*)\) ===$", line)
                if m:
                    page = "%s/%s" % (m.group(1), m.group(2))
                    continue
                if rx.search(line):
                    lo, hi = max(0, i - context), min(len(lines), i + context + 1)
                    yield f.name, page, i + 1, " / ".join(l.strip() for l in lines[lo:hi])
