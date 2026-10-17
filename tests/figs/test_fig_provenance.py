"""Each data figure reads only committed output files: a pinned owner document or a tracked path."""
import json
import subprocess

import pytest
from figs_helpers import REPO

from nacre.figs import build, paths, schema, upstream

DATA_FIGS = ["fig4", "fig5", "fig7"]  # built from real outputs in P0-W6.3


def _mod(fid):
    return build.load_template(paths(REPO)["src"] / (fid + ".py"))


def _tracked(path):
    out = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch", path], capture_output=True)
    return out.returncode == 0


@pytest.mark.parametrize("fid", DATA_FIGS)
def test_real_input_is_a_pinned_owner_output(fid):
    ref = _mod(fid).FIGURE["input"]
    assert ref.startswith(schema.UPSTREAM), ref
    e = upstream.entry(ref[len(schema.UPSTREAM):], REPO)
    assert e["kind"] == "data" and e["owner"] in {"p0-w2", "p0-w4"}
    assert _tracked(e["snapshot"]), e["snapshot"]
    upstream.snapshot_bytes(ref[len(schema.UPSTREAM):], REPO)  # raises on a sha256 mismatch


@pytest.mark.parametrize("fid", DATA_FIGS)
def test_real_aux_files_are_committed(fid):
    for name, ref in _mod(fid).FIGURE.get("aux", {}).items():
        if isinstance(ref, str):
            assert ref.startswith(schema.UPSTREAM), name
            assert _tracked(upstream.entry(ref[len(schema.UPSTREAM):], REPO)["snapshot"]), name
        else:
            assert _tracked(ref["real"]), (name, ref["real"])


@pytest.mark.parametrize("fid", DATA_FIGS)
def test_manifest_records_the_owner_commit_and_sha(fid):
    rec = json.loads((REPO / "figures/out/manifest.json").read_text())["figures"][fid]
    e = upstream.entry(_mod(fid).FIGURE["input"][len(schema.UPSTREAM):], REPO)
    assert rec["mock"] is False
    assert rec["input_source"] == {"owner": e["owner"], "path": e["path"], "commit": e["commit"], "sha256": e["sha256"]}
    assert rec["input"] == e["snapshot"] and rec["input_sha256"] == e["sha256"]
    assert rec["font"]["family"] and "release" in rec["font"]


@pytest.mark.parametrize("key", sorted(k for k, e in upstream.registry(REPO).items() if e.get("kind") == "data"))
def test_snapshot_equals_the_owner_commit_where_git_has_it(key):
    e = upstream.entry(key, REPO)
    out = subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (e["commit"], e["path"])], capture_output=True)
    if out.returncode != 0:
        pytest.skip("owner commit %s not in this clone" % e["commit"][:7])
    assert out.stdout == upstream.snapshot_bytes(key, REPO)


def test_pinned_input_must_be_a_data_entry(monkeypatch):
    mod = _mod("fig5")
    monkeypatch.setitem(mod.FIGURE, "input", "upstream:thresholds")
    with pytest.raises(build.FigureError, match="not a pinned output document"):
        build.load_input(REPO, mod, mock=False)


def test_tampered_data_snapshot_is_refused(monkeypatch):
    e = dict(upstream.entry("retro_results", REPO))
    e["sha256"] = "0" * 64
    monkeypatch.setitem(upstream.registry(REPO), "retro_results", e)
    with pytest.raises(upstream.UpstreamError, match="sha256"):
        build.load_input(REPO, _mod("fig4"), mock=False)
