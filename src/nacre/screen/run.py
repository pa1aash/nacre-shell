"""Screen runs: production (P0-W4.3, after cp3) and dry runs (mock or draft priors).

A run propagates each regime's joint prior through the chain (Monte Carlo, Task 4a),
computes per link the Sobol indices of the independent marginals sized to the stated
target and verified by doubling (4b), the Shapley effects under the stated correlations
(4c), optionally the robustness of the Shapley ranking to the correlation assumption (4e),
and the threshold evaluation when the thresholds are frozen; it writes one results
document (configs/preprint/results_schema.json, v2).

Guards
  production  priors from lit/params.yaml (not mock), thresholds frozen in
              configs/preprint/thresholds.yaml, tag p0-cp3 present (session P0-W4.3 needs
              cp1, cp2 and cp3), output under results/preprint/screen/ outside dryrun/,
              one ledger line in jobs/ledger/p0-w4.jsonl.
  dry run     any prior table with --mock; output only under results/preprint/screen/dryrun/
              (git-ignored); always marked mock; never reported (rule R-dry), no ledger line.
"""
import hashlib
import json
import subprocess
from functools import partial
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import admissibility, chain, decision, gaps, params_adapter, ph_prov, propagate, shapley, sobol, study, summary
from nacre.screen import thresholds as thr
from nacre.screen.mineral import CALCITE

CONFIG = Path("configs") / "preprint" / "screen.yaml"
THRESHOLDS = Path("configs") / "preprint" / "thresholds.yaml"
CONTRACT_CHECK = Path("configs") / "preprint" / "contract_check.json"
SCREEN_DIR = Path("results") / "preprint" / "screen"
DRYRUN_DIR = SCREEN_DIR / "dryrun"
DRYRUN_PH_DIR = SCREEN_DIR / "dryrun_ph"            # PH-W4.1: phosphate dry runs, git-ignored, never reported
LEDGER = Path("jobs") / "ledger" / "p0-w4.jsonl"
CHECKPOINT_TAG = "p0-cp3"
#: Session that writes production documents (ledger lines and provenance).
SESSION = "PH-W4.2"
#: Mass groups that count refused draws (activity model, geometric bounds), not clipped boundaries.
REFUSAL_GROUPS = ("speciation", "geometry")


class ProductionRefused(RuntimeError):
    """A production run was requested before its inputs are frozen."""


def _sha256_file(path):
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()


def _rel(root, path):
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _inside(path, directory):
    try:
        Path(path).resolve().relative_to(Path(directory).resolve())
        return True
    except ValueError:
        return False


def _hydroxide_input(s, mineral):
    """pKw, which turns the speciated pH and a_w into a_OH, when the table supplies it for a phosphate mineral."""
    return ("pKw",) if mineral.speciation == "phosphate" and "pKw" in s else ()


def _sampled(names, s, mineral=CALCITE):
    """Replace derived symbols by the sampled inputs they come from (speciation, ignorance)."""
    out = []
    spec_in = chain.speciation_inputs(mineral)
    spec_out = chain.SPECIATION_OUTPUTS.get(mineral.speciation, ()) + (("a_OH",) if mineral.speciation == "phosphate" else ())
    for k in names:
        if k in s:
            out.append(k)
        elif k in spec_out and spec_in and s >= set(spec_in):
            out.extend(spec_in + _hydroxide_input(s, mineral))
        elif k in chain.ignorance_pairs(s):
            u, pair = chain.ignorance_pairs(s)[k]
            out.extend([u, *pair])
        elif k == "Delta_gamma_w" and chain.IGNORANCE["gamma_sn0"][0] in s:
            continue
        elif k == "delta_s" and chain.GEOMETRY[0] in s:
            out.extend([chain.GEOMETRY[0], *chain.GEOMETRY[1]])
        elif k == "Delta_G_site" and chain.SITE_ANALOG[0] in s:
            out.extend([chain.SITE_ANALOG[0], *chain.SITE_ANALOG[1], chain.GEOMETRY[0], *chain.GEOMETRY[1]])
        elif k == "gamma_pw" and "gamma_sl0" in s:
            out.append("gamma_sl0")
        else:
            out.append(k)
    return list(dict.fromkeys(out))


def link_inputs(link, symbols, mineral=CALCITE):
    """Sampled symbols a link reads (nucleate includes the upstream cycle when gamma_sl0 is given)."""
    s = set(symbols)
    d = chain.derived_symbols(s, mineral)
    seq = list(chain.SEQ_CYCLE_INPUTS) if d >= set(chain.SEQ_CYCLE_INPUTS) else ["Delta_G_seq"]
    if chain.SEQ_CYCLE_2H in s and d >= set(chain.SEQ_CYCLE_INPUTS):
        seq.append(chain.SEQ_CYCLE_2H)                      # the two-proton cycle of the analog route (AM3)
    seq = [k for k in dict.fromkeys(seq + list(chain.SEQ_LOCAL_INPUTS))]
    if link == "anchor":
        base = list(chain.PMF_INPUTS) if d >= set(chain.PMF_INPUTS) else list(chain.ANCHOR_INPUTS)
        return _sampled(base + (["W_adh_wet"] if "W_adh_wet" in s else []), s, mineral)
    if link == "speciation":
        extra = [k for k in mineral.omega_symbols[1:] if k in s and k not in chain.speciation_inputs(mineral)]
        return list(chain.speciation_inputs(mineral)) + list(_hydroxide_input(s, mineral)) + extra
    if link == "sequester":
        return _sampled(seq, s, mineral)
    if link == "nucleate":
        access = [k for k in chain.ACCESS_INPUTS if k in d]
        base = list(chain.nuc_base(mineral))
        if chain.template_energy_mode(d) == "ca_free":
            return _sampled(seq + base + ["gamma_sl0"] + access, s, mineral)
        return _sampled(base + ["gamma_sl"] + access, s, mineral)
    raise KeyError(link)


def link_joint(joint, link, mineral=CALCITE):
    """Joint prior of a link's inputs and of every input correlated with one of them."""
    sym = joint.symbols
    need = {sym.index(s) for s in link_inputs(link, sym, mineral) if s in sym}
    partners = {j for i in need for j in range(joint.k) if joint.spearman[i, j] != 0}
    idx = sorted(need | partners)
    return joint.marginal([joint.names[i] for i in idx])


def link_model(link, admissible=False, mineral=CALCITE):
    """Model of one link on the sensitivity scale of each quantity (chain.Output.scale).

    admissible: the nucleate link is analysed on the admitted draws (AM3, sensitivity).
    """
    return chain.sensitivity_model(link, admissible=admissible, mineral=mineral)


def _round_quantiles(levels):
    return tuple(float(q) for q in levels)


def run_regime(rp, cfg, seed, links=None, dependence_check=None, thresholds=None, independence=False,
               return_outputs=False, admissible=None, mineral=CALCITE):
    """Results entry of one regime (schema $defs/regime). rp: params_adapter.RegimePriors.

    With return_outputs the propagated draws ({link: {quantity: array}}) are returned too,
    for the decision rule.
    """
    joint = rp.joint.independent() if independence else rp.joint
    pc, sc, hc = cfg["propagation"], cfg["sobol"], cfg["shapley"]
    if admissible is None:
        admissible = bool((cfg.get("registrations") or {}).get("admissibility"))
    links = links or chain.evaluable_links(joint.symbols, mineral)
    mc_seq, sens_seq = np.random.SeedSequence(seed).spawn(2)
    evaluate = chain.evaluate if mineral is CALCITE else partial(chain.evaluate, mineral=mineral)
    outputs, masses = propagate.propagate_chain(evaluate, joint, pc["draws_per_regime"],
                                                int(mc_seq.generate_state(1)[0]), pc["chunk"])
    levels = _round_quantiles(pc["quantiles"])
    out_links, convergences, designs = {}, [], []
    adm_rec = None
    if admissible and "nucleate" in outputs:
        keep = chain.admissible_mask(outputs)
        ev = np.isfinite(np.asarray(outputs["nucleate"][chain.ADMISSIBILITY_QUANTITY], dtype=float))
        adm_rec = {"label": admissibility.SENSITIVITY_NOTE, "M_adm": float(keep.sum() / ev.sum()) if ev.any() else None,
                   "n_evaluable": int(ev.sum()), "n_refused": int(ev.sum() - keep.sum())}
        outputs = dict(outputs, nucleate={q: np.where(keep, np.asarray(v, dtype=float), np.nan)
                                          for q, v in outputs["nucleate"].items()})
    check = dependence_check if dependence_check is not None else cfg.get("dependence_check", False)
    agreement = {}
    for link, link_seq in zip(links, sens_seq.spawn(len(links))):
        meta = chain.OUTPUTS[link]
        quantities = {}
        for q, m in meta.items():
            if q not in outputs[link]:                       # a quantity of another mineral's speciation
                continue
            values = outputs[link][q]
            if not np.any(np.isfinite(values)):
                continue
            quantities[q] = {"symbol": m.symbol, "units": m.units, **propagate.describe(values, levels)}
        names = [q for q in meta if q in quantities and meta[q].scale != "none"]
        sub = link_joint(joint, link, mineral)
        s_seq, h_seq, d_seq = link_seq.spawn(3)
        idx, design, conv = sobol.size_and_verify(
            link_model(link, admissible, mineral), sub, names, sc["target_ci_half_width"], int(s_seq.generate_state(1)[0]),
            pilot=sc["pilot_base"], n_bootstrap=sc["bootstrap"], confidence=sc["confidence"], key="symbol",
            chunk=pc["chunk"], max_base=sc["max_base"], on_cap="cap", scope=sc.get("target_scope", "all"),
            top_k=int(sc.get("top_k", 3)))
        players = sum(not p.is_fixed for p in sub.priors)
        kw = dict(n_var=hc["n_var"], n_outer=hc["n_outer"], n_inner=hc["n_inner"], key="symbol",
                  n_bootstrap=hc["bootstrap"], confidence=hc["confidence"], chunk=pc["chunk"],
                  design="subsets" if players <= hc["max_players_for_subsets"] else "permutations",
                  n_perm=hc["n_perm"])
        sh, sh_design = shapley.shapley_effects(link_model(link, admissible, mineral), sub, names, rng=np.random.default_rng(h_seq),
                                                **kw)
        if admissible and link == "nucleate":
            # AM3: on the admitted draws; the restriction makes the inputs dependent, so the Shapley effects
            # (rejection inside the double loop) carry the ranking and the Sobol indices are approximate
            sh_design = dict(sh_design, admissibility=admissibility.SENSITIVITY_NOTE)
            design = dict(design, method="%s; %s" % (design["method"], admissibility.SENSITIVITY_NOTE))
        entry = {"quantities": quantities, "sobol": idx, "shapley": sh, "threshold_evaluation": None,
                 "sensitivity_scale": {q: meta[q].scale for q in names}, "sobol_design": design,
                 "convergence": conv, "shapley_design": sh_design}
        if check and not sub.is_independent:
            rec, _, _ = shapley.dependence_check(link_model(link, admissible, mineral), sub, names, np.random.default_rng(d_seq), **kw)
            agreement[link] = rec["rank_agreement"]
        out_links[link] = entry
        convergences.append(conv)
        designs.append(design)
    regime = {
        "draws": int(pc["draws_per_regime"]), "seed": int(seed),
        "sobol_design": {"method": sobol.METHOD + "; sized per link",
                         "base_samples": max(d["base_samples"] for d in designs),
                         "evaluations": sum(d["evaluations"] for d in designs),
                         "bootstrap_resamples": int(sc["bootstrap"]), "confidence_level": float(sc["confidence"])},
        "parameters": joint.names, "links": out_links,
        "boundary_mass": {lk: {q: m.as_dict() for q, m in d.items()} for lk, d in masses.items()
                          if lk in out_links and lk not in REFUSAL_GROUPS},
        "refused": {lk: {q: m.as_dict() for q, m in d.items()} for lk, d in masses.items()
                    if lk in REFUSAL_GROUPS} or None,
        "dependence": joint.dependence_record(),
        "admissibility": adm_rec,
        "dependence_check": {"alternative": "independent", "rank_agreement": agreement} if agreement else None,
        "convergence": {
            "target_ci_half_width": float(sc["target_ci_half_width"]),
            "base_samples": max(c["base_samples"] for c in convergences),
            "base_samples_doubled": max(c["base_samples_doubled"] for c in convergences),
            "max_ci_half_width": max(c["max_ci_half_width"] for c in convergences),
            "max_estimate_shift": max(c["max_estimate_shift"] for c in convergences),
            "converged": all(c["converged"] for c in convergences),
            "capped": any(c["capped"] for c in convergences),
            "target_scope": convergences[0].get("target_scope", "all")},
    }
    return (regime, outputs) if return_outputs else regime


def _attach_link_records(regimes_out, claims):
    """Each test record of the detail point also goes to threshold_evaluation of the link carrying it."""
    reg = regimes_out.get("R-slurry")
    if reg is None:
        return
    for claim, rec in claims.items():
        for tid, t in (rec.get("tests") or {}).items():
            src = decision.QUANTITY_SOURCE.get(t.get("quantity"))
            if src and src[0] in reg["links"]:
                ev = reg["links"][src[0]]["threshold_evaluation"] or {}
                ev["%s.%s" % (claim, tid)] = {k: v for k, v in t.items() if k in ("verdict", "P_good", "P_bad", "edge",
                                                                                "edge_expression", "gap", "notes")}
                reg["links"][src[0]]["threshold_evaluation"] = ev


FRAMING_KEY = "regimes.R-slurry.parameters.framing"


def load_states(params_path, regime, cfg, allow_mock, framing=None, dry_run=True, prior_set="table",
                truncation=True):
    """[(state, RegimePriors)] of one regime at the primary framing and the central design point.

    A mock table without bindings is read whole as one state. Otherwise the table is read
    through the bindings of configs/preprint/screen.yaml (nacre.screen.study.load_point). The
    framings are registered in screen.yaml (cp3 R6); a framing passed explicitly selects one.
    """
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    b = (cfg.get("bindings") or {}).get(regime)
    try:
        if doc["mock"] and not study.bound_table(doc, b):
            return [("default", params_adapter.regime_priors(params_path, regime, allow_mock))]
        if not b:
            return []
        frs = [framing] if framing else list((cfg.get("registrations") or {}).get("framings") or [])
        if not frs:
            registered = decision.Resolver.from_table(doc)
            fr = registered.value(FRAMING_KEY) if registered.has(FRAMING_KEY) else None
            if fr is None:
                raise ProductionRefused("the framing (%s) is not registered%s"
                                        % (FRAMING_KEY, "" if not dry_run else "; pass framing for a dry run"))
            frs = [fr]
        if frs[0] not in b["by_framing"]:
            raise params_adapter.PriorFileError("no bindings for framing %r" % frs[0])
        resolver = decision.Resolver.from_table(doc)
        try:
            pts = study.design_points(cfg, resolver)
        except decision.Gap:
            pts = []
        design = pts[len(pts) // 2][1] if pts else {}
        return study.load_point(params_path, cfg, frs[0], design, allow_mock, prior_set, truncation, regime)
    except params_adapter.PriorFileError as exc:
        if "no sampled or fixed inputs" in str(exc):
            return []
        raise


def run_states(states, cfg, seed, dependence_check, thresholds, independence, full=True):
    """Regime entry and per-state chain outputs.

    The first state with an evaluable link gets the full analysis (quantiles, boundary mass,
    sized Sobol, Shapley, dependence check); every other state is propagated, summarised
    under ``states`` and passed to the decision rule. Returns (entry or None, {state: outputs}).
    """
    entry, outs = None, {}
    seqs = np.random.SeedSequence(seed).spawn(max(len(states), 1))
    pc = cfg["propagation"]
    levels = _round_quantiles(pc["quantiles"])
    for (sid, rp), sq in zip(states, seqs):
        joint = rp.joint.independent() if independence else rp.joint
        if not chain.evaluable_links(joint.symbols):
            continue
        st_seed = int(sq.generate_state(1)[0])
        if entry is None and full:
            entry, outs[sid] = run_regime(rp, cfg, st_seed, dependence_check=dependence_check, thresholds=thresholds,
                                          independence=independence, return_outputs=True)
            entry["primary_state"] = sid
            entry["unsampled"] = dict(rp.unsampled)
            continue
        o, masses = propagate.propagate_chain(chain.evaluate, joint, pc["draws_per_regime"], st_seed, pc["chunk"])
        outs[sid] = o
        if entry is not None:
            entry.setdefault("states", {})[sid] = {
                "quantities": {lk: {q: {"symbol": chain.OUTPUTS[lk][q].symbol, "units": chain.OUTPUTS[lk][q].units,
                                        **propagate.describe(v, levels)}
                                    for q, v in d.items() if np.any(np.isfinite(v))} for lk, d in o.items()},
                "boundary_mass": {lk: {q: m.as_dict() for q, m in d.items()} for lk, d in masses.items()
                                  if lk not in REFUSAL_GROUPS},
                "refused": {lk: {q: m.as_dict() for q, m in d.items()} for lk, d in masses.items()
                            if lk in REFUSAL_GROUPS} or None,
                "unsampled": dict(rp.unsampled)}
    return entry, outs


def load_config(root, path=CONFIG):
    return yaml.safe_load((Path(root) / path).read_text(encoding="utf-8"))


def _provenance(root, cfg, cfg_path, rp_list, thresholds_path, dry):
    sha, dirty = summary.git_state(root)
    prior_path = rp_list[0].path
    params_sha = None if dry else (_git(root, "log", "-1", "--format=%H", "--", _rel(root, prior_path)) or None)
    check = Path(root) / CONTRACT_CHECK
    contract = json.loads(check.read_text(encoding="utf-8")).get("contract_sha") if check.exists() else None
    th = Path(root) / thresholds_path
    th_source = thr.split_copy(th.read_text(encoding="utf-8"))[0] if th.exists() else None
    gt = Path(root) / gaps.GAP_TABLE
    am = [a for a in (gaps.load(gt).get("amendments") or []) if a.get("w3_admissibility_sha")] if gt.exists() else []
    adm_cfg = (cfg.get("registrations") or {}).get("admissibility")
    return {"git_sha": sha, "git_dirty": dirty,
            "session": SESSION,
            "admissibility_sha": am[-1]["w3_admissibility_sha"] if am and adm_cfg else None,
            "admissibility_rule": ("%s (gap table %s)" % (adm_cfg.get("rule"), am[-1]["id"])) if am and adm_cfg else None,
            "config_hash": summary.config_hash({"screen": cfg, "regimes": [r.regime for r in rp_list]}),
            "config_file": _rel(root, cfg_path), "config_file_hash": _sha256_file(cfg_path),
            "prior_file": _rel(root, prior_path), "prior_file_hash": rp_list[0].sha256,
            "params_sha": params_sha,
            "thresholds_file": _rel(root, th) if th.exists() else None,
            "thresholds_hash": _sha256_file(th) if th.exists() else None,
            "thresholds_source_sha": th_source,
            "contract_sha": contract,
            "schema_sha": _git(root, "log", "-1", "--format=%H", "--", "configs/preprint/results_schema.json") or None,
            "gap_table_file": gaps.GAP_TABLE.as_posix() if gt.exists() else None,
            "gap_table_sha": _git(root, "log", "-1", "--format=%H", "--", gaps.GAP_TABLE.as_posix()) or None,
            "gap_table_hash": _sha256_file(gt) if gt.exists() else None,
            **ph_prov.extra(root),
            "params_tag": CHECKPOINT_TAG if _git(root, "tag", "-l", CHECKPOINT_TAG) else None,
            "params_sha_at_tag": _git(root, "log", "-1", "--format=%H", CHECKPOINT_TAG, "--",
                                      params_adapter.PRODUCTION_PARAMS.as_posix()) or None
            if _git(root, "tag", "-l", CHECKPOINT_TAG) else None}


def _inputs_frozen(root, thresholds_path=THRESHOLDS):
    ph_prov.check_frozen(root)                     # p0-cp5: the ladder, the bindings hash and the tag (PH-W4.2)
    if not _git(root, "tag", "-l", CHECKPOINT_TAG):
        raise ProductionRefused("tag %s is missing: production screens need cp1, cp2 and cp3" % CHECKPOINT_TAG)
    if not (Path(root) / thresholds_path).exists():
        raise ProductionRefused("thresholds are not frozen (%s is missing)" % thresholds_path)
    if not (Path(root) / params_adapter.PRODUCTION_PARAMS).exists():
        raise ProductionRefused("%s is missing" % params_adapter.PRODUCTION_PARAMS)


def production_guard(root, rp_list, out_path, thresholds_path=THRESHOLDS):
    """Raise ProductionRefused unless every production precondition holds."""
    root = Path(root)
    if any(rp.mock for rp in rp_list):
        raise ProductionRefused("production runs read lit/params.yaml, not a mock table")
    if any(_rel(root, rp.path) != params_adapter.PRODUCTION_PARAMS.as_posix() for rp in rp_list):
        raise ProductionRefused("production priors come only from %s" % params_adapter.PRODUCTION_PARAMS)
    if not (root / thresholds_path).exists():
        raise ProductionRefused("thresholds are not frozen (%s is missing)" % thresholds_path)
    if not _git(root, "tag", "-l", CHECKPOINT_TAG):
        raise ProductionRefused("tag %s is missing: production screens need cp1, cp2 and cp3" % CHECKPOINT_TAG)
    if _inside(out_path, root / DRYRUN_DIR) or not _inside(out_path, root / SCREEN_DIR):
        raise ProductionRefused("production output belongs under %s, outside %s" % (SCREEN_DIR, DRYRUN_DIR))
    if Path(out_path).exists():
        raise ProductionRefused("%s exists: a production document is never overwritten (use a new run name)"
                                % _rel(root, Path(out_path)))


def run(root, out_path, params_path=None, regimes=params_adapter.REGIMES, dry_run=True, allow_mock=False,
        config_path=CONFIG, independence=False, dependence_check=None, overrides=None, stability_path=None,
        cell_paths=None, controls=None, framing=None, prior_set="table", truncation=True, decide=True,
        decision_draws=None, truncation_sensitivity=False, conventions=None, bind=None, sensitivity=True,
        run_label=None, mechanism=False):
    """Run the screen and write the results document; returns (path, doc).

    The sensitivity analysis runs at the primary framing and the central design point. The
    decision layer (nacre.screen.study) runs over every design point, registered framing and
    registered state; in a dry run its claims are mock like the rest of the document.

    framing: one framing for a dry run (the registered set is in screen.yaml). prior_set:
    table | ignorance | analog (labelled in the output). truncation: False reports the
    untruncated gamma_sl0 sensitivity; truncation_sensitivity reruns the decisions untruncated and
    lists the verdicts that change (block v2, decision.priors). stability_path: a W5 document with the R-slurry
    Pourbaix section; cell_paths: W5's per-sink R-cell documents; controls: {control: table}
    for the deletion test (bare_oxide, PVDF): names of screen.yaml ``controls`` (a mapping is
    read as its keys). stability_path may be a directory of W5's per-point R-slurry documents.

    conventions: {table key: value} overrides of registered conventions for a sweep (p_cred,
    m_cos), labelled in the provenance; bind: {symbol: table key} overrides of the R-slurry
    bindings (a labelled sensitivity). sensitivity: False skips the Sobol and Shapley analysis
    (sweep runs). The decision layer runs under the sizing rule (study.evaluate_sized); the
    sensitivity propagation then uses the sized draws per state. mechanism: write the admitted
    versus refused draws of the admissibility rule per design point, framing and state under
    extensions.p0-w4 (the report-only diagnostics of P0-W4.3b).
    """
    root = Path(root)
    out_path = Path(out_path)
    cfg_path = root / config_path
    cfg = load_config(root, config_path)
    for section, values in (overrides or {}).items():
        cfg[section] = {**(cfg.get(section) or {}), **values}
    if bind:
        cfg["bindings"]["R-slurry"]["common"] = {**cfg["bindings"]["R-slurry"]["common"], **bind}
    params_path = Path(params_path) if params_path else root / params_adapter.PRODUCTION_PARAMS
    if not dry_run:
        _inputs_frozen(root)
    _sizing_caps(cfg)
    loaded = {r: load_states(params_path, r, cfg, allow_mock, framing, dry_run, prior_set, truncation) for r in regimes}
    rp_list = [rp for states in loaded.values() for _, rp in states]
    if not rp_list:
        raise params_adapter.PriorFileError("no regime has sampled inputs in %s" % params_path)
    if dry_run:
        if not (_inside(out_path, root / DRYRUN_DIR) or _inside(out_path, root / DRYRUN_PH_DIR)):
            raise ProductionRefused("dry-run output belongs under %s" % DRYRUN_DIR)
    else:
        production_guard(root, rp_list, out_path)
    thresholds = thr.load_thresholds(root / THRESHOLDS) if (root / THRESHOLDS).exists() else None
    seeds = np.random.SeedSequence(cfg["propagation"]["seed"]).spawn(len(params_adapter.REGIMES) + 1)
    seed_of = {r: int(s.generate_state(1)[0]) for r, s in zip(params_adapter.REGIMES, seeds)}
    claims = study_doc = None
    mech = None
    if thresholds is not None and decide and "R-slurry" in regimes:
        rule = thresholds["rule"]
        resolver = decision.Resolver.from_table(yaml.safe_load(Path(params_path).read_text(encoding="utf-8")))
        gt = root / gaps.GAP_TABLE
        if gt.exists():
            resolver = resolver.alias(gaps.load(gt).get("key_aliases"))
        if conventions:
            resolver = resolver.override(conventions)
        stability = _stability(stability_path)
        creg = (cfg.get("registrations") or {}).get("R-cell") or {}
        cells = study.load_cells(cell_paths, creg.get("phase_windows"),
                                 (root / creg["benchmark_errors"]) if creg.get("benchmark_errors") else None)
        frs = [framing] if framing else None
        kw = dict(draws=decision_draws, seed=int(seeds[-1].generate_state(1)[0]), framings=frs, stability=stability,
                  cells=cells, controls=list(controls or ()), independence=independence)
        claims, study_doc, extra = study.evaluate_sized(rule, resolver, params_path, cfg, allow_mock, prior_set,
                                                        truncation, **kw)
        kw["draws"] = study_doc["sizing"]["draws_per_state"]
        cfg["propagation"] = {**cfg["propagation"], "draws_per_regime": kw["draws"]}
        trunc = truncation_report(loaded.get("R-slurry") or [], cfg)
        if trunc and truncation and truncation_sensitivity:
            c2, s2, _ = study.evaluate(rule, resolver, params_path, cfg, allow_mock, prior_set, False, **kw)
            trunc["untruncated_sensitivity"] = changed_verdicts(claims, study_doc, c2, s2)
        study_doc["truncation"] = trunc or None
        mech = extra.get("mechanism") if mechanism else None
        study_doc["gaps"] = _gaps(claims, extra)
        study_doc["overrides"] = {"conventions": conventions, "bind": bind, "independence": bool(independence)} \
            if (conventions or bind or independence) else None
        study_doc["controls_registered"] = {c: ("gap: " + s["gap"]) if s.get("gap") else "evaluable"
                                            for c, s in (cfg.get("controls") or {}).items()} or None
    regimes_out, not_evaluable = {}, {}
    for regime, states in (loaded.items() if sensitivity else ()):
        entry, _ = run_states(states, cfg, seed_of[regime], dependence_check, thresholds, independence)
        if entry is None:
            not_evaluable[regime] = {sid: dict(rp.unsampled) for sid, rp in states}
            continue
        entry["prior_set"] = prior_set
        entry["barrier_prefactor"] = barrier_prefactor(states)
        regimes_out[regime] = entry
    if claims is not None:
        _attach_link_records(regimes_out, claims)
        study_doc["not_evaluable"] = not_evaluable or None
    if not regimes_out and claims is None:
        raise params_adapter.PriorFileError(
            "no link of the chain is evaluable from %s; unsampled inputs: %s" % (params_path, not_evaluable))
    prov = _provenance(root, cfg, cfg_path, rp_list, THRESHOLDS, dry_run)
    prov["overrides"] = {"conventions": conventions, "bind": bind, "independence": bool(independence),
                         "truncation": bool(truncation)} if (conventions or bind or independence or not truncation) else None
    prov["run_label"] = run_label
    ext = {"p0-w4": {"admissibility_mechanism": {
        "label": "report-only diagnostic of the admissibility rule (D27): quantiles (5, 50, 95 %) of the admitted and "
                 "refused draws per design point, framing and state; gamma_sl0 = gamma_sl_insitu + Pi_ads",
        "by_design": mech}}} if mech is not None else None
    doc = summary.build(regimes_out or None, prov, mock=dry_run or any(rp.mock for rp in rp_list), claims=claims,
                        study=study_doc, extensions=ext)
    path = summary.write(doc, out_path)
    if not dry_run:
        line = {"kind": "screen", "session": SESSION, "git_sha": prov["git_sha"], "git_dirty": prov["git_dirty"],
                "config": prov["config_file"], "config_hash": prov["config_hash"],
                "params_hash": prov["prior_file_hash"], "thresholds_hash": prov["thresholds_hash"],
                "contract_sha": prov["contract_sha"], "mock": False,
                "outputs": [{"path": _rel(root, path), "sha256": _sha256_file(path).split(":", 1)[1]}]}
        ledger = root / LEDGER
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    return path, doc


def _stability(path):
    """W5's R-slurry stability input: one document (its stability mapping) or a directory of per-point documents."""
    if not path:
        return None
    path = Path(path)
    if path.is_dir():
        return study.load_slurry_stability(path)
    return json.loads(path.read_text(encoding="utf-8")).get("stability")


def truncation_report(states, cfg):
    """{symbol: removed prior mass} of every truncated prior of the primary state (cp3 R8)."""
    out = {}
    for _, rp in states[:1]:
        for pr in rp.joint.priors:
            if pr.truncate:
                kept = pr.truncated_mass()
                out[pr.symbol] = {"bounds": list(pr.truncate), "kept_mass": kept, "removed_mass": 1.0 - kept,
                                  "key": pr.name}
    return out


def changed_verdicts(claims, study_doc, claims_u, study_u):
    """Verdicts that differ between the truncated run and the untruncated sensitivity."""
    out = {}
    for c in claims:
        a, b = claims[c].get("verdict"), claims_u[c].get("verdict")
        if a != b:
            out[c] = {"truncated": a, "untruncated": b}
        for pid, r in (claims[c].get("by_design") or {}).items():
            ru = (claims_u[c].get("by_design") or {}).get(pid)
            if isinstance(r, dict) and isinstance(ru, dict) and r.get("verdict") != ru.get("verdict"):
                out.setdefault(c + " by design", {})[pid] = {"truncated": r.get("verdict"), "untruncated": ru.get("verdict")}
    if study_doc["verdict"] != study_u["verdict"]:
        out["study"] = {"truncated": study_doc["verdict"], "untruncated": study_u["verdict"]}
    return {"label": "untruncated gamma_sl0 prior (labelled sensitivity)", "changed": out}


def _gaps(claims, extra):
    """Every explicit gap of the decision layer, by link and test, plus the unsampled inputs."""
    out = {}
    for c, rec in claims.items():
        g = [rec["gap"]] if rec.get("gap") else []
        g += ["%s: %s" % (t, r["gap"]) for t, r in (rec.get("tests") or {}).items() if isinstance(r, dict) and r.get("gap")]
        if g:
            out[c] = g
    if extra.get("design_gap"):
        out["design_axes"] = [extra["design_gap"]]
    if extra.get("d_max_flags"):
        out["C4s_d_max"] = list(extra["d_max_flags"])
    return out


def _sizing_caps(cfg):
    """The sizing rule's caps (thresholds, cp2): at most 2^20 draws per state, chunks of 2^14."""
    pc = cfg["propagation"]
    if int(pc["draws_per_regime"]) > 2 ** 20:
        raise ProductionRefused("draws_per_regime %d exceeds the sizing rule's cap of 2^20 per state"
                                % pc["draws_per_regime"])
    if int(pc["chunk"]) > 2 ** 17:
        raise ProductionRefused("chunk %d exceeds the memory bound of the run" % pc["chunk"])


def barrier_prefactor(states):
    """Fig 5 prefactor: Delta_G*_hom / k_B T = B / ln^2(Omega) at the reference inputs (medians).

    B = 16 pi gamma_nl^3 V_m^2 / (3 N_A^2 (k_B T)^3), at the prior medians of gamma_nl, V_m and T
    of the primary state; the references are recorded with it.
    """
    from nacre.physics.constants import AVOGADRO, BOLTZMANN
    if not states:
        return None
    joint = states[0][1].joint
    med = {}
    for sym in ("gamma_nl", "V_m", "T"):
        if sym not in joint.symbols:
            return None
        med[sym] = float(joint.priors[joint.symbols.index(sym)].ppf(0.5))
    b = 16 * np.pi * med["gamma_nl"] ** 3 * med["V_m"] ** 2 / (3 * AVOGADRO ** 2 * (BOLTZMANN * med["T"]) ** 3)
    return {"reference_gamma_nl": med["gamma_nl"], "V_m": med["V_m"], "T": med["T"], "B_kT": float(b),
            "reference": "prior medians of the primary state", "state": states[0][0],
            "units": {"reference_gamma_nl": "J m^-2", "V_m": "m^3 mol^-1", "T": "K", "B_kT": "1"}}
