"""Anchor production driver (P0-W5.4): cycles, the mock pipeline with resume, the bookkeeping, and the
consistency of the pod specs with the linux-64 lock. No xtb, CREST or DFT is run here."""
import json
import math
from pathlib import Path

import pytest
import yaml

from nacre.anchor import cycle
from nacre.anchor import production as P

REPO = Path(__file__).resolve().parents[2]
SPECS = REPO / "jobs" / "preprint" / "specs"
LOCK = REPO / "src" / "nacre" / "anchor" / "pod_env_linux64.lock"


def test_cycles_follow_the_structure_index():
    cyc = {c["complex"]: c for c in P.cycles(P.species_index())}
    assert set(cyc) == {"Ca_catecholate_monoanion_bidentate_w4", "Ca_catecholate_dianion_bidentate_w4",
                        "Ca_acetate_monodentate_w5", "Ca_acetate_bidentate_w4"}
    assert cyc["Ca_acetate_monodentate_w5"]["water"] == "water_w1" and cyc["Ca_acetate_monodentate_w5"]["k"] == 1
    assert cyc["Ca_acetate_bidentate_w4"]["water"] == "water_w2" and cyc["Ca_acetate_bidentate_w4"]["k"] == 2
    assert cyc["Ca_catecholate_dianion_bidentate_w4"]["ligand"] == "ligand_catecholate_dianion"
    assert all(c["aqua"] == "Ca_aqua_w6" and c["m"] == 6 for c in cyc.values())


def test_read_ensemble(tmp_path):
    p = tmp_path / "crest_conformers.xyz"
    p.write_text("3\n -5.07000000\nO 0 0 0\nH 0 0 1\nH 0 1 0\n3\n -5.06900000\nO 0 0 0\nH 0 0 1.1\nH 0 1 0\n")
    ens = P.read_ensemble(p)
    assert [e for e, _ in ens] == [-5.07, -5.069] and len(ens[1][1]) == 3


def test_g_star_sums_its_terms():
    rec = {"sp_gas": {"E_Eh": -76.0, "E_disp_Eh": -0.001}, "sp_smd": {"E_Eh": -76.01}, "xtb": {"G_RRHO_Eh": 0.002}}
    g = P.g_star(rec)
    eh = P._eh()
    assert g["dG_solv_J_per_mol"] == pytest.approx(-0.01 * eh)
    assert g["dG_1atm_to_1M_J_per_mol"] == pytest.approx(cycle.standard_state_correction(P.T_K))
    assert g["G_star_J_per_mol"] == pytest.approx(g["E_el_disp_J_per_mol"] + g["dG_solv_J_per_mol"]
                                                  + g["G_RRHO_J_per_mol"] + g["dG_1atm_to_1M_J_per_mol"])


def test_mock_pipeline_runs_every_cycle_and_resumes(tmp_path):
    out = tmp_path / "run"
    s = P.run(out, "mock", jobs=4, threads=2)
    assert s["mock"] is True and all(v["status"] == "ok" for v in s["species"].values())
    assert len(s["species"]) == len(P.species_index())
    for c in s["cycles"]:
        assert c["status"] == "ok" and math.isfinite(c["dG_bind_J_per_mol"])
        # two solutes in, two out: the 1 atm -> 1 M terms cancel and the check agrees
        assert c["terms_J_per_mol"]["dG_1atm_to_1M_J_per_mol"] == pytest.approx(0.0, abs=1e-6)
        assert c["net_standard_state_check_J_per_mol"] == pytest.approx(0.0, abs=1e-9)
        assert c["terms_J_per_mol"]["RT_ln_H2O_over_k"] > 0
    stamp = {p: p.stat().st_mtime_ns for p in out.glob("species/*/conf*.json")}
    s2 = P.run(out, "mock", jobs=4, threads=2)
    assert {p: p.stat().st_mtime_ns for p in out.glob("species/*/conf*.json")} == stamp  # finished steps skipped
    assert [c["dG_bind_J_per_mol"] for c in s2["cycles"]] == [c["dG_bind_J_per_mol"] for c in s["cycles"]]


def test_conformer_window_and_cap(tmp_path):
    out = tmp_path / "run"
    P.run(out, "mock", jobs=1, threads=1, max_conformers=2, species=["ligand_acetate"])
    rec = json.loads((out / "species" / "ligand_acetate" / "species.json").read_text())
    assert rec["conformers_considered"] <= 2


def _spec(name):
    return yaml.safe_load((SPECS / name).read_text(encoding="utf-8"))


def test_production_spec_is_pinned_and_builds_smd():
    s = _spec("anchor_production.yaml")
    assert s["mock"] is False and s["launcher"] == "tmux"
    inst = s["install_command"]
    assert "-DENABLE_SMD=ON" in inst
    assert inst.count("sha256sum -c -") == 2  # micromamba and the PySCF source
    assert "src/src/nacre/anchor/pod_env_linux64.lock" in inst
    # the dispersion add-on comes after the source build and without deps, so it cannot replace it
    assert inst.index("./pyscf-2.14.0.tar.gz") < inst.index("pyscf-dispersion==1.5.0")
    assert "--no-deps --disable-pip-version-check pyscf-dispersion" in inst
    assert all("==" in p for p in s["packages"])
    assert "-m nacre.anchor.production run" in s["command"] and "--backend real" in s["command"]


def test_dry_run_spec_runs_the_same_command_with_the_mock_backend():
    prod, dry = _spec("anchor_production.yaml"), _spec("anchor_production_dryrun.yaml")
    assert dry["mock"] is True
    tail = lambda c: c.split("-m nacre.anchor.production run", 1)[1]  # noqa: E731
    assert tail(dry["command"]).replace("--backend mock", "") == tail(prod["command"]).replace("--backend real", "")


def test_lock_carries_the_linux_builds_of_the_env_file():
    env = yaml.safe_load((REPO / "src" / "nacre" / "anchor" / "pod_env_linux64.yaml").read_text())
    lines = [ln for ln in LOCK.read_text().splitlines() if ln.startswith("https://")]
    assert lines and all("/linux-64/" in ln or "/noarch/" in ln for ln in lines)
    assert all(len(ln.rsplit("#", 1)[1]) == 32 for ln in lines)  # md5 per package
    for dep in env["dependencies"]:
        parts = dep.split("=")
        if len(parts) == 3 and "*" not in dep:
            name, ver, build = parts
            assert any("/%s-%s-%s." % (name, ver, build) in ln for ln in lines), dep
    assert any("/libgfortran5-13.4.0-" in ln for ln in lines)


def test_cds_status_is_reported_with_a_reason():
    st = P.smd_cds_status()
    assert "active" in st
    if not st["active"]:
        assert st["reason"]
