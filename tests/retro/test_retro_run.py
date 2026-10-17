"""The retrodiction run (lane p0-w2): permutation null, tallies and the frozen-input check.

Every case here is synthetic; the frozen preprint/retrodiction/cases.yaml is never run in this suite.
"""
import subprocess

import numpy as np
import pytest
import yaml

from nacre.retro import run

SHARED = {"gamma_nl": {"symbol": "gamma_nl", "interface": "gamma_nl",
                       "distribution": {"type": "uniform", "low": 0.10, "high": 0.12}, "unit": "J m^-2"},
          "V_m": {"symbol": "V_m", "interface": "bulk", "value": 3.7e-5, "unit": "m^3 mol^-1"}}
COMMON = [{"symbol": "Omega", "role": "shared", "interface": "bulk",
           "distribution": {"type": "uniform_log", "low_sigma": 4.0, "high_sigma": 5.0}, "unit": "1"},
          {"symbol": "T", "role": "shared", "interface": "bulk", "value": 298.0, "unit": "K"},
          {"symbol": "A_c", "role": "shared", "interface": "gamma_sn",
           "distribution": {"type": "uniform", "low": 0.3, "high": 0.4}, "unit": "nm^2"}]


def _dupre(cid, test, ref, study, relation="test_higher_barrier"):
    side = lambda role, mean: {"symbol": "dG_bind", "role": role, "interface": "gamma_sn", "interface_mapping": "dupre",
                               "distribution": {"type": "normal", "mean": mean, "sd": 0.1}, "unit": "kcal mol^-1"}
    return {"id": cid, "study": study, "termination": "thiol", "negative": False, "status": "usable",
            "test": {"label": "t" + cid}, "reference": {"label": "r" + cid},
            "outcome": {"relation": relation}, "inputs": COMMON + [side("test", test), side("reference", ref)]}


def _write(tmp_path, cases):
    p = tmp_path / "cases.yaml"
    p.write_text(yaml.safe_dump({"schema": "retro-cases/v1", "shared_priors": SHARED, "cases": cases}),
                 encoding="utf-8")
    return p


def _cases():
    # weak binders tested against strong binders: every case correct by construction
    return [_dupre("RC%02d" % i, -2.0 - 0.2 * i, -8.0 - 0.2 * i, "S-%d" % (i % 2)) for i in range(1, 7)]


def test_evaluate_keeps_misses_apart_and_reports_both_null_schemes(tmp_path):
    cases = _cases()
    cases.append(_dupre("RC07", -5.0, -5.0, "S-1"))                     # inconclusive by construction
    cases.append(_dupre("RC08", -8.0, -2.0, "S-0"))                     # incorrect by construction
    rec = run.evaluate(_write(tmp_path, cases), None, draws=2000, seed=1, n_perm=40)
    s = rec["summary"]
    assert (s["N"], s["correct"], s["incorrect"], s["inconclusive"], s["undetermined"]) == (8, 6, 1, 1, 0)
    assert s["misses"] == 2 and s["misses_by_case"] == {"RC07": "inconclusive", "RC08": "incorrect"}
    assert s["swap_check"]["holds"]
    for scheme in run.SCHEMES:
        null = s["permutation_null"][scheme]
        assert null["descriptive"] and null["n_perm"] == 40 and sum(null["counts"]) == 40
        assert null["range95"][0] <= null["median"] <= null["range95"][1]
    assert all(r["nonfinite_fraction"] == 0.0 for r in rec["cases"])


def test_evaluate_reproduces_the_entry_point_draw_by_draw(tmp_path):
    path = _write(tmp_path, _cases())
    a = run.evaluate(path, None, draws=1000, seed=7, n_perm=5)
    b = run.evaluate(path, None, draws=1000, seed=7, n_perm=5)
    assert [r["delta"] for r in a["cases"]] == [r["delta"] for r in b["cases"]]
    assert a["summary"]["permutation_null"] == b["summary"]["permutation_null"]


def test_slots_move_only_within_a_mapping_and_within_a_study_when_asked(tmp_path):
    usable, prepared, _ = run.prepare_all(_write(tmp_path, _cases()), None, 100, 0)
    within = run.slot_groups(usable, prepared, "within_study")
    across = run.slot_groups(usable, prepared, "across_studies")
    assert sorted(within) == [("S-0", "dupre"), ("S-1", "dupre")] and list(across) == [("dupre",)]
    assert sum(len(v) for v in within.values()) == sum(len(v) for v in across.values()) == 12


def test_a_case_given_one_input_set_twice_is_inconclusive(tmp_path):
    usable, prepared, _ = run.prepare_all(_write(tmp_path, _cases()[:1]), None, 500, 0)
    shared, test, _, mapping = prepared[0]
    assert run._verdict(usable[0], shared, test, test, mapping) == "inconclusive"
    # a single case: within its study the null can only keep or swap the labels
    counts = run.permutation_null(usable, prepared, "within_study", 200, np.random.default_rng(0))
    assert set(counts.tolist()) <= {0, 1} and 0 < counts.mean() < 1


def test_check_frozen_refuses_changed_bytes_and_dirty_trees(tmp_path):
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.org")
    git("config", "user.name", "t")
    git("config", "commit.gpgsign", "false")
    git("config", "tag.gpgsign", "false")
    for path in (run.CASES, run.CRITERION, run.PARAMS, run.CONTRACT):
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text("v1\n", encoding="utf-8")
    git("add", "-A")
    git("commit", "-q", "-m", "frozen")
    git("tag", "cp")
    prov = run.check_frozen(tmp_path, "HEAD", "cp")
    assert prov["git_dirty"] is False and prov["params_file_hash"].startswith("sha256:")
    (tmp_path / run.CRITERION).write_text("v2\n", encoding="utf-8")
    with pytest.raises(run.RunError, match="not clean"):
        run.check_frozen(tmp_path, "HEAD", "cp")
    git("commit", "-q", "-am", "changed after the freeze")
    with pytest.raises(run.RunError, match="fixed-before-run"):
        run.check_frozen(tmp_path, "HEAD~1", "cp")
