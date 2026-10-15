"""Track lanes: matcher, hooks and `nacre verify` on preprint/* branches."""
import pytest

import _lanes
from conftest import REPO, git, init_repo
from nacre.cli.commands import verify


@pytest.fixture(scope="module")
def cfg():
    return _lanes.load_lanes(str(REPO))


def ok(cfg, lane, path):
    return _lanes.check_path(lane, path, cfg)[0]


def commit(repo, files, message="tooling(test): change", branch=None, extra=()):
    if branch:
        git(repo, "checkout", "-q", "-B", branch)
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        git(repo, "add", "-f", rel)
    return git(repo, "commit", "-q", "-m", message, *extra)


# --- matcher --------------------------------------------------------------------

@pytest.mark.parametrize("branch,lane", [("preprint/p0", "p0-int")] +
                         [("preprint/p0-w%d" % n, "p0-w%d" % n) for n in range(1, 9)])
def test_resolve_track_branches(cfg, branch, lane):
    assert _lanes.resolve_lane(branch, cfg) == (lane, None)


@pytest.mark.parametrize("branch", ["preprint/p0-w9", "preprint/p1", "preprint/x", "lane/p0-w1"])
def test_resolve_unregistered_track_branch_refused(cfg, branch):
    lane, err = _lanes.resolve_lane(branch, cfg)
    assert lane is None and err


def test_master_mapping_unchanged(cfg):
    assert _lanes.resolve_lane("main", cfg) == ("a-main", None)
    assert _lanes.resolve_lane("lane/a-charter", cfg) == ("a-charter", None)
    assert _lanes.resolve_lane("lane/b-venue", cfg) == ("b-venue", None)
    assert _lanes.track_lane(cfg, "a-charter") is None
    assert not ok(cfg, "a-charter", "paper/main.tex")
    assert ok(cfg, "a-main", "src/nacre/physics/x.py")


def test_integrator(cfg):
    assert _lanes.is_integrator(cfg, "p0-int")
    assert not _lanes.is_integrator(cfg, "p0-w1")
    assert not _lanes.is_integrator(cfg, "a-main")


def test_track_ownership(cfg):
    assert ok(cfg, "p0-w1", "lit/params.yaml")
    assert ok(cfg, "p0-w1", "src/nacre/lit/table.py")
    assert not ok(cfg, "p0-w1", "theory/x")
    assert ok(cfg, "p0-w3", "theory/x")
    assert ok(cfg, "p0-w8", "preprint/paper/main.tex")
    assert not ok(cfg, "p0-w2", "preprint/paper/main.tex")
    assert ok(cfg, "p0-w6", "figures/style/nacre.mplstyle")
    assert not ok(cfg, "p0-w7", "figures/style/nacre.mplstyle")


def test_track_carveouts(cfg):
    assert ok(cfg, "p0-w1", "ops/state/p0-w1.json")
    assert ok(cfg, "p0-w1", "ops/reports/P0-W1.1.md")
    assert ok(cfg, "p0-w1", "jobs/ledger/p0-w1.jsonl")
    assert ok(cfg, "p0-w1", "pyproject.toml") and ok(cfg, "p0-w1", "uv.lock")
    assert not ok(cfg, "p0-w1", "ops/state/p0-w2.json")
    assert not ok(cfg, "p0-w1", "ops/reports/P0-W2.1.md")
    assert not ok(cfg, "p0-w1", "ops/reports/S11.md")


def test_integrator_paths(cfg):
    for path in ("ops/tracks/p0.yaml", "charter/claim_register.yaml", "src/nacre/cli/commands/track.py",
                 "tools/githooks/_lanes.py", ".github/workflows/ci.yml", ".env.example",
                 "pyproject.toml", "uv.lock", "tests/test_hooks.py", "tests/test_track.py"):
        assert ok(cfg, "p0-int", path), path
    for path in ("theory/x", "lit/params.yaml", "preprint/paper/main.tex", "ops/waves.yaml"):
        assert not ok(cfg, "p0-int", path), path


# --- hooks (scratch repo wired to the real hook scripts) -------------------------------

def test_hook_rejects_theory_on_p0_w1(hook_repo):
    r = commit(hook_repo, {"theory/x": "x\n"}, branch="preprint/p0-w1")
    assert r.returncode != 0 and "[lane-ownership] theory/x" in r.stderr


def test_hook_accepts_params_on_p0_w1(hook_repo):
    r = commit(hook_repo, {"lit/params.yaml": "a: 1\n"}, branch="preprint/p0-w1")
    assert r.returncode == 0, r.stderr


def test_hook_rejects_theory_non_merge_on_p0(hook_repo):
    r = commit(hook_repo, {"theory/x": "x\n"}, branch="preprint/p0")
    assert r.returncode != 0 and "[lane-ownership] theory/x" in r.stderr


def test_hook_accepts_integrator_path_on_p0(hook_repo):
    r = commit(hook_repo, {"ops/tracks/p0.yaml": "meta: {}\n"}, branch="preprint/p0")
    assert r.returncode == 0, r.stderr


def test_hook_merge_on_p0_is_exempt(hook_repo):
    git(hook_repo, "checkout", "-q", "-B", "preprint/p0")
    assert commit(hook_repo, {"theory/x": "x\n"}, branch="preprint/p0-w3").returncode == 0
    git(hook_repo, "checkout", "-q", "preprint/p0")
    assert commit(hook_repo, {"ops/x.md": "y\n"}).returncode == 0
    r = git(hook_repo, "merge", "--no-ff", "-m", "merge preprint/p0-w3 into preprint/p0", "preprint/p0-w3")
    assert r.returncode == 0, r.stderr + r.stdout


def test_hook_rejects_unregistered_track_branch(hook_repo):
    r = commit(hook_repo, {"lit/params.yaml": "a: 1\n"}, branch="preprint/p0-w9")
    assert r.returncode != 0 and "[branch]" in r.stderr


# --- verify --------------------------------------------------------------------------

@pytest.fixture
def track_repo(tmp_path):
    repo = init_repo(tmp_path / "t")
    (repo / "README.md").write_text("x\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "scratch: init")
    return repo


def _nv_commit(repo, files, msg="scratch: change"):
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", "-A")
    assert git(repo, "commit", "-q", "--no-verify", "-m", msg).returncode == 0


def test_verify_integrator_counts_only_first_parent_non_merge(track_repo):
    repo = track_repo
    git(repo, "checkout", "-q", "-b", "lane/a-charter")
    _nv_commit(repo, {"theory/from_lane.md": "x\n"})
    git(repo, "checkout", "-q", "main")
    git(repo, "checkout", "-q", "-b", "preprint/p0")
    _nv_commit(repo, {"ops/tracks/p0.yaml": "meta: {}\n"})
    assert git(repo, "merge", "-q", "--no-ff", "--no-verify", "-m", "merge", "lane/a-charter").returncode == 0
    r = verify.check_lanes(repo, False)
    assert r["status"] == "PASS" and "lane p0-int" in r["detail"], r
    _nv_commit(repo, {"theory/direct.md": "x\n"})
    r = verify.check_lanes(repo, False)
    assert r["status"] == "FAIL" and "theory/direct.md" in r["detail"]
    assert "from_lane" not in r["detail"]


def test_verify_track_lane_diffs_against_track_base(track_repo):
    repo = track_repo
    git(repo, "checkout", "-q", "-b", "preprint/p0")
    _nv_commit(repo, {"ops/tracks/p0.yaml": "meta: {}\n"})
    git(repo, "checkout", "-q", "-b", "preprint/p0-w1")
    _nv_commit(repo, {"lit/params.yaml": "a: 1\n", "ops/state/p0-w1.json": "{}\n"})
    r = verify.check_lanes(repo, False)
    assert r["status"] == "PASS" and "2 paths, lane p0-w1" in r["detail"], r
    _nv_commit(repo, {"theory/x.md": "x\n"})
    r = verify.check_lanes(repo, False)
    assert r["status"] == "FAIL" and "theory/x.md" in r["detail"]


def test_verify_refuses_unregistered_track_branch(track_repo):
    git(track_repo, "checkout", "-q", "-b", "preprint/zz")
    r = verify.check_lanes(track_repo, False)
    assert r["status"] == "FAIL" and "not registered" in r["detail"]
