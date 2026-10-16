"""Anchor DFT protocol test (P0-W5.2, task D): a small case run end to end on the laptop.

    uv run python -m nacre.anchor.protocol_test run

Thermodynamic question: with the level in PROTOCOL.md, what free energy does the binding cycle

    [Ca(H2O)6]2+ (aq) + OAc- (aq) -> [Ca(OAc)(H2O)4]+ (aq) + (H2O)2 (aq, as liquid water)

give, how long does each step take on this machine, and is a single point deterministic? The
number is a pipeline test. It is compared with W1's single-source keys and is never a parameter.

Rule R10 (memory): before every xtb, CREST or DFT step the free-memory percentage from
`memory_pressure` is read; below 25 % the step waits five minutes and rechecks, for up to 45
minutes, then the DFT test is recorded as outstanding. DFT runs with OMP_NUM_THREADS=2 and a
2500 MB cap, one heavy computation at a time, each single point in its own process.
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from nacre.anchor import cycle, protocol
from nacre.pourbaix import inputs, provenance

REPO = Path(__file__).resolve().parents[3]
STRUCT = REPO / "results" / "preprint" / "anchor" / "structures"
OUT = REPO / "results" / "preprint" / "anchor" / "protocol_test"
XTB_ENV = Path.home() / ".nacre-envs" / "xtb"
D3_ENV = Path.home() / ".nacre-envs" / "dftd3"
MEM_FLOOR = 25
MEM_WAIT_S = 300
MEM_MAX_WAIT_S = 45 * 60
DFT_THREADS = 2
DFT_MAX_MEMORY_MB = 2500

SPECIES = {  # name -> role in the cycle
    "Ca_aqua_w6": "aqua ion (m = 6)",
    "ligand_acetate": "free ligand",
    "Ca_acetate_bidentate_w4": "complex (n = 4, bidentate)",
    "water_w2": "released waters as one (H2O)2 cluster",
}
CREST_SPECIES = "Ca_acetate_bidentate_w4"  # the smallest complex (nacre.anchor.xtb_smoke)


def _hartree_constant():
    from scipy import constants

    return constants.physical_constants["Hartree energy"][0] * constants.N_A


EH = _hartree_constant()  # J mol^-1 per Eh, from CODATA via scipy


def free_memory_percent():
    out = subprocess.run(["memory_pressure"], capture_output=True, text=True).stdout.strip().splitlines()
    m = re.search(r"(\d+)%", out[-1]) if out else None
    return int(m.group(1)) if m else None


def memory_gate(log, step):
    waited = 0
    while True:
        pct = free_memory_percent()
        log.append({"step": step, "utc": provenance.utc_now(), "free_percent": pct, "waited_s": waited})
        if pct is not None and pct >= MEM_FLOOR:
            return True
        if waited >= MEM_MAX_WAIT_S:
            return False
        time.sleep(MEM_WAIT_S)
        waited += MEM_WAIT_S


def species_meta(name):
    idx = json.loads((STRUCT / "index.json").read_text(encoding="utf-8"))["species"]
    return next(s for s in idx if s["name"] == name)


def _read_xyz(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    n = int(lines[0])
    return [(ln.split()[0], [float(v) for v in ln.split()[1:4]]) for ln in lines[2:2 + n]]


def _write_xyz(path, atoms, comment=""):
    body = "\n".join("%-2s %15.8f %15.8f %15.8f" % (s, *x) for s, x in atoms)
    Path(path).write_text("%d\n%s\n%s\n" % (len(atoms), comment, body), encoding="utf-8")


def _xtb_env():
    return dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OMP_STACKSIZE="1G")


def crest(name, workdir):
    """CREST conformer search (GFN2-xTB, ALPB water, quick mode, one thread)."""
    meta = species_meta(name)
    shutil.copy(STRUCT / (name + ".xyz"), workdir / "in.xyz")
    cmd = [str(XTB_ENV / "bin" / "crest"), "in.xyz", "--gfn2", "--alpb", "water", "--chrg", str(meta["charge"]),
           "--uhf", "0", "-T", "1", "--quick"]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, env=_xtb_env())
    wall = time.time() - t0
    text = p.stdout + p.stderr
    n_conf = None
    ens = workdir / "crest_conformers.xyz"
    if ens.is_file():
        n_conf = sum(1 for ln in ens.read_text().splitlines() if ln.strip().isdigit())
    ok = p.returncode == 0 and (workdir / "crest_best.xyz").is_file()
    return {"species": name, "status": "ok" if ok else "failed", "returncode": p.returncode, "wall_s": round(wall, 1),
            "command": " ".join(["crest"] + cmd[1:]), "n_conformers": n_conf, "threads": 1,
            "normal_termination": "CREST terminated normally" in text,
            "best": str(workdir / "crest_best.xyz") if ok else None}


def xtb_ohess(name, xyz, workdir):
    """GFN2-xTB/ALPB(water) optimisation and frequencies: geometry and G(RRHO) at 298.15 K."""
    meta = species_meta(name)
    shutil.copy(xyz, workdir / "in.xyz")
    cmd = [str(XTB_ENV / "bin" / "xtb"), "in.xyz", "--ohess", "normal", "--gfn", "2", "--chrg", str(meta["charge"]),
           "--uhf", "0", "--alpb", "water", "-P", "1"]
    t0 = time.time()
    p = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, env=_xtb_env())
    wall = time.time() - t0
    text = p.stdout + p.stderr
    g = re.findall(r"G\(RRHO\) contrib\.\s+(-?[0-9.]+)\s+Eh", text)
    e = re.findall(r"TOTAL ENERGY\s+(-?[0-9.]+)\s+Eh", text)
    imag = re.search(r"imaginary freq\.\s+:?\s*(\d+)|# imaginary freq\.\s+(\d+)", text)
    n_imag = int(next(x for x in imag.groups() if x)) if imag else None
    ok = p.returncode == 0 and bool(g) and (workdir / "xtbopt.xyz").is_file()
    return {"status": "ok" if ok else "failed", "returncode": p.returncode, "wall_s": round(wall, 1),
            "command": " ".join(["xtb"] + cmd[1:]), "G_RRHO_Eh": float(g[-1]) if g else None,
            "E_xtb_Eh": float(e[-1]) if e else None, "n_imaginary": n_imag,
            "geometry": _read_xyz(workdir / "xtbopt.xyz") if ok else None}


def d3bj(atoms, charge):
    """D3(BJ) energy (Eh) with the HSE06 parameters of the simple-dftd3 parameter file."""
    with tempfile.TemporaryDirectory() as tmp:
        _write_xyz(Path(tmp) / "m.xyz", atoms)
        p = subprocess.run([str(D3_ENV / "bin" / "s-dftd3"), "run", "--bj", "hse06", "--json", "d3.json", "m.xyz"],
                           cwd=tmp, capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError("s-dftd3 failed: %s" % p.stderr[-300:])
        d = json.loads((Path(tmp) / "d3.json").read_text())
        v = subprocess.run([str(D3_ENV / "bin" / "s-dftd3"), "--version"], capture_output=True, text=True).stdout.strip()
    return {"E_disp_Eh": d["energy"], "damping": d["damping parameters"], "program": v}


# ------------------------------------------------------------------- single point (subprocess)
def single_point(xyz, charge, solvent, out_json, basis=None):
    """One DFT single point in this process (called through the `sp` subcommand)."""
    import resource

    from pyscf import dft, gto, lib

    lib.num_threads(DFT_THREADS)
    atoms = _read_xyz(xyz)
    mol = gto.M(atom=[[s, x] for s, x in atoms], charge=charge, spin=0, basis=basis or protocol.LEVEL["basis"],
                max_memory=DFT_MAX_MEMORY_MB, verbose=3)
    mf = dft.RKS(mol).density_fit(auxbasis=protocol.LEVEL["density_fitting"])
    mf.xc = protocol.LEVEL["functional"]
    mf.conv_tol = 1e-10
    mf.max_memory = DFT_MAX_MEMORY_MB
    cds_note = None
    if solvent:
        mf = mf.SMD()
        mf.with_solvent.solvent = "water"
        mf.with_solvent.max_memory = DFT_MAX_MEMORY_MB
        # the PyPI build lacks the compiled CDS term: run the SMD electrostatics only (IEF-PCM, SMD radii)
        mf.with_solvent.get_cds = lambda *a, **k: 0.0
        cds_note = "SMD electrostatics only (IEF-PCM with SMD radii); CDS term set to zero"
    t0 = time.time()
    e = mf.kernel()
    wall = time.time() - t0
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    rss_mb = rss / 1024 / 1024 if sys.platform == "darwin" else rss / 1024
    res = {"E_Eh": float(e), "converged": bool(mf.converged), "wall_s": round(wall, 2), "nao": int(mol.nao),
           "n_electrons": int(mol.nelectron), "solvent": bool(solvent), "solvent_note": cds_note,
           "threads": int(lib.num_threads()), "threads_requested": DFT_THREADS, "peak_rss_MB": round(rss_mb, 1), "basis": mol.basis,
           "xc": mf.xc, "auxbasis": protocol.LEVEL["density_fitting"], "pyscf": __import__("pyscf").__version__}
    Path(out_json).write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    return res


def run_sp(xyz, charge, solvent, log, step, basis=None):
    if not memory_gate(log, step):
        return {"status": "outstanding", "reason": "free memory below %d %% for 45 minutes (R10)" % MEM_FLOOR}
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sp.json"
        env = dict(os.environ, OMP_NUM_THREADS=str(DFT_THREADS), MKL_NUM_THREADS=str(DFT_THREADS),
                   PYSCF_MAX_MEMORY=str(DFT_MAX_MEMORY_MB))
        cmd = [sys.executable, "-m", "nacre.anchor.protocol_test", "sp", str(xyz), str(charge),
               "1" if solvent else "0", str(out)] + ([basis] if basis else [])
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=REPO)
        wall = time.time() - t0
        if p.returncode != 0 or not out.is_file():
            return {"status": "failed", "returncode": p.returncode, "stderr_tail": p.stderr[-800:]}
        res = json.loads(out.read_text())
    res["status"] = "ok"
    res["process_wall_s"] = round(wall, 2)
    return res


# ---------------------------------------------------------------------------------- the run
def run(out=OUT, params_sha=protocol.PARAMS_SHA):
    params = inputs.Params(inputs.load_snapshot(params_sha, check_git=False))
    out = Path(out)
    (out / "geometries").mkdir(parents=True, exist_ok=True)
    mem_log, record = [], {"species": {}, "level": protocol.LEVEL}
    T = 298.15
    work = Path(tempfile.mkdtemp(prefix="w52-"))
    try:
        # 1. conformer search on the smallest complex
        if not memory_gate(mem_log, "crest"):
            record["crest"] = {"status": "outstanding", "reason": "memory gate (R10)"}
        else:
            cw = work / "crest"
            cw.mkdir()
            record["crest"] = crest(CREST_SPECIES, cw)
        # 2. geometries and thermal corrections
        for name in SPECIES:
            src = STRUCT / (name + ".xyz")
            if name == CREST_SPECIES and record["crest"].get("status") == "ok":
                src = Path(record["crest"]["best"])
            if not memory_gate(mem_log, "xtb %s" % name):
                record["species"][name] = {"xtb": {"status": "outstanding"}}
                continue
            xw = work / ("xtb_" + name)
            xw.mkdir()
            x = xtb_ohess(name, src, xw)
            geo = out / "geometries" / (name + ".xyz")
            if x["geometry"]:
                _write_xyz(geo, x["geometry"], "%s GFN2-xTB/ALPB(water) optimised (P0-W5.2 protocol test)" % name)
            x.pop("geometry")
            record["species"][name] = {"role": SPECIES[name], "charge": species_meta(name)["charge"],
                                       "xtb": x, "geometry": geo.relative_to(REPO).as_posix()}
        # 3. dispersion and single points
        for name, rec in record["species"].items():
            if rec["xtb"].get("status") != "ok":
                continue
            geo = REPO / rec["geometry"]
            rec["d3"] = d3bj(_read_xyz(geo), rec["charge"])
            rec["sp_gas"] = run_sp(geo, rec["charge"], False, mem_log, "dft gas %s" % name)
            rec["sp_solv"] = run_sp(geo, rec["charge"], True, mem_log, "dft solvent %s" % name)
        # 4. determinism: rerun one single point in a fresh process
        aqua = record["species"].get("Ca_aqua_w6", {})
        if aqua.get("sp_gas", {}).get("status") == "ok":
            again = run_sp(REPO / aqua["geometry"], aqua["charge"], False, mem_log, "dft gas rerun Ca_aqua_w6")
            d = abs(again["E_Eh"] - aqua["sp_gas"]["E_Eh"]) if again.get("status") == "ok" else None
            record["determinism"] = {"species": "Ca_aqua_w6", "phase": "gas", "first_Eh": aqua["sp_gas"]["E_Eh"],
                                     "second_Eh": again.get("E_Eh"), "abs_diff_Eh": d,
                                     "deterministic": d is not None and d < 1e-8, "tolerance_Eh": 1e-8,
                                     "rerun_wall_s": again.get("wall_s")}
        record["cycle"] = binding_cycle(record, params, T)
        record["scaling"] = scaling_estimate(record)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    record["memory_log"] = mem_log
    return record


def g_star(rec, T):
    """Solution free energy (J mol^-1) of one species and its terms."""
    e_gas = rec["sp_gas"]["E_Eh"] * EH
    dsolv = (rec["sp_solv"]["E_Eh"] - rec["sp_gas"]["E_Eh"]) * EH
    disp = rec["d3"]["E_disp_Eh"] * EH
    grrho = rec["xtb"]["G_RRHO_Eh"] * EH
    ss = cycle.standard_state_correction(T)
    return {"E_el": e_gas, "E_disp": disp, "dG_solv": dsolv, "G_RRHO": grrho, "dG_1atm_to_1M": ss,
            "G_star": e_gas + disp + dsolv + grrho + ss}


def binding_cycle(record, params, T):
    """[Ca(H2O)6]2+ + OAc- -> [Ca(OAc)(H2O)4]+ + (H2O)2, water released as one cluster."""
    from pymatgen.core import Composition

    sp = record["species"]
    need = ("Ca_aqua_w6", "ligand_acetate", "Ca_acetate_bidentate_w4", "water_w2")
    if any(sp.get(n, {}).get("sp_solv", {}).get("status") != "ok" or sp.get(n, {}).get("sp_gas", {}).get("status") != "ok"
           for n in need):
        return {"status": "outstanding", "reason": "a single point did not run"}
    g = {n: g_star(sp[n], T) for n in need}
    m, n_w = 6, 4
    k = m - n_w
    # liquid-water reference of the released cluster: RT ln([H2O]/k), [H2O] from the W1 density
    rho = float(params.value("water_density"))  # kg m^-3
    m_h2o = float(Composition("H2O").weight) / 1000.0  # kg mol^-1 from the atomic weights
    c_w = rho / m_h2o / 1000.0  # mol L^-1
    water_term = _R() * T * math.log(c_w / k)
    dg = (g["Ca_acetate_bidentate_w4"]["G_star"] + g["water_w2"]["G_star"] + water_term
          - g["Ca_aqua_w6"]["G_star"] - g["ligand_acetate"]["G_star"])
    parts = {t: (g["Ca_acetate_bidentate_w4"][t] + g["water_w2"][t] - g["Ca_aqua_w6"][t] - g["ligand_acetate"][t])
             for t in ("E_el", "E_disp", "dG_solv", "G_RRHO", "dG_1atm_to_1M")}
    lk = float(params.value("log10_k_ca_carboxylate"))
    return {
        "status": "ok", "reaction": "[Ca(H2O)6]2+ + OAc- -> [Ca(OAc)(H2O)4]+ + (H2O)2", "water_mode": "cluster",
        "stoichiometry": cycle.stoichiometry(m, n_w, "cluster"), "T_K": T,
        "dG_bind_J_per_mol": dg, "terms_J_per_mol": {**parts, "RT_ln_H2O_over_k": water_term},
        "net_standard_state_check": cycle.net_standard_state_correction(T, m, n_w, "cluster"),
        "water_concentration_mol_per_L": c_w, "water_density_source": params.cite("water_density"),
        "comparators": {"dg_bind_ca_acetate": {**params.cite("dg_bind_ca_acetate"),
                                               "value_J_per_mol": float(params.value("dg_bind_ca_acetate"))},
                        "log10_k_ca_carboxylate": {**params.cite("log10_k_ca_carboxylate"), "value": lk,
                                                   "as_dG_J_per_mol": -_R() * T * math.log(10.0) * lk}},
        "error_budget": {"electronic": params.cite("m_seq_method_error"),
                         "electronic_J_per_mol": float(params.value("m_seq_method_error")),
                         "solvation_rows": ["TE-067", "TE-081"]},
        "status_note": "pipeline test at a reduced protocol (SMD without CDS, xtb thermal terms); never a parameter",
    }


def _R():
    from scipy import constants

    return constants.R


def scaling_estimate(record, vcpu=32, ram_gb=128, efficiency=0.6, conformers=5, jobs_in_parallel=4):
    """Wall time of the production set on a 32 vCPU / 128 GB pod from the measured single points.

    Fit t = a nao^p to the measured gas and solvent single points, scale to the production
    species (every structure in the index, `conformers` CREST conformers per complex, gas and
    solvent single points each) and divide by the thread gain. `efficiency` and the job layout are
    planning assumptions, stated as such, not measurements.
    """
    import numpy as np
    from pyscf import gto

    pts = []
    for rec in record["species"].values():
        for key in ("sp_gas", "sp_solv"):
            r = rec.get(key, {})
            if r.get("status") == "ok":
                pts.append((r["nao"], r["wall_s"], key))
    if len(pts) < 3:
        return {"status": "outstanding", "reason": "too few single points for a fit"}
    out = {}
    idx = json.loads((STRUCT / "index.json").read_text(encoding="utf-8"))["species"]
    nao = {}
    for s in idx:
        atoms = _read_xyz(STRUCT / (s["name"] + ".xyz"))
        mol = gto.M(atom=[[a, x] for a, x in atoms], charge=s["charge"], spin=0, basis=protocol.LEVEL["basis"], verbose=0)
        nao[s["name"]] = int(mol.nao)
    for key in ("sp_gas", "sp_solv"):
        xs = np.array([p[0] for p in pts if p[2] == key], float)
        ys = np.array([p[1] for p in pts if p[2] == key], float)
        p_exp, ln_a = np.polyfit(np.log(xs), np.log(ys), 1)
        out[key] = {"exponent": float(p_exp), "prefactor_s": float(np.exp(ln_a)), "n_points": len(xs)}
    thread_gain = (vcpu / jobs_in_parallel) / record["species"]["Ca_aqua_w6"]["sp_gas"]["threads"] * efficiency
    total_laptop = 0.0
    per = {}
    for s in idx:
        n_struct = conformers if s["kind"] == "complex" else 1
        t = sum(out[k]["prefactor_s"] * nao[s["name"]] ** out[k]["exponent"] for k in ("sp_gas", "sp_solv")) * n_struct
        per[s["name"]] = {"nao": nao[s["name"]], "structures": n_struct, "laptop_2_threads_s": t}
        total_laptop += t
    pod_wall = total_laptop / thread_gain / jobs_in_parallel
    peak = max((rec.get(k, {}).get("peak_rss_MB") or 0) for rec in record["species"].values() for k in ("sp_gas", "sp_solv"))
    return {"fits": out, "per_species": per, "laptop_total_s": total_laptop,
            "pod": {"vcpu": vcpu, "ram_GB": ram_gb, "jobs_in_parallel": jobs_in_parallel,
                    "threads_per_job": vcpu // jobs_in_parallel, "parallel_efficiency_assumed": efficiency,
                    "conformers_per_complex_assumed": conformers, "wall_s_estimate": pod_wall,
                    "memory_per_job_GB_needed": round(peak / 1024 * 2, 2),
                    "memory_note": "measured laptop peak RSS doubled for headroom; well below 128 GB / jobs"},
            "excluded": "DFT geometry optimisations and DFT frequencies (the test uses GFN2-xTB for both); "
                        "if production adds them, multiply by the number of gradient and Hessian steps"}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.anchor.protocol_test")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("run")
    s = sub.add_parser("sp")
    s.add_argument("xyz")
    s.add_argument("charge", type=int)
    s.add_argument("solvent", type=int)
    s.add_argument("out")
    s.add_argument("basis", nargs="?")
    args = ap.parse_args(argv)
    if args.cmd == "sp":
        single_point(args.xyz, args.charge, bool(args.solvent), args.out, args.basis)
        return 0
    rec = run()
    rec.update({"session": "P0-W5.2", "generated_utc": provenance.utc_now(),
                "question": "binding free energy of acetate to hydrated Ca2+ by the protocol of PROTOCOL.md, "
                            "timings, determinism and a production estimate (pipeline test, not a parameter)",
                "git_sha": provenance.git_sha(), "git_dirty": provenance.git_dirty(),
                "params_sha": protocol.PARAMS_SHA})
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "summary.json"
    path.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    outs = [path] + sorted((OUT / "geometries").glob("*.xyz"))
    provenance.ledger_append(REPO / "jobs" / "ledger" / "p0-w5.jsonl", {
        "session": "P0-W5.2", "run": "anchor-protocol-test", "kind": "dft-test", "mock": False,
        "utc": rec["generated_utc"], "git_sha": rec["git_sha"], "git_dirty": rec["git_dirty"],
        "params_sha": protocol.PARAMS_SHA,
        "outputs": [{"path": p.relative_to(REPO).as_posix(), "sha256": provenance.sha256_file(p)} for p in outs]})
    print(json.dumps({k: rec.get(k) for k in ("crest", "determinism", "cycle")}, indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
