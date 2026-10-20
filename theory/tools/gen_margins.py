"""Write the generated `margins_v6` entry of the thresholds block (theory/thresholds.md, block version 6).

Every number in that entry is derived here from committed files read by git object (never typed): the PH-W5.1
outputs of lane p0-w5 (K1 ladder, per-reaction budgets, phosphate benchmark, Al-O-H window) and lit/params.yaml of
lane p0-w1. The pins (commit and blob of each file) are written beside the values, and `--check` re-derives the entry
and compares it with the block. The rules are those of theory/thresholds.md Section 7 and claims_redirect.md
Section 10; this file only applies them. Run from the repository root:

    uv run python theory/tools/gen_margins.py           # rewrite the entry between the markers
    uv run python theory/tools/gen_margins.py --check   # exit 1 if the block differs from a fresh derivation
"""

import csv
import io
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import scipy.constants as sc
import yaml

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS = ROOT / "theory" / "thresholds.md"
BEGIN = "  # BEGIN generated margins_v6 (theory/tools/gen_margins.py; do not edit by hand)"
END = "  # END generated margins_v6"

W5_DIR = "results/preprint/pourbaix/ph_w51/"
PINS = {
    "ladder": {"ref": "origin/preprint/p0-w5", "commit": "c735c78a10f4e26e00041ca28e6e5ab1cd8a3888",
               "file": W5_DIR + "ladder_v2.csv", "blob": "5703cd51c1d961fad1efd9833a7d0ec4478c8a56"},
    "budgets": {"ref": "origin/preprint/p0-w5", "commit": "c735c78a10f4e26e00041ca28e6e5ab1cd8a3888",
                "file": W5_DIR + "ph_w51.json", "blob": "9885f5ac6607cfd2bf835c6891418bb363b88a70"},
    "benchmark": {"ref": "origin/preprint/p0-w5", "commit": "c735c78a10f4e26e00041ca28e6e5ab1cd8a3888",
                  "file": W5_DIR + "benchmark_w51.csv", "blob": "3688b306c5927ddd5893039afad29f9734e83414"},
    "al_window": {"ref": "origin/preprint/p0-w5", "commit": "c735c78a10f4e26e00041ca28e6e5ab1cd8a3888",
                  "file": W5_DIR + "al_window.json", "blob": "dda3174d5004bf188266f79833a31eb58b148074"},
    "params": {"ref": "origin/preprint/p0-w1", "commit": "0e3e2762805d95836102413555f6598153a6e1dc",
               "file": "lit/params.yaml", "blob": "ac9d7ff5e4da06f63038c61551f75b88ff07c4fb"},
}
F = sc.value("Faraday constant")
KJ = 10**3


class SourceMissing(RuntimeError):
    pass


def git_blob(pin):
    """Content of a pinned file, refusing a blob that differs from the pin."""
    spec = "%s:%s" % (pin["commit"], pin["file"])
    try:
        blob = subprocess.run(["git", "rev-parse", spec], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise SourceMissing("%s not in this clone (git fetch origin)" % spec) from exc
    if blob != pin["blob"]:
        raise RuntimeError("%s is blob %s, pinned %s" % (spec, blob, pin["blob"]))
    return subprocess.run(["git", "cat-file", "blob", blob], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def r4(x):
    return None if x is None else round(float(x), 4)


def r3(x):
    return None if x is None else round(float(x), 3)


def load():
    ladder = list(csv.DictReader(io.StringIO("".join(l for l in git_blob(PINS["ladder"]).splitlines(True)
                                                       if not l.startswith("#")))))
    bud = json.loads(git_blob(PINS["budgets"]))
    bench = list(csv.DictReader(io.StringIO("".join(l for l in git_blob(PINS["benchmark"]).splitlines(True)
                                                      if not l.startswith("#")))))
    win = json.loads(git_blob(PINS["al_window"]))
    params = yaml.safe_load(git_blob(PINS["params"]))["params"]
    return ladder, bud, bench, win, params


def cutoff_classes(ladder):
    """The registered classes, read from the ladder's cutoff columns (d_<E>_V) and its status headers."""
    cut = sorted(float(m.group(1)) for k in ladder[0] for m in [re.fullmatch(r"d_([\d.]+)_V", k)] if m)
    names = [k[len("status_"):] for k in ladder[0] if k.startswith("status_")]
    lo, mid, hi = names
    bands = {mid: [float(x) for x in re.findall(r"[\d.]+", mid)], hi: [float(x) for x in re.findall(r"[\d.]+", hi)]}
    lo_vals = [c for c in cut if not any(b[0] <= c <= b[-1] for b in bands.values())]
    return {"C_lo": {"name": lo, "E_c_V": lo_vals}, "C_mid": {"name": mid, "E_c_V": bands[mid]},
            "C_hi": {"name": hi, "E_c_V": bands[hi]}}


def bench_index(bench):
    out = {}
    for row in bench:
        label = row["display"]
        status = label.split(" (")[0]
        delta = row["dft_minus_dfH_kJ_per_atom"]
        out[row["phase"]] = {"status": status, "delta_kJ_per_atom": r3(delta) if delta else None}
    return out


def reaction_margins(bud):
    """One margin per (phase, framing, reaction) on the solid-salt sink: the linear-sum budget of the expt route."""
    rows = []
    for phase, det in bud["detail"].items():
        for framing in ("crystalline", "amorphous"):
            for rid, rx in ((det.get(framing) or {}).get("reactions") or {}).items():
                e = rx["routes"].get("expt") or {}
                row = {"phase": phase, "framing": framing, "reaction": rid, "text": rx["text"], "sink": "LiClO4 (solid salt)"}
                if e.get("status") != "finite":
                    row.update(status="symbolic", reason="expt route undetermined: %s" % ", ".join(
                        m.get("species", "?") for m in e.get("missing", [])) or "input missing")
                    rows.append(row)
                    continue
                terms = e["budget_terms_kJ"]
                n_e = e["n_e"]
                total = sum(terms.values())
                m = total * KJ / (n_e * F)
                if abs(m - e["budget_V"]) > 10**-9:
                    raise RuntimeError("%s %s %s: budget %s V does not reproduce from its terms (%s V)" % (
                        phase, framing, rid, e["budget_V"], m))
                row.update(E_ub_V=r4(e["onset_V"]), n_e=r4(n_e), terms_kJ={k: r3(v) for k, v in terms.items()}, m_V=r4(m))
                refs = {"LiClO4", "O2", "Li"}
                no_u = [s for s, t in e["terms"].items() if s not in refs and not t.get("u_kJ")]
                al_sink = any(s.startswith("Al(ClO4)") for s in rx["stoichiometry"]) and not terms.get("entropy_bound")
                if e.get("budget_complete", True) and not no_u and not al_sink:
                    row["status"] = "set"
                else:
                    why = []
                    if no_u:
                        why.append("no printed uncertainty for %s" % ", ".join(no_u))
                    if al_sink:
                        why.append("no bound on the exchange entropy of the Al perchlorate sink (dfg_al_clo4_3 is a gap)")
                    row.update(status="symbolic", reason="budget incomplete (%s); a partial budget can neither pass nor "
                               "falsify, so the reaction is undetermined" % "; ".join(why), m_V_partial=row.pop("m_V"))
                rows.append(row)
    return rows


def row_crossovers(rows, classes):
    """Tier 1 alone, per phase and framing: falsified at E_c when some reaction has E_ub + m < E_c."""
    out = []
    keyed = {}
    for r in rows:
        keyed.setdefault((r["phase"], r["framing"]), []).append(r)
    for (phase, framing), rs in keyed.items():
        det = [r for r in rs if r["status"] == "set"]
        undet = [r["reaction"] for r in rs if r["status"] != "set"]
        if not det:
            out.append({"phase": phase, "framing": framing, "falsified_above_V": None, "classes": "undetermined",
                        "undetermined_reactions": undet})
            continue
        x = min(r["E_ub_V"] + r["m_V"] for r in det)
        lim = min(det, key=lambda r: r["E_ub_V"] + r["m_V"])["reaction"]
        cls = {}
        for cname, c in classes.items():
            if all(e > x for e in c["E_c_V"]):
                cls[cname] = "falsified (tier 1)"
            elif any(e > x for e in c["E_c_V"]):
                cls[cname] = "partial"
            else:
                cls[cname] = "not falsified"
        out.append({"phase": phase, "framing": framing, "falsified_above_V": r4(x), "by": lim, "classes": cls,
                    "undetermined_reactions": undet})
    return out


def amorphous_by_bound(ladder, crossovers):
    """Falsifying side only: E_ub,glass = E_ub,crystal - DeltaG_g->c/(Delta_n_Li F) with DeltaG_g->c >= 0, so an amorphous
    row without data is falsified wherever its crystalline row is (claims_redirect.md I17); it can never pass this way."""
    cr = {c["phase"]: c for c in crossovers if c["framing"] == "crystalline"}
    have = {c["phase"] for c in crossovers if c["framing"] == "amorphous"}
    out = []
    for row in ladder:
        p = row["phase"]
        if row["framing"] != "amorphous" or row["row_type"] not in ("phase", "baseline") or p in have or p not in cr:
            continue
        if "not registered" in row["label"]:
            continue
        c = cr[p]
        cls = c["classes"] if isinstance(c["classes"], dict) else {}
        out.append({"phase": p, "classes": {k: ("falsified (bound)" if v == "falsified (tier 1)" else "undetermined")
                                            for k, v in cls.items()} or "undetermined"})
    return out


def dft_margin(bud, bidx):
    """m_E applies only where the expt route is missing and every species whose DFT energy does not cancel is
    dft-benchmarked (the exchange sink cancels against LiClO4; O2 and Li are references)."""
    names = {"Ca3(PO4)2 [b-TCP]": "b-TCP", "Ca3(PO4)2 [a-TCP]": "a-TCP", "Ca5(PO4)3OH [HAp]": "HAp",
             "CaPH5O6 [brushite]": "brushite", "Ca8P6H12O29 [OCP]": "OCP", "Ca(PO3)2": "Ca(PO3)2 glass"}
    cancels = {"LiClO4", "Ca(ClO4)2", "Al(ClO4)3", "O2", "Li", "H2O"}
    cases = []
    for phase, det in bud["detail"].items():
        for rid, rx in ((det.get("crystalline") or {}).get("reactions") or {}).items():
            if (rx["routes"].get("expt") or {}).get("status") == "finite":
                continue
            species = [s for s in rx["stoichiometry"] if s not in cancels]
            labels = {s: (bidx.get(names.get(s, s)) or {"status": "not in the benchmark"})["status"] for s in species}
            ok = all(v == "dft-benchmarked" for v in labels.values())
            cases.append({"phase": phase, "reaction": rid, "species": labels, "qualifies": ok})
    return cases


def ruling_b(bud, params, bench):
    """Ruling (b), tighten: the Ca(PO3)2 crystal enters through its direct assessed enthalpy; the analogue
    vitrification enthalpy becomes a consistency check only."""
    vit = bud["staged_products"]["vitrification"]
    vals = bud["staged_products"]["values"]["Ca(PO3)2"]
    det = bud["detail"]["Ca(PO3)2 / Ca-polyphosphate glass"]["crystalline"]["reactions"]["r1"]["routes"]["expt"]
    corr = params["glass_crystal_correction_cameta_calphad"]
    cryst = params["glass_dfh_cameta_crystal"]
    glass = params["glass_dfh_cameta_glass"]
    u_glass = float(next(r for r in bench if r["phase"] == "Ca(PO3)2 glass")["expt_u_kJ"])
    half_span = (cryst["range"]["max"] - cryst["range"]["min"]) / 2 / KJ
    infl = vit["inflation"]
    u_corr = infl * (half_span + u_glass)
    d_corr = corr["value"] / KJ - vals["h_vit_kJ"]
    old_species_u = det["terms"]["Ca(PO3)2"]["u_kJ"]
    new_species_u = old_species_u - vals["u_vit_kJ"] + u_corr - u_glass
    n_e = det["n_e"]
    tab = det["budget_terms_kJ"]["tabulated"] - old_species_u + new_species_u
    m_new = (tab + det["budget_terms_kJ"]["entropy_bound"]) * KJ / (n_e * F)
    n_po3 = 2
    h_max = vit["h_max_kJ_per_PO3"]
    per_po3 = corr["value"] / KJ / n_po3
    return {
        "correction_kJ": r3(corr["value"] / KJ), "correction_key": "glass_crystal_correction_cameta_calphad",
        "check_glass_minus_crystal_kJ": r3((glass["value"] - cryst["value"]) / KJ),
        "u_correction_kJ": r3(u_corr),
        "u_rule": "inflation x (half the polymorph span of glass_dfh_cameta_crystal + tabulated u of the glass enthalpy)",
        "inflation": infl, "half_span_kJ": r3(half_span), "u_glass_kJ": r3(u_glass),
        "band_kJ": [r3(max(0, corr["value"] / KJ - u_corr)), r3(corr["value"] / KJ + u_corr)],
        "analogue_check": {"per_PO3_kJ": r3(per_po3), "analogue_bound_per_PO3_kJ": [0, r3(h_max)],
                           "inside": bool(0 <= per_po3 <= h_max)},
        "replaces": {"h_vit_kJ": r3(vals["h_vit_kJ"]), "u_vit_kJ": r3(vals["u_vit_kJ"])},
        "crystalline_reference_row": {"E_ub_V": r4(det["onset_V"] + d_corr * KJ / (n_e * F)), "m_V": r4(m_new),
                                      "was": {"E_ub_V": r4(det["onset_V"]), "m_V": r4(det["budget_V"])},
                                      "for": "W5 to adopt in the crystalline reference row; the governing amorphous row does not use the correction"},
    }


def residual_entropy(win):
    T = win["conventions"]["T_K"]
    n_po3 = 2
    s_max = n_po3 * sc.R * math.log(2)
    return {"bound_J_per_K": [0, r3(s_max)], "per": "formula unit Ca(PO3)2 (R ln 2 per PO3, n_PO3 = 2)",
            "span_V": r4(T * s_max / (2 * F)),
            "ends": {"E_ub": "S_resid at the upper end (most stable glass, highest onset)", "E_lb": "S_resid = 0"}}


def r1_input_width(win):
    b = win["benchmark"]
    diffs = [abs(x["diff_log"]) for x in b if "diff_log" in x]
    solids = win["solids"]
    return {
        "role": "input width, not a margin: the Omega_AlPP edge stays 1 (as K2); the a(Al3+) prior carries the width",
        "log10_K_s_width": {
            "Al(OH)3 am": {"value": r3(max(diffs)), "from": "largest |diff_log| of the Al ion-data benchmark (tabulated u not printed)"},
            "boehmite": {"value": r3(solids["boehmite"]["u_log"]), "from": "u_log of the boehmite route"}},
        "nu_Al": "the width enters log10 a(Al3+) once per Al3+ in the formula unit (slope -3 per pH unchanged)",
        "active": "no: K_sp,AlPP is a gap (polyp_log10_ksp_al), so R1 is undetermined (F1r) whatever the width"}


def derive():
    ladder, bud, bench, win, params = load()
    classes = cutoff_classes(ladder)
    bidx = bench_index(bench)
    rows = reaction_margins(bud)
    lfp = params["e_cell_max_lfp"]["value"]
    entry = {
        "generated_by": "theory/tools/gen_margins.py",
        "sources": {k: dict(v) for k, v in PINS.items()},
        "cutoff_classes": dict(classes, unit="V", source="ladder columns d_<E>_V and status_<class> (registered names)",
                               flag={"e_cell_max_lfp_V": lfp, "note": "the sourced LFP charge cutoff differs from the registered "
                                     "LFP-class value; the registered value is used; planning chat to confirm"}),
        "m_K1": {
            "symbol": "m_expt per (phase, framing, reaction, sink)",
            "rule": "linear sum of the tabulated uncertainties of every species whose energy does not cancel, plus T0 times "
                    "the bound on the neglected exchange entropy of the solid-salt sink, over n_e F (the cp3 R2 budget of the "
                    "carbonate gate, applied per reaction); a bound, not a standard deviation",
            "rows": [r for r in rows],
        },
        "tier1_crossovers": row_crossovers(rows, classes),
        "tier1_amorphous_by_bound": None,
        "m_E": {"status": "not set for any phosphate row",
                "rule": "m_E = N_unc max(e_form, |delta_P|) / (n_e F) for a reaction without an expt route, only when every "
                        "uncancelled species is dft-benchmarked; otherwise the DFT value is a comparator",
                "e_form_key": "formation_energy_mae", "e_form_kJ_per_atom": r3(params["formation_energy_mae"]["value"] / KJ),
                "cases": dft_margin(bud, bidx),
                "benchmark_per_phase": {k: v for k, v in bidx.items() if v["delta_kJ_per_atom"] is not None}},
        "m_K1_amorphous": {
            "rule": "glass data where they exist (the row's own budget above); otherwise m_am = m_cr + u(DeltaG_g->c)/(n_e F), "
                    "symbolic while the correction is a gap (the row is then undetermined)",
            "ruling_b": ruling_b(bud, params, bench),
            "residual_entropy": residual_entropy(win)},
        "m_svc": {"status": "rule (per record)", "rule": "the potential uncertainty stated by the tier 2 record; if none is "
                  "stated, one unit of the last printed digit of its potential; never below that digit"},
        "K2": {"margin": "none (edge 1; K_sp and speciation carry their uncertainty)"},
        "K2h": {"margin": "none beyond tau_k", "f_min": "symbolic: needs a registered criterion for when an orthophosphate "
                "fraction sets the film's K1 (coverage or percolation), a gap"},
        "K3_R1": r1_input_width(win),
        "K4": {"m_S": "unchanged (thresholds.C4.margin_S_spread, zero: the priors carry the method error)"},
    }
    entry["tier1_amorphous_by_bound"] = amorphous_by_bound(ladder, entry["tier1_crossovers"])
    return entry


class _Flow(dict):
    pass


yaml.SafeDumper.add_representer(_Flow, lambda d, data: d.represent_mapping(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, data, flow_style=True))


def render(entry):
    """Rows of the long lists are written one mapping per line (flow style)."""
    for key in ("rows",):
        entry["m_K1"][key] = [_Flow(r) for r in entry["m_K1"][key]]
    entry["tier1_crossovers"] = [_Flow(r) for r in entry["tier1_crossovers"]]
    entry["m_E"]["cases"] = [_Flow(r) for r in entry["m_E"]["cases"]]
    entry["tier1_amorphous_by_bound"] = [_Flow(r) for r in entry["tier1_amorphous_by_bound"]]
    body = yaml.safe_dump({"margins_v6": entry}, sort_keys=False, width=10**4, default_flow_style=None, allow_unicode=True)
    body = "\n".join("  " + l if l else l for l in body.splitlines())
    return "%s\n%s\n%s" % (BEGIN, body, END)


def main(argv):
    text = THRESHOLDS.read_text(encoding="utf-8")
    pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    try:
        new = render(derive())
    except SourceMissing as exc:
        print("gen_margins: %s" % exc)
        return 2
    if "--check" in argv:
        m = pat.search(text)
        same = bool(m) and m.group(0) == new
        print("gen_margins: margins_v6 %s" % ("matches a fresh derivation" if same else "DIFFERS from a fresh derivation"))
        return 0 if same else 1
    if not pat.search(text):
        print("gen_margins: markers not found in theory/thresholds.md")
        return 1
    THRESHOLDS.write_text(pat.sub(lambda _: new, text), encoding="utf-8")
    print("gen_margins: wrote margins_v6")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
