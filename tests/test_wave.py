import json
import shutil

import pytest
import yaml

from conftest import REPO, git, init_repo
from nacre.cli.commands import verify, wave


def write_waves(repo, waves):
    (repo / "ops").mkdir(exist_ok=True)
    text = (REPO / "ops" / "waves.yaml").read_text().split("\nwaves:")[0]
    (repo / "ops" / "waves.yaml").write_text(text + "\nwaves:\n" + yaml.safe_dump(waves))


def wave0(**kw):
    w = {"wave": 0, "base": None, "required_tags": [], "sessions": {"A1": ["S00"], "B1": ["S00b"]},
         "lanes": {"S00": "a-main", "S00b": "b-setup"}, "status": "open", "opened_utc": None, "closed_utc": None}
    w.update(kw)
    return w


def commit_all(repo, msg="scratch: change"):
    git(repo, "add", "-A")
    assert git(repo, "commit", "-q", "--no-verify", "-m", msg).returncode == 0
    return git(repo, "rev-parse", "HEAD").stdout.strip()


@pytest.fixture
def repo(tmp_path):
    r = init_repo(tmp_path / "r")
    write_waves(r, [wave0()])
    commit_all(r, "scratch: init")
    return r


def put_state(repo, lane, last, status="DONE"):
    p = repo / "ops" / "state" / (lane + ".json")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"lane": lane, "last_session": last, "status": status}))


def blocked(fn, *a, **k):
    with pytest.raises(wave.Blocked) as exc:
        fn(*a, **k)
    return str(exc.value)


# --- check --------------------------------------------------------------------

def test_check_passes_for_listed_session(repo):
    w, lane = wave.check(repo, "S00")
    assert lane == "a-main" and w["wave"] == 0


def test_check_fails_for_unlisted_session(repo):
    assert "not listed" in blocked(wave.check, repo, "S99")


def test_check_requires_the_lane_branch(repo):
    assert "lane/b-setup" in blocked(wave.check, repo, "S00b")
    git(repo, "checkout", "-q", "-b", "lane/b-setup")
    assert wave.check(repo, "S00b")[1] == "b-setup"
    assert "main" in blocked(wave.check, repo, "S00")


def test_check_fails_on_branch_missing_base(repo):
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "checkout", "-q", "--orphan", "unrelated")
    write_waves(repo, [wave0(base=base, sessions={"A1": ["S00"]}, lanes={"S00": "a-main"})])
    commit_all(repo, "scratch: unrelated history")
    git(repo, "branch", "-M", "main")
    assert "base commit" in blocked(wave.check, repo, "S00")


def test_check_passes_when_head_contains_base(repo):
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    write_waves(repo, [wave0(base=base)])
    commit_all(repo)
    wave.check(repo, "S00")


def test_check_fails_if_required_tag_absent(repo):
    write_waves(repo, [wave0(required_tags=["g0"])])
    assert "g0" in blocked(wave.check, repo, "S00")
    git(repo, "tag", "g0")
    wave.check(repo, "S00")


def test_check_needs_exactly_one_open_wave(repo):
    write_waves(repo, [wave0(status="closed")])
    assert "open wave" in blocked(wave.check, repo, "S00")


# --- integration sessions -------------------------------------------------------

def make_origin(repo, tmp_path):
    bare = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", str(bare))
    git(repo, "remote", "add", "origin", str(bare))
    assert git(repo, "push", "-q", "origin", "main").returncode == 0
    return bare


def test_integration_check_passes_on_main_while_wave_open(repo, tmp_path):
    make_origin(repo, tmp_path)
    w, lane = wave.check(repo, "I0")
    assert lane == "a-main" and w["wave"] == 0


def test_integration_check_fails_off_main(repo, tmp_path):
    make_origin(repo, tmp_path)
    git(repo, "checkout", "-q", "-b", "lane/a-charter")
    assert "main" in blocked(wave.check, repo, "I0")


def test_integration_check_fails_for_wrong_wave(repo, tmp_path):
    make_origin(repo, tmp_path)
    assert "wave 1" in blocked(wave.check, repo, "I1")


# --- status -------------------------------------------------------------------

def test_status_reports_states(repo):
    text = "\n".join(wave.status_lines(repo))
    assert "S00 (lane a-main): pending" in text and "S00b (lane b-setup): pending" in text
    put_state(repo, "a-main", "S00")
    put_state(repo, "b-setup", "S00b", "HOLD-P")
    text = "\n".join(wave.status_lines(repo))
    assert "S00 (lane a-main): DONE" in text
    assert "S00b (lane b-setup): running(HOLD-P)" in text
    assert "missing before close: S00b" in text


# --- open ---------------------------------------------------------------------

@pytest.fixture
def passing_verify(monkeypatch):
    monkeypatch.setattr(verify, "run_checks", lambda root, strict=False: [{"name": "x", "status": "PASS", "detail": ""}])


OPEN = dict(tags=["g0"], sessions={"A1": ["S02"], "B1": ["S01", "S03"]},
            lanes={"S02": "a-charter", "S01": "b-venue", "S03": "b-paper"})


def do_open(repo, n=1, **kw):
    args = dict(OPEN, **kw)
    base = git(repo, "rev-parse", "HEAD").stdout.strip()
    return wave.open_next(repo, n, base, args["tags"], args["sessions"], args["lanes"])


def test_open_refuses_while_state_missing_or_not_done(repo, passing_verify):
    assert "ops/state/a-main.json is missing" in blocked(do_open, repo)
    put_state(repo, "a-main", "S00")
    assert "b-setup" in blocked(do_open, repo)
    put_state(repo, "b-setup", "S00b", "HOLD-P")
    assert "status is HOLD-P" in blocked(do_open, repo)
    put_state(repo, "b-setup", "S00", "DONE")
    assert "expected S00b" in blocked(do_open, repo)


def test_open_succeeds_when_all_done_and_closes_previous(repo, passing_verify):
    put_state(repo, "a-main", "S00")
    put_state(repo, "b-setup", "S00b")
    commit_all(repo)
    w = do_open(repo)
    assert w["wave"] == 1 and w["status"] == "open" and len(w["base"]) == 40
    waves = wave.load_waves(repo)
    assert [x["status"] for x in waves] == ["closed", "open"]
    assert waves[0]["closed_utc"] and waves[1]["required_tags"] == ["g0"]
    assert git(repo, "log", "-1", "--format=%s").stdout.strip() == "ops(wave): open wave 1"
    assert git(repo, "status", "--porcelain").stdout.strip() == ""
    assert (repo / "ops" / "waves.yaml").read_text().startswith("# Wave ledger")


def test_open_checks_final_session_per_lane_in_window(repo, passing_verify):
    waves = [wave0(sessions={"A3": ["S30", "S31"]}, lanes={"S30": "a-infra", "S31": "a-infra"})]
    write_waves(repo, waves)
    put_state(repo, "a-infra", "S30")
    commit_all(repo)
    assert "expected S31" in blocked(do_open, repo)
    put_state(repo, "a-infra", "S31")
    commit_all(repo)
    assert do_open(repo)["wave"] == 1


def test_open_refuses_off_main(repo, passing_verify):
    put_state(repo, "a-main", "S00")
    put_state(repo, "b-setup", "S00b")
    commit_all(repo)
    git(repo, "checkout", "-q", "-b", "lane/a-charter")
    assert "main only" in blocked(do_open, repo)


def test_open_refuses_unregistered_lane_and_failing_verify(repo, monkeypatch):
    put_state(repo, "a-main", "S00")
    put_state(repo, "b-setup", "S00b")
    commit_all(repo)
    assert "not registered" in blocked(do_open, repo, lanes={"S02": "a-nope", "S01": "b-venue", "S03": "b-paper"})
    monkeypatch.setattr(verify, "run_checks", lambda root, strict=False: [{"name": "tests", "status": "FAIL", "detail": ""}])
    assert "verify fails" in blocked(do_open, repo)


def test_open_refuses_gaps_and_duplicates(repo, passing_verify):
    put_state(repo, "a-main", "S00")
    put_state(repo, "b-setup", "S00b")
    commit_all(repo)
    assert "does not exist" in blocked(do_open, repo, n=2)
    do_open(repo)
    assert "already exists" in blocked(do_open, repo)
