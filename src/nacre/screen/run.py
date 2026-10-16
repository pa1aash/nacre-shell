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
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import chain, params_adapter, propagate, shapley, sobol, summary
from nacre.screen import thresholds as thr

CONFIG = Path("configs") / "preprint" / "screen.yaml"
THRESHOLDS = Path("configs") / "preprint" / "thresholds.yaml"
CONTRACT_CHECK = Path("configs") / "preprint" / "contract_check.json"
SCREEN_DIR = Path("results") / "preprint" / "screen"
DRYRUN_DIR = SCREEN_DIR / "dryrun"
LEDGER = Path("jobs") / "ledger" / "p0-w4.jsonl"
CHECKPOINT_TAG = "p0-cp3"


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


def link_inputs(link, symbols):
    """Theory symbols a link reads (sequester and nucleate include the upstream cycle)."""
    s = set(symbols)
    seq = list(chain.SEQ_CYCLE_INPUTS) if s >= set(chain.SEQ_CYCLE_INPUTS) else ["Delta_G_seq"]
    seq = [k for k in dict.fromkeys(seq + list(chain.SEQ_LOCAL_INPUTS))]
    if link == "anchor":
        return list(chain.ANCHOR_INPUTS)
    if link == "sequester":
        return seq
    if link == "nucleate":
        return [k for k in dict.fromkeys(seq + list(chain.NUC_INPUTS) + ["c_bulk"])]
    raise KeyError(link)


def link_joint(joint, link):
    """Joint prior of a link's inputs and of every input correlated with one of them."""
    sym = joint.symbols
    need = {sym.index(s) for s in link_inputs(link, sym) if s in sym}
    partners = {j for i in need for j in range(joint.k) if joint.spearman[i, j] != 0}
    idx = sorted(need | partners)
    return joint.marginal([joint.names[i] for i in idx])


def link_model(link):
    """Model of one link on the sensitivity scale of each quantity (chain.Output.scale)."""
    return chain.sensitivity_model(link)


def _round_quantiles(levels):
    return tuple(float(q) for q in levels)


def run_regime(rp, cfg, seed, links=None, dependence_check=None, thresholds=None, independence=False):
    """Results entry of one regime (schema $defs/regime). rp: params_adapter.RegimePriors."""
    joint = rp.joint.independent() if independence else rp.joint
    pc, sc, hc = cfg["propagation"], cfg["sobol"], cfg["shapley"]
    links = links or chain.evaluable_links(joint.symbols)
    mc_seq, sens_seq = np.random.SeedSequence(seed).spawn(2)
    outputs, masses = propagate.propagate_chain(chain.evaluate, joint, pc["draws_per_regime"],
                                                int(mc_seq.generate_state(1)[0]), pc["chunk"])
    levels = _round_quantiles(pc["quantiles"])
    out_links, convergences, designs = {}, [], []
    check = dependence_check if dependence_check is not None else cfg.get("dependence_check", False)
    agreement = {}
    for link, link_seq in zip(links, sens_seq.spawn(len(links))):
        meta = chain.OUTPUTS[link]
        quantities = {}
        for q, m in meta.items():
            values = outputs[link][q]
            if not np.any(np.isfinite(values)):
                continue
            quantities[q] = {"symbol": m.symbol, "units": m.units, **propagate.describe(values, levels)}
        names = [q for q in meta if q in quantities]
        sub = link_joint(joint, link)
        s_seq, h_seq, d_seq = link_seq.spawn(3)
        idx, design, conv = sobol.size_and_verify(
            link_model(link), sub, names, sc["target_ci_half_width"], int(s_seq.generate_state(1)[0]),
            pilot=sc["pilot_base"], n_bootstrap=sc["bootstrap"], confidence=sc["confidence"], key="symbol",
            chunk=pc["chunk"], max_base=sc["max_base"], on_cap="cap")
        players = sum(not p.is_fixed for p in sub.priors)
        kw = dict(n_var=hc["n_var"], n_outer=hc["n_outer"], n_inner=hc["n_inner"], key="symbol",
                  n_bootstrap=hc["bootstrap"], confidence=hc["confidence"], chunk=pc["chunk"],
                  design="subsets" if players <= hc["max_players_for_subsets"] else "permutations",
                  n_perm=hc["n_perm"])
        sh, sh_design = shapley.shapley_effects(link_model(link), sub, names, rng=np.random.default_rng(h_seq), **kw)
        entry = {"quantities": quantities, "sobol": idx, "shapley": sh, "threshold_evaluation": None,
                 "sensitivity_scale": {q: meta[q].scale for q in names}, "sobol_design": design,
                 "convergence": conv, "shapley_design": sh_design}
        if check and not sub.is_independent:
            rec, _, _ = shapley.dependence_check(link_model(link), sub, names, np.random.default_rng(d_seq), **kw)
            agreement[link] = rec["rank_agreement"]
        if thresholds is not None:
            entry["threshold_evaluation"] = thr.evaluate_link(link, outputs[link], thresholds)
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
        "boundary_mass": {lk: {q: m.as_dict() for q, m in d.items()} for lk, d in masses.items() if lk in out_links},
        "dependence": joint.dependence_record(),
        "dependence_check": {"alternative": "independent", "rank_agreement": agreement} if agreement else None,
        "convergence": {
            "target_ci_half_width": float(sc["target_ci_half_width"]),
            "base_samples": max(c["base_samples"] for c in convergences),
            "base_samples_doubled": max(c["base_samples_doubled"] for c in convergences),
            "max_ci_half_width": max(c["max_ci_half_width"] for c in convergences),
            "max_estimate_shift": max(c["max_estimate_shift"] for c in convergences),
            "converged": all(c["converged"] for c in convergences),
            "capped": any(c["capped"] for c in convergences)},
    }
    return regime


def load_config(root, path=CONFIG):
    return yaml.safe_load((Path(root) / path).read_text(encoding="utf-8"))


def _provenance(root, cfg, cfg_path, rp_list, thresholds_path, dry):
    sha, dirty = summary.git_state(root)
    prior_path = rp_list[0].path
    params_sha = None if dry else (_git(root, "log", "-1", "--format=%H", "--", _rel(root, prior_path)) or None)
    check = Path(root) / CONTRACT_CHECK
    contract = json.loads(check.read_text(encoding="utf-8")).get("contract_sha") if check.exists() else None
    th = Path(root) / thresholds_path
    th_source = None
    if th.exists():
        head = yaml.safe_load(th.read_text(encoding="utf-8")) or {}
        th_source = (head.get("source") or {}).get("sha") if isinstance(head, dict) else None
    return {"git_sha": sha, "git_dirty": dirty,
            "config_hash": summary.config_hash({"screen": cfg, "regimes": [r.regime for r in rp_list]}),
            "config_file": _rel(root, cfg_path), "config_file_hash": _sha256_file(cfg_path),
            "prior_file": _rel(root, prior_path), "prior_file_hash": rp_list[0].sha256,
            "params_sha": params_sha,
            "thresholds_file": _rel(root, th) if th.exists() else None,
            "thresholds_hash": _sha256_file(th) if th.exists() else None,
            "thresholds_source_sha": th_source,
            "contract_sha": contract,
            "schema_sha": _git(root, "log", "-1", "--format=%H", "--", "configs/preprint/results_schema.json") or None}


def _inputs_frozen(root, thresholds_path=THRESHOLDS):
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


def run(root, out_path, params_path=None, regimes=params_adapter.REGIMES, dry_run=True, allow_mock=False,
        config_path=CONFIG, independence=False, dependence_check=None, overrides=None):
    """Run the screen and write the results document; returns (path, doc)."""
    root = Path(root)
    out_path = Path(out_path)
    cfg_path = root / config_path
    cfg = load_config(root, config_path)
    for section, values in (overrides or {}).items():
        cfg[section] = {**cfg[section], **values}
    params_path = Path(params_path) if params_path else root / params_adapter.PRODUCTION_PARAMS
    if not dry_run:
        _inputs_frozen(root)
    rp_list = []
    for regime in regimes:
        try:
            rp_list.append(params_adapter.regime_priors(params_path, regime, allow_mock=allow_mock))
        except params_adapter.PriorFileError as exc:
            if "no sampled or fixed inputs" not in str(exc):
                raise
    if not rp_list:
        raise params_adapter.PriorFileError("no regime has sampled inputs in %s" % params_path)
    if dry_run:
        if not _inside(out_path, root / DRYRUN_DIR):
            raise ProductionRefused("dry-run output belongs under %s" % DRYRUN_DIR)
        thresholds = None
    else:
        production_guard(root, rp_list, out_path)
        thresholds = thr.load_thresholds(root / THRESHOLDS)
    seeds = np.random.SeedSequence(cfg["propagation"]["seed"]).spawn(len(params_adapter.REGIMES))
    seed_of = {r: int(s.generate_state(1)[0]) for r, s in zip(params_adapter.REGIMES, seeds)}
    regimes_out = {rp.regime: run_regime(rp, cfg, seed_of[rp.regime], dependence_check=dependence_check,
                                         thresholds=thresholds, independence=independence)
                   for rp in rp_list}
    prov = _provenance(root, cfg, cfg_path, rp_list, THRESHOLDS, dry_run)
    doc = summary.build(regimes_out, prov, mock=dry_run or any(rp.mock for rp in rp_list))
    path = summary.write(doc, out_path)
    if not dry_run:
        line = {"kind": "screen", "session": "P0-W4.3", "git_sha": prov["git_sha"], "git_dirty": prov["git_dirty"],
                "config": prov["config_file"], "config_hash": prov["config_hash"],
                "params_hash": prov["prior_file_hash"], "thresholds_hash": prov["thresholds_hash"],
                "contract_sha": prov["contract_sha"], "mock": False,
                "outputs": [{"path": _rel(root, path), "sha256": _sha256_file(path).split(":", 1)[1]}]}
        ledger = root / LEDGER
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, sort_keys=True) + "\n")
    return path, doc
