#!/usr/bin/env bash
# Pod-side runner of one P0 job (jobs/preprint/dispatch.py ships it beside the archive).
#   bash run_job.sh <job dir>
# Reads <job dir>/job.json, writes a heartbeat every heartbeat_s seconds, installs the pinned
# packages (logged to install.log), runs the command in <job dir>/src with OUTPUTS pointing at
# <job dir>/<outputs_dir>, then writes manifest.json (sha256 of every output) and status.json.
set -u
JD="$(cd "$1" && pwd)"
cfg() { python3 -c "import json,sys;v=json.load(open('$JD/job.json'))[sys.argv[1]];print(v if isinstance(v,(str,int)) else ' '.join(v))" "$1"; }
utc() { date -u +%Y-%m-%dT%H:%M:%SZ; }
HB=$(cfg heartbeat_s)
OUT="$JD/$(cfg outputs_dir)"
mkdir -p "$OUT"

beat=0
( while true; do
    beat=$((beat + 1))
    printf '{"utc": "%s", "beat": %d, "state": "running", "pid": %d}\n' "$(utc)" "$beat" "$$" > "$JD/heartbeat.json.tmp"
    mv "$JD/heartbeat.json.tmp" "$JD/heartbeat.json"
    sleep "$HB"
  done ) &
HBPID=$!

PKGS="$(cfg packages)"
INSTALL="$(cfg install_command)"
{
  echo "start $(utc)"
  if [ -n "$PKGS" ] && [ -n "$INSTALL" ]; then
    echo "installing pinned packages: $PKGS"
    ( cd "$JD" && eval "${INSTALL//\{packages\}/$PKGS}" )
    echo "install exit $?"
  else
    echo "nothing to install"
  fi
} > "$JD/install.log" 2>&1

CMD="$(cfg command)"
( cd "$JD/src" && OUTPUTS="$OUT" JOBDIR="$JD" bash -c "$CMD" ) > "$JD/job.log" 2>&1
RC=$?

python3 - "$OUT" "$JD/manifest.json" <<'PY'
import hashlib, json, os, sys
root, dest = sys.argv[1], sys.argv[2]
files = []
for d, _, names in os.walk(root):
    for n in sorted(names):
        p = os.path.join(d, n)
        files.append({"path": os.path.relpath(p, root), "sha256": hashlib.sha256(open(p, "rb").read()).hexdigest(),
                      "bytes": os.path.getsize(p)})
json.dump({"files": sorted(files, key=lambda f: f["path"])}, open(dest, "w"), indent=1, sort_keys=True)
PY

kill "$HBPID" 2>/dev/null
wait "$HBPID" 2>/dev/null
STATE=done; [ "$RC" -ne 0 ] && STATE=failed
printf '{"state": "%s", "exit_code": %d, "finished_utc": "%s"}\n' "$STATE" "$RC" "$(utc)" > "$JD/status.json"
