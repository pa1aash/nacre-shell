"""R-cell window, final run (P0-W5.2, task C).

Thermodynamic question: between which potentials vs Li+/Li are CaCO3 and the native Al oxide at
equilibrium against lithiation and against oxidation that releases CO2 and O2, with the cation
taken up by the anion of each registered electrolyte salt; and does the regime range
[E_cell_min, E_cell_max] lie inside each window under every gas-reference scheme? Windows are
thermodynamic; nothing here is a rate.

- Reduction: the Li-open grand potential (MP energies, 0 K); no gas enters, so the limit does not
  depend on the gas scheme. The all-experimental route is a cross-check where every lithiation
  product is tabulated.
- Oxidation: explicit reactions phase + x LiA -> sink + CO2 + O2 + n Li (theory Eq. th:eq:sink)
  for the anion A of each registered salt, under every scheme: `janaf`, `mp` (gasref.SCHEMES) and
  `expt` (every species from fetched tables or W1 keys). A missing sink phase makes the limit
  undetermined, never a pass.
- Verdict: cp2 ruling F5, applied mechanically per phase, salt and scheme (see f5_verdict).
"""
import math
import re

from scipy import constants

from nacre.pourbaix import cache, gasref, salts
from nacre.pourbaix import window as w
from nacre.pourbaix.cell import chemsys_entries
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV, entry_key, material_id
from nacre.pourbaix.paths import rel

K_B_EV = constants.k / constants.e
F_KJ = constants.e * constants.N_A / 1000.0

# expt scheme: formula -> W1 params key (dfG, J mol^-1, 298.15 K) or JANAF table name
EXPT_PARAMS = {"CaCO3": "dfg_caco3_calcite", "CaO": "dfg_cao", "Al2O3": "dfg_corundum", "LiCl": "dfg_licl",
               "CaCl2": "dfg_cacl2", "LiNO3": "dfg_lino3", "Ca(NO3)2": "dfg_ca_no3_2", "Li2SO4": "dfg_li2so4",
               "CaSO4": "dfg_caso4", "Al2(SO4)3": "dfg_al2_so4_3", "CO2": "dfg_co2_g"}
EXPT_JANAF = ("LiClO4", "Li2CO3", "Li2O", "AlCl3")


class ExchangeBook:
    """A scheme's energy book, plus sink salts entered through a tabulated exchange enthalpy."""

    def __init__(self, base, exchange):
        self.base = base
        self.exchange = exchange  # formula -> (Li salt, count, dH eV, locator)

    def __call__(self, formula):
        try:
            return self.base(formula)
        except w.MissingPhase:
            if formula not in self.exchange:
                raise
            li, n, dh, loc = self.exchange[formula]
            g_li, meta = self.base(li)
            return n * g_li + dh, {"kind": "derived", "basis": "exchange Ca + %d %s -> %s + %d Li: %g x G(%s) "
                                   "under this scheme plus the tabulated exchange enthalpy" % (n, li, formula, n, n, li),
                                   "exchange_dH_eV": dh, "locator": loc, "li_salt": meta}


class ExptBook:
    """All-experimental free energies (eV per formula unit, 298.15 K): W1 keys and JANAF tables."""

    def __init__(self, params, T, pressures):
        if abs(T - 298.15) > 1e-9:
            raise ValueError("the expt scheme is tabulated at 298.15 K")
        self.params, self.T, self.p = params, T, pressures

    def __call__(self, formula):
        if formula == "Li":
            return 0.0, {"kind": "reference", "basis": "Li metal"}
        if formula == "O2":
            return K_B_EV * self.T * math.log(self.p["O2"]), {"kind": "gas", "basis": "element in its reference state"}
        if formula in EXPT_PARAMS:
            key = EXPT_PARAMS[formula]
            if self.params.unit(key) != "J mol^-1":
                raise ValueError(key)
            g = float(self.params.value(key)) / 1000.0 / KJ_PER_MOL_PER_EV
            if formula == "CO2":
                g += K_B_EV * self.T * math.log(self.p["CO2"])
            return g, {"kind": "expt", "source": self.params.cite(key)}
        if formula in EXPT_JANAF:
            r = salts.janaf(formula, self.T)
            return r["dfG_kJ_per_mol"] / KJ_PER_MOL_PER_EV, {"kind": "expt", "source": r["table"]}
        raise w.MissingPhase(formula)


def exchange_table(cfg, T):
    out = {}
    for salt, li in (cfg.get("exchange", {}).get("salts") or {}).items():
        dh_salt, loc_s = salts.dfh_kj(salt, T)
        dh_li, loc_l = salts.dfh_kj(li, T)
        n = 2  # CaA2 from 2 LiA (the exchange is written for divalent Ca)
        out[salt] = (li, n, (dh_salt - n * dh_li) / KJ_PER_MOL_PER_EV, [loc_s, loc_l])
    return out


def books(cfg, params, T):
    entries = gasref.pooled_entries()
    pinned = {f: p["material_id"] for f, p in cfg["phases"].items()}
    ex = exchange_table(cfg, T)
    gases = {g: {"pressure_bar": float(cfg["gas_pressure_bar"][g]),
                 "enthalpy_scheme": gasref.SCHEMES[s][g]["enthalpy_scheme"]} for s in ("janaf",) for g in ("O2", "CO2")}
    out = {}
    for s in cfg["schemes"]:
        if s == "expt":
            out[s] = ExchangeBook(ExptBook(params, T, {g: float(cfg["gas_pressure_bar"][g]) for g in ("O2", "CO2")}), ex)
        else:
            gs = {g: {"pressure_bar": gases[g]["pressure_bar"], "enthalpy_scheme": gasref.SCHEMES[s][g]["enthalpy_scheme"]}
                  for g in ("O2", "CO2")}
            out[s] = ExchangeBook(w.EnergyBook(entries, T, gs, cache.CACHE_DIR, pinned=pinned), ex)
    return out, ex


def limit_dict(c):
    if c.status == "finite":
        return {"status": "ok", "value_V": c.onset_V, "reaction": c.reaction, "reason": "",
                "method": "explicit oxidation reaction", "delta_g_ev": c.delta_g_ev, "delta_n_li": c.delta_n_li}
    return {"status": "undetermined", "value_V": None, "reaction": c.reaction or "", "method": "explicit oxidation reaction",
            "reason": c.reason or "not computable", "delta_g_ev": None, "delta_n_li": None}


def oxidation(phase, spec, salt_id, salt, bk):
    """Lowest onset over the salt's products under one scheme (a list of candidates)."""
    sink = {"li_source": salt["li_source"], "products": salt["products"]}
    cands = [w.oxidation_candidate(phase, spec["cation"], salt_id, sink, prod, bk, tuple(spec["gases"]))
             for prod in salt["products"][spec["cation"]]]
    ok = [c for c in cands if c.status == "finite"]
    best = min(ok, key=lambda c: c.onset_V) if ok and len(ok) == len(cands) else (
        next(c for c in cands if c.status != "finite"))
    return best, cands


def margin_provisional(cand, e_form_ev):
    """Provisional m_E (V) by W1's stated recipe: e_form times the atoms of the DFT-computed solids
    in the reaction, per transferred electron (linear sum). W1 owns window_margin (P0-W1.3)."""
    if cand.status != "finite":
        return None
    atoms = 0.0
    for f, sp in cand.species.items():
        if sp.get("kind") in ("solid", "derived"):
            from pymatgen.core import Composition

            atoms += abs(sp["coefficient"]) * Composition(f).num_atoms
    return e_form_ev * atoms / abs(cand.delta_n_li)


def reduction(spec):
    from pymatgen.analysis.phase_diagram import PhaseDiagram

    ents = chemsys_entries(spec["lithiation_chemsys"])
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pd = PhaseDiagram(ents)
    pe_ = [e for e in ents if material_id(e) == spec["material_id"]]
    red, _, note = w.li_open_limits(pd, pe_[0])
    return red, note, entry_key(pe_[0])


def expt_reduction(phase, red, expt):
    """The Li-open lithiation reaction re-evaluated with tabulated free energies, if every species is."""
    if red.status != "finite":
        return {"status": "undetermined", "value_V": None, "reaction": "", "reason": "no lithiation reaction"}
    rhs = red.reaction.split("->")[1]
    terms = re.findall(r"([0-9.]+)?\s*([A-Z][A-Za-z0-9()]*)", rhs)
    prods = [f for _, f in terms]
    try:
        coeffs, text = w.balance([phase, "Li"], prods, phase)
        dg = sum(c * expt(f)[0] for f, c in coeffs.items() if f != "Li" and f not in ("C", "Al", "Ca"))
    except w.MissingPhase as exc:
        return {"status": "undetermined", "value_V": None, "reaction": red.reaction,
                "reason": "%s not tabulated in the fetched sources" % exc.args[0]}
    dn = coeffs["Li"]
    return {"status": "ok", "value_V": dg / dn, "reaction": text, "reason": "",
            "method": "Li-open lithiation reaction with tabulated free energies (elements at 0)"}


def f5_verdict(ox_by_scheme, e_max, m_e, solid_salt):
    """cp2 ruling F5 for one phase and one sink. A pass must hold under the lowest-onset scheme and
    counts only with a solvated sink; a falsification must hold under every scheme; a solid-salt
    falsification stands and a solid-salt pass is inconclusive; undetermined never passes."""
    vals = {s: l["value_V"] for s, l in ox_by_scheme.items()}
    if any(v is None for v in vals.values()):
        undet = sorted(s for s, v in vals.items() if v is None)
        return "inconclusive", "limit undetermined under scheme(s) %s; a falsification must hold under every scheme" % undet
    lo, hi = min(vals.values()), max(vals.values())
    if hi < e_max - m_e:
        return "falsified", ("E_ox < E_cell_max - m_E under every scheme (highest %.3f V < %.3f V)%s"
                             % (hi, e_max - m_e, "; solid-salt limit is an upper bound on the onset, so the "
                                "falsification stands" if solid_salt else ""))
    if lo >= e_max + m_e:
        if solid_salt:
            return "inconclusive", "passes under the lowest-onset scheme (%.3f V) but with a solid-salt sink only" % lo
        return "feasible", "passes under the lowest-onset scheme (%.3f V)" % lo
    return "inconclusive", ("the schemes straddle E_cell_max (%.3f V, margin %.3f V): onsets %.3f to %.3f V"
                            % (e_max, m_e, lo, hi))


ORDER = ["feasible", "inconclusive", "falsified"]


def worst(vs):
    return max(vs, key=ORDER.index)


def run_cell(raw, meta, params, prov, ext):
    import json

    import numpy as np

    from nacre.pourbaix import final_run as R

    cfg = raw["R-cell"]
    T = float(cfg["temperature_K"]["value"])
    e_min = float(params.value(cfg["E_min"]["key"]))
    e_max = float(params.value(cfg["E_max"]["key"]))
    e_max_rng = params.range(cfg["E_max"]["key"])
    e_min_rng = params.range(cfg["E_min"]["key"])
    m_e_entry = params.entry(cfg["window_margin"]["key"])
    m_e = 0.0 if m_e_entry["value"] is None else float(m_e_entry["value"])
    e_form_ev = float(params.value("formation_energy_mae")) / 1000.0 / KJ_PER_MOL_PER_EV
    bks, ex = books(cfg, params, T)
    bench = json.loads((R.POURBAIX_RESULTS / "gas_reference.json").read_text(encoding="utf-8"))
    b2 = next(b for b in bench["result"]["benchmarks"] if b["id"] == "B2")

    table, phase_out = [], {}
    for phase, spec in cfg["phases"].items():
        red, note, eid = reduction(spec)
        red_d = {"status": "ok" if red.status == "finite" else "undetermined",
                 "value_V": red.value if red.status == "finite" else None, "reaction": red.reaction,
                 "reason": red.reason or "", "method": red.method, "delta_g_ev": red.delta_g_ev,
                 "delta_n_li": red.delta_n_li}
        expt_red = expt_reduction(phase, red, bks["expt"])
        red_ok = red_d["status"] == "ok"
        red_verdict = ("feasible" if red_ok and red_d["value_V"] <= e_min - m_e else
                       "falsified" if red_ok and red_d["value_V"] > e_min + m_e else "inconclusive")
        per_salt = {}
        for group, sdefs in (("registered", cfg["salts"]), ("comparator", {k: v for k, v in cfg["comparators"].items()
                                                                           if k != "note"})):
            for salt_id, salt in sdefs.items():
                by_scheme, cand_rec, margins = {}, {}, {}
                for s, bk in bks.items():
                    best, cands = oxidation(phase, spec, salt_id, salt, bk)
                    by_scheme[s] = limit_dict(best)
                    cand_rec[s] = [{"product": c.product, "status": c.status, "onset_V": c.onset_V,
                                    "reaction": c.reaction, "reason": c.reason,
                                    "species": {f: {k: v for k, v in sp.items() if k in ("coefficient", "G_eV", "kind",
                                                                                          "material_id", "scheme", "source",
                                                                                          "exchange_dH_eV")}
                                                for f, sp in c.species.items()}} for c in cands]
                    margins[s] = margin_provisional(best, e_form_ev)
                rec = {"group": group, "sink": {"kind": "solid_salt", "anion_of": salt_id, "li_source": salt["li_source"],
                                                "products": salt["products"][spec["cation"]]},
                       "oxidation_by_scheme": by_scheme, "candidates": cand_rec,
                       "provisional_m_E_V": margins}
                if group == "registered":
                    v0, why0 = f5_verdict(by_scheme, e_max, m_e, True)
                    mp_ = [m for m in margins.values() if m is not None]
                    mprov = max(mp_) if mp_ else None
                    vprov = f5_verdict(by_scheme, e_max, mprov, True) if mprov is not None else (v0, why0)
                    vals = [l["value_V"] for l in by_scheme.values() if l["value_V"] is not None]
                    rec["F5"] = {"oxidation_verdict": v0, "reason": why0, "m_E_used": m_e,
                                 "m_E_status": m_e_entry["status"],
                                 "verdict_at_provisional_m_E": {"m_E_V": mprov, "verdict": vprov[0], "reason": vprov[1]},
                                 "m_E_that_turns_a_falsification_inconclusive_V":
                                     (e_max - max(vals)) if v0 == "falsified" else None,
                                 "over_E_cell_max_range": {
                                     str(x): f5_verdict(by_scheme, float(x), m_e, True)[0]
                                     for x in (e_max_rng["min"], e_max, e_max_rng["max"])},
                                 "two_scheme_set": f5_verdict({k: v for k, v in by_scheme.items() if k != "expt"},
                                                              e_max, m_e, True)[0],
                                 "reduction_verdict": red_verdict,
                                 "verdict": worst([v0, red_verdict])}
                    if phase == "CaCO3":
                        rec["benchmark_corrected_sensitivity"] = {
                            s: (by_scheme[s]["value_V"] - b2["schemes"][s]["error_V_per_electron"]
                                if by_scheme[s]["value_V"] is not None and s in b2["schemes"] else None)
                            for s in by_scheme}
                per_salt[salt_id] = rec
        solv = {"group": "registered", "sink": {"kind": "solvated"}, "status": "undetermined",
                "reason": cfg["solvated"]["reason"], "missing_keys": [params.cite(k) for k in cfg["solvated"]["keys"]],
                "F5": {"oxidation_verdict": "inconclusive", "reason": "undetermined never passes",
                       "reduction_verdict": red_verdict, "verdict": worst(["inconclusive", red_verdict])}}
        per_salt["solvated"] = solv
        reg = {k: v for k, v in per_salt.items() if v["group"] == "registered" and k != "solvated"}
        phase_out[phase] = {"material_id": spec["material_id"], "entry_id": eid, "reduction": red_d,
                            "reduction_hull": note, "reduction_expt_crosscheck": expt_red,
                            "by_sink": per_salt,
                            "verdict_by_salt": {k: v["F5"]["verdict"] for k, v in reg.items()},
                            "verdict_any_registered_salt": worst([v["F5"]["verdict"] for v in reg.values()]),
                            "verdict_all_registered_salts": min([v["F5"]["verdict"] for v in reg.values()], key=ORDER.index)}
        for k, v in per_salt.items():
            if v["group"] == "registered" and k != "solvated":
                table.append({"phase": phase, "salt": k, **{s: v["oxidation_by_scheme"][s]["value_V"] for s in bks},
                              "verdict": v["F5"]["verdict"]})

    out_files = []
    # schema v2 documents: one per registered sink (and the solvated sink)
    for salt_id in list(cfg["salts"]) + ["solvated"]:
        windows = {}
        for phase, po in phase_out.items():
            rec = po["by_sink"][salt_id]
            if salt_id == "solvated":
                und = {"status": "undetermined", "value_V": None, "reaction": "", "reason": rec["reason"]}
                by = {s: dict(und) for s in bks}
            else:
                by = rec["oxidation_by_scheme"]
            oks = [l for l in by.values() if l["status"] == "ok"]
            main = (min(oks, key=lambda l: l["value_V"]) if len(oks) == len(by) else
                    next(l for l in by.values() if l["status"] != "ok"))
            windows[phase] = {"material_id": po["material_id"], "reduction": po["reduction"], "oxidation": main,
                              "oxidation_by_scheme": by,
                              "reduction_by_scheme": {s: po["reduction"] for s in bks if s != "expt"},
                              "notes": ["reduction does not depend on the gas scheme (no gas in lithiation)",
                                        "oxidation: lowest over the schemes; the cp2 rule F5 verdict is in "
                                        "extensions.p0-w5"]}
        kind = "solvated" if salt_id == "solvated" else "solid_salt"
        doc = {"schema_version": "2", "mock": False, "generated_utc": R.provenance.utc_now(), "provenance": prov,
               "stability": {"R-cell": {
                   "kind": "window", "reference_electrode": "Li+/Li", "temperature_K": T,
                   "convention": "theory contract E_window = Delta_G_r/(Delta_n_Li F_c); E_ox = min over Delta_n_Li > 0",
                   "sink_assumption": {"active": salt_id, "kind": kind,
                                       "statement": (cfg["solvated"]["reason"] if kind == "solvated" else
                                                     "The cation leaves as the solid salt of the anion of %s; Li from %s "
                                                     "is plated at the Li+/Li reference. A solid-salt limit is an upper "
                                                     "bound on the true onset (theory Eq. th:eq:sink, rule 3)."
                                                     % (salt_id, cfg["salts"][salt_id]["li_source"])),
                                       "switch": "one document per registered salt"},
                   "windows": windows}},
               "extensions": {"p0-w5": {**ext, "question": cfg["question"], "sink": salt_id,
                                        "F5": {ph: phase_out[ph]["by_sink"][salt_id]["F5"] for ph in phase_out}}}}
        out_files.append(R._dump(R.OUT / "cell" / ("%s.json" % salt_id), doc))

    summary = {
        "session": "P0-W5.2", "generated_utc": R.provenance.utc_now(), "provenance": prov, "extensions": ext,
        "question": cfg["question"], "scope": R.SCOPE, "temperature": cfg["temperature_K"],
        "regime_range": {"E_cell_min": {"value": e_min, "range": e_min_rng, "source": params.cite(cfg["E_min"]["key"])},
                         "E_cell_max": {"value": e_max, "range": e_max_rng, "source": params.cite(cfg["E_max"]["key"])}},
        "m_E": {"value_used": m_e, "status": m_e_entry["status"], "reason": m_e_entry.get("range_reason"),
                "provisional_recipe": margin_provisional.__doc__.strip()},
        "schemes": {s: (gasref.SCHEME_TEXT.get(s) or "all-experimental: W1 dfg keys, NIST-JANAF condensed tables, "
                        "NBS 1982 via the exchange enthalpy; CO2 and O2 at their tabulated free energies") for s in bks},
        "exchange": {k: {"li_salt": v[0], "count": v[1], "dH_eV": v[2], "locators": v[3]} for k, v in ex.items()},
        "sink_thermo_attempts": sink_attempts(params),
        "phases": phase_out, "table": table,
        "F5_rule": "cp2 ruling F5 (planning chat, 2026-10-17): every registered CO2 reference scheme is carried; a "
                   "pass must hold under the lowest-onset scheme and counts only with a solvated sink; a "
                   "falsification must hold under every registered scheme; a solid-salt falsification stands, a "
                   "solid-salt pass is inconclusive; otherwise inconclusive.",
        "aggregation_over_salts": "electrolyte_salts lists three options and none is registered as the electrolyte. "
                                  "verdict_by_salt gives each option; verdict_any_registered_salt is the worst over "
                                  "them (rule 2 of theory Eq. th:eq:sink if every option's anion is admissible) and "
                                  "verdict_all_registered_salts the best (the phase is falsified as a design only if "
                                  "every option falsifies it).",
        "limitations": [
            "The electrolyte's own anodic stability limit (oxidation of the anion or the solvent) is not assessed: "
            "above it the electrolyte reacts first, and it may lie below any limit here (theory section 9).",
            "Measured anodic onsets of Al in fluorine-free electrolytes (key al_onset_ffree) are a comparator, "
            "not an input.",
            "Reduction limits use 0 K energies; solid entropies are neglected in every scheme, the gases carry "
            "their absolute entropies (gas_reference.md quantifies that approximation).",
            "The Ca2+ and Al3+ solvation free energies relative to Li+ (keys solvation_ca_vs_li, "
            "solvation_al_vs_li) are gaps, so no solvated-sink limit exists and no pass can count."],
        "comparator_al_onset_ffree": {**params.cite("al_onset_ffree"), "value": params.value("al_onset_ffree"),
                                      "range": params.range("al_onset_ffree")},
    }
    out_files.append(R._dump(R.OUT / "cell_summary.json", summary))
    return out_files


def sink_attempts(params):
    """Log of the attempts to find thermochemistry for the sink salts missing from MP."""
    tried = []
    for formula, key in (("Al(NO3)3", "dfg_al_no3_3"), ("Ca(ClO4)2", "dfg_ca_clo4_2"),
                         ("Al(ClO4)3", "dfg_al_clo4_3"), ("AlCl3", "dfg_alcl3")):
        rec = {"formula": formula, "w1_key": params.cite(key), "w1_reason": params.entry(key).get("range_reason"),
               "materials_project": "absent from MP %s (cached element systems)" % cache.manifest()["mp_database_version"]
               if formula != "AlCl3" else "present (Li-Al-Cl system)",
               "routes": []}
        rec["routes"].append({"route": "NIST-JANAF formula index (https://janaf.nist.gov/formula.html)",
                              "result": "table Al-025, AlCl3(cr), cached" if formula == "AlCl3" else "no table"})
        rec["routes"].append({"route": "NIST Chemistry WebBook formula search", "date": "2026-10-17",
                              "result": "formula not found" if formula != "AlCl3" else "not needed"})
        rec["routes"].append({"route": "NIST data release of the NBS tables, doi:10.18434/M32124 (CSV)",
                              "date": "2026-10-17", "result": "HTTP 524 and connection resets; not retrieved"})
        nbs = {"Al(NO3)3": "only the aqueous ionized state and the 6- and 9-hydrates are tabulated (pdf p. 137); "
                           "no anhydrous solid",
               "Ca(ClO4)2": "dfH(cr) tabulated, dfG and S blank (pdf p. 276); enters through the exchange enthalpy",
               "Al(ClO4)3": "not tabulated in the Al table (pdf pp. 135-138, OCR searched)",
               "AlCl3": "dfH, dfG and S tabulated (pdf p. 136), consistent with JANAF"}[formula]
        rec["routes"].append({"route": "NBS tables 1982, scanned PDF at srd.nist.gov, OCR", "result": nbs})
        rec["status"] = {"Al(NO3)3": "undetermined", "Ca(ClO4)2": "dfH only (exchange route)",
                         "Al(ClO4)3": "undetermined", "AlCl3": "determined (JANAF, NBS, MP)"}[formula]
        tried.append(rec)
    for formula, salt in (("CaB2C8O16", "LiBOB"), ("AlB3C12O24", "LiBOB"), ("Ca(C8N5)2", "LiPCP"),
                          ("Al(C8N5)3", "LiPCP")):
        tried.append({"formula": formula, "salt": salt,
                      "materials_project": "absent from MP (systems Li-Ca-B-C-O, Li-Al-B-C-O, Li-Ca-C-N, Li-Al-C-N fetched)",
                      "routes": [{"route": "NIST-JANAF formula index", "result": "no table"},
                                 {"route": "NBS tables 1982", "result": "organic anions beyond C2 are outside the tables"}],
                      "status": "undetermined"})
    return tried
