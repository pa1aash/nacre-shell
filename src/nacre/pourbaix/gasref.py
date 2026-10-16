"""Gas-reference benchmark (P0-W5.2 task A): how well each CO2/O2 reference scheme reproduces
experimental reaction free energies of carbonates that release gaseous CO2 or O2.

Thermodynamic question: when MP solid energies are combined with a gas reference to give the
free energy of a reaction that releases CO2 (and O2), how far is the result from the measured
reaction free energy at 298.15 K and 1 bar? The answer sizes the error that each scheme carries
into the R-cell oxidation limits of CaCO3, where the same combination appears.

Every scheme shares the window code's conventions (window.EnergyBook): a solid enters at its MP
formation energy (0 K, MP2020 corrections, entropy neglected); a gas at dfH - T S + k T ln p
with S(T) from NIST-JANAF; O2 with dfH = 0 because the MP2020 oxide correction is fitted against
the computed O2 reference. The schemes differ only in the CO2 enthalpy:

- `janaf`: dfH(CO2) from NIST-JANAF table C-095;
- `mp`: dfH(CO2) from the MP CO2 molecular solid (sublimation not included).

No scheme is chosen here: every scheme is carried into the window, and the verdict rule (cp2
ruling F5) decides how they combine. The diagnostic `entropy_approximation` evaluates each
reaction with experimental enthalpies under the same entropy approximation (solid entropies
neglected), separating that approximation from the DFT enthalpy error.

Experimental references, all fetched: W1's keys and rows in lit/params.yaml at the pinned sha
(drg_caco3_decomposition from rows TI-010 and TI-051, the formation keys from TI-002, TI-006,
TI-008) and NIST-JANAF condensed-phase tables for Li2CO3, Li2O, Na2CO3 and Na2O.
"""
import json
import math

from scipy import constants

from nacre.pourbaix import cache, provenance
from nacre.pourbaix import gas as gasmod
from nacre.pourbaix import window as w
from nacre.pourbaix.entries import KJ_PER_MOL_PER_EV, entry_key
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

T_BENCH = 298.15
P_BAR = 1.0
F_KJ_PER_V = constants.e * constants.N_A / 1000.0  # kJ mol^-1 per V per electron

SCHEMES = {
    "janaf": {"O2": {"pressure_bar": P_BAR, "enthalpy_scheme": "mp_fitted_reference"},
              "CO2": {"pressure_bar": P_BAR, "enthalpy_scheme": "janaf"}},
    "mp": {"O2": {"pressure_bar": P_BAR, "enthalpy_scheme": "mp_fitted_reference"},
           "CO2": {"pressure_bar": P_BAR, "enthalpy_scheme": "mp"}},
}
SCHEME_TEXT = {
    "janaf": "CO2 dfH from NIST-JANAF C-095; O2 dfH = 0 (MP2020-fitted reference); gas S(T) from JANAF; "
             "solids at MP formation energies, entropy neglected",
    "mp": "CO2 dfH from the MP CO2 molecular solid (no sublimation); O2 dfH = 0; gas S(T) from JANAF; "
          "solids at MP formation energies, entropy neglected",
}

# Benchmark reactions: reactants and products (formula: coefficient), electrons transferred
# per formula unit of the carbonate (0 for a chemical decomposition) and the experimental
# reference. kind "params" reads lit/params.yaml keys; kind "janaf" reads dfG from tables.
BENCHMARKS = [
    {"id": "B1", "reaction": {"CaCO3": -1, "CaO": 1, "CO2": 1}, "n_e": 0,
     "role": "primary: the CO2 reference in a carbonate decomposition (prompt task A)",
     "expt": {"kind": "params", "key": "drg_caco3_decomposition",
              "rows": [("TI-010", 1), ("TI-051", -1)], "dh_key": "drh_caco3_decomposition"}},
    {"id": "B2", "reaction": {"CaCO3": -1, "Ca": 1, "CO2": 1, "O2": 0.5}, "n_e": 2,
     "role": "the redox core of every CaCO3 oxidation limit: carbonate to CO2 + 1/2 O2, cation as metal",
     "expt": {"kind": "params_sum", "terms": [("dfg_co2_g", 1), ("dfg_caco3_calcite", -1)]}},
    {"id": "B3", "reaction": {"CaCO3": -1, "Ca": 1, "C": 1, "O2": 1.5}, "n_e": 0,
     "role": "the O2 reference and carbon in the carbonate (minus the formation energy of calcite)",
     "expt": {"kind": "params_sum", "terms": [("dfg_caco3_calcite", -1)]}},
    {"id": "B4", "reaction": {"CaO": -1, "Ca": 1, "O2": 0.5}, "n_e": 0,
     "role": "the O2 reference in an oxide (minus the formation energy of lime)",
     "expt": {"kind": "params_sum", "terms": [("dfg_cao", -1)]}},
    {"id": "B5", "reaction": {"Li2CO3": -1, "Li2O": 1, "CO2": 1}, "n_e": 0,
     "role": "the CO2 reference in a second carbonate decomposition",
     "expt": {"kind": "janaf", "species": {"Li2CO3": -1, "Li2O": 1, "CO2": 1}}},
    {"id": "B6", "reaction": {"Li2CO3": -1, "Li": 2, "CO2": 1, "O2": 0.5}, "n_e": 2,
     "role": "a carbonate oxidation to CO2 + 1/2 O2 referenced to Li metal: the window reaction type",
     "expt": {"kind": "janaf", "species": {"Li2CO3": -1, "CO2": 1}},
     "comparator": {"key": "li2co3_oxidation_onset",
                    "note": "measured onset of CO2 evolution (kinetic, includes an overpotential); "
                            "an upper bound on the thermodynamic potential, not its value"}},
    {"id": "B7", "reaction": {"Na2CO3": -1, "Na2O": 1, "CO2": 1}, "n_e": 0,
     "role": "the CO2 reference in a third carbonate decomposition",
     "expt": {"kind": "janaf", "species": {"Na2CO3": -1, "Na2O": 1, "CO2": 1}}},
]
GASES = ("O2", "CO2")
UNIT_J = {"kJ/mol": 1000.0, "J/mol": 1.0, "J mol^-1": 1.0, "kJ mol^-1": 1000.0}


def pooled_entries(cache_dir=cache.CACHE_DIR):
    """Every cached MP entry (cell systems and the slurry system), one per entry id."""
    seen, out = set(), []
    names = sorted(cache.files_of_kind("mp_entries", cache_dir))
    for name in names:
        for e in cache.load_entries(name, cache_dir):
            k = entry_key(e)
            if k not in seen:
                seen.add(k)
                out.append(e)
    return out


def book(scheme, T=T_BENCH, entries=None, cache_dir=cache.CACHE_DIR, pinned=None):
    return w.EnergyBook(entries if entries is not None else pooled_entries(cache_dir), T,
                        SCHEMES[scheme], cache_dir, pinned=pinned)


def _element_ref(formula):
    return formula in ("Ca", "Li", "Na", "C", "Al")


def species_energy(bk, formula):
    """Free energy (eV per formula unit) of a species under a book; elements are 0."""
    if _element_ref(formula):
        return 0.0, {"kind": "element", "basis": "reference element, formation energy 0"}
    return bk(formula)


def reaction_energy(bk, reaction):
    """Sum of nu * G over the reaction (eV per formula unit of the first reactant) and species data."""
    total, species = 0.0, {}
    for f, nu in reaction.items():
        g, meta = species_energy(bk, f)
        total += nu * g
        species[f] = {"coefficient": nu, "G_eV": g, **{k: v for k, v in meta.items() if k != "locator"}}
    return total, species


def _row_j(row):
    unit = row["unit"].replace(" ", "")
    if unit not in {u.replace(" ", "") for u in UNIT_J}:
        raise ValueError("unexpected unit %r in row %s" % (row["unit"], row["row_id"]))
    factor = {u.replace(" ", ""): f for u, f in UNIT_J.items()}[unit]
    return float(row["value"]) * factor


def experimental(bench, params, T=T_BENCH, cache_dir=cache.CACHE_DIR):
    """Experimental reaction free energy (J mol^-1) with its sources, and dH where available."""
    ex = bench["expt"]
    if ex["kind"] == "params":
        unit = params.unit(ex["key"])
        if unit != "J mol^-1":
            raise ValueError("%s: unit %s" % (ex["key"], unit))
        rows = [{"row_id": rid, "value_J_per_mol": sign * _row_j(params.row(rid)),
                 "doi": params.row(rid)["doi"], "locator": params.row(rid)["locator"],
                 "grade": params.row(rid)["grade"], "sign_applied": sign}
                for rid, sign in ex["rows"]]
        out = {"value_J_per_mol": float(params.value(ex["key"])), "range_J_per_mol": params.range(ex["key"]),
               "source": params.cite(ex["key"]), "rows": rows}
        if ex.get("dh_key"):
            out["dH_J_per_mol"] = float(params.value(ex["dh_key"]))
            out["dH_source"] = params.cite(ex["dh_key"])
        return out
    if ex["kind"] == "params_sum":
        val = 0.0
        srcs = []
        for key, sign in ex["terms"]:
            if params.unit(key) != "J mol^-1":
                raise ValueError("%s: unit %s" % (key, params.unit(key)))
            val += sign * float(params.value(key))
            srcs.append({**params.cite(key), "sign": sign})
        return {"value_J_per_mol": val, "source": srcs}
    if ex["kind"] == "janaf":
        dg = dh = 0.0
        srcs = []
        for f, nu in ex["species"].items():
            r = gasmod.row_kj(f, T, cache_dir)
            dg += nu * r["dfG_kJ_per_mol"] * 1000.0
            dh += nu * r["dfH_kJ_per_mol"] * 1000.0
            srcs.append({"species": f, "coefficient": nu, "table": r["table"],
                         "dfG_kJ_per_mol": r["dfG_kJ_per_mol"], "dfH_kJ_per_mol": r["dfH_kJ_per_mol"]})
        return {"value_J_per_mol": dg, "dH_J_per_mol": dh,
                "source": {"tables": srcs, "citation": "NIST-JANAF Thermochemical Tables "
                           "(Chase 1998, Monograph 9), doi:10.18434/T42S31", "T_K": T}}
    raise ValueError(ex["kind"])


def entropy_approximation(bench, expt, T=T_BENCH, cache_dir=cache.CACHE_DIR):
    """Experimental dH minus T times the gas entropies only (the schemes' entropy convention),
    minus the experimental dG: the error of the approximation alone (J mol^-1), or None."""
    if "dH_J_per_mol" not in expt:
        return None
    ts = 0.0
    for g in GASES:
        nu = bench["reaction"].get(g, 0.0)
        if nu:
            ts += nu * T * gasmod.row_kj(g, T, cache_dir)["S_J_per_K_mol"]
    approx = expt["dH_J_per_mol"] - ts
    return {"value_J_per_mol": approx, "error_J_per_mol": approx - expt["value_J_per_mol"]}


def run_benchmark(params, T=T_BENCH, cache_dir=cache.CACHE_DIR):
    entries = pooled_entries(cache_dir)
    books = {s: book(s, T, entries, cache_dir) for s in SCHEMES}
    out = []
    for b in BENCHMARKS:
        expt = experimental(b, params, T, cache_dir)
        rec = {"id": b["id"], "role": b["role"], "reaction": b["reaction"], "n_e": b["n_e"],
               "experiment": expt, "entropy_approximation": entropy_approximation(b, expt, T, cache_dir),
               "schemes": {}}
        for s, bk in books.items():
            dg_ev, species = reaction_energy(bk, b["reaction"])
            dg_j = dg_ev * KJ_PER_MOL_PER_EV * 1000.0
            err = dg_j - expt["value_J_per_mol"]
            rec["schemes"][s] = {"dG_J_per_mol": dg_j, "dG_eV": dg_ev, "error_J_per_mol": err,
                                 "error_V_per_electron": (err / 1000.0 / (b["n_e"] * F_KJ_PER_V)
                                                          if b["n_e"] else None),
                                 "species": species}
        if b.get("comparator"):
            c = b["comparator"]
            rec["comparator"] = {**params.cite(c["key"]), "value": params.value(c["key"]),
                                 "unit": params.unit(c["key"]), "range": params.range(c["key"]),
                                 "note": c["note"],
                                 "experimental_equilibrium_V": expt["value_J_per_mol"] / 1000.0
                                 / (b["n_e"] * F_KJ_PER_V)}
        out.append(rec)
    summary = {}
    for s in SCHEMES:
        errs = [r["schemes"][s]["error_J_per_mol"] for r in out]
        co2 = [r["schemes"][s]["error_J_per_mol"] for r in out if "CO2" in r["reaction"]]
        summary[s] = {"mean_abs_error_J_per_mol": sum(abs(e) for e in errs) / len(errs),
                      "mean_abs_error_CO2_reactions_J_per_mol": sum(abs(e) for e in co2) / len(co2),
                      "B1_error_J_per_mol": next(r for r in out if r["id"] == "B1")["schemes"][s]["error_J_per_mol"],
                      "B2_error_V_per_electron": next(r for r in out if r["id"] == "B2")["schemes"][s]["error_V_per_electron"],
                      "description": SCHEME_TEXT[s]}
    return {"temperature_K": T, "pressure_bar": P_BAR, "benchmarks": out, "summary": summary}


def _kj(x):
    return "%.1f" % (x / 1000.0)


def _formula(reaction):
    lhs = " + ".join(("%g %s" % (-v, f)).replace("1 ", "", 1) if -v != 1 else f
                     for f, v in reaction.items() if v < 0)
    rhs = " + ".join(("%g %s" % (v, f)) if v != 1 else f for f, v in reaction.items() if v > 0)
    return "%s -> %s" % (lhs, rhs)


def markdown(result, prov, params):
    s_names = list(SCHEMES)
    lines = [
        "# Gas-reference benchmark (P0-W5.2, task A)",
        "",
        "Generated by `uv run python -m nacre.pourbaix.gasref` from the offline cache and lit/params.yaml at",
        "`%s` (snapshot `results/preprint/pourbaix/inputs/params_%s.json`). Git %s, cache %s." % (
            params.sha, params.sha[:7], prov["git_sha"][:12], prov["cache_hash"][:19]),
        "",
        "**Thermodynamic question.** When MP solid formation energies are combined with a gas reference to give",
        "the free energy of a reaction that releases CO2 (and O2), how far is the result from the measured",
        "reaction free energy at 298.15 K and 1 bar? The R-cell oxidation limits of CaCO3 combine the same",
        "terms, so the error of each scheme here is the error it carries into those limits. This is a",
        "thermochemical benchmark; it says nothing about rates.",
        "",
        "**Schemes (all carried; none is chosen).**",
        "",
    ]
    for s in s_names:
        lines.append("- `%s`: %s." % (s, SCHEME_TEXT[s]))
    lines += ["", "**Errors** (computed minus experiment, kJ mol^-1 per formula unit of the carbonate or oxide;",
              "for the redox reactions B2 and B6 also V per electron).", "",
              "| Id | Reaction | Experiment | Source | " + " | ".join("`%s` error" % s for s in s_names)
              + " | Entropy approximation alone |",
              "|---|---|---|---|" + "---|" * len(s_names) + "---|"]
    for r in result["benchmarks"]:
        ex = r["experiment"]
        if isinstance(ex["source"], dict) and "key" in ex["source"]:
            src = "`%s` (%s)" % (ex["source"]["key"], ", ".join(ex["source"]["sources"]))
        elif isinstance(ex["source"], list):
            src = "; ".join("`%s` (%s)" % (c["key"], ", ".join(c["sources"])) for c in ex["source"])
        else:
            src = "JANAF " + ", ".join(t["table"].rsplit("/", 1)[-1].replace(".txt", "")
                                       for t in ex["source"]["tables"])
        errs = []
        for s in s_names:
            sc = r["schemes"][s]
            e = _kj(sc["error_J_per_mol"])
            if sc["error_V_per_electron"] is not None:
                e += " (%.3f V)" % sc["error_V_per_electron"]
            errs.append(e)
        ea = r["entropy_approximation"]
        lines.append("| %s | %s | %s | %s | %s | %s |" % (
            r["id"], _formula(r["reaction"]), _kj(ex["value_J_per_mol"]), src, " | ".join(errs),
            _kj(ea["error_J_per_mol"]) if ea else "n/a (no experimental dH)"))
    lines += ["", "**Per-scheme summary.**", "",
              "| Scheme | Mean abs. error, all (kJ/mol) | Mean abs. error, CO2-releasing (kJ/mol) | B1 error (kJ/mol) | B2 error (V per electron) |",
              "|---|---|---|---|---|"]
    for s in s_names:
        sm = result["summary"][s]
        lines.append("| `%s` | %s | %s | %s | %.3f |" % (s, _kj(sm["mean_abs_error_J_per_mol"]),
                                                       _kj(sm["mean_abs_error_CO2_reactions_J_per_mol"]),
                                                       _kj(sm["B1_error_J_per_mol"]), sm["B2_error_V_per_electron"]))
    b1 = next(r for r in result["benchmarks"] if r["id"] == "B1")
    lines += ["", "**B1 rows** (W1 key `drg_caco3_decomposition`, range %s to %s kJ/mol):" % (
        _kj(b1["experiment"]["range_J_per_mol"]["min"]), _kj(b1["experiment"]["range_J_per_mol"]["max"])), ""]
    for row in b1["experiment"]["rows"]:
        lines.append("- %s: %s kJ/mol (doi:%s, %s, grade %s%s)." % (
            row["row_id"], _kj(row["value_J_per_mol"]), row["doi"], row["locator"], row["grade"],
            ", sign reversed: the row is the formation from the oxides" if row["sign_applied"] < 0 else ""))
    b6 = next(r for r in result["benchmarks"] if r["id"] == "B6")
    c = b6["comparator"]
    lines += ["", "**B6 comparator.** The experimental equilibrium potential of Li2CO3 -> 2 Li + CO2 + 1/2 O2 from",
              "the JANAF free energies is %.3f V vs Li+/Li. W1's measured onset of CO2 evolution (`%s`, %s) is %s V" % (
                  c["experimental_equilibrium_V"], c["key"], ", ".join(c["sources"]), c["value"]),
              "(range %s to %s V); %s." % (c["range"]["min"], c["range"]["max"], c["note"]),
              "",
              "**Reading.**",
              "",
              "- The entropy approximation shared by both schemes (solid entropies neglected, the gas carrying its",
              "  absolute entropy) is itself a systematic error, listed per reaction in the last column.",
              "- The two schemes bracket the experiment for the reactions that release CO2: one overestimates and",
              "  the other underestimates the decomposition and oxidation free energies (signs in the table). The",
              "  window therefore evaluates every limit under both schemes; under the cp2 rule F5 a pass must",
              "  hold under the lowest-onset scheme and a falsification under every scheme.",
              "- B2 is the redox core of every CaCO3 oxidation limit: its error in V per electron is the shift each",
              "  scheme carries into the CaCO3 onset, before any sink-specific error.",
              "- B3 and B4 locate the error. Against experiment the MP formation energy of calcite is too negative",
              "  by the B3 error, whereas that of lime (B4) is close: the carbonate anion carries the error (MP2020",
              "  fits no carbonate or CO2 correction, row TI-084). The `janaf` scheme pairs that over-bound",
              "  carbonate with an exact CO2 enthalpy and overestimates; the `mp` scheme pairs it with a DFT CO2",
              "  that shares part of the error (and lacks sublimation) and underestimates.",
              "- The window also carries an all-experimental route, `expt`, for every reaction whose species are",
              "  all tabulated in fetched sources (W1 keys, NIST-JANAF, the NBS tables). Its error on these",
              "  benchmarks is the spread between the fetched evaluations themselves (B1: the two rows above).",
              "",
              "Machine-readable result: `results/preprint/pourbaix/gas_reference.json`.", ""]
    return "\n".join(lines)


def main(argv=None):
    import argparse

    from nacre.pourbaix import inputs

    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.gasref")
    ap.add_argument("--params-sha", required=True)
    args = ap.parse_args(argv)
    if cache.verify():
        raise SystemExit("cache check failed")
    params = inputs.Params(inputs.load_snapshot(args.params_sha))
    result = run_benchmark(params)
    prov = {"git_sha": provenance.git_sha(), "git_dirty": provenance.git_dirty(),
            "cache_hash": cache.cache_hash(), "params_sha": params.sha,
            "params_snapshot": inputs.snapshot_path(params.sha).relative_to(REPO).as_posix(),
            "mp_database_version": cache.manifest()["mp_database_version"],
            "library_versions": provenance.lib_versions()}
    doc = {"session": "P0-W5.2", "generated_utc": provenance.utc_now(), "provenance": prov,
           "question": "error of each CO2/O2 reference scheme against experimental reaction free "
                       "energies of carbonates releasing CO2 or O2 (298.15 K, 1 bar)",
           "result": result}
    jpath = POURBAIX_RESULTS / "gas_reference.json"
    mpath = POURBAIX_RESULTS / "gas_reference.md"
    jpath.write_text(json.dumps(doc, indent=1, sort_keys=True, default=float) + "\n", encoding="utf-8")
    mpath.write_text(markdown(result, prov, params), encoding="utf-8")
    record = {"session": "P0-W5.2", "run": "gas_reference", "kind": "benchmark", "mock": False,
              "utc": doc["generated_utc"], "git_sha": prov["git_sha"], "git_dirty": prov["git_dirty"],
              "cache_hash": prov["cache_hash"], "params_sha": params.sha,
              "outputs": [{"path": p.relative_to(REPO).as_posix(), "sha256": provenance.sha256_file(p)}
                          for p in (jpath, mpath)]}
    provenance.ledger_append(REPO / "jobs" / "ledger" / "p0-w5.jsonl", record)
    for s, sm in result["summary"].items():
        print("%-6s B1 error %+.1f kJ/mol, B2 %+.3f V/e, MAE(CO2) %.1f kJ/mol" % (
            s, sm["B1_error_J_per_mol"] / 1000, sm["B2_error_V_per_electron"],
            sm["mean_abs_error_CO2_reactions_J_per_mol"] / 1000))
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
