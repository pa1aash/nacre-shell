"""Lane ownership and frozen-path matcher (see ops/lanes.yaml, ops/frozen.yaml).

Used by the hooks and by `nacre verify`. Needs pyyaml; otherwise standard library.
"""
import functools
import os
import re

import yaml


@functools.lru_cache(maxsize=None)
def _regex(pattern):
    out, i, n = [], 0, len(pattern)
    while i < n:
        c = pattern[i]
        if c == "*":
            if pattern[i:i + 3] == "**/":
                out.append("(?:.*/)?")
                i += 3
                continue
            if pattern[i:i + 2] == "**":
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def glob_match(pattern, path):
    return _regex(pattern).match(path) is not None


def matches(path, patterns):
    return any(glob_match(p, path) for p in (patterns or []))


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_lanes(root):
    return load_yaml(os.path.join(root, "ops", "lanes.yaml"))


def lane_entry(cfg, lane_id):
    """The registry entry for a lane (exact key first, then wildcard keys)."""
    lanes = cfg.get("lanes") or {}
    if lane_id in lanes:
        return lanes[lane_id] or {}
    for key, val in lanes.items():
        if "*" in key and glob_match(key, lane_id):
            return val or {}
    return None


def laptop_of(lane_id, cfg):
    for name, spec in (cfg.get("laptops") or {}).items():
        if lane_id.startswith(spec["prefix"]):
            return name
    return None


# --- tracks -----------------------------------------------------------------

def track_lane(cfg, lane_id):
    """(track name, track spec, lane entry) for a track lane, else None.

    A lane registered in the master `lanes` map is never a track lane.
    """
    if lane_entry(cfg, lane_id) is not None:
        return None
    for name, track in (cfg.get("tracks") or {}).items():
        lanes = (track or {}).get("lanes") or {}
        if lane_id in lanes:
            return name, track, lanes[lane_id] or {}
    return None


def track_of_branch(cfg, branch):
    """(track name, lane id) whose registered branch is `branch`, else None."""
    for name, track in (cfg.get("tracks") or {}).items():
        for lane_id, entry in ((track or {}).get("lanes") or {}).items():
            if (entry or {}).get("branch") == branch:
                return name, lane_id
    return None


def is_integrator(cfg, lane_id):
    """True for the lane whose branch is its track's base branch."""
    tl = track_lane(cfg, lane_id)
    return bool(tl) and tl[2].get("branch") == tl[1].get("base")


def _check_track_path(lane, path, track, entry):
    own = [p.format(lane=lane, LANE=lane.upper()) for p in track.get("carveouts") or []]
    if matches(path, own):
        return True, "track carve-out"
    if matches(path, track.get("shared")):
        return True, "shared path"
    if matches(path, entry.get("owns")) and not matches(path, entry.get("except")):
        return True, "owned by lane " + lane
    return False, "outside the ownership list of lane " + lane


def resolve_lane(branch, cfg):
    """Map a branch name to (lane_id, error). Exactly one of them is None."""
    if not branch:
        return None, "detached HEAD is not a lane branch"
    if branch == "main":
        return "a-main", None
    found = track_of_branch(cfg, branch)
    if found:
        return found[1], None
    if branch.startswith("preprint/"):
        return None, "branch %r is not registered by any track in ops/lanes.yaml" % branch
    if branch.startswith("lane/"):
        lane = branch[len("lane/"):]
        if laptop_of(lane, cfg) is None:
            return None, "lane id %r has no laptop prefix" % lane
        entry = lane_entry(cfg, lane)
        if entry is None:
            return None, "lane %r is not registered in ops/lanes.yaml" % lane
        if entry.get("branch") and entry["branch"] != branch:
            return None, "lane %r lives on branch %r" % (lane, entry["branch"])
        return lane, None
    return None, "branch %r is neither main nor lane/<id>" % branch


def b_owned(path, cfg):
    spec = (cfg.get("laptops") or {}).get("B", {})
    return matches(path, spec.get("owns")) and not matches(path, spec.get("except"))


def check_path(lane, path, cfg, merge=False):
    """Return (allowed, reason) for a lane writing a repo-relative path."""
    path = path.replace("\\", "/")
    tl = track_lane(cfg, lane)
    if tl:
        return _check_track_path(lane, path, tl[1], tl[2])
    entry = lane_entry(cfg, lane)
    laptop = laptop_of(lane, cfg)
    if entry is None or laptop is None:
        return False, "lane %r is not registered" % lane
    carve = cfg.get("carveouts") or {}
    own = [p.format(lane=lane) for p in carve.get("per_lane", [])]
    if path in own or matches(path, carve.get("any")):
        return True, "carve-out"
    if matches(path, cfg.get("main_only")):
        if lane == "a-main":
            return True, "main-only path, written on main"
        return False, "writable only on main (lane a-main)"
    if matches(path, cfg.get("shared")):
        return True, "shared path"
    if laptop == "A" and matches(path, cfg.get("a_laptop_extra")):
        return True, "Laptop A gate/packet path"
    if entry.get("owns") is not None:
        if matches(path, entry["owns"]) and not matches(path, entry.get("except")):
            return True, "owned by lane " + lane
        return False, "outside the ownership list of lane " + lane
    if laptop == "B":
        if b_owned(path, cfg):
            return True, "owned by Laptop B"
        return False, "not owned by Laptop B"
    if not b_owned(path, cfg):
        return True, "owned by Laptop A"
    if entry.get("merge_writes_laptop_b") and merge:
        return True, "Laptop B path written during a merge"
    return False, "owned by Laptop B (writable on main only during a merge)"


def lane_violations(lane, paths, cfg, merge=False):
    out = []
    for path in paths:
        ok, reason = check_path(lane, path, cfg, merge)
        if not ok:
            out.append((path, reason))
    return out


# --- frozen paths -----------------------------------------------------------

def load_frozen(root):
    p = os.path.join(root, "ops", "frozen.yaml")
    return (load_yaml(p).get("rules") or []) if os.path.exists(p) else []


def frozen_violations(rules, tag_exists, changes):
    """changes maps path -> (added, deleted); a deleted of None means unknown.

    A rule applies once its tag exists. Append-only paths accept additions but
    no removed lines.
    """
    out = []
    for rule in rules:
        if not tag_exists(rule["after_tag"]):
            continue
        for path, (_added, deleted) in sorted(changes.items()):
            if not matches(path, rule.get("paths")):
                continue
            if matches(path, rule.get("append_only")) and deleted == 0:
                continue
            out.append((path, "frozen after tag %s" % rule["after_tag"]))
    return out


def parse_numstat(text):
    """Parse `git diff --numstat -z --no-renames` output into a changes dict."""
    changes = {}
    for rec in text.split("\0"):
        if not rec:
            continue
        added, deleted, path = rec.split("\t", 2)
        changes[path] = (
            None if added == "-" else int(added),
            None if deleted == "-" else int(deleted),
        )
    return changes
