"""nacre track: the day ledger of a preprint track (ops/tracks/<track>.yaml).

A track runs in days. Exactly one day is open at a time; `open-day` is run by
the integrator on the track base branch and closes the previous day. A session
may run only on its lane branch, in its open day (or as a session carried into
it), on a clean tree that contains the commit that opened the day, with every
checkpoint it requires satisfied. Checkpoint cpN is satisfied by tag <track>-cpN;
cp1 is also satisfied by tag g0.

Freeze rule: the ledger's `freeze:` block (tag, paths) names a tag and path globs. Once the tag exists, a
commit in <tag>..HEAD that modifies, deletes or renames a file existing at the tag under a frozen path fails the check unless <track>_deviations.md carries a dated
entry that names the changed path and the outputs to re-audit ('Re-audit:' line). No block, no rule.
"""
import re

import yaml

from nacre import _util

PASSING = ("DONE", "DONE-PART1", "HOLD-P", "GATE-C", "GATE-H")
CHECKPOINT_ALIASES = {"cp1": ["g0"]}


_ENTRY = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b.*$", re.MULTILINE)


class Blocked(Exception):
    pass


def track_path(root, track):
    return _util.Path(root) / "ops" / "tracks" / (track + ".yaml")


def load_track(root, track):
    path = track_path(root, track)
    if not path.exists():
        raise Blocked("no track ledger %s" % path.relative_to(root))
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def save_track(root, track, data):
    path = track_path(root, track)
    header = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            header.append(line)
        else:
            break
    body = yaml.safe_dump(data, sort_keys=False, default_flow_style=None, width=100, allow_unicode=True)
    path.write_text("\n".join(header) + "\n" + body, encoding="utf-8")


def sessions(data):
    """Every session entry in day order."""
    return [s for d in data.get("days") or [] for s in d.get("sessions") or []]


def find_session(data, session_id):
    for s in sessions(data):
        if s["id"] == session_id:
            return s
    return None


def find_day(data, n):
    return next((d for d in data.get("days") or [] if d.get("day") == n), None)


def open_day(data):
    opened = [d for d in data.get("days") or [] if d.get("status") == "open"]
    if len(opened) != 1:
        raise Blocked("expected exactly one open day, found %d" % len(opened))
    return opened[0]


def lane_branch(data, lane_id):
    for lane in data.get("lanes") or []:
        if lane.get("id") == lane_id:
            return lane.get("branch")
    return None


def base_branch(data):
    return (data.get("meta") or {}).get("base")


def checkpoint_tags(track, cp):
    return ["%s-%s" % (track, cp)] + CHECKPOINT_ALIASES.get(cp, [])


def checkpoint_satisfied(root, track, cp):
    """The tag that satisfies checkpoint cp, or None."""
    return next((t for t in checkpoint_tags(track, cp) if _util.tag_exists(root, t)), None)


def read_state(root, lane_id):
    return _util.read_json(_util.Path(root) / "ops" / "state" / (lane_id + ".json"))


def session_status(data, session, state):
    """The status a session has reached given its lane state, or None if not reached.

    A session listed in the ledger's top-level `done:` list is DONE whatever the lane state says: the integrator
    records a session there when its lane state moved past it to a session the ledger does not list.
    """
    if session["id"] in (data.get("done") or []):
        return "DONE"
    order = [s["id"] for s in sessions(data) if s["lane"] == session["lane"]]
    last = (state or {}).get("last_session")
    if last not in order:
        return None
    if order.index(last) > order.index(session["id"]):
        return "DONE"
    if last == session["id"]:
        return state.get("status")
    return None


def deviation_entries(root, track):
    """[(date, block text)] for the dated '## YYYY-MM-DD ...' entries of ops/tracks/<track>_deviations.md."""
    path = _util.Path(root) / "ops" / "tracks" / (track + "_deviations.md")
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    marks = list(_ENTRY.finditer(text))
    out = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out.append((m.group(1), text[m.start():end]))
    return out


def freeze_rule(root, track):
    """(tag, paths) of the ledger's freeze block, or None."""
    try:
        block = load_track(root, track).get("freeze") or {}
    except Blocked:
        return None
    tag, paths = block.get("tag"), list(block.get("paths") or [])
    return (tag, paths) if tag and paths else None


def freeze_problems(root, track):
    """Frozen paths changed by commits in <tag>..HEAD without a covering deviation entry."""
    rule = freeze_rule(root, track)
    if rule is None or not _util.tag_exists(root, rule[0]):
        return []
    tag, paths = rule
    # Commits reachable from HEAD but not from the tag: a branch behind the tag, or one fast-forwarded to it,
    # has none, and a tree diff against the tag would wrongly report the tag's own later changes.
    # Only a modification, deletion or rename (shown as a deletion of the old path) of a file that exists at
    # the tag counts; added files never do.
    names = _util.git(root, "log", "--name-only", "--diff-filter=MD", "--format=", "-z", "--no-renames",
                      tag + "..HEAD", "--", *[":(glob)" + g for g in paths])
    changed = sorted({p for p in names.stdout.split("\0") if p.strip()
                      and _util.git(root, "cat-file", "-e", "%s:%s" % (tag, p)).returncode == 0})
    if not changed:
        return []
    since = _util.git(root, "log", "-1", "--format=%cs", tag).stdout.strip()
    entries = [(d, block) for d, block in deviation_entries(root, track) if d >= since]
    problems = []
    for path in changed:
        covered = any(path in block and re.search(r"(?mi)^\s*re-?audit:\s*\S", block) for _, block in entries)
        if not covered:
            problems.append(path)
    return problems


def day_open_commit(root, track, data, day, ref):
    """The latest commit on `ref` that opened `day` (day 0: the commit adding the ledger)."""
    if day == 0:
        rel = "ops/tracks/%s.yaml" % track
        out = _util.git(root, "log", "--diff-filter=A", "--format=%H", ref, "--", rel).stdout.split()
        return out[-1] if out else None
    subject = "ops(%s): open day %d" % (track, day)
    out = _util.git(root, "log", "--format=%H%x00%s", ref).stdout
    for line in out.splitlines():
        sha, _, subj = line.partition("\0")
        if subj == subject:
            return sha
    return None


def check(root, track, session_id):
    """Raise Blocked unless the session may run now; return (session, current day)."""
    data = load_track(root, track)
    session = find_session(data, session_id)
    if session is None:
        raise Blocked("session %s is not listed in track %s" % (session_id, track))
    current = open_day(data)
    carried = current.get("carried") or []
    if session["day"] != current["day"] and session_id not in carried:
        raise Blocked("session %s belongs to day %s, but day %s is open"
                      % (session_id, session["day"], current["day"]))
    want = lane_branch(data, session["lane"])
    branch = _util.current_branch(root)
    if branch != want:
        raise Blocked("session %s runs on branch %s, current branch is %s" % (session_id, want, branch))
    if _util.git(root, "status", "--porcelain").stdout.strip():
        raise Blocked("the working tree is not clean")
    base = base_branch(data)
    _util.git(root, "fetch", "origin", timeout=60)
    ref = "origin/" + base
    if _util.git(root, "rev-parse", "-q", "--verify", ref + "^{commit}").returncode != 0:
        raise Blocked("%s does not exist" % ref)
    opener = day_open_commit(root, track, data, current["day"], ref)
    if opener is None:
        raise Blocked("no commit on %s opened day %s" % (ref, current["day"]))
    if _util.git(root, "merge-base", "--is-ancestor", opener, "HEAD").returncode != 0:
        raise Blocked("HEAD does not contain %s, the commit that opened day %s" % (opener[:12], current["day"]))
    missing = [cp for cp in session.get("requires") or [] if not checkpoint_satisfied(root, track, cp)]
    if missing:
        raise Blocked("required checkpoints not satisfied: %s (tags %s)" % (
            ", ".join(missing), ", ".join(" or ".join(checkpoint_tags(track, cp)) for cp in missing)))
    frozen = freeze_problems(root, track)
    if frozen:
        raise Blocked("frozen since %s and changed without a dated entry in ops/tracks/%s_deviations.md "
                      "naming the change and a 'Re-audit:' line: %s" % (freeze_rule(root, track)[0], track, ", ".join(frozen)))
    return session, current


def open_next_day(root, track, n, carry=()):
    """Close the open day n-1 and open day n; commit the ledger. Integrator only."""
    data = load_track(root, track)
    base = base_branch(data)
    branch = _util.current_branch(root)
    if branch != base:
        raise Blocked("open-day runs on the track base %s (integrator), current branch is %s" % (base, branch))
    if _util.git(root, "status", "--porcelain").stdout.strip():
        raise Blocked("the working tree is not clean")
    target = find_day(data, n)
    if target is None:
        raise Blocked("day %d is not in the track ledger" % n)
    if target.get("status") != "pending":
        raise Blocked("day %d is already %s" % (n, target.get("status")))
    prev = find_day(data, n - 1)
    if prev is None or prev.get("status") != "open":
        raise Blocked("day %d is not the open day" % (n - 1))
    prev_ids = [s["id"] for s in prev.get("sessions") or []] + list(prev.get("carried") or [])
    unknown = [c for c in carry if c not in prev_ids]
    if unknown:
        raise Blocked("cannot carry %s: not a day %d session" % (", ".join(unknown), n - 1))
    problems = []
    for sid in prev_ids:
        if sid in carry:
            continue
        session = find_session(data, sid)
        status = session_status(data, session, read_state(root, session["lane"]))
        if status not in PASSING:
            problems.append("%s is %s" % (sid, status or "not run"))
    if problems:
        raise Blocked("day %d is not complete: %s (finish them or pass --carry)" % (n - 1, "; ".join(problems)))
    now = _util.utc_now()
    prev["status"] = "closed"
    prev["closed_utc"] = now
    target["status"] = "open"
    target["opened_utc"] = now
    target["carried"] = list(carry)
    save_track(root, track, data)
    rel = "ops/tracks/%s.yaml" % track
    _util.git(root, "add", rel, check=True)
    _util.git(root, "commit", "-q", "-m", "ops(%s): open day %d" % (track, n), "--", rel, check=True)
    return target


def status_lines(root, track):
    try:
        data = load_track(root, track)
    except Blocked as exc:
        return ["track ledger: unavailable (%s)" % exc]
    meta = data.get("meta") or {}
    lines = ["track %s: %s" % (track, meta.get("title_working", "")),
             "venue %s, base %s" % (meta.get("venue"), meta.get("base")), "days:"]
    for d in data.get("days") or []:
        extra = " (carried in: %s)" % ", ".join(d["carried"]) if d.get("carried") else ""
        lines.append("  day %s: %s%s" % (d["day"], d.get("status"), extra))
        for s in d.get("sessions") or []:
            st = session_status(data, s, read_state(root, s["lane"])) or "pending"
            req = " requires %s" % ",".join(s["requires"]) if s.get("requires") else ""
            lines.append("    %s (lane %s, %s): %s%s" % (s["id"], s["lane"], s.get("model"), st, req))
    lines.append("lanes:")
    for lane in data.get("lanes") or []:
        st = read_state(root, lane["id"])
        lines.append("  %s on %s: %s" % (lane["id"], lane.get("branch"), "%s (last %s)" % (
            st.get("status"), st.get("last_session")) if st else "no state file"))
    lines.append("checkpoints:")
    for cp in data.get("checkpoints") or []:
        tag = checkpoint_satisfied(root, track, cp["id"])
        lines.append("  %s day %s %s: %s" % (cp["id"], cp.get("day"), cp.get("title"),
                                             "satisfied by %s" % tag if tag else "open"))
    lines.append("inputs:")
    for key, val in (data.get("inputs") or {}).items():
        if isinstance(val, dict):
            val = ", ".join("%s=%s" % kv for kv in val.items())
        lines.append("  %s: %s" % (key, val))
    return lines


def _cmd_check(args):
    root = _util.repo_root()
    try:
        session, day = check(root, args.track, args.session)
    except Blocked as exc:
        print("BLOCKED: %s" % exc)
        return 1
    print("OK: %s on day %s, lane %s" % (session["id"], day["day"], session["lane"]))
    return 0


def _cmd_status(args):
    print("\n".join(status_lines(_util.repo_root(), args.track)))
    return 0


def _cmd_open_day(args):
    root = _util.repo_root()
    try:
        day = open_next_day(root, args.track, args.n, args.carry or [])
    except Blocked as exc:
        print("BLOCKED: %s" % exc)
        return 1
    carried = " carrying %s" % ", ".join(day["carried"]) if day["carried"] else ""
    print("opened day %d of track %s%s" % (args.n, args.track, carried))
    return 0


def register(subparsers):
    p = subparsers.add_parser("track", help="preprint track day ledger")
    p.add_argument("--track", default="p0", help="track id (default p0)")
    sub = p.add_subparsers(dest="track_command", metavar="<subcommand>", required=True)
    c = sub.add_parser("check", help="check that a track session may run now")
    c.add_argument("session")
    c.set_defaults(func=_cmd_check)
    s = sub.add_parser("status", help="days, sessions, lanes, checkpoints and inputs")
    s.set_defaults(func=_cmd_status)
    o = sub.add_parser("open-day", help="close day N-1 and open day N (integrator, on the track base)")
    o.add_argument("n", type=int)
    o.add_argument("--carry", action="append", metavar="SESSION",
                   help="a day N-1 session to carry into day N unfinished (repeatable)")
    o.set_defaults(func=_cmd_open_day)
