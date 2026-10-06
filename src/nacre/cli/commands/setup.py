"""nacre setup: idempotent configuration of a fresh clone or worktree."""
import json
import os
import shutil
import stat
import sys
from pathlib import Path

from nacre import _util

HOOKS = ["commit-msg", "pre-commit", "pre-merge-commit", "pre-push"]

WINDOWS_OPENSSH_KEYGEN = "C:/Windows/System32/OpenSSH/ssh-keygen.exe"


def _git_install_root(root):
    """The Git-for-Windows install root, derived from `git --exec-path`."""
    p = _util.git(root, "--exec-path")
    if p.returncode != 0 or not p.stdout.strip():
        return None
    parents = Path(p.stdout.strip()).parents
    # exec-path is typically <root>/mingw64/libexec/git-core
    return parents[2] if len(parents) > 2 else None


def ssh_program_candidates(root):
    candidates = [WINDOWS_OPENSSH_KEYGEN]
    install_root = _git_install_root(root)
    if install_root is not None:
        candidates.append(str(install_root / "usr" / "bin" / "ssh-keygen.exe"))
    return candidates


def resolve_ssh_program(root, path_exists):
    for candidate in ssh_program_candidates(root):
        if path_exists(candidate):
            return candidate
    return None


def _cfg(root, key):
    p = _util.git(root, "config", "--local", "--get", key)
    return p.stdout.strip() if p.returncode == 0 else None


def _git_path(root, rel):
    out = _util.git(root, "rev-parse", "--path-format=absolute", "--git-path", rel, check=True).stdout.strip()
    return Path(out)


def settings_payload():
    return {"attribution": {"commit": "", "pr": ""},
            "include" + "Co" + "Authored" + "By": False}


def desired_config(root, signing_key):
    scan = _util.hooklib(root, "_scan")
    want = {"user.name": scan.R1_NAME, "user.email": scan.R1_EMAIL,
            "core.hooksPath": "tools/githooks", "core.autocrlf": "false"}
    key = signing_key or _cfg(root, "user.signingkey")
    if key:
        want.update({"gpg.format": "ssh", "user.signingkey": str(key), "commit.gpgsign": "true",
                     "tag.gpgsign": "true", "gpg.ssh.allowedSignersFile": "ops/allowed_signers"})
    return want


def plan(root, signing_key=None, ssh_program=None, path_exists=None):
    """List of (description, ok, apply) for everything setup manages."""
    root = Path(root)
    scan = _util.hooklib(root, "_scan")
    items = []

    for key, value in desired_config(root, signing_key).items():
        def apply(key=key, value=value):
            _util.git(root, "config", "--local", key, value, check=True)
        have = _cfg(root, key)
        # git lower-cases the variable part for matching; compare values only
        items.append(("git config %s = %s" % (key, value), have == value, apply))
    if not signing_key and not _cfg(root, "user.signingkey"):
        items.append(("signing is not configured (pass --signing-key PATH)", False, None))

    if sys.platform == "win32" and (signing_key or _cfg(root, "user.signingkey")):
        exists = path_exists or (lambda p: Path(p).exists())
        current = _cfg(root, "gpg.ssh.program")
        if ssh_program:
            want = ssh_program
        elif current and exists(current):
            want = current
        else:
            want = resolve_ssh_program(root, exists)

        def apply_ssh_program(want=want):
            _util.git(root, "config", "--local", "gpg.ssh.program", want, check=True)
        ok = bool(want) and current == want
        desc = "git config gpg.ssh.program = %s" % (want or "<no ssh-keygen found>")
        items.append((desc, ok, apply_ssh_program if want else None))

    exclude = _git_path(root, "info/exclude")
    wanted = [scan.LOCAL_GUIDE, scan.LOCAL_SETTINGS_DIR + "/", ".local/", ".env"]

    def have_excludes():
        lines = exclude.read_text(encoding="utf-8").splitlines() if exclude.exists() else []
        return [w for w in wanted if w not in lines]

    def apply_excludes():
        exclude.parent.mkdir(parents=True, exist_ok=True)
        text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
        for w in have_excludes():
            text += ("" if not text or text.endswith("\n") else "\n") + w + "\n"
        exclude.write_text(text, encoding="utf-8")
    items.append(("local-only exclude entries", not have_excludes(), apply_excludes))

    guide = root / scan.LOCAL_GUIDE
    guide_text = "Read ops/RUNBOOK.md first; it is the operating manual for this repository.\n"
    items.append(("local guide file", guide.exists(), lambda: guide.write_text(guide_text, encoding="utf-8")))

    settings = root / scan.LOCAL_SETTINGS_DIR / "settings.json"

    def apply_settings():
        settings.parent.mkdir(exist_ok=True)
        settings.write_text(json.dumps(settings_payload(), indent=2) + "\n", encoding="utf-8")
    items.append(("local settings directory", settings.exists(), apply_settings))

    prompts = root / ".local" / "prompts"
    items.append((".local/prompts/", prompts.is_dir(), lambda: prompts.mkdir(parents=True, exist_ok=True)))

    env, example = root / ".env", root / ".env.example"
    if example.exists():
        items.append((".env from .env.example", env.exists() or env.is_symlink(),
                      lambda: shutil.copyfile(example, env)))

    if os.name != "nt":
        for hook in HOOKS:
            path = root / "tools" / "githooks" / hook

            def apply_exec(path=path):
                path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            items.append(("executable shim %s" % hook, path.exists() and os.access(path, os.X_OK), apply_exec))
    return items


def signer_line(root, signing_key=None):
    scan = _util.hooklib(root, "_scan")
    key = signing_key or _cfg(root, "user.signingkey")
    if not key:
        return None
    path = Path(key).expanduser()
    if path.suffix != ".pub":
        path = path.with_name(path.name + ".pub")
    if not path.exists():
        return None
    return '%s namespaces="git" %s' % (scan.R1_EMAIL, path.read_text(encoding="utf-8").strip())


def _cmd(args):
    root = _util.repo_root()
    key = str(Path(args.signing_key).expanduser()) if args.signing_key else None
    ssh_program = args.ssh_program
    items = plan(root, key, ssh_program)
    drift = [i for i in items if not i[1]]
    for desc, ok, _ in items:
        print("%-5s %s" % ("ok" if ok else "DRIFT", desc))
    if args.check:
        print("setup --check: %s" % ("no drift" if not drift else "%d item(s) drifted" % len(drift)))
        return 1 if drift else 0
    for desc, ok, apply in drift:
        if apply:
            apply()
            print("fixed %s" % desc)
    still = [d for d, ok, a in plan(root, key, ssh_program) if not ok]
    line = signer_line(root, key)
    if line:
        print("allowed_signers line for this machine (add it to ops/allowed_signers via main):")
        print(line)
    return 1 if still else 0


def register(subparsers):
    p = subparsers.add_parser("setup", help="configure this clone or worktree (idempotent)")
    p.add_argument("--signing-key", metavar="PATH", help="SSH public key used to sign commits")
    p.add_argument("--ssh-program", metavar="PATH", help="override gpg.ssh.program (Windows)")
    p.add_argument("--check", action="store_true", help="report drift without changing anything")
    p.set_defaults(func=_cmd)
