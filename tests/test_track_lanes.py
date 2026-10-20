"""Track lanes: matcher, hooks and `nacre verify` on preprint/* branches."""
from pathlib import Path
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


_TOML = """[project]
name = "x"
dependencies = ["pyyaml"]

[dependency-groups]
dev = ["pytest"]
p0-w1 = []
p0-w2 = []

[tool.uv]
default-groups = ["dev", "p0-w1", "p0-w2"]
"""


def test_hook_worker_changes_only_its_dependency_group(hook_repo):
    assert commit(hook_repo, {"pyproject.toml": _TOML}, branch="preprint/p0").returncode == 0
    git(hook_repo, "checkout", "-q", "-B", "preprint/p0-w1")
    ok_change = _TOML.replace("p0-w1 = []", 'p0-w1 = ["pint"]')
    assert commit(hook_repo, {"pyproject.toml": ok_change}).returncode == 0


def test_hook_worker_rejects_other_group_tool_uv_and_lock(hook_repo):
    assert commit(hook_repo, {"pyproject.toml": _TOML}, branch="preprint/p0").returncode == 0
    git(hook_repo, "checkout", "-q", "-B", "preprint/p0-w1")
    r = commit(hook_repo, {"pyproject.toml": _TOML.replace("p0-w2 = []", 'p0-w2 = ["numpy"]')})
    assert r.returncode != 0 and "[dependency-groups]" in r.stderr and "dependency-groups.p0-w2" in r.stderr
    git(hook_repo, "reset", "-q", "--hard")
    r = commit(hook_repo, {"pyproject.toml": _TOML.replace('"p0-w2"]', '"p0-w2", "x"]')})
    assert r.returncode != 0 and "[tool.uv]" in r.stderr
    git(hook_repo, "reset", "-q", "--hard")
    r = commit(hook_repo, {"uv.lock": "version = 1\n"})
    assert r.returncode != 0 and "never stages uv.lock" in r.stderr


def test_hook_integrator_may_change_everything_in_pyproject(hook_repo):
    assert commit(hook_repo, {"pyproject.toml": _TOML}, branch="preprint/p0").returncode == 0
    r = commit(hook_repo, {"pyproject.toml": _TOML.replace('["pyyaml"]', '["pyyaml", "numpy"]'), "uv.lock": "v\n"})
    assert r.returncode == 0, r.stderr


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


# --- nacre lane new --track -------------------------------------------------------------

from conftest import LOCAL_GUIDE, LOCAL_SETTINGS, nacre as run_nacre  # noqa: E402
from nacre.cli.commands import lane as lane_cmd  # noqa: E402


@pytest.fixture
def track_origin(tmp_path):
    """A main checkout with origin (bare) holding main and preprint/p0, plus local-only files."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    main = init_repo(tmp_path / "nacre-shell")
    (main / ".git" / "info" / "exclude").write_text(
        "%s\n%s/\n.local/\n.env\n" % (LOCAL_GUIDE, LOCAL_SETTINGS))
    (main / "README.md").write_text("x\n")
    git(main, "add", "-A")
    git(main, "commit", "-q", "--no-verify", "-m", "scratch: init")
    git(main, "remote", "add", "origin", str(origin))
    git(main, "push", "-q", "origin", "main")
    git(main, "checkout", "-q", "-b", "preprint/p0")
    (main / "ops" / "tracks").mkdir(parents=True)
    (main / "ops" / "tracks" / "p0.yaml").write_text("meta: {}\n")
    git(main, "add", "-A")
    git(main, "commit", "-q", "--no-verify", "-m", "scratch: track")
    git(main, "push", "-q", "origin", "preprint/p0")
    (main / ".env").write_text("A=1\n")
    (main / LOCAL_GUIDE).write_text("guide\n")
    (main / LOCAL_SETTINGS).mkdir()
    (main / LOCAL_SETTINGS / "settings.json").write_text("{}\n")
    return main


def test_lane_new_track_creates_worktree(track_origin):
    calls = []
    target, branch = lane_cmd.new_track_lane(track_origin, "p0", "w1", provision_fn=calls.append)
    assert target == track_origin.parent / "nacre-shell-p-w1" and branch == "preprint/p0-w1"
    assert calls == [target]
    assert git(target, "symbolic-ref", "--short", "HEAD").stdout.strip() == "preprint/p0-w1"
    assert git(target, "rev-parse", "HEAD").stdout == git(track_origin, "rev-parse", "origin/preprint/p0").stdout
    env = target / ".env"
    assert env.is_symlink() and env.resolve() == (track_origin / ".env").resolve()
    assert (target / LOCAL_GUIDE).read_text() == "guide\n"
    assert (target / LOCAL_SETTINGS / "settings.json").exists()
    assert (target / ".local" / "prompts").is_dir()
    assert git(target, "status", "--porcelain").stdout == ""
    assert git(target, "diff", "--cached", "--name-only").stdout == ""


def test_lane_new_track_accepts_full_lane_id(track_origin):
    target, branch = lane_cmd.new_track_lane(track_origin, "p0", "p0-w2", provision_fn=lambda t: None)
    assert target.name == "nacre-shell-p-w2" and branch == "preprint/p0-w2"


def test_lane_new_track_matches_registry_worktree(cfg):
    for lane_id, entry in cfg["tracks"]["p0"]["lanes"].items():
        if lane_id != "p0-int":
            assert entry["worktree"].rsplit("/", 1)[1] == "nacre-shell-p-" + lane_id[3:]


@pytest.mark.parametrize("track,lane,why", [
    ("p0", "w9", "not registered in track p0"),
    ("p0", "int", "integrator"),
    ("p9", "w1", "track 'p9' is not registered"),
])
def test_lane_new_track_refusals(track_origin, track, lane, why):
    with pytest.raises(SystemExit) as exc:
        lane_cmd.new_track_lane(track_origin, track, lane, provision_fn=lambda t: None)
    assert why in str(exc.value)


def test_lane_new_track_refuses_existing_target(track_origin):
    (track_origin.parent / "nacre-shell-p-w3").mkdir()
    with pytest.raises(SystemExit) as exc:
        lane_cmd.new_track_lane(track_origin, "p0", "w3", provision_fn=lambda t: None)
    assert "already exists" in str(exc.value)


def test_lane_new_without_track_is_unchanged(track_origin):
    r = run_nacre(["lane", "new", "w1"], track_origin)
    assert r.returncode != 0 and "not registered in ops/lanes.yaml" in (r.stdout + r.stderr)
    assert not (track_origin.parent / "nacre-shell-w1").exists()


@pytest.mark.parametrize("platform,chflags", [("darwin", True), ("linux", False)])
def test_provision_runs_sync_and_chflags(tmp_path, platform, chflags):
    calls = []
    lane_cmd.provision(tmp_path, run=lambda cmd, **kw: calls.append(cmd), platform=platform)
    assert calls[0] == ["uv", "sync"]
    assert (["chflags", "-R", "nohidden", ".venv"] in calls) is chflags


@pytest.fixture(autouse=True)
def _no_real_venv(monkeypatch, request):
    """Worktree creation must not build environments under the real home directory."""
    if not request.node.name.startswith("test_link_venv"):
        monkeypatch.setattr(lane_cmd, "link_venv", lambda *a, **k: None)


def test_link_venv_creates_store_and_symlink(tmp_path):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        Path(cmd[2]).mkdir(parents=True)

    target = tmp_path / "wt"
    target.mkdir()
    store = lane_cmd.link_venv(target, "w1", run=run, home=tmp_path / "home")
    assert store == tmp_path / "home" / ".nacre-venvs" / "p-w1"
    assert calls == [["uv", "venv", str(store)]]
    assert (target / ".venv").is_symlink() and (target / ".venv").resolve() == store.resolve()


def test_link_venv_reuses_existing_store_and_keeps_existing_link(tmp_path):
    store = tmp_path / "home" / ".nacre-venvs" / "p-w2"
    store.mkdir(parents=True)
    target = tmp_path / "wt"
    target.mkdir()
    calls = []
    lane_cmd.link_venv(target, "w2", run=lambda cmd, **kw: calls.append(cmd), home=tmp_path / "home")
    assert calls == [] and (target / ".venv").resolve() == store.resolve()
    other = tmp_path / "other"
    other.mkdir()
    (target / ".venv").unlink()
    (target / ".venv").symlink_to(other)
    lane_cmd.link_venv(target, "w2", run=lambda cmd, **kw: calls.append(cmd), home=tmp_path / "home")
    assert (target / ".venv").resolve() == other.resolve()


def test_new_track_lane_links_venv_before_provisioning(track_origin, monkeypatch):
    order = []
    monkeypatch.setattr(lane_cmd, "link_venv", lambda target, short, **k: order.append(("link", short)))
    lane_cmd.new_track_lane(track_origin, "p0", "w4", provision_fn=lambda t: order.append(("provision", t.name)))
    assert order == [("link", "w4"), ("provision", "nacre-shell-p-w4")]


def test_ph_report_names_are_owned_per_lane(cfg):
    for n in range(1, 9):
        lane = "p0-w%d" % n
        assert ok(cfg, lane, "ops/reports/PH-W%d.1.md" % n)
        assert not ok(cfg, lane, "ops/reports/PH-W%d.1.md" % (n % 8 + 1))
    assert ok(cfg, "p0-w1", "ops/reports/P0-W1.PH-W1.1.md")


def test_ph_k1_report_is_owned_by_w5_only(hook_repo):
    assert commit(hook_repo, {"ops/reports/PH-K1.md": "r\n"}, branch="preprint/p0-w5").returncode == 0
    assert commit(hook_repo, {"ops/reports/PH-K1.md": "r2\n"}, branch="preprint/p0-w1").returncode != 0
