"""PH-W5.1 step 1: the phosphate benchmark of Materials Project formation energies (lane p0-w5).

Question: for every phase with both a tabulated formation value (lit/evidence_table.csv rows, or a cached
JANAF table) and a Materials Project entry, how far is the DFT formation energy (0 K, MP2020 corrections,
database 2026.09.28) from experiment per formula unit, and why? The DFT number is a 0 K energy, so the
enthalpy DfH is the like-for-like comparison; DfG is printed beside it. Each phase gets a one-line cause
from what the entry itself records (its MP2020 energy adjustments, its structure) and the tabulated phase.

Display rule read off the registered error key (thresholds.C5.formation_energy_error, params key
formation_energy_mae, upper end of its sourced span): a phase whose |DFT - DfH| per atom lies within it is
`dft-benchmarked` (shown as a comparator with its measured error); outside it, `dft-benchmark-failed`
(shown only as a labelled comparator with its measured error); with no tabulated value,
`dft-unbenchmarked`. No MP number is ever shown unlabelled, and none passes or falsifies a K1 row.

    uv run python -m nacre.pourbaix.ph_w51 benchmark
"""
import csv
import json
import statistics

import yaml

from nacre.pourbaix import cache, ph_cache
from nacre.pourbaix import gas as gasmod
from nacre.pourbaix import ph_k1 as k
from nacre.pourbaix import ph_w51_cache as wc
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV, material_id
from nacre.pourbaix.paths import LIT_PARAMS, REPO, rel

OXIDE_CORRECTION_EV_PER_O = None  # read from the entries (MP2020 anion correction (oxide)), never typed
PH_K1_JSON = k.OUT / "ph_k1.json"

# phase -> formula, expt rows (dfh / dfg row ids or a JANAF table), MP selection (pin or space group number),
# lattice-water count, OH count, and the structural note on the tabulated phase. One line per phase.
PHASES = [
    {"id": "P2O5", "formula": "P2O5", "dfh": "TR-011", "dfg": "TR-012", "pin": "mp-562613", "family": "phosphate"},
    {"id": "H3PO4", "formula": "H3PO4", "dfg": "TR-119", "pin": "mp-23902", "family": "phosphate", "n_oh": 3},
    {"id": "HAp", "formula": "Ca5(PO4)3OH", "dfh": "TR-008", "dfg": "TR-009", "pin": "mp-41472", "family": "phosphate",
     "n_oh": 1},
    {"id": "b-TCP", "formula": "Ca3(PO4)2", "dfh": "TR-005", "dfg": "TR-006", "pin": "mp-531132", "family": "phosphate"},
    {"id": "a-TCP", "formula": "Ca3(PO4)2", "dfh": "TR-025", "dfg": "TR-026", "pin": "mp-1197377", "family": "phosphate"},
    {"id": "OCP", "formula": "Ca8P6H12O29", "dfg": "TR-039", "pin": "mp-1229154", "family": "phosphate", "n_w": 5, "n_oh": 2},
    {"id": "brushite", "formula": "CaPH5O6", "dfh": "TR-036", "dfg": "TR-037", "pin": "mp-24389", "family": "phosphate",
     "n_w": 2, "n_oh": 1},
    {"id": "monetite", "formula": "CaHPO4", "dfh": "TR-033", "dfg": "TR-034", "pin": "mp-24390", "family": "phosphate",
     "n_oh": 1},
    {"id": "Ca2P2O7", "formula": "Ca2P2O7", "dfh": "TR-028", "dfg": "TR-029", "pin": "mp-3531", "family": "phosphate"},
    {"id": "AlPO4", "formula": "AlPO4", "dfh": "TR-002", "dfg": "TR-003", "pin": "mp-5331", "family": "phosphate"},
    {"id": "Li3PO4", "formula": "Li3PO4", "dfh": "TR-040", "lowest": True, "family": "phosphate"},
    {"id": "LiPO3", "formula": "LiPO3", "dfh": "TR-042", "lowest": True, "family": "phosphate"},
    {"id": "LiPO3 glass", "formula": "LiPO3", "dfh": "TR-041", "dfh_alt": "TT-044", "lowest": True, "family": "phosphate",
     "glass": True},
    {"id": "Ca(PO3)2 glass", "formula": "Ca(PO3)2", "dfh": "TR-032", "pin": "mp-5680", "family": "phosphate", "glass": True},
    {"id": "CaSiO3", "formula": "CaSiO3", "dfh": "TR-017", "dfg": "TR-018", "pin": "mp-4429", "family": "silicate"},
    {"id": "Ca2SiO4", "formula": "Ca2SiO4", "dfh": "TR-020", "dfg": "TR-021", "pin": "mp-4481", "family": "silicate"},
    {"id": "Li2SiO3", "formula": "Li2SiO3", "dfh": "TR-043", "dfg": "TR-044", "pin": "mp-5012", "family": "silicate"},
    {"id": "boehmite", "formula": "AlHO2", "dfg": "TI-026", "lowest": True, "family": "Al-O-H", "n_oh": 1},
    {"id": "gibbsite", "formula": "Al(OH)3", "dfh": "TI-028", "sg": [14], "family": "Al-O-H", "n_oh": 3},
    {"id": "CaCO3", "formula": "CaCO3", "dfg": "TI-002", "pin": "mp-3953", "family": "carbonate"},
    {"id": "LiClO4", "formula": "LiClO4", "janaf": "LiClO4", "pin": "mp-30301", "family": "sink salt"},
]

# One-line causes. Slots are filled from the computed row (numbers are never typed here).
CAUSES = {
    "P2O5": "no cation: every O is in covalent P-O (bridging and terminal), where the oxide correction fitted on "
            "ionic oxides over-corrects ({raw_per_O:+.0f} kJ/mol raw per O against {corr_per_O:.0f} applied); largest "
            "per-atom error of the anhydrous set",
    "H3PO4": "DfG only (no DfH): a molecular acid crystal; 3 OH oxygens carry the oxide correction; entropy of the "
             "free energy not separable",
    "HAp": "within the registered error per atom; the one OH oxygen also carries the oxide correction",
    "b-TCP": "within the registered error per atom: the most ionic Ca-O environment, closest to the oxides the "
             "correction was fitted on (MP cell R3, {n_sites} sites, an ordered approximant of the partly occupied "
             "whitlockite structure)",
    "a-TCP": "polymorph mismatch: the table's alpha form is the metastable high-temperature polymorph "
             "(DfH {dh_ab:+.1f} kJ/mol above beta), MP places its alpha cell {dft_ab:+.1f} kJ/mol from its beta cell: "
             "the alpha-beta order is {order}",
    "OCP": "DfG only (no DfH or S): five lattice waters and two HPO4 OH carry the oxide correction (not "
           "separable without DfH)",
    "brushite": "hydrate-water handling: MP2020 applies the oxide correction to the two lattice-water O as to "
                "lattice oxide; brushite exceeds monetite by {hyd_excess:.1f} kJ/mol per water against "
                "{corr_per_O:.1f} kJ/mol per O of the correction",
    "monetite": "acid phosphate: the HPO4 P-O(H) oxygen is covalent and H-bonded; over-correction "
                "({raw_per_O:+.0f} kJ/mol raw per O)",
    "Ca2P2O7": "one bridging P-O-P per formula unit: over-correction between the orthophosphates and P2O5",
    "AlPO4": "berlinite, the tabulated polymorph (no mismatch); Al-O and P-O both covalent in the quartz-like "
             "framework: over-correction ({raw_per_O:+.0f} kJ/mol raw per O)",
    "Li3PO4": "DfH only; MP lowest Li3PO4 entry ({mid}, {sg}) against the tabulated crystalline Li3PO4 (polymorph not "
              "stated in the table)",
    "LiPO3": "DfH only; covalent PO3 chains: over-correction as for the condensed phosphates",
    "LiPO3 glass": "polymorph mismatch: the table's value is the glass, MP has only crystals; the two tabulated glass "
                   "values differ by {alt_spread:.1f} kJ/mol (TR-041, TT-044)",
    "Ca(PO3)2 glass": "polymorph mismatch: the table's value is the glass (TR-032), MP mp-5680 is the crystal; the "
                      "difference contains the vitrification enthalpy",
    "CaSiO3": "silicate comparator: ionic, near the registered error",
    "Ca2SiO4": "silicate comparator: ionic, near the registered error",
    "Li2SiO3": "silicate comparator: within the registered error",
    "boehmite": "DfG only (DfH not in the corpus); MP lowest AlO(OH) cell ({mid}, {sg}), an H-ordered cell",
    "gibbsite": "Al hydroxide: three OH oxygens carry the oxide correction",
    "CaCO3": "DfG only; carbonate C-O is covalent (over-correction as for the oxyanions)",
    "LiClO4": "perchlorate: the four O bonded to Cl(VII) carry the oxide correction; cancels in every K1 reaction "
              "(Cl conserved)",
}

CAUSE_SHORT = {
    "P2O5": "covalent P-O only: oxide correction over-corrects", "H3PO4": "DfG only", "HAp": "within error (OH O corrected)",
    "b-TCP": "within error (ionic Ca-O)", "a-TCP": "within error; alpha/beta order inverted (polymorph)",
    "OCP": "DfG only (5 lattice waters)", "brushite": "hydrate water given the oxide correction",
    "monetite": "acid HPO4: over-correction", "Ca2P2O7": "P-O-P bridge: over-correction",
    "AlPO4": "covalent Al-O/P-O framework: over-correction", "Li3PO4": "within error (polymorph unstated)",
    "LiPO3": "PO3 chains: over-correction", "LiPO3 glass": "glass vs crystal", "Ca(PO3)2 glass": "glass vs crystal",
    "CaSiO3": "ionic, near the limit", "Ca2SiO4": "ionic, near the limit", "Li2SiO3": "within error",
    "boehmite": "DfG only", "gibbsite": "three OH O corrected", "CaCO3": "DfG only",
    "LiClO4": "Cl-O given the oxide correction (cancels)",
}


def e_form_kj_per_atom():
    """Registered error per atom (upper end of the sourced span), kJ/mol per atom."""
    p = yaml.safe_load(LIT_PARAMS.read_text(encoding="utf-8"))["params"]["formation_energy_mae"]
    return {"value": p["value"] / 1000.0, "max": p["range"]["max"] / 1000.0, "min": p["range"]["min"] / 1000.0,
            "key": "formation_energy_mae (thresholds.C5.formation_energy_error)", "sources": p["sources"]}


def _select(spec, by_id, by_formula):
    from pymatgen.core import Composition
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    if spec.get("pin"):
        cands = by_id.get(spec["pin"]) or []
    else:
        cands = by_formula.get(Composition(spec["formula"]).reduced_formula, [])
        if spec.get("sg"):
            cands = [e for e in cands if SpacegroupAnalyzer(e.structure, symprec=0.1).get_space_group_number()
                     in spec["sg"]] or cands
    if not cands:
        return None
    return min(cands, key=lambda e: (e.energy_per_atom, material_id(e)))


def rows(entries, ew):
    """Benchmark rows (kJ/mol per formula unit)."""
    from pymatgen.core import Composition
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer

    by_id, by_formula = {}, {}
    for e in entries:
        by_id.setdefault(material_id(e), []).append(e)
        by_formula.setdefault(e.composition.reduced_formula, []).append(e)
    ef = e_form_kj_per_atom()
    out = []
    for spec in PHASES:
        best = _select(spec, by_id, by_formula)
        if best is None:
            continue
        comp = Composition(spec["formula"])
        scale = comp.num_atoms / best.composition.num_atoms
        adj = [a for a in best.energy_adjustments if "oxide" in a.name]
        corr = sum(a.value for a in adj) * scale * KJ_PER_MOL_PER_EV
        n_o = comp["O"]
        sga = SpacegroupAnalyzer(best.structure, symprec=0.1)
        r = {"phase": spec["id"], "formula": spec["formula"], "family": spec["family"], "material_id": material_id(best),
             "space_group": sga.get_space_group_symbol(), "n_sites": len(best.structure),
             "atoms_per_formula": comp.num_atoms, "n_O": n_o, "n_lattice_water": spec.get("n_w", 0),
             "n_OH": spec.get("n_oh", 0), "mp_Ef_kJ": ew.formation_energy(best) * scale * KJ_PER_MOL_PER_EV,
             "mp2020_oxide_correction_kJ": corr,
             "corr_per_O_kJ": corr / n_o if n_o else None, "glass": bool(spec.get("glass"))}
        if spec.get("janaf"):
            j = gasmod.row_kj(spec["janaf"], 298.15, cache.CACHE_DIR)
            r.update(expt_dfH_kJ=j["dfH_kJ_per_mol"], expt_dfG_kJ=j["dfG_kJ_per_mol"], dfH_source=j["table"],
                     dfG_source=j["table"], expt_u_kJ=None)
        else:
            if spec.get("dfh"):
                v, u, _ = k.row_kj(spec["dfh"])
                r.update(expt_dfH_kJ=v, dfH_source=spec["dfh"], expt_u_kJ=u)
                if spec.get("dfh_alt"):
                    va, _, _ = k.row_kj(spec["dfh_alt"])
                    r.update(expt_dfH_alt_kJ=va, dfH_alt_source=spec["dfh_alt"], alt_spread=abs(va - v))
            if spec.get("dfg"):
                v, u, _ = k.row_kj(spec["dfg"])
                r.update(expt_dfG_kJ=v, dfG_source=spec["dfg"])
                r.setdefault("expt_u_kJ", u)
        if r.get("expt_dfH_kJ") is not None:
            d = r["mp_Ef_kJ"] - r["expt_dfH_kJ"]
            r.update(dft_minus_dfH_kJ=d, dft_minus_dfH_kJ_per_atom=d / comp.num_atoms,
                     dft_minus_dfH_per_O_kJ=d / n_o if n_o else None,
                     raw_minus_dfH_per_O_kJ=(d - corr) / n_o if n_o else None)
        if r.get("expt_dfG_kJ") is not None:
            r["dft_minus_dfG_kJ"] = r["mp_Ef_kJ"] - r["expt_dfG_kJ"]
        basis = r.get("dft_minus_dfH_kJ_per_atom")
        if basis is None:
            r["display"] = "dft-unbenchmarked (DfG only: the 0 K energy has no like-for-like DfH)"
        elif r["glass"]:
            r["display"] = "dft-unbenchmarked (the tabulated phase is a glass, MP a crystal)"
        elif abs(basis) <= ef["max"]:
            r["display"] = "dft-benchmarked (|error| %.1f <= %.2f kJ/mol per atom)" % (abs(basis), ef["max"])
        else:
            r["display"] = "dft-benchmark-failed (|error| %.1f > %.2f kJ/mol per atom)" % (abs(basis), ef["max"])
        out.append(r)
    _causes(out)
    return out


def _causes(out):
    by = {r["phase"]: r for r in out}
    corr_per_O = next(r["corr_per_O_kJ"] for r in out if r["corr_per_O_kJ"])
    extra = {}
    if "brushite" in by and "monetite" in by:
        extra["hyd_excess"] = (by["brushite"]["dft_minus_dfH_kJ"] - by["monetite"]["dft_minus_dfH_kJ"]) / 2.0
    if "a-TCP" in by and "b-TCP" in by:
        dh_ab = by["a-TCP"]["expt_dfH_kJ"] - by["b-TCP"]["expt_dfH_kJ"]
        dft_ab = by["a-TCP"]["mp_Ef_kJ"] - by["b-TCP"]["mp_Ef_kJ"]
        extra.update(dh_ab=dh_ab, dft_ab=dft_ab, order="inverted" if dh_ab * dft_ab < 0 else "the same")
    for r in out:
        slots = dict(r, corr_per_O=r["corr_per_O_kJ"] or corr_per_O, raw_per_O=r.get("raw_minus_dfH_per_O_kJ") or 0.0,
                     mid=r["material_id"], sg=r["space_group"], alt_spread=r.get("alt_spread", 0.0), **extra)
        r["cause"] = CAUSES[r["phase"]].format(**slots)
        r["cause_short"] = CAUSE_SHORT[r["phase"]]
        if r["phase"] == "brushite":
            r["hydrate_excess_per_water_kJ"] = extra["hyd_excess"]
        if r["phase"] == "a-TCP":
            r.update(alpha_minus_beta_expt_kJ=extra["dh_ab"], alpha_minus_beta_dft_kJ=extra["dft_ab"])


def onset_spread():
    """DFT minus experiment onsets over the PH-K1 reactions (same reaction, both gas schemes)."""
    doc = json.loads(PH_K1_JSON.read_text(encoding="utf-8"))
    vals = []
    for pid, ph in doc["phases"].items():
        if pid == "CaCO3":
            continue
        for rid, r in ph["reactions"].items():
            for s, d in (r.get("dft_minus_expt_V") or {}).items():
                vals.append({"phase": pid, "reaction": rid, "scheme": s, "dft_minus_expt_V": d})
    lo = min(vals, key=lambda v: v["dft_minus_expt_V"])
    hi = max(vals, key=lambda v: v["dft_minus_expt_V"])
    return {"n": len(vals), "min": lo, "max": hi,
            "median_V": statistics.median(v["dft_minus_expt_V"] for v in vals), "values": vals,
            "source": rel(PH_K1_JSON)}


def p_reference(entries):
    """The MP elemental P reference (lowest-energy P entry) and what the tables refer to."""
    ps = [e for e in entries if e.composition.reduced_formula == "P"]
    ref = min(ps, key=lambda e: e.energy_per_atom)
    from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
    return {"mp_reference": material_id(ref), "space_group": SpacegroupAnalyzer(ref.structure, 0.1).get_space_group_symbol(),
            "n_sites": len(ref.structure), "n_P_entries": len({material_id(e) for e in ps}),
            "tables": "the NBS and USGS tables refer P to white phosphorus (JANAF P-002 is the white crystal); no MP "
                      "entry is white P, so every P-bearing error contains the MP-reference-to-white-P offset, which is "
                      "not quantified here (no sourced allotrope DfH in the corpus)"}


def run(entries, ew):
    bench = rows(entries, ew)
    spread = onset_spread()
    ef = e_form_kj_per_atom()
    errs_h = [r for r in bench if r.get("dft_minus_dfH_kJ") is not None and not r["glass"] and r["family"] == "phosphate"]
    summary = {
        "e_form": ef,
        "phosphate_dfH_error_range_kJ": [min(abs(r["dft_minus_dfH_kJ"]) for r in errs_h),
                                         max(abs(r["dft_minus_dfH_kJ"]) for r in errs_h)],
        "benchmark_passes_for_phosphates": all(r["display"].startswith("dft-benchmarked") for r in errs_h),
        "onset_spread": {x: spread[x] for x in ("n", "min", "max", "median_V", "source")},
        "p_reference": p_reference(entries),
        "oxide_correction_kJ_per_O": next(r["corr_per_O_kJ"] for r in bench if r["corr_per_O_kJ"]),
        "reading": "MP2020 applies one oxide correction per O atom whatever the O bonds to (lattice oxide, OH, lattice "
                   "water, covalent P-O, P-O-P, Cl-O); it was fitted on ionic oxides. Raw GGA underbinding per O falls "
                   "from the ionic Ca orthophosphates and silicates to the covalent P2O5, AlPO4 and acid phosphates, so "
                   "the uniform correction over-corrects the condensed and acid phases and every lattice water. The "
                   "DFT-minus-experiment spread on one reaction is itself an SI finding: DFT is never shown unlabelled.",
        "display_rule": "dft-benchmarked: comparator with its measured error; dft-benchmark-failed: labelled comparator "
                        "with its measured error; dft-unbenchmarked: comparator without a measured error. None passes or "
                        "falsifies a K1 row; the experimental route governs.",
    }
    return bench, summary


BENCH_COLS = ["phase", "formula", "family", "material_id", "space_group", "n_sites", "atoms_per_formula", "n_O",
              "n_lattice_water", "n_OH", "mp_Ef_kJ", "mp2020_oxide_correction_kJ", "expt_dfH_kJ", "dfH_source",
              "expt_dfH_alt_kJ", "dfH_alt_source", "expt_dfG_kJ", "dfG_source", "expt_u_kJ", "dft_minus_dfH_kJ",
              "dft_minus_dfH_kJ_per_atom", "dft_minus_dfH_per_O_kJ", "raw_minus_dfH_per_O_kJ", "dft_minus_dfG_kJ",
              "display", "cause"]


def write_csv(bench, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write("# PH-W5.1 phosphate benchmark: Materials Project 2026.09.28 (BY-C, MP2020) minus tabulated formation "
                 "values, kJ/mol per formula unit. DFT is a 0 K energy: DfH is the like-for-like basis.\n")
        wr = csv.DictWriter(fh, fieldnames=BENCH_COLS, extrasaction="ignore", lineterminator="\n")
        wr.writeheader()
        for r in bench:
            wr.writerow({c: ("%.2f" % v if isinstance(v, float) else ("" if v is None else v))
                         for c, v in r.items() if c in BENCH_COLS})


def inputs_record():
    return {"evidence_table_sha256": k.evidence_sha256(), "ph_k1_cache_manifest_sha256": ph_cache.cache_hash(),
            "w51_cache_manifest_sha256": wc.cache_hash(), "mp_database_version": wc.manifest()["mp_database_version"],
            "params_file": rel(LIT_PARAMS), "repo": REPO.name}
