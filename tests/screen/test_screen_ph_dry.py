"""Phosphate dry runs and the carbonate regression of the generalised chain (PH-W4.1)."""
import json
import shutil

import pytest

from nacre.screen import ph_dry, ph_regress, run, summary

ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
SMALL_DRAWS = 2048


@pytest.fixture(scope="module")
def out_dir():
    d = ROOT / run.DRYRUN_PH_DIR / "_pytest"
    d.mkdir(parents=True, exist_ok=True)
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.parametrize("name", ["hap", "acp", "capoly"])
def test_dry_run_writes_a_schema_valid_document(name, out_dir):
    path, doc, stats = ph_dry.run_mineral(ROOT, name, out_dir / name / "summary.json", allow_mock=True, k1_override=True,
                                          draws=SMALL_DRAWS)
    summary.validate(json.loads(path.read_text(encoding="utf-8")))
    rec = doc["extensions"]["p0-w4"]["ph_screen"]
    assert doc["mock"] is True and rec["provisional"] is True
    assert set(rec) >= {"K1", "K2", "K3", "K4", "deletion_test", "gate", "mineral", "route_extension_points_pending"}
    assert rec["gate"]["overridden"] is True
    assert rec["mineral"]["phase_state"] in ("crystalline", "amorphous")
    assert stats["seconds"] > 0 and stats["peak_mb"] > 0


def test_dry_run_without_the_override_stops_at_the_k1_gate(out_dir):
    _, doc, _ = ph_dry.run_mineral(ROOT, "hap", out_dir / "gate" / "summary.json", allow_mock=True, draws=SMALL_DRAWS)
    rec = doc["extensions"]["p0-w4"]["ph_screen"]
    assert rec["K3"]["verdict"] == "not run" and rec["K1"]["passes_at"] == []


def test_dry_run_refuses_output_outside_dryrun_ph(tmp_path):
    with pytest.raises(ph_dry.DryRunRefused):
        ph_dry.run_mineral(ROOT, "hap", tmp_path / "summary.json", allow_mock=True, draws=SMALL_DRAWS)
    with pytest.raises(ph_dry.DryRunRefused):
        ph_dry.run_mineral(ROOT, "hap", ROOT / run.DRYRUN_DIR / "summary.json", allow_mock=True, draws=SMALL_DRAWS)


def test_dry_run_refuses_a_table_that_is_not_mock(out_dir):
    with pytest.raises(Exception):
        ph_dry.run_mineral(ROOT, "hap", out_dir / "x" / "summary.json", params_path=ROOT / "lit" / "params.yaml",
                           allow_mock=True, draws=SMALL_DRAWS)
    with pytest.raises(Exception):
        ph_dry.run_mineral(ROOT, "hap", out_dir / "y" / "summary.json", allow_mock=False, draws=SMALL_DRAWS)


def test_dry_run_directory_is_git_ignored():
    assert (ROOT / run.DRYRUN_PH_DIR / ".gitignore").exists()
    import subprocess
    r = subprocess.run(["git", "check-ignore", "-q", str(run.DRYRUN_PH_DIR / "hap" / "summary.json")], cwd=ROOT)
    assert r.returncode == 0


def test_mock_tables_bind_mineral_keys_separately():
    from nacre.screen import mineral, params_adapter
    ms = mineral.registry(run.load_config(ROOT))
    doc, _ = params_adapter.read_table(ROOT / ph_dry.MOCK_TABLE, True)
    h = ph_dry.bindings_for(doc, ms["hap"], ms)
    a = ph_dry.bindings_for(doc, ms["acp"], ms)
    c = ph_dry.bindings_for(doc, ms["capoly"], ms)
    assert h["K_sp"] == "log10_ksp_hap" and a["K_sp"] == "log10_ksp_acp" and "n_hyd" in a and "n_hyd" not in h
    assert "a_Ca" not in h and c["a_Ca"] == "a_ca_cameta"           # speciation supplies a_Ca for apatite, not for capoly
    ctl = ph_dry.bindings_for(doc, ms["hap"], ms, drop=["gamma_sl0", "Gamma_s"], control=True)
    assert "gamma_sl" in ctl and "gamma_sl0" not in ctl and "Gamma_s" not in ctl


# ------------------------------------------------------------------ carbonate regression against the committed W4.3b documents
@pytest.mark.parametrize("doc,prior_set,links", [
    ("results/preprint/screen/table_adm/summary.json", "table", {"speciation"}),
    ("results/preprint/screen/ignorance_adm/summary.json", "ignorance", {"anchor", "nucleate", "sequester", "speciation"})])
def test_carbonate_reproduces_the_committed_w43b_document(doc, prior_set, links):
    sid, rp, entry, cfg = ph_regress.primary_state(ROOT, doc, prior_set)
    res = ph_regress.compare(ph_regress.rerun(rp, entry, cfg), entry)
    assert set(res) == links
    bad = {(l, q): r for l, qs in res.items() for q, r in qs.items() if not r["within_tolerance"]}
    assert bad == {}
    assert max(r["max_rel_diff"] for qs in res.values() for r in qs.values()) < 1e-9
