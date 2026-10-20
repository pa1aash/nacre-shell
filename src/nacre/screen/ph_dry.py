"""Dry run of the generic mineral screen (PH-W4.1): the path from a parameter table to K1 to K4, on mock priors.

    python -m nacre.screen ph-dryrun --mineral hap --mock [--k1-override] [--draws N]

A dry run shows that the path runs end to end and that its document conforms to the results schema. It
reads a mock table, propagates the chain with a Mineral object, evaluates K2, K3, K4 and the deletion test
(nacre.screen.kscreen), reads K1 from W5's ladder file, and writes only under results/preprint/screen/dryrun_ph/.
It is never reported, tunes nothing and registers nothing. K1 is read from a ladder in the v2 layout (default: the mock
ladder kscreen.MOCK_LADDER); since PH-W4.2a the cp4 F1 rule lets an unresolved phase proceed, so no override is
needed (the flag is kept and recorded). A Ca orthophosphate also gets its stage rows (F5, schema v5).
"""
import resource
import time
from functools import partial
from pathlib import Path

import numpy as np
import yaml

from nacre.physics import film
from nacre.screen import chain, kscreen, params_adapter, ph_rows, propagate, run, summary
from nacre.screen import mineral as mineral_mod

DRYRUN_PH = run.DRYRUN_PH_DIR
MOCK_TABLE = Path("configs") / "preprint" / "mock_params_ph.yaml"
CONTROL_PREFIX = "ctl_"                      # table keys that belong to the bare-oxide control only
DEFAULT_DRAWS = 2 ** 13
#: Sensitivity analysis sizes of a dry run: small, because a dry run shows the path and reports nothing.
SMALL = {"sobol": {"pilot_base": 128, "bootstrap": 40, "max_base": 1024},
         "shapley": {"n_var": 2000, "n_outer": 60, "n_inner": 2, "n_perm": 40, "bootstrap": 40, "max_players_for_subsets": 8},
         "dependence_check": False}


class DryRunRefused(RuntimeError):
    """A dry run was asked to do something a dry run never does."""


def mineral_keys(minerals):
    """Every table key that belongs to one mineral (its K_sp, V_m, gamma set, n and supplied inputs)."""
    keys = set()
    for m in minerals.values():
        keys |= {m.ksp_key, m.vm_key, *m.gamma_keys.values(), *m.input_keys.values()}
        if m.n_hyd_key:
            keys.add(m.n_hyd_key)
    return keys


def bindings_for(doc, mineral, minerals, drop=(), control=False):
    """{symbol: table key} of one mineral's chain inputs from the table.

    Every key that is not specific to a mineral is bound to its own symbol; the mineral binds K_sp, V_m, gamma_nl
    and the like to its own keys. ``control`` binds the ctl_* keys and drops the template symbols ``drop``.
    """
    specific = mineral_keys(minerals)
    own = {"K_sp": mineral.ksp_key, "V_m": mineral.vm_key, "gamma_nl": mineral.gamma_keys.get("gamma_nl"),
           **dict(mineral.input_keys)}
    if mineral.n_hyd_key:
        own["n_hyd"] = mineral.n_hyd_key
    out = {}
    for key, e in doc["params"].items():
        sym = e["symbol"]
        is_control_key = key.startswith(CONTROL_PREFIX)
        if key in specific or (is_control_key and not control) or (control and not is_control_key and sym in drop):
            continue
        out[sym] = key
    for sym, key in own.items():
        if key is not None and key in doc["params"]:
            out[sym] = key
    return out


def load_priors(params_path, mineral, minerals, drop=(), control=False, allow_mock=True):
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    b = bindings_for(doc, mineral, minerals, drop, control)
    return params_adapter.regime_priors(params_path, "R-slurry", allow_mock, bindings=b, absent="gap")


def fixed_value(rp, symbol):
    for p in rp.joint.priors:
        if p.symbol == symbol and p.is_fixed:
            return float(p.params["value"])
    return None


def thickness_bound(rp):
    """d_max (m) from the fixed R_A_max and rho_e of the table (the ohmic bound); None when either is absent."""
    r, rho = fixed_value(rp, "R_A_max"), fixed_value(rp, "rho_e")
    if r is None or rho is None:
        return None
    return float(film.ohmic_thickness_bound(r, rho))


def dosed(evaluate, ln_dose, mineral):
    """The chain at a dose scaled by exp(ln D) at fixed ratio: Ca_T and P_T, or the supplied activities."""
    factor = float(np.exp(ln_dose))
    names = ("Ca_T", "P_T") if mineral.speciation else ("a_Ca", mineral.x_symbol, "c_bulk")

    def model(x):
        y = dict(x)
        for k in names:
            if k in y:
                y[k] = np.asarray(y[k], dtype=float) * factor
        return evaluate(y)
    return model


def propagate_doses(rp, mineral, ln_doses, n, seed, chunk):
    """{ln D: chain outputs} on the same draws (common random numbers across the dose axis)."""
    base = partial(chain.evaluate, mineral=mineral)
    out = {}
    for d in ln_doses:
        o, _ = propagate.propagate_chain(dosed(base, d, mineral), rp.joint, n, seed, chunk)
        out[float(d)] = o
    return out


def small_config(cfg, draws):
    c = dict(cfg)
    c["propagation"] = {**cfg["propagation"], "draws_per_regime": int(draws), "chunk": min(int(draws), cfg["propagation"]["chunk"])}
    for k, v in SMALL.items():
        c[k] = {**cfg[k], **v} if isinstance(v, dict) else v
    return c


def peak_mb():
    """Peak resident set of this process in MB (ru_maxrss is bytes on macOS, kilobytes on Linux)."""
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    import sys
    return r / 2 ** 20 if sys.platform == "darwin" else r / 2 ** 10


def run_mineral(root, name, out_path, params_path=None, allow_mock=False, k1_override=False, draws=DEFAULT_DRAWS,
                sensitivity=True, ladder_path=None, seed=None):
    """One dry run: returns (path, document, stats). Refuses output outside dryrun_ph/ and any non-mock table."""
    t0 = time.perf_counter()
    root, out_path = Path(root), Path(out_path)
    if not run._inside(out_path, root / DRYRUN_PH):
        raise DryRunRefused("a phosphate dry run writes only under %s, got %s" % (DRYRUN_PH, out_path))
    cfg_path = root / run.CONFIG
    cfg = run.load_config(root)
    minerals = mineral_mod.registry(cfg)
    if name not in minerals:
        raise DryRunRefused("unknown mineral %r (registered: %s)" % (name, sorted(minerals)))
    m = minerals[name]
    k = kscreen.k_config(cfg)
    params_path = Path(params_path) if params_path else root / MOCK_TABLE
    doc, _ = params_adapter.read_table(params_path, allow_mock)
    if not doc["mock"]:
        raise DryRunRefused("a dry run reads a mock table only")
    drop = ((cfg.get("controls") or {}).get("bare_oxide") or {}).get("drop") or []
    rp = load_priors(params_path, m, minerals, allow_mock=allow_mock)
    ctl = load_priors(params_path, m, minerals, drop=drop, control=True, allow_mock=allow_mock)
    seed = int(seed if seed is not None else cfg["propagation"]["seed"])
    chunk = min(int(draws), int(cfg["propagation"]["chunk"]))
    ln_doses = [float(d) for d in k["ln_dose_axis"]]
    links = chain.evaluable_links(rp.joint.symbols, m)
    if "nucleate" not in links:
        raise DryRunRefused("the nucleate link is not evaluable for %s from %s; unsampled: %s"
                            % (name, params_path, dict(rp.unsampled)))
    regimes = None
    if sensitivity:
        entry = run.run_regime(rp, small_config(cfg, draws), seed, mineral=m)
        entry["prior_set"] = "table"
        regimes = {"R-slurry": entry}
    tmpl = propagate_doses(rp, m, ln_doses, draws, seed, chunk)
    doses = {d: {"slurry": kscreen.samples(o)} for d, o in tmpl.items()}
    control_doses = None
    if "nucleate" in chain.evaluable_links(ctl.joint.symbols, m):
        control_doses = {d: {"slurry": kscreen.samples(o)}
                         for d, o in propagate_doses(ctl, m, ln_doses, draws, seed, chunk).items()}
    ladder = kscreen.read_k1(root / (ladder_path or kscreen.MOCK_LADDER))
    ref = doses[ln_doses[len(ln_doses) // 2]]
    p = {key: k[key] for key in ("p_cred", "p_deg", "m_cos", "m_S")}
    p["admissible"] = bool(k.get("admissible", True))
    rec = kscreen.evaluate_mineral(m, ladder, doses, p, control_doses=control_doses, d_max=thickness_bound(rp),
                                   k1_override=k1_override)
    rec["dry_run"] = {"mock_table": str(params_path.relative_to(root)) if params_path.is_relative_to(root) else str(params_path),
                      "draws": int(draws), "seed": seed, "ln_dose_axis": ln_doses, "k1_gate_overridden": bool(k1_override),
                      "unsampled": dict(rp.unsampled), "links_evaluable": links,
                      "note": "path check on mock priors; never reported; tunes nothing"}
    prov = run._provenance(root, cfg, cfg_path, [rp], run.THRESHOLDS, True)
    prov["run_label"] = "ph-dryrun %s" % name
    prov["session"] = "PH-W4.2a"
    rows = None
    if m.speciation == "phosphate" and m.chain_length_n is None:
        # F5: a Ca orthophosphate used as formed at the low-cutoff class (slurry row K2 to K4, cell row K1)
        rows = ph_rows.ortho_low_cutoff_rows("%s_as_formed" % name, m.k1_phase or name, rec, ladder, m)
        problems = ph_rows.check_presentation(rows)
        if problems:
            raise DryRunRefused("presentation rule: %s" % problems)
    document = summary.build(regimes, prov, mock=True, extensions={"p0-w4": {"ph_screen": rec}}, ph_rows=rows)
    if regimes is None:
        document.pop("regimes", None)
    path = summary.write(document, out_path)
    stats = {"mineral": name, "seconds": time.perf_counter() - t0, "peak_mb": peak_mb(), "path": str(path)}
    return path, document, stats
