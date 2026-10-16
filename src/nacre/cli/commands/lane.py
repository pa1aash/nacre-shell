"""nacre lane: create worktrees for registered lanes."""
import shutil
import subprocess
import sys
from pathlib import Path

from nacre import _util


def main_repo(root):
    """The primary working tree, even when called from a lane worktree."""
    common = _util.git(root, "rev-parse", "--path-format=absolute", "--git-common-dir", check=True).stdout.strip()
    return Path(common).parent


def new_lane(root, lane, base="origin/main"):
    lib = _util.hooklib(root, "_lanes")
    scan = _util.hooklib(root, "_scan")
    cfg = lib.load_lanes(str(root))
    entry = lib.lane_entry(cfg, lane)
    if entry is None or lib.laptop_of(lane, cfg) is None:
        raise SystemExit("REFUSED: lane %r is not registered in ops/lanes.yaml" % lane)
    if entry.get("branch"):
        raise SystemExit("REFUSED: lane %r lives on branch %s, not a lane worktree" % (lane, entry["branch"]))
    main = main_repo(root)
    target = main.parent / ("%s-%s" % (main.name, lane))
    if target.exists():
        raise SystemExit("REFUSED: %s already exists" % target)
    _util.git(root, "fetch", "origin", timeout=60)
    if _util.git(root, "rev-parse", "-q", "--verify", base + "^{commit}").returncode != 0:
        raise SystemExit("REFUSED: base %s does not exist (is the remote empty?)" % base)
    _util.git(root, "worktree", "add", "-b", "lane/" + lane, str(target), base, check=True)
    guide, settings = scan.LOCAL_GUIDE, scan.LOCAL_SETTINGS_DIR
    if (main / guide).exists():
        shutil.copyfile(main / guide, target / guide)
    if (main / settings).is_dir():
        shutil.copytree(main / settings, target / settings, dirs_exist_ok=True)
    (target / ".local" / "prompts").mkdir(parents=True, exist_ok=True)
    env = target / ".env"
    if not env.exists() and (main / ".env").exists():
        env.symlink_to(main / ".env")
    subprocess.run(["uv", "sync"], cwd=target, check=True)
    subprocess.run(["uv", "run", "nacre", "setup", "--check"], cwd=target)
    return target


def link_local_files(main, target):
    """Copy the local guide and settings and link .env, as for master lanes."""
    scan = _util.hooklib(main, "_scan")
    guide, settings = scan.LOCAL_GUIDE, scan.LOCAL_SETTINGS_DIR
    if (main / guide).exists():
        shutil.copyfile(main / guide, target / guide)
    if (main / settings).is_dir():
        shutil.copytree(main / settings, target / settings, dirs_exist_ok=True)
    (target / ".local" / "prompts").mkdir(parents=True, exist_ok=True)
    env = target / ".env"
    if not env.exists() and (main / ".env").exists():
        env.symlink_to(main / ".env")


def provision(target, run=subprocess.run, platform=sys.platform):
    """uv sync, then clear the macOS hidden flag on .venv (see RUNBOOK section 7)."""
    run(["uv", "sync"], cwd=target, check=True)
    if platform == "darwin":
        run(["chflags", "-R", "nohidden", ".venv"], cwd=target, check=True)
    run(["uv", "run", "nacre", "setup", "--check"], cwd=target)


def link_venv(target, short, run=subprocess.run, home=None):
    """Make <target>/.venv a symlink to ~/.nacre-venvs/p-<short> (created with uv venv if absent).

    The environment lives outside synced folders (RUNBOOK section 7); `uv sync` then fills it.
    """
    store = Path(home or Path.home()) / ".nacre-venvs" / ("p-" + short)
    if not store.exists():
        store.parent.mkdir(parents=True, exist_ok=True)
        run(["uv", "venv", str(store)], cwd=target, check=True)
    link = Path(target) / ".venv"
    if link.is_symlink() or link.exists():
        return store
    link.symlink_to(store)
    return store


def track_lane_id(track, lane):
    return lane if lane.startswith(track + "-") else "%s-%s" % (track, lane)


def new_track_lane(root, track, lane, base=None, provision_fn=provision):
    """Create <main checkout>-p-<short id> on the lane's track branch from the track base."""
    lib = _util.hooklib(root, "_lanes")
    cfg = lib.load_lanes(str(root))
    spec = (cfg.get("tracks") or {}).get(track)
    if not spec:
        raise SystemExit("REFUSED: track %r is not registered in ops/lanes.yaml" % track)
    lane_id = track_lane_id(track, lane)
    entry = (spec.get("lanes") or {}).get(lane_id)
    if entry is None:
        raise SystemExit("REFUSED: lane %r is not registered in track %s" % (lane_id, track))
    branch = entry.get("branch")
    if not branch or branch == spec.get("base"):
        raise SystemExit("REFUSED: lane %r is the track integrator, not a lane worktree" % lane_id)
    main = main_repo(root)
    short = lane_id[len(track) + 1:]
    target = main.parent / ("%s-p-%s" % (main.name, short))
    if target.exists():
        raise SystemExit("REFUSED: %s already exists" % target)
    _util.git(root, "fetch", "origin", timeout=60)
    if base is None:
        base = "origin/" + spec["base"]
        if _util.git(root, "rev-parse", "-q", "--verify", base + "^{commit}").returncode != 0:
            base = spec["base"]
    if _util.git(root, "rev-parse", "-q", "--verify", base + "^{commit}").returncode != 0:
        raise SystemExit("REFUSED: base %s does not exist" % base)
    if _util.git(root, "rev-parse", "-q", "--verify", "refs/heads/" + branch).returncode == 0:
        raise SystemExit("REFUSED: branch %s already exists" % branch)
    _util.git(root, "worktree", "add", "--no-track", "-b", branch, str(target), base, check=True)
    link_local_files(main, target)
    link_venv(target, short)
    provision_fn(target)
    return target, branch


def _cmd(args):
    root = _util.repo_root()
    if args.track:
        target, branch = new_track_lane(root, args.track, args.lane_id, args.base)
        print("created %s on branch %s" % (target, branch))
        print("code %s" % target)
        return 0
    target = new_lane(root, args.lane_id, args.base or "origin/main")
    print("created %s on branch lane/%s" % (target, args.lane_id))
    print("code %s" % target)
    return 0


def register(subparsers):
    p = subparsers.add_parser("lane", help="lane worktree commands")
    sub = p.add_subparsers(dest="lane_command", metavar="<subcommand>", required=True)
    n = sub.add_parser("new", help="create a worktree and branch for a registered lane")
    n.add_argument("lane_id")
    n.add_argument("--base", default=None,
                   help="base ref (default origin/main; with --track, origin/<track base>)")
    n.add_argument("--track", help="create a lane of this track (see tracks in ops/lanes.yaml)")
    n.set_defaults(func=_cmd)
