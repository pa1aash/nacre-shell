"""Final C5 runs of P0-W5.2: R-slurry over the design axes (task B) and the R-cell window
(task C), written as results documents of schema v2 (configs/preprint/results_schema.json, W4,
decision D4) plus summaries.

    uv run python -m nacre.pourbaix.final_run --config results/preprint/pourbaix/config/final.yaml [--regime R-slurry|R-cell]

Outputs under results/preprint/pourbaix/final/; one ledger record per regime in
jobs/ledger/p0-w5.jsonl. Every output states the thermodynamic question it answers.
"""
import argparse
import json
import sys

import numpy as np
import yaml

from nacre.pourbaix import cache, inputs, provenance
from nacre.pourbaix import final as F
from nacre.pourbaix.config import canonical_hash, file_hash
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO, rel

OUT = POURBAIX_RESULTS / "final"
LEDGER = REPO / "jobs" / "ledger" / "p0-w5.jsonl"
SCOPE = ("Thermodynamic proxies only: a stability domain, a decomposition energy or a window says "
         "which state is at equilibrium, never how fast anything corrodes, dissolves or decomposes.")


def _r(x, nd=6):
    a = np.asarray(x, dtype=float)
    return np.where(np.isfinite(a), np.round(a, nd), np.nan).tolist()


def _clean(obj):
    if isinstance(obj, float):
        return obj if np.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, np.generic):
        return _clean(obj.item())
    if isinstance(obj, np.ndarray):
        return _clean(obj.tolist())
    return obj


def _dump(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_clean(doc), indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _pick(entry, spec):
    """'range.min' | 'range.max' | 'value' of a params entry."""
    if spec == "value":
        return float(entry["value"])
    side = spec.split(".")[1]
    return float(entry["range"][side])


def load_config(path):
    path = REPO / path if not str(path).startswith("/") else path
    raw = yaml.safe_load(open(path, encoding="utf-8"))
    if raw.get("mock"):
        raise SystemExit("final_run refuses a mock configuration")
    return raw, {"path": rel(path), "file_hash": file_hash(path), "config_hash": canonical_hash(raw)}


def w4_provenance(meta, params_sha):
    return {"git_sha": provenance.git_sha(), "git_dirty": provenance.git_dirty(),
            "config_hash": meta["config_hash"], "config_file": meta["path"],
            "config_file_hash": meta["file_hash"], "contract_sha": provenance.W3_CONTRACT_V2[0],
            "params_sha": params_sha, "thresholds_file": None, "thresholds_hash": None,
            "schema_sha": provenance.W4_SCHEMA_V2[0]}


def lane_extension(params, meta):
    m = cache.manifest()
    return {"session": "P0-W5.2", "scope": SCOPE,
            "provenance_pourbaix": {"cache_hash": cache.cache_hash(), "mp_database_version": m["mp_database_version"],
                                    "library_versions": provenance.lib_versions(),
                                    "params_snapshot": rel(inputs.snapshot_path(params.sha)),
                                    "params_blob": params.snap["params"]["blob"],
                                    "thresholds": {"rev": provenance.W3_THRESHOLDS[0], "path": provenance.W3_THRESHOLDS[1]}},
            "config": meta["path"]}


# =============================================================================== R-slurry
def slurry_axes(cfg, params):
    ph_e = params.entry(cfg["pH"]["key"])
    e_e = params.entry(cfg["E_V_SHE"]["key"])
    ph = np.linspace(_pick(ph_e, "range.min"), _pick(ph_e, "range.max"), int(cfg["pH"]["n"]))
    E = np.linspace(_pick(e_e, "range.min"), _pick(e_e, "range.max"), int(cfg["E_V_SHE"]["n"]))
    return ph, E


def acc_offsets(cfg, params):
    """ACC offsets in eV per CaCO3 formula unit, converted explicitly from J mol^-1."""
    e = params.entry(cfg["acc_offset"]["key"])
    if e["unit"] != "J mol^-1":
        raise SystemExit("acc_offset unit %r, expected J mol^-1" % e["unit"])
    scan = {s: _pick(e, s) for s in cfg["acc_offset"]["scan"]}
    return {s: {"J_per_mol": v, "eV_per_formula_unit": v * F.EV_PER_J_PER_MOL} for s, v in scan.items()}


def c_t_grid(cfg, params):
    e = params.entry(cfg["design_axes"]["C_T"]["key"])
    if e["unit"] != "mol m^-3":
        raise SystemExit("dic_slurry unit %r" % e["unit"])
    # mol m^-3 -> mol dm^-3 (/1000), read per kg of water (W1 dilute-solution convention)
    return [{"from": s, "mol_m3": _pick(e, s), "mol_kg": _pick(e, s) / 1000.0}
            for s in cfg["design_axes"]["C_T"]["grid_from"]]


def edge_ev_per_atom(params, key, offset_ev=0.0, n_at=5):
    """C5 edge per atom: e_form (per atom) plus, for ACC, the offset per atom (thresholds.md C5)."""
    e = params.entry(key)
    if e["unit"] != "J mol^-1":
        raise SystemExit("%s unit %r" % (key, e["unit"]))
    e_form = float(e["value"]) * F.EV_PER_J_PER_MOL
    return e_form + offset_ev / n_at


def schema_state(conditions, phases, idx, dec, roles, named):
    decomp = {}
    for r, g in dec.items():
        ent = named.get(r)
        decomp[r] = {"units": "eV/atom", "grid": _r(np.maximum(g, 0.0)),
                     "material_id": roles[r]["material_id"] if r in roles else None,
                     "formula": ("CaCO3" if r in ("calcite", "ACC")
                                 else ent.entry.composition.reduced_formula.replace("(HO)3", "(OH)3")
                                 if ent is not None else None)}
    return {"conditions": conditions, "phases": phases, "domains": {"index_grid": idx.astype(int).tolist()},
            "decomposition_energy": decomp}


def water_lines_record(ph):
    """Water-stability lines on the pH axis (V vs SHE), until schema v2 has a field for them (N13)."""
    from nacre.pourbaix import slurry

    w = slurry.water_lines(ph)
    return {"pH": _r(ph), "lower_V_SHE": _r(w["lower"]), "upper_V_SHE": _r(w["upper"]),
            "note": "H2/H2O (lower) and H2O/O2 (upper) at 1 bar and 298.15 K; held here until W4 adds the "
                    "schema v2 field for the Fig 7 water-stability lines (lane notes N12, N13)"}


def run_slurry(raw, meta, params):
    cfg = raw["R-slurry"]
    S = F.setup()
    consts = F.implied_constants(S["all"])
    ph, E = slurry_axes(cfg, params)
    offs = acc_offsets(cfg, params)
    off_c = offs["value"]["eV_per_formula_unit"]
    a_ca_grid = [float(x) for x in cfg["design_axes"]["a_Ca"]["grid"]]
    cts = c_t_grid(cfg, params)
    al_grid = [float(x) for x in cfg["al_activity"]["grid"]]
    a_al_map = float(cfg["al_activity"]["map_value"])
    edge_cal = edge_ev_per_atom(params, cfg["formation_energy_error"]["key"])
    edge_acc = edge_ev_per_atom(params, cfg["formation_energy_error"]["key"], off_c)
    pk1, pk2 = params.value("pk1_carbonic"), params.value("pk2_carbonic")
    lk_cal, lk_acc = params.value("log10_ksp_calcite"), params.value("log10_ksp_acc")
    prov = w4_provenance(meta, params.sha)
    ext = lane_extension(params, meta)

    # Al baseline (no Ca), per total dissolved Al
    baseline = {}
    for a_al in al_grid:
        dec, labels, idx = F.al_baseline(S, a_al, ph, E)
        baseline["%.0e" % a_al] = {
            "a_Al_total": a_al, "domains": labels, "index_grid": idx.astype(int).tolist(),
            "decomposition_energy_eV_per_atom": {r: {"grid": _r(g), "max": float(g.max()), "min": float(g.min())}
                                                 for r, g in dec.items()},
            "stable_fraction": {r: float(np.mean(g < 1e-9)) for r, g in dec.items()}}

    points, docs = [], []
    for ct in cts:
        for a_ca in a_ca_grid:
            pid = "aCa%.0e_CT%s" % (a_ca, ct["from"].replace("range.", ""))
            cal = F.ca_c_exact(S, a_ca, ct["mol_kg"], ph, E, off_c, consts)
            acc = F.ca_c_exact(S, a_ca, ct["mol_kg"], ph, E, off_c, consts, target="ACC")
            margins = {s: F.ca_c_exact(S, a_ca, ct["mol_kg"], ph, E, o["eV_per_formula_unit"], consts,
                                       exclude_carbonates=True, target="ACC") for s, o in offs.items()}
            unc = F.ca_c_unconstrained(S, a_ca, ct["mol_kg"], ph, E)
            phases, idx, cross, _ = F.domain_map(S, a_ca, ct["mol_kg"], a_al_map, ph, E, off_c)
            dec_al, _, _ = F.al_baseline(S, a_al_map, ph, E)
            a_co3 = F.alpha2(ph, consts["pKa1"], consts["pKa2"]) * ct["mol_kg"]
            om_cal = [F.experimental_omega(a_ca, ct["mol_kg"], p, pk1, pk2, lk_cal) for p in ph]
            om_acc = [F.experimental_omega(a_ca, ct["mol_kg"], p, pk1, pk2, lk_acc) for p in ph]
            conditions = {
                "a_Ca": a_ca, "a_CO3": None,
                "a_CO3_by_pH": _r(a_co3, 12), "a_CO3_note": "a_CO3 = alpha2(pH) C_T (ideal solution, "
                "closed C(IV) system); it varies along the pH axis, so the scalar is null",
                "c_bulk_mol_m3": a_ca * 1000.0, "C_T_mol_kg": ct["mol_kg"], "C_T_source": params.cite("dic_slurry"),
                "a_Ca_grid_status": "provisional design grid (gap policy (ii))",
                "a_w": 1.0, "temperature_K": F.T_K, "a_Al_total_map": a_al_map,
                "carbon": "C(IV) only; exact speciation per pH column for calcite and ACC; predominance "
                          "convention for the domain map",
                "acc_offset": {"J_per_mol": offs["value"]["J_per_mol"], "eV_per_formula_unit": off_c,
                               "source": params.cite("acc_offset")}}
            dec = {"calcite": cal, "ACC": acc, **{r: dec_al[r] for r in F.AL_ROLES}}
            bulk = schema_state(conditions, phases, idx, dec, S["roles"], {**S["named"], "ACC": None})
            enriched = json.loads(json.dumps(_clean(bulk)))
            enriched["conditions"]["state_note"] = (
                "identical to the bulk state by derivation: at equilibrium the template does not change "
                "Delta mu (theory/derivation_body.tex section 7, rule 5; contract v2); not computed separately")
            doc = {"schema_version": "2", "mock": False, "generated_utc": provenance.utc_now(),
                   "provenance": prov,
                   "stability": {"R-slurry": {"kind": "pourbaix", "reference_electrode": "SHE",
                                              "temperature_K": F.T_K,
                                              "axes": {"pH": _r(ph), "E_V": _r(E)},
                                              "states": {"bulk": bulk, "enriched": enriched}}},
                   "extensions": {"p0-w5": {**ext, "question": cfg["question"], "design_point": pid,
                                            "design_axes": {"a_Ca": a_ca, "C_T": ct},
                                            "water_lines": water_lines_record(ph)}}}
            docs.append(_dump(OUT / "slurry" / ("%s.json" % pid), doc))
            worst_cal = float(cal.max())
            points.append({
                "id": pid, "a_Ca": a_ca, "c_bulk_mol_m3": a_ca * 1000.0, "C_T": ct,
                "calcite": {"max_dec_eV_per_atom": worst_cal, "edge_eV_per_atom": edge_cal,
                            "within_edge_everywhere": worst_cal <= edge_cal,
                            "stable_fraction": float(np.mean(cal < 1e-9))},
                "ACC": {"max_dec_eV_per_atom": float(acc.max()), "edge_eV_per_atom": edge_acc,
                        "within_edge_everywhere": float(acc.max()) <= edge_acc},
                "ACC_dissolution_margin": {s: {"max_eV_per_atom": float(g.max()), "stable_fraction": float(np.mean(g < 1e-9)),
                                               "offset_J_per_mol": offs[s]["J_per_mol"]} for s, g in margins.items()},
                "carbon_redox_sensitivity": {"calcite_max_dec_eV_per_atom": float(unc.max()),
                                             "fraction_above_edge": float(np.mean(unc > edge_cal))},
                "experimental_omega": {"calcite_min": float(min(om_cal)), "calcite_max": float(max(om_cal)),
                                       "ACC_min": float(min(om_acc)), "ACC_max": float(max(om_acc))},
                "domains_in_region": sorted({phases[k]["label"] for k in np.unique(idx)}),
                "cross_compounds_stable": cross,
                "document": rel(docs[-1])})

    controls = run_controls(raw, S, consts, params, ph, E, edge_cal, a_ca_grid, cts, al_grid, a_al_map)
    bias = consts["log10_ksp_calcite"] - lk_cal
    summary = {
        "session": "P0-W5.2", "generated_utc": provenance.utc_now(), "provenance": prov, "extensions": ext,
        "question": cfg["question"], "scope": SCOPE,
        "axes": {"pH": {"from": params.cite("ph_slurry"), "min": float(ph[0]), "max": float(ph[-1]), "n": len(ph)},
                 "E_V_SHE": {"from": params.cite("e_she_slurry"), "min": float(E[0]), "max": float(E[-1]), "n": len(E)}},
        "design_axes": {"a_Ca": {"grid": a_ca_grid, "status": "provisional", "reason": cfg["design_axes"]["a_Ca"]["reason"]},
                        "c_bulk_mol_m3": {"grid": [a * 1000.0 for a in a_ca_grid], "status": "provisional",
                                          "relation": cfg["design_axes"]["c_bulk"]["relation"]},
                        "C_T": cts, "a_Al_total": {"grid": al_grid, "status": "provisional",
                                                   "reason": cfg["al_activity"]["reason"]}},
        "temperature": cfg["temperature_K"],
        "carbonate": cfg["carbonate"],
        "implied_constants": {"from_cached_ion_energies": consts,
                              "sourced": {"pk1_carbonic": pk1, "pk2_carbonic": pk2, "log10_ksp_calcite": lk_cal,
                                          "log10_ksp_acc": lk_acc,
                                          "sources": [params.cite(k) for k in ("pk1_carbonic", "pk2_carbonic",
                                                                                "log10_ksp_calcite", "log10_ksp_acc")]},
                              "calcite_solubility_bias_log10": bias,
                              "reading": "The proxy's calcite solubility product (from the MP ion energies and the "
                                         "MP calcite energy) differs from the sourced one by this many log10 units; "
                                         "a negative bias makes the proxy hold calcite more stable than experiment."},
        "edges": {"calcite_eV_per_atom": edge_cal, "ACC_eV_per_atom": edge_acc,
                  "rule": "thresholds.md C5: tau = n_at e_f / n_M per non-O, non-H atom, plus Delta_ACC / n_M for "
                          "ACC; written here per atom (n_at = 5 for CaCO3)",
                  "e_form": params.cite("formation_energy_mae")},
        "points": points,
        "native_oxide_baseline": {"question": "Without any Ca phase, is a native Al oxide or hydroxide the "
                                              "equilibrium state of Al at the regime pH and potential? It does "
                                              "not gate C5 (thresholds.md: alkaline attack is the corrosion mode "
                                              "the slurry regime describes).",
                                  "by_total_Al": baseline,
                                  "gibbsite_note": "The Al(OH)3 ground state (gibbsite role) carries the client's "
                                                   "aqueous-compatibility hydrate adjustment, which treats it as "
                                                   "Al2O3.3H2O and raises its energy by several eV per formula unit; "
                                                   "its decomposition energy reflects that adjustment, not a "
                                                   "measured instability (key dfg_gibbsite is a gap at this sha)."},
        "F6": f6_statement(points, edge_cal, edge_acc, offs),
        "F7": f7_statement(cfg, params),
        "enriched_state": cfg["states"]["enriched"]["reason"],
        "falsifiability_control": controls,
    }
    spath = _dump(OUT / "slurry_summary.json", summary)
    return summary, docs + [spath]


def f6_statement(points, edge_cal, edge_acc, offs):
    same = all(p["calcite"]["within_edge_everywhere"] == p["ACC"]["within_edge_everywhere"] for p in points)
    return {
        "statement": "Adding the ACC offset to the hull edge makes the ACC test the calcite-level phase-stability "
                     "test, up to the framing's metastability: ACC sits above the hull by calcite's own distance "
                     "plus the offset per atom, and its edge is calcite's edge plus the same offset per atom "
                     "(cp2 ruling F6).",
        "check_same_verdict_at_every_design_point": same,
        "ACC_specific_margin": "labelled sensitivity, never a verdict: the decomposition energy of ACC against a hull "
                               "with every crystalline Ca carbonate removed (ACC against the dissolved ions and the "
                               "non-carbonate solids), at the acc_offset range minimum, value and maximum; 0 means ACC "
                               "is stable against dissolution at that point. The sourced-Ksp supersaturation of ACC "
                               "(experimental_omega.ACC_*) is reported beside it.",
        "offsets": offs}


def f7_statement(cfg, params):
    return {
        "a_w_per_state": {"wet slurry (bulk; enriched = bulk)": {"a_w": 1.0, "source": cfg["states"]["bulk"]["a_w_source"]},
                          "drying": {"a_w": None, "source": params.cite("a_w_slurry"),
                                     "status": "gap: no water activity during drying is sourced; drying states are not "
                                               "evaluated separately, and the wet-slurry result is used for them"}},
        "bias_note": "The ion activity product here is IAP = a_Ca a_CO3 (W3 Q13, contract). For a hydrated ACC "
                     "framing, CaCO3.nH2O, the IAP carries a_w^n; omitting it overstates Omega when a_w < 1. Drying "
                     "states are therefore optimistic for the ACC framing (cp2 ruling F7).",
        "also": "The drying temperature (key t_drying_primary) lies outside the 298.15 K construction."}


def run_controls(raw, S, consts, params, ph, E, edge_cal, a_ca_grid, cts, al_grid, a_al_map):
    """Proxy falsifiability control (C5, Phase 7 item 21): the screen must report instability
    where a sourced phase and condition demand it, and stability where experiment demands it."""
    cfg = raw["R-slurry"]["falsifiability_control"]
    pk1, pk2, lk = params.value("pk1_carbonic"), params.value("pk2_carbonic"), params.value("log10_ksp_calcite")
    out = {}
    # (a) calcite at a sourced undersaturated condition
    c = cfg["calcite_undersaturated"]
    p_ = _pick(params.entry(c["pH"]["key"]), c["pH"]["from"])
    ct = _pick(params.entry(c["C_T"]["key"]), c["C_T"]["from"]) / 1000.0
    a_ca = min(a_ca_grid)
    g = F.ca_c_exact(S, a_ca, ct, np.array([p_]), E, 0.0, consts)
    om = F.experimental_omega(a_ca, ct, p_, pk1, pk2, lk)
    reports = bool(np.all(g > edge_cal))
    # experimental log Omega below which the proxy reports calcite above its edge
    bias = consts["log10_ksp_calcite"] - lk
    thr = -(5 * edge_cal) / consts["nernst_prefactor_eV"] + bias
    out["calcite_undersaturated"] = {
        "condition": {"pH": p_, "pH_source": params.cite(c["pH"]["key"]), "C_T_mol_kg": ct,
                      "C_T_source": params.cite(c["C_T"]["key"]), "a_Ca": a_ca},
        "experimental_log10_omega": float(np.log10(om)), "must_report": "instability",
        "proxy_max_dec_eV_per_atom": float(g.max()), "proxy_min_dec_eV_per_atom": float(g.min()),
        "edge_eV_per_atom": edge_cal, "proxy_reports_instability": reports,
        "fails_where_it_must": reports,
        "detection_threshold_log10_omega": float(thr),
        "reading": "The proxy reports calcite above its edge only where the sourced log10 Omega is below "
                   "detection_threshold_log10_omega: the edge (n_at e_f per formula unit) and the proxy's "
                   "calcite solubility bias shift the dissolution boundary by that many log units."}
    # (b) native oxide at the alkaline end of the regime
    c = cfg["native_oxide_alkaline"]
    p_ = _pick(params.entry(c["pH"]["key"]), c["pH"]["from"])
    dec, _, _ = F.al_baseline(S, a_al_map, np.array([p_]), E)
    g = dec["corundum"]
    out["native_oxide_alkaline"] = {
        "condition": {"pH": p_, "pH_source": params.cite(c["pH"]["key"]), "E_source": params.cite("e_she_slurry"),
                      "a_Al_total": a_al_map, "basis": "the e_she_slurry rows are open-circuit potentials of "
                      "aluminium corroding in alkaline media"},
        "must_report": "instability", "proxy_min_dec_eV_per_atom": float(g.min()),
        "edge_eV_per_atom": edge_cal, "proxy_reports_instability": bool(np.all(g > edge_cal)),
        "fails_where_it_must": bool(np.all(g > edge_cal))}
    # (c) calcite at a supersaturated condition: must be within its edge
    c = cfg["calcite_supersaturated"]
    p_ = _pick(params.entry(c["pH"]["key"]), c["pH"]["from"])
    ct = _pick(params.entry(c["C_T"]["key"]), c["C_T"]["from"]) / 1000.0
    a_ca = max(a_ca_grid)
    g = F.ca_c_exact(S, a_ca, ct, np.array([p_]), E, 0.0, consts)
    out["calcite_supersaturated"] = {
        "condition": {"pH": p_, "C_T_mol_kg": ct, "a_Ca": a_ca},
        "experimental_log10_omega": float(np.log10(F.experimental_omega(a_ca, ct, p_, pk1, pk2, lk))),
        "must_report": "stability", "proxy_max_dec_eV_per_atom": float(g.max()),
        "proxy_reports_stability": bool(np.all(g <= edge_cal))}
    passed = (out["calcite_undersaturated"]["fails_where_it_must"]
              and out["native_oxide_alkaline"]["fails_where_it_must"]
              and out["calcite_supersaturated"]["proxy_reports_stability"])
    out["control_fails_where_it_must"] = bool(out["calcite_undersaturated"]["fails_where_it_must"])
    out["all_controls_pass"] = bool(passed)
    out["consequence"] = ("thresholds.md C5: R-slurry is feasible only if the control fails where it must; "
                          "otherwise C5s is at best inconclusive. The framing-phase control is the calcite one.")
    return out


# ================================================================================== main
def ledger(run, outputs, prov):
    rec = {"session": "P0-W5.2", "run": run, "kind": "pourbaix-final", "mock": False, "utc": provenance.utc_now(),
           "git_sha": prov["git_sha"], "git_dirty": prov["git_dirty"], "config_hash": prov["config_hash"],
           "params_sha": prov["params_sha"], "cache_hash": cache.cache_hash(),
           "contract_sha": prov["contract_sha"], "schema_sha": prov["schema_sha"],
           "outputs": [{"path": rel(p), "sha256": provenance.sha256_file(p)} for p in outputs]}
    provenance.ledger_append(LEDGER, rec)
    return rec


def validate(paths):
    out = {}
    for p in paths:
        doc = json.loads(p.read_text(encoding="utf-8"))
        if "schema_version" in doc:
            out[rel(p)] = provenance.validate_against(provenance.W4_SCHEMA_V2, doc)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.final_run")
    ap.add_argument("--config", required=True)
    ap.add_argument("--regime", choices=["R-slurry", "R-cell", "both"], default="both")
    args = ap.parse_args(argv)
    if cache.verify():
        raise SystemExit("cache check failed")
    raw, meta = load_config(args.config)
    params = inputs.Params(inputs.load_snapshot(raw["params_sha"]))
    prov = w4_provenance(meta, params.sha)
    if args.regime in ("R-slurry", "both"):
        summary, outs = run_slurry(raw, meta, params)
        checks = validate(outs)
        bad = [k for k, v in checks.items() if not v.get("valid")]
        cpath = _dump(OUT / "slurry_schema_checks.json", checks)
        outs.append(cpath)
        ledger("final-R-slurry", outs, prov)
        print("R-slurry: %d documents, schema v2 invalid: %d" % (len(outs), len(bad)))
    if args.regime in ("R-cell", "both"):
        from nacre.pourbaix import cell_final
        outs = cell_final.run_cell(raw, meta, params, prov, lane_extension(params, meta))
        checks = validate(outs)
        bad = [k for k, v in checks.items() if not v.get("valid")]
        cpath = _dump(OUT / "cell_schema_checks.json", checks)
        outs.append(cpath)
        ledger("final-R-cell", outs, prov)
        print("R-cell: %d documents, schema v2 invalid: %d" % (len(outs), len(bad)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
