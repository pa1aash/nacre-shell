"""The parameter table changes only by addition after tag p0-cp3 (README section 8, decision D30)."""
import subprocess
from pathlib import Path

import pytest
import yaml

from nacre.lit import params as P

ROOT = Path(__file__).resolve().parents[2]

TAG = "p0-cp3"
EDITED = {"n_req"}  # cp3 R5: N_req = ln(1/q_0)/A_patch (README section 8)
EDITED_ALIASES = {("thresholds", "C3", "N_req")}


def _tag_table():
    res = subprocess.run(["git", "show", "%s:lit/params.yaml" % TAG], cwd=ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip("tag %s is not available in this checkout" % TAG)
    return yaml.safe_load(res.stdout)


def _leaves(node, path=()):
    if isinstance(node, dict) and "key" in node and "prior" in node:
        yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from _leaves(v, path + (k,))


@pytest.fixture(scope="module")
def tables():
    return _tag_table(), yaml.safe_load((ROOT / P.PARAMS).read_text(encoding="utf-8"))


def test_every_key_at_the_tag_is_unchanged_except_the_mandated_edit(tables):
    old, new = tables
    changed = sorted(k for k, e in old["params"].items() if new["params"].get(k) != e)
    assert set(changed) <= EDITED, changed


def test_no_key_is_removed(tables):
    old, new = tables
    assert not set(old["params"]) - set(new["params"])


def test_aliases_at_the_tag_are_unchanged_except_the_edited_key(tables):
    old, new = tables
    new_leaves = {p: leaf for root in P.VIEW_ROOTS for p, leaf in _leaves(new.get(root, {}), (root,))}
    for root in P.VIEW_ROOTS:
        for path, leaf in _leaves(old.get(root, {}), (root,)):
            if path in EDITED_ALIASES:
                assert new_leaves[path]["key"] == leaf["key"]
                continue
            assert new_leaves.get(path) == leaf, ".".join(path)


def test_correlation_groups_at_the_tag_keep_their_members_and_kind(tables):
    old, new = tables
    for gid, g in old["correlation_groups"].items():
        assert new["correlation_groups"][gid] == g, gid


def test_new_keys_name_the_session_that_added_them(tables):
    old, new = tables
    added = [k for k in new["params"] if k not in old["params"]]
    assert all(str(new["params"][k].get("added_in") or "").startswith("P0-W1.") for k in added), added


def test_filled_gaps_are_still_gaps_as_at_the_tag(tables):
    old, new = tables
    for k, e in new["params"].items():
        if "fills" in e:
            assert old["params"][e["fills"]]["status"] == "gap", k
            assert new["params"][e["fills"]] == old["params"][e["fills"]], k


def test_n_req_is_the_poisson_rule():
    e = P.load_params(ROOT / P.PARAMS, ROOT).entries["n_req"]
    assert e["derived"]["expr"] == "log(1 / (1 - p_cred)) / A_patch"
    assert e["derived"]["inputs"] == {"p_cred": "p_cred", "A_patch": "patch_area"}
