import sys
from pathlib import Path

import yaml

import nacre
from conftest import R1_EMAIL, git, nacre as run_nacre
from nacre.cli.commands import setup


def test_discovery_loads_subpackage_cli(tmp_path, monkeypatch, capsys):
    good = tmp_path / "zzgood"
    good.mkdir()
    (good / "__init__.py").write_text("")
    (good / "cli.py").write_text(
        "def register(subparsers):\n"
        "    p = subparsers.add_parser('dummy-hello')\n"
        "    p.set_defaults(func=lambda a: 0)\n")
    bad = tmp_path / "zzbad"
    bad.mkdir()
    (bad / "__init__.py").write_text("")
    (bad / "cli.py").write_text("raise RuntimeError('boom')\n")
    monkeypatch.setattr(nacre, "__path__", list(nacre.__path__) + [str(tmp_path)])
    for m in [m for m in sys.modules if m.startswith(("nacre.zzgood", "nacre.zzbad"))]:
        monkeypatch.delitem(sys.modules, m)
    from nacre.cli import build_parser
    parser = build_parser()
    args = parser.parse_args(["dummy-hello"])
    assert args.func(args) == 0
    assert "zzbad" in capsys.readouterr().err
    assert parser.parse_args(["status"]).func is not None


def test_builtin_commands_registered():
    from nacre.cli import build_parser
    parser = build_parser()
    for cmd in (["status"], ["verify"], ["gate", "G0"], ["setup"], ["lane", "new", "x"],
                ["wave", "status"], ["wave", "check", "S00"]):
        assert parser.parse_args(cmd).func is not None


def test_status_in_scratch_clone(scratch_clone):
    r = run_nacre(["status"], scratch_clone)
    assert r.returncode == 0, r.stderr
    assert "branch: main" in r.stdout
    assert "lane: a-main   laptop: A" in r.stdout
    assert "wave 0 open" in r.stdout


def test_setup_check_and_apply_in_scratch_clone(scratch_clone, ssh_key):
    pub = str(ssh_key) + ".pub"
    r = run_nacre(["setup", "--check"], scratch_clone)
    assert r.returncode == 1 and "DRIFT git config core.hooksPath" in r.stdout
    assert git(scratch_clone, "config", "--local", "--get", "core.hooksPath").stdout == ""  # unchanged
    r = run_nacre(["setup", "--signing-key", pub], scratch_clone)
    assert r.returncode == 0, r.stdout + r.stderr
    assert 'namespaces="git"' in r.stdout and R1_EMAIL in r.stdout
    r = run_nacre(["setup", "--check", "--signing-key", pub], scratch_clone)
    assert r.returncode == 0 and "no drift" in r.stdout
    r = run_nacre(["setup", "--check"], scratch_clone)
    assert r.returncode == 0
    assert (scratch_clone / ".local" / "prompts").is_dir() and (scratch_clone / ".env").exists()
    exclude = (scratch_clone / ".git" / "info" / "exclude").read_text()
    assert ".local/" in exclude and ".env" in exclude


def _ssh_program_item(items):
    return next(i for i in items if "gpg.ssh.program" in i[0])


def test_setup_windows_ssh_program_unset_uses_openssh_path(scratch_clone, ssh_key, monkeypatch):
    run_nacre(["setup", "--signing-key", str(ssh_key) + ".pub"], scratch_clone)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    desc, ok, apply = _ssh_program_item(
        setup.plan(scratch_clone, path_exists=lambda p: p == setup.WINDOWS_OPENSSH_KEYGEN))
    assert not ok and setup.WINDOWS_OPENSSH_KEYGEN in desc
    apply()
    got = git(scratch_clone, "config", "--local", "--get", "gpg.ssh.program").stdout.strip()
    assert got == setup.WINDOWS_OPENSSH_KEYGEN


def test_setup_windows_ssh_program_falls_back_to_git_path_when_openssh_absent(scratch_clone, ssh_key, monkeypatch):
    run_nacre(["setup", "--signing-key", str(ssh_key) + ".pub"], scratch_clone)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    monkeypatch.setattr(setup, "_git_install_root", lambda root: Path("C:/Program Files/Git"))
    git_path = "C:/Program Files/Git/usr/bin/ssh-keygen.exe"
    desc, ok, apply = _ssh_program_item(
        setup.plan(scratch_clone, path_exists=lambda p: p == git_path))
    assert not ok and git_path in desc


def test_setup_windows_ssh_program_override_respected(scratch_clone, ssh_key, monkeypatch):
    run_nacre(["setup", "--signing-key", str(ssh_key) + ".pub"], scratch_clone)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    override = "D:/custom/ssh-keygen.exe"
    desc, ok, apply = _ssh_program_item(
        setup.plan(scratch_clone, ssh_program=override, path_exists=lambda p: False))
    assert override in desc and not ok
    apply()
    got = git(scratch_clone, "config", "--local", "--get", "gpg.ssh.program").stdout.strip()
    assert got == override


def test_setup_windows_ssh_program_check_reports_drift(scratch_clone, ssh_key, monkeypatch):
    run_nacre(["setup", "--signing-key", str(ssh_key) + ".pub"], scratch_clone)
    monkeypatch.setattr(setup.sys, "platform", "win32")
    _, ok, _ = _ssh_program_item(setup.plan(scratch_clone, path_exists=lambda p: False))
    assert not ok


def test_setup_ssh_program_noop_on_darwin(scratch_clone, ssh_key, monkeypatch):
    run_nacre(["setup", "--signing-key", str(ssh_key) + ".pub"], scratch_clone)
    monkeypatch.setattr(setup.sys, "platform", "darwin")
    items = setup.plan(scratch_clone)
    assert not any("gpg.ssh.program" in i[0] for i in items)


def _gate_files(repo, extra_paths, audit, signoffs):
    (repo / "ops" / "gates" / "G9.yaml").write_text(yaml.safe_dump(
        {"gate": "G9", "criteria": [{"type": "files_exist", "paths": extra_paths}]}))
    lines = ["Gate: G9", "A-check: PENDING", audit] + ["H-signoff %s: %s" % kv for kv in signoffs]
    (repo / "ops" / "gates" / "G9.md").write_text("\n".join(lines) + "\n")


def test_gate_refuses_tag_without_audit_and_signoffs(scratch_clone):
    _gate_files(scratch_clone, ["README.md"], "C-audit: PENDING", [("Palaash Gang", "PENDING")])
    r = run_nacre(["gate", "G9", "--tag"], scratch_clone)
    assert r.returncode == 1
    assert "C-audit" in r.stdout and "H-signoff Palaash Gang" in r.stdout
    assert git(scratch_clone, "tag", "-l", "g9").stdout == ""


def test_gate_refuses_tag_when_layer_a_fails(scratch_clone):
    _gate_files(scratch_clone, ["nope.txt"], "C-audit: PASS 2026-10-05", [("Palaash Gang", "PASS 2026-10-05")])
    r = run_nacre(["gate", "G9", "--tag"], scratch_clone)
    assert r.returncode == 1 and "layer A" in r.stdout and "nope.txt" in r.stdout
    assert git(scratch_clone, "tag", "-l", "g9").stdout == ""


def test_gate_check_and_packet(scratch_clone):
    _gate_files(scratch_clone, ["README.md"], "C-audit: PENDING", [("Palaash Gang", "PENDING")])
    r = run_nacre(["gate", "G9", "--check", "--packet"], scratch_clone)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "A-check: PASS 20" in (scratch_clone / "ops" / "gates" / "G9.md").read_text()
    packet = (scratch_clone / "ops" / "packets" / "G9.md").read_text()
    assert "README.md" in packet and "C-audit" in packet


def test_gate_tags_when_everything_is_in_place(scratch_clone, ssh_key):
    _gate_files(scratch_clone, ["README.md"], "C-audit: PASS 2026-10-05", [("Palaash Gang", "PASS 2026-10-05")])
    git(scratch_clone, "config", "gpg.format", "ssh")
    git(scratch_clone, "config", "user.signingkey", str(ssh_key) + ".pub")
    git(scratch_clone, "config", "tag.gpgsign", "true")
    r = run_nacre(["gate", "G9", "--tag"], scratch_clone)
    assert r.returncode == 0, r.stdout + r.stderr
    body = git(scratch_clone, "cat-file", "tag", "g9").stdout
    assert "BEGIN SSH SIGNATURE" in body


def test_gate_refuses_unsigned_tag(scratch_clone):
    _gate_files(scratch_clone, ["README.md"], "C-audit: PASS 2026-10-05", [("Palaash Gang", "PASS 2026-10-05")])
    r = run_nacre(["gate", "G9", "--tag"], scratch_clone)
    assert r.returncode == 1 and "not signed" in r.stdout
    assert git(scratch_clone, "tag", "-l", "g9").stdout == ""


def test_lane_new_refuses_unregistered(scratch_clone):
    r = run_nacre(["lane", "new", "a-nonexistent"], scratch_clone)
    assert r.returncode != 0 and "not registered" in (r.stdout + r.stderr)


def test_verify_json_in_scratch_clone(scratch_clone):
    import json, os
    env = dict(os.environ, NACRE_VERIFY_SKIP_TESTS="1")
    r = run_nacre(["verify", "--json"], scratch_clone, env=env)
    data = json.loads(r.stdout)
    names = [c["name"] for c in data["checks"]]
    assert names == ["tests", "attribution", "identity", "signatures", "lane ownership",
                     "frozen paths", "provenance", "number linter"]
    status = {c["name"]: c["status"] for c in data["checks"]}
    assert status["attribution"] == "PASS" and status["identity"] == "PASS"
    assert status["signatures"] == "FAIL"  # the scratch snapshot commit is unsigned
    assert status["number linter"] == "INACTIVE"
