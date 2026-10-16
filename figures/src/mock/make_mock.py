"""Generate the mock inputs figures/src/mock/fig4.json ... fig7.json.

MOCK DATA. Every number here is synthetic, chosen only to exercise the templates; none is a
result, a literature value or a parameter of the study. Each file carries "mock": true and the
figure builder writes its output only to figures/out/mock/.

Run: uv run python figures/src/mock/make_mock.py
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
SEED = 20261016
NOTE = "MOCK: synthetic values to exercise the template; not a result"


def _round(x, n=4):
    return [round(float(v), n) for v in x]


def _write(name, doc):
    (HERE / name).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")


def _shape_factor(theta_deg):
    c = np.cos(np.radians(theta_deg))
    return (2 + c) * (1 - c) ** 2 / 4


def fig4(rng):
    threshold = 60.0
    cases = []
    for i in range(8):
        formed = i % 2 == 0
        centre = threshold * (0.45 if formed else 1.8) * float(np.exp(rng.normal(0.0, 0.35)))
        spread = float(np.exp(rng.uniform(0.15, 0.45)))
        cases.append({
            "id": "M%d" % (i + 1),
            "label": "M%d" % (i + 1),
            "source": "mock",
            "predicted": round(centre, 2),
            "predicted_lo": round(centre / spread, 2),
            "predicted_hi": round(centre * spread, 2),
            "observed": "layer_formed" if formed else "no_layer",
        })
    return {"mock": True, "schema": "fig4-retrodiction/assumed-v0", "note": NOTE,
            "quantity": {"symbol": "barrier_het"},
            "threshold": {"symbol": "barrier_crit", "value": threshold},
            "cases": cases}


def fig5(_rng):
    theta = np.arange(5.0, 175.0 + 1e-9, 2.5)
    s = np.geomspace(1.5, 100.0, 60)
    b = 400.0
    barrier = b * _shape_factor(theta)[None, :] / np.log(s)[:, None] ** 2
    return {"mock": True, "schema": "fig5-barrier-map/assumed-v0", "note": NOTE,
            "wetting_angle_deg": _round(theta, 2),
            "supersaturation": _round(s, 4),
            "barrier_kT": [_round(row, 4) for row in barrier],
            "thresholds_kT": [40.0, 80.0]}


def fig6(rng):
    symbols = ["interfacial_energy", "wetting_angle", "ln_supersaturation", "molecular_volume",
               "temperature", "kinetic_prefactor"]
    weights = np.array([0.55, 0.22, 0.12, 0.05, 0.02, 0.01])
    params = []
    for sym, w in zip(symbols, weights):
        s1 = float(w * rng.uniform(0.7, 0.95))
        st = float(min(1.0, w * rng.uniform(1.05, 1.4)))
        h1, ht = float(rng.uniform(0.01, 0.03)), float(rng.uniform(0.01, 0.04))
        params.append({
            "symbol": sym,
            "S1": round(s1, 4), "S1_ci": [round(s1 - h1, 4), round(s1 + h1, 4)],
            "ST": round(st, 4), "ST_ci": [round(st - ht, 4), round(st + ht, 4)],
            "required_precision": round(float(0.02 / np.sqrt(w)), 4),
        })
    return {"mock": True, "schema": "fig6-sobol/assumed-v0", "note": NOTE,
            "output": "barrier_het", "parameters": params}


def _regime(rid, p1, p2, e0, slope, ph=(0.0, 14.0), e=(-2.5, 1.5)):
    lo, hi = ph
    elo, ehi = e

    def line(x):
        return e0 - slope * x

    domains = [
        {"species": "mock-solid-1", "phase": "solid",
         "polygon": [[lo, elo], [hi, elo], [hi, line(hi)], [lo, line(lo)]]},
        {"species": "mock-aqueous-1", "phase": "aqueous",
         "polygon": [[lo, line(lo)], [p1, line(p1)], [p1, ehi], [lo, ehi]]},
        {"species": "mock-solid-2", "phase": "solid",
         "polygon": [[p1, line(p1)], [p2, line(p2)], [p2, ehi], [p1, ehi]]},
        {"species": "mock-aqueous-2", "phase": "aqueous",
         "polygon": [[p2, line(p2)], [hi, line(hi)], [hi, ehi], [p2, ehi]]},
    ]
    for d in domains:
        d["polygon"] = [[round(float(x), 4), round(float(y), 4)] for x, y in d["polygon"]]
    water = [
        {"kind": "upper", "points": [[lo, 1.2], [hi, 1.2 - 0.06 * hi]]},
        {"kind": "lower", "points": [[lo, 0.0], [hi, -0.06 * hi]]},
    ]
    for w in water:
        w["points"] = [[round(float(x), 4), round(float(y), 4)] for x, y in w["points"]]
    return {"id": rid, "conditions": {"note": NOTE}, "ph_range": list(ph), "potential_range": list(e),
            "domains": domains, "water_lines": water}


def fig7(_rng):
    return {"mock": True, "schema": "fig7-pourbaix/assumed-v0", "note": NOTE,
            "regimes": [_regime("regime-1", 4.0, 8.6, -1.6, 0.06),
                        _regime("regime-2", 4.8, 7.6, -1.5, 0.06)]}


def main():
    rng = np.random.default_rng(SEED)
    _write("fig4.json", fig4(rng))
    _write("fig5.json", fig5(rng))
    _write("fig6.json", fig6(rng))
    _write("fig7.json", fig7(rng))
    print("wrote mock inputs fig4..fig7")


if __name__ == "__main__":
    main()
