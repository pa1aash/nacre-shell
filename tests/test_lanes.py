"""Matcher unit tests for tools/githooks/_lanes.py."""
import pytest

import _lanes
from conftest import REPO


@pytest.fixture(scope="module")
def cfg():
    return _lanes.load_lanes(str(REPO))


def ok(cfg, lane, path, merge=False):
    return _lanes.check_path(lane, path, cfg, merge)[0]


@pytest.mark.parametrize("pat,path,expect", [
    ("charter/**", "charter/x.yaml", True),
    ("charter/**", "charter/a/b.yaml", True),
    ("charter/**", "charterx/y", False),
    ("figures/src/validation_*", "figures/src/validation_a.py", True),
    ("figures/src/validation_*", "figures/src/validation_a/b.py", False),
    ("lit/instrument_gaps.*", "lit/instrument_gaps.md", True),
    (".dvcignore", ".dvcignore", True),
    ("**/x.py", "x.py", True),
    ("**/x.py", "a/b/x.py", True),
    (".github/workflows/containers*.yml", ".github/workflows/containers-gpu.yml", True),
    (".github/workflows/containers*.yml", ".github/workflows/ci.yml", False),
])
def test_glob(pat, path, expect):
    assert _lanes.glob_match(pat, path) is expect


@pytest.mark.parametrize("branch,lane", [("main", "a-main"), ("lane/a-charter", "a-charter"),
                                         ("lane/b-venue", "b-venue"), ("lane/b-setup", "b-setup")])
def test_resolve_ok(cfg, branch, lane):
    assert _lanes.resolve_lane(branch, cfg) == (lane, None)


@pytest.mark.parametrize("branch", ["feature/x", "lane/a-unknown", "lane/zzz", "lane/a-main", None, "master"])
def test_resolve_refused(cfg, branch):
    lane, err = _lanes.resolve_lane(branch, cfg)
    assert lane is None and err


def test_laptop_of(cfg):
    assert _lanes.laptop_of("a-infra", cfg) == "A"
    assert _lanes.laptop_of("b-x", cfg) == "B"
    assert _lanes.laptop_of("c-x", cfg) is None


def test_includes(cfg):
    assert ok(cfg, "b-paper", "paper/main.tex")
    assert ok(cfg, "b-paper", "src/nacre/morphology/a.py")
    assert ok(cfg, "b-paper", "figures/src/validation_x.py")
    assert ok(cfg, "a-charter", "charter/claim_register.yaml")
    assert ok(cfg, "a-infra", "jobs/x/y.json")
    assert ok(cfg, "a-main", "src/nacre/physics/x.py")


def test_excepts(cfg):
    for path in ("paper/sections/results.tex", "paper/generated/t.tex", "paper/captions/f.tex"):
        assert not ok(cfg, "b-paper", path)
        assert ok(cfg, "a-main", path)
    assert not ok(cfg, "a-charter", "charter/venue/v.yaml")
    assert ok(cfg, "b-venue", "charter/venue/v.yaml")
    assert not ok(cfg, "a-main", "charter/venue/v.yaml")


def test_laptop_boundaries(cfg):
    assert not ok(cfg, "b-test", "src/nacre/physics/x.py")
    assert not ok(cfg, "a-charter", "paper/main.tex")
    assert not ok(cfg, "a-retrieval", "charter/x.yaml")
    assert not ok(cfg, "a-main", "paper/main.tex")


def test_carveouts(cfg):
    assert ok(cfg, "b-test", "ops/state/b-test.json")
    assert not ok(cfg, "b-test", "ops/state/b-other.json")
    assert ok(cfg, "a-retrieval", "jobs/ledger/a-retrieval.jsonl")
    assert not ok(cfg, "a-retrieval", "jobs/ledger/a-infra.jsonl")
    assert ok(cfg, "b-paper", "ops/reports/S03.md")
    assert ok(cfg, "a-charter", "ops/reports/S02.md")
    assert not ok(cfg, "b-paper", "ops/reports/sub/x.md")


def test_b_setup_owns_only_state_and_report(cfg):
    assert ok(cfg, "b-setup", "ops/state/b-setup.json")
    assert ok(cfg, "b-setup", "ops/reports/S00b.md")
    assert not ok(cfg, "b-setup", "paper/main.tex")


def test_shared_paths(cfg):
    for lane in ("a-charter", "b-paper", "b-setup", "a-main"):
        assert ok(cfg, lane, "pyproject.toml")
        assert ok(cfg, lane, "uv.lock")


def test_a_lanes_write_gates_and_packets(cfg):
    assert ok(cfg, "a-charter", "ops/gates/G0.md")
    assert ok(cfg, "a-retrieval", "ops/packets/G1.md")
    assert not ok(cfg, "b-paper", "ops/gates/G0.md")


def test_merge_in_progress_rule(cfg):
    assert not ok(cfg, "a-main", "paper/main.tex")
    assert ok(cfg, "a-main", "paper/main.tex", merge=True)
    assert not ok(cfg, "a-charter", "paper/main.tex", merge=True)


def test_main_only_ledger(cfg):
    assert ok(cfg, "a-main", "ops/waves.yaml")
    for lane in ("a-charter", "a-infra", "b-paper", "b-setup"):
        assert not ok(cfg, lane, "ops/waves.yaml")


def test_unregistered_lane_refused(cfg):
    assert not ok(cfg, "a-nope", "charter/x.yaml")


def test_lane_violations_lists_each(cfg):
    bad = _lanes.lane_violations("b-test", ["paper/a.tex", "src/x.py", "tests/t.py"], cfg)
    assert [p for p, _ in bad] == ["src/x.py", "tests/t.py"]


RULES = [{"paths": ["registration/**"], "after_tag": "prereg-v1", "append_only": ["registration/deviations.md"]}]


def test_frozen_rules():
    chg = {"registration/p.md": (1, 1), "registration/deviations.md": (3, 0), "src/a.py": (1, 0)}
    assert _lanes.frozen_violations(RULES, lambda t: False, chg) == []
    bad = _lanes.frozen_violations(RULES, lambda t: True, chg)
    assert [p for p, _ in bad] == ["registration/p.md"]
    bad = _lanes.frozen_violations(RULES, lambda t: True, {"registration/deviations.md": (1, 1)})
    assert len(bad) == 1
    bad = _lanes.frozen_violations(RULES, lambda t: True, {"registration/deviations.md": (None, None)})
    assert len(bad) == 1


def test_parse_numstat():
    assert _lanes.parse_numstat("1\t2\ta.txt\0-\t-\tb.bin\0") == {"a.txt": (1, 2), "b.bin": (None, None)}
