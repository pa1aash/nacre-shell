"""Results rows of the redirected screen: the STAGE field, conversion-step rows and the F5 panel (cp4 F1, F4, F5;
theory/claims_redirect.md 2d, 2g, 9d, 9e).

Every row carries ``stage``:

    slurry      K2, K2h, K3, K4 apply (brushite, ACP, HAp; the slurry form of a route product); K1 never in this row
    cell        K1 applies (Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3, the Al-salt rungs, the route products as dried)
    conversion  one row per precursor-to-cell-stage pair: a_w*, T_conv_lit beside the baseline cure range, K2h for an
                aqueous step, and a process status (never a verdict on any condition)

A film is reported across stages only as the chain slurry row, conversion row, cell row sharing one ``film_id``. A
phase used as formed (a Ca orthophosphate at the low-cutoff class, a route product that only dries) carries a slurry
and a cell row of the same phase under one film_id and no conversion row. ``check_presentation`` refuses any other
combination: K1 of a condensed phase and K2 to K4 of an orthophosphate are never one film.

Proceeding (F1): a slurry row's K3 and K4 run unless the film's K1 is falsified at every registered cutoff class
(nacre.screen.kscreen.proceeds); the cell row keeps its verdict.
"""
from nacre.screen import kscreen, routes

STAGES = kscreen.STAGES
ROLES = ("candidate", "route", "comparator", "baseline", "conversion")
K_SLURRY = ("K2", "K2h", "K3", "K4")
CONVERSION_STATUS = ("feasible within the baseline cure range", "requires a higher temperature", "undetermined")


class PresentationError(ValueError):
    """Rows that would present one film across stages without the registered chain."""


# ------------------------------------------------------------------ cell rows (K1)
def k1_cell_row(film_id, phase, k1_by_framing, role, route=None, baked=False, scope_class=None, labels=()):
    """Cell-stage row: K1 per cutoff class and framing, read from the ladder (never recomputed).

    k1_by_framing: {framing: kscreen.k1_for record}. Route products: the amorphous framing governs and the crystalline
    one is the optimistic upper reference (9d); baked baselines report both under `structure unspecified`;
    a candidate with one framing reports that framing. scope_class: the class the row is reported for (F5: the
    low-cutoff class of the Ca orthophosphates), printed; the F1 rule still reads every class.
    """
    framings = sorted(k1_by_framing)
    classes = []
    for f in framings:
        for c in k1_by_framing[f]["by_class"]:
            if c not in classes:
                classes.append(c)
    by_class, labs = {}, list(labels)
    if not classes:
        labs.append("no K1 row in the ladder: K1 undetermined (never passes)")
    for c in classes:
        per = {f: _k1_entry(k1_by_framing[f], c) for f in framings}
        if route is not None or baked:
            gov = routes.route_framing(per.get("crystalline", {}).get("verdict", "undetermined"),
                                       per.get("amorphous", {}).get("verdict", "undetermined"), baked=baked)
            verdict = gov["verdict"]
            for lab in gov["labels"]:
                if lab not in labs:
                    labs.append(lab)
            governing = gov["governing_framing"]
        else:
            governing = framings[0] if len(framings) == 1 else None
            verdict = per[governing]["verdict"] if governing else _worst_framing(per)
        by_class[c] = {"verdict": verdict, "governing_framing": governing, "framings": per}
    gate_framing = "amorphous" if (route is not None and "amorphous" in k1_by_framing) else framings[0] if framings else None
    gate = kscreen.proceeds(k1_by_framing[gate_framing] if gate_framing else {"by_class": {}})
    if baked:
        framing = "structure unspecified"
    elif route is not None:
        framing = "amorphous"
    else:
        framing = framings[0] if len(framings) == 1 else "both"
    return {"row_id": "%s:cell" % film_id, "film_id": film_id, "phase": phase, "stage": "cell", "role": role,
            "route": route, "framing": framing, "scope_class": scope_class,
            "K1": {"by_class": by_class, "source": _source(k1_by_framing),
                   "label": "tier 1 read from the ladder file; not recomputed"},
            "proceeds": gate, "labels": labs, "provisional": True}


def _k1_entry(rec, cls):
    br = (rec.get("bracket") or {}).get(cls) or {"E_ub": None, "E_lb": None, "E_lb_status": "pending",
                                                  "E_ub_status": "pending"}
    return {"verdict": rec["by_class"].get(cls, "undetermined"), "framing": rec["framing"],
            "E_ub": br.get("E_ub"), "E_lb": br.get("E_lb"), "E_ub_status": br.get("E_ub_status", "pending"),
            "E_lb_status": br.get("E_lb_status", "pending")}


def _worst_framing(per):
    vs = {f: e["verdict"] for f, e in per.items()}
    return routes.decision.combine_framings(vs)["verdict"] if all(v in routes.decision.ORDER for v in vs.values()) \
        else "undetermined"


def _source(k1_by_framing):
    for r in k1_by_framing.values():
        return r.get("source")
    return None


# ------------------------------------------------------------------ slurry rows (K2 to K4)
def slurry_row(film_id, phase, role, framing, K2, K3=None, K4=None, K2h=None, route=None, retained_mass=None,
               gate=None, labels=()):
    """Slurry-stage row: K2 (and K2h for a condensed route product), K3 and K4 when the film proceeds (F1)."""
    row = {"row_id": "%s:slurry" % film_id, "film_id": film_id, "phase": phase, "stage": "slurry", "role": role,
           "route": route, "framing": framing, "K2": _brief(K2), "retained_mass": retained_mass,
           "labels": list(labels), "provisional": True}
    if K2h is not None:
        row["K2h"] = K2h
    if gate is not None and not gate["proceeds"]:
        row["K3"] = row["K4"] = {"verdict": "not run", "note": gate["note"], "evidence": {}}
    else:
        if K3 is not None:
            row["K3"] = _brief(K3)
        if K4 is not None:
            row["K4"] = _brief(K4)
    if gate is not None:
        row["gate"] = {"proceeds": gate["proceeds"], "note": gate.get("note")}
    return row


def _brief(rec):
    if rec is None:
        return None
    out = {k: v for k, v in rec.items() if k != "points"}
    out.setdefault("evidence", {})
    return out


# ------------------------------------------------------------------ conversion rows (F4)
def conversion_status(T_conv_lit, T_cure):
    """Process status of a conversion step against the baseline cure range [lo, hi] (K). Not a verdict."""
    if T_conv_lit is None:
        return "undetermined"
    if T_cure is None:
        return "undetermined"
    lo, hi = float(T_cure[0]), float(T_cure[1])
    return "feasible within the baseline cure range" if float(T_conv_lit) <= hi else "requires a higher temperature"


def conversion_row(film_id, precursor, product, a_w_star=None, T_conv_lit=None, T_cure=None, hydrolysis=None,
                   T_eval=None, sources=None):
    """Conversion-step row of one precursor-to-cell-stage pair (claims_redirect.md 2g). Carries no K verdict."""
    status = conversion_status(T_conv_lit, T_cure)
    pos = None
    if T_conv_lit is not None and T_cure is not None:
        lo, hi = float(T_cure[0]), float(T_cure[1])
        pos = "below" if T_conv_lit < lo else "inside" if T_conv_lit <= hi else "above"
    return {"row_id": "%s:conversion:%s-%s" % (film_id, precursor, product), "film_id": film_id, "stage": "conversion",
            "role": "conversion", "framing": None, "phase": "%s -> %s" % (precursor, product), "precursor": precursor, "product": product,
            "a_w_star": a_w_star, "a_w_star_T": T_eval, "T_conv_lit": T_conv_lit, "T_cure_baseline": list(T_cure) if T_cure else None,
            "T_conv_position": pos, "hydrolysis": hydrolysis, "status": status, "sources": sources or {},
            "labels": [] if status != "undetermined" else ["no conversion temperature sourced"], "provisional": True}


# ------------------------------------------------------------------ presentation rule
def check_presentation(rows):
    """Problems of a set of rows against the stage rules (empty when every film is presented as registered)."""
    problems = []
    by_film = {}
    for r in rows:
        st = r.get("stage")
        if st not in STAGES:
            problems.append("%s: stage %r is not one of %s" % (r.get("row_id"), st, STAGES))
            continue
        if st == "cell" and any(k in r for k in K_SLURRY):
            problems.append("%s: a cell-stage row carries K2 to K4" % r["row_id"])
        if st == "slurry" and "K1" in r:
            problems.append("%s: a slurry-stage row carries K1 (only K1_reference is allowed)" % r["row_id"])
        if st == "conversion" and any(k in r for k in ("K1",) + K_SLURRY):
            problems.append("%s: a conversion row carries a K verdict" % r["row_id"])
        by_film.setdefault(r["film_id"], []).append(r)
    for fid, rs in by_film.items():
        slurry = {r["phase"] for r in rs if r["stage"] == "slurry"}
        cell = {r["phase"] for r in rs if r["stage"] == "cell"}
        conv = [(r["precursor"], r["product"]) for r in rs if r["stage"] == "conversion"]
        if len(slurry) > 1 or len(cell) > 1:
            problems.append("%s: more than one slurry or cell phase in one film" % fid)
            continue
        if slurry and cell and slurry != cell and not _chained(next(iter(slurry)), next(iter(cell)), conv):
            problems.append("%s: K1 of %s and K2 to K4 of %s presented as one film without the conversion chain"
                            % (fid, next(iter(cell)), next(iter(slurry))))
    return problems


def _chained(start, end, steps):
    """True when the conversion steps lead from start to end."""
    nxt = dict(steps)
    seen, cur = set(), start
    while cur in nxt and cur not in seen:
        seen.add(cur)
        cur = nxt[cur]
        if cur == end:
            return True
    return False


def chain_summary(rows, film_id):
    """Summary line of one film: the chain is only as strong as its weakest member."""
    rs = [r for r in rows if r["film_id"] == film_id]
    labels = []
    for r in rs:
        if r["stage"] == "conversion" and r["status"] in ("undetermined", "requires a higher temperature"):
            labels.append("conversion %s: %s" % (r["phase"], r["status"]))
    return {"film_id": film_id, "rows": [r["row_id"] for r in rs], "labels": labels,
            "weakest": labels[0] if labels else None}


# ------------------------------------------------------------------ F5 panel
def ortho_low_cutoff_rows(film_id, phase, mineral_record, k1_table, mineral):
    """F5: a Ca orthophosphate used as formed at the low-cutoff class. Splits the kscreen record of one mineral into
    its slurry row (K2 to K4) and its cell row (K1, reported at the low-cutoff class), sharing film_id."""
    low = k1_table.low_cutoff_class(mineral.k1_phase or mineral.name)
    k1 = kscreen.k1_for(k1_table, mineral)
    cell = k1_cell_row(film_id, phase, {k1["framing"] or "crystalline": k1}, "candidate", scope_class=low,
                       labels=["used as formed: frame C applies to the Ca orthophosphates only"])
    adm = _min_retained(mineral_record)
    slurry = slurry_row(film_id, phase, "candidate", mineral.phase_state, mineral_record["K2"],
                        mineral_record.get("K3"), mineral_record.get("K4"), retained_mass=adm, gate=cell["proceeds"],
                        labels=["low-cutoff class %s" % low])
    for k in ("K2", "K3", "K4"):
        if slurry.get(k) is not None:
            slurry[k].setdefault("evidence", {})
    return [slurry, cell]


def _min_retained(rec):
    vals = []
    for k in ("K3", "K4"):
        for a in ((rec.get(k) or {}).get("admissibility") or {}).values():
            if a and a.get("M_adm") is not None:
                vals.append(a)
    if not vals:
        return None
    worst = min(vals, key=lambda a: a["M_adm"])
    return {k: worst.get(k) for k in ("M_adm", "n_evaluable", "n_refused", "inadmissible_inputs", "label")}


def comparator_lipo3_rows(film_id, k1_by_framing, solubility=None, k4=None, grade=None):
    """F5: the (LiPO3)n comparator (Hydro-Quebec chemistry; expected K2 fail, water-soluble). K1, K2, K4 only."""
    k2 = routes.baseline_k2("(LiPO3)n comparator", solubility, hydro_quebec=True, grade=grade)
    k4 = k4 or {"verdict": "undetermined", "evidence": {}, "note": "insulating bound: film thickness not registered"}
    return [slurry_row(film_id, "(LiPO3)n", "comparator", "both", k2, K4=k4,
                       labels=["comparator: no performance claim", "expected K2 fail (water-soluble)"]),
            k1_cell_row(film_id, "(LiPO3)n", k1_by_framing, "comparator", baked=True)]


def baseline_rows(film_id, name, phase, k1_by_framing, k2, k4, hydro_quebec=False):
    """C5 baseline (K1, K2, K4 only; no K3; no performance claim): both framings, `structure unspecified`."""
    s = slurry_row(film_id, phase, "baseline", "structure unspecified", k2, K4=k4,
                   labels=["baseline %s: comparator through K1, K2 and K4 only; no performance claim" % name])
    if hydro_quebec:
        s["labels"].append("film solubility: inference from chemistry, not a patent statement")
    return [s, k1_cell_row(film_id, phase, k1_by_framing, "baseline", baked=True)]


def baseline_k4(d_film, d_max, grade_d_film="gap"):
    """K4 of a baseline (L5): the insulating bound with the patent film thickness; a gap is undetermined."""
    ev = {"matrix_baseline_film_thickness": grade_d_film}
    if d_film is None or d_max is None:
        return {"test": "K4", "row": "L5", "verdict": "undetermined", "evidence": ev,
                "note": "insulating bound: %s is a gap" % ("film thickness" if d_film is None else "d_max")}
    ok = float(d_film) <= float(d_max)
    return {"test": "K4", "row": "L5", "verdict": "feasible" if ok else "falsified", "evidence": ev,
            "d_film": float(d_film), "d_max": float(d_max), "rule": "d_film <= d_max (ohmic insulating bound)"}
