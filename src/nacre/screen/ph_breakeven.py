"""PH-W4.9: break-even ratio r* of the saturated-sink exclusions (cp6 F10), from the ladder and the thresholds copy.

For every (phase, framing, stage) of ladder_v3.csv with an ALL row, and every registered cutoff edge E_c of the classes C_mid and
C_hi (configs/preprint/thresholds.yaml, screen_ph.margins_v6.cutoff_classes), r* = exp[(E_c - E_ub - m_expt) / (2 R T / F)] from
nacre.physics.sink.breakeven_ratio. E_ub and m_expt are the ALL row's (the limiting complete-budget reaction, ladder README rule
X1), read, never typed; T is the ladder's 298.15 K. A (row, class) is listed when at least one edge of the class is excluded
(non-negative headroom); an edge of a listed class with negative headroom is listed as "not excluded without correction".
Writes results/preprint/screen/breakeven_ph/{breakeven.csv, breakeven.md, provenance.json}.
"""
import csv
import json
from pathlib import Path

import yaml

from nacre.physics import sink
from nacre.physics.bindings import DEFAULT_T
from nacre.screen import kscreen, params_adapter, ph_prov, run

SESSION = "PH-W4.9"
OUT = Path("results") / "preprint" / "screen" / "breakeven_ph"
CLASSES = ("C_mid", "C_hi")
COLUMNS = ("phase", "class", "E_c", "E_ub", "m_expt", "headroom_V", "r_star")
NOTE_ALL = "ALL"


def cutoff_edges(root):
    """{class: [E_c, ...]} for C_mid and C_hi from the thresholds copy."""
    doc = yaml.safe_load((Path(root) / "configs" / "preprint" / "thresholds.yaml").read_text(encoding="utf-8"))
    cc = doc["screen_ph"]["margins_v6"]["cutoff_classes"]
    return {c: sorted(float(e) for e in cc[c]["E_c_V"]) for c in CLASSES}


def limiting_reaction_complete(group, e_ub, margin):
    """True if a complete-budget reaction row of the group carries the ALL row's E_ub and margin (the aggregate's falsifying row)."""
    return any(r["E_ub"] == e_ub and r["margin"] == margin and r["budget_status"] == "complete" for r in group)


def rows(root):
    """The table rows (dicts with COLUMNS plus framing and stage) and the omitted (row, why) pairs."""
    root = Path(root)
    edges = cutoff_edges(root)
    table = kscreen.read_k1(root / ph_prov.LADDER)
    by_group = {}
    for r in table.reactions:
        by_group.setdefault((r["phase"], r["framing"], r["stage"]), []).append(r)
    out, omitted = [], []
    with (root / ph_prov.LADDER).open(encoding="utf-8", newline="") as fh:
        for rec in csv.DictReader(ln for ln in fh if ln.strip() and not ln.startswith("#")):
            if rec["reaction_id"].strip() != NOTE_ALL:
                continue
            e_ub, m = (float(rec[c]) if rec[c].strip() else None for c in ("E_ub_V", "margin_V"))
            key = (rec["phase"], rec["framing"], rec["stage"])
            if e_ub is None or m is None:
                continue
            if not limiting_reaction_complete(by_group.get(key, []), e_ub, m):
                omitted.append((key, "no complete-budget reaction carries the aggregate E_ub and margin"))
                continue
            for cls in CLASSES:
                head = [e - e_ub - m for e in edges[cls]]
                if not any(h >= 0 for h in head):
                    continue
                for e_c, h in zip(edges[cls], head):
                    out.append({"phase": rec["phase"], "class": cls, "E_c": e_c, "E_ub": e_ub, "m_expt": m,
                                "headroom_V": round(h, 6), "r_star": sink.breakeven_ratio(e_c, e_ub, m, DEFAULT_T),
                                "framing": rec["framing"], "stage": rec["stage"]})
    return out, omitted


def _fmt(v):
    return "%.6g" % v if isinstance(v, float) else str(v)


def write_csv(path, data):
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(COLUMNS)
        for r in data:
            w.writerow([r["phase"], r["class"], r["E_c"], r["E_ub"], r["m_expt"], r["headroom_V"],
                        "%.6g" % r["r_star"] if isinstance(r["r_star"], float) else r["r_star"]])


def markdown(data, omitted, prov):
    L = ["# Break-even ratio r* of the saturated-sink exclusions (PH-W4.9)", "",
         "r* = exp[(E_c - E_ub - m_expt) / (2 R T / F)], T = %g K, nu_salt = 1: the exclusion of a row at a cutoff edge E_c stands while "
         "a_pm,sat / a_pm < r* (claims_redirect Section 2h; m_sink = 2 nu (R T / F) ln(a_pm,sat / a_pm)). One decade of the ratio "
         "costs 2 ln10 R T / F = %.1f mV of headroom. E_ub and m_expt are the ALL row of ladder_v3.csv." % (
             DEFAULT_T, 1000 * 2 * 2.302585092994046 * 8.314462618 * DEFAULT_T / 96485.33212), "",
         "| phase | framing | stage | class | E_c (V) | E_ub (V) | m_expt (V) | headroom (mV) | r* |", "|---|---|---|---|---|---|---|---|---|"]
    for r in data:
        L.append("| %s | %s | %s | %s | %g | %g | %g | %.1f | %s |" % (
            r["phase"], r["framing"], r["stage"], r["class"], r["E_c"], r["E_ub"], r["m_expt"], 1000 * r["headroom_V"],
            "%.3g" % r["r_star"] if isinstance(r["r_star"], float) else r["r_star"]))
    if omitted:
        L += ["", "Omitted: " + "; ".join("%s (%s)" % ("/".join(k), why) for k, why in omitted) + "."]
    L += ["", "Provenance: code sha %s%s; ladder sha256 %s; thresholds copy sha256 %s." % (
        prov["code_sha"], " (dirty tree)" if prov["git_dirty"] else "", prov["ladder_sha256"], prov["thresholds_copy_sha256"])]
    return "\n".join(L) + "\n"


def main(root):
    root = Path(root)
    out = root / OUT
    if out.exists():
        raise run.ProductionRefused("%s exists" % out)
    ph_prov.check_frozen(root)
    data, omitted = rows(root)
    params = root / params_adapter.PRODUCTION_PARAMS
    ctx_prov = run._provenance(root, run.load_config(root), root / run.CONFIG,
                               [params_adapter.RegimePriors("R-slurry", None, {}, str(params), run._sha256_file(params), False)],
                               run.THRESHOLDS, False)
    prov = {"session": SESSION, "code_sha": ctx_prov["git_sha"], "git_dirty": ctx_prov["git_dirty"],
            "ladder_file": ph_prov.LADDER.as_posix(), "ladder_sha256": ph_prov.sha256_file(root / ph_prov.LADDER),
            "thresholds_copy_file": "configs/preprint/thresholds.yaml",
            "thresholds_copy_sha256": ph_prov.sha256_file(root / "configs" / "preprint" / "thresholds.yaml"),
            "temperature_K": DEFAULT_T, "nu_salt": 1, "classes": list(CLASSES), "edges": cutoff_edges(root), "n_rows": len(data)}
    out.mkdir(parents=True)
    write_csv(out / "breakeven.csv", data)
    (out / "breakeven.md").write_text(markdown(data, omitted, prov), encoding="utf-8")
    (out / "provenance.json").write_text(json.dumps(prov, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    ph_prov.ledger_append(root, SESSION, ctx_prov, ctx_prov["config_file"], ctx_prov["config_hash"],
                          [out / "breakeven.csv", out / "breakeven.md", out / "provenance.json"],
                          note="break-even ratio r* of the saturated-sink exclusions (cp6 F10), pure arithmetic over the frozen ladder")
    return data


if __name__ == "__main__":
    from nacre._util import repo_root
    main(repo_root())
