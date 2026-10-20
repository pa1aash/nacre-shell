"""PH-K1 run: the tier-1 oxidation-limit ladder of every candidate (outputs under results/preprint/pourbaix/ph_k1/).

    uv run python -m nacre.pourbaix.ph_k1 run

Reads: the evidence rows (lit/evidence_table.csv, ids TR-*), params at tag p0-cp3 (as the frozen carbonate
runs), the production cache (JANAF, NBS tables), the PH-K1 Materials Project cache (BY-C only, raw files local).
Writes ph_k1.json, ladder.csv, benchmark.csv and ph_k1.md. The frozen carbonate outputs are only read.
"""
import csv
import itertools
import json
import math
import statistics
import warnings

from nacre.pourbaix import cache, gasref, ph_cache, provenance
from nacre.pourbaix import ph_k1 as k
from nacre.pourbaix import supplement_cache as sc
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV, entry_key, material_id
from nacre.pourbaix.paths import rel

KEY_REQUESTS = [
    {"key": "a_w_electrolyte", "why": "a_w of the carbonate electrolyte (trace water); a_w_slurry is a slurry-only gap. "
                                      "Until then a_w is reported over the grid %s." % k.A_W_GRID},
    {"key": "a_oh_site", "why": "activity (site fraction) of OH in a carbonated or substituted apatite; reported over the "
                                "grid %s." % k.A_OH_GRID},
    {"key": "solvation_ca_vs_li, solvation_al_vs_li (organic carbonate solvent)",
     "why": "gaps at this params sha: without a solvated sink every onset is a solid-salt upper bound and no phase can "
            "pass at tier 1"},
    {"key": "exchange_entropy_bound_al_clo4_3", "why": "entropy bound of the Al + 3 LiClO4 exchange (W1's bound is for "
                                                      "Ca(ClO4)2 only); the Al-phase budgets lack this term"},
    {"key": "dfg_li3po4, s_li3po4", "why": "Li3PO4 DfG and S (only DfH, TR-040): its experimental route is undetermined"},
    {"key": "dfh_al_po3_3, dfg_al_po3_3, s_al_po3_3", "why": "Al(PO3)3 has no thermochemistry: AlPO4's staged reaction and "
                                                              "Al(PO3)3 itself are undetermined"},
    {"key": "dfh_ca_po3_2, dfg_ca_po3_2", "why": "crystalline Ca(PO3)2 (only S, and the glass DfH); needed for Ca(PO3)2 and for "
                                                  "the staged Ca2P2O7 reaction (Sandstrom 2006 EMF is paywalled)"},
    {"key": "dfh_ocp, s_ocp", "why": "OCP DfH and S (only DfG, TR-039): no cross-check of the OCP value and no "
                                      "dehydration threshold"},
    {"key": "u_tab_dfg_sio2_quartz", "why": "tabulated uncertainty of the quartz formation free energy (the JANAF text prints "
                                            "none); silicate budgets lack this term"},
    {"key": "window_margin_expt per reaction", "why": "thresholds C5c_ox grants m_expt to the registered carbonate reaction "
                                                     "only; the per-reaction budgets computed here by the same recipe "
                                                     "(provisional) need registered keys"},
    {"key": "tier-2 records (class A or B) for Ca phosphates", "why": "none found for Ca phosphates; Li3PO4 and AlPO4 have "
                                                                       "class B sources (W2)"},
]


def _kj(ev):
    return ev * KJ_PER_MOL_PER_EV


def _grid_points(by_sid):
    has_w = "H2O" in by_sid
    has_oh = any(k.SPECIES[s].get("oh_site") for s in by_sid)
    aw = k.A_W_GRID if has_w else [None]
    aoh = k.A_OH_GRID if has_oh else [None]
    return [(a, b) for a, b in itertools.product(aw, aoh)]


def _compact(res):
    keep = ("status", "onset_V", "n_e", "budget_V", "budget_complete", "budget_terms_kJ", "missing")
    return {x: res[x] for x in keep if x in res}


def evaluate_reaction(by_sid, books):
    """Reference-state result and grid for every route of one reaction."""
    out = {"stoichiometry": {s: round(c, 6) for s, c in by_sid.items()}, "text": k.reaction_text(by_sid),
           "n_e": by_sid["Li"], "routes": {}}
    for name, bk in books.items():
        ref = k.evaluate(by_sid, bk, {"a_w": 1.0, "a_oh": 1.0})
        entry = _compact(ref)
        if ref["status"] == "finite":
            grid = []
            for aw, aoh in _grid_points(by_sid):
                r = k.evaluate(by_sid, bk, {"a_w": aw, "a_oh": aoh}, budget=False)
                grid.append({"a_w": aw, "a_oh": aoh, "onset_V": r["onset_V"]})
            entry["grid"] = grid
            entry["onset_grid_min_V"] = min(g["onset_V"] for g in grid)
        if name == "expt":
            entry["sources"] = sorted({t["row"]["row_id"] if isinstance(t.get("row"), dict) else str(t.get("row"))
                                       for t in ref["terms"].values() if t.get("row")})
            entry["terms"] = {s: {kk: vv for kk, vv in t.items() if kk in ("coefficient", "G_eV", "u_kJ", "u_basis", "note",
                                                                           "basis", "state")}
                              | ({"row_id": t["row"]["row_id"]} if isinstance(t.get("row"), dict) else {})
                              for s, t in ref["terms"].items()}
        entry["benchmark_status"] = "expt (tabulated rows)" if name == "expt" else "dft-unbenchmarked"
        out["routes"][name] = entry
    ex, jn, mp = (out["routes"].get(r) for r in ("expt", "janaf", "mp"))
    out["dft_minus_expt_V"] = {r: (out["routes"][r]["onset_V"] - ex["onset_V"])
                               for r in k.SCHEMES if r in out["routes"] and ex and ex["status"] == "finite"
                               and out["routes"][r]["status"] == "finite"} if ex else {}
    return out


def phase_summary(pid, reactions):
    """E_ox(P) = min over the registered reactions; undetermined reactions are kept apart (claims_redirect 2a)."""
    det = [(rid, r["routes"]["expt"]) for rid, r in reactions.items() if r["routes"]["expt"]["status"] == "finite"]
    und = [rid for rid, r in reactions.items() if r["routes"]["expt"]["status"] != "finite"]
    out = {"expt_determined": [d[0] for d in det], "expt_undetermined": und}
    if det:
        rid, e = min(det, key=lambda d: d[1]["onset_V"])
        out["expt"] = {"onset_V": e["onset_V"], "limiting": rid, "budget_V": e["budget_V"],
                       "budget_complete": e["budget_complete"], "onset_grid_min_V": min(d[1]["onset_grid_min_V"] for d in det),
                       "complete": not und}
    else:
        out["expt"] = None
    for s in k.SCHEMES:
        vals = [(rid, r["routes"][s]["onset_V"]) for rid, r in reactions.items()
                if s in r["routes"] and r["routes"][s]["status"] == "finite"]
        unds = [rid for rid, r in reactions.items() if s in r["routes"] and r["routes"][s]["status"] != "finite"]
        if vals and not unds:
            rid, v = min(vals, key=lambda d: d[1])
            out[s] = {"onset_V": v, "limiting": rid}
        else:
            out[s] = {"onset_V": None, "limiting": None, "undetermined_reactions": unds or ["all"]}
    return out


def class_status(summ, inf, sup):
    """Status of the tier-1 onset against one cutoff class: below / above / within budget / undetermined."""
    e = summ["expt"]
    if e is None:
        return "undetermined", "no determined reaction on the experimental route"
    m = e["budget_V"]
    if e["onset_V"] < inf - m:
        return "below", "falsifies at tier 1 (the solid-salt onset bounds E_ox from above)"
    if not e["complete"]:
        return "undetermined", "reactions %s undetermined; the determined subset is not below the class" % \
            ",".join(summ["expt_undetermined"])
    if e["onset_V"] >= sup + m:
        return "above", "upper bound only (solid-salt sink): not a pass until a solvated sink exists"
    return "within budget", "onset within the budget of the class"


def comparator_entries(bk):
    """Materials Project entry, space group and energy above the lowest same-formula entry of every DFT species."""
    from pymatgen.core import Composition
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    out = {}
    for sid, spec in k.SPECIES.items():
        if sid in ("Li", "O2", "CO2", "Ca(ClO4)2", "Al(ClO4)3", "H2O") or (spec.get("mp") or {}).get("frozen"):
            continue
        try:
            t = bk.solid(sid)
        except k.Missing:
            continue
        best = next(e for e in bk.by_id[t.meta["material_id"]] if entry_key(e) == t.meta["entry_id"])
        same = bk.ew._by_formula.get(Composition(spec["formula"]).reduced_formula, [])
        low = min(e.energy_per_atom for e in same)
        sg = SpacegroupAnalyzer(best.structure, symprec=0.1)
        out[sid] = {"material_id": t.meta["material_id"], "entry_id": t.meta["entry_id"],
                    "space_group": sg.get_space_group_symbol(), "space_group_number": sg.get_space_group_number(),
                    "n_sites": len(best.structure), "above_lowest_same_formula_eV_per_atom": best.energy_per_atom - low,
                    "licence": (best.data or {}).get("license")}
    return out


# ------------------------------------------------------------------------------------ benchmark
def benchmark(ctx, entries, ew_janaf):
    """DFT minus experiment formation energies (kJ/mol per formula unit) for every phase with both."""
    from pymatgen.core import Composition

    by_id = {}
    for e in entries:
        by_id.setdefault(material_id(e), []).append(e)
    rows = []
    for sid, spec in k.SPECIES.items():
        ex = spec["expt"]
        mp = spec.get("mp") or {}
        if ex["kind"] not in ("row", "janaf") or not mp.get("pin") or sid in ("LiClO4",) and False:
            continue
        pin = mp["pin"]
        cands = by_id.get(pin)
        if not cands:
            continue
        best = min(cands, key=lambda e: e.energy_per_atom)
        comp = Composition(spec["formula"])
        ef = _kj(ew_janaf.formation_energy(best) * comp.num_atoms / best.composition.num_atoms)
        row = {"species": sid, "formula": spec["formula"], "material_id": pin, "mp_Ef_kJ_per_mol": ef,
               "atoms_per_formula": comp.num_atoms}
        if ex["kind"] == "row":
            dg, ug, _ = k.row_kj(ex["dfg"])
            row.update(expt_dfG_kJ_per_mol=dg, expt_dfG_row=ex["dfg"], expt_u_kJ_per_mol=ug)
            if ex.get("dfh"):
                row.update(expt_dfH_kJ_per_mol=k.row_kj(ex["dfh"])[0], expt_dfH_row=ex["dfh"])
        else:  # janaf table
            cdir = ph_cache.PH_CACHE if ex.get("cache") == "ph" else cache.CACHE_DIR
            from nacre.pourbaix import gas as gasmod
            r = gasmod.row_kj(ex["table"], ctx.T, cdir)
            row.update(expt_dfG_kJ_per_mol=r["dfG_kJ_per_mol"], expt_dfG_row=r["table"],
                       expt_dfH_kJ_per_mol=r["dfH_kJ_per_mol"], expt_dfH_row=r["table"])
        row["dft_minus_dfG_kJ_per_mol"] = ef - row["expt_dfG_kJ_per_mol"]
        if "expt_dfH_kJ_per_mol" in row:
            row["dft_minus_dfH_kJ_per_mol"] = ef - row["expt_dfH_kJ_per_mol"]
        row["dft_minus_dfG_kJ_per_atom"] = row["dft_minus_dfG_kJ_per_mol"] / comp.num_atoms
        rows.append(row)
    med = statistics.median(abs(r["dft_minus_dfG_kJ_per_atom"]) for r in rows if r["species"] != "OCP")
    for r in rows:
        r["flag"] = ("inconsistent: |DFT minus DfG| per atom is %.1f times the median of the other species" %
                     (abs(r["dft_minus_dfG_kJ_per_atom"]) / med)) if abs(r["dft_minus_dfG_kJ_per_atom"]) > 2.5 * med else ""
    return rows


# --------------------------------------------------------------------------------- thresholds
def dehydration(ctx):
    """Brushite -> monetite + 2 H2O(l): a_w* at which the hydrate and the anhydrate have equal free energy."""
    bk = k.ExptBook(ctx)
    gb, gm, gw = bk("brushite"), bk("monetite"), bk("H2O")
    dg = gm.g_eV + 2 * gw.g_eV - gb.g_eV
    u = gm.u_kJ + 2 * gw.u_kJ + gb.u_kJ
    kT = k.K_B_EV * ctx.T
    star = math.exp(-dg / (2 * kT))
    lo = math.exp(-(dg + u / KJ_PER_MOL_PER_EV) / (2 * kT))
    hi = math.exp(-(dg - u / KJ_PER_MOL_PER_EV) / (2 * kT))
    return {"reaction": "CaHPO4.2H2O -> CaHPO4 + 2 H2O (liquid at activity a_w)", "dG_kJ_per_mol_a_w_1": _kj(dg),
            "u_kJ_per_mol": u, "a_w_star": star, "a_w_star_range": [lo, hi],
            "reading": "the hydrate is the stable form only above a_w*; a_w* >= 1 within the row uncertainties means brushite "
                       "is not stable against monetite at unit water activity (a precursor, reported not decided)",
            "sources": ["TR-037", "TR-034", "dfg_h2o_l"]}


# --------------------------------------------------------------------------------------- run
def run():
    warnings.simplefilter("ignore")
    ctx = k.Ctx()
    g = k.gate(ctx)
    print("gate: carbonate control %.6f V vs frozen %.3f V (%.3f mV); budget %.6f V vs %.6f V"
          % (g["value_V"], g["frozen_V_inventory"], g["difference_to_inventory_mV"], g["budget_V"], g["frozen_budget_V"]))
    if not g["passed"]:
        print("BLOCKED: gate failed")
        return 1
    entries, excluded = ph_cache.load_entries()
    books = {"expt": k.ExptBook(ctx)} | {s: k.DftBook(s, ctx, entries) for s in k.SCHEMES}
    frozen = json.loads(k.FROZEN_SUMMARY.read_text(encoding="utf-8"))["phases"]["CaCO3"]["by_sink"]["LiClO4"]

    phases = {}
    for ph in k.PHASES:
        pid = ph["id"]
        reactions = {}
        for rid, cls, extra, products in ph["reactions"]:
            try:
                by_sid = k.build_reaction(pid, extra, products)
            except ValueError as exc:  # a registered reaction must balance as an oxidation: fail loudly
                raise SystemExit("registered reaction %s/%s is invalid: %s" % (pid, rid, exc))
            r = evaluate_reaction(by_sid, books if pid != "CaCO3" else {"expt": books["expt"]})
            r["class"] = cls
            if pid == "OCP":  # a stand-alone DfG row: a provisional value is shown, never used for a status
                pv = k.evaluate(by_sid, k.ExptBook(ctx, provisional=True))
                r["provisional_dfg_only"] = {"onset_V": pv["onset_V"], "budget_V": pv.get("budget_V"),
                                             "used_for_status": False,
                                             "why": "one NBS DfG row (TR-039), no DfH or S to cross-check it: undetermined by "
                                                    "rule, the value is shown for information only"}
            r["sink"] = "LiClO4 (solid salt)" if "LiClO4" in extra else "none (Li-open: Li+ leaves as Li)"
            r["sink_kind"] = "solid-salt upper bound" if extra else "Li-open (no salt)"
            if pid == "CaCO3":
                r["routes"]["janaf"] = {"status": "finite", "benchmark_status": "dft, frozen production value", "onset_V": frozen["oxidation_by_scheme"]["janaf"]["value_V"],
                                        "source": "frozen production value (database 2026.04.13)"}
                r["routes"]["mp"] = {"status": "finite", "benchmark_status": "dft, frozen production value", "onset_V": frozen["oxidation_by_scheme"]["mp"]["value_V"],
                                     "source": "frozen production value (database 2026.04.13)"}
                r["dft_minus_expt_V"] = {s: r["routes"][s]["onset_V"] - r["routes"]["expt"]["onset_V"] for s in k.SCHEMES}
            reactions[rid] = r
        summ = phase_summary(pid, reactions)
        phases[pid] = {"name": k.NAMES[pid], "role": ph["role"], "formula": k.SPECIES[pid]["formula"],
                       "reactions": reactions, "summary": summ}

    mp_entries = comparator_entries(books["janaf"])
    bench = benchmark(ctx, entries, books["janaf"].ew)
    dehyd = dehydration(ctx)

    # ladder
    ladder = []
    for pid in k.ORDER:
        ph, summ = phases[pid], phases[pid]["summary"]
        e = summ["expt"]
        for cls, (inf, sup) in k.CUTOFF_CLASSES.items():
            status, note = class_status(summ, inf, sup)
            lim = e["limiting"] if e else None
            ladder.append({
                "phase": pid, "name": ph["name"], "role": ph["role"], "class": cls, "cutoff_inf_V": inf, "cutoff_sup_V": sup,
                "tier1_onset_V": e["onset_V"] if e else None, "limiting_reaction": lim,
                "route": "expt" if e else "none", "margin_V": e["budget_V"] if e else None,
                "margin_complete": e["budget_complete"] if e else None,
                "distance_to_inf_V": (e["onset_V"] - inf) if e else None, "distance_to_sup_V": (e["onset_V"] - sup) if e else None,
                "status": status, "note": note, "undetermined_reactions": ",".join(summ["expt_undetermined"]),
                "onset_grid_min_V": e["onset_grid_min_V"] if e else None,
                "dft_janaf_V": summ["janaf"]["onset_V"], "dft_mp_V": summ["mp"]["onset_V"],
                "dft_status": "dft-unbenchmarked" if pid != "CaCO3" else "frozen production comparator"})

    # clearing sets (a pass needs a solvated sink: none is available)
    classes = list(k.CUTOFF_CLASSES)
    upper = {c: [r["phase"] for r in ladder if r["class"] == c and r["status"] == "above"] for c in classes}
    undet = sorted({r["phase"] for r in ladder if r["status"] == "undetermined"}, key=k.ORDER.index)
    doc = {
        "session": k.SESSION, "generated_utc": provenance.utc_now(), "git_sha": provenance.git_sha(),
        "question": __doc__.split("\n")[0],
        "rule": "claims_redirect.md 2a/2c: E_ox = min over registered oxidation reactions; undetermined never passes; a "
                "solid-salt sink bounds the onset from above (a falsification stands, a pass is inconclusive).",
        "gate": g,
        "inputs": {"params_sha": k.PARAMS_SHA, "evidence_table_sha256": k.evidence_sha256(),
                   "evidence_table_git_blob": provenance._git("rev-parse", "HEAD:lit/evidence_table.csv")[1].strip(),
                   "ph_cache_manifest_sha256": ph_cache.cache_hash(), "production_cache_manifest_sha256": cache.cache_hash(),
                   "supplement_cache_manifest_sha256": sc.cache_hash(),
                   "mp_database_version_ph_cache": ph_cache.manifest()["mp_database_version"],
                   "mp_database_version_production_cache": cache.manifest()["mp_database_version"],
                   "mp_licence_filter": "BY-C only; excluded entries: %s" % (excluded or "none"),
                   "lit_params_corpus_note": "lit/corpus/phosphate_coverage.yaml named in the brief does not exist on any "
                                             "branch; the row ids come from lit/evidence_table.csv (TR-001..TR-119) and "
                                             "lit/corpus/T-R/gaps.md"},
        "conventions": {
            "T_K": ctx.T, "sink": "solid-salt LiClO4 (Ca(ClO4)2 and Al(ClO4)3 through the tabulated exchange enthalpy, solid "
                                  "entropy of the exchange neglected and bounded); solvated sink: gap",
            "water": "H2O(l) at activity a_w on the experimental route; DFT water is H2O(g) at p = a_w x p_sat(%.4f bar)"
                     % books["janaf"].p_sat,
            "a_w_grid": k.A_W_GRID, "a_oh_grid": k.A_OH_GRID,
            "a_oh_reading": "activity of the OH-site (HAp) component in the lattice; lowering it raises the onset",
            "budget": "linear sum of the row uncertainties (2 sigma USGS as printed; NBS rows 20 units of the last figure) plus "
                      "T x the exchange entropy bound, divided by n_e F: the recipe of window_margin_expt, which it reproduces "
                      "for the carbonate reaction",
            "cutoff_classes": {c: {"inf_V": a, "sup_V": b} for c, (a, b) in k.CUTOFF_CLASSES.items()},
            "status_rule": "below: onset < inf - m; above: onset >= sup + m and every reaction determined; undetermined: "
                           "a reaction lacks data and the determined subset is not below; else within budget",
            "polymorph_pins": {s: (v.get("mp") or {}).get("pin") for s, v in k.SPECIES.items() if (v.get("mp") or {}).get("pin")},
        },
        "mp_entries": mp_entries, "phases": phases, "ladder": ladder, "benchmark": bench, "dehydration_threshold": dehyd,
        "upper_bound_above": upper, "undetermined_phases": undet, "key_requests": KEY_REQUESTS,
    }
    k.OUT.mkdir(parents=True, exist_ok=True)
    (k.OUT / "ph_k1.json").write_text(json.dumps(doc, indent=1, sort_keys=False, default=float) + "\n", encoding="utf-8")
    write_ladder(ladder)
    write_benchmark(bench)
    write_md(doc)
    print("wrote", rel(k.OUT / "ph_k1.json"))
    return 0


def _f(x, nd=3):
    return "" if x is None else ("%.*f" % (nd, x))


def write_ladder(ladder):
    cols = ["phase", "role", "class", "cutoff_inf_V", "cutoff_sup_V", "tier1_onset_V", "limiting_reaction", "route",
            "margin_V", "margin_complete", "distance_to_inf_V", "distance_to_sup_V", "status", "note",
            "undetermined_reactions", "onset_grid_min_V", "dft_janaf_V", "dft_mp_V", "dft_status"]
    with open(k.OUT / "ladder.csv", "w", newline="", encoding="utf-8") as fh:
        fh.write("# PH-K1 tier 1 ladder. The margin_V column is PROVISIONAL: a per-reaction budget by the recipe of "
                 "window_margin_expt (not yet a registered key). Tier 2 is added later.\n")
        fh.write("# Onsets are vs Li+/Li at a_w = 1, a_OH = 1 on the experimental route with the solid-salt LiClO4 sink "
                 "(an upper bound): 'below' stands, 'above' is not a pass. DFT columns are comparators.\n")
        wr = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        wr.writeheader()
        for r in ladder:
            row = dict(r)
            for c in ("tier1_onset_V", "margin_V", "distance_to_inf_V", "distance_to_sup_V", "onset_grid_min_V", "dft_janaf_V",
                      "dft_mp_V"):
                row[c] = _f(r[c], 4)
            wr.writerow(row)


def write_benchmark(bench):
    cols = ["species", "formula", "material_id", "atoms_per_formula", "mp_Ef_kJ_per_mol", "expt_dfG_kJ_per_mol", "expt_dfG_row",
            "expt_dfH_kJ_per_mol", "expt_dfH_row", "expt_u_kJ_per_mol", "dft_minus_dfG_kJ_per_mol", "dft_minus_dfH_kJ_per_mol",
            "dft_minus_dfG_kJ_per_atom", "flag"]
    with open(k.OUT / "benchmark.csv", "w", newline="", encoding="utf-8") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        wr.writeheader()
        for r in bench:
            wr.writerow({c: ("%.2f" % v if isinstance(v, float) else v) for c, v in r.items() if c in cols})


def write_md(doc):
    from nacre.pourbaix import ph_k1_md
    (k.OUT / "ph_k1.md").write_text(ph_k1_md.render(doc), encoding="utf-8")


LEDGER = k.REPO / "jobs" / "ledger" / "p0-w5.jsonl"
OUTPUTS = ("ph_k1.json", "ladder.csv", "benchmark.csv", "ph_k1.md", "cache/manifest.json", "cache/janaf_SiO2.json")


def ledger():
    """Append one provenance record for the current outputs (run once per set of outputs)."""
    man = ph_cache.manifest()
    rec = {"session": k.SESSION, "run": "ph-k1-tier1", "kind": "pourbaix-ph-k1", "mock": False,
           "utc": provenance.utc_now(), "git_sha": provenance.git_sha(), "git_dirty": provenance.git_dirty(),
           "params_sha": k.PARAMS_SHA, "cache_hash": cache.cache_hash(), "ph_cache_hash": ph_cache.cache_hash(),
           "evidence_table_sha256": k.evidence_sha256(), "mp_database_version": man["mp_database_version"],
           "outputs": [{"path": rel(k.OUT / o), "sha256": provenance.sha256_file(k.OUT / o)} for o in OUTPUTS],
           "local_only": [{"path": f["location"], "sha256": f["sha256"], "bytes": f["bytes"]}
                          for f in man["files"] if f.get("local_only")]}
    provenance.ledger_append(LEDGER, rec)
    return rec
