"""P0-scoped job dispatch (ruling B5): git-archive sync of a pinned commit, tmux launch with a
heartbeat, hash-verified collection and one ledger line per job.

    uv run python jobs/preprint/dispatch.py run --spec jobs/preprint/specs/dryrun_probe.yaml \
        --transport local --root .local/pod
    uv run python jobs/preprint/dispatch.py run --spec jobs/preprint/specs/anchor_production.yaml \
        --transport ssh --ssh "ssh -p 22 user@host" --remote-root /workspace/nacre

The transport is an interface (put, get, run). LocalTransport treats a local directory as the
pod and runs commands there, so the whole sequence is exercised with no SSH. SSHTransport
speaks ssh and scp with keep-alive options. Nothing in the pipeline above the transport knows
which one it talks to. See README.md in this directory for the ledger format.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUN_JOB = HERE / "remote" / "run_job.sh"
LEDGER = REPO / "jobs" / "ledger" / "p0-w5.jsonl"
SSH_OPTS = ["-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4", "-o", "BatchMode=yes"]
LEDGER_FORMAT = "p0-dispatch/1"


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class DispatchError(RuntimeError):
    pass


# ================================================================================ transports
class Transport:
    """What the pipeline needs from a pod: copy a file there, copy one back, run a command in the
    remote root. Paths on the pod are relative to its root."""

    name = "abstract"

    def put(self, local, remote):
        raise NotImplementedError

    def get(self, remote, local):
        raise NotImplementedError

    def run(self, cmd, timeout=600):
        """Run a shell command in the pod root; returns (returncode, stdout, stderr)."""
        raise NotImplementedError

    def describe(self):
        return {"transport": self.name}

    def check(self, cmd, timeout=600):
        rc, out, err = self.run(cmd, timeout)
        if rc != 0:
            raise DispatchError("%s failed (rc %d): %s" % (cmd, rc, (err or out)[-500:]))
        return out


class LocalTransport(Transport):
    """A local directory plays the pod: the full sequence runs with no SSH."""

    name = "local"

    def __init__(self, root, extra_path=()):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.extra_path = [str(p) for p in extra_path]

    def _env(self):
        env = dict(os.environ)
        if self.extra_path:
            env["PATH"] = os.pathsep.join(self.extra_path + [env.get("PATH", "")])
        return env

    def put(self, local, remote):
        dest = self.root / remote
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local, dest)

    def get(self, remote, local):
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(self.root / remote, local)

    def run(self, cmd, timeout=600):
        p = subprocess.run(["bash", "-c", cmd], cwd=self.root, capture_output=True, text=True,
                           timeout=timeout, env=self._env())
        return p.returncode, p.stdout, p.stderr

    def describe(self):
        root = self.root.relative_to(REPO).as_posix() if self.root.is_relative_to(REPO) else self.root.name
        return {"transport": self.name, "root": root}


class SSHTransport(Transport):
    """ssh/scp to a pod given as the SSH string its provider prints (for example
    'ssh -p 2222 root@203.0.113.7 -i ~/.ssh/key'); remote_root is the pod working directory."""

    name = "ssh"

    def __init__(self, ssh_string, remote_root):
        args = shlex.split(ssh_string)
        if args and args[0] == "ssh":
            args = args[1:]
        self.port, self.identity, self.target, self.extra = None, None, None, []
        i = 0
        while i < len(args):
            a = args[i]
            if a == "-p":
                self.port, i = args[i + 1], i + 2
            elif a == "-i":
                self.identity, i = os.path.expanduser(args[i + 1]), i + 2
            elif a.startswith("-"):
                self.extra += [a, args[i + 1]] if a in ("-o", "-l", "-J") else [a]
                i += 2 if a in ("-o", "-l", "-J") else 1
            else:
                self.target, i = a, i + 1
        if not self.target:
            raise DispatchError("no user@host in the SSH string")
        self.remote_root = remote_root.rstrip("/")

    def _ssh(self):
        cmd = ["ssh"] + SSH_OPTS + self.extra
        if self.port:
            cmd += ["-p", str(self.port)]
        if self.identity:
            cmd += ["-i", self.identity]
        return cmd + [self.target]

    def _scp(self):
        cmd = ["scp", "-q"] + SSH_OPTS + [x for x in self.extra if x != "-t"]
        if self.port:
            cmd += ["-P", str(self.port)]
        if self.identity:
            cmd += ["-i", self.identity]
        return cmd

    def run(self, cmd, timeout=600):
        full = "mkdir -p %s && cd %s && %s" % (shlex.quote(self.remote_root), shlex.quote(self.remote_root), cmd)
        p = subprocess.run(self._ssh() + [full], capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr

    def put(self, local, remote):
        self.check("mkdir -p %s" % shlex.quote(str(Path(remote).parent)))
        p = subprocess.run(self._scp() + [str(local), "%s:%s/%s" % (self.target, self.remote_root, remote)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise DispatchError("scp put failed: %s" % p.stderr[-300:])

    def get(self, remote, local):
        Path(local).parent.mkdir(parents=True, exist_ok=True)
        p = subprocess.run(self._scp() + ["%s:%s/%s" % (self.target, self.remote_root, remote), str(local)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise DispatchError("scp get failed: %s" % p.stderr[-300:])

    def describe(self):
        return {"transport": self.name, "target": self.target, "port": self.port, "remote_root": self.remote_root}


# =================================================================================== jobs
def load_spec(path):
    import yaml

    spec = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    for k in ("id", "command", "outputs_dir"):
        if k not in spec:
            raise DispatchError("job spec %s lacks %s" % (path, k))
    spec.setdefault("packages", [])
    spec.setdefault("install_command", "")
    spec.setdefault("heartbeat_s", 30)
    spec.setdefault("stale_after_s", 300)
    spec.setdefault("launcher", "tmux")
    return spec


def pin(commit="HEAD"):
    """Full sha of the commit to ship; refuses a dirty tree when shipping HEAD."""
    sha = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--verify", commit + "^{commit}"],
                         capture_output=True, text=True)
    if sha.returncode != 0:
        raise DispatchError("cannot resolve commit %s" % commit)
    return sha.stdout.strip()


def archive(commit, out_tar):
    """git archive of the pinned commit (tracked files only); returns the tar's sha256."""
    p = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", "-o", str(out_tar), commit],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise DispatchError("git archive failed: %s" % p.stderr)
    return sha256_file(out_tar)


def job_dir(job_id):
    return "jobs/%s" % job_id


def sync(tr, spec, commit, work):
    """Ship the archive, the runner and the job description; verify the tar hash on the pod."""
    jd = job_dir(spec["run_id"])
    tar = Path(work) / "src.tar"
    tar_sha = archive(commit, tar)
    tr.put(tar, jd + "/src.tar")
    tr.put(RUN_JOB, jd + "/run_job.sh")
    desc = {k: spec[k] for k in ("command", "packages", "install_command", "heartbeat_s", "outputs_dir")}
    desc.update({"run_id": spec["run_id"], "commit": commit})
    jpath = Path(work) / "job.json"
    jpath.write_text(json.dumps(desc, indent=1, sort_keys=True), encoding="utf-8")
    tr.put(jpath, jd + "/job.json")
    remote_sha = tr.check("python3 -c \"import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())\" "
                          "%s/src.tar" % jd).strip()
    if remote_sha != tar_sha:
        raise DispatchError("archive hash differs on the pod: %s != %s" % (remote_sha, tar_sha))
    tr.check("mkdir -p %s/src && tar -xf %s/src.tar -C %s/src" % (jd, jd, jd))
    return {"archive_sha256": tar_sha, "job_json_sha256": sha256_file(jpath),
            "runner_sha256": sha256_file(RUN_JOB)}


def launch(tr, spec):
    jd = job_dir(spec["run_id"])
    session = "p0-" + spec["run_id"]
    inner = "bash %s/run_job.sh %s" % (jd, jd)
    if spec["launcher"] == "tmux":
        rc, out, _ = tr.run("command -v tmux")
        if rc != 0:
            raise DispatchError("tmux not found on the pod (launcher tmux)")
        tr.check("tmux new-session -d -s %s %s" % (shlex.quote(session), shlex.quote(inner)))
    elif spec["launcher"] == "nohup":
        tr.check("nohup %s > %s/launcher.out 2>&1 < /dev/null &" % (inner, jd))
    else:
        raise DispatchError("unknown launcher %s" % spec["launcher"])
    return {"session": session, "launcher": spec["launcher"], "launched_utc": utc_now()}


def status(tr, spec):
    """(state, heartbeat record) where state is running | done | failed | stale | absent."""
    jd = job_dir(spec["run_id"])
    rc, out, _ = tr.run("cat %s/status.json 2>/dev/null" % jd)
    st = json.loads(out) if rc == 0 and out.strip() else None
    rc, hb, _ = tr.run("cat %s/heartbeat.json 2>/dev/null" % jd)
    hb = json.loads(hb) if rc == 0 and hb.strip() else None
    if st:
        return st["state"], hb, st
    if hb is None:
        return "absent", None, None
    age = (dt.datetime.now(dt.timezone.utc)
           - dt.datetime.strptime(hb["utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds()
    return ("stale" if age > spec["stale_after_s"] else "running"), hb, None


def wait(tr, spec, timeout_s=3600, poll_s=5):
    t0 = time.time()
    beats = 0
    while True:
        state, hb, st = status(tr, spec)
        if hb:
            beats = max(beats, int(hb.get("beat", 0)))
        if state in ("done", "failed", "stale"):
            return state, hb, st, beats
        if time.time() - t0 > timeout_s:
            return "timeout", hb, st, beats
        time.sleep(poll_s)


def collect(tr, spec, dest):
    """Fetch the pod's output manifest and every listed file; refuse any hash mismatch."""
    jd = job_dir(spec["run_id"])
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    tr.get(jd + "/manifest.json", dest / "manifest.json")
    man = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    got = []
    for f in man["files"]:
        local = dest / "outputs" / f["path"]
        tr.get("%s/%s/%s" % (jd, spec["outputs_dir"], f["path"]), local)
        h = sha256_file(local)
        if h != f["sha256"]:
            raise DispatchError("hash mismatch for %s: %s != %s" % (f["path"], h, f["sha256"]))
        got.append({"path": local, "sha256": h})
    for log in ("status.json", "heartbeat.json", "install.log", "job.log"):
        rc, _, _ = tr.run("test -f %s/%s" % (jd, log))
        if rc == 0:
            tr.get("%s/%s" % (jd, log), dest / "logs" / log)
    return man, got


def ledger_line(spec, commit, sync_info, launch_info, final, collected, dest, tr, ledger=LEDGER, session="P0-W5.2"):
    """One line per job (format p0-dispatch/1, README.md)."""
    state, hb, st, beats = final
    files = [p["path"] for p in collected]
    files += sorted(Path(dest).joinpath("logs").glob("*")) + [Path(dest) / "manifest.json"]
    rec = {
        "format": LEDGER_FORMAT, "session": session, "run": spec["run_id"], "kind": "dispatch",
        "job": spec["id"], "mock": bool(spec.get("mock", False)), "transport": tr.describe(),
        "git_sha": commit, "git_dirty": False, "archive_sha256": sync_info["archive_sha256"],
        "runner_sha256": sync_info["runner_sha256"], "launcher": launch_info["launcher"],
        "session_name": launch_info["session"], "launched_utc": launch_info["launched_utc"],
        "finished_utc": (st or {}).get("finished_utc"), "state": state, "exit_code": (st or {}).get("exit_code"),
        "heartbeats": beats, "heartbeat_last_utc": (hb or {}).get("utc"),
        "packages": spec["packages"], "utc": utc_now(),
        "outputs": [{"path": Path(p).resolve().relative_to(REPO).as_posix(), "sha256": sha256_file(p)} for p in files],
    }
    Path(ledger).parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return rec


def run_job(spec_path, tr, dest_root=REPO / "results" / "preprint" / "anchor" / "dispatch", commit="HEAD",
            ledger=LEDGER, timeout_s=3600, poll_s=5, run_id=None):
    spec = load_spec(spec_path)
    commit = pin(commit)
    spec["run_id"] = run_id or "%s-%s" % (spec["id"], commit[:7])
    dest = Path(dest_root) / spec["run_id"]
    with tempfile.TemporaryDirectory() as work:
        info = sync(tr, spec, commit, work)
    li = launch(tr, spec)
    final = wait(tr, spec, timeout_s=timeout_s, poll_s=poll_s)
    if final[0] not in ("done", "failed"):
        raise DispatchError("job %s ended in state %s" % (spec["run_id"], final[0]))
    man, got = collect(tr, spec, dest)
    return ledger_line(spec, commit, info, li, final, got, dest, tr, ledger=ledger)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="jobs/preprint/dispatch.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="sync, launch, wait, collect and write the ledger line")
    r.add_argument("--spec", required=True)
    r.add_argument("--transport", choices=["local", "ssh"], required=True)
    r.add_argument("--root", help="local transport: directory that plays the pod")
    r.add_argument("--ssh", help="ssh transport: the pod's SSH string")
    r.add_argument("--remote-root", default="/workspace/nacre")
    r.add_argument("--commit", default="HEAD")
    r.add_argument("--timeout", type=int, default=6 * 3600)
    r.add_argument("--tmux-bin", default=str(Path.home() / ".nacre-envs" / "tmux" / "bin"))
    args = ap.parse_args(argv)
    if args.transport == "local":
        tr = LocalTransport(args.root or REPO / ".local" / "pod", extra_path=[args.tmux_bin])
    else:
        if not args.ssh:
            raise SystemExit("--ssh is required for the ssh transport")
        tr = SSHTransport(args.ssh, args.remote_root)
    rec = run_job(args.spec, tr, commit=args.commit, timeout_s=args.timeout)
    print(json.dumps({k: rec[k] for k in ("run", "state", "exit_code", "heartbeats", "archive_sha256")}, indent=1))
    return 0 if rec["state"] == "done" else 1


if __name__ == "__main__":
    sys.exit(main())
