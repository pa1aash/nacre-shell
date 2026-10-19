"""Anchor production driver (P0-W5.4, task 1e; lane note N27): CREST, GFN2-xTB thermal terms and DFT
single points on every anchor and reference species, then the binding free energies of the cycle.

    python -m nacre.anchor.production check-env --out <dir>                 # tools, versions, SMD CDS term
    python -m nacre.anchor.production run --out <dir> --jobs 4 --threads 8  # the production set (pod)
    python -m nacre.anchor.production run --out <dir> --backend mock        # plumbing only (dry run)

Thermodynamic question: what is the free energy of replacing first-shell waters of hydrated Ca2+ by
acetate (mono- and bidentate) and catecholate (mono- and dianion, bidentate) in water, at the level of
PROTOCOL.md with the full SMD model (electrostatics and the CDS term)? A consistency check of the
pipeline (src/nacre/anchor/README.md); never a screen input. The literature comparison is a later
session's step and is not made here.

Per species (results/preprint/anchor/structures/index.json, starting geometries from the builder):
1. CREST conformer search, GFN2-xTB/ALPB(water) (water_w1 has one structure and is not searched);
2. the lowest `max_conformers` conformers within `ewin_kcal` of the CREST minimum: GFN2-xTB/ALPB(water)
   optimisation and frequencies (G_RRHO at 298.15 K), restarted from xtb's distorted geometry while an
   imaginary mode remains;
3. HSE06/def2-TZVP (all-electron Ca, density fitting def2-universal-jkfit) with D3(BJ), in the gas phase and
   with SMD(water); Delta_G_solv = E(SMD) - E(gas) at the same geometry, the CDS term included when the
   build has it (check-env says so; if not, the electrostatic part is run and the departure flagged);
4. G* = E_el+disp + Delta_G_solv + G_RRHO + Delta_G(1 atm -> 1 M); the species takes its lowest-G* conformer
   (TE-087: DFT re-ranks the semi-empirical ensemble); the Boltzmann ensemble value is a sensitivity.

Cycles: [Ca(H2O)6]2+ + L -> [Ca L (H2O)n] + (H2O)k, k = 6 - n, the released waters as one cluster
(water_w<k>) with one standard-state correction and RT ln([H2O]/k) (nacre.anchor.cycle; README.md).

Every step writes its record under <out>/species/<name>/ before the next starts, and a rerun skips the
steps that finished (resume after an interruption). Species run in parallel, `jobs` at a time, each step
with `threads` OpenMP threads. The mock backend writes the same records from deterministic stand-in
numbers, marked mock, so the dry run exercises the orchestration and the cycle without any chemistry.
"""
import argparse
import concurrent.futures as cf
import hashlib
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

REPO = Path(__file__).resolve().parents[3]
STRUCT = REPO / "results" / "preprint" / "anchor" / "structures"
PARAMS_SHA = "8bc15c88f5f4a28e64d394186729836bac01cfec"  # params at p0-cp3 (water density)
T_K = 298.15
AQUA = "Ca_aqua_w6"
DRIVER_VERSION = "1.0.0"

LEVEL = dict(protocol.LEVEL, solvent_run="SMD (water), electrostatics and CDS; the CDS term from the "
                                         "ENABLE_SMD build (check-env), or flagged and omitted if absent",
             dispersion_run="D3(BJ) HSE06 parameters via the DFT library's dispersion add-on",
             conformers="CREST (GFN2-xTB/ALPB water, default mode); lowest max_conformers within ewin_kcal, "
                        "re-ranked by G* (TE-087)")
DEFAULTS = {"max_conformers": 5, "ewin_kcal": 3.0, "jobs": 4, "threads": 8, "max_memory_mb": 24000}


def _eh():
    from scipy import constants

    return constants.physical_constants["Hartree energy"][0] * constants.N_A


def _kcal():
    from scipy import constants

    return constants.calorie * 1000.0  # J per kcal (thermochemical)


def _R():
    from scipy import constants

    return constants.R


def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def read_xyz(path):
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    n = int(lines[0])
    return [(ln.split()[0], [float(v) for v in ln.split()[1:4]]) for ln in lines[2:2 + n]]


def write_xyz(path, atoms, comment=""):
    body = "\n".join("%-2s %15.8f %15.8f %15.8f" % (s, *x) for s, x in atoms)
    Path(path).write_text("%d\n%s\n%s\n" % (len(atoms), comment, body), encoding="utf-8")


def read_ensemble(path):
    """CREST ensemble: [(energy_Eh, atoms)] from crest_conformers.xyz (energy in the comment line)."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    out, i = [], 0
    while i < len(lines):
        if not lines[i].strip():
            i += 1
            continue
        n = int(lines[i])
        e = float(re.findall(r"-?\d+\.\d+", lines[i + 1])[0])
        atoms = [(ln.split()[0], [float(v) for v in ln.split()[1:4]]) for ln in lines[i + 2:i + 2 + n]]
        out.append((e, atoms))
        i += 2 + n
    return out


def species_index():
    return json.loads((STRUCT / "index.json").read_text(encoding="utf-8"))["species"]


def cycles(index):
    """The binding cycles implied by the structure index: every complex against the aqua ion, its free
    ligand and the released-water cluster."""
    by = {s["name"]: s for s in index}
    m = by[AQUA]["n_water"]
    out = []
    for s in index:
        if s["kind"] != "complex":
            continue
        lig = "ligand_" + s["name"].split("_", 1)[1].rsplit("_", 2)[0]
        k = m - s["n_water"]
        water = "water_w%d" % k
        if lig not in by or water not in by:
            raise ValueError("cycle of %s needs %s and %s" % (s["name"], lig, water))
        out.append({"complex": s["name"], "ligand": lig, "aqua": AQUA, "water": water, "m": m, "n": s["n_water"],
                    "k": k, "reaction": "[Ca(H2O)%d]2+ + %s -> %s + (H2O)%d" % (m, lig, s["name"], k)})
    return out


# ================================================================================= backends
class RealBackend:
    """xtb and CREST from PATH (the pod environment), DFT through the `sp` subcommand in a fresh process."""

    name = "real"
    mock = False

    def __init__(self, threads, max_memory_mb):
        self.threads, self.max_memory_mb = int(threads), int(max_memory_mb)

    def env(self):
        n = str(self.threads)
        return dict(os.environ, OMP_NUM_THREADS=n, MKL_NUM_THREADS=n, OPENBLAS_NUM_THREADS=n, OMP_STACKSIZE="1G",
                    OMP_MAX_ACTIVE_LEVELS="1")

    def crest(self, xyz, charge, work):
        shutil.copy(xyz, work / "in.xyz")
        cmd = ["crest", "in.xyz", "--gfn2", "--alpb", "water", "--chrg", str(charge), "--uhf", "0", "-T", str(self.threads)]
        t0 = time.time()
        p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, env=self.env())
        (work / "crest.out").write_text(p.stdout + p.stderr, encoding="utf-8")
        ens = work / "crest_conformers.xyz"
        ok = p.returncode == 0 and ens.is_file() and "CREST terminated normally" in p.stdout + p.stderr
        return {"status": "ok" if ok else "failed", "returncode": p.returncode, "wall_s": round(time.time() - t0, 1),
                "command": " ".join(cmd), "ensemble": read_ensemble(ens) if ok else []}

    def ohess(self, atoms, charge, work, max_restarts=3):
        src = work / "start.xyz"
        write_xyz(src, atoms)
        attempts = []
        for k in range(max_restarts + 1):
            shutil.copy(src, work / "in.xyz")
            cmd = ["xtb", "in.xyz", "--ohess", "normal" if k == 0 else "tight", "--gfn", "2", "--chrg", str(charge),
                   "--uhf", "0", "--alpb", "water", "-P", str(self.threads)]
            t0 = time.time()
            p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, env=self.env())
            text = p.stdout + p.stderr
            g = re.findall(r"G\(RRHO\) contrib\.\s+(-?[0-9.]+)\s+Eh", text)
            imag = re.findall(r"# imaginary freq\.\s+(\d+)", text)
            r = {"returncode": p.returncode, "wall_s": round(time.time() - t0, 1), "command": " ".join(cmd),
                 "G_RRHO_Eh": float(g[-1]) if g else None, "n_imaginary": int(imag[-1]) if imag else None}
            attempts.append(r)
            if p.returncode != 0 or r["n_imaginary"] == 0 or not (work / "xtbhess.xyz").is_file():
                break
            shutil.copy(work / "xtbhess.xyz", src)
        last = attempts[-1]
        geo = work / "xtbopt.xyz"
        ok = last["returncode"] == 0 and last["G_RRHO_Eh"] is not None and last["n_imaginary"] == 0 and geo.is_file()
        return {"status": "ok" if ok else "failed", "attempts": attempts, "G_RRHO_Eh": last["G_RRHO_Eh"],
                "n_imaginary": last["n_imaginary"], "geometry": read_xyz(geo) if geo.is_file() else None}

    def single_point(self, atoms, charge, solvent, work):
        xyz = work / ("sp_%s.xyz" % ("smd" if solvent else "gas"))
        out = work / ("sp_%s.json" % ("smd" if solvent else "gas"))
        write_xyz(xyz, atoms)
        cmd = [sys.executable, "-m", "nacre.anchor.production", "sp", "--xyz", str(xyz), "--charge", str(charge),
               "--solvent", "1" if solvent else "0", "--threads", str(self.threads),
               "--max-memory-mb", str(self.max_memory_mb), "--out", str(out)]
        t0 = time.time()
        p = subprocess.run(cmd, capture_output=True, text=True, env=self.env(), cwd=REPO)
        if p.returncode != 0 or not out.is_file():
            return {"status": "failed", "returncode": p.returncode, "stderr_tail": p.stderr[-1500:]}
        res = json.loads(out.read_text(encoding="utf-8"))
        res.update({"status": "ok" if res.get("converged") else "failed", "process_wall_s": round(time.time() - t0, 1)})
        return res


class MockBackend:
    """Deterministic stand-in numbers for the dry run (no chemistry; every record says mock)."""

    name = "mock"
    mock = True

    def __init__(self, threads, max_memory_mb):
        self.threads = int(threads)

    @staticmethod
    def _h(*parts):
        return int(hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()[:12], 16) / float(16 ** 12)

    def crest(self, xyz, charge, work):
        atoms = read_xyz(xyz)
        ens = []
        for i in range(7):
            shift = [(s, [c + 1e-3 * i for c in x]) for s, x in atoms]
            ens.append((-10.0 * len(atoms) + 0.002 * i * (1 + self._h(xyz.name, i)), shift))
        time.sleep(0.2)
        return {"status": "ok", "returncode": 0, "wall_s": 0.2, "command": "mock crest", "ensemble": ens}

    def ohess(self, atoms, charge, work, max_restarts=3):
        time.sleep(0.1)
        g = 0.05 + 0.01 * len(atoms) * self._h("rrho", atoms[0][1][0])
        return {"status": "ok", "attempts": [{"command": "mock xtb", "wall_s": 0.1}], "G_RRHO_Eh": g, "n_imaginary": 0,
                "geometry": atoms}

    def single_point(self, atoms, charge, solvent, work):
        time.sleep(0.1)
        n = len(atoms)
        e = -20.0 * n - 0.01 * self._h("e", atoms[0][1][0], n)
        if solvent:
            e += -0.002 * n - 0.03 * charge ** 2
        return {"status": "ok", "E_Eh": e, "E_disp_Eh": -0.001 * n, "converged": True, "solvent": bool(solvent),
                "cds": {"active": bool(solvent), "e_cds_Eh": -0.0005 * n if solvent else None, "mock": True},
                "wall_s": 0.1, "nao": 20 * n, "threads": self.threads, "mock": True}


BACKENDS = {"real": RealBackend, "mock": MockBackend}


# ============================================================================== single point
def smd_cds_status():
    """Whether this PySCF build has the SMD CDS term: the compiled library is loadable and gives a
    non-zero CDS energy for a water molecule in water."""
    rec = {"utc": utc()}
    try:
        import pyscf
        from pyscf import gto
        from pyscf.solvent import smd
    except Exception as exc:  # noqa: BLE001
        return dict(rec, active=False, reason="pyscf not importable: %s" % exc)
    rec["pyscf"] = pyscf.__version__
    rec["libsolvent_loaded"] = smd.libsolvent is not None
    if smd.libsolvent is None:
        return dict(rec, active=False, reason="libsolvent not built (pyscf compiled without -DENABLE_SMD=ON)")
    mol = gto.M(atom="O 0 0 0.1173; H 0 0.7572 -0.4692; H 0 -0.7572 -0.4692", basis="sto-3g", verbose=0)
    s = smd.SMD(mol)
    s.solvent = "water"
    e = float(s.get_cds())
    return dict(rec, active=e != 0.0 and math.isfinite(e), e_cds_water_Eh=e,
                reason="" if e != 0.0 else "CDS energy of water is zero")


def single_point(xyz, charge, solvent, threads, max_memory_mb, out):
    """One DFT single point in this process (the `sp` subcommand)."""
    import resource

    import pyscf
    from pyscf import dft, gto, lib

    lib.num_threads(threads)
    atoms = read_xyz(xyz)
    mol = gto.M(atom=[[s, x] for s, x in atoms], charge=charge, spin=0, basis=LEVEL["basis"],
                max_memory=max_memory_mb, verbose=3)
    mf = dft.RKS(mol).density_fit(auxbasis=LEVEL["density_fitting"])
    mf.xc = LEVEL["functional"]
    disp = os.environ.get("NACRE_ANCHOR_DISP", "d3bj")  # "none" only for a local smoke without the add-on
    if disp != "none":
        mf.disp = disp
    mf.conv_tol = 1e-10
    mf.max_memory = max_memory_mb
    cds = None
    if solvent:
        cds = smd_cds_status()
        mf = mf.SMD()
        mf.with_solvent.solvent = "water"
        mf.with_solvent.max_memory = max_memory_mb
        if not cds["active"]:
            mf.with_solvent.get_cds = lambda *a, **k: 0.0  # flagged departure: electrostatics only
    t0 = time.time()
    e = mf.kernel()
    wall = time.time() - t0
    e_disp = (getattr(mf, "scf_summary", {}) or {}).get("dispersion")
    if solvent and cds["active"]:
        cds["e_cds_Eh"] = float(mf.with_solvent.e_cds) if mf.with_solvent.e_cds is not None else None
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    res = {"E_Eh": float(e), "E_disp_Eh": None if e_disp is None else float(e_disp), "converged": bool(mf.converged),
           "wall_s": round(wall, 2), "nao": int(mol.nao), "n_electrons": int(mol.nelectron), "solvent": bool(solvent),
           "cds": cds, "threads": int(lib.num_threads()), "peak_rss_MB": round(rss / 1024 / (1024 if sys.platform == "darwin" else 1), 1),
           "basis": LEVEL["basis"], "xc": mf.xc, "disp": disp, "auxbasis": LEVEL["density_fitting"], "pyscf": pyscf.__version__}
    Path(out).write_text(json.dumps(res, indent=1, sort_keys=True), encoding="utf-8")
    return res


# ================================================================================= pipeline
def _done(path):
    if Path(path).is_file():
        rec = json.loads(Path(path).read_text(encoding="utf-8"))
        if rec.get("status") == "ok":
            return rec
    return None


def _save(path, rec):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str), encoding="utf-8")
    tmp.replace(path)
    return rec


def run_species(s, out, backend, opts):
    """Steps 1-4 for one species; every finished step is a file under out/species/<name>/."""
    d = Path(out) / "species" / s["name"]
    d.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="anchor-%s-" % s["name"]))
    try:
        # 1. conformers
        crest_rec = _done(d / "crest.json")
        if crest_rec is None:
            if s["name"] == "water_w1":
                crest_rec = {"status": "ok", "skipped": "one structure", "ensemble": [(None, read_xyz(STRUCT / "water_w1.xyz"))]}
            else:
                cw = work / "crest"
                cw.mkdir()
                crest_rec = backend.crest(STRUCT / (s["name"] + ".xyz"), s["charge"], cw)
            crest_rec["mock"] = backend.mock
            _save(d / "crest.json", crest_rec)
            if crest_rec["status"] != "ok":
                return {"name": s["name"], "status": "failed", "step": "crest"}
        ens = crest_rec["ensemble"]
        e0 = min((e for e, _ in ens if e is not None), default=None)
        ewin = opts["ewin_kcal"] * _kcal() / _eh()
        picked = [i for i, (e, _) in enumerate(ens) if e is None or e - e0 <= ewin][:opts["max_conformers"]]
        # 2.-3. per conformer
        confs = []
        for i in picked:
            f = d / ("conf%02d.json" % i)
            rec = _done(f)
            if rec is None:
                rec = {"conformer": i, "crest_E_Eh": ens[i][0], "mock": backend.mock}
                cw = work / ("c%02d" % i)
                cw.mkdir(exist_ok=True)
                x = backend.ohess(ens[i][1], s["charge"], cw)
                rec["xtb"] = {k: v for k, v in x.items() if k != "geometry"}
                if x["status"] != "ok":
                    rec["status"] = "failed"
                    _save(f, rec)
                    continue
                rec["geometry"] = x["geometry"]
                rec["sp_gas"] = backend.single_point(x["geometry"], s["charge"], False, cw)
                rec["sp_smd"] = backend.single_point(x["geometry"], s["charge"], True, cw)
                ok = rec["sp_gas"].get("status") == "ok" and rec["sp_smd"].get("status") == "ok"
                rec["status"] = "ok" if ok else "failed"
                if ok:
                    rec["G"] = g_star(rec)
                _save(f, rec)
            confs.append(rec)
        good = [c for c in confs if c.get("status") == "ok"]
        if not good:
            return _save(d / "species.json", {"name": s["name"], "status": "failed", "step": "conformers", "mock": backend.mock})
        best = min(good, key=lambda c: c["G"]["G_star_J_per_mol"])
        RT = _R() * T_K
        gmin = best["G"]["G_star_J_per_mol"]
        ens_g = gmin - RT * math.log(sum(math.exp(-(c["G"]["G_star_J_per_mol"] - gmin) / RT) for c in good))
        write_xyz(d / "selected.xyz", best["geometry"], "%s conformer %d, lowest G* (%s)" % (s["name"], best["conformer"],
                                                                                         "mock" if backend.mock else "production"))
        cds = [c["sp_smd"].get("cds") or {} for c in good]
        return _save(d / "species.json", {
            "name": s["name"], "status": "ok", "charge": s["charge"], "kind": s["kind"], "mock": backend.mock,
            "conformers_considered": len(picked), "conformers_ok": len(good), "selected_conformer": best["conformer"],
            "G_star_J_per_mol": gmin, "G_star_ensemble_J_per_mol": ens_g, "terms": best["G"],
            "cds_active_all": all(c.get("active") for c in cds), "selected_geometry": "selected.xyz"})
    finally:
        shutil.rmtree(work, ignore_errors=True)


def g_star(rec):
    eh = _eh()
    e_gas = rec["sp_gas"]["E_Eh"] * eh
    dsolv = (rec["sp_smd"]["E_Eh"] - rec["sp_gas"]["E_Eh"]) * eh
    grrho = rec["xtb"]["G_RRHO_Eh"] * eh
    ss = cycle.standard_state_correction(T_K)
    return {"E_el_disp_J_per_mol": e_gas, "E_disp_J_per_mol": (rec["sp_gas"].get("E_disp_Eh") or 0.0) * eh,
            "dG_solv_J_per_mol": dsolv, "G_RRHO_J_per_mol": grrho, "dG_1atm_to_1M_J_per_mol": ss,
            "G_star_J_per_mol": e_gas + dsolv + grrho + ss}


def water_concentration(params):
    from ase.data import atomic_masses, atomic_numbers

    rho = float(params.value("water_density"))  # kg m^-3
    m = (2 * atomic_masses[atomic_numbers["H"]] + atomic_masses[atomic_numbers["O"]]) / 1000.0  # kg mol^-1
    return rho / m / 1000.0, params.cite("water_density")  # mol L^-1


def binding(species, cyc, params):
    c_w, src = water_concentration(params)
    RT = _R() * T_K
    out = []
    for c in cyc:
        need = [c["complex"], c["ligand"], c["aqua"], c["water"]]
        if any(species.get(n, {}).get("status") != "ok" for n in need):
            out.append({**c, "status": "outstanding", "missing": [n for n in need if species.get(n, {}).get("status") != "ok"]})
            continue
        g = {n: species[n]["G_star_J_per_mol"] for n in need}
        ge = {n: species[n]["G_star_ensemble_J_per_mol"] for n in need}
        wt = RT * math.log(c_w / c["k"])
        dg = g[c["complex"]] + g[c["water"]] + wt - g[c["aqua"]] - g[c["ligand"]]
        dge = ge[c["complex"]] + ge[c["water"]] + wt - ge[c["aqua"]] - ge[c["ligand"]]
        terms = {t: (species[c["complex"]]["terms"][t] + species[c["water"]]["terms"][t]
                     - species[c["aqua"]]["terms"][t] - species[c["ligand"]]["terms"][t])
                 for t in ("E_el_disp_J_per_mol", "dG_solv_J_per_mol", "G_RRHO_J_per_mol", "dG_1atm_to_1M_J_per_mol")}
        out.append({**c, "status": "ok", "water_mode": "cluster", "dG_bind_J_per_mol": dg,
                    "dG_bind_ensemble_J_per_mol": dge, "terms_J_per_mol": dict(terms, RT_ln_H2O_over_k=wt),
                    "net_standard_state_check_J_per_mol": cycle.net_standard_state_correction(T_K, c["m"], c["n"], "cluster"),
                    "water_concentration_mol_per_L": c_w, "water_density_source": src,
                    "cds_active": all(species[n].get("cds_active_all") for n in need)})
    return out


def run(out, backend_name="real", species=None, **opts):
    from nacre.pourbaix import inputs

    opts = dict(DEFAULTS, **{k: v for k, v in opts.items() if v is not None})
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    backend = BACKENDS[backend_name](opts["threads"], opts["max_memory_mb"])
    params = inputs.Params(inputs.load_snapshot(PARAMS_SHA, check_git=False))
    index = [s for s in species_index() if not species or s["name"] in species]
    cyc = cycles(species_index())
    env = check_env(backend_name) if backend_name == "real" else {"backend": "mock", "mock": True}
    _save(out / "env_check.json", dict(env, status="ok"))
    t0 = time.time()
    results = {}
    with cf.ThreadPoolExecutor(max_workers=int(opts["jobs"])) as pool:
        futs = {pool.submit(run_species, s, out, backend, opts): s["name"] for s in index}
        for f in cf.as_completed(futs):
            try:
                results[futs[f]] = f.result()
            except Exception as exc:  # noqa: BLE001 - one species failing must not stop the others
                results[futs[f]] = {"name": futs[f], "status": "failed", "error": repr(exc)[:500]}
    summary = {
        "driver_version": DRIVER_VERSION, "backend": backend_name, "mock": backend.mock, "generated_utc": utc(),
        "question": "binding free energies of acetate and catecholate to hydrated Ca2+ (pipeline consistency check; "
                    "no literature comparison in this step)",
        "level": LEVEL, "options": opts, "params_sha": PARAMS_SHA, "T_K": T_K, "env_check": env,
        "species": results, "cycles": binding(results, cyc, params), "wall_s": round(time.time() - t0, 1),
        "departures": [] if backend.mock or env.get("smd_cds", {}).get("active") else
        ["SMD CDS term absent in this build: electrostatics only (flagged per species)"]}
    _save(out / "summary.json", dict(summary, status="ok"))
    return summary


def _version(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return (p.stdout + p.stderr).strip().splitlines()[:6]
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ["unavailable: %s" % exc]


def check_env(backend_name="real"):
    import platform

    rec = {"utc": utc(), "platform": platform.platform(), "machine": platform.machine(), "python": sys.version.split()[0],
           "cpu_count": os.cpu_count(), "backend": backend_name}
    try:
        rec["mem_total_kB"] = int(re.search(r"MemTotal:\s+(\d+)", Path("/proc/meminfo").read_text()).group(1))
    except (OSError, AttributeError):
        rec["mem_total_kB"] = None
    rec["glibc"] = platform.libc_ver()
    rec["xtb"] = _version(["xtb", "--version"])
    rec["crest"] = _version(["crest", "--version"])
    rec["smd_cds"] = smd_cds_status()
    try:
        import pyscf.scf.dispersion  # noqa: F401
        import pyscf_dispersion  # noqa: F401

        rec["dispersion_addon"] = True
    except Exception as exc:  # noqa: BLE001
        rec["dispersion_addon"] = "unavailable: %s" % exc
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.anchor.production")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check-env")
    c.add_argument("--out", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", required=True)
    r.add_argument("--backend", choices=sorted(BACKENDS), default="real")
    r.add_argument("--jobs", type=int)
    r.add_argument("--threads", type=int)
    r.add_argument("--max-conformers", type=int)
    r.add_argument("--ewin-kcal", type=float)
    r.add_argument("--max-memory-mb", type=int)
    r.add_argument("--species", nargs="*")
    s = sub.add_parser("sp")
    s.add_argument("--xyz", required=True)
    s.add_argument("--charge", type=int, required=True)
    s.add_argument("--solvent", type=int, required=True)
    s.add_argument("--threads", type=int, required=True)
    s.add_argument("--max-memory-mb", type=int, required=True)
    s.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "sp":
        single_point(a.xyz, a.charge, bool(a.solvent), a.threads, a.max_memory_mb, a.out)
        return 0
    if a.cmd == "check-env":
        rec = check_env()
        _save(Path(a.out) / "env_check.json", dict(rec, status="ok"))
        print(json.dumps(rec, indent=1, default=str))
        return 0 if rec["smd_cds"].get("active") else 3  # 3: CDS absent (the run continues, flagged)
    summ = run(a.out, a.backend, a.species, jobs=a.jobs, threads=a.threads, max_conformers=a.max_conformers,
               ewin_kcal=a.ewin_kcal, max_memory_mb=a.max_memory_mb)
    bad = [n for n, v in summ["species"].items() if v.get("status") != "ok"]
    print(json.dumps({"species_ok": len(summ["species"]) - len(bad), "failed": bad,
                      "cycles": {c["complex"]: c.get("dG_bind_J_per_mol") for c in summ["cycles"]}}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
