"""Provenance records of this lane's generated files in jobs/ledger/p0-w1.jsonl.

`nacre verify` checks that the latest record for each output path matches the file's sha256, so
every command that rewrites a generated file under lit/ appends one record here.
"""
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path

LEDGER = Path("jobs") / "ledger" / "p0-w1.jsonl"
LANE = "p0-w1"


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def record(root, job, session, command, inputs, outputs):
    """Append one record: input git blobs (as they are on disk), output sha256 and the code commit."""
    root = Path(root)
    ins = [{"path": str(p), "git_blob": _git(root, "hash-object", str(p))} for p in inputs if (root / p).exists()]
    outs = [{"path": str(p), "sha256": hashlib.sha256((root / p).read_bytes()).hexdigest()} for p in outputs]
    rec = {"code_commit": _git(root, "rev-parse", "HEAD"), "command": command, "inputs": ins, "job": job,
           "lane": LANE, "outputs": outs, "session": session,
           "utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    path = root / LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec
