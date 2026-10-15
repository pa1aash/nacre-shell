"""Internet Archive availability API: snapshot lookup for cited URLs."""
from nacre.retrieval.base import Client

API = "https://archive.org/wayback/available"


def parse_snapshot(data, url, retrieved_utc, cache_key):
    snap = ((data or {}).get("archived_snapshots") or {}).get("closest") or {}
    if not snap.get("available"):
        return None
    return {"source": "wayback", "url": url, "snapshot_url": snap.get("url"),
            "timestamp": snap.get("timestamp"), "status": snap.get("status"),
            "retrieved_utc": retrieved_utc, "raw_cache_key": cache_key}


class Wayback(Client):
    name = "wayback"

    def snapshot(self, url):
        resp = self.fetch(url, API, params={"url": url})
        data = self.json_or_gap(url, resp)
        if data is None:
            return None
        snap = parse_snapshot(data, url, self.now(), resp.cache_key)
        if snap is None:
            self.gap(url, "not_indexed", "no archived snapshot")
        return snap
