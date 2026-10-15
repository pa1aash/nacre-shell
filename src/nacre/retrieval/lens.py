"""Lens.org patent search. Without LENS_TOKEN every query writes a gap row and returns empty."""
from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://api.lens.org/patent/search"


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one patent. Abstract and claims are never requested or read."""
    biblio = item.get("biblio") or {}
    titles = biblio.get("invention_title") or []
    en = [t for t in titles if t.get("lang") == "en"] or titles
    inventors = ((biblio.get("parties") or {}).get("inventors")) or []
    authors = []
    for inv in inventors:
        fam, giv = R.split_name(((inv.get("extracted_name") or {}).get("value")))
        authors.append(R.author(fam, giv))
    number = "-".join(str(item.get(k)) for k in ("jurisdiction", "doc_number", "kind") if item.get(k))
    return R.make_record(
        "lens", item.get("lens_id"), retrieved_utc, cache_key,
        title=en[0].get("text") if en else None, authors=authors,
        year=(item.get("date_published") or "")[:4] or None, venue=number or None, type="patent",
        urls=["https://www.lens.org/lens/patent/%s" % item["lens_id"]] if item.get("lens_id") else [])


class Lens(Client):
    name = "lens"

    def search(self, query, limit=10):
        token = self.config.key("LENS_TOKEN")
        if not token:
            self.gap(query, "no_token", "LENS_TOKEN is not set; patent search skipped")
            return []
        body = {"query": {"match": {"title": query}}, "size": limit,
                "include": ["lens_id", "jurisdiction", "doc_number", "kind", "date_published", "biblio"]}
        resp = self.fetch(query, API, method="POST", json_body=body,
                          headers={"Authorization": "Bearer " + token})
        data = self.json_or_gap(query, resp)
        if data is None:
            return []
        rows = data.get("data") or []
        if not rows:
            self.empty_gap(query)
        return [parse_item(r, self.now(), resp.cache_key) for r in rows]
