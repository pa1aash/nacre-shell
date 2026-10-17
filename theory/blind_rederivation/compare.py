"""Compare the blind re-derivation (results.py) with the registered theory.

Run from the repository root:

    uv run python theory/blind_rederivation/compare.py

The registered expressions are read from theory/contract.yaml (with @references expanded by the
contract checker's own parser), the fenced `thresholds` block of theory/thresholds.md and the
fenced `ignorance` block of theory/ignorance_priors.md; nothing is retyped here. Each target is
compared by symbolic equality where sympy can decide it, and otherwise numerically at random
admissible points to a relative tolerance of 10^-10.
"""

import importlib.util
import random
import re
import sys
from pathlib import Path

import sympy as sp
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "theory" / "tools"))
import check_contract as cc  # noqa: E402

HERE = Path(__file__).resolve().parent
RTOL = sp.Rational(1, 10**10)

# contract ids -> the blind agent's symbol names (I is the ionic strength in units of m_std)
RENAME = {"R_gas": "R", "J0_het": "J0", "t_proc": "t_p", "A_carb": "A_c", "P_pair": "P_c", "D_Ca": "D_c",
          "I_ionic": "I", "p_cred": "p", "m_CT": "m_CT", "m_CaT": "m_CaT"}


def load_blind():
    spec = importlib.util.spec_from_file_location("blind_results", HERE / "results.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.RESULTS


def to_plain(expr, extra=None):
    """Replace every symbol by a plain one named as the blind agent names it."""
    extra = extra or {}
    sub = {}
    for s in expr.free_symbols:
        name = RENAME.get(s.name, s.name)
        sub[s] = extra[name] if name in extra else sp.Symbol(name)
    return expr.xreplace(sub)


def plain(expr):
    return expr.xreplace({s: sp.Symbol(s.name) for s in expr.free_symbols})


def registered():
    symbols_doc = yaml.safe_load((ROOT / "theory" / "symbols.yaml").read_text(encoding="utf-8"))
    contract = yaml.safe_load((ROOT / "theory" / "contract.yaml").read_text(encoding="utf-8"))
    ctx = cc.Context(symbols_doc, contract)
    g = lambda name: to_plain(ctx.parse("@" + name), {"m_std": sp.Integer(1)})
    thr = yaml.safe_load(re.search(r"```thresholds\n(.*?)```", (ROOT / "theory" / "thresholds.md").read_text(), re.S).group(1))
    ign = yaml.safe_load(re.search(r"```ignorance\n(.*?)```", (ROOT / "theory" / "ignorance_priors.md").read_text(), re.S).group(1))
    c3b = [t for t in thr["links"]["C3"]["tests"] if t["id"] == "C3b"][0]
    N = sp.Symbol
    ref = {
        "f_theta": g("f_theta"),
        "cos_theta": g("cos_theta_young").subs(N("gamma_sl"), N("gamma_sl")),
        "dcos_dDgw": sp.diff(g("cos_theta_young"), N("Delta_gamma_w")),
        "cos_theta_deck": g("cos_theta_deck"),
        "Delta_mu": g("Delta_mu").subs(N("Omega"), N("a_Ca") * N("a_CO3") / N("K_sp")),
        "Delta_gamma_ads": g("Delta_gamma_ads"),
        "r_star": g("r_star"),
        "DG_hom": g("DG_hom"),
        "DG_het": g("DG_het"),
        "B_acc": g("B_acc"),
        "N_req": to_plain(ctx.parse(str(c3b["edge"]))).subs(N("p"), 1 - N("q0")),
        "q0": 1 - N("p"),
        "S_spread": g("S_spread"),
        "S_spread_from_cos": N("gamma_nl") * (sp.cos(N("theta")) - 1),
        "a_CO3_root": g("a_CO3_speciation"),
        "gamma_davies_z1": g("gamma_act_1"),
        "gamma_davies_z2": g("gamma_act_2"),
    }
    # df/dDelta_gamma_w through Young: d f/d cos * d cos/d Delta_gamma_w, written in theta
    c = N("c")
    fc = (2 + c) * (1 - c) ** 2 / 4
    ref["df_dDgw"] = (sp.diff(fc, c) * ref["dcos_dDgw"]).subs(c, sp.cos(N("theta")))
    br = ign["branches"]
    span = to_plain(ctx.parse(br["span"]))
    G = N("gamma_max")
    for k, key in (("complete", "P_complete"), ("partial", "P_partial"), ("non", "P_non")):
        ref[key] = to_plain(ctx.parse(br["masses_interior"][k])).subs(span, G)
    return ref


def admissible_point(syms, rnd):
    """Random positive rationals, with the orderings the targets need (|cos theta| < 1, Omega > 1,
    J0 t_p > N_req, interior branch cuts, q0 and p in (0, 1))."""
    v = {s: sp.Rational(rnd.randint(1, 97), rnd.randint(1, 23)) for s in syms}
    by = {s.name: s for s in syms}
    if "theta" in by:
        v[by["theta"]] = sp.Rational(rnd.randint(1, 98), 99) * sp.pi
    if "Omega" in by:
        v[by["Omega"]] = 1 + sp.Rational(rnd.randint(1, 50), 7)
    for name in ("p", "q0"):
        if name in by:
            v[by[name]] = sp.Rational(rnd.randint(1, 98), 99)
    if "gamma_max" in by and "gamma_sl" in by and "gamma_nl" in by:
        nl = sp.Rational(rnd.randint(1, 9), 10)
        v[by["gamma_nl"]] = nl
        v[by["gamma_sl"]] = nl + sp.Rational(rnd.randint(1, 9), 10)
        v[by["gamma_max"]] = v[by["gamma_sl"]] + nl + sp.Rational(rnd.randint(1, 9), 10)
    for name in ("Delta_gamma_w", "Delta_G_seq"):
        if name in by:
            v[by[name]] = sp.Rational(rnd.randint(-40, 40), 13)
    if "I" in by:
        v[by["I"]] = sp.Rational(rnd.randint(1, 50), 99)
    return v


def normalise(name, mine, ref):
    """Bring the two forms to the same variables without changing either expression:
    Delta_mu = k_B T ln Omega (the blind agent kept Delta_mu as a symbol); gamma_sn = gamma_sn0 +
    Delta_gamma_w (Young's convention); and for df/dDelta_gamma_w, cos(theta) from Young, because
    the blind form is written in the energies and the registered form in theta."""
    S = sp.Symbol
    sub = {S("Delta_mu"): S("k_B") * S("T") * sp.log(S("Omega")), S("gamma_sn"): S("gamma_sn0") + S("Delta_gamma_w")}
    mine, ref = mine.xreplace(sub), ref.xreplace(sub)
    if name == "df_dDgw":
        young = (S("gamma_sl") - S("gamma_sn0") - S("Delta_gamma_w")) / S("gamma_nl")
        ref = ref.rewrite(sp.cos).subs(sp.sin(S("theta")) ** 2, 1 - sp.cos(S("theta")) ** 2)
        ref = sp.expand(ref.subs(sp.sin(S("theta")), sp.sqrt(1 - sp.cos(S("theta")) ** 2))).subs(sp.cos(S("theta")), young)
    return mine, ref


def compare(name, mine, ref, rnd, npts=8):
    if mine is None:
        return "missing", "not in results.py"
    mine, ref = normalise(name, plain(sp.sympify(mine)), plain(sp.sympify(ref)))
    diff = mine - ref
    try:
        if sp.simplify(diff) == 0:
            return "agree", "symbolic equality"
    except Exception:
        pass
    syms = sorted(diff.free_symbols, key=lambda s: s.name)
    worst = 0
    for _ in range(npts):
        pt = admissible_point(syms, rnd)
        a, b = sp.N(mine.subs(pt), 40), sp.N(ref.subs(pt), 40)
        scale = max(abs(b), sp.Rational(1, 10**30))
        worst = max(worst, abs(a - b) / scale)
    ok = worst <= RTOL
    return ("agree" if ok else "DISAGREE"), "numeric at %d random admissible points, max relative difference %s" % (
        npts, sp.N(worst, 3))


def main():
    rnd = random.Random(20)
    ref = registered()
    blind = load_blind()
    rows = []
    for name in ref:
        verdict, how = compare(name, blind.get(name), ref[name], rnd)
        rows.append((name, verdict, how))
        print("%-18s %-9s %s" % (name, verdict, how))
    extra = sorted(set(blind) - set(ref))
    if extra:
        print("not compared (no registered counterpart):", extra)
    bad = [r for r in rows if r[1] != "agree"]
    print("\n%d of %d expressions agree" % (len(rows) - len(bad), len(rows)))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
