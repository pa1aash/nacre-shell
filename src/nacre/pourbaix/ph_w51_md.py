"""PH-W5.1 report (ph_w51.md, at most 60 lines) rendered from the committed JSON outputs."""

MAX_LINES = 60
BENCH_SHOWN = ["P2O5", "HAp", "b-TCP", "a-TCP", "brushite", "monetite", "Ca2P2O7", "AlPO4", "Li3PO4", "LiPO3",
               "Ca(PO3)2 glass", "gibbsite"]


def _v(x, nd=3):
    return "-" if x is None else "%.*f" % (nd, x)


def _short(display):
    return display.split(" (")[0]


def _bench(bench):
    by = {r["phase"]: r for r in bench["rows"]}
    s = bench["summary"]
    sp = s["onset_spread"]
    out = ["## 1. Phosphate benchmark (MP 2026.09.28 minus tables, kJ/mol per formula unit; DfH basis)",
           "| Phase | MP | DFT-DfH | per atom | Status | Cause |", "|---|---|---|---|---|---|"]
    for p in BENCH_SHOWN:
        r = by[p]
        out.append("| %s | %s | %s | %s | %s | %s |" % (p, r["material_id"], _v(r.get("dft_minus_dfH_kJ"), 0),
                                                       _v(r.get("dft_minus_dfH_kJ_per_atom"), 1), _short(r["display"]),
                                                       r["cause_short"]))
    ok = ", ".join(r["phase"] for r in bench["rows"] if r["display"].startswith("dft-benchmarked"))
    out.append("Shown MP numbers: `dft-benchmarked` = " + ok + " (|error| <= %.2f kJ/mol per atom, "
               "formation_energy_mae); every other MP number is a labelled comparator with its measured error (`dft-benchmark-"
               "failed`) or `dft-unbenchmarked` (DfG-only rows, glasses, Ca(PO3)2 and Al(PO3)3 crystals). The phosphate "
               "benchmark does not pass as a set; no DFT number decides a K1 row." % s["e_form"]["max"])
    out.append("Spread: %.0f to %.0f kJ/mol over the PH-K1 set. Causes: MP2020 puts one oxide correction (%.1f kJ/mol per O) "
               "on every O (lattice water, OH, covalent P-O, P-O-P); brushite exceeds monetite by %.1f per lattice water; "
               "raw GGA underbinding falls from ~59 (ionic Ca-O) to 39 to 49 kJ/mol per O (P2O5, AlPO4, acid phosphates), so "
               "condensed and acid phases are over-corrected; alpha/beta-TCP order inverted (polymorph); glasses vs crystals; "
               "MP's P reference is %s, not white P (offset unquantified). **SI finding:** on one reaction DFT minus "
               "experiment runs %+.2f to %+.2f V (median %+.2f V, %d reaction-scheme pairs)."
               % (min(abs(by[p]["dft_minus_dfH_kJ"]) for p in ("P2O5", "HAp", "b-TCP", "a-TCP", "brushite", "monetite",
                                                               "Ca2P2O7", "AlPO4")),
                  max(abs(by[p]["dft_minus_dfH_kJ"]) for p in ("P2O5", "HAp", "b-TCP", "brushite")),
                  s["oxide_correction_kJ_per_O"], by["brushite"]["hydrate_excess_per_water_kJ"],
                  s["p_reference"]["mp_reference"], sp["min"]["dft_minus_expt_V"], sp["max"]["dft_minus_expt_V"],
                  sp["median_V"], sp["n"]))
    return out


def _window(al):
    p, ref = al["primary"], al["reference"]
    w = {(x["solid"], x["c_thr_M"]): x for x in al["windows"]}

    def rng(x):
        if not x["passive"]:
            return "none"
        hi = ">10" if x.get("upper_clipped") else _v(x["upper"], 2)
        lo = "<3" if x.get("lower_clipped") else _v(x["lower"], 2)
        return "%s-%s" % (lo, hi)
    b = al["benchmark"]
    out = ["", "## 2. Al-O-H passivation window (own speciation, tabulated ion data, pH 3 to 10, I = 0)",
           "| Film solid (log K_s) | 0.1 mM | 10 uM | 1 uM |", "|---|---|---|---|"]
    for s in ("Al(OH)3 am", "boehmite", "gibbsite", "corundum"):
        out.append("| %s (%.2f) | %s | %s | %s |" % (s, al["solids"][s]["log_ks"], *(rng(w[(s, c)]) for c in
                                                                                   (1e-4, 1e-5, 1e-6))))
    out.append("**Window: pH %.1f to %.1f** (Al(OH)3 am at 0.1 mM, governing: the film is amorphous; chosen here, for "
               "PH-W3.2 to vet). Crystalline reference boehmite (grade A): %.1f (%.1f-%.1f) to >10. Published: 4.5 to 8.5 "
               "(TR-090, grade D) and 4 to 8.5 at 0.1 mM (TR-091, grade C). Ion-data benchmark: aluminate DfG (TB-032) vs "
               "TI-022 + TB-026 %+.1f kJ/mol; boehmite TI-026 vs TB-033 %+.1f kJ/mol; gibbsite minimum at pH %.1f (measured "
               "%.1f, microcrystalline, %.1f log units more soluble)."
               % (p["lower"], p["upper"], ref["lower"], ref["lower_range"][0], ref["lower_range"][1], b[0]["diff_kJ"],
                  b[1]["diff_kJ"], b[2]["computed_ph_min"], b[2]["measured_ph_min"], -b[2]["diff_log"]))
    rows = {r["pH"]: r for r in al["a_al3_rows"]}
    out.append("R1 input (a_al3_oxide.csv): log10 a(Al3+) at pH 5 / 7 / 8.5 = %.1f / %.1f / %.1f (am) and %.1f / %.1f / "
               "%.1f (boehmite); slope -3 per pH; polyphosphate complexation leaves a(Al3+) unchanged (linear-chain "
               "constants a gap)." % tuple(rows[x]["log10_a_Al3_%s" % s] for s in ("AlOH3_am", "boehmite")
                                           for x in (5.0, 7.0, 8.5)))
    return out


def _cls(r):
    st = r.get("statuses") or {}
    m = {"above (ub)": "ub+", "below": "below", "within budget": "within", "undetermined": "und", "not run": "n/r",
         "tier 2 gap": "t2 gap"}
    return "/".join(m.get(st.get(c), "-") for c in ("LFP-class", "4.2-4.3 V", "4.4-4.5 V"))


def _ladder(doc):
    rows = doc["ladder"]
    by = {}
    for r in rows:
        by.setdefault(r["phase"], {})[r["framing"]] = r
    out = ["", "## 3-7. K1 ladder v2, tier 1 (V vs Li+/Li; E_ub solid-salt sink +- provisional margin; classes "
           "LFP/4.2-4.3/4.4-4.5)", "| Phase | Stage | Crystalline E_ub | Amorphous E_ub | E_lb | Classes (cr; am) | Label |",
           "|---|---|---|---|---|---|---|"]
    for ph, f in by.items():
        if "crystalline" in f:
            c, a = f["crystalline"], f.get("amorphous", {})

            def e(r):
                return "%.3f +- %.3f" % (r["E_ub_V"], r["margin_V"]) if r.get("E_ub_V") is not None else "und."
            lab = c.get("label", "").replace("crystalline shown, glass-to-crystal correction missing (gap flagged); ", "gap; ")
            out.append("| %s | %s | %s | %s | %s | %s; %s | %s |" % (ph, c["stage"], e(c), e(a) if a else "-",
                                                                   "pending" if "pending" in c["bracket"] else "-",
                                                                   _cls(c), _cls(a) if a else "-", lab.split(";")[0]))
    matrix = [r["phase"] for r in rows if r["row_type"] == "matrix"]
    not_run = [r["phase"] for r in rows if (r.get("statuses") or {}).get("LFP-class") == "not run"]
    out.append("Matrix rungs (C6, tier 2 only): %s: gap, matrix-risk flag (no tier 2 record at W1.2; polydopamine is the "
               "stated K1 risk, contrary B4); never a tier-1 number. Not run: %s (no Ca-Al phosphate data)."
               % (", ".join(matrix), ", ".join(not_run)))
    return out


def _tail(doc):
    st = doc["staged_products"]
    ca, cg = st["values"]["Ca(PO3)2"], st["values"]["Ca(PO3)2-glass"]
    conv = {c["step"]: c for c in doc["conversions"]}
    br, f7 = doc["bracket"], doc["carbonate_f7"]

    def aw(step):
        c = conv[step]
        return "%.3g (%.2g-%.3g)" % (c["a_w_star"], *c["a_w_star_range"])
    return [
        "",
        "**F3(a) Ca(PO3)2:** DfG(crystal) = %.1f +- %.1f kJ/mol (glass DfH TR-032 minus h_vit %.1f, u %.1f inflated x%g from "
        "LiPO3/NaPO3 glass-crystal pairs; S0 TR-031; JANAF white P, alpha Ca, O2); glass %.1f +- %.1f. It makes Ca(PO3)2 "
        "(4.97/4.89 V) and the staged Ca2P2O7 route determined. **F3(b) Al(PO3)3:** undetermined (search logged in "
        "ph_w51.json; DFT 5.63 V stays a comparator)." % (ca["dfG_kJ"], ca["u_kJ"], ca["h_vit_kJ"], ca["u_vit_kJ"],
                                                         st["vitrification"]["inflation"], cg["dfG_kJ"], cg["u_kJ"]),
        "**Conversion steps (a_w*):** brushite->monetite %s; monetite->Ca2P2O7 %s; Ca2P2O7 + H3PO4 -> Ca(PO3)2 %s; AlO(OH) + "
        "H3PO4 -> AlPO4 %s; coacervate->glass, AlPO4->Al(PO3)3, R1 gel: undetermined. Literature conversion temperatures: "
        "pending PH-W1.3 (no rows); beside them the 100 to 350 C cure of US 8,252,463 (novelty BL3) and the 150 C dry of "
        "US 6,485,866 (BL1)." % (aw("brushite -> monetite + 2 H2O"), aw("2 monetite -> Ca2P2O7 + H2O"),
                                 aw("Ca2P2O7 + 2 H3PO4 -> 2 Ca(PO3)2 + 3 H2O"), aw("AlO(OH) + H3PO4 -> AlPO4 + 2 H2O")),
        "**Bracket (F2):** %s: %s at %s (%s). Convention when computed: Li+/Li with Li+ hydrated in the same solvent; anion "
        "term ClO4-(aq)." % (br["status"], ", ".join(br.get("missing", [])) or "keys present", br["ref"],
                             br.get("commit", "")[:7]),
        "**Carbonate (F7):** expt %.3f V (frozen gate unchanged); DFT 2026.09.28 janaf/mp %.3f/%.3f V against frozen "
        "2026.04.13 %.3f/%.3f V." % (f7["expt_V"], f7["dft_2026_09_28_V"]["janaf"], f7["dft_2026_09_28_V"]["mp"],
                                     f7["dft_frozen_2026_04_13_V"]["janaf"], f7["dft_frozen_2026_04_13_V"]["mp"]),
        "**Reading.** No row passes (no solvated sink). Ca orthophosphates stay below 4.2 V (ub). Condensed phases sit "
        "above every class on the upper bound: Ca(PO3)2 crystal/glass, (LiPO3)n crystal/glass; Ca2P2O7's staged route "
        "(4.47 V) is within the 4.2-4.5 V margins. AlPO4 and every Al(PO3)3 or Al-polyphosphate row stay undetermined. No "
        "row is 'requires crystallisation'. (LiPO3)n: K2 expected fail (water-soluble; composition-based inference).",
    ]


def render(bench, al, doc):
    lines = ["# PH-W5.1: phosphate benchmark, Al passivation window, K1 ladder v2", "",
             "Tier 1 only, 298.15 K, a_w = a_OH = 1; margins provisional; DFT = Materials Project 2026.09.28, comparator "
             "only. Files: benchmark_w51.csv, al_window.json, a_al3_oxide.csv, ladder_v2.csv, ph_w51.json.", ""]
    lines += _bench(bench) + _window(al) + _ladder(doc) + _tail(doc)
    if len(lines) > MAX_LINES:
        raise ValueError("ph_w51.md has %d lines (limit %d)" % (len(lines), MAX_LINES))
    return "\n".join(lines) + "\n"
