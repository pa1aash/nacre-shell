"""nacre track: check, open-day and status against a scratch repo with an origin."""
import json
import re

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
        "freeze": {"tag": "p0-cp3", "paths": ["lit/params.yaml", "configs/preprint/thresholds.yaml",
                                              "theory/thresholds.md"]},
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


def test_done_list_marks_a_session_done_when_the_lane_state_cannot(repo):
    data = ledger()
    s = track.find_session(data, "P0-W1.1")
    state = {"last_session": "P0-W1.1c", "status": "DONE"}
    assert track.session_status(data, s, state) is None
    data["done"] = ["P0-W1.1"]
    assert track.session_status(data, s, state) == "DONE"
    assert track.session_status(data, track.find_session(data, "P0-W1.2"), state) is None


def test_open_day_accepts_a_session_in_the_done_list(repo):
    open_day1(repo)
    data = track.load_track(repo, "p0")
    data["done"] = ["P0-I0", "P0-W1.1", "P0-W2.1", "P0-I1"]
    track.save_track(repo, "p0", data)
    commit_all(repo)
    assert track.open_next_day(repo, "p0", 2)["day"] == 2


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


# --- freeze rule after cp3 -------------------------------------------------------------

FROZEN = ["lit/params.yaml", "configs/preprint/thresholds.yaml", "theory/thresholds.md"]


def _write(repo, files):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)


@pytest.fixture
def frozen_repo(repo):
    _write(repo, {rel: "v1\n" for rel in FROZEN})
    commit_all(repo, "scratch: inputs")
    return repo


def _today():
    import datetime
    return datetime.date.today().isoformat()


def test_freeze_rule_is_inactive_before_cp3(frozen_repo):
    _write(frozen_repo, {"lit/params.yaml": "v2\n"})
    commit_all(frozen_repo)
    assert track.freeze_problems(frozen_repo, "p0") == []
    assert track.check(frozen_repo, "p0", "P0-I0")


def test_freeze_rule_passes_when_nothing_changed_since_cp3(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {"README.md": "other\n"})
    commit_all(frozen_repo)
    assert track.freeze_problems(frozen_repo, "p0") == []


@pytest.mark.parametrize("rel", FROZEN)
def test_freeze_rule_fails_on_each_frozen_input(frozen_repo, rel):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {rel: "v2\n"})
    commit_all(frozen_repo)
    assert track.freeze_problems(frozen_repo, "p0") == [rel]
    msg = blocked(track.check, frozen_repo, "p0", "P0-I0")
    assert "frozen since p0-cp3" in msg and rel in msg


def test_freeze_rule_accepts_a_dated_entry_with_reaudit(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {"lit/params.yaml": "v2\n",
                         "ops/tracks/p0_deviations.md": "# Deviations\n\n## %s lit/params.yaml\nChange: ksp.\nRe-audit: screen, fig5\n" % _today()})
    commit_all(frozen_repo)
    assert track.freeze_problems(frozen_repo, "p0") == []
    assert track.check(frozen_repo, "p0", "P0-I0")


def test_freeze_rule_needs_the_path_the_date_and_the_reaudit_line(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {"lit/params.yaml": "v2\n", "theory/thresholds.md": "v2\n"})
    commit_all(frozen_repo)
    entry = lambda date, body: "# Deviations\n\n## %s x\n%s\n" % (date, body)
    # names only one of the two changed paths
    _write(frozen_repo, {"ops/tracks/p0_deviations.md": entry(_today(), "lit/params.yaml\nRe-audit: screen")})
    assert track.freeze_problems(frozen_repo, "p0") == ["theory/thresholds.md"]
    # no Re-audit line
    _write(frozen_repo, {"ops/tracks/p0_deviations.md": entry(_today(), "lit/params.yaml theory/thresholds.md")})
    assert sorted(track.freeze_problems(frozen_repo, "p0")) == ["lit/params.yaml", "theory/thresholds.md"]
    # empty Re-audit
    _write(frozen_repo, {"ops/tracks/p0_deviations.md": entry(_today(), "lit/params.yaml theory/thresholds.md\nRe-audit:")})
    assert len(track.freeze_problems(frozen_repo, "p0")) == 2
    # dated before the tag
    _write(frozen_repo, {"ops/tracks/p0_deviations.md": entry("2000-01-01", "lit/params.yaml theory/thresholds.md\nRe-audit: all")})
    assert len(track.freeze_problems(frozen_repo, "p0")) == 2
    # a covering entry
    _write(frozen_repo, {"ops/tracks/p0_deviations.md": entry(_today(), "lit/params.yaml theory/thresholds.md\nRe-audit: all")})
    assert track.freeze_problems(frozen_repo, "p0") == []


def test_repo_deviations_file_has_header_and_well_formed_entries():
    from pathlib import Path
    text = (Path(__file__).resolve().parent.parent / "ops" / "tracks" / "p0_deviations.md").read_text()
    assert text.startswith("# Deviations of track p0")
    marks = list(track._ENTRY.finditer(text))
    for i, m in enumerate(marks):
        body = text[m.end():marks[i + 1].start() if i + 1 < len(marks) else len(text)]
        assert re.search(r"(?m)^Re-audit:\s*\S", body), m.group(0)


# --- freeze rule counts only changes to files that exist at the tag ---------------------------

def test_freeze_rule_ignores_a_new_file_under_a_frozen_path(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {"lit/new_phosphate.csv": "a\n", "theory/new_note.md": "b\n"})
    commit_all(frozen_repo, "scratch: add files")
    _write(frozen_repo, {"lit/new_phosphate.csv": "a2\n"})
    commit_all(frozen_repo, "scratch: edit the added file")
    assert track.freeze_problems(frozen_repo, "p0") == []


def test_freeze_rule_modify_needs_reaudit_but_unlisted_path_passes(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    _write(frozen_repo, {"lit/params.yaml": "v2\n", "docs/unlisted.md": "x\n"})
    commit_all(frozen_repo, "scratch: modify")
    assert track.freeze_problems(frozen_repo, "p0") == ["lit/params.yaml"]
    _write(frozen_repo, {"ops/tracks/p0_deviations.md":
                         "# Deviations\n\n## %s lit/params.yaml\nChange: ksp.\nRe-audit: screen\n" % _today()})
    commit_all(frozen_repo, "scratch: deviation")
    assert track.freeze_problems(frozen_repo, "p0") == []


def test_freeze_rule_flags_deletion_and_rename_of_a_tag_file(frozen_repo):
    git(frozen_repo, "tag", "p0-cp3")
    git(frozen_repo, "rm", "-q", "lit/params.yaml")
    git(frozen_repo, "mv", "theory/thresholds.md", "theory/thresholds_old.md")
    commit_all(frozen_repo, "scratch: delete and rename")
    assert track.freeze_problems(frozen_repo, "p0") == ["lit/params.yaml", "theory/thresholds.md"]


# --- freeze rule reads commits since the tag, not the tag's tree -------------------------------

@pytest.fixture
def tagged_after_change(frozen_repo):
    """preprint/p0 has an older commit (inputs v1) and the cp3 tag on a later commit that changed an input."""
    before = git(frozen_repo, "rev-parse", "HEAD").stdout.strip()
    _write(frozen_repo, {"lit/params.yaml": "v2\n"})
    commit_all(frozen_repo, "scratch: table at cp3")
    git(frozen_repo, "tag", "p0-cp3")
    return before


def test_freeze_rule_passes_for_a_branch_behind_the_tag(frozen_repo, tagged_after_change):
    git(frozen_repo, "checkout", "-q", "-b", "preprint/p0-w9", tagged_after_change)
    assert track.freeze_problems(frozen_repo, "p0") == []


def test_freeze_rule_fails_for_a_branch_commit_after_the_tag(frozen_repo, tagged_after_change):
    git(frozen_repo, "checkout", "-q", "-b", "preprint/p0-w9", "p0-cp3")
    _write(frozen_repo, {"lit/params.yaml": "v3\n"})
    commit_all(frozen_repo, "scratch: own change")
    assert track.freeze_problems(frozen_repo, "p0") == ["lit/params.yaml"]
    _write(frozen_repo, {"ops/tracks/p0_deviations.md":
                         "# Deviations\n\n## %s lit/params.yaml\nChange: ksp.\nRe-audit: screen\n" % _today()})
    commit_all(frozen_repo, "scratch: deviation")
    assert track.freeze_problems(frozen_repo, "p0") == []


def test_freeze_rule_passes_for_a_branch_at_the_tag(frozen_repo, tagged_after_change):
    git(frozen_repo, "checkout", "-q", "-b", "preprint/p0-w9", tagged_after_change)
    git(frozen_repo, "merge", "-q", "--ff-only", "p0-cp3")
    assert track.freeze_problems(frozen_repo, "p0") == []


# --- the freeze block is data -----------------------------------------------------------

def _set_freeze(repo, tag, paths):
    p = repo / "ops" / "tracks" / "p0.yaml"
    data = yaml.safe_load(p.read_text())
    data["freeze"] = {"tag": tag, "paths": paths}
    p.write_text(HEADER + yaml.safe_dump(data, sort_keys=False))
    commit_all(repo, "scratch: freeze block")


@pytest.fixture
def control_repo(repo):
    _write(repo, {"results/preprint/a.json": "v1\n", "ops/reports/P0-W9.9.md": "v1\n", "lit/params.yaml": "k: 1\n"})
    _set_freeze(repo, "p0-carbonate-control", ["results/preprint/**", "ops/reports/P0-W*.md"])
    git(repo, "tag", "p0-carbonate-control")
    return repo


def test_freeze_block_untouched_frozen_path_passes(control_repo):
    _write(control_repo, {"README.md": "other\n"})
    commit_all(control_repo)
    assert track.freeze_problems(control_repo, "p0") == []


def test_freeze_block_unlisted_additive_key_passes(control_repo):
    _write(control_repo, {"lit/params.yaml": "k: 1\nnew_key: 2\n", "theory/new.md": "x\n"})
    commit_all(control_repo)
    assert track.freeze_problems(control_repo, "p0") == []


def test_freeze_block_frozen_path_needs_an_entry(control_repo):
    _write(control_repo, {"results/preprint/a.json": "v2\n"})
    commit_all(control_repo)
    assert track.freeze_problems(control_repo, "p0") == ["results/preprint/a.json"]
    assert "frozen since p0-carbonate-control" in blocked(track.check, control_repo, "p0", "P0-I0")
    _write(control_repo, {"ops/tracks/p0_deviations.md":
                          "# Deviations\n\n## %s results/preprint/a.json\nChange: x.\nRe-audit: cp5\n" % _today()})
    commit_all(control_repo)
    assert track.freeze_problems(control_repo, "p0") == []


def test_freeze_block_glob_matches_reports_only_by_pattern(control_repo):
    _write(control_repo, {"ops/reports/P0-W9.9.md": "v2\n", "ops/reports/PH-W1.1.md": "new\n"})
    commit_all(control_repo)
    assert track.freeze_problems(control_repo, "p0") == ["ops/reports/P0-W9.9.md"]


def test_no_freeze_block_no_rule(repo):
    p = repo / "ops" / "tracks" / "p0.yaml"
    data = yaml.safe_load(p.read_text())
    del data["freeze"]
    p.write_text(HEADER + yaml.safe_dump(data, sort_keys=False))
    commit_all(repo)
    git(repo, "tag", "p0-cp3")
    _write(repo, {"lit/params.yaml": "v2\n"})
    commit_all(repo)
    assert track.freeze_problems(repo, "p0") == []
