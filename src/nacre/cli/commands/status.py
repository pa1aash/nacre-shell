"""nacre status: where this checkout stands."""
from pathlib import Path

from nacre import _util
from nacre.cli.commands import wave

GATE_TAGS = ["g%d" % i for i in range(14)] + ["prereg-v1"]


def last_report(root, state):
    reports = Path(root) / "ops" / "reports"
    if state and state.get("last_session"):
        p = reports / (state["last_session"] + ".md")
        if p.exists():
            return p.relative_to(root)
    files = sorted(reports.glob("*.md"), key=lambda f: f.stat().st_mtime) if reports.exists() else []
    return files[-1].relative_to(root) if files else None


def _cmd(args):
    root = _util.repo_root()
    lib = _util.hooklib(root, "_lanes")
    cfg = lib.load_lanes(str(root))
    branch = _util.current_branch(root)
    lane, err = lib.resolve_lane(branch, cfg)
    print("repo root: %s" % root)
    print("branch: %s" % (branch or "(detached)"))
    if lane:
        print("lane: %s   laptop: %s" % (lane, lib.laptop_of(lane, cfg)))
    else:
        print("lane: unresolved (%s)" % err)
    dirty = _util.git(root, "status", "--porcelain").stdout.strip()
    print("working tree: %s" % ("dirty (%d entries)" % len(dirty.splitlines()) if dirty else "clean"))
    present = [t for t in GATE_TAGS if _util.tag_exists(root, t)]
    print("tags present: %s" % (", ".join(present) if present else "none"))
    state_path = Path(root) / "ops" / "state" / ("%s.json" % lane) if lane else None
    state = _util.read_json(state_path) if state_path else None
    print("state file: %s" % (state_path.relative_to(root) if state is not None else "none"))
    print("last report: %s" % (last_report(root, state) or "none"))
    print("--- nacre wave status")
    print("\n".join(wave.status_lines(root)))
    return 0


def register(subparsers):
    p = subparsers.add_parser("status", help="show repository, lane and wave status")
    p.set_defaults(func=_cmd)
