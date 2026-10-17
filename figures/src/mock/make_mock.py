"""Generate the mock inputs of the data figures, in the owners' shapes.

MOCK DATA. Every number here is synthetic, chosen only to exercise the templates; none is a
result, a literature value or a parameter of the study. Each file carries "mock": true, and the
figure builder writes figures built from it only to figures/out/mock/.

  retro_results.json   retro-results/v1 (lane p0-w2, SCHEMA.md section 5)       -> fig4
  screen_summary.json  results schema v2, screen regimes (lane p0-w4)            -> fig5, fig6
  stability.json       results schema v2, stability section C5 (p0-w4, p0-w5)    -> fig7
  params.yaml          mock rows in the layout of lit/params.yaml (lane p0-w1)    -> fig5, fig7

Case ids, labels, terminations and observed relations of the retrodiction mock are read from
the pinned cases.yaml so that the template is exercised on the real case list; the barriers
and verdicts are synthetic. The nucleation quantities use the contract's functions
(nacre.physics) on synthetic draws, so the mock quantiles are mutually consistent.

Run: uv run python figures/src/mock/make_mock.py
"""
import json
from math import comb
from pathlib import Path

import numpy as np
import yaml

from nacre.figs import upstream
from nacre.physics import wetting

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = 20261017
NOTE = "MOCK: synthetic values to exercise the template; not a result"
STAMP = "2026-10-17T00:00:00Z"
ZERO40 = "0" * 40
ZSHA = "sha256:" + "0" * 64
QUANTILES = (0.005, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975, 0.995)


def _r(x, n=6):
    return float("%.*g" % (n, float(x)))


def _write_json(name, doc):
    (HERE / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


# ----------------------------------------------------------------------------------- fig 4

def _verdict(relation, q05, q95):
    """criterion.md section 2."""
    if q05 <= 0.0 <= q95:
        return "inconclusive"
    agrees = q05 > 0 if relation == "test_higher_barrier" else q95 < 0
    return "correct" if agrees else "incorrect"


def retro_results(rng):
    cases_doc = upstream.load("retro_cases", ROOT)
    usable = [c for c in cases_doc["cases"] if c["status"] == "usable"]
    # Synthetic centre/width pairs (k_B T) chosen to give every verdict at least once.
    plan = [(28, 10), (15, 9), (40, 30), (6, 9), (-12, 7), (55, 20), (3, 2), (19, 11), (-2, 6), (75, 40),
            (9, 12), (31, 14)]
    out = []
    for c, (mid, half) in zip(usable, plan):
        mid = mid * float(np.exp(rng.normal(0.0, 0.05)))
        q05, q95 = mid - half, mid + half * float(rng.uniform(0.9, 1.4))
        ref_med = float(rng.uniform(20, 80))
        rel = c["outcome"]["relation"]
        out.append({
            "id": c["id"],
            "label": "%s vs %s" % (c["test"]["label"], c["reference"]["label"]),
            "termination": c["termination"],
            "negative": bool(c["negative"]),
            "observed_relation": rel,
            "barrier_test": {"median": _r(ref_med + mid), "q05": _r(ref_med + q05), "q95": _r(ref_med + q95)},
            "barrier_reference": {"median": _r(ref_med), "q05": _r(ref_med * 0.7), "q95": _r(ref_med * 1.3)},
            "delta": {"median": _r(mid), "q05": _r(q05), "q95": _r(q95)},
            "p_test_higher": _r(min(1.0, max(0.0, 0.5 + mid / (2 * (abs(mid) + half))))),
            "boundary_mass": _r(rng.uniform(0.0, 0.08)),
            "verdict": _verdict(rel, q05, q95),
        })
    n = len(out)
    k = next(k for k in range(n + 1) if sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n <= 0.05)
    tally = {v: sum(1 for c in out if c["verdict"] == v) for v in ("correct", "incorrect", "inconclusive")}
    return {
        "schema": "retro-results/v1", "mock": True,
        "cases_sha256": "sha256:" + upstream.entry("retro_cases", ROOT)["sha256"],
        "criterion_sha256": ZSHA, "fixed_before_run_commit": ZERO40,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "contract_sha": ZERO40, "params_file_hash": ZSHA},
        "draws": 20000, "seed": 0, "cases": out,
        "summary": {"N": n, **tally, "k": k,
                    "chance_probability": _r(sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n),
                    "pass": tally["correct"] >= k},
    }


# ------------------------------------------------------------------------------ fig 5, 6

def _quantity(symbol, units, x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return {"symbol": symbol, "units": units, "n_valid": int(x.size), "mean": _r(x.mean()), "sd": _r(x.std()),
            "quantiles": {("%g" % q): _r(np.quantile(x, q)) for q in QUANTILES}}


def _nucleate(rng, n, omega_lo, omega_hi, a_med, b_acc_med):
    omega = np.exp(rng.uniform(np.log(omega_lo), np.log(omega_hi), n))
    cos_raw = rng.normal(0.35, 0.45, n)
    clipped_0, clipped_180 = int((cos_raw > 1).sum()), int((cos_raw < -1).sum())
    cos_t = np.clip(cos_raw, -1.0, 1.0)
    f = wetting.shape_factor_from_cos(cos_t)
    a = a_med * np.exp(rng.normal(0.0, 0.5, n))  # synthetic prefactor of 1/ln^2(Omega)
    hom = a / np.log(omega) ** 2
    het = f * hom
    b_acc = rng.normal(b_acc_med, 3.0, n)
    q = {
        "Omega_bulk": _quantity("Omega_bulk", "1", omega),
        "cos_theta": _quantity("cos(theta) (clipped to [-1, 1])", "1", cos_t),
        "f_theta": _quantity("f(theta)", "1", f),
        "barrier_hom_bulk_kT": _quantity("Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", hom),
        "barrier_het_template_kT": _quantity("f(theta) Delta_G*_hom(Omega_bulk) / k_B T", "k_B T", het),
        "B_acc_kT": _quantity("B_acc / k_B T", "k_B T", b_acc),
    }
    finite = n - clipped_0 - clipped_180
    mass = {"n_finite": finite, "n_clipped_theta_0": clipped_0, "n_clipped_theta_180": clipped_180,
            "fraction_theta_0": _r(clipped_0 / n), "fraction_theta_180": _r(clipped_180 / n),
            "fraction_total": _r((clipped_0 + clipped_180) / n)}
    return q, {"cos_theta": mass}


def _ci(est, half):
    return {"estimate": _r(est), "ci_low": _r(est - half), "ci_high": _r(est + half)}


def screen_summary(rng):
    params = ["gamma_nl", "gamma_sl0", "gamma_sn0", "Delta_gamma_w", "Delta_G_site", "V_m", "a_Ca", "T"]
    weights = np.array([0.38, 0.21, 0.17, 0.09, 0.06, 0.05, 0.03, 0.01])
    q_slurry, m_slurry = _nucleate(rng, 40000, 3.0, 60.0, 900.0, 62.0)
    q_dry, m_dry = _nucleate(rng, 40000, 8.0, 300.0, 820.0, 66.0)
    sobol, shapley = {}, {}
    for p, w in zip(params, weights):
        s1 = w * rng.uniform(0.75, 0.95)
        st = min(1.0, w * rng.uniform(1.05, 1.35))
        sobol[p] = {"first_order": _ci(s1, rng.uniform(0.004, 0.01)), "total_order": _ci(st, rng.uniform(0.004, 0.012))}
        shapley[p] = _ci(w, rng.uniform(0.005, 0.015))
    quantity = "barrier_het_template_kT"
    precision = {}
    statuses = ["ok", "ok", "ok", "ok", "already_clears", "ok", "unreachable", "already_clears"]
    for p, w, st in zip(params, weights, statuses):
        prior = float(rng.uniform(0.2, 1.0))
        req = None if st == "unreachable" else (prior if st == "already_clears" else prior * float(0.6 * np.sqrt(w)))
        precision[p] = {"status": st, "units": "mock", "prior_width": _r(prior),
                        "required_width": None if req is None else _r(req),
                        "width_ratio": None if req is None else _r(req / prior),
                        "nearest_threshold": "C3a", "method": "mock"}
    regime = {
        "draws": 40000, "seed": SEED,
        "sobol_design": {"method": "mock", "base_samples": 4096, "evaluations": 4096 * (len(params) + 2),
                         "bootstrap_resamples": 0, "confidence_level": 0.95},
        "parameters": params,
        "links": {"nucleate": {
            "quantities": q_slurry,
            "sobol": {quantity: sobol},
            "threshold_evaluation": None,
            "shapley": {quantity: shapley},
            "sensitivity_scale": {quantity: "log10", "Omega_bulk": "log10"},
        }},
        "boundary_mass": {"nucleate": m_slurry},
        "dependence": {"method": "gaussian_copula",
                       "rank_correlations": [{"a": "gamma_sl0", "b": "gamma_sn0", "spearman_rho": 0.5,
                                              "source": "mock"}]},
        "primary_state": "slurry",
        "states": {"drying": {"quantities": {"nucleate": q_dry}, "boundary_mass": {"nucleate": m_dry}}},
    }
    return {
        "schema_version": "2", "mock": True, "generated_utc": STAMP,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "config_hash": ZSHA,
                       "prior_file": "figures/src/mock/params.yaml", "prior_file_hash": ZSHA,
                       "contract_sha": None, "params_sha": None, "thresholds_file": None, "thresholds_hash": None,
                       "thresholds_source_sha": None, "schema_sha": upstream.entry("results_schema", ROOT)["commit"]},
        "regimes": {"R-slurry": regime},
        "required_precision": {"R-slurry": precision},
        "extensions": {"p0-w6": {"note": NOTE}},
    }


# ----------------------------------------------------------------------------------- fig 7

_PHASES = [
    # (label, kind, [(species, kind)])
    ("Al(OH)4[-] + Ca[2+] + HCO3[-]", "aqueous", [("Al(OH)4[-]", "aqueous"), ("Ca[2+]", "aqueous"), ("HCO3[-]", "aqueous")]),
    ("Al2O3(s) + CaCO3(s)", "solid", [("Al2O3", "solid"), ("CaCO3", "solid")]),
    ("Al(OH)4[-] + CaCO3(s)", "mixed", [("Al(OH)4[-]", "aqueous"), ("CaCO3", "solid")]),
    ("Al2O3(s) + Ca[2+] + CO2(aq)", "mixed", [("Al2O3", "solid"), ("Ca[2+]", "aqueous"), ("CO2(aq)", "aqueous")]),
    ("Al(s) + CaH2(s) + CH4(aq)", "mixed", [("Al", "solid"), ("CaH2", "solid"), ("CH4(aq)", "aqueous")]),
    ("Al[3+] + Ca[2+] + CO2(aq)", "aqueous", [("Al[3+]", "aqueous"), ("Ca[2+]", "aqueous"), ("CO2(aq)", "aqueous")]),
]


def _grid(ph, e, shift):
    """Synthetic domain map: straight boundaries in (pH, E), indexed [i][j] at E[i], pH[j]."""
    idx = np.empty((len(e), len(ph)), dtype=int)
    for i, ev in enumerate(e):
        for j, p in enumerate(ph):
            red = ev < -1.75 - 0.06 * p
            if red:
                idx[i, j] = 4
            elif p < 4.0 + shift:
                idx[i, j] = 5 if p < 3.0 + shift else 3
            elif p < 7.8 + shift:
                idx[i, j] = 1
            elif p < 11.2 + shift:
                idx[i, j] = 2
            else:
                idx[i, j] = 0
    return idx


def _state(ph, e, shift, a_ca, a_co3, rng):
    idx = _grid(ph, e, shift)
    phases = [{"index": k, "label": lab, "kind": kind,
               "components": [{"species": s, "kind": sk, "material_id": None} for s, sk in comps]}
              for k, (lab, kind, comps) in enumerate(_PHASES)]
    dec = {}
    for name, formula in (("calcite", "CaCO3"), ("corundum", "Al2O3")):
        g = np.abs(rng.normal(0.0, 0.05, idx.shape)) + 0.02 * (idx != 1)
        dec[name] = {"units": "eV/atom", "material_id": None, "formula": formula,
                     "grid": [[_r(v, 4) for v in row] for row in g]}
    return {"conditions": {"a_Ca": a_ca, "a_CO3": a_co3, "note": NOTE},
            "phases": phases, "domains": {"index_grid": idx.tolist()}, "decomposition_energy": dec}


def _limit(status, value, reaction="", reason=""):
    return {"status": status, "value_V": None if status == "undetermined" else _r(value, 4),
            "reaction": reaction, "reason": reason}


def stability(rng):
    ph = np.round(np.linspace(0.0, 14.0, 57), 4)
    e = np.round(np.linspace(-2.5, 1.5, 81), 4)
    undet = "mock: no computable oxidation reaction for the active sink"
    return {
        "schema_version": "2", "mock": True, "generated_utc": STAMP,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "config_hash": ZSHA, "contract_sha": None,
                       "schema_sha": upstream.entry("results_schema", ROOT)["commit"]},
        "stability": {
            "R-slurry": {
                "kind": "pourbaix", "reference_electrode": "SHE", "temperature_K": 298.15,
                "axes": {"pH": ph.tolist(), "E_V": e.tolist()},
                "states": {"bulk": _state(ph, e, 0.0, 1e-3, 1e-4, rng),
                           "enriched": _state(ph, e, -0.6, 2e-2, 1e-4, rng)},
            },
            "R-cell": {
                "kind": "window", "reference_electrode": "Li+/Li", "temperature_K": 298.15,
                "convention": "mock",
                "sink_assumption": {"active": "mock-sink", "statement": NOTE, "kind": "solid_salt"},
                "windows": {
                    "CaCO3": {
                        "material_id": None,
                        "reduction": _limit("ok", 1.55, "mock reduction"),
                        "oxidation": _limit("ok", 3.7, "mock oxidation, lowest scheme"),
                        "oxidation_by_scheme": {"scheme-1": _limit("ok", 3.7, "mock oxidation"),
                                                "scheme-2": _limit("ok", 4.25, "mock oxidation")},
                        "reduction_by_scheme": {"scheme-1": _limit("ok", 1.55, "mock reduction"),
                                                "scheme-2": _limit("ok", 1.55, "mock reduction")},
                    },
                    "Al2O3": {
                        "material_id": None,
                        "reduction": _limit("ok", 1.2, "mock reduction"),
                        "oxidation": _limit("undetermined", None, reason=undet),
                        "oxidation_by_scheme": {"scheme-1": _limit("undetermined", None, reason=undet),
                                                "scheme-2": _limit("ok", 4.6, "mock oxidation")},
                        "reduction_by_scheme": {"scheme-1": _limit("ok", 1.2, "mock reduction"),
                                                "scheme-2": _limit("ok", 1.2, "mock reduction")},
                    },
                },
            },
        },
        "extensions": {"p0-w6": {"note": NOTE}},
    }


# ------------------------------------------------------------------------------ parameters

def params():
    """Mock rows for the keys the figures read, in lit/params.yaml's layout (key, value, range)."""
    def row(key, value=None, lo=None, hi=None, unit="1"):
        r = {"key": key, "unit": unit, "status": "mock", "value": value, "range": None}
        if lo is not None:
            r["range"] = {"min": lo, "max": hi}
        return r
    return {
        "mock": True,
        "meta": {"note": NOTE, "layout": "lit/params.yaml (lane p0-w1)"},
        "thresholds": {"C3": {"margin_cos_theta": row("m_cos", 0.2)}},
        "regimes": {
            "R-slurry": {"parameters": {"pH_range": row("pH_range", 11.0, 9.5, 12.5),
                                        "E_SHE_range": row("E_SHE_range", -0.9, -1.25, -0.55, "V")}},
            "R-cell": {"parameters": {"E_min": row("E_min", 2.5, unit="V"), "E_max": row("E_max", 4.1, unit="V")}},
        },
    }


def main():
    rng = np.random.default_rng(SEED)
    _write_json("retro_results.json", retro_results(rng))
    _write_json("screen_summary.json", screen_summary(rng))
    _write_json("stability.json", stability(rng))
    (HERE / "params.yaml").write_text(
        "# MOCK parameter rows in the layout of lit/params.yaml; synthetic, not literature values.\n"
        + yaml.safe_dump(params(), sort_keys=False))
    print("wrote mock inputs: retro_results.json, screen_summary.json, stability.json, params.yaml")


if __name__ == "__main__":
    main()
