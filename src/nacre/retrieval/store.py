"""Committed corpus store: metadata only, deduped, with merged provenance."""
import hashlib
import json
import os
from pathlib import Path

from nacre.retrieval import record as R

COMMITTED = R.FIELDS + ["seen_in", "fulltext_sha256"]
# Lower rank wins when two sources disagree on a field.
RANK = ["crossref", "unpaywall", "semanticscholar", "openaire", "arxiv", "chemrxiv", "zenodo", "lens"]
UNPAYWALL_FIELDS = ("oa_status", "licence")


def rank(source):
    return RANK.index(source) if source in RANK else len(RANK)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _empty(v):
    return v is None or v == "" or v == []


def _seen(rec):
    return {k: rec.get(k) for k in ("source", "source_id", "retrieved_utc", "raw_cache_key")}


def _clean(rec):
    """Keep only committed fields; abstracts, text and anything else never reach disk."""
    return {k: rec.get(k) for k in COMMITTED}


def _authors_score(a):
    return (len(a), sum(1 for x in a if x.get("orcid")), sum(1 for x in a if x.get("given")))


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.records = []
        self.load()

    def load(self):
        self.records = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    self.records.append(_clean(json.loads(line)))

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w") as fh:
            for rec in self.records:
                fh.write(json.dumps(_clean(rec), sort_keys=True, ensure_ascii=False) + "\n")
        os.replace(tmp, self.path)

    def find(self, rec):
        """Dedupe precedence: exact DOI, then arXiv id, then normalised title plus year."""
        doi, arx = rec.get("doi"), rec.get("arxiv_id")
        if doi:
            for e in self.records:
                if e.get("doi") == doi:
                    return e, "doi"
        if arx:
            for e in self.records:
                if e.get("arxiv_id") == arx:
                    return e, "arxiv_id"
        title, year = R.normalize_title(rec.get("title")), rec.get("year")
        if title and year:
            for e in self.records:
                if R.normalize_title(e.get("title")) != title or e.get("year") != year:
                    continue
                if doi and e.get("doi") and doi != e["doi"]:
                    continue
                if arx and e.get("arxiv_id") and arx != e["arxiv_id"]:
                    continue
                return e, "title_year"
        return None, None

    def upsert(self, rec):
        """Insert or merge one normalised record. Returns (stored_record, how)."""
        rec = dict(rec)
        existing, how = self.find(rec)
        if existing is None:
            new = _clean(rec)
            new["seen_in"] = [_seen(rec)]
            new["fulltext_sha256"] = rec.get("fulltext_sha256")
            self.records.append(new)
            return new, "new"
        self._merge(existing, rec)
        return existing, how

    def _merge(self, e, rec):
        new_wins = rank(rec.get("source")) < rank(e.get("source"))
        for k in R.FIELDS:
            if k in ("source", "source_id", "retrieved_utc", "raw_cache_key", "authors", "urls"):
                continue
            v = rec.get(k)
            if _empty(v):
                continue
            if k in UNPAYWALL_FIELDS:
                if rec.get("source") == "unpaywall" or _empty(e.get(k)):
                    e[k] = v
            elif _empty(e.get(k)) or new_wins:
                e[k] = v
        if _authors_score(rec.get("authors") or []) > _authors_score(e.get("authors") or []):
            e["authors"] = rec["authors"]
        e["urls"] = sorted(set(e.get("urls") or []) | set(rec.get("urls") or []))
        seen = e.setdefault("seen_in", [])
        entry = _seen(rec)
        if all((s["source"], s["source_id"]) != (entry["source"], entry["source_id"]) for s in seen):
            seen.append(entry)
        else:
            for s in seen:
                if (s["source"], s["source_id"]) == (entry["source"], entry["source_id"]):
                    s.update(entry)
        if new_wins:
            for k in ("source", "source_id", "retrieved_utc", "raw_cache_key"):
                e[k] = rec.get(k)
        if rec.get("fulltext_sha256"):
            e["fulltext_sha256"] = rec["fulltext_sha256"]

    def lookup(self, ident):
        doi, arx = R.normalize_doi(ident), R.normalize_arxiv(ident)
        for e in self.records:
            if (doi and e.get("doi") == doi) or (arx and e.get("arxiv_id") == arx):
                return e
        return None

    def attach_fulltext(self, ident, path, licence=None):
        """Record the content sha256 of a locally cached full text. Returns the digest."""
        e = self.lookup(ident)
        if e is None:
            raise KeyError("record %s is not in the store" % ident)
        e["fulltext_sha256"] = sha256_file(path)
        if licence:
            e["licence"] = licence
        return e["fulltext_sha256"]

    def stats(self):
        by_source = {}
        for e in self.records:
            for s in e.get("seen_in") or []:
                by_source[s["source"]] = by_source.get(s["source"], 0) + 1
        return {
            "records": len(self.records),
            "with_doi": sum(1 for e in self.records if e.get("doi")),
            "with_arxiv_id": sum(1 for e in self.records if e.get("arxiv_id")),
            "with_fulltext_sha256": sum(1 for e in self.records if e.get("fulltext_sha256")),
            "multi_source": sum(1 for e in self.records if len(e.get("seen_in") or []) > 1),
            "seen_in_by_source": dict(sorted(by_source.items())),
        }
