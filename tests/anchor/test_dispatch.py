"""P0 dispatch on the local transport: sync, launch, heartbeat, hash-verified collection, ledger."""
import importlib.util
import json
import shutil
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("p0_dispatch", REPO / "jobs" / "preprint" / "dispatch.py")
D = importlib.util.module_from_spec(SPEC)
sys.modules["p0_dispatch"] = D
SPEC.loader.exec_module(D)

TMUX_BIN = Path.home() / ".nacre-envs" / "tmux" / "bin"


def _launcher():
    return "tmux" if (TMUX_BIN / "tmux").exists() or shutil.which("tmux") else "nohup"


def _spec(tmp_path, command, **kw):
    s = {"id": "t-" + kw.pop("tag", "job"), "command": command, "outputs_dir": "outputs", "heartbeat_s": 1,
         "stale_after_s": 30, "launcher": _launcher(), "packages": [], "install_command": "", "mock": True}
    s.update(kw)
    p = tmp_path / "spec.yaml"
    import yaml

    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    return p


def _transport(tmp_path):
    return D.LocalTransport(tmp_path / "pod", extra_path=[TMUX_BIN])


def test_full_cycle_on_the_local_transport(tmp_path):
    spec = _spec(tmp_path, 'sleep 3; echo hi > "$OUTPUTS/a.txt"; mkdir -p "$OUTPUTS/d"; echo x > "$OUTPUTS/d/b.txt"',
                 packages=["demo==1.0"], install_command="echo would install {packages}")
    tr = _transport(tmp_path)
    ledger = tmp_path / "ledger.jsonl"
    dest = REPO / ".local" / "test_dispatch" / tmp_path.name
    try:
        rec = D.run_job(spec, tr, dest_root=dest, ledger=ledger, timeout_s=120, poll_s=1, run_id="t-%d" % time.time_ns())
        assert rec["state"] == "done" and rec["exit_code"] == 0
        assert rec["format"] == D.LEDGER_FORMAT and rec["heartbeats"] >= 1
        paths = {o["path"].rsplit("/", 1)[-1] for o in rec["outputs"]}
        assert {"a.txt", "b.txt", "manifest.json", "install.log", "status.json"} <= paths
        line = json.loads(ledger.read_text().splitlines()[-1])
        assert line["run"] == rec["run"] and line["packages"] == ["demo==1.0"]
        install = (dest / rec["run"] / "logs" / "install.log").read_text()
        assert "would install demo==1.0" in install
    finally:
        shutil.rmtree(dest, ignore_errors=True)
        if rec_session := locals().get("rec"):
            tr.run("tmux kill-session -t %s 2>/dev/null" % rec_session["session_name"])


def test_collection_refuses_a_tampered_output(tmp_path):
    spec_path = _spec(tmp_path, 'echo good > "$OUTPUTS/a.txt"', tag="tamper")
    tr = _transport(tmp_path)
    spec = D.load_spec(spec_path)
    spec["run_id"] = "tamper"
    with __import__("tempfile").TemporaryDirectory() as work:
        D.sync(tr, spec, D.pin("HEAD"), work)
    D.launch(tr, spec)
    state = D.wait(tr, spec, timeout_s=60, poll_s=1)[0]
    assert state == "done"
    (tr.root / "jobs" / "tamper" / "outputs" / "a.txt").write_text("evil\n")
    with pytest.raises(D.DispatchError, match="hash mismatch"):
        D.collect(tr, spec, tmp_path / "got")


def test_stale_heartbeat_is_reported(tmp_path):
    spec = D.load_spec(_spec(tmp_path, "true", tag="stale"))
    spec["run_id"] = "stale"
    tr = _transport(tmp_path)
    jd = tr.root / "jobs" / "stale"
    jd.mkdir(parents=True)
    (jd / "heartbeat.json").write_text(json.dumps({"utc": "2000-01-01T00:00:00Z", "beat": 3}))
    assert D.status(tr, spec)[0] == "stale"


def test_sync_refuses_a_corrupted_archive(tmp_path, monkeypatch):
    spec = D.load_spec(_spec(tmp_path, "true", tag="corrupt"))
    spec["run_id"] = "corrupt"
    tr = _transport(tmp_path)
    real_put = tr.put

    def put(local, remote):
        real_put(local, remote)
        if remote.endswith("src.tar"):
            with open(tr.root / remote, "ab") as fh:
                fh.write(b"x")

    monkeypatch.setattr(tr, "put", put)
    with pytest.raises(D.DispatchError, match="archive hash differs"):
        with __import__("tempfile").TemporaryDirectory() as work:
            D.sync(tr, spec, D.pin("HEAD"), work)


def test_ssh_string_parsing():
    t = D.SSHTransport("ssh -p 2222 root@203.0.113.7 -i ~/.ssh/k -o StrictHostKeyChecking=no", "/workspace/n")
    assert t.port == "2222" and t.target == "root@203.0.113.7" and t.identity.endswith("/.ssh/k")
    assert "-P" in t._scp() and "-p" in t._ssh() and "StrictHostKeyChecking=no" in t._ssh()
    with pytest.raises(D.DispatchError):
        D.SSHTransport("ssh -p 22", "/x")
