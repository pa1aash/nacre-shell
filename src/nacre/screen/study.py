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
import dataclasses
import itertools
import time

import numpy as np
import yaml

from nacre.screen import admissibility, chain, decision, params_adapter, propagate
from nacre.screen import units
from nacre.screen.priors import Prior

#: Links whose decisive quantities depend on the gamma_sn ignorance prior (C3, C4) or the C1 comparator.
IGNORANCE_DEPENDENT = {"C3", "C4"}


# ------------------------------------------------------------------ design axes


def _key_points(key, ats, resolver, si_unit, label=None):
    out = []
    for at in ats:
        if at == "value":
            v, u = resolver.get(key)
        else:
            v, u = resolver.range(key)[at], resolver.get(key)[1]
        out.append(("%s@%s" % (label or key, at), units.convert(float(v), u or "1", si_unit)))
    return out


def _axis_values(spec, resolver, si_unit):
    """Values of one design axis in SI: listed values with a unit, points of a table key, a list of
    labelled points (a registered value or a table point), or table keys per class (cathode class)."""
    if "classes" in spec:
        out = []
        for label, key in spec["classes"].items():
            out += _key_points(key, spec.get("at", ["value"]), resolver, si_unit, label)
        return out
    if "points" in spec:
        out = []
        for pt in spec["points"]:
            if "value" in pt:
                out.append((pt["label"], units.convert(float(pt["value"]), pt.get("unit", si_unit), si_unit)))
            else:
                out += [(pt["label"], v) for _, v in _key_points(pt["params"], [pt["at"]], resolver, si_unit)]
        return out
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


AXIS_UNITS = {"Ca_T": "mol m^-3", "C_T": "mol m^-3", "E_cell_max": "V", "R_A_max": "Ohm m^2", "j_req": "A m^-2",
              "a_w": "1", "Al_T": "mol m^-3"}
#: The axes of the R-slurry chain grid, in order; an axis absent from screen.yaml is skipped, except
#: the first two (the gap policy's dose axes), without which there is no grid.
CHAIN_AXES = ("Ca_T", "C_T", "a_w")


def design_points(cfg, resolver, axes=None):
    """[(point id, {symbol: SI value}, {axis: label})] of the R-slurry design grid.

    An axis with ``state: <id>`` applies to that registered state only; its symbol is keyed
    ``<symbol>@<state>`` in the point (gap_resolution.yaml: a_w at the drying state).
    """
    spec = (cfg.get("design_axes") or {})
    axes = list(axes) if axes is not None else [a for i, a in enumerate(CHAIN_AXES) if i < 2 or spec.get(a)]
    lists = []
    for a in axes:
        if a not in spec:
            return []
        sym = a + ("@" + spec[a]["state"] if spec[a].get("state") else "")
        lists.append([(a, sym, lab, v) for lab, v in _axis_values(spec[a], resolver, AXIS_UNITS[a])])
    pts = []
    for combo in itertools.product(*lists):
        pid = "; ".join("%s=%s" % (a, lab) for a, _, lab, _ in combo)
        pts.append((pid, {sym: v for _, sym, _, v in combo}, {a: lab for a, _, lab, _ in combo}))
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


def _by_framing(key, framing):
    return key[framing] if isinstance(key, dict) else key


def bindings_for(cfg, regime, framing, state, prior_set, control=None):
    """The bindings of one (framing, state) under a prior set, and the injected aux inputs.

    prior_set ``ignorance`` applies the gap table's ignorance, geometry and analog treatments
    (configs/preprint/gap_resolution.yaml, as bound in screen.yaml). control: a deletion-test
    control of screen.yaml ``controls`` (the template inputs it drops, the surface it binds and
    the aux uniforms of its ignorance priors).
    """
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
                bind[sym] = _by_framing(key, framing)
            bind.pop(target, None)
            if target == "gamma_sn0":
                bind.pop("Delta_gamma_w", None)
            aux.append(_aux(u))
        geo = ps.get("delta_s")
        if geo:
            for sym, key in geo["bounds"].items():
                bind[sym] = _by_framing(key, framing)
            bind.pop("delta_s", None)
            aux.append(_aux(chain.GEOMETRY[0]))
        for sym, key in (ps.get("analogs") or {}).items():
            bind[sym] = _by_framing(key, framing)
        for sym, key in (ps.get("analog_route") or {}).items():     # AM3: the two-proton cycle (thresholds C2)
            bind[sym] = _by_framing(key, framing)
        for sym in ps.get("drop") or ():
            bind.pop(sym, None)
    elif prior_set == "analog":
        if not ps.get("bindings"):
            raise params_adapter.PriorFileError("prior set 'analog': no analog priors are registered in screen.yaml")
        bind.update(ps["bindings"])
    if control is not None:
        for sym in control.get("drop") or ():
            bind.pop(sym, None)
        for sym, key in (control.get("bind") or {}).items():
            bind[sym] = _by_framing(key, framing)
        aux += [_aux(u) for u in control.get("aux") or ()]
    return bind, aux


def bound_table(doc, b):
    """True when the table holds the keys the bindings name (a mock in its own key names is read whole)."""
    if not b:
        return False
    keys = set((b.get("common") or {}).values())
    return bool(keys & set(doc.get("params") or {}))


def load_point(params_path, cfg, framing, design, allow_mock, prior_set="table", truncation=True,
               regime="R-slurry", fixed_inputs=None, control=None, independence=False):
    """[(state, RegimePriors)] of the registered states at one design point and framing.

    A design symbol keyed ``<symbol>@<state>`` applies to that state only. independence: the
    stated correlations are dropped (the dependence sweep).
    """
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    b = (cfg.get("bindings") or {}).get(regime)
    trunc = {k: (v.get("low"), v.get("high")) for k, v in ((cfg.get("registrations") or {}).get("truncate") or {}).items()} \
        if truncation else {}
    if doc["mock"] and not bound_table(doc, b):
        return [("default", params_adapter.regime_priors(params_path, regime, allow_mock))]
    out = []
    for state, sb in (b.get("states") or {"default": {}}).items():
        bind, aux = bindings_for(cfg, regime, framing, state, prior_set, control)
        extra = list(aux)
        here = {k.split("@")[0]: v for k, v in design.items() if "@" not in k or k.split("@")[1] == state}
        fixed = {k: v for k, v in {**((sb or {}).get("_fixed") or {}), **(fixed_inputs or {})}.items() if k not in here}
        bind = {k: v for k, v in bind.items() if not str(k).startswith("_") and k not in here and k not in fixed}
        for sym, v in here.items():
            extra.append(_fixed(sym, v, AXIS_UNITS.get(sym, "1"), "design axis"))
        for sym, v in fixed.items():
            extra.append(_fixed(sym, v, params_adapter.symbol_units().get(sym, "1"), "registered state value"))
        rp = params_adapter.regime_priors(params_path, regime, allow_mock, bindings=bind, absent="gap",
                                          truncate=trunc, extra=extra)
        if independence:
            rp = dataclasses.replace(rp, joint=rp.joint.independent())
        out.append((state, rp))
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
    for q, (link, name) in {**decision.QUANTITY_SOURCE, **{v: ("anchor", v) for v in C1_SIDE_BY_SIDE.values()}}.items():
        if link in outputs and name in outputs[link] and np.any(np.isfinite(outputs[link][name])):
            s[q] = outputs[link][name]
    if "nucleate" in outputs:
        for q in ("cos_theta", "gamma_sl_minus_nl", "Omega_bulk", "gamma_sl_insitu", "Pi_ads", "gamma_sl_floor",
                  "r_ads", "branch_favourable"):
            s[q] = outputs["nucleate"][q]
    if "sequester" in outputs:
        s["Theta_occ"] = outputs["sequester"]["Theta_occ"]
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


#: C1 results run beside the PMF route (gap_resolution.yaml c1.side_by_side): id -> decisive quantity.
C1_SIDE_BY_SIDE = {"C1_analog": "W_adh_wet_analog", "C1_dupre": "W_adh_wet_comparator"}


def _rule_with_quantity(rule, claim, quantity):
    """A copy of the rule whose single-test link reads another quantity (same edge and comparator)."""
    link = dict(rule["links"][claim])
    link["tests"] = [dict(link["tests"][0], quantity=quantity)]
    return dict(rule, links=dict(rule["links"], **{claim: link}))


def c1_side_by_side(rule, resolver, states, registered, rng):
    """C1 under the flagged analog and the Dupre estimate (ignorance priors), each by the C1 rule."""
    out = {}
    for sid, q in C1_SIDE_BY_SIDE.items():
        have = {s: dict(v, W_adh_wet=v[q]) for s, v in states.items() if q in v}
        if not have:
            continue
        rec = decision.evaluate_link(_rule_with_quantity(rule, "C1", "W_adh_wet"), "C1", have, resolver,
                                     registered_states=registered, rng=rng)
        rec["quantity"] = q
        rec["label"] = ("conditional on the flagged analog w_adh_wet_catechol_oxide_analog" if sid == "C1_analog"
                        else "Dupre estimate gamma_ow + gamma_pw - gamma_op under ignorance priors: never a finding")
        rec["finding_eligible"] = False
        out[sid] = rec
    return out


def claims_at(rule, resolver, outs, registered, d_max=None, rng=None, loaded=None, admissible=False):
    """C1 to C4 at one design point and framing ({state: (outputs, masses, rp)}).

    admissible: apply the admissibility rule (thresholds block v4, decision.admissibility; AM3) to C3
    and C4: their verdicts use the admitted draws, the unrestricted verdict on the same draws is kept
    beside, and M_adm is printed (nacre.screen.admissibility).
    """
    states = {sid: state_samples(o) for sid, (o, _, _) in outs.items()}
    m = admissibility.mask(states) if admissible else None
    adm = admissibility.summary(states, m, decision.credible_level(rule, resolver)) if m is not None else None
    claims = {}
    need = {"C1": {"W_adh_wet"}, "C3": {"f_theta", "N_nuc"}, "C4": {"S_spread", "N_nuc", "cos_theta"}}
    for claim, q in need.items():
        have = {sid: s for sid, s in states.items() if q <= set(s)}
        if not have:
            missing = sorted(q - set().union(*[set(s) for s in states.values()])) if states else sorted(q)
            claims[claim] = {"verdict": "inconclusive", "tests": {}, "falsified_mass": None, "role": "gating",
                             "gap": "not evaluable: no registered state supplies %s; missing inputs %s"
                                    % (missing, link_gaps(loaded or [], claim))}
            continue
        kw = dict(registered_states=registered, d_max=d_max if claim == "C4" else None, rng=rng)
        if adm is not None and claim in ("C3", "C4"):
            restricted = decision.evaluate_link(rule, claim, admissibility.restrict(have, m), resolver, **kw)
            claims[claim] = admissibility.apply(restricted, decision.evaluate_link(rule, claim, have, resolver, **kw),
                                                adm)
            continue
        claims[claim] = decision.evaluate_link(rule, claim, have, resolver, **kw)
    side = c1_side_by_side(rule, resolver, states, registered, rng)
    if side:
        claims["C1"]["side_by_side"] = side
    claims["C1"]["terminations"] = {"registered": [], "resolved_by_inputs": False,
                                    "note": "no P0 input is resolved by termination and none is registered: the "
                                            "per-termination verdicts and the flat-Dirichlet mixture equal the pooled "
                                            "verdict (gap_resolution.yaml, termination_weights)"}
    seq = {sid: s for sid, s in states.items() if "Delta_G_seq" in s}
    claims["C2"] = decision.evaluate_c2(rule, seq, resolver) if seq else \
        {"verdict": "descriptor", "role": "descriptor", "tests": {}, "falsified_mass": None,
         "gap": "not evaluable: Delta_G_seq is not supplied; missing inputs %s" % link_gaps(loaded or [], "C2")}
    if adm is not None and seq:
        claims["C2"]["admissibility"] = dict(admissibility.descriptor(seq, m), M_adm=adm["M_adm"])
    if adm is not None:
        claims["_mechanism"] = admissibility.mechanism(states, m)
    return claims


def omega_point(outs, p):
    """Omega_bulk >= 1 at one design point: worst over the registered states (CP3-R1)."""
    per = {}
    for sid, (o, _, _) in outs.items():
        om = None
        for lk in ("nucleate", "speciation"):        # the same quantity; speciation alone suffices (C5s)
            if lk in o and "Omega_bulk" in o[lk] and np.any(np.isfinite(o[lk]["Omega_bulk"])):
                om = o[lk]["Omega_bulk"]
                break
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
             d_max_rng_seed=1, independence=False, admissible=None):
    """Claims and the study verdict over the design points and framings; returns (claims, study, extra).

    controls: names of the deletion-test controls of screen.yaml ``controls`` (bare_oxide, PVDF),
    rerun at the same design points, framings and states; the deletion test is formed per framing
    at every point (block v2, study.framings). A control registered as a gap is reported as not
    evaluable. stability: {(Ca label, C_T tag): {Al label: R-slurry section}} of W5's documents, or
    one section for every point. extra carries the dose window, the gaps and the largest band-mass
    half-width over every record (the sizing rule).
    """
    pc = cfg["propagation"]
    if admissible is None:
        admissible = bool((cfg.get("registrations") or {}).get("admissibility"))
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
    ctl_specs = {c: (cfg.get("controls") or {}).get(c) for c in (controls or ())}
    widths = []

    def run_point(fr, design, sd, control=None):
        states = load_point(params_path, cfg, fr, design, allow_mock, prior_set, truncation, control=control,
                            independence=independence)
        outs, notes = propagate_states(states, n, sd, chunk)
        cl = claims_at(rule, resolver, outs, [sid for sid, _ in states], d_max, rng, states, admissible) if outs else \
            {c: {"verdict": "inconclusive" if c != "C2" else "descriptor", "tests": {}, "falsified_mass": None,
                 "role": "gating" if c != "C2" else "descriptor",
                 "gap": "not evaluable; missing inputs %s" % link_gaps(states, c)} for c in ("C1", "C2", "C3", "C4")}
        widths.append(max_half_width(cl))
        return states, outs, notes, cl

    for pid, design, labels in points:
        per_f = {}
        for fr in framings:
            sd = int(seeds[k].generate_state(1)[0])
            k += 1
            states, outs, notes, cl = run_point(fr, design, sd)
            om = omega_point(outs, p)
            if fr == "calcite" and om is not None:
                omega_pts[pid] = {"axes": labels, **om}
            elif om is not None:
                omega_sens.setdefault("C5s_ACC: Omega_bulk under the %s framing (labelled, not gating)" % fr, {})[pid] = \
                    {"axes": labels, **om}
            for r in (om,):
                if r is not None and r.get("half_width") is not None:
                    widths.append(r["half_width"])
            ctl_claims = {}
            for name, spec in ctl_specs.items():
                if not spec or spec.get("gap"):
                    msg = (spec or {}).get("gap") or "control not registered in screen.yaml"
                    ctl_claims[name] = {c: {"verdict": "inconclusive", "tests": {}, "falsified_mass": None,
                                            "gap": "control not evaluable: %s" % msg} for c in ("C1", "C2", "C3", "C4")}
                    ctl_claims[name]["_gap"] = msg
                    continue
                ctl_claims[name] = run_point(fr, design, sd, spec)[3]
            mech = cl.pop("_mechanism", None)
            for cc in ctl_claims.values():
                cc.pop("_mechanism", None)
            per_f[fr] = {"claims": cl, "controls": ctl_claims, "notes": notes, "unsampled": _unsampled(states),
                         "mechanism": mech}
            del outs
        by_point[pid] = {"axes": labels, "design": design, "framings": per_f}
    ctl = {}
    for name, cp in _safe_controls(cfg, resolver).items():
        if isinstance(cp, str):
            ctl[name] = {"axes": {}, "verdict": "inconclusive", "gap": cp}
            continue
        ctl[name] = _control(params_path, cfg, allow_mock, prior_set, truncation, n, chunk,
                             int(seeds[-1].generate_state(1)[0]), p, *cp)
        if ctl[name].get("half_width") is not None:
            widths.append(ctl[name]["half_width"])
    omega = decision.omega_window(omega_pts, p, decision.control_outcomes(ctl), omega_sens) if omega_pts else None
    claims, study, extra = assemble(rule, resolver, by_point, omega, stability, cells, framings, prior_set, cfg, gap,
                                    d_flags, admissible)
    if claims["C1"].get("side_by_side"):
        claims["C1"]["side_by_side"]["gamma_pw_consistency"] = gamma_pw_consistency(cfg, resolver)
    ws = [w for w in widths if w is not None and np.isfinite(w)]
    extra["max_band_half_width"] = max(ws) if ws else None
    extra["draws"] = n
    return claims, study, extra


def gamma_pw_consistency(cfg, resolver):
    """ignorance_priors.md 1d: gamma_pw (= gamma_sl0) <= gamma_p + gamma_w over the whole sourced spans."""
    b = (cfg.get("bindings") or {}).get("R-slurry") or {}
    ign = ((cfg.get("prior_sets") or {}).get("ignorance") or {})
    keys = {"gamma_pw": (b.get("common") or {}).get("gamma_sl0"),
            "gamma_p": ((ign.get("gamma_sn0") or {}).get("bounds") or {}).get("gamma_p"),
            "gamma_w": ((ign.get("gamma_ow") or {}).get("bounds") or {}).get("gamma_w")}
    try:
        top = resolver.range(keys["gamma_pw"])["max"]
        low = resolver.range(keys["gamma_p"])["min"] + resolver.range(keys["gamma_w"])["min"]
    except (decision.Gap, TypeError):
        return {"checked": False, "keys": keys}
    return {"checked": True, "holds_over_the_spans": bool(top <= low), "gamma_pw_max": float(top),
            "gamma_p_plus_gamma_w_min": float(low), "keys": keys, "rule": "ignorance_priors.md 1d (consistency check)"}


def max_half_width(record):
    """Largest band-mass half-width anywhere in a record (None when there is none)."""
    best = None
    if isinstance(record, dict):
        for k, v in record.items():
            if k == "half_width" and isinstance(v, (int, float)) and np.isfinite(v):
                best = v if best is None else max(best, v)
            elif isinstance(v, (dict, list)):
                m = max_half_width(v)
                if m is not None:
                    best = m if best is None else max(best, m)
    elif isinstance(record, list):
        for v in record:
            m = max_half_width(v)
            if m is not None:
                best = m if best is None else max(best, m)
    return best


def evaluate_sized(rule, resolver, params_path, cfg, allow_mock=False, prior_set="table", truncation=True, **kw):
    """The decision layer under the sizing rule (thresholds, cp2; gap_resolution.yaml sizing).

    The draws per state start at ``sizing.start`` and are doubled until the largest band-mass
    half-width (twice the binomial standard error) over every record is at most the registered
    target, or until a cap binds: the draw cap (``sizing.draw_cap`` per state) or the wall-clock
    cap (``sizing.wall_clock_s``; the next doubling is not started when it would exceed it,
    taking it as twice the last run). A capped run is reported as capped with the half-width reached.
    """
    sz = cfg.get("sizing") or {}
    target = float(sz.get("band_mass_half_width_max", 0.01))
    cap = min(int(sz.get("draw_cap", cfg["propagation"]["draws_per_regime"])), int(cfg["propagation"]["draws_per_regime"]))
    wall = float(sz.get("wall_clock_s", 6 * 3600))
    n = min(int(kw.pop("draws", None) or sz.get("start", cap)), cap)
    t0 = time.time()
    history, capped = [], None
    while True:
        t1 = time.time()
        claims, study, extra = evaluate(rule, resolver, params_path, cfg, allow_mock, prior_set, truncation,
                                        draws=n, **kw)
        hw = extra["max_band_half_width"]
        history.append({"draws_per_state": n, "max_band_half_width": hw, "seconds": round(time.time() - t1, 1)})
        if hw is None or hw <= target:
            break
        if 2 * n > cap:
            capped = "draw cap %d per state" % cap
            break
        if (time.time() - t0) + 2 * (time.time() - t1) > wall:
            capped = "wall-clock cap %g s" % wall
            break
        n *= 2
    study["sizing"] = {"rule": "band-mass half-width (2 x binomial SE) <= %g; draws doubled from %d" % (target, history[0]["draws_per_state"]),
                       "draws_per_state": n, "max_band_half_width": history[-1]["max_band_half_width"],
                       "target": target, "met": capped is None, "capped": capped is not None, "cap": capped,
                       "history": history, "seconds": round(time.time() - t0, 1)}
    return claims, study, extra


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


def _unrestricted_claims(claims):
    """C3 and C4 replaced by their unrestricted records (the labelled sensitivity of the admissibility rule)."""
    return {c: (r.get("_unrestricted") or r) if isinstance(r, dict) and c in ("C3", "C4") else r
            for c, r in claims.items()}


def _adm_brief(rec):
    a = (rec or {}).get("admissibility") or {}
    return {k: a.get(k) for k in ("M_adm", "inadmissible_inputs", "verdict_restricted", "verdict_unrestricted", "verdict")} \
        if a else None


def assemble(rule, resolver, by_point, omega, stability, cells, framings, prior_set, cfg, gap=None, d_flags=(),
             admissible=False):
    """Reduce (states done) over framings then design points; C5 and the study per point and framing.

    admissible: the admissibility rule was applied (AM3); the unrestricted study verdicts on the same
    draws are formed beside (a labelled sensitivity) and the retained masses are summarised.
    """
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
    by_design_c5 = {}
    study_u_by_point, link_u_by_point = {}, {c: {} for c in ("C3", "C4")}
    adm_by_point = {}
    for pid in point_ids:
        pbs = pourbaix_for(stability, by_point[pid].get("axes") or {})
        studies = {al: {} for al in pbs}
        studies_u = {al: {} for al in pbs}
        c5s = {al: {} for al in pbs}
        for fr, fd in by_point[pid]["framings"].items():
            om_pt = (omega or {}).get("dose_window", {}).get("points", {}).get(pid) if omega else None
            om_rec = decision.omega_window({pid: om_pt}, p, (omega or {}).get("controls")) if om_pt else None
            for al, pb in pbs.items():
                c5 = decision.evaluate_c5(rule, resolver, omega=om_rec, pourbaix=pb, cells=cells, framing=fr,
                                          cutoffs=cutoffs, never_pass_sinks=tuple(cell_reg.get("never_pass_sinks") or ()),
                                          margin_routes=cell_reg.get("margin_by_route"))
                claims_al = dict(fd["claims"], C5=c5)
                deletion = None
                if fd["controls"]:
                    ctl = {k: (dict(cc, C5=c5) if "_gap" not in cc else cc) for k, cc in fd["controls"].items()}
                    deletion = decision.deletion_test(rule, claims_al, ctl, resolver)
                studies[al][fr] = decision.study_verdict(rule, claims_al, deletion)
                if admissible:
                    deletion_u = None
                    if fd["controls"]:
                        ctl_u = {k: (dict(_unrestricted_claims(cc), C5=c5) if "_gap" not in cc else cc)
                                 for k, cc in fd["controls"].items()}
                        deletion_u = decision.deletion_test(rule, _unrestricted_claims(claims_al), ctl_u, resolver)
                    if deletion is not None:
                        deletion["admissibility"] = {
                            "template": _adm_brief(claims_al.get("C3")),
                            "controls": {k: _adm_brief(cc.get("C3")) for k, cc in fd["controls"].items() if "_gap" not in cc},
                            "unrestricted_holds": deletion_u["holds"] if deletion_u else None}
                    studies_u[al][fr] = decision.study_verdict(rule, _unrestricted_claims(claims_al), deletion_u)
                c5s[al][fr] = c5
            if admissible:
                adm_by_point.setdefault(pid, {})[fr] = {c: _adm_brief(fd["claims"].get(c)) for c in ("C3", "C4")}
                for c in ("C3", "C4"):
                    rec_u = (fd["claims"].get(c) or {}).get("_unrestricted")
                    if rec_u is not None:
                        link_u_by_point[c].setdefault(pid, {})[fr] = rec_u["verdict"]
            fd["claims"]["C5"] = c5s[next(iter(pbs))][fr]
            fd["c5_by_al"] = {al: decision.public(c5s[al][fr]) for al in pbs} if len(pbs) > 1 else None
            fd["claims"] = {c: decision.public(r) for c, r in fd["claims"].items()}
            fd["controls"] = {k: {c: {"verdict": r["verdict"], "falsified_mass": r.get("falsified_mass"),
                                      **({"gap": r["gap"]} if r.get("gap") else {})}
                                  for c, r in cc.items() if isinstance(r, dict)} for k, cc in fd["controls"].items()}
        for c in ("C1", "C2", "C3", "C4"):
            link_by_point[c][pid] = decision.combine_framings(
                {fr: by_point[pid]["framings"][fr]["claims"][c] for fr in by_point[pid]["framings"]}) if c != "C2" else \
                {fr: (by_point[pid]["framings"][fr]["claims"]["C2"].get("finding") or {}).get("statement")
                 for fr in by_point[pid]["framings"]}
        if admissible:
            for c in ("C3", "C4"):
                if c in link_by_point and pid in link_by_point[c]:
                    link_by_point[c][pid]["admissibility_by_framing"] = {fr: (adm_by_point.get(pid) or {}).get(fr, {}).get(c)
                                                                         for fr in by_point[pid]["framings"]}
                if pid in link_u_by_point[c]:
                    link_u_by_point[c][pid] = decision.combine_framings(link_u_by_point[c][pid])
        for al in pbs:
            key = pid if al is None else "%s; Al_T=%s" % (pid, al)
            if admissible:
                study_u_by_point[key] = decision.combine_framings(studies_u[al])["verdict"]
            link_by_point["C5"][key] = decision.combine_framings(c5s[al])
            study_by_point[key] = decision.combine_framings(studies[al])
            study_by_point[key]["deletion_by_framing"] = {fr: s.get("deletion_test") for fr, s in studies[al].items()}
            if al is not None:
                by_design_c5.setdefault(pid, {})[al] = {"C5": link_by_point["C5"][key]["verdict"],
                                                        "study": study_by_point[key]["verdict"]}
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
        if admissible and c in ("C3", "C4"):
            blk = dict(claims[c].get("admissibility") or {})
            masses = [b[c]["M_adm"] for pf in adm_by_point.values() for b in pf.values()
                      if b.get(c) and b[c].get("M_adm") is not None]
            head_u = decision.over_design({pid: r["verdict"] for pid, r in link_u_by_point[c].items()})
            blk["over_design"] = {
                "M_adm_min": min(masses) if masses else None, "M_adm_max": max(masses) if masses else None,
                "n_inadmissible": sum(1 for pf in adm_by_point.values() for b in pf.values()
                                      if b.get(c) and b[c].get("inadmissible_inputs")),
                "n_point_framings": sum(len(pf) for pf in adm_by_point.values()),
                "verdict_unrestricted": head_u["verdict"],
                "unrestricted_by_design": {pid: r["verdict"] for pid, r in link_u_by_point[c].items()},
                "differs": {pid: {"rule": link_by_point[c][pid]["verdict"], "unrestricted": r["verdict"]}
                            for pid, r in link_u_by_point[c].items() if r["verdict"] != link_by_point[c][pid]["verdict"]}}
            claims[c]["admissibility"] = blk
        if c == "C5" and omega is not None:
            claims[c]["dose_window"] = omega["dose_window"]
            claims[c]["omega_controls"] = omega.get("controls")
            claims[c]["omega_sensitivities"] = omega.get("sensitivities")      # C5s_ACC, labelled, never gating
    head = decision.over_design({pid: r["verdict"] for pid, r in study_by_point.items()})
    gating = rule["study"].get("gating_links") or ["C1", "C3", "C4", "C5"]
    deletions = [d for r in study_by_point.values() for d in r["deletion_by_framing"].values()]
    study = {"verdict": head["verdict"], "links": {c: claims[c]["verdict"] for c in gating},
             "by_design_c5": by_design_c5 or None,
             "deletion_test": deletions[0] if len(deletions) == 1 else ({"by_point": {pid: r["deletion_by_framing"]
                                                                                       for pid, r in study_by_point.items()}}
                                                                        if any(deletions) else None),
             "framing": None, "gating_links": list(gating), "design_dependent": head["design_dependent"],
             "by_design": study_by_point, "framings": list(framings), "prior_set": prior_set,
             "finding_eligible": eligible,
             "sequestration_premise": link_by_point["C2"].get(primary, {}).get(framings[0])}
    if any(d is not None and not d["holds"] for d in deletions):
        study["framing"] = "generic adhesion study"
    if admissible:
        head_u = decision.over_design(study_u_by_point)
        study["admissibility"] = {
            "label": admissibility.LABEL,
            "rule": "thresholds block v4 decision.admissibility (D27; gap_resolution.yaml AM3)",
            "C3": {k: claims["C3"]["admissibility"]["over_design"][k] for k in ("M_adm_min", "M_adm_max", "n_inadmissible",
                                                                                  "n_point_framings")}
            if (claims["C3"].get("admissibility") or {}).get("over_design") else None,
            "by_design": adm_by_point,
            "unrestricted": {"label": "unrestricted joint prior on the same draws (labelled sensitivity, never a verdict)",
                             "verdict": head_u["verdict"], "design_dependent": head_u["design_dependent"],
                             "by_design": study_u_by_point},
            "differs": {k: {"rule": study_by_point[k]["verdict"], "unrestricted": v}
                        for k, v in study_u_by_point.items() if v != study_by_point[k]["verdict"]}}
    extra = {"design_gap": gap, "d_max_flags": list(d_flags), "omega": omega, "points": point_ids,
             "mechanism": {pid: {fr: fd.get("mechanism") for fr, fd in by_point[pid]["framings"].items()}
                           for pid in point_ids} if admissible else None,
             "unsampled": {pid: {fr: fd["unsampled"] for fr, fd in by_point[pid]["framings"].items()}
                           for pid in point_ids}}
    return claims, study, extra


def _ca_tag(label):
    try:
        return "%.0e" % float(str(label).split()[0])
    except ValueError:
        return str(label)


def pourbaix_for(stability, axes):
    """{Al label or None: R-slurry Pourbaix section} for one design point.

    stability: None; one stability mapping ({"R-slurry": ...}) for every point; or
    {"by_point": {(Ca tag, C_T tag): {Al label: section}}} from W5's per-point documents
    (aCa<Ca>_CT<min|value|max>_Al<Al>.json).
    """
    if not stability:
        return {None: None}
    if "by_point" not in stability:
        return {None: stability.get("R-slurry")}
    key = (_ca_tag(axes.get("Ca_T")), str(axes.get("C_T", "")).split("@")[-1])
    found = stability["by_point"].get(key)
    return dict(sorted(found.items())) if found else {None: None}


def load_slurry_stability(directory):
    """{"by_point": {(Ca tag, C_T tag): {Al label: section}}} from W5's R-slurry C5 documents."""
    import json
    import re
    from pathlib import Path
    out = {}
    for path in sorted(Path(directory).glob("aCa*_CT*_Al*.json")):
        m = re.fullmatch(r"aCa([^_]+)_CT([^_]+)_Al([^_]+)", path.stem)
        if not m:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        sec = (doc.get("stability") or {}).get("R-slurry")
        if sec:
            out.setdefault((m.group(1), m.group(2)), {})["%s mol dm^-3" % m.group(3)] = sec
    return {"by_point": out} if out else None


def _primary(point_ids, by_point):
    """The central design point (middle of the list), whose detailed records are kept."""
    return point_ids[len(point_ids) // 2]


def load_cells(paths, phase_windows=None, benchmark_file=None):
    """{sink: R-cell section} from W5's per-sink stability documents (schema v2 or v3).

    phase_windows: {gated phase: W5 window name} (gap_resolution.yaml AM2: corundum is W5's
    Al2O3); benchmark_file: W5's scheme table, whose per-electron benchmark errors fill the
    comparator rows of every sink (never deciding).
    """
    import json
    from pathlib import Path
    cells = {}
    bench = None
    if benchmark_file and Path(benchmark_file).exists():
        rows = json.loads(Path(benchmark_file).read_text(encoding="utf-8")).get("table") or []
        errs = next((r.get("benchmark_error_V_per_electron") for r in rows if r.get("benchmark_error_V_per_electron")), None)
        bench = {s: {"benchmark_error_V": float(v), "source": Path(benchmark_file).as_posix()} for s, v in (errs or {}).items()}
    for path in paths or ():
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        cell = (doc.get("stability") or {}).get("R-cell")
        if cell:
            cell = dict(cell, windows=dict(cell.get("windows") or {}))
            for phase, name in (phase_windows or {}).items():
                if name in cell["windows"] and phase not in cell["windows"]:
                    cell["windows"][phase] = cell["windows"][name]
            if bench and not cell.get("schemes"):
                cell["schemes"] = bench
            sink = cell.get("sink_assumption", {}).get("active") or Path(path).stem
            cells[sink] = cell
    return cells


def config_registrations(cfg):
    return yaml.safe_dump(cfg.get("registrations") or {}, sort_keys=True)
