"""Decision layer of a screen run: design points x framings x registered states (cp3 rulings).

For every design point of the R-slurry design axes (configs/preprint/screen.yaml, CP3-R8:
total dissolved Ca dose and C_T) and every registered framing (CP3-R6: calcite and ACC), the
registered states are propagated with common random numbers and the links are evaluated
under the frozen rule (nacre.screen.decision). The results are reduced, in this order:

  1. states   worst state per test, path sum for C3(b), joint masses draw by draw (R7(1));
              a registered state that cannot be propagated is missing (R7(4));
  2. framings falsified only under every framing, feasible under at least one (R6);
  3. design   the common verdict over the design points, else design-dependent (inconclusive
              at the headline) with the point-by-point table; C5's Omega test is reported as
              the dose window (R1).

The prior set is selectable per run and labelled in every output: ``table`` (the parameter
table as bound), ``ignorance`` (the bounded ignorance priors of theory/ignorance_priors.md for
the unmeasured interfacial energies) or ``analog`` (flagged analog priors, side by side). A
verdict that depends on an ignorance prior is never a finding (finding_eligible: false).
Arrays are released after each (point, framing): only the public records are kept.
"""
import itertools

import numpy as np
import yaml

from nacre.screen import chain, decision, params_adapter, propagate
from nacre.screen import units
from nacre.screen.priors import Prior

#: Links whose decisive quantities depend on the gamma_sn ignorance prior (C3, C4) or the C1 comparator.
IGNORANCE_DEPENDENT = {"C3", "C4"}


# ------------------------------------------------------------------ design axes


def _axis_values(spec, resolver, si_unit):
    """Values of one design axis in SI: listed values with a unit, or points of a table key."""
    if "values" in spec:
        if spec["values"] is None:
            raise decision.Gap("design axis has no registered values (%s)" % spec.get("source", "pending"))
        return [(_label(v, spec), units.convert(float(v), spec.get("unit", si_unit), si_unit)) for v in spec["values"]]
    key = spec["params"]
    out = []
    for at in spec.get("at", ["value"]):
        if at == "value":
            v, u = resolver.get(key)
        else:
            v, u = resolver.range(key)[at], resolver.get(key)[1]
        out.append(("%s@%s" % (key, at), units.convert(float(v), u or "1", si_unit)))
    return out


def _label(v, spec):
    return "%g %s" % (float(v), spec.get("unit", ""))


AXIS_UNITS = {"Ca_T": "mol m^-3", "C_T": "mol m^-3", "E_cell_max": "V", "R_A_max": "Ohm m^2", "j_req": "A m^-2"}


def design_points(cfg, resolver, axes=("Ca_T", "C_T")):
    """[(point id, {symbol: SI value}, {axis: label})] of the R-slurry design grid."""
    spec = (cfg.get("design_axes") or {})
    lists = []
    for a in axes:
        if a not in spec:
            return []
        lists.append([(a, lab, v) for lab, v in _axis_values(spec[a], resolver, AXIS_UNITS[a])])
    pts = []
    for combo in itertools.product(*lists):
        pid = "; ".join("%s=%s" % (a, lab) for a, lab, _ in combo)
        pts.append((pid, {a: v for a, _, v in combo}, {a: lab for a, lab, _ in combo}))
    return pts


def control_points(cfg, resolver):
    """W5's registered control states of the Omega test (block v2 C5s.control): {name: (values, labels)}."""
    out = {}
    for name, c in ((cfg.get("omega_control") or {}).get("states") or {}).items():
        vals, labels = {}, {}
        for sym, spec in c.items():
            unit = AXIS_UNITS.get(sym, "1")
            if "value" in spec:
                vals[sym] = units.convert(float(spec["value"]), spec.get("unit", unit), unit)
                labels[sym] = "%g %s" % (spec["value"], spec.get("unit", ""))
            else:
                v = resolver.range(spec["params"])[spec["at"]] if spec["at"] != "value" else resolver.value(spec["params"])
                vals[sym] = units.convert(float(v), resolver.get(spec["params"])[1] or "1", unit)
                labels[sym] = "%s@%s" % (spec["params"], spec["at"])
        out[name] = (vals, labels)
    return out


def _fixed(symbol, value, unit, source):
    return Prior("design:" + symbol, symbol, unit, "fixed", {"value": float(value)}, source)


def _aux(symbol):
    return Prior("aux:" + symbol, symbol, "1", "uniform", {"low": 0.0, "high": 1.0},
                 "ignorance prior auxiliary (theory/ignorance_priors.md)")


# ------------------------------------------------------------------ states


def bindings_for(cfg, regime, framing, state, prior_set):
    """The bindings of one (framing, state) under a prior set, and the injected aux inputs."""
    b = (cfg.get("bindings") or {})[regime]
    bind = {**(b.get("common") or {}), **b["by_framing"][framing], **((b.get("states") or {}).get(state) or {})}
    aux = []
    ps = (cfg.get("prior_sets") or {}).get(prior_set) or {}
    if prior_set == "ignorance":
        for target, (u, pair) in chain.IGNORANCE.items():
            spec = ps.get(target)
            if not spec:
                continue
            for sym, key in spec["bounds"].items():
                bind[sym] = key[framing] if isinstance(key, dict) else key
            bind.pop(target, None)
            if target == "gamma_sn0":
                bind.pop("Delta_gamma_w", None)
            aux.append(_aux(u))
    elif prior_set == "analog":
        if not ps.get("bindings"):
            raise params_adapter.PriorFileError("prior set 'analog': no analog priors are registered in screen.yaml")
        bind.update(ps["bindings"])
    return bind, aux


def bound_table(doc, b):
    """True when the table holds the keys the bindings name (a mock in its own key names is read whole)."""
    if not b:
        return False
    keys = set((b.get("common") or {}).values())
    return bool(keys & set(doc.get("params") or {}))


def load_point(params_path, cfg, framing, design, allow_mock, prior_set="table", truncation=True,
               regime="R-slurry", fixed_inputs=None):
    """[(state, RegimePriors)] of the registered states at one design point and framing."""
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    b = (cfg.get("bindings") or {}).get(regime)
    trunc = {k: (v.get("low"), v.get("high")) for k, v in ((cfg.get("registrations") or {}).get("truncate") or {}).items()} \
        if truncation else {}
    if doc["mock"] and not bound_table(doc, b):
        return [("default", params_adapter.regime_priors(params_path, regime, allow_mock))]
    out = []
    for state, sb in (b.get("states") or {"default": {}}).items():
        bind, aux = bindings_for(cfg, regime, framing, state, prior_set)
        extra = list(aux)
        fixed = {**((sb or {}).get("_fixed") or {}), **(fixed_inputs or {})}
        bind = {k: v for k, v in bind.items() if not str(k).startswith("_") and k not in design and k not in fixed}
        for sym, v in design.items():
            extra.append(_fixed(sym, v, AXIS_UNITS.get(sym, "1"), "design axis"))
        for sym, v in fixed.items():
            extra.append(_fixed(sym, v, params_adapter.symbol_units().get(sym, "1"), "registered state value"))
        out.append((state, params_adapter.regime_priors(params_path, regime, allow_mock, bindings=bind, absent="gap",
                                                        truncate=trunc, extra=extra)))
    return out


def propagate_states(states, n, seed, chunk):
    """{state: chain outputs} with common random numbers; also the uncoupled-state notes."""
    outs, notes = {}, []
    if not states:
        return outs, notes
    symbols = [tuple(rp.joint.symbols) for _, rp in states]
    keys = [tuple(rp.joint.names) for _, rp in states]
    coupled = len(set(symbols)) == 1
    specific = {s for i, s in enumerate(symbols[0]) if len({k[i] for k in keys}) > 1} if coupled else set()
    if not coupled:
        notes.append("states have different input sets: draws are not coupled across states")
    seqs = np.random.SeedSequence(seed).spawn(len(states) + 1)
    for (sid, rp), sq in zip(states, seqs[1:]):
        if not chain.evaluable_links(rp.joint.symbols):
            continue
        common = int(seqs[0].generate_state(1)[0]) if coupled else int(sq.generate_state(1)[0])
        o, masses = propagate.propagate_chain(chain.evaluate, rp.joint, n, common, chunk,
                                              redraw=tuple(specific), redraw_seed=int(sq.generate_state(1)[0]))
        outs[sid] = (o, masses, rp)
    return outs, notes


def state_samples(outputs):
    """Decision-rule samples of one state: the chain outputs keyed by quantity."""
    s = {}
    for q, (link, name) in decision.QUANTITY_SOURCE.items():
        if link in outputs and name in outputs[link] and np.any(np.isfinite(outputs[link][name])):
            s[q] = outputs[link][name]
    if "nucleate" in outputs:
        for q in ("cos_theta", "gamma_sl_minus_nl", "Omega_bulk"):
            s[q] = outputs["nucleate"][q]
    return s


# ------------------------------------------------------------------ claims at one (point, framing)


#: The chain inputs each link needs (before derive: the speciation and ignorance steps supply some).
LINK_NEEDS = {"C1": chain.PMF_INPUTS,
              "C2": ("Delta_G_site", "pKa", "pH", "T", "c_bulk", "Gamma_s", "delta_s"),
              "C3": chain.NUC_BASE + ("gamma_sl0", "J0_het", "t_proc", "Delta_G_site", "pKa", "c_bulk", "Gamma_s",
                                      "delta_s"),
              "C4": chain.NUC_BASE + ("gamma_sl0", "J0_het", "t_proc", "Delta_G_site", "pKa", "c_bulk", "Gamma_s",
                                      "delta_s")}


def _reason(sym, rp, have):
    """Why a needed input is absent: its table reason, or the gaps of the step that derives it."""
    if sym in rp.unsampled:
        return rp.unsampled[sym]
    upstream = None
    if sym in ("a_Ca", "a_CO3", "c_bulk"):
        upstream = [s for s in chain.SPECIATION_INPUTS if s not in have]
        step = "speciation (contract v3)"
    elif sym in ("gamma_sn0", "Delta_gamma_w"):
        u, pair = chain.IGNORANCE["gamma_sn0"]
        upstream = [s for s in (u,) + pair if s not in have]
        step = "the gamma_sn ignorance prior"
    if upstream:
        return "derived by %s, which lacks %s" % (step, {s: rp.unsampled.get(s, "not bound") for s in upstream})
    return "not bound"


def link_gaps(states, claim):
    """{state: {symbol: reason}} of the inputs a link needs that a state does not supply."""
    out = {}
    for sid, rp in states:
        have = chain.derived_symbols(rp.joint.symbols)
        miss = {s: _reason(s, rp, set(rp.joint.symbols)) for s in LINK_NEEDS[claim] if s not in have}
        if miss:
            out[sid] = miss
    return out


def claims_at(rule, resolver, outs, registered, d_max=None, rng=None, states=None):
    """C1 to C4 at one design point and framing ({state: (outputs, masses, rp)})."""
    states = {sid: state_samples(o) for sid, (o, _, _) in outs.items()}
    claims = {}
    need = {"C1": {"W_adh_wet"}, "C3": {"f_theta", "N_nuc"}, "C4": {"S_spread", "N_nuc", "cos_theta"}}
    for claim, q in need.items():
        have = {sid: s for sid, s in states.items() if q <= set(s)}
        if not have:
            missing = sorted(q - set().union(*[set(s) for s in states.values()])) if states else sorted(q)
            claims[claim] = {"verdict": "inconclusive", "tests": {}, "falsified_mass": None, "role": "gating",
                             "gap": "not evaluable: no registered state supplies %s; missing inputs %s"
                                    % (missing, link_gaps(states or [], claim))}
            continue
        claims[claim] = decision.evaluate_link(rule, claim, have, resolver, registered_states=registered,
                                               d_max=d_max if claim == "C4" else None, rng=rng)
    seq = {sid: s for sid, s in states.items() if "Delta_G_seq" in s}
    claims["C2"] = decision.evaluate_c2(rule, seq, resolver) if seq else \
        {"verdict": "descriptor", "role": "descriptor", "tests": {}, "falsified_mass": None,
         "gap": "not evaluable: Delta_G_seq is not supplied; missing inputs %s" % link_gaps(states or [], "C2")}
    return claims


def omega_point(outs, p):
    """Omega_bulk >= 1 at one design point: worst over the registered states (CP3-R1)."""
    per = {}
    for sid, (o, _, _) in outs.items():
        om = None
        if "nucleate" in o and np.any(np.isfinite(o["nucleate"]["Omega_bulk"])):
            om = o["nucleate"]["Omega_bulk"]
        if om is not None:
            per[sid] = decision.evaluate_omega_point(om, p)
            if "speciation" in o:            # a grid in total calcium: print the speciated a_Ca beside it
                per[sid]["a_Ca_median"] = _median(o["speciation"]["a_Ca"])
                per[sid]["a_CO3_median"] = _median(o["speciation"]["a_CO3"])
    if not per:
        return None
    sid = max(per, key=lambda k: decision.ORDER.index(per[k]["verdict"]))
    return {**per[sid], "state": sid, "by_state": {k: v["verdict"] for k, v in per.items()}}


def _median(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else None


# ------------------------------------------------------------------ the run


def evaluate(rule, resolver, params_path, cfg, allow_mock=False, prior_set="table", truncation=True,
             draws=None, seed=0, chunk=None, framings=None, stability=None, cells=None, controls=None,
             d_max_rng_seed=1):
    """Claims and the study verdict over the design points and framings; returns (claims, study, extra).

    controls: {control: parameter table} of the deletion test (bare_oxide, PVDF), rerun at the
    same design points, framings and states; the deletion test is formed per framing at every
    point (block v2, study.framings). extra carries the dose window and the gaps.
    """
    pc = cfg["propagation"]
    n = int(draws or pc["draws_per_regime"])
    chunk = int(chunk or pc["chunk"])
    framings = list(framings or (rule.get("study", {}).get("framings") or {}).get("registered")
                    or (cfg.get("registrations") or {}).get("framings") or ["calcite"])
    p = decision.credible_level(rule, resolver)
    try:
        points = design_points(cfg, resolver) or [("table", {}, {})]
        gap = None
    except decision.Gap as exc:
        points, gap = [("table", {}, {})], str(exc)
    rng = np.random.default_rng(np.random.SeedSequence([seed, 7]))
    by_point, omega_pts, omega_sens = {}, {}, {}
    seeds = np.random.SeedSequence(seed).spawn(len(points) * len(framings) + 3)
    k = 0
    c4s = next(t for t in rule["links"]["C4"]["tests"] if t["id"] == "C4s")
    try:
        d_max, d_flags = decision.d_max_draws(c4s, resolver, n, np.random.default_rng(d_max_rng_seed))
    except decision.Gap as exc:
        d_max, d_flags = None, ["d_max not evaluable: %s" % exc]

    def run_point(table, fr, design, sd, mock_ok):
        states = load_point(table, cfg, fr, design, mock_ok, prior_set, truncation)
        outs, notes = propagate_states(states, n, sd, chunk)
        cl = claims_at(rule, resolver, outs, [sid for sid, _ in states], d_max, rng, states) if outs else \
            {c: {"verdict": "inconclusive" if c != "C2" else "descriptor", "tests": {}, "falsified_mass": None,
                 "role": "gating" if c != "C2" else "descriptor",
                 "gap": "not evaluable; missing inputs %s" % link_gaps(states, c)} for c in ("C1", "C2", "C3", "C4")}
        return states, outs, notes, cl

    for pid, design, labels in points:
        per_f = {}
        for fr in framings:
            sd = int(seeds[k].generate_state(1)[0])
            k += 1
            states, outs, notes, cl = run_point(params_path, fr, design, sd, allow_mock)
            om = omega_point(outs, p)
            if fr == "calcite" and om is not None:
                omega_pts[pid] = {"axes": labels, **om}
            elif om is not None:
                omega_sens.setdefault("C5s_ACC: Omega_bulk under the %s framing (labelled, not gating)" % fr, {})[pid] = \
                    {"axes": labels, **om}
            ctl_claims = {}
            for name, table in (controls or {}).items():
                ctl_claims[name] = run_point(table, fr, design, sd, False)[3]
            per_f[fr] = {"claims": cl, "controls": ctl_claims, "notes": notes, "unsampled": _unsampled(states)}
            del outs
        by_point[pid] = {"axes": labels, "framings": per_f}
    ctl = {}
    for name, cp in _safe_controls(cfg, resolver).items():
        if isinstance(cp, str):
            ctl[name] = {"axes": {}, "verdict": "inconclusive", "gap": cp}
            continue
        ctl[name] = _control(params_path, cfg, allow_mock, prior_set, truncation, n, chunk,
                             int(seeds[-1].generate_state(1)[0]), p, *cp)
    omega = decision.omega_window(omega_pts, p, decision.control_outcomes(ctl), omega_sens) if omega_pts else None
    return assemble(rule, resolver, by_point, omega, stability, cells, framings, prior_set, cfg, gap, d_flags)


def _unsampled(states):
    return {sid: dict(rp.unsampled) for sid, rp in states}


def _safe_controls(cfg, resolver):
    """{control: (values, labels) or the Gap message} of the registered control states."""
    out = {}
    for name in ((cfg.get("omega_control") or {}).get("states") or {}):
        one = {"omega_control": {"states": {name: cfg["omega_control"]["states"][name]}}}
        try:
            out[name] = control_points(one, resolver)[name]
        except decision.Gap as exc:
            out[name] = str(exc)
    return out


def _control(params_path, cfg, allow_mock, prior_set, truncation, n, chunk, seed, p, vals, labels):
    design = {k: v for k, v in vals.items() if k in AXIS_UNITS}
    fixed = {k: v for k, v in vals.items() if k not in AXIS_UNITS}
    states = load_point(params_path, cfg, "calcite", design, allow_mock, prior_set, truncation, fixed_inputs=fixed)
    outs, _ = propagate_states(states, n, seed, chunk)
    om = omega_point(outs, p)
    if om is None:
        return {"axes": labels, "verdict": "inconclusive",
                "gap": "Omega_bulk not evaluable at the control: %s" % _unsampled(states)}
    return {"axes": labels, **om}


def assemble(rule, resolver, by_point, omega, stability, cells, framings, prior_set, cfg, gap=None, d_flags=()):
    """Reduce (states done) over framings then design points; C5 and the study per point and framing."""
    reg = cfg.get("registrations") or {}
    cell_reg = reg.get("R-cell") or {}
    p = decision.credible_level(rule, resolver)
    cutoffs = None
    try:
        e_axis = (cfg.get("design_axes") or {}).get("E_cell_max")
        if e_axis:
            cutoffs = {"oxidation": dict(_axis_values(e_axis, resolver, "V"))}
    except decision.Gap:
        cutoffs = None
    point_ids = list(by_point)
    study_by_point, link_by_point = {}, {c: {} for c in ("C1", "C2", "C3", "C4", "C5")}
    for pid in point_ids:
        studies = {}
        for fr, fd in by_point[pid]["framings"].items():
            om_pt = (omega or {}).get("dose_window", {}).get("points", {}).get(pid) if omega else None
            om_rec = decision.omega_window({pid: om_pt}, p, (omega or {}).get("controls")) if om_pt else None
            pb = (stability or {}).get("R-slurry") if isinstance(stability, dict) else None

            def c5_of(_):
                return decision.evaluate_c5(rule, resolver, omega=om_rec, pourbaix=pb, cells=cells, framing=fr,
                                            cutoffs=cutoffs, never_pass_sinks=tuple(cell_reg.get("never_pass_sinks") or ()))
            fd["claims"]["C5"] = c5_of(None)
            deletion = None
            if fd["controls"]:
                for cc in fd["controls"].values():
                    cc["C5"] = fd["claims"]["C5"]
                deletion = decision.deletion_test(rule, fd["claims"], fd["controls"], resolver)
            studies[fr] = decision.study_verdict(rule, fd["claims"], deletion)
            fd["claims"] = {c: decision.public(r) for c, r in fd["claims"].items()}
            fd["controls"] = {k: {c: {"verdict": r["verdict"], "falsified_mass": r.get("falsified_mass")}
                                  for c, r in cc.items()} for k, cc in fd["controls"].items()}
        for c in link_by_point:
            link_by_point[c][pid] = decision.combine_framings(
                {fr: by_point[pid]["framings"][fr]["claims"][c] for fr in by_point[pid]["framings"]}) if c != "C2" else \
                {fr: (by_point[pid]["framings"][fr]["claims"]["C2"].get("finding") or {}).get("statement")
                 for fr in by_point[pid]["framings"]}
        study_by_point[pid] = decision.combine_framings(studies)
        study_by_point[pid]["deletion_by_framing"] = {fr: s.get("deletion_test") for fr, s in studies.items()}
    primary = _primary(point_ids, by_point)
    claims = {}
    eligible = prior_set != "ignorance"
    for c in ("C1", "C2", "C3", "C4", "C5"):
        detail = dict(by_point[primary]["framings"][framings[0]]["claims"][c])
        if c == "C2":
            claims[c] = {**detail, "by_design": link_by_point[c]}
            continue
        head = decision.over_design({pid: r["verdict"] for pid, r in link_by_point[c].items()})
        claims[c] = {**detail, "verdict": head["verdict"], "design_dependent": head["design_dependent"],
                     "by_design": link_by_point[c], "detail_point": primary, "detail_framing": framings[0],
                     "prior_set": prior_set,
                     "finding_eligible": eligible or c not in IGNORANCE_DEPENDENT}
        if c == "C5" and omega is not None:
            claims[c]["dose_window"] = omega["dose_window"]
            claims[c]["omega_controls"] = omega.get("controls")
    head = decision.over_design({pid: r["verdict"] for pid, r in study_by_point.items()})
    gating = rule["study"].get("gating_links") or ["C1", "C3", "C4", "C5"]
    deletions = [d for r in study_by_point.values() for d in r["deletion_by_framing"].values()]
    study = {"verdict": head["verdict"], "links": {c: claims[c]["verdict"] for c in gating},
             "deletion_test": deletions[0] if len(deletions) == 1 else ({"by_point": {pid: r["deletion_by_framing"]
                                                                                       for pid, r in study_by_point.items()}}
                                                                        if any(deletions) else None),
             "framing": None, "gating_links": list(gating), "design_dependent": head["design_dependent"],
             "by_design": study_by_point, "framings": list(framings), "prior_set": prior_set,
             "finding_eligible": eligible,
             "sequestration_premise": link_by_point["C2"].get(primary, {}).get(framings[0])}
    if any(d is not None and not d["holds"] for d in deletions):
        study["framing"] = "generic adhesion study"
    extra = {"design_gap": gap, "d_max_flags": list(d_flags), "omega": omega, "points": point_ids,
             "unsampled": {pid: {fr: fd["unsampled"] for fr, fd in by_point[pid]["framings"].items()}
                           for pid in point_ids}}
    return claims, study, extra


def _primary(point_ids, by_point):
    """The central design point (middle of the list), whose detailed records are kept."""
    return point_ids[len(point_ids) // 2]


def load_cells(paths):
    """{sink: R-cell section} from W5's per-sink stability documents (schema v2 or v3)."""
    import json
    from pathlib import Path
    cells = {}
    for path in paths or ():
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        cell = (doc.get("stability") or {}).get("R-cell")
        if cell:
            sink = cell.get("sink_assumption", {}).get("active") or Path(path).stem
            cells[sink] = cell
    return cells


def config_registrations(cfg):
    return yaml.safe_dump(cfg.get("registrations") or {}, sort_keys=True)
