"""Dry-run probe of the P0 dispatch: runs on the pod from the shipped archive.

It answers no physics question. It checks what a real job relies on: the archive unpacked at
the pinned commit, the job description readable, outputs written where the runner collects
them, and a run long enough to leave several heartbeats. Standard library only.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

out = Path(os.environ["OUTPUTS"])
job = json.loads(Path(os.environ["JOBDIR"], "job.json").read_text(encoding="utf-8"))
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else 6.0
src = Path.cwd()
tracked = sorted(p.relative_to(src).as_posix() for p in src.rglob("*") if p.is_file())
digest = hashlib.sha256("\n".join(tracked).encode()).hexdigest()
time.sleep(seconds)
(out / "probe.json").write_text(json.dumps({
    "commit": job["commit"], "run_id": job["run_id"], "n_files": len(tracked), "file_list_sha256": digest,
    "has_runner_source": (src / "jobs" / "preprint" / "dispatch.py").is_file(),
    "python": sys.version.split()[0], "slept_s": seconds}, indent=1, sort_keys=True) + "\n", encoding="utf-8")
(out / "nested").mkdir(exist_ok=True)
(out / "nested" / "note.txt").write_text("collected through the manifest\n", encoding="utf-8")
