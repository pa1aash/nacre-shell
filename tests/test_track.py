"""nacre track: check, open-day and status against a scratch repo with an origin."""
import json

import pytest
import yaml

from conftest import git, init_repo
from nacre.cli.commands import track

HEADER = "# Track ledger (scratch).\n"


def ledger():
    def s(sid, lane, day, requires=()):
        return {"id": sid, "lane": lane, "day": day, "model": "m", "master_trace": "none",
                "requires": list(requires)}
    return {
        "meta": {"title_working": "scratch", "venue": "V", "base": "preprint/p0"},
        "lanes": [{"id": "p0-w1", "branch": "preprint/p0-w1"}, {"id": "p0-w2", "branch": "preprint/p0-w2"},
                  {"id": "p0-int", "branch": "preprint/p0"}],
        "days": [
            {"day": 0, "status": "open", "opened_utc": None, "closed_utc": None, "carried": [],
             "sessions": [s("P0-I0", "p0-int", 0)]},
            {"day": 1, "status": "pending", "opened_utc": None, "closed_utc": None, "carried": [],
             "sessions": [s("P0-W1.1", "p0-w1", 1), s("P0-W2.1", "p0-w2", 1, ["cp1"]), s("P0-I1", "p0-int", 1)]},
            {"day": 2, "status": "pending", "opened_utc": None, "closed_utc": None, "carried": [],
             "sessions": [s("P0-W1.2", "p0-w1", 2, ["cp2"]), s("P0-I2", "p0-int", 2)]},
        ],
        "checkpoints": [{"id": "cp1", "day": 0, "title": "G0 science", "packet": "ops/packets/p0-1.md"},
                        {"id": "cp2", "day": 2, "title": "equations", "packet": "ops/packets/p0-2.md"}],
        "inputs": {"mp_key": "absent"},
    }


def commit_all(repo, msg="scratch: change"):
    git(repo, "add", "-A")
    assert git(repo, "commit", "-q", "--no-verify", "-m", msg).returncode == 0


def put_state(repo, lane, last, status):
    p = repo / "ops" / "state" / (lane + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"last_session": last, "status": status, "day": 1}))


@pytest.fixture
def repo(tmp_path):
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    r = init_repo(tmp_path / "r", copy_ops=False)
    (r / "README.md").write_text("x\n")
    commit_all(r, "scratch: init")
    git(r, "remote", "add", "origin", str(origin))
    git(r, "checkout", "-q", "-b", "preprint/p0")
    (r / "ops" / "tracks").mkdir(parents=True)
    (r / "ops" / "tracks" / "p0.yaml").write_text(HEADER + yaml.safe_dump(ledger(), sort_keys=False))
    put_state(r, "p0-int", None, "READY")
    commit_all(r, "scratch: add track ledger")
    git(r, "push", "-q", "origin", "preprint/p0")
    return r


def blocked(fn, *a, **k):
    with pytest.raises(track.Blocked) as exc:
        fn(*a, **k)
    return str(exc.value)


def open_day1(repo, carry=("P0-I0",)):
    track.open_next_day(repo, "p0", 1, carry)
    git(repo, "push", "-q", "origin", "preprint/p0")


def lane_branch(repo, name, start="preprint/p0"):
    git(repo, "checkout", "-q", "-b", name, start)


# --- check ----------------------------------------------------------------------

def test_check_passes_for_integrator_on_day0(repo):
    s, day = track.check(repo, "p0", "P0-I0")
    assert s["lane"] == "p0-int" and day["day"] == 0


def test_check_passes_for_lane_session(repo):
    open_day1(repo)
    lane_branch(repo, "preprint/p0-w1")
    s, day = track.check(repo, "p0", "P0-W1.1")
    assert s["lane"] == "p0-w1" and day["day"] == 1


def test_check_refuses_unlisted(repo):
    assert "not listed" in blocked(track.check, repo, "p0", "P0-W9.1")


def test_check_refuses_day_not_open(repo):
    lane_branch(repo, "preprint/p0-w1")
    assert "belongs to day 1, but day 0 is open" in blocked(track.check, repo, "p0", "P0-W1.1")


def test_check_admits_carried_session(repo):
    open_day1(repo)
    s, day = track.check(repo, "p0", "P0-I0")
    assert day["day"] == 1


def test_check_refuses_wrong_branch(repo):
    lane_branch(repo, "preprint/p0-w1")
    assert "runs on branch preprint/p0" in blocked(track.check, repo, "p0", "P0-I0")


def test_check_refuses_dirty_tree(repo):
    (repo / "README.md").write_text("dirty\n")
    assert "not clean" in blocked(track.check, repo, "p0", "P0-I0")


def test_check_refuses_without_origin_base(repo):
    git(repo, "push", "-q", "origin", "--delete", "preprint/p0")
    git(repo, "update-ref", "-d", "refs/remotes/origin/preprint/p0")
    assert "origin/preprint/p0 does not exist" in blocked(track.check, repo, "p0", "P0-I0")


def test_check_refuses_branch_missing_day_opener(repo):
    before = git(repo, "rev-parse", "HEAD").stdout.strip()
    open_day1(repo)
    lane_branch(repo, "preprint/p0-w1", before)
    # the ledger in this stale branch still shows day 0 open; give it the new ledger
    git(repo, "checkout", "-q", "preprint/p0", "--", "ops/tracks/p0.yaml")
    commit_all(repo, "scratch: copy ledger")
    assert "does not contain" in blocked(track.check, repo, "p0", "P0-W1.1")


def test_check_refuses_missing_checkpoint_and_accepts_tags(repo):
    open_day1(repo)
    lane_branch(repo, "preprint/p0-w2")
    msg = blocked(track.check, repo, "p0", "P0-W2.1")
    assert "cp1" in msg and "p0-cp1 or g0" in msg
    git(repo, "tag", "g0")
    assert track.check(repo, "p0", "P0-W2.1")[0]["id"] == "P0-W2.1"
    git(repo, "tag", "-d", "g0")
    git(repo, "tag", "p0-cp1")
    assert track.check(repo, "p0", "P0-W2.1")[0]["id"] == "P0-W2.1"


def test_only_cp1_has_the_g0_alias(repo):
    git(repo, "tag", "g0")
    assert track.checkpoint_satisfied(repo, "p0", "cp1") == "g0"
    assert track.checkpoint_satisfied(repo, "p0", "cp2") is None


# --- open-day -------------------------------------------------------------------

def test_open_day_refuses_off_base(repo):
    lane_branch(repo, "preprint/p0-w1")
    assert "runs on the track base" in blocked(track.open_next_day, repo, "p0", 1, ["P0-I0"])


def test_open_day_refuses_dirty_tree(repo):
    (repo / "README.md").write_text("dirty\n")
    assert "not clean" in blocked(track.open_next_day, repo, "p0", 1, ["P0-I0"])


def test_open_day_refuses_unknown_day(repo):
    assert "not in the track ledger" in blocked(track.open_next_day, repo, "p0", 9)


def test_open_day_refuses_already_open(repo):
    assert "already open" in blocked(track.open_next_day, repo, "p0", 0)


def test_open_day_refuses_skipping_a_day(repo):
    assert "day 1 is not the open day" in blocked(track.open_next_day, repo, "p0", 2)


def test_open_day_refuses_unfinished_session(repo):
    msg = blocked(track.open_next_day, repo, "p0", 1)
    assert "P0-I0 is not run" in msg and "--carry" in msg
    put_state(repo, "p0-int", "P0-I0", "HOLD-X")
    commit_all(repo)
    assert "P0-I0 is HOLD-X" in blocked(track.open_next_day, repo, "p0", 1)


def test_open_day_refuses_unknown_carry(repo):
    assert "cannot carry P0-W1.1" in blocked(track.open_next_day, repo, "p0", 1, ["P0-I0", "P0-W1.1"])


@pytest.mark.parametrize("status", track.PASSING)
def test_open_day_accepts_passing_statuses(repo, status):
    put_state(repo, "p0-int", "P0-I0", status)
    commit_all(repo)
    day = track.open_next_day(repo, "p0", 1)
    assert day["status"] == "open" and day["carried"] == []


def test_open_day_carry_records_and_commits(repo):
    track.open_next_day(repo, "p0", 1, ["P0-I0"])
    data = track.load_track(repo, "p0")
    assert track.find_day(data, 0)["status"] == "closed" and track.find_day(data, 0)["closed_utc"]
    assert track.find_day(data, 1)["carried"] == ["P0-I0"]
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "ops(p0): open day 1"
    assert git(repo, "status", "--porcelain").stdout == ""
    assert (repo / "ops" / "tracks" / "p0.yaml").read_text().startswith(HEADER)


def test_open_day_needs_carried_sessions_finished_later(repo):
    open_day1(repo)
    for lane, last in (("p0-w1", "P0-W1.1"), ("p0-w2", "P0-W2.1"), ("p0-int", "P0-I1")):
        put_state(repo, lane, last, "DONE")
    commit_all(repo)
    day = track.open_next_day(repo, "p0", 2)
    assert day["day"] == 2


def test_later_session_implies_earlier_done(repo):
    data = ledger()
    s = track.find_session(data, "P0-W1.1")
    assert track.session_status(data, s, {"last_session": "P0-W1.2", "status": "HOLD-X"}) == "DONE"
    assert track.session_status(data, s, {"last_session": "P0-W1.1", "status": "HOLD-X"}) == "HOLD-X"
    assert track.session_status(data, s, {"last_session": None, "status": "READY"}) is None


# --- status ---------------------------------------------------------------------

def test_status_lines(repo):
    git(repo, "tag", "g0")
    text = "\n".join(track.status_lines(repo, "p0"))
    assert "day 0: open" in text and "P0-W2.1 (lane p0-w2, m): pending requires cp1" in text
    assert "cp1 day 0 G0 science: satisfied by g0" in text and "cp2 day 2 equations: open" in text
    assert "p0-int on preprint/p0: READY (last None)" in text and "p0-w1 on preprint/p0-w1: no state file" in text
    assert "mp_key: absent" in text


def test_track_command_is_discovered():
    from nacre.cli import build_parser
    parser = build_parser()
    for cmd in (["track", "status"], ["track", "check", "P0-I0"], ["track", "open-day", "1", "--carry", "P0-I0"]):
        assert parser.parse_args(cmd).func is not None
