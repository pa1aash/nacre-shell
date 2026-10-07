"""Zenodo records search."""
from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://zenodo.org/api/records"


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one Zenodo record. The description field is dropped."""
    md = item.get("metadata") or {}
    authors = []
    for c in md.get("creators") or []:
        fam, giv = R.split_name(c.get("name"))
        authors.append(R.author(fam, giv, c.get("orcid")))
    lic = md.get("license")
    lic = lic.get("id") if isinstance(lic, dict) else lic
    rtype = md.get("resource_type") or {}
    return R.make_record(
        "zenodo", item.get("id"), retrieved_utc, cache_key,
        doi=item.get("doi") or md.get("doi"), title=md.get("title"), authors=authors,
        year=(md.get("publication_date") or "")[:4] or None, venue="Zenodo",
        type=rtype.get("type") or rtype.get("title"), oa_status=md.get("access_right"),
        licence=lic, urls=[(item.get("links") or {}).get("self_html")])


class Zenodo(Client):
    name = "zenodo"

    def search(self, query, limit=10):
        params = {"q": query, "size": limit}
        token = self.config.key("ZENODO_TOKEN")
        if token:
            params["access_token"] = token
        resp = self.fetch(query, API, params=params)
        data = self.json_or_gap(query, resp)
        if data is None:
            return []
        hits = (data.get("hits") or {}).get("hits") or []
        if not hits:
            self.empty_gap(query)
        return [parse_item(h, self.now(), resp.cache_key) for h in hits]
