"""Generate the mock inputs of the data figures, in the owners' shapes.

MOCK DATA. Every number here is synthetic, chosen only to exercise the templates; none is a
result, a literature value or a parameter of the study. Each file carries "mock": true, and the
figure builder writes figures built from it only to figures/out/mock/.

  retro_results.json   retro-results/v1 (lane p0-w2, SCHEMA.md section 5)       -> fig4
  screen_summary.json  results schema v3, screen regimes (lane p0-w4)            -> fig5, fig6
  screen_c5.json       results schema v3, claim C5 tests (lane p0-w4)            -> fig7
  params.yaml          mock rows in the layout of lit/params.yaml (lane p0-w1)    -> fig5, fig7
  ladder_v3*.json, ladder_cutoffs.yaml, benchmark_w51*.json, passivation_window_v3.json,
  al_window.json       CSV outputs as {columns, rows} and their JSON/YAML companions -> fig9, fig10, fig11

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
            "interface": ROUTES[len(out) % len(ROUTES)],
        })
    n = len(out)
    k = next(k for k in range(n + 1) if sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n <= 0.05)
    tally = {v: sum(1 for c in out if c["verdict"] == v)
             for v in ("correct", "incorrect", "inconclusive", "undetermined")}
    return {
        "schema": "retro-results/v1", "mock": True,
        "cases_sha256": "sha256:" + upstream.entry("retro_cases", ROOT)["sha256"],
        "criterion_sha256": ZSHA, "fixed_before_run_commit": ZERO40,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "contract_sha": ZERO40, "params_tag": "mock",
                       "params_file_hash": ZSHA, "criterion_sha": ZERO40},
        "draws": 20000, "seed": 0, "cases": out,
        "summary": {"N": n, **tally, "k": k,
                    "chance_probability": _r(sum(comb(n, j) for j in range(k, n + 1)) / 2 ** n),
                    "pass": tally["correct"] >= k,
                    "swap_check": {"holds": True, "max_abs_sum": 0.0},
                    "permutation_null": {key: _null(rng, n, 2000, shift) for key, shift in
                                         (("within_study", 0.0), ("across_studies", 0.4))}},
    }


ROUTES = ("gamma_sn", "gamma_sl")


def _null(rng, n, n_perm, shift):
    """Synthetic permutation null: a binomial count of correct cases."""
    draws = rng.binomial(n, 0.4 + 0.02 * shift, n_perm)
    counts = np.bincount(draws, minlength=n + 1)[: n + 1]
    return {"n_perm": n_perm, "median": float(np.median(draws)),
            "range95": [float(np.quantile(draws, 0.025)), float(np.quantile(draws, 0.975))],
            "mean": _r(draws.mean()), "fraction_ge_observed": _r(rng.uniform(0.05, 0.3)),
            "counts": [int(c) for c in counts], "descriptive": True}


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


def _prefactor():
    """Synthetic reference inputs; B_kT from the contract functions at them (fig5 checks the match)."""
    from nacre.physics import nucleation
    g, vm, temp = 0.25, 3.5e-5, 300.0
    omega = 10.0
    b = nucleation.barrier_in_kT(nucleation.homogeneous_barrier_from_saturation(g, vm, omega, temp), temp)
    return {"reference_gamma_nl": g, "V_m": vm, "T": temp, "B_kT": float(b * np.log(omega) ** 2),
            "reference": NOTE, "state": "slurry",
            "units": {"reference_gamma_nl": "J m^-2", "V_m": "m^3 mol^-1", "T": "K", "B_kT": "1"}}


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
        "barrier_prefactor": _prefactor(),
        "dependence": {"method": "gaussian_copula",
                       "rank_correlations": [{"a": "gamma_sl0", "b": "gamma_sn0", "spearman_rho": 0.5,
                                              "source": "mock"}]},
        "primary_state": "slurry",
        "states": {"drying": {"quantities": {"nucleate": q_dry}, "boundary_mass": {"nucleate": m_dry}}},
    }
    return {
        "schema_version": "3", "mock": True, "generated_utc": STAMP,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "config_hash": ZSHA,
                       "prior_file": "figures/src/mock/params.yaml", "prior_file_hash": ZSHA,
                       "contract_sha": None, "params_sha": None, "thresholds_file": None, "thresholds_hash": None,
                       "thresholds_source_sha": None, "schema_sha": upstream.entry("results_schema", ROOT)["commit"]},
        "regimes": {"R-slurry": regime},
        "required_precision": {"R-slurry": precision},
        "extensions": {"p0-w6": {"note": NOTE}},
    }


# ----------------------------------------------------------------------------------- fig 7

CA_DOSES = (1e-6, 1e-5, 1e-4, 1e-3, 1e-2)  # mol dm^-3, synthetic grid
CT_AT = ("min", "value", "max")
A_W = ("wet", "dry")


def _point(ca, at, aw, p_good):
    verdict = "feasible" if p_good >= 0.9 else ("falsified" if p_good <= 0.1 else "inconclusive")
    return {"axes": {"Ca_T": "%g mol dm^-3" % ca, "C_T": "dic_slurry@%s" % at, "a_w": aw},
            "P_good": _r(p_good), "P_bad": _r(1 - p_good), "half_width": 0.0, "verdict": verdict, "state": "slurry"}


def _row(phase, scheme, status, value, role="comparator", sink="mock-salt"):
    return {"phase": phase, "sink": sink, "sink_kind": "solid_salt", "scheme": scheme,
            "role": "governing" if scheme == "expt" else role, "status": status,
            "value_V": None if status != "ok" else _r(value, 4), "benchmark_error_V": None}


def screen_c5(rng):
    points = {}
    for ca in CA_DOSES:
        for k, at in enumerate(CT_AT):
            p = 1.0 / (1.0 + np.exp(-(np.log10(ca) + 4.6 - 0.3 * k) * 3.0))
            for aw in A_W:
                points["Ca_T=%g; C_T=%s; a_w=%s" % (ca, at, aw)] = _point(ca, at, aw, p)
    ox = [_row("CaCO3", "expt", "ok", 3.8), _row("CaCO3", "janaf", "ok", 4.2), _row("CaCO3", "janaf_corrected", "ok", 3.8),
          _row("CaCO3", "mp", "ok", 3.6), _row("CaCO3", "mp_corrected", "ok", 3.8),
          _row("corundum", "expt", "undetermined", None), _row("corundum", "janaf", "undetermined", None),
          _row("CaCO3", "expt", "undetermined", None, sink="mock-other")]
    red = [_row("CaCO3", "expt", "absent", None), _row("CaCO3", "janaf", "ok", 1.6), _row("CaCO3", "janaf_corrected", "ok", 1.3),
           _row("CaCO3", "mp", "ok", 1.6), _row("CaCO3", "mp_corrected", "ok", 1.8),
           _row("corundum", "expt", "absent", None), _row("corundum", "janaf", "ok", 1.2)]
    cutoffs = {"class-A@min": 3.6, "class-A@value": 4.0, "class-A@max": 4.2,
               "class-B@min": 4.3, "class-B@value": 4.5, "class-B@max": 4.6}
    axis = {k: {"bound_V": v, "verdict": "falsified" if v > 3.9 else "inconclusive"} for k, v in cutoffs.items()}
    return {
        "schema_version": "3", "mock": True, "generated_utc": STAMP,
        "provenance": {"git_sha": ZERO40, "git_dirty": False, "config_hash": ZSHA, "contract_sha": None,
                       "schema_sha": upstream.entry("results_schema", ROOT)["commit"]},
        "claims": {"C5": {"verdict": "inconclusive", "dose_window": {
            "points": points,
            "feasible_points": sorted(k for k, v in points.items() if v["verdict"] == "feasible"),
            "falsified_points": sorted(k for k, v in points.items() if v["verdict"] == "falsified"),
            "inconclusive_points": sorted(k for k, v in points.items() if v["verdict"] == "inconclusive")}, "tests": {
            "C5s": {"verdict": "inconclusive"},
            "C5c_ox": {"verdict": "inconclusive", "scheme_table": ox, "cutoff_axis": axis, "margin_V": 0.09,
                       "crossovers": {"CaCO3": {"mock-salt": {"falsified_above_V": 3.89, "feasible_at_or_below_V": None}}}},
            "C5c_red": {"verdict": "inconclusive", "scheme_table": red,
                        "cutoff_axis": {"registered": {"bound_V": 3.0, "verdict": "inconclusive"}}},
        }}},
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
        "params": {"dic_slurry": row("dic_slurry", 9.0, 4.0, 16.0, "mol m^-3")},
        "thresholds": {"C3": {"margin_cos_theta": row("m_cos", 0.2)},
                       "decision": {"credible_level": row("p_cred", 0.9)}},
        "regimes": {
            "R-slurry": {"parameters": {"pH_range": row("pH_range", 11.0, 9.5, 12.5),
                                        "E_SHE_range": row("E_SHE_range", -0.9, -1.25, -0.55, "V"),
                                        "J0_het": row("j0_het", 1e18, unit="m^-2 s^-1"),
                                        "t_proc": row("t_proc_slurry", 3600.0, unit="s"),
                                        "patch_area": row("patch_area", 1e-10, unit="m^2")}},
            "R-cell": {"parameters": {"E_min": row("E_min", 2.5, unit="V"), "E_max": row("E_max", 4.1, unit="V")}},
        },
    }


# ------------------------------------------------------------------------------ figs 9 to 11

def _table(columns, rows):
    """A CSV output as nacre.figs.upstream.parse_csv returns it: every cell a string."""
    return {"mock": True, "note": NOTE, "columns": columns,
            "rows": [{c: str(r.get(c, "")) for c in columns} for r in rows]}


def ladder():
    cols = ["phase", "framing", "stage", "reaction_id", "k1_class_lfp", "k1_class_42_43", "k1_class_44_45",
            "k1_verdict"]
    spec = [("brushite", "slurry", "inconclusive", "falsified", "falsified"),
            ("HAp", "slurry", "inconclusive", "inconclusive", "falsified"),
            ("AlPO4", "cell", "undetermined", "undetermined", "undetermined"),
            ("Ca2P2O7", "cell", "inconclusive", "inconclusive", "inconclusive"),
            ("CaSiO3", "comparator", "falsified", "falsified", "falsified"),
            ("CaCO3", "control", "inconclusive", "falsified", "falsified")]
    rows = []
    for ph, st, *v in spec:
        rows.append(dict(zip(cols, [ph, "crystalline", st, "ALL", *v, v[0]])))
        rows.append(dict(zip(cols, [ph, "amorphous", st, "-", *["undetermined"] * 3, "undetermined"])))
    return _table(cols, rows)


def benchmark():
    cols = ["phase", "family", "dft_minus_dfH_kJ_per_atom", "display"]
    spec = [("HAp", "phosphate", -4.1, "dft-benchmarked"), ("brushite", "phosphate", -15.0, "dft-benchmark-failed"),
            ("LiPO3 glass", "phosphate", -12.0, "dft-unbenchmarked"), ("Li2SiO3", "silicate", -3.0, "dft-benchmarked"),
            ("CaSiO3", "silicate", -6.5, "dft-benchmark-failed"), ("gibbsite", "Al-O-H", -11.0, "dft-benchmark-failed")]
    return _table(cols, [dict(zip(cols, r)) for r in spec])


def passivation():
    cols = ["solid", "role", "al_level_M", "ph_lower", "ph_upper", "window"]
    rows = []
    for lvl, am, bo in ((1e-4, ("5.0", "8.3"), ("4.0", ">10")), (1e-5, ("5.5", "7.2"), ("4.3", "9.9")),
                        (1e-6, ("", ""), ("4.7", "9.0"))):
        rows.append(dict(zip(cols, ["Al(OH)3 am", "governing (ruling a)", lvl, *am, "mock"])))
        rows.append(dict(zip(cols, ["boehmite", "reference (ruling a)", lvl, *bo, "mock"])))
    return _table(cols, rows)


def main():
    rng = np.random.default_rng(SEED)
    _write_json("retro_results.json", retro_results(rng))
    _write_json("screen_summary.json", screen_summary(rng))
    _write_json("screen_c5.json", screen_c5(rng))
    _write_json("ladder_v3.json", ladder())
    _write_json("ladder_v3_sens40.json", ladder())
    (HERE / "ladder_cutoffs.yaml").write_text(
        "# MOCK cutoff classes in the layout of thresholds.yaml; synthetic.\nmock: true\n" + yaml.safe_dump(
            {"screen_ph": {"margins_v6": {"cutoff_classes": {"C_lo": {"E_c_V": [3.0]}, "C_mid": {"E_c_V": [4.0, 4.1]},
                                                             "C_hi": {"E_c_V": [4.2, 4.3]}}}}}))
    _write_json("benchmark_w51.json", benchmark())
    _write_json("benchmark_w51_summary.json", {"mock": True, "summary": {"e_form": {"max": 5.0},
                                                                         "oxide_correction_kJ_per_O": -60.0}})
    _write_json("passivation_window_v3.json", passivation())
    _write_json("al_window.json", {"mock": True, "conventions": {"ph_range": [3.0, 10.0]},
                                   "published": {"MOCK-1": {"lower": 4.5, "upper": 8.5}, "MOCK-2": {"lower": 4.0, "upper": 8.0}}})
    (HERE / "params.yaml").write_text(
        "# MOCK parameter rows in the layout of lit/params.yaml; synthetic, not literature values.\n"
        + yaml.safe_dump(params(), sort_keys=False))
    print("wrote mock inputs: retro_results.json, screen_summary.json, screen_c5.json, params.yaml")


if __name__ == "__main__":
    main()
