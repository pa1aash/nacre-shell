"""Retrodiction entry point for P0-W2.3: predicted barrier differences of the frozen cases.

Reads preprint/retrodiction/cases.yaml (schema retro-cases/v1, preprint/retrodiction/SCHEMA.md)
and returns, for every usable case, the C3 heterogeneous barrier of the test and of the
reference surface in k_B T and their per-draw difference Delta = barrier(test) -
barrier(reference), with its median and 90 % interval (q05, q95), under the registered
contract (v3 bookkeeping: Omega is the bulk Omega of the pair; enrichment never raises it).

Each input is mapped to its own interface (lane note N11, decision D17):
  * crystal-template adhesion (a binding free energy per contact area, dG_bind or E_int over
    A_c, or a work of adhesion W_adh) -> the template-nucleus energy gamma_sn by Dupre,
    W = gamma_sl + gamma_nl - gamma_sn, so that cos(theta) = W / gamma_nl - 1;
  * Ca2+ binding (a measured near-surface c_local with the site density Gamma_s and layer
    thickness delta_s, or Delta_G_seq) -> the template-liquid energy gamma_sl through the
    Gibbs-Langmuir term Delta_gamma_ads = -R T (Gamma_s ln(1 + x) - delta_s c_bulk), so that
    cos(theta) = cos_theta0 + Delta_gamma_ads / gamma_nl with the Ca-free contact common to both
    surfaces (a shared nuisance);
  * substrate surface-energy components (OWRK) -> gamma_sl against water, with gamma_sn common;
  * a simulated net interfacial energy gamma_net -> f(theta) = (gamma_net / gamma_nl)^3.
A mapping that raises Omega by the local concentration (Omega_local) is refused: under the
contract's uniform chemical potential the driving force is the bulk one.

Label symmetry (criterion.md, condition 4): shared draws (Omega, T, gamma_nl, V_m, contact
area, nuisances) are drawn once per pair; the function that computes a barrier sees the inputs
of one surface and the shared draws only. The swap check recomputes every case with test and
reference exchanged on the same draws and confirms Delta changes sign draw by draw. The
permutation null (cp3 R9, descriptive only) reassigns the test-surface inputs among cases that
share an input mapping and reports the distribution of the number of correct verdicts.

Nothing here runs a case: the run is P0-W2.3's. Numbers come from the cases file and the
parameter table only; the SI conversion is nacre.screen.units (a ``kT`` unit is the only one
resolved here, with the pair's temperature).
"""
import hashlib
import math
from pathlib import Path

import numpy as np
import yaml

from nacre.physics.constants import AVOGADRO, BOLTZMANN, GAS_CONSTANT
from nacre.screen import units
from nacre.screen.boundary import clip_cos_theta

LEVELS = (0.05, 0.5, 0.95)
#: input symbol -> (interface, mapping), unless the input names its interface explicitly.
MAPPINGS = {"dG_bind": ("gamma_sn", "dupre"), "E_int": ("gamma_sn", "dupre"), "W_adh": ("gamma_sn", "dupre"),
            "gamma_s_owrk": ("gamma_sl", "owrk"), "c_local": ("gamma_sl", "gibbs_langmuir"),
            "Delta_G_seq": ("gamma_sl", "gibbs_langmuir"), "gamma_net_sim": ("f_theta", "net")}
SURFACE_SI = {"dG_bind": "J mol^-1", "E_int": "J", "W_adh": "J m^-2", "c_local": "mol m^-3", "Delta_G_seq": "J mol^-1",
              "gamma_net_sim": "J m^-2", "gamma_s_owrk": "J m^-2", "Gamma_s": "mol m^-2", "delta_s": "m"}
SHARED_SI = {"A_c": "m^2", "T": "K", "gamma_nl": "J m^-2", "V_m": "m^3 mol^-1", "c_bulk": "mol m^-3",
             "Gamma_s": "mol m^-2", "delta_s": "m", "gamma_w": "J m^-2", "K_sp": "1", "Omega": "1",
             "Omega_bulk": "1", "cos_theta_ref": "1", "cos_theta": "1", "gamma_sn": "J m^-2"}
REFUSED_MAPS = ("Omega_local",)


class CaseError(ValueError):
    """A case cannot be mapped to the contract (unknown input, refused mapping, missing key)."""


# ------------------------------------------------------------------ draws


def _si(value, unit, target, T=None):
    """value in unit -> target; 'kT' (per contact) is resolved with the pair temperature T."""
    if str(unit).strip() == "kT":
        if T is None:
            raise CaseError("an input in kT needs the pair temperature")
        return np.asarray(value, float) * BOLTZMANN * T * (AVOGADRO if units.dimension(target) == units.dimension(
            "J mol^-1") else 1.0)
    try:
        return units.convert(value, unit, target)
    except units.UnitError as exc:
        raise CaseError(str(exc)) from None


def draw(spec, n, rng):
    """n draws of an input distribution in its stated unit (SCHEMA.md 3.4)."""
    d = spec.get("distribution")
    if d is None:
        v = spec["value"]
        if isinstance(v, dict):
            return {k: np.full(n, float(x)) for k, x in v.items()}
        return np.full(n, float(v))
    t = d["type"]
    if t == "normal":
        return d["mean"] + d["sd"] * rng.standard_normal(n)
    if t == "uniform":
        return rng.uniform(d["low"], d["high"], n)
    if t == "loguniform":
        return np.exp(rng.uniform(math.log(d["low"]), math.log(d["high"]), n))
    if t == "uniform_log":                       # sigma = ln(Omega) uniform
        return np.exp(rng.uniform(d["low_sigma"], d["high_sigma"], n))
    raise CaseError("unknown distribution type %r" % t)


def _prior_from_table(key, table, n, rng):
    """Draws of a lit/params.yaml key in the SI unit of its symbol (via the screen's adapter)."""
    from nacre.screen import params_adapter
    e = (table.get("params") or {}).get(key)
    if e is None:
        raise CaseError("params_key %r is not in the parameter table (a BLOCKED precondition of W2.3)" % key)
    fam, params = params_adapter._family_params(e.get("prior") or {}, key)
    if params is None:
        raise CaseError("params_key %r has no sampled or fixed prior (%s)" % (key, fam))
    unit, params = params_adapter.to_si(e["symbol"], e["unit"], e.get("transform", "none"), params, key)
    from nacre.screen.priors import Prior
    return Prior(key, e["symbol"], unit, fam, params, "", e.get("transform", "none")).sample(rng, n), e["symbol"]


def shared_draws(case, doc, table, n, rng):
    """Shared draws of a pair: shared_priors of the file and the case's shared inputs, in SI."""
    out = {}
    for name, sp in (doc.get("shared_priors") or {}).items():
        sym = sp.get("symbol", name)
        if "params_key" in sp:
            if table is None:
                raise CaseError("shared prior %s names params_key %r: a parameter table is needed" % (name, sp["params_key"]))
            out[sym], _ = _prior_from_table(sp["params_key"], table, n, rng)
        else:
            v = draw(sp, n, rng)
            out[sym] = {k: _si(x, sp["unit"], "J m^-2") for k, x in v.items()} if isinstance(v, dict) \
                else _si(v, sp.get("unit", "1"), SHARED_SI.get(sym, "1"))
    for inp in case["inputs"]:
        if inp["role"] != "shared":
            continue
        sym = inp["symbol"]
        if sym not in SHARED_SI:
            raise CaseError("%s: unknown shared input %r" % (case["id"], sym))
        if any(r in str(inp.get("maps_to", "")) for r in REFUSED_MAPS) and sym != "Omega_bulk":
            raise CaseError("%s: %s maps through Omega_local, which contract v3 refuses" % (case["id"], sym))
        out[sym] = _si(draw(inp, n, rng), inp.get("unit", "1"), SHARED_SI[sym], out.get("T"))
    if "Omega_bulk" in out and "Omega" not in out:
        out["Omega"] = out.pop("Omega_bulk")
    for need in ("Omega", "T", "gamma_nl", "V_m"):
        if need not in out:
            raise CaseError("%s: shared input %s is not supplied" % (case["id"], need))
    return out


def surface_inputs(case, role, n, rng, T):
    """{symbol: SI draws} of one surface's inputs, with the mapping each one uses."""
    out, kinds = {}, set()
    for inp in case["inputs"]:
        if inp["role"] != role:
            continue
        if any(r in str(inp.get("maps_to", "")) for r in REFUSED_MAPS):
            raise CaseError("%s: %s maps through Omega_local, which contract v3 refuses (map Ca2+ binding to gamma_sl)"
                            % (case["id"], inp["symbol"]))
        sym = inp["symbol"]
        if sym not in MAPPINGS and sym not in SURFACE_SI:
            raise CaseError("%s: no interface mapping for input %r" % (case["id"], sym))
        if sym in MAPPINGS:
            kinds.add(inp.get("interface_mapping") or MAPPINGS[sym][1])
        v = draw(inp, n, rng)
        out[sym] = {k: _si(x, inp["unit"], "J m^-2") for k, x in v.items()} if isinstance(v, dict) \
            else _si(v, inp.get("unit", "1"), SURFACE_SI[sym], T)
    if len(kinds) != 1:
        raise CaseError("%s: the %s surface needs exactly one interface mapping, got %s" % (case["id"], role, sorted(kinds)))
    return out, kinds.pop()


# ------------------------------------------------------------------ one surface


def _owrk_gamma_sl(comp, water):
    """gamma_sl against water from the OWRK components of the solid (J m^-2)."""
    gs = comp["polar"] + comp["dispersive"]
    gw = water["gamma_w"]
    return gs + gw - 2.0 * (np.sqrt(comp["dispersive"] * water["gamma_w_dispersive"])
                            + np.sqrt(comp["polar"] * water["gamma_w_polar"]))


def surface_ratio(mapping, x, shared):
    """Young ratio (or f directly) of one surface from its own inputs and the shared draws only.

    Returns ("ratio", array) or ("f", array).
    """
    nl = shared["gamma_nl"]
    if mapping == "dupre":
        if "W_adh" in x:
            w = np.abs(x["W_adh"])
        elif "dG_bind" in x:
            w = np.abs(x["dG_bind"]) / (AVOGADRO * shared["A_c"])
        else:
            w = np.abs(x["E_int"]) / shared["A_c"]
        return "ratio", w / nl - 1.0
    if mapping == "net":
        return "f", (x["gamma_net_sim"] / nl) ** 3
    if mapping == "owrk":
        sl = _owrk_gamma_sl(x["gamma_s_owrk"], shared["gamma_w"])
        if "gamma_sn" in shared:
            return "ratio", (sl - shared["gamma_sn"]) / nl
        return "ratio", (sl - shared["_gamma_sn_anchor"]) / nl
    if mapping == "gibbs_langmuir":
        gs = x.get("Gamma_s", shared.get("Gamma_s"))
        ds = x.get("delta_s", shared.get("delta_s"))
        cb, t = shared["c_bulk"], shared["T"]
        if gs is None or ds is None:
            raise CaseError("the Gibbs-Langmuir mapping needs Gamma_s and delta_s")
        c_max = gs / ds
        if "c_local" in x:
            with np.errstate(divide="ignore", invalid="ignore"):
                odds = np.where(x["c_local"] < c_max, x["c_local"] / (c_max - x["c_local"]), np.nan)
        else:
            odds = np.exp(-x["Delta_G_seq"] / (GAS_CONSTANT * t)) * cb / c_max
        d_ads = -GAS_CONSTANT * t * (gs * np.log1p(odds) - ds * cb)
        base = shared.get("cos_theta", shared.get("cos_theta_ref"))
        if base is None:
            raise CaseError("the Gibbs-Langmuir mapping needs the shared Ca-free contact (cos_theta)")
        return "ratio", base + d_ads / nl
    raise CaseError("unknown mapping %r" % mapping)


def surface_barrier(mapping, x, shared):
    """Heterogeneous barrier of one surface in k_B T at the pair's bulk Omega; (barrier, BoundaryMass)."""
    kind, v = surface_ratio(mapping, x, shared)
    if kind == "ratio":
        c, mass = clip_cos_theta(v)
        f = (2.0 + c) * (1.0 - c) ** 2 / 4.0
    else:
        f = np.clip(v, 0.0, 1.0)
        _, mass = clip_cos_theta(np.where(v >= 1.0, -2.0, np.where(v <= 0.0, 2.0, 0.0)))
    kt = BOLTZMANN * shared["T"]
    with np.errstate(divide="ignore", invalid="ignore"):
        hom = 16.0 * np.pi * shared["gamma_nl"] ** 3 * shared["V_m"] ** 2 / (
            3.0 * AVOGADRO ** 2 * kt ** 3 * np.log(shared["Omega"]) ** 2)
    hom = np.where(shared["Omega"] > 1.0, hom, np.nan)
    return f * hom, mass


# ------------------------------------------------------------------ a case


def _quant(v):
    v = v[np.isfinite(v)]
    if not v.size:
        return None
    q = np.quantile(v, LEVELS)
    return {"q05": float(q[0]), "median": float(q[1]), "q95": float(q[2])}


def verdict(delta_q, relation):
    """criterion.md section 2; an undetermined prediction (no finite draw) counts as a miss."""
    if delta_q is None:
        return "undetermined"
    lo, hi = delta_q["q05"], delta_q["q95"]
    if relation == "test_higher_barrier":
        return "correct" if lo > 0 else ("incorrect" if hi < 0 else "inconclusive")
    return "correct" if hi < 0 else ("incorrect" if lo > 0 else "inconclusive")


def prepare(case, doc, table, n, rng):
    """The shared draws and both surfaces' inputs of a case (drawn once; reused by the checks)."""
    shared = shared_draws(case, doc, table, n, rng)
    test, m_t = surface_inputs(case, "test", n, rng, shared["T"])
    ref, m_r = surface_inputs(case, "reference", n, rng, shared["T"])
    if m_t != m_r:
        raise CaseError("%s: test and reference use different mappings (%s, %s)" % (case["id"], m_t, m_r))
    if m_t == "owrk" and "gamma_sn" not in shared:
        # the frozen nuisance cos_theta_ref is anchored on the reference surface; it is turned into
        # a shared gamma_sn draw here, before any barrier is computed, so both surfaces see the same one
        ref_sl = _owrk_gamma_sl(ref["gamma_s_owrk"], shared["gamma_w"])
        shared["_gamma_sn_anchor"] = ref_sl - shared["gamma_nl"] * shared["cos_theta_ref"]
    return shared, test, ref, m_t


def evaluate_case(case, shared, test, ref, mapping):
    """Barriers, Delta and the verdict of one prepared case."""
    bt, mt = surface_barrier(mapping, test, shared)
    br, mr = surface_barrier(mapping, ref, shared)
    delta = bt - br
    dq = _quant(delta)
    fin = np.isfinite(delta)
    bm = (mt + mr)
    return {"id": case["id"], "termination": case.get("termination"), "negative": case.get("negative"),
            "observed_relation": case["outcome"]["relation"], "mapping": mapping,
            "interface": {"dupre": "gamma_sn", "owrk": "gamma_sl", "gibbs_langmuir": "gamma_sl",
                          "net": "f_theta"}[mapping],
            "barrier_test": _quant(bt), "barrier_reference": _quant(br), "delta": dq,
            "p_test_higher": float(np.mean(delta[fin] > 0)) if fin.any() else None,
            "boundary_mass": float(bm.total_fraction) if bm.n_finite else 0.0,
            "verdict": verdict(dq, case["outcome"]["relation"]), "_delta": delta}


def swap_check(case, shared, test, ref, mapping, delta):
    """Delta with test and reference exchanged on the same draws must be -Delta, draw by draw."""
    bt, _ = surface_barrier(mapping, ref, shared)
    br, _ = surface_barrier(mapping, test, shared)
    swapped = bt - br
    fin = np.isfinite(delta) & np.isfinite(swapped)
    err = float(np.max(np.abs(swapped[fin] + delta[fin]))) if fin.any() else 0.0
    return {"max_abs_sum": err, "holds": err == 0.0 and bool(np.array_equal(np.isfinite(delta), np.isfinite(swapped)))}


def pass_threshold(n_cases, alpha=0.05):
    """Smallest k with P(X >= k | N, 1/2) <= alpha (criterion.md section 3)."""
    for k in range(n_cases + 1):
        if sum(math.comb(n_cases, j) for j in range(k, n_cases + 1)) / 2 ** n_cases <= alpha:
            return k
    return None


def permutation_null(prepared, n_perm, rng):
    """cp3 R9 (descriptive): the test-surface inputs reassigned among cases with the same mapping.

    Each permutation keeps every case's shared draws and reference inputs and gives it the test
    inputs of another case of the same mapping; the number of correct verdicts is recorded.
    """
    groups = {}
    for cid, (case, shared, test, ref, mapping) in prepared.items():
        groups.setdefault(mapping, []).append(cid)
    counts = np.zeros(n_perm, dtype=int)
    for i in range(n_perm):
        for mapping, ids in groups.items():
            perm = rng.permutation(len(ids))
            for j, cid in enumerate(ids):
                case, shared, _, ref, _ = prepared[cid]
                donor = prepared[ids[perm[j]]][2]
                if not _compatible(donor, shared):
                    continue
                r = evaluate_case(case, shared, donor, ref, mapping)
                counts[i] += r["verdict"] == "correct"
    return counts


def _compatible(donor, shared):
    n = len(next(iter(shared.values()))) if shared else 0
    return all((len(v) == n) if not isinstance(v, dict) else all(len(a) == n for a in v.values()) for v in donor.values())


def run_cases(cases_path, params_path=None, draws=20000, seed=0, n_perm=1000, criterion_path=None):
    """Predicted barrier differences of every usable case; the result record of SCHEMA.md section 5.

    Returns the record with the swap check and the permutation null; nothing is written.
    """
    cases_path = Path(cases_path)
    raw = cases_path.read_bytes()
    doc = yaml.safe_load(raw)
    if doc.get("schema") != "retro-cases/v1":
        raise CaseError("cases file is not retro-cases/v1")
    table = yaml.safe_load(Path(params_path).read_text(encoding="utf-8")) if params_path else None
    root = np.random.SeedSequence(seed)
    usable = [c for c in doc["cases"] if c.get("status") == "usable"]
    prepared, results, swaps = {}, [], {}
    for case, seq in zip(usable, root.spawn(len(usable))):
        rng = np.random.default_rng(seq)
        shared, test, ref, mapping = prepare(case, doc, table, draws, rng)
        r = evaluate_case(case, shared, test, ref, mapping)
        swaps[case["id"]] = swap_check(case, shared, test, ref, mapping, r.pop("_delta"))
        prepared[case["id"]] = (case, shared, test, ref, mapping)
        r["swap_check"] = swaps[case["id"]]
        results.append(r)
    n_cases = len(results)
    correct = sum(r["verdict"] == "correct" for r in results)
    k = pass_threshold(n_cases)
    counts = permutation_null(prepared, n_perm, np.random.default_rng(root.spawn(1)[0])) if n_perm else np.zeros(0)
    conclusive = [r for r in results if r["verdict"] in ("correct", "incorrect")]
    studies = {}
    for case, r in zip(usable, results):
        studies.setdefault(case["study"], []).append(r["verdict"] == "correct")
    summary = {"N": n_cases, "correct": correct,
               "incorrect": sum(r["verdict"] in ("incorrect", "undetermined") for r in results),
               "inconclusive": sum(r["verdict"] == "inconclusive" for r in results),
               "undetermined": sum(r["verdict"] == "undetermined" for r in results), "k": k,
               "chance_probability": (sum(math.comb(n_cases, j) for j in range(k, n_cases + 1)) / 2 ** n_cases
                                      if k is not None else None),
               "pass": k is not None and correct >= k,
               "conclusive_only": {"n": len(conclusive), "correct": sum(r["verdict"] == "correct" for r in conclusive),
                                   "descriptive": True},
               "study_level": {"studies": len(studies), "all_correct": sum(all(v) for v in studies.values()),
                               "descriptive": True},
               "swap_check": {"holds": all(s["holds"] for s in swaps.values()),
                              "max_abs_sum": max((s["max_abs_sum"] for s in swaps.values()), default=0.0)},
               "permutation_null": ({"n_perm": int(n_perm), "mean_correct": float(counts.mean()),
                                     "p_value_ge_observed": float(np.mean(counts >= correct)),
                                     "counts": np.bincount(counts, minlength=n_cases + 1).tolist(),
                                     "descriptive": True, "rule": "cp3 R9: reported as a descriptive control"}
                                    if n_perm else None)}
    rec = {"schema": "retro-results/v1", "mock": False,
           "cases_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(), "draws": int(draws), "seed": int(seed),
           "levels": list(LEVELS), "cases": results, "summary": summary}
    if criterion_path:
        rec["criterion_sha256"] = "sha256:" + hashlib.sha256(Path(criterion_path).read_bytes()).hexdigest()
    return rec
