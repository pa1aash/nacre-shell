import json

from nacre.lit import evidence as E
from nacre.retrieval.http import HttpError, Response


def good_row(**kw):
    r = {
        "row_id": "TC-001", "thread": "T-C", "doi": "10.1021/example.123", "locator": "p. 4, Table 2",
        "quantity": "ksp_calcite", "symbol": "log10 Ksp", "value": "-8.48", "unit": "1",
        "range_or_uncertainty": "±0.02", "conditions": "T=298.15 K; pH=n.s.; I->0; water; calcite",
        "method": "experiment: solubility titration", "grade": "A", "extraction_route": "full text",
        "retrieved_at": "2026-10-16T09:00:00Z", "contrary": "n", "retro_candidate": "n",
        "notes": "infinite-dilution value from the regression",
    }
    r.update(kw)
    return r


class FakeHttp:
    """Routes request URLs (substring match) to JSON payloads; downloads write scripted bytes."""

    def __init__(self, routes=None, downloads=None):
        self.routes, self.downloads, self.calls = routes or {}, downloads or {}, []

    def request(self, source, method, url, params=None, headers=None, json_body=None, use_cache=True):
        self.calls.append((source, url, params))
        for key, payload in self.routes.items():
            if key in url:
                if isinstance(payload, HttpError):
                    raise payload
                text = payload if isinstance(payload, str) else json.dumps(payload)
                return Response(200, text, "k" * 64)
        raise HttpError("not_indexed", "HTTP 404 %s" % url, 404)

    def get(self, source, url, **kw):
        return self.request(source, "GET", url, **kw)

    def download(self, source, url, dest, headers=None):
        self.calls.append((source, url, None))
        for key, blob in self.downloads.items():
            if key in url:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(blob)
                return len(blob)
        raise HttpError("http_error", "HTTP 403 %s" % url, 403)


def tiny_pdf(pages):
    import pymupdf

    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    blob = doc.tobytes()
    doc.close()
    return blob


__all__ = ["E", "good_row", "FakeHttp", "tiny_pdf"]
