"""pre-commit: banned strings, identity, lane ownership and frozen paths."""
import os
import sys

import _lanes
import _scan


def main():
    root = _scan.git_out("rev-parse", "--show-toplevel").strip()
    failures = 0
    for problem in _scan.identity_problems():
        _scan.report("identity", "git config", None, problem)
        failures += 1
    failures += _scan.scan_staged()

    cfg = _lanes.load_lanes(root)
    rc, branch = _scan.git("symbolic-ref", "--short", "-q", "HEAD")
    branch = branch.strip() if rc == 0 else None
    lane, err = _lanes.resolve_lane(branch, cfg)
    merge_head = _scan.git_out("rev-parse", "--path-format=absolute", "--git-path", "MERGE_HEAD").strip()
    merging = os.path.exists(merge_head)
    if err:
        _scan.report("branch", branch or "HEAD", None, err)
        failures += 1
    elif not merging:
        for path, reason in _lanes.lane_violations(lane, _scan.staged_paths(), cfg):
            _scan.report("lane-ownership", path, None, "lane %s: %s" % (lane, reason))
            failures += 1

    def tag_exists(tag):
        return _scan.git("rev-parse", "-q", "--verify", "refs/tags/" + tag)[0] == 0

    changes = _lanes.parse_numstat(
        _scan.git_out("diff", "--cached", "--numstat", "-z", "--no-renames"))
    for path, reason in _lanes.frozen_violations(_lanes.load_frozen(root), tag_exists, changes):
        _scan.report("frozen-path", path, None, reason + "; record a dated entry in registration/deviations.md")
        failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
