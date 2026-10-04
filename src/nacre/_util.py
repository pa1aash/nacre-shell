"""Helpers shared by the CLI commands. Every function takes the repo root."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_PKG_ROOT = Path(__file__).resolve().parents[2]
_cache = {}


def repo_root(start=None):
    p = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=start, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("not inside a git repository")
    return Path(p.stdout.strip())


def git(root, *args, check=False, input=None, timeout=None):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                       input=input, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), p.stderr.strip()))
    return p


def current_branch(root):
    p = git(root, "symbolic-ref", "--short", "-q", "HEAD")
    return p.stdout.strip() if p.returncode == 0 else None


def tag_exists(root, tag):
    return git(root, "rev-parse", "-q", "--verify", "refs/tags/" + tag).returncode == 0


def hooklib(root, name):
    """Load tools/githooks/<name>.py from the repo (or from this checkout)."""
    for base in (Path(root), _PKG_ROOT):
        path = base / "tools" / "githooks" / (name + ".py")
        if path.exists():
            break
    else:
        raise SystemExit("missing tools/githooks/%s.py" % name)
    key = str(path)
    if key not in _cache:
        hooks_dir = str(path.parent)
        if hooks_dir not in sys.path:
            sys.path.insert(0, hooks_dir)
        spec = importlib.util.spec_from_file_location("_nacre_hook_" + name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _cache[key] = mod
    return _cache[key]


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def utc_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
