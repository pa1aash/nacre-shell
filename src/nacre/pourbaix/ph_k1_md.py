"""ph_k1.md: the K1 tier-1 ladder as a short document (at most 60 lines)."""
import statistics

from nacre.pourbaix import ph_k1 as k

LABEL = {"below": "below", "above": "above (ub)", "within budget": "within", "undetermined": "undetermined"}
SHORT = {"HAp": "HAp", "b-TCP": "beta-TCP", "a-TCP": "alpha-TCP", "OCP": "OCP", "brushite": "brushite (precursor)",
         "monetite": "monetite (precursor)", "Ca2P2O7": "Ca2P2O7", "Ca(PO3)2": "Ca(PO3)2", "AlPO4": "AlPO4",
         "Al(PO3)3": "Al(PO3)3", "Li3PO4": "Li3PO4 (competing)", "CaSiO3": "CaSiO3 (cmp)", "Ca2SiO4": "Ca2SiO4 (cmp)",
         "Li2SiO3": "Li2SiO3 (cmp)", "CaCO3": "CaCO3 (control)"}


def _v(x, nd=2):
    return "-" if x is None else "%.*f" % (nd, x)


def render(doc):
    ph, lad = doc["phases"], doc["ladder"]
    g = doc["gate"]
    cls = list(k.CUTOFF_CLASSES)
    by = {(r["phase"], r["class"]): r for r in lad}
    L = []
    L.append("# PH-K1 tier 1: oxidation-limit ladder (experimental route, vs Li+/Li)")
    L.append("")
    L.append("Gate: carbonate control %.4f V vs frozen %.3f V (%.2f mV); its budget %.4f V equals `window_margin_expt`. "
             "Onsets: a_w = 1, a_OH = 1, solid-salt LiClO4 sink (**upper bound on the onset**: *below* stands; *above (ub)* "
             "is not a pass, no solvated sink exists). Margin m is provisional." % (
                 g["value_V"], g["frozen_V_inventory"], g["difference_to_inventory_mV"], g["budget_V"]))
    L.append("")
    L.append("| Phase | Limiting reaction | E_ox (V) +- m | DFT janaf/mp | 3.65 V | 4.2-4.3 V | 4.4-4.5 V |")
    L.append("|---|---|---|---|---|---|---|")
    for pid in k.ORDER:
        s = ph[pid]["summary"]
        e = s["expt"]
        lim = ph[pid]["reactions"][e["limiting"]]["class"].split("(")[0].replace("lattice O2 release", "lattice O2").strip() \
            if e else "undetermined: " + ", ".join(s["expt_undetermined"])
        if e and e["limiting"] in ph[pid]["reactions"]:
            r = ph[pid]["reactions"][e["limiting"]]
            tail = r["class"][r["class"].index("(") :] if "(" in r["class"] else ""
            lim = "%s %s" % (e["limiting"], tail)
        dj, dm = s["janaf"]["onset_V"], s["mp"]["onset_V"]
        cells = [LABEL[by[(pid, c)]["status"]] for c in cls]
        L.append("| %s | %s | %s | %s/%s | %s |" % (
            SHORT[pid], lim, ("%.3f +- %.3f%s" % (e["onset_V"], e["budget_V"], "*" if not e["budget_complete"] else ""))
            if e else "-", _v(dj), _v(dm), " | ".join(cells)))
    L.append("")
    L.append("`*` budget lacks a term (Al(ClO4)3 exchange entropy; quartz uncertainty). A phase with undetermined reactions "
             "shows the determined minimum only when it is already below the class. DFT: Materials Project %s, BY-C, "
             "`dft-unbenchmarked`; CaCO3 DFT values are the frozen production ones." %
             doc["inputs"]["mp_database_version_ph_cache"])
    L.append("")
    up = doc["upper_bound_above"]
    L.append("**Clearing.** No phase passes at any class: a pass needs a solvated sink (keys are gaps). Upper-bound *above*: "
             "3.65 V: %s; 4.2-4.3 V: %s; 4.4-4.5 V: %s. Undetermined: %s." % (
                 ", ".join(up[cls[0]]) or "none", ", ".join(up[cls[1]]) or "none", ", ".join(up[cls[2]]) or "none",
                 ", ".join(doc["undetermined_phases"])))
    ca = [p for p in ("HAp", "b-TCP", "a-TCP") if ph[p]["summary"]["expt"]]
    L.append("**Reading.** The Ca orthophosphates fall at %s V (staged release to Ca2P2O7), below the 4.2-4.3 V class and above "
             "the LFP class; carbonate sits at %.3f V. AlPO4's determined reaction is %.2f V but its staged route to Al(PO3)3 is "
             "untabulated (DFT comparator 4.99 V); Ca2P2O7's staged route to Ca(PO3)2 is untabulated (DFT comparator %.2f V "
             "against 4.55 V for its full release). Silicates lie at %.2f-%.2f V, at or below the LFP class." % (
                 "/".join("%.2f" % ph[p]["summary"]["expt"]["onset_V"] for p in ca), g["value_V"],
                 ph["AlPO4"]["summary"]["expt"]["onset_V"],
                 ph["Ca2P2O7"]["reactions"]["r1s"]["routes"]["janaf"]["onset_V"], ph["Ca2SiO4"]["summary"]["expt"]["onset_V"],
                 ph["Li2SiO3"]["summary"]["expt"]["onset_V"]))
    L.append("")
    b = [r for r in doc["benchmark"] if "dft_minus_dfH_kJ_per_mol" in r and r["species"] not in ("LiClO4",)]
    rng = "; ".join("%s %.0f" % (r["species"], r["dft_minus_dfH_kJ_per_mol"]) for r in b
                    if r["species"] in ("HAp", "b-TCP", "a-TCP", "brushite", "monetite", "Ca2P2O7", "AlPO4", "P2O5"))
    L.append("**Benchmark** (MP formation energy minus tabulated DfH, kJ/mol per formula unit; minus DfG is 40-260 kJ/mol "
             "more negative, see benchmark.csv): %s. DFT-minus-experiment onsets, same reaction: %s." % (rng, _onset_gap(ph)))
    L.append("")
    L.append("**Biggest gaps.** (1) Solvated sink: every onset is an upper bound. (2) Missing species make the reaction "
             "undetermined: Ca(PO3)2 and Al(PO3)3 (no data), Li3PO4 (DfG, S), and the staged routes through them. (3) a_w and the "
             "OH-site activity are grids (a_w = 1e-6 lowers a water-releasing onset by 0.02-0.05 V). (4) Brushite/monetite: "
             "a_w* = %.2f (range %.2f-%.2f), so brushite is at the dehydration threshold within the row uncertainties. (5) OCP "
             "rests on one DfG row (no DfH or S): undetermined; its information-only value is %.2f V (r1s)." % (
                 doc["dehydration_threshold"]["a_w_star"], *doc["dehydration_threshold"]["a_w_star_range"],
                 ph["OCP"]["reactions"]["r1s"]["provisional_dfg_only"]["onset_V"]))
    L.append("")
    L.append("**Key requests for W1**")
    for r in doc["key_requests"][:8]:
        L.append("- `%s`: %s" % (r["key"], r["why"].split(";")[0].split(" (")[0].rstrip(".")))
    return "\n".join(L) + "\n"


def _onset_gap(ph):
    d = []
    for pid in k.ORDER:
        if pid == "CaCO3":
            continue
        for r in ph[pid]["reactions"].values():
            for s, v in (r.get("dft_minus_expt_V") or {}).items():
                d.append(v)
    return "%.2f to %.2f V (median %.2f V)" % (min(d), max(d), statistics.median(d)) if d else "none"
