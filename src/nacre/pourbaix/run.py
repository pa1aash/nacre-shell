"""Run the R-slurry Pourbaix screen and the R-cell window from a configuration (offline).

    uv run python -m nacre.pourbaix.run --config results/preprint/pourbaix/config/mock.yaml --mock

Writes results/preprint/pourbaix/<run>/ (slurry.json, cell.json, fig7_pourbaix_input.json,
schema_checks.json) and appends one record to jobs/ledger/p0-w5.jsonl. Mock configurations are
refused without --mock.
"""
import argparse
import json
import sys

import numpy as np

from nacre.pourbaix import cache, cell, config, provenance, slurry
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

LEDGER = REPO / "jobs" / "ledger" / "p0-w5.jsonl"
SESSION = "P0-W5.1"

SLURRY_QUESTIONS = [
    "Which combination of Al-, Ca- and C-bearing species has the lowest free energy at each "
    "(pH, E vs SHE) in the regime's range, at the configured ion concentrations and fixed total "
    "carbonate? (stability domains)",
    "How far above that equilibrium do calcite, ACC, corundum, boehmite and diaspore sit, in eV "
    "per atom, across the regime's pH and potential range? (decomposition energies)",
    "With the crystalline CaCO3 polymorphs excluded, where is ACC part of the stable Ca-C "
    "state, and how does that region move with the ACC free-energy offset? (constrained "
    "equilibrium)",
]
CELL_QUESTION = ("Between which potentials vs Li+/Li are CaCO3 and Al2O3 at equilibrium against "
                 "lithiation (Li-open grand potential) and against oxidation to O2 (and CO2) "
                 "with the cation going to the stated sink?")
SCOPE = ("Thermodynamic proxies only: stability domains and windows say which state is at "
         "equilibrium, not how fast any phase corrodes, dissolves or decomposes. The window is "
         "a thermodynamic window, not a kinetic statement.")


def _r(x, nd=6):
    a = np.asarray(x, dtype=float)
    return np.where(np.isfinite(a), np.round(a, nd), np.nan).tolist()


def _clean(obj):
    """JSON-safe copy: NaN and inf become None."""
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.generic):
        return _clean(obj.item())
    return obj


def slurry_payload(cfg, res):
    ph, E = res["ph"], res["E"]
    dec = {}
    for role, grid in res["decomposition"].items():
        dec[role] = {"units": "eV/atom", "grid": _r(grid),
                     "min_over_E": _r(np.nanmin(grid, axis=0)),
                     "max_over_E": _r(np.nanmax(grid, axis=0)),
                     "stable_fraction_of_grid": float(np.mean(grid < 1e-9))}
    stable_labels = [slurry.label(s) for s in res["stable"]]
    spec = res["speciation"]
    acc = res["acc_region"]
    roles = res["roles"]
    return {
        "questions": SLURRY_QUESTIONS, "scope": SCOPE,
        "regime": "R-slurry",
        "axes": {"pH": _r(ph), "E_V_SHE": _r(E)},
        "conditions": {k: cfg[k] for k in ("temperature_K", "pH", "potential_V_SHE",
                                            "concentrations_mol_kg", "composition",
                                            "carbonate_system", "acc_offset")},
        "carbonate_system": {
            "choice": "closed",
            "reason": cfg.get("carbonate_reason", ""),
            "convention": "Pourbaix predominance: each aqueous ion at the element's total "
                          "concentration; the closed-system C(IV) speciation below follows "
                          "from pH with acid constants derived from the cached ion energies.",
            "pKa1_derived": round(spec["pKa1"], 4), "pKa2_derived": round(spec["pKa2"], 4),
            "alpha_CO2aq": _r(spec["alpha_CO2aq"]), "alpha_HCO3": _r(spec["alpha_HCO3"]),
            "alpha_CO3": _r(spec["alpha_CO3"]), "a_CO3_ideal": _r(spec["a_CO3"], 12)},
        "domains": {"labels": stable_labels,
                    "index_grid": res["index"].astype(int).tolist(),
                    "index_grid_axes": "rows follow E_V_SHE, columns follow pH",
                    "tie_break": "stable entries ordered by label; first minimum wins",
                    "polygons": slurry.polygons(res["pd"], res["limits"])},
        "cross_compounds_stable": res["cross_compounds"],
        "water_lines": {"lower": _r(res["water"]["lower"]), "upper": _r(res["water"]["upper"])},
        "phases": {r: roles[r] for r in ("calcite", "corundum", "boehmite", "diaspore")},
        "ACC": {"definition": "calcite (%s) plus the configured free-energy offset per CaCO3 "
                              "formula unit" % roles["calcite"]["material_id"],
                "offset": cfg["acc_offset"]},
        "decomposition_energy": {
            "reference": "Pourbaix hull of each phase's own element subsystem (Ca-C for calcite "
                         "and ACC, Al for the Al phases) at the same concentrations; exact for "
                         "the full system when no Al-Ca or Al-C compound is stable (see "
                         "cross_compounds_stable)",
            **dec},
        "acc_constrained": {"excluded": "all crystalline CaCO3 solids",
                            "area_fraction": acc["area_fraction"],
                            "ph_min_at_E": _r(acc["ph_min"])},
    }


def cell_payload(cfg, res):
    phases = res["phases"]
    sink = cfg["sinks"][cfg["active_sink"]]
    return {
        "question": CELL_QUESTION, "scope": SCOPE, "regime": "R-cell",
        "reference_electrode": "Li+/Li",
        "temperature_K": res["temperature_K"],
        "gas": cfg["gas"],
        "sink_assumption": {"active": cfg["active_sink"], "definition": sink,
                            "statement": cfg.get("sink_statement", ""),
                            "switch": "set regimes/R-cell/active_sink in the run configuration; "
                                      "no code change (cp2 ruling on Q9)"},
        "windows": {p: v["window"] for p, v in phases.items()},
        "phase_records": phases,
        "oxidation_candidates": res["candidates"],
        "sensitivity_CO2_enthalpy_scheme": res["sensitivity_CO2_scheme"],
        "chemical_decomposition_check": res["chemical"],
        "convention": "W3 contract E_window = Delta_G_r/(Delta_n_Li F); Delta_n_Li > 0 releases "
                      "Li to the reservoir (oxidation), < 0 takes it up (lithiation)",
    }


def fig7_export(slurry_out, prov_extra, w4_prov):
    """The R-slurry part in the shape of W6's assumed Fig 7 schema (assumed-v0)."""
    ph = slurry_out["axes"]["pH"]
    E = slurry_out["axes"]["E_V_SHE"]
    return {
        "mock": None,  # filled by the caller
        "schema": "fig7-pourbaix/assumed-v0",
        "note": "Exported by lane p0-w5 from slurry.json. R-cell has no (pH, E) plane and is "
                "not exported here; see cell.json and the schema checks.",
        "provenance": {**w4_prov, "cache_hash": prov_extra["cache_hash"],
                       "mp_database_version": prov_extra["mp_database_version"]},
        "regimes": [{
            "id": "R-slurry",
            "conditions": slurry_out["conditions"],
            "ph_range": [ph[0], ph[-1]],
            "potential_range": [E[0], E[-1]],
            "domains": [{"species": d["label"], "phase": d["kind"], "polygon": d["polygon"]}
                        for d in slurry_out["domains"]["polygons"]],
            # the water lines are straight, so their end points define them
            "water_lines": [{"kind": k, "points": [[ph[0], slurry_out["water_lines"][k][0]],
                                                   [ph[-1], slurry_out["water_lines"][k][-1]]]}
                            for k in ("upper", "lower")],
        }],
    }


def run(config_path, allow_mock=False, run_name=None, scan=True):
    cfg, meta = config.load(config_path, allow_mock=allow_mock)
    bad = cache.verify()
    if bad:
        raise SystemExit("cache check failed: %s" % bad)
    name = run_name or cfg["run"]
    out_dir = POURBAIX_RESULTS / name
    out_dir.mkdir(parents=True, exist_ok=True)
    w4_prov, extra = provenance.block(meta)
    head = {"mock": meta["mock"], "generated_utc": provenance.utc_now(), "session": SESSION,
            "provenance": w4_prov, "provenance_pourbaix": extra, "inputs": meta["sources"]}
    outputs = []

    regimes = cfg["regimes"]
    slurry_out = None
    if "R-slurry" in regimes:
        rs = regimes["R-slurry"]
        res = slurry.build(rs)
        slurry_out = slurry_payload(rs, res)
        if scan and rs.get("acc_offset_scan_kj_per_mol"):
            conc = {k: float(v) for k, v in rs["concentrations_mol_kg"].items()}
            sc = slurry.acc_offset_scan(rs["acc_offset_scan_kj_per_mol"], conc, res["ph"], res["E"])
            slurry_out["acc_offset_scan"] = [{"offset_kj_per_mol": s["offset_kj_per_mol"],
                                              "area_fraction": s["area_fraction"],
                                              "ph_min_at_E": _r(s["ph_min"])} for s in sc]
        path = out_dir / "slurry.json"
        path.write_text(json.dumps(_clean({**head, "regimes": {"R-slurry": slurry_out}}),
                                   indent=1, sort_keys=True) + "\n", encoding="utf-8")
        outputs.append(path)

    if "R-cell" in regimes:
        rc = regimes["R-cell"]
        cell_out = cell_payload(rc, cell.build(rc))
        path = out_dir / "cell.json"
        path.write_text(json.dumps(_clean({**head, "regimes": {"R-cell": cell_out}}),
                                   indent=1, sort_keys=True) + "\n", encoding="utf-8")
        outputs.append(path)

    checks = {"w4_provenance": provenance.validate_against(provenance.W4_SCHEMA, w4_prov,
                                                           subschema="provenance")}
    if slurry_out is not None:
        fig7 = fig7_export(slurry_out, extra, w4_prov)
        fig7["mock"] = meta["mock"]
        path = out_dir / "fig7_pourbaix_input.json"
        path.write_text(json.dumps(_clean(fig7), indent=1, sort_keys=True) + "\n", encoding="utf-8")
        outputs.append(path)
        checks["w6_fig7"] = provenance.validate_against(provenance.W6_SCHEMA, _clean(fig7))
    path = out_dir / "schema_checks.json"
    path.write_text(json.dumps(checks, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    outputs.append(path)

    record = {"session": SESSION, "run": name, "mock": meta["mock"], "utc": head["generated_utc"],
              "kind": "pourbaix", "config": meta["path"], "config_hash": meta["config_hash"],
              "git_sha": w4_prov["git_sha"], "git_dirty": w4_prov["git_dirty"],
              "cache_hash": extra["cache_hash"], "contract_sha": w4_prov["contract_sha"],
              "outputs": [{"path": p.relative_to(REPO).as_posix(), "sha256": provenance.sha256_file(p)}
                          for p in outputs]}
    provenance.ledger_append(LEDGER, record)
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.run")
    ap.add_argument("--config", required=True)
    ap.add_argument("--mock", action="store_true", help="allow a mock configuration")
    ap.add_argument("--name", default=None, help="run directory name (default: config run)")
    args = ap.parse_args(argv)
    try:
        rec = run(args.config, allow_mock=args.mock, run_name=args.name)
    except config.MockRefused as exc:
        print("refused: %s" % exc, file=sys.stderr)
        return 2
    for o in rec["outputs"]:
        print("%s  %s" % (o["sha256"][:12], o["path"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
