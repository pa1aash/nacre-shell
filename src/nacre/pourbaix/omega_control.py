"""Falsifiability test fixture for the C5 R-slurry Omega test (cp3 decision 2; P0-W5.3, task C1).

Under the cp3 ruling, C5 R-slurry dissolution is judged directly from Omega_bulk with the measured
Ksp and the contract's carbonate speciation (W4 implements the evaluator); the Pourbaix diagram
stays as the competing-phase and Al-phase baseline. An Omega test must fail where it must: this
module supplies a sourced condition at which calcite dissolves (Omega < 1) and one at which it does
not, for W4's evaluator to be run on.

Every input is a lit/params.yaml key (read from the frozen snapshot) with its evidence rows; no
number is typed. No Ca2+ activity is sourced in the slurry (a_ca_slurry is a design input), so the
fixture fixes a_Ca physically instead: a slurry saturated with calcite at a sourced condition (the
low end of the unmodified slurry pH, ph_slurry range.min, at the dic_slurry central value) has
a_Ca = Ksp / a_CO3 there. Acidifying that slurry to the low end of the pH-modified slurries
(ph_slurry_modified range.min, a sourced pH reached with H3PO4, acetic acid or CO2) at the same a_Ca
and C_T removes carbonate and calcite must dissolve. Raising pH and C_T to the high ends of their
sourced ranges at the same a_Ca must give supersaturation.

The values written beside each case are this lane's ideal-solution reference (closed C(IV) system,
exact speciation), recomputed over the pK ranges and with the CaHCO3+ and CaCO3(aq) ion pairs. They
are cross-checks for W4, not the verdict: W4's evaluator applies the contract's activity model. The
expected sign holds as long as that model moves log10 Omega by less than the stated margin.

    uv run python -m nacre.pourbaix.omega_control
"""
import argparse
import itertools
import json
import math
import sys

from nacre.pourbaix import inputs, provenance
from nacre.pourbaix.final import T_K
from nacre.pourbaix.paths import POURBAIX_RESULTS, rel

OUT = POURBAIX_RESULTS / "omega_control.json"
SESSION = "P0-W5.3"


def _pick(params, key, side):
    if side == "value":
        return float(params.value(key))
    return float(params.range(key)[side.split(".")[1]])


def ref(params, key, side):
    """A fixture input: the value, the key and side it comes from, and the key's evidence rows."""
    e = params.entry(key)
    return {"value": _pick(params, key, side), "key": key, "from": side, "unit": e["unit"],
            "row_ids": list(e.get("sources") or []), "status": e.get("status")}


def carbonate_terms(ph, pk1, pk2):
    """Species of the closed C(IV) system per unit a_CO3: (H2CO3*, HCO3-, CO3 2-)."""
    return 10.0 ** (pk1 + pk2 - 2.0 * ph), 10.0 ** (pk2 - ph), 1.0


def a_co3(c_t, ph, pk1, pk2, a_ca=0.0, k_cahco3=None, k_caco3=None):
    """Free a_CO3 from C_T (mol kg^-1) at fixed free a_Ca, ideal solution, optional Ca ion pairs."""
    h2, hco3, co3 = carbonate_terms(ph, pk1, pk2)
    s = h2 + hco3 + co3
    if k_cahco3 is not None:
        s += k_cahco3 * a_ca * hco3
    if k_caco3 is not None:
        s += k_caco3 * a_ca * co3
    return c_t / s


def log10_omega(a_ca, c_t, ph, pk1, pk2, log10_ksp, **pairs):
    return math.log10(a_ca * a_co3(c_t, ph, pk1, pk2, a_ca, **pairs)) - log10_ksp


def case(params, name, ph_ref, ct_ref, a_ca_sat, expected, purpose):
    lk = float(params.value("log10_ksp_calcite"))
    k_h = 10.0 ** float(params.value("log10_k_cahco3"))
    k_0 = 10.0 ** float(params.value("log10_k_caco3_aq"))
    ph, ct = ph_ref["value"], ct_ref["value"] / 1000.0  # mol m^-3 -> mol kg^-1 (W1 dilute convention)
    pk1s = [_pick(params, "pk1_carbonic", s) for s in ("range.min", "value", "range.max")]
    pk2s = [_pick(params, "pk2_carbonic", s) for s in ("range.min", "value", "range.max")]
    central = log10_omega(a_ca_sat, ct, ph, pk1s[1], pk2s[1], lk)
    span = [log10_omega(a_ca_sat, ct, ph, a, b, lk) for a, b in itertools.product(pk1s, pk2s)]
    paired = log10_omega(a_ca_sat, ct, ph, pk1s[1], pk2s[1], lk, k_cahco3=k_h, k_caco3=k_0)
    allv = span + [paired]
    sign_ok = all(v < 0 for v in allv) if expected == "dissolves" else all(v > 0 for v in allv)
    return {
        "id": name, "purpose": purpose,
        "conditions": {"pH": ph_ref, "C_T": {**ct_ref, "value_mol_kg": ct},
                       "a_Ca": {"value": a_ca_sat, "unit": "1", "basis": "free Ca2+ activity of the calcite-saturated "
                                "reference slurry (see reference_state); not a typed number"},
                       "T_K": T_K, "phase": "calcite"},
        "expected": {"omega_test": expected, "omega_relation": "Omega < 1" if expected == "dissolves" else "Omega > 1",
                     "evaluator_must_report": ("instability (dissolution)" if expected == "dissolves" else "stability")},
        "reference_values": {
            "log10_omega_ideal_central": central,
            "log10_omega_ideal_over_pK_ranges": [min(span), max(span)],
            "log10_omega_with_ion_pairs": paired,
            "ion_pairs": ["CaHCO3+ (log10_k_cahco3)", "CaCO3(aq) (log10_k_caco3_aq)"],
            "margin_log10": min(abs(v) for v in allv),
            "sign_holds_for_all_reference_variants": sign_ok,
            "note": "ideal solution, closed C(IV) system; W4's contract activity model may shift log10 Omega; "
                    "the expectation holds while that shift is below margin_log10"},
    }


def build(params):
    pk1, pk2 = float(params.value("pk1_carbonic")), float(params.value("pk2_carbonic"))
    lk = float(params.value("log10_ksp_calcite"))
    ph_sat = ref(params, "ph_slurry", "range.min")
    ct_sat = ref(params, "dic_slurry", "value")
    a_co3_sat = a_co3(ct_sat["value"] / 1000.0, ph_sat["value"], pk1, pk2)
    a_ca_sat = 10.0 ** lk / a_co3_sat
    cases = [
        case(params, "calcite_dissolves_after_acidification", ref(params, "ph_slurry_modified", "range.min"), ct_sat,
             a_ca_sat, "dissolves",
             "the falsifiability control: the Omega test must report calcite unstable here (C5, Phase 7 item 21)"),
        case(params, "calcite_supersaturated_alkaline_high_dic", ref(params, "ph_slurry", "range.max"),
             ref(params, "dic_slurry", "range.max"), a_ca_sat, "precipitates",
             "the companion control: the Omega test must report calcite stable here"),
    ]
    return {
        "session": SESSION, "generated_utc": provenance.utc_now(), "kind": "omega-test-fixture",
        "params_sha": params.sha, "params_snapshot": rel(inputs.snapshot_path(params.sha)),
        "question": "Does the C5 R-slurry Omega test (measured Ksp, contract carbonate speciation) report calcite "
                    "unstable at a sourced condition where it dissolves, and stable where it is supersaturated? "
                    "(thermodynamic proxy; no rates)",
        "for": "lane p0-w4, the C5 R-slurry Omega evaluator (cp3 decision 2)",
        "reference_state": {
            "statement": "a slurry saturated with calcite (Omega = 1) at the low end of the unmodified slurry pH and "
                         "the central dissolved carbonate; it fixes the free Ca2+ activity carried into both cases",
            "pH": ph_sat, "C_T": {**ct_sat, "value_mol_kg": ct_sat["value"] / 1000.0},
            "log10_ksp_calcite": ref(params, "log10_ksp_calcite", "value"),
            "pk1_carbonic": ref(params, "pk1_carbonic", "value"), "pk2_carbonic": ref(params, "pk2_carbonic", "value"),
            "a_CO3_ideal": a_co3_sat, "a_Ca_saturated": a_ca_sat},
        "ion_pair_keys": [ref(params, "log10_k_cahco3", "value"), ref(params, "log10_k_caco3_aq", "value")],
        "cases": cases,
        "scope": "Thermodynamic proxies only: Omega says whether calcite is at or above equilibrium, never how fast "
                 "it dissolves.",
    }


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.omega_control")
    ap.add_argument("--params-sha", default="680a44b2efdb94694b25f5317ddc3d73db2f117c")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    params = inputs.Params(inputs.load_snapshot(args.params_sha))
    doc = build(params)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    for c in doc["cases"]:
        r = c["reference_values"]
        print("%-44s %-11s log10 Omega %.2f (margin %.2f, sign holds %s)" % (
            c["id"], c["expected"]["omega_test"], r["log10_omega_ideal_central"], r["margin_log10"],
            r["sign_holds_for_all_reference_variants"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
