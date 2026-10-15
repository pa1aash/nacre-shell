"""Unpaywall: OA status, licence and best OA location by DOI."""
import urllib.parse

from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://api.unpaywall.org/v2/"


def parse_item(item, retrieved_utc, cache_key):
    best = item.get("best_oa_location") or {}
    urls = [best.get("url_for_pdf"), best.get("url"), item.get("doi_url")]
    authors = [R.author(a.get("family", ""), a.get("given", ""), a.get("ORCID"))
               for a in item.get("z_authors") or []]
    return R.make_record(
        "unpaywall", item.get("doi"), retrieved_utc, cache_key,
        doi=item.get("doi"), title=item.get("title"), authors=authors, year=item.get("year"),
        venue=item.get("journal_name"), type=item.get("genre"),
        oa_status=item.get("oa_status") if item.get("is_oa") else "closed",
        licence=best.get("license"), urls=urls)


def best_pdf_url(item):
    best = (item or {}).get("best_oa_location") or {}
    return best.get("url_for_pdf")


class Unpaywall(Client):
    name = "unpaywall"

    def lookup_raw(self, doi):
        doi = R.normalize_doi(doi)
        if not doi:
            return None, None
        resp = self.fetch(doi, API + urllib.parse.quote(doi, safe="/"), params={"email": self.config.mailto})
        return self.json_or_gap(doi, resp), resp

    def lookup(self, doi):
        data, resp = self.lookup_raw(doi)
        return parse_item(data, self.now(), resp.cache_key) if data else None
