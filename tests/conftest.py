import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOKS_SRC = REPO / "tools" / "githooks"
sys.path.insert(0, str(HOOKS_SRC))

R1_NAME = "Palaash Gang"
R1_EMAIL = "palaashgang@gmail.com"


def words(codes):
    """Build a string from character codes so test sources never spell it."""
    return "".join(map(chr, codes))


PRODUCT = words([99, 108, 97, 117, 100, 101])
MAKER = words([97, 110, 116, 104, 114, 111, 112, 105, 99])
COAUTHOR = "Co" + "-Au" + "thored-" + "By"
LOCAL_GUIDE = PRODUCT.upper() + ".md"
LOCAL_SETTINGS = "." + PRODUCT


def run(args, cwd, **kw):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, **kw)


def git(repo, *args, **kw):
    return run(["git", *args], repo, **kw)


@pytest.fixture(scope="session")
def ssh_key(tmp_path_factory):
    d = tmp_path_factory.mktemp("sshkey")
    key = d / "id_test"
    subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(key), "-C", "test"], check=True)
    return key


def init_repo(path, copy_ops=True):
    """A scratch repo with R1 identity and the real ops config (not the hooks)."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    git(path, "config", "user.name", R1_NAME)
    git(path, "config", "user.email", R1_EMAIL)
    git(path, "config", "commit.gpgsign", "false")
    git(path, "config", "tag.gpgsign", "false")
    if copy_ops:
        (path / "ops").mkdir(exist_ok=True)
        for name in ("lanes.yaml", "frozen.yaml"):
            shutil.copy(REPO / "ops" / name, path / "ops" / name)
    return path


@pytest.fixture
def hook_repo(tmp_path):
    """Scratch repo wired to the real hook scripts (run with this interpreter)."""
    repo = init_repo(tmp_path / "repo")
    shutil.copytree(HOOKS_SRC, repo / "tools" / "githooks", ignore=shutil.ignore_patterns("__pycache__"))
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    for name in ("commit-msg", "pre-commit", "pre-merge-commit", "pre-push"):
        shim = hooks / name
        shim.write_text('#!/bin/sh\nexec "%s" "%s/tools/githooks/%s.py" "$@"\n' % (sys.executable, repo, name))
        shim.chmod(0o755)
    git(repo, "config", "core.hooksPath", str(hooks))
    (repo / "README.md").write_text("scratch\n")
    git(repo, "add", "README.md")
    assert git(repo, "commit", "-q", "--no-verify", "-m", "scratch: init").returncode == 0
    return repo


def stage_all(repo, pause=1.0):
    """git add -A, asserted: it must succeed and leave something staged. One retry after a pause, then a clear error."""
    last = None
    for attempt in (1, 2):
        added = git(repo, "add", "-A")
        staged = git(repo, "diff", "--cached", "--quiet")
        if added.returncode == 0 and staged.returncode != 0:
            return
        last = (added, staged)
        if attempt == 1:
            time.sleep(pause)
    added, staged = last
    raise RuntimeError(
        "git add -A staged nothing in %s after 2 attempts (add rc=%s, diff --cached --quiet rc=%s); stderr: %s %s"
        % (repo, added.returncode, staged.returncode, added.stderr.strip(), staged.stderr.strip())
    )


@pytest.fixture
def scratch_clone(tmp_path):
    """A copy of the working tree (tracked and untracked, not ignored) as a new repo."""
    names = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], REPO).stdout.split("\0")
    dest = tmp_path / "clone"
    for rel in [n for n in names if n]:
        src = REPO / rel
        if src.is_file():
            (dest / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest / rel)
    init_repo(dest, copy_ops=False)
    stage_all(dest)
    assert git(dest, "commit", "-q", "--no-verify", "-m", "scratch: snapshot").returncode == 0
    return dest


def nacre(args, cwd, **kw):
    code = "from nacre.cli import main; main()"
    return subprocess.run([sys.executable, "-c", code, *args], cwd=cwd, capture_output=True, text=True, **kw)
