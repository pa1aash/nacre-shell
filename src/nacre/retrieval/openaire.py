"""OpenAIRE Graph: publications and datasets."""
from nacre.retrieval import record as R
from nacre.retrieval.base import Client

API = "https://api.openaire.eu/graph/v1/researchProducts"


def _pid(item, scheme):
    for p in item.get("pids") or []:
        if p.get("scheme") == scheme and p.get("value"):
            return p["value"]
    return None


def parse_item(item, retrieved_utc, cache_key):
    """Normalise one research product. Descriptions (abstracts) are dropped."""
    authors = []
    for a in sorted(item.get("authors") or [], key=lambda x: x.get("rank") or 0):
        fam, giv = a.get("surname"), a.get("name")
        if not fam:
            full = " ".join((a.get("fullName") or "").split())
            if full.isupper() and "," not in full:
                # all-caps names (patent feeds) are written "FAMILY GIVEN"
                head, _, tail = full.rpartition(" ")
                fam, giv = (head or tail).title(), (tail if head else "").title()
            else:
                fam, giv = R.split_name(full)
        orcid = ((a.get("pid") or {}).get("id") or {}).get("value")
        authors.append(R.author(fam, giv or "", orcid))
    inst = (item.get("instances") or [{}])[0]
    urls = list(inst.get("urls") or [])
    right = (item.get("bestAccessRight") or {}).get("label")
    return R.make_record(
        "openaire", item.get("id"), retrieved_utc, cache_key,
        doi=_pid(item, "doi"), arxiv_id=_pid(item, "arXiv"), title=item.get("mainTitle"),
        authors=authors, year=(item.get("publicationDate") or "")[:4] or None,
        venue=(item.get("container") or {}).get("name") or item.get("publisher"),
        type=item.get("type"), oa_status=right, licence=inst.get("license"), urls=urls)


class OpenAire(Client):
    name = "openaire"

    def search(self, query, limit=10):
        out = []
        for kind in ("publication", "dataset"):
            resp = self.fetch(query, API, params={"search": query, "type": kind, "pageSize": limit})
            data = self.json_or_gap(query, resp)
            if data is None:
                continue
            rows = data.get("results") or []
            if not rows:
                self.gap(query, "not_indexed", "no %s results" % kind)
            out += [parse_item(r, self.now(), resp.cache_key) for r in rows]
        return out

    def lookup(self, doi):
        doi = R.normalize_doi(doi)
        if not doi:
            return None
        resp = self.fetch(doi, API, params={"pid": doi, "pageSize": 1})
        data = self.json_or_gap(doi, resp)
        rows = (data or {}).get("results") or []
        if data is not None and not rows:
            self.empty_gap(doi)
        return parse_item(rows[0], self.now(), resp.cache_key) if rows else None
