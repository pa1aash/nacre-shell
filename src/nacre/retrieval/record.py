"""The normalised record, identifier normalisation and title keys.

Committed fields never hold abstracts or full text; those stay in the local cache.
"""
import re
import unicodedata

FIELDS = ["source", "source_id", "doi", "arxiv_id", "title", "authors", "year", "venue",
          "type", "oa_status", "licence", "urls", "retrieved_utc", "raw_cache_key"]

_DOI_PREFIX = re.compile(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", re.I)
_DOI_BODY = re.compile(r"^10\.\d{4,9}/\S+$")
_ARXIV_NEW = re.compile(r"(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
_ARXIV_OLD = re.compile(r"([a-z\-]+(?:\.[A-Z]{2})?/\d{7})(?:v\d+)?", re.I)


def normalize_doi(value):
    if not value:
        return None
    s = _DOI_PREFIX.sub("", str(value).strip()).strip().rstrip(".,;").lower()
    return s if _DOI_BODY.match(s) else None


def normalize_arxiv(value):
    if not value:
        return None
    s = str(value).strip()
    s = re.sub(r"^(?:https?://arxiv\.org/(?:abs|pdf)/|arxiv:)", "", s, flags=re.I)
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    m = _ARXIV_NEW.fullmatch(s)
    if m:
        return m.group(1)
    m = _ARXIV_OLD.fullmatch(s)
    return m.group(1).lower() if m else None


def normalize_title(title):
    if not title:
        return ""
    s = unicodedata.normalize("NFKD", str(title))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())


def split_name(full):
    """'Given Middle Family' or 'Family, Given' -> (family, given)."""
    full = " ".join(str(full or "").split())
    if "," in full:
        fam, giv = full.split(",", 1)
        return fam.strip(), giv.strip()
    parts = full.rsplit(" ", 1)
    return (parts[-1], parts[0] if len(parts) == 2 else "")


def author(family, given="", orcid=None):
    orcid = re.sub(r"^https?://orcid\.org/", "", orcid or "") or None
    return {"family": family or "", "given": given or "", "orcid": orcid}


def make_record(source, source_id, retrieved_utc, raw_cache_key, **kw):
    rec = {f: None for f in FIELDS}
    rec.update(source=source, source_id=str(source_id) if source_id is not None else None,
               retrieved_utc=retrieved_utc, raw_cache_key=raw_cache_key)
    for k, v in kw.items():
        if k not in FIELDS:
            raise KeyError("field %r is not part of the normalised record" % k)
        rec[k] = v
    rec["doi"] = normalize_doi(rec["doi"])
    rec["arxiv_id"] = normalize_arxiv(rec["arxiv_id"])
    rec["authors"] = rec["authors"] or []
    rec["urls"] = sorted({u for u in (rec["urls"] or []) if u})
    if rec["year"] is not None:
        try:
            rec["year"] = int(rec["year"])
        except (TypeError, ValueError):
            rec["year"] = None
    return rec
