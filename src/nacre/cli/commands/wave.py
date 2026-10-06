"""nacre wave: the wave ledger that keeps the two laptops in lock-step."""
import re

import yaml

from nacre import _util


class Blocked(Exception):
    pass


INTEGRATION_RE = re.compile(r"^I(\d+)$")


def waves_path(root):
    return _util.Path(root) / "ops" / "waves.yaml"


def load_waves(root):
    data = yaml.safe_load(waves_path(root).read_text(encoding="utf-8")) or {}
    return data.get("waves") or []


def save_waves(root, waves):
    path = waves_path(root)
    header = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            header.append(line)
        else:
            break
    body = yaml.safe_dump({"waves": waves}, sort_keys=False, default_flow_style=None, width=100)
    path.write_text("\n".join(header) + "\n" + body, encoding="utf-8")


def open_wave(waves):
    opened = [w for w in waves if w.get("status") == "open"]
    if len(opened) != 1:
        raise Blocked("expected exactly one open wave, found %d" % len(opened))
    return opened[0]


def lane_branch(lane):
    return "main" if lane == "a-main" else "lane/" + lane


def window_order(wave, session):
    """(window, ordered sessions of that window) for a session, or (None, [])."""
    for window, sessions in (wave.get("sessions") or {}).items():
        if session in sessions:
            return window, list(sessions)
    return None, []


def check_integration(root, n):
    """Raise Blocked unless integration session I<n> may run now.

    Passes iff: current branch is main; wave n is the single open wave;
    local main equals origin/main after a fetch.
    """
    branch = _util.current_branch(root)
    if branch != "main":
        raise Blocked("integration session I%d runs on main, current branch is %s" % (n, branch))
    waves = load_waves(root)
    wave = open_wave(waves)
    if wave["wave"] != n:
        raise Blocked("integration session I%d requires wave %d to be open, open wave is %d" % (n, n, wave["wave"]))
    _util.git(root, "fetch", "origin", timeout=60)
    local = _util.git(root, "rev-parse", "main", check=True).stdout.strip()
    remote = _util.git(root, "rev-parse", "origin/main", check=True).stdout.strip()
    if local != remote:
        raise Blocked("local main %s does not equal origin/main %s" % (local, remote))
    return wave, "a-main"


def check(root, session):
    """Raise Blocked unless `session` may run now."""
    m = INTEGRATION_RE.match(session)
    if m:
        return check_integration(root, int(m.group(1)))
    waves = load_waves(root)
    wave = open_wave(waves)
    window, _ = window_order(wave, session)
    if window is None:
        raise Blocked("session %s is not listed in open wave %s" % (session, wave["wave"]))
    lane = (wave.get("lanes") or {}).get(session)
    if not lane:
        raise Blocked("session %s has no lane in wave %s" % (session, wave["wave"]))
    want = lane_branch(lane)
    branch = _util.current_branch(root)
    if branch != want:
        raise Blocked("session %s runs on branch %s, current branch is %s" % (session, want, branch))
    base = wave.get("base")
    if base:
        _util.git(root, "fetch", "origin", timeout=60)
        rc = _util.git(root, "merge-base", "--is-ancestor", base, "HEAD").returncode
        if rc != 0:
            raise Blocked("HEAD does not contain the wave base commit %s" % base)
    for tag in wave.get("required_tags") or []:
        if not _util.tag_exists(root, tag):
            raise Blocked("required tag %s is missing" % tag)
    return wave, lane


def read_lane_state(root, lane):
    """The lane state file from the working tree, else from origin/lane/<lane>."""
    st = _util.read_json(_util.Path(root) / "ops" / "state" / (lane + ".json"))
    if st is not None:
        return st
    ref = "origin/main" if lane == "a-main" else "origin/lane/" + lane
    p = _util.git(root, "show", "%s:ops/state/%s.json" % (ref, lane))
    if p.returncode == 0:
        import json
        try:
            return json.loads(p.stdout)
        except ValueError:
            return None
    return None


def session_state(wave, session, state):
    """pending | running(<status>) | DONE for one session given its lane state."""
    _, order = window_order(wave, session)
    last = (state or {}).get("last_session")
    if not state or last not in order:
        return "pending"
    if order.index(last) > order.index(session):
        return "DONE"
    if last == session:
        return "DONE" if state.get("status") == "DONE" else "running(%s)" % state.get("status")
    return "pending"


def status_lines(root):
    try:
        waves = load_waves(root)
        wave = open_wave(waves)
    except (OSError, Blocked) as exc:
        return ["wave ledger: unavailable (%s)" % exc]
    lines = ["wave %s open, base %s" % (wave["wave"], wave.get("base") or "null")]
    missing = []
    lanes = wave.get("lanes") or {}
    for window, sessions in (wave.get("sessions") or {}).items():
        for s in sessions:
            lane = lanes.get(s, "?")
            st = session_state(wave, s, read_lane_state(root, lane))
            lines.append("  %s %s (lane %s): %s" % (window, s, lane, st))
            if st != "DONE":
                missing.append("%s (lane %s) is %s" % (s, lane, st))
    lines.append("missing before close: " + ("; ".join(missing) if missing else "nothing"))
    return lines


def previous_wave_problems(root, prev):
    """Reasons wave `prev` cannot be closed yet."""
    problems = []
    lanes = prev.get("lanes") or {}
    for window, sessions in (prev.get("sessions") or {}).items():
        for s in sessions:
            lane = lanes.get(s)
            if not lane:
                problems.append("%s has no lane" % s)
                continue
            path = _util.Path(root) / "ops" / "state" / (lane + ".json")
            st = _util.read_json(path)
            if st is None:
                problems.append("ops/state/%s.json is missing on main (session %s)" % (lane, s))
                continue
            final = [x for x in sessions if lanes.get(x) == lane][-1]
            if st.get("last_session") != final:
                problems.append("lane %s last_session is %s, expected %s" % (lane, st.get("last_session"), final))
            elif st.get("status") != "DONE":
                problems.append("lane %s status is %s, expected DONE" % (lane, st.get("status")))
    return problems


def open_next(root, n, base, tags, sessions, lanes):
    if _util.current_branch(root) != "main":
        raise Blocked("wave open runs on main only")
    waves = load_waves(root)
    if any(w["wave"] == n for w in waves):
        raise Blocked("wave %d already exists" % n)
    prev = next((w for w in waves if w["wave"] == n - 1), None)
    if prev is None:
        raise Blocked("wave %d does not exist" % (n - 1))
    problems = previous_wave_problems(root, prev)
    if problems:
        raise Blocked("wave %d is not complete: %s" % (n - 1, "; ".join(problems)))
    lib = _util.hooklib(root, "_lanes")
    cfg = lib.load_lanes(str(root))
    for s, lane in lanes.items():
        if lib.lane_entry(cfg, lane) is None:
            raise Blocked("lane %s (session %s) is not registered in ops/lanes.yaml" % (lane, s))
    for window, ss in sessions.items():
        for s in ss:
            if s not in lanes:
                raise Blocked("session %s has no lane" % s)
    from nacre.cli.commands import verify
    failed = [r for r in verify.run_checks(root) if r["status"] == "FAIL"]
    if failed:
        raise Blocked("nacre verify fails: " + ", ".join(r["name"] for r in failed))
    full = _util.git(root, "rev-parse", "--verify", base + "^{commit}")
    if full.returncode != 0:
        raise Blocked("base %s is not a commit" % base)
    now = _util.utc_now()
    prev["status"] = "closed"
    prev["closed_utc"] = now
    waves.append({"wave": n, "base": full.stdout.strip(), "required_tags": list(tags),
                  "sessions": sessions, "lanes": lanes, "status": "open",
                  "opened_utc": now, "closed_utc": None})
    save_waves(root, waves)
    _util.git(root, "add", "ops/waves.yaml", check=True)
    _util.git(root, "commit", "-m", "ops(wave): open wave %d" % n, "--", "ops/waves.yaml", check=True)
    return waves[-1]


def _kv(items, split_values):
    out = {}
    for item in items or []:
        key, _, val = item.partition("=")
        out[key] = [v for v in val.split(",") if v] if split_values else val
    return out


def _cmd_check(args):
    root = _util.repo_root()
    try:
        wave, lane = check(root, args.session)
    except Blocked as exc:
        print("BLOCKED: %s" % exc)
        return 1
    print("OK: %s in wave %s, lane %s" % (args.session, wave["wave"], lane))
    return 0


def _cmd_open(args):
    root = _util.repo_root()
    try:
        base = args.base or _util.git(root, "rev-parse", "HEAD", check=True).stdout.strip()
        wave = open_next(root, args.n, base, args.tags or [], _kv(args.sessions, True), _kv(args.lanes, False))
    except Blocked as exc:
        print("BLOCKED: %s" % exc)
        return 1
    print("opened wave %d at base %s" % (wave["wave"], wave["base"]))
    return 0


def _cmd_status(args):
    print("\n".join(status_lines(_util.repo_root())))
    return 0


def register(subparsers):
    p = subparsers.add_parser("wave", help="wave ledger commands")
    sub = p.add_subparsers(dest="wave_command", metavar="<subcommand>", required=True)
    c = sub.add_parser("check", help="check that a session may run now")
    c.add_argument("session")
    c.set_defaults(func=_cmd_check)
    o = sub.add_parser("open", help="close the previous wave and open wave N (main only)")
    o.add_argument("n", type=int)
    o.add_argument("--base", help="full sha the wave starts from (default HEAD)")
    o.add_argument("--tags", nargs="*", default=[], help="required tags")
    o.add_argument("--sessions", nargs="+", metavar="WINDOW=S1,S2", required=True)
    o.add_argument("--lanes", nargs="+", metavar="SESSION=LANE", required=True)
    o.set_defaults(func=_cmd_open)
    s = sub.add_parser("status", help="show the open wave and session states")
    s.set_defaults(func=_cmd_status)
