"""arXiv export API (Atom) and local-cache-only full-text download."""
import xml.etree.ElementTree as ET
from pathlib import Path

from nacre.retrieval import record as R
from nacre.retrieval.base import Client
from nacre.retrieval.http import HttpError

API = "http://export.arxiv.org/api/query"
NS = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}


def parse_feed(xml_text, retrieved_utc, cache_key):
    """Normalise every entry of an Atom feed; the summary (abstract) is never read."""
    root = ET.fromstring(xml_text)
    out = []
    for e in root.findall("a:entry", NS):
        ident = (e.findtext("a:id", "", NS) or "").strip()
        if "/api/errors" in ident:
            continue
        arx = R.normalize_arxiv(ident)
        authors = []
        for a in e.findall("a:author", NS):
            fam, giv = R.split_name(a.findtext("a:name", "", NS))
            authors.append(R.author(fam, giv))
        published = e.findtext("a:published", "", NS) or ""
        cat = e.find("x:primary_category", NS)
        urls = [ident] + [l.get("href") for l in e.findall("a:link", NS) if l.get("href")]
        out.append(R.make_record(
            "arxiv", arx or ident, retrieved_utc, cache_key,
            doi=e.findtext("x:doi", None, NS), arxiv_id=arx,
            title=" ".join((e.findtext("a:title", "", NS) or "").split()) or None, authors=authors,
            year=published[:4] or None, venue="arXiv" + (":" + cat.get("term") if cat is not None else ""),
            type="preprint", urls=urls))
    return out


class Arxiv(Client):
    name = "arxiv"

    def _feed(self, query_or_id, params):
        resp = self.fetch(query_or_id, API, params=params)
        if resp is None:
            return []
        try:
            recs = parse_feed(resp.text, self.now(), resp.cache_key)
        except ET.ParseError as exc:
            self.gap(query_or_id, "parse_error", "Atom: %s" % exc)
            return []
        if not recs:
            self.empty_gap(query_or_id)
        return recs

    def search(self, query, limit=10):
        return self._feed(query, {"search_query": "all:" + query, "max_results": limit})

    def lookup(self, arxiv_id):
        arx = R.normalize_arxiv(arxiv_id)
        if not arx:
            return None
        recs = self._feed(arx, {"id_list": arx, "max_results": 1})
        return recs[0] if recs else None

    def fetch_fulltext(self, arxiv_id):
        """Download the PDF into the local cache only. Returns the path or None."""
        arx = R.normalize_arxiv(arxiv_id)
        if not arx:
            return None
        dest = Path(self.config.fulltext_dir) / ("arxiv_%s.pdf" % arx.replace("/", "_"))
        try:
            self.http.download(self.name, "https://arxiv.org/pdf/" + arx, dest)
        except HttpError as exc:
            self.gap(arx, exc.kind, exc.detail)
            return None
        return dest
