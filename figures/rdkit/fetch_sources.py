"""Fetch the SMILES of the structures that have no shared SMILES in the repository.

The structure set (figures/rdkit/structures.yaml) takes every SMILES from shared code when it
exists: the oligomer from nacre.structures.oligomer, the catecholates and acetate from
nacre.anchor.builders.LIGANDS. Catechol, 1,2-benzoquinone and the glucosamine residue of
chitosan are defined nowhere in the repository, so their records are fetched from PubChem
(PUG REST, headless) and stored byte for byte in figures/rdkit/sources/. Each fetch appends
one row to figures/style/fetch_log.jsonl with its sha256.

Run: uv run python figures/rdkit/fetch_sources.py
"""
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCES = HERE / "sources"
FETCH_LOG = ROOT / "figures" / "style" / "fetch_log.jsonl"
PUG = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/%d/property/SMILES,InChIKey,IUPACName,Title/JSON"

# fetch id -> (PubChem CID, what the record is used for)
FETCHES = {
    "F6": (289, "catechol"),
    "F7": (11421, "1,2-benzoquinone (oxidised catechol)"),
    "F8": (441477, "beta-D-glucosamine, the residue of the chitosan repeat unit"),
}


def raw_path(cid):
    return SOURCES / ("pubchem_cid%d.json" % cid)


def fetch(fid, cid, use):
    url = PUG % cid
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        status = resp.status
        body = resp.read()
        ctype = resp.headers.get("Content-Type", "")
    json.loads(body)  # refuse anything that is not JSON
    out = raw_path(cid)
    out.write_bytes(body)
    return {
        "bytes": len(body),
        "content_type": ctype,
        "final_url": "same",
        "id": fid,
        "note": "PubChem CID %d, %s; raw response stored at %s" % (cid, use, out.relative_to(ROOT)),
        "sha256": hashlib.sha256(body).hexdigest(),
        "status": status,
        "url": url,
        "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "via": "live",
    }


def main():
    SOURCES.mkdir(exist_ok=True)
    rows = [json.loads(line) for line in FETCH_LOG.read_text().splitlines() if line.strip()]
    known = {r["id"] for r in rows}
    added = []
    for fid, (cid, use) in FETCHES.items():
        if fid in known and raw_path(cid).exists():
            print("%s: already fetched (%s)" % (fid, raw_path(cid).relative_to(ROOT)))
            continue
        row = fetch(fid, cid, use)
        rows = [r for r in rows if r["id"] != fid] + [row]
        added.append(fid)
        print("%s: CID %d -> %s sha256 %s" % (fid, cid, raw_path(cid).relative_to(ROOT), row["sha256"][:12]))
    if added:
        FETCH_LOG.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
