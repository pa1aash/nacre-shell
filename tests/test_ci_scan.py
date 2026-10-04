import subprocess
import sys

from conftest import HOOKS_SRC, MAKER, PRODUCT, git, init_repo


def scan(repo):
    return subprocess.run([sys.executable, str(HOOKS_SRC / "ci_scan.py")], cwd=repo, capture_output=True, text=True)


def add(repo, name, text, msg="scratch: add"):
    (repo / name).write_text(text)
    git(repo, "add", name)
    assert git(repo, "commit", "-q", "--no-verify", "-m", msg).returncode == 0


def test_clean_history_passes(tmp_path):
    repo = init_repo(tmp_path / "r", copy_ops=False)
    add(repo, "a.txt", "fine\n")
    r = scan(repo)
    assert r.returncode == 0 and "0 violations" in r.stdout


def test_banned_blob_found_even_after_removal(tmp_path):
    repo = init_repo(tmp_path / "r", copy_ops=False)
    add(repo, "a.txt", "note %s\n" % PRODUCT)
    git(repo, "rm", "-q", "a.txt")
    assert git(repo, "commit", "-q", "--no-verify", "-m", "scratch: remove").returncode == 0
    r = scan(repo)
    assert r.returncode == 1 and "a.txt:1" in r.stderr


def test_banned_message_and_identity_found(tmp_path):
    repo = init_repo(tmp_path / "r", copy_ops=False)
    add(repo, "a.txt", "x\n", "scratch: about %s" % MAKER)
    git(repo, "config", "user.email", "other@example.com")
    add(repo, "b.txt", "y\n")
    r = scan(repo)
    assert r.returncode == 1
    assert "banned-maker-name" in r.stderr and "other@example.com" in r.stderr
