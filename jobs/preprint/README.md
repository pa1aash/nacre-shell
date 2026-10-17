# P0 dispatch (ruling B5)

P0-scoped job dispatch for the one pod job of the preprint (anchor production, P0-W5.3). S31 is not
run in this track, so this directory holds a small, self-contained replacement. It does not touch
the main study's dispatch and does not rebuild any image.

## Pipeline

`dispatch.py run --spec <spec> --transport local|ssh` does, in order:

1. **Pin.** Resolve the commit to a full sha (default `HEAD`).
2. **Sync.** `git archive` that commit (tracked files only) to a tar and record its sha256. Copy the tar,
   `remote/run_job.sh` and `job.json` to `jobs/<run_id>/` on the pod. Recompute the tar's sha256 there
   (any mismatch stops the job), then unpack it to `jobs/<run_id>/src`.
3. **Launch.** Start `bash run_job.sh` in a detached tmux session `p0-<run_id>`. The launcher checks
   that tmux exists on the pod; `launcher: nohup` exists for test machines without tmux.
4. **Run, on the pod** (`remote/run_job.sh`):
   - A heartbeat loop rewrites `heartbeat.json` (`utc`, `beat`, `state`, `pid`) every `heartbeat_s`.
   - The pinned `packages` are installed at job start with the spec's `install_command`, logged to
     `install.log`; no image is rebuilt.
   - The command runs in `src/` with `OUTPUTS` and `JOBDIR` set, logging to `job.log`.
   - `manifest.json` lists every output with its sha256; `status.json` holds `state` (done or failed),
     `exit_code` and `finished_utc`.
5. **Wait.** Poll `status.json`. A heartbeat older than `stale_after_s` with no status is reported as
   `stale`.
6. **Collect.** Fetch `manifest.json` and every listed file. Recompute each sha256 and refuse any
   mismatch. Fetch the logs.
7. **Ledger.** Append one line to `jobs/ledger/p0-w5.jsonl` (format below). `outputs` lists only files
   that are committed: every collected file up to `COMMIT_LIMIT_BYTES` (1 MiB) is staged with
   `git add -f` (`--stage`; `*.log` and `*.out` are git-ignored), and a larger file stays local, recorded
   under `local_only` by sha256 and size. `nacre verify`'s provenance check reads `outputs` only and
   requires each listed file on a clean checkout (lane note N19).

`run` does all of this in one call. For a long job the same steps split in two, so a session can end
while the job runs and a later session collects it:

    uv run python jobs/preprint/dispatch.py launch  --spec <spec> --transport ssh --ssh-file .local/w5/pod.txt
    uv run python jobs/preprint/dispatch.py status  --run-id <run_id> --transport ssh --ssh-file .local/w5/pod.txt
    uv run python jobs/preprint/dispatch.py collect --run-id <run_id> --transport ssh --ssh-file .local/w5/pod.txt --stage

`launch` writes the launch record to `.local/w5/runs/<run_id>.json` (local only), which `status` and
`collect` read back.

The transport is an interface with three operations: `put`, `get` and `run` (`dispatch.Transport`).

- `LocalTransport(root)` makes a local directory the pod, so the full sequence runs with no SSH.
- `SSHTransport(ssh_string, remote_root)` uses ssh and scp with `ServerAliveInterval=15`,
  `ServerAliveCountMax=4` and `BatchMode=yes`. It accepts the SSH string as the provider prints it,
  for example `ssh -p 2222 root@203.0.113.7 -i ~/.ssh/pod_key`, or reads it from a file under `.local/`
  (`--ssh-file`). The SSH string is never committed: the ledger records the transport as
  `{transport: ssh, host: cpu-pod, remote_root}`, with no user, host, port or key path.

Tests: `tests/anchor/test_dispatch.py`. They cover the local transport end to end, the tamper
refusal, a stale heartbeat and the ledger line.

## Ledger format `p0-dispatch/1`

No S31 ledger format is documented anywhere in this repository (searched: `ops/`, `jobs/`, `src/`).
This format is therefore defined here, one JSON object per line:

| Field | Meaning |
|---|---|
| `format` | `p0-dispatch/1` |
| `session`, `run`, `job`, `kind` | session id; run id `<job id>-<sha7>`; job id from the spec; `dispatch` |
| `mock` | true for a dry run (no result of the study) |
| `transport` | `{transport: local, root}` or `{transport: ssh, host: cpu-pod, remote_root}` (no SSH details) |
| `git_sha`, `git_dirty` | the pinned commit shipped; `git_dirty` is false because only tracked files of that commit are shipped |
| `archive_sha256`, `runner_sha256` | sha256 of the shipped tar and of `run_job.sh` |
| `launcher`, `session_name` | `tmux` (or `nohup`) and the tmux session |
| `launched_utc`, `finished_utc`, `state`, `exit_code` | as recorded on the pod |
| `heartbeats`, `heartbeat_last_utc` | the highest beat count seen and the last beat |
| `packages` | the pinned packages installed at job start |
| `outputs` | `[{path, sha256}]`: repository paths of the committed collected files, under `results/preprint/anchor/dispatch/<run_id>/`. `nacre verify` checks them like every other ledger record. |
| `local_only` | `[{path, sha256, bytes, local_only: true}]`: collected files over the commit limit, kept local and recorded by hash only (from P0-W5.3) |
| `commit_limit_bytes` | the per-file commit limit applied (from P0-W5.3) |
| `utc` | time the line was written |

## Specs

- `specs/dryrun_probe.yaml`: the full dry run on the local transport. Its job is `probe.py`, which
  checks only the plumbing.
- `specs/anchor_production.yaml`: draft for P0-W5.3, with the pinned packages of the local protocol
  test. Open item: `src/nacre/anchor/xtb_env.yaml` pins osx-arm64 builds, so linux-64 builds of
  xtb 6.6.1 and CREST 2.12 must be pinned before launch.

## What Palaash must provide for the real pod run (P0-W5.3)

1. The pod's SSH string exactly as the provider prints it (user, host, port, key path). The key must
   already be loaded or named with `-i`; the dispatch uses `BatchMode=yes`, so it never prompts.
2. A CPU pod with at least 32 vCPU and 128 GB RAM, Linux x86_64, with outbound network (pip and
   conda-forge for the pinned installs), `python3` (3.10 or later), `tar`, `curl` and `tmux`.
3. A writable working directory (default `/workspace/nacre`), passed as `--remote-root`.

Run: `uv run python jobs/preprint/dispatch.py run --spec jobs/preprint/specs/anchor_production.yaml --transport ssh --ssh "<SSH string>" --remote-root /workspace/nacre`.
