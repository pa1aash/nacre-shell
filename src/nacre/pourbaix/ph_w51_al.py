"""PH-W5.1 step 2: the Al-O-H passivation window and a(Al3+) at the oxide-equilibrium state (lane p0-w5).

Thermodynamic question: over pH 3 to 10 at 298.15 K and I = 0, where does an Al oxide or hydroxide film stay
the stable Al phase with the total dissolved Al at equilibrium below a stated level c_thr (passivity, the
Pourbaix criterion), and what is the Al3+ activity it fixes at pH 5 to 8.5 (route R1, slurry stage)?

Inputs, all tabulated (no DFT): DfG of Al3+(aq) (TI-022), H2O(l) (params dfg_h2o_l, as PH-K1), boehmite
(TI-026); the hydrolysis constants of AlOH2+, Al(OH)2+, Al(OH)3(aq), Al(OH)4- (TB-023 to TB-026); the
solubility constants of Al(OH)3(am), gibbsite and corundum (TB-027 to TB-029). The ion data are benchmarked
against independent determinations before use: the aluminate from its DfG (TB-032) against TB-026 with
TI-022; boehmite DfG TI-026 against TB-033; the gibbsite solubility minimum against the measured minimum
(TB-030, TB-031). The published windows (TR-090: 4.5 to 8.5; TR-091: 4 to 8.5 at 0.1 mM Al) are printed
beside the computed one, not used.

Polyphosphate complexation of Al3+ (route C2) does not change a(Al3+) at fixed solid equilibrium: it raises
the total dissolved Al only. The complexation constants for linear chains are a gap
(polyp_al_log_beta1_linear), so total dissolved Al with polyphosphate present is not computed.
"""
import math

import numpy as np

from nacre.pourbaix import ph_k1 as k

LN10 = math.log(10.0)
PH_RANGE = (3.0, 10.0)
R1_RANGE = (5.0, 8.5)
C_THR = [1.0e-4, 1.0e-5, 1.0e-6]  # mol/L total dissolved Al; 1e-4 is TR-091's stated level, 1e-6 Pourbaix's
HYDROLYSIS = {"AlOH2+": ("TB-023", 1), "Al(OH)2+": ("TB-024", 2), "Al(OH)3(aq)": ("TB-025", 3),
              "Al(OH)4-": ("TB-026", 4)}
PUBLISHED = {"TR-090": (4.5, 8.5, "RSC Sustainability 2023 (d3su00031a), grade D, no Al level stated"),
             "TR-091": (4.0, 8.5, "Chem. Commun. 2016 (c6cc03969c), grade C, 0.1 mM soluble Al3+")}
PRIMARY = ("Al(OH)3 am", 1.0e-4)
REFERENCE = ("boehmite", 1.0e-4)
SLUG = {"boehmite": "boehmite", "gibbsite": "gibbsite", "Al(OH)3 am": "AlOH3_am", "corundum": "corundum"}


def _val(row_id):
    return float(k.evidence_rows()[row_id]["value"])


def rt_ln10_kj(T=k.T0):
    return k.constants.R * T * LN10 / 1000.0


def solids(ctx):
    """log10 K_s (solid + 3 H+ = Al3+ + n H2O, per Al) with source, grade and uncertainty in log units."""
    g_al, u_al, _ = k.row_kj("TI-022")
    h2o = k.ExptBook(ctx)("H2O")
    g_w, u_w = h2o.g_eV * k.KJ_PER_MOL_PER_EV, h2o.u_kJ
    g_b, u_b, _ = k.row_kj("TI-026")
    dg = g_al + 2 * g_w - g_b
    rows = {"boehmite": {"log_ks": -dg / rt_ln10_kj(), "u_log": (u_al + 2 * u_w + u_b) / rt_ln10_kj(),
                         "route": "DfG Al3+ (TI-022) + 2 DfG H2O(l) - DfG boehmite (TI-026)",
                         "sources": ["TI-022", "TI-026", "dfg_h2o_l"], "grade": "A"}}
    for name, rid, per in (("gibbsite", "TB-028", 1), ("Al(OH)3 am", "TB-027", 1), ("corundum", "TB-029", 2)):
        rows[name] = {"log_ks": _val(rid) / per, "u_log": None, "route": "solubility constant (acid form)%s" %
                      (", per Al (Al2O3 + 6 H+ = 2 Al3+ + 3 H2O)" if per == 2 else ""),
                      "sources": [rid], "grade": k.evidence_rows()[rid]["grade"]}
    return rows, {"dfg_al3_kJ": g_al, "dfg_h2o_kJ": g_w, "dfg_boehmite_kJ": g_b}


def log_betas():
    return {sp: _val(rid) for sp, (rid, _) in HYDROLYSIS.items()}


def speciation(log_ks, ph, betas):
    """log10 a of each Al species and of the total dissolved Al at equilibrium with one solid (I = 0)."""
    ph = np.asarray(ph, dtype=float)
    la = log_ks - 3.0 * ph
    out = {"Al3+": la}
    for sp, (_, n) in HYDROLYSIS.items():
        out[sp] = la + betas[sp] + n * ph
    tot = np.log10(sum(10.0 ** v for v in out.values()))
    out["total"] = tot
    return out


def _edge(f, a, b):
    """Root of a monotone f on [a, b] by bisection; None when f has no sign change."""
    fa, fb = f(a), f(b)
    if fa * fb > 0:
        return None
    for _ in range(80):
        m = 0.5 * (a + b)
        if f(m) * fa > 0:
            a, fa = m, f(m)
        else:
            b = m
    return 0.5 * (a + b)


def window(log_ks, betas, c_thr, lo=PH_RANGE[0], hi=PH_RANGE[1]):
    """pH interval inside [lo, hi] where the total dissolved Al at equilibrium is <= c_thr."""
    def f(ph):
        return float(speciation(log_ks, ph, betas)["total"]) - math.log10(c_thr)
    grid = np.linspace(lo, hi, 7001)
    tot = speciation(log_ks, grid, betas)["total"]
    imin = int(np.argmin(tot))
    ph_min, log_min = float(grid[imin]), float(tot[imin])
    if log_min > math.log10(c_thr):
        return {"lower": None, "upper": None, "passive": False, "ph_min": ph_min, "log_total_min": log_min}
    lower = _edge(f, lo, ph_min) if f(lo) > 0 else lo
    upper = _edge(f, ph_min, hi) if f(hi) > 0 else hi
    return {"lower": lower, "upper": upper, "passive": True, "lower_clipped": f(lo) <= 0, "upper_clipped": f(hi) <= 0,
            "ph_min": ph_min, "log_total_min": log_min}


def benchmark(ctx, sol, base):
    """Cross-checks of the ion data against independent determinations (differences in kJ/mol and log units)."""
    rt = rt_ln10_kj()
    g_alu_tb032 = _val("TB-032")
    g_alu_hyd = base["dfg_al3_kJ"] + 4 * base["dfg_h2o_kJ"] - rt * _val("TB-026")
    g_b_d = _val("TB-033")
    gib = sol["gibbsite"]["log_ks"]
    w = window(gib, log_betas(), 1.0)
    al_mass = 26.98
    meas_min = _val("TB-030") * 1e-3 / al_mass  # ppm (mg/L) as Al to mol/L
    return [
        {"check": "DfG Al(OH)4-: TB-032 (solubility, grade D) against TI-022 + 4 H2O + TB-026 log K",
         "a": g_alu_tb032, "b": g_alu_hyd, "diff_kJ": g_alu_tb032 - g_alu_hyd, "diff_log": (g_alu_hyd - g_alu_tb032) / rt,
         "sources": ["TB-032", "TI-022", "TB-026", "dfg_h2o_l"]},
        {"check": "DfG boehmite: TI-026 (grade A) against TB-033 (grade D)", "a": base["dfg_boehmite_kJ"], "b": g_b_d,
         "diff_kJ": base["dfg_boehmite_kJ"] - g_b_d, "diff_log": (g_b_d - base["dfg_boehmite_kJ"]) / rt,
         "sources": ["TI-026", "TB-033"]},
        {"check": "gibbsite solubility minimum: computed (TB-028 + TB-023..026) against the measured minimum for "
                  "microcrystalline gibbsite (TB-030, TB-031)",
         "computed_ph_min": w["ph_min"], "measured_ph_min": _val("TB-031"), "computed_log_total_min": w["log_total_min"],
         "measured_log_total_min": math.log10(meas_min), "diff_log": w["log_total_min"] - math.log10(meas_min),
         "note": "the measured phase is microcrystalline gibbsite, more soluble than the crystalline phase of TB-028",
         "sources": ["TB-028", "TB-030", "TB-031"]},
        {"check": "boehmite log K_s (TI-026 route) against gibbsite (TB-028) and Al(OH)3 am (TB-027)",
         "boehmite": sol["boehmite"]["log_ks"], "gibbsite": gib, "am": sol["Al(OH)3 am"]["log_ks"],
         "ordering_ok": gib <= sol["Al(OH)3 am"]["log_ks"] and sol["boehmite"]["log_ks"] <= sol["Al(OH)3 am"]["log_ks"],
         "sources": ["TI-026", "TB-027", "TB-028"]},
    ]


def run(ctx=None):
    ctx = ctx or k.Ctx()
    sol, base = solids(ctx)
    betas = log_betas()
    windows = []
    for name, s in sol.items():
        for c in C_THR:
            wnd = window(s["log_ks"], betas, c)
            if s.get("u_log"):
                wl = window(s["log_ks"] - s["u_log"], betas, c)
                wh = window(s["log_ks"] + s["u_log"], betas, c)
                wnd["lower_range"] = [wl["lower"], wh["lower"]]
                wnd["upper_range"] = [wh["upper"], wl["upper"]]
            windows.append({"solid": name, "c_thr_M": c, **wnd, "log_ks": s["log_ks"], "sources": s["sources"]})
    primary = next(x for x in windows if (x["solid"], x["c_thr_M"]) == PRIMARY)
    reference = next(x for x in windows if (x["solid"], x["c_thr_M"]) == REFERENCE)
    grid = np.round(np.arange(R1_RANGE[0], R1_RANGE[1] + 1e-9, 0.1), 2)
    a_rows = []
    specs = {n: speciation(s["log_ks"], grid, betas) for n, s in sol.items()}
    for i, ph in enumerate(grid):
        row = {"pH": float(ph)}
        for n in sol:
            row["log10_a_Al3_%s" % SLUG[n]] = float(specs[n]["Al3+"][i])
            row["log10_total_Al_%s" % SLUG[n]] = float(specs[n]["total"][i])
        row["fraction_Al3_of_dissolved"] = float(10 ** (specs["boehmite"]["Al3+"][i] - specs["boehmite"]["total"][i]))
        a_rows.append(row)
    return {"question": __doc__.split("\n")[2].strip(), "solids": sol, "base_kJ": base, "log_betas": betas,
            "hydrolysis_sources": {sp: rid for sp, (rid, _) in HYDROLYSIS.items()}, "windows": windows,
            "primary": {"solid": PRIMARY[0], "c_thr_M": PRIMARY[1], **primary,
                        "why": "the native and in-situ films are amorphous, so the amorphous phase governs (the C4 reading "
                               "applied to the oxide film; chosen in PH-W5.1, for vetting in PH-W3.2); 0.1 mM is the one Al "
                               "level a published window states (TR-091)"},
            "reference": {"solid": REFERENCE[0], "c_thr_M": REFERENCE[1], **reference,
                          "why": "crystalline upper reference: the only Al solid with a grade-A DfG (TI-026), the gated Al "
                                 "phase of the R-cell window (params s_boehmite)"},
            "published": {rid: {"lower": a, "upper": b, "note": n} for rid, (a, b, n) in PUBLISHED.items()},
            "benchmark": benchmark(ctx, sol, base), "a_al3_rows": a_rows,
            "r1_reading": "a(Al3+) at oxide equilibrium falls 1000-fold per pH unit (slope -3); the robust R1 falsifying "
                          "test uses the most soluble film phase, Al(OH)3 am (the highest a(Al3+)), and boehmite as the "
                          "stable reference. Polyphosphate complexation leaves a(Al3+) unchanged at fixed solid "
                          "equilibrium; linear-chain constants are a gap, cyclic ones are single-source.",
            "conventions": {"T_K": ctx.T, "I": 0, "activities": "a = c (I = 0)", "ph_range": PH_RANGE,
                            "criterion": "passive where total dissolved Al at equilibrium with the solid <= c_thr"}}
