"""nacre lane: create worktrees for registered lanes."""
import shutil
import subprocess
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


def _cmd(args):
    root = _util.repo_root()
    target = new_lane(root, args.lane_id, args.base)
    print("created %s on branch lane/%s" % (target, args.lane_id))
    print("code %s" % target)
    return 0


def register(subparsers):
    p = subparsers.add_parser("lane", help="lane worktree commands")
    sub = p.add_subparsers(dest="lane_command", metavar="<subcommand>", required=True)
    n = sub.add_parser("new", help="create a worktree and branch for a registered lane")
    n.add_argument("lane_id")
    n.add_argument("--base", default="origin/main", help="base ref (default origin/main)")
    n.set_defaults(func=_cmd)
