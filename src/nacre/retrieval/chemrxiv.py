"""ChemRxiv public API: search and item lookup."""
import urllib.parse

from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://chemrxiv.org/engage/chemrxiv/public-api/v1"


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one ChemRxiv item. The abstract field is dropped."""
    authors = [R.author(a.get("lastName", ""), a.get("firstName", ""), a.get("orcid"))
               for a in item.get("authors") or []]
    lic = item.get("license") or {}
    asset = ((item.get("asset") or {}).get("original") or {}).get("url")
    date = item.get("publishedDate") or item.get("statusDate") or ""
    return R.make_record(
        "chemrxiv", item.get("id"), retrieved_utc, cache_key,
        doi=item.get("doi"), title=item.get("title"), authors=authors, year=date[:4] or None,
        venue="ChemRxiv", type="preprint", oa_status="open" if asset else None,
        licence=lic.get("name") or lic.get("url"), urls=[asset])


class ChemRxiv(Client):
    name = "chemrxiv"

    def search(self, query, limit=10):
        resp = self.fetch(query, API + "/items", params={"term": query, "limit": limit})
        data = self.json_or_gap(query, resp)
        if data is None:
            return []
        items = [h.get("item") for h in data.get("itemHits") or [] if h.get("item")]
        if not items:
            self.empty_gap(query)
        return [parse_item(i, self.now(), resp.cache_key) for i in items]

    def lookup(self, item_id):
        resp = self.fetch(item_id, API + "/items/" + urllib.parse.quote(str(item_id), safe=""))
        data = self.json_or_gap(item_id, resp)
        return parse_item(data, self.now(), resp.cache_key) if data and data.get("id") else None
