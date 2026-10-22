"""Pin the owners' contracts and output documents that the figure templates read.

The templates read data whose shape other lanes own: W4 the results schema and the thresholds
copy, W2 the retrodiction schema and cases, W3 the symbol register. They also read the owners'
committed output documents: W2's retrodiction record and W4's production screen documents.
Until integration brings those files into this branch, each is pinned as a byte copy of the
owner's file at a named commit, with its sha256: contracts in figures/src/schemas/upstream/,
output documents in figures/src/data/upstream/. upstream.yaml is the registry; nacre.figs.upstream
reads it, and the tests check every snapshot against its hash.

Where this branch already holds the owner's file with the pinned bytes (after an integration
merge), the entry points at that file and no copy is kept (lane note N15). Each entry also
records whether the merged tree (origin/preprint/p0) holds the pinned bytes.

Re-pin after an owner pushes (reads only with git show, never merges):
  git fetch origin --prune
  uv run python figures/src/schemas/pin_upstream.py [--only <id> ...]
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
REGISTRY = HERE / "upstream.yaml"
SNAP_DIR = HERE / "upstream"

DATA_DIR = ROOT / "figures" / "src" / "data" / "upstream"
MERGED = "origin/preprint/p0"

# id -> (owner lane, branch, path in the owner's tree, snapshot file name, what the figures use it for)
SOURCES = {
    "results_schema": ("p0-w4", "preprint/p0-w4", "configs/preprint/results_schema.json", "results_schema.json",
                       "fig5, fig6 and fig7 inputs (screen regimes, stability section C5)"),
    "thresholds": ("p0-w4", "preprint/p0-w4", "configs/preprint/thresholds.yaml", "thresholds.yaml",
                   "fig5 threshold contours (C3a edge, C3b absolute-barrier bound)"),
    "retro_schema": ("p0-w2", "preprint/p0-w2", "preprint/retrodiction/SCHEMA.md", "retrodiction_SCHEMA.md",
                     "fig4 input (retro-results/v1, SCHEMA.md section 5)"),
    "retro_cases": ("p0-w2", "preprint/p0-w2", "preprint/retrodiction/cases.yaml", "retrodiction_cases.yaml",
                    "fig4 case labels and observed relations"),
    "symbols": ("p0-w3", "preprint/p0", "theory/symbols.yaml", "symbols.yaml",
                "axis titles and parameter labels (theory symbol ids)"),
}

# Output documents (same layout); their snapshots live in DATA_DIR.
DATA = {
    "retro_results": ("p0-w2", "preprint/p0-w2", "preprint/retrodiction/results/results.json",
                      "retrodiction_results.json", "fig4 input: the P0-W2.3 retrodiction record"),
    "screen_table_r2": ("p0-w4", "preprint/p0-w4", "results/preprint/screen/table_r2/summary.json",
                        "screen_table_r2.json",
                        "fig7 input: P0-W4.3 production run table_r2 (sourced priors; C5 dose window and R-cell scheme tables)"),
    "screen_ignorance": ("p0-w4", "preprint/p0-w4", "results/preprint/screen/ignorance/summary.json",
                         "screen_ignorance.json",
                         "fig5 input: P0-W4.3 production run ignorance (barrier prefactor; theta prior mass, a property of the prior)"),
    # PH-W6.1: phosphate screen outputs of lane p0-w5 (CSV and JSON) and the cutoff classes of the merged thresholds.
    "ladder_v3": ("p0-w5", "preprint/p0", "results/preprint/pourbaix/ph_w52/ladder_v3.csv", "ladder_v3.csv",
                  "fig9 input: K1 tier-1 ladder v3 (verdict per phase, framing and cutoff class)"),
    "ladder_v3_sens40": ("p0-w5", "preprint/p0", "results/preprint/pourbaix/ph_w52/ladder_v3_sens40.csv",
                         "ladder_v3_sens40.csv", "fig9 check: the ladder with 4.0 V as the lowest class edge"),
    "benchmark_w51": ("p0-w5", "preprint/p0-w5", "results/preprint/pourbaix/ph_w51/benchmark_w51.csv",
                      "benchmark_w51.csv", "fig10 input: DFT minus experiment formation enthalpy per phase"),
    "benchmark_w51_summary": ("p0-w5", "preprint/p0-w5", "results/preprint/pourbaix/ph_w51/benchmark_w51.json",
                              "benchmark_w51.json", "fig10 registered error band and oxide correction"),
    "passivation_window_v3": ("p0-w5", "preprint/p0-w5", "results/preprint/pourbaix/ph_w52/passivation_window_v3.csv",
                              "passivation_window_v3.csv", "fig11 input: Al passivation windows per film solid and Al level"),
    "al_window": ("p0-w5", "preprint/p0-w5", "results/preprint/pourbaix/ph_w51/al_window.json", "al_window.json",
                  "fig11 reference bars: the two published pH windows"),
    "thresholds_screen_ph": ("p0-w4", "preprint/p0", "configs/preprint/thresholds.yaml", "thresholds_screen_ph.yaml",
                             "fig9 tick labels: the registered cutoff classes (screen_ph.margins_v6.cutoff_classes)"),
    # PH-W6.2: production outputs read from the merged tree (origin/preprint/p0).
    "k2_grid_ph": ("p0-w4", "preprint/p0", "results/preprint/screen/k2_grid_ph/summary.json", "k2_grid_ph.json",
                   "fig12 input: K2 verdict over the registered Ca_T by C_T grid per polymorph, and the acid-adjusted comparator"),
    "precision_map_ph": ("p0-w4", "preprint/p0", "results/preprint/screen/precision_ph/precision_map.json",
                         "precision_map_ph.json", "fig14 input: prior range, flip value and required precision per quantity"),
    "phosphate_films_ph": ("p0-w4", "preprint/p0", "results/preprint/screen/phosphate_films_ph/summary.json",
                           "phosphate_films_ph.json", "fig15 processing column: K2 regime of each phosphate and comparator film"),
    # PH-W6.3: per-pH K2 tables and the post-freeze reruns (PH-W4.5), and the generated regime table.
    "k2_perph_ph2": ("p0-w4", "preprint/p0", "results/preprint/screen/k2_perph_ph2/perph.csv", "k2_perph_ph2.csv",
                     "fig15 and fig17 input: passing cells and minimum passing doses per phase and pH"),
    "k2_acid_ph2": ("p0-w4", "preprint/p0", "results/preprint/screen/k2_acid_ph2/summary.json", "k2_acid_ph2.json",
                    "fig15 and fig17: cell verdicts of the phosphates in the acid-adjusted state (post-freeze keys)"),
    "k2_alkaline_ph2": ("p0-w4", "preprint/p0", "results/preprint/screen/k2_alkaline_ph2/summary.json",
                        "k2_alkaline_ph2.json", "fig15 and fig17: cell verdicts of the phosphates in the as-prepared slurry"),
    "regime_table": ("p0-w8", "preprint/p0", "preprint/generated/regime_table.csv", "regime_table.csv",
                     "fig15 cross-check: the first-pass pH of the acid-adjusted column of the regime table"),
}


def _show(ref, path):
    try:
        return _git("show", "%s:%s" % (ref, path))
    except subprocess.CalledProcessError:
        return None


HEADER = """\
# Owner contracts and output documents pinned for the figure templates (generated by
# pin_upstream.py; do not edit).
#
# Each entry is a byte copy of an owner's file at the commit that last changed it on the
# owner's branch (kind contract: figures/src/schemas/upstream/; kind data: figures/src/data/upstream/),
# or the in-tree file itself where this branch already holds those bytes. nacre.figs.upstream
# validates and reads figure inputs from these snapshots; the tests check each against sha256.
# merged_tree records whether origin/preprint/p0 held the pinned bytes when pinned. When
# integration brings an owner's file into this branch, `nacre figs` reports any difference.
"""


def _git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True).stdout


def pin(only=None):
    reg = yaml.safe_load(REGISTRY.read_text()) if REGISTRY.exists() else {"entries": {}}
    entries = reg.get("entries", {})
    SNAP_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    merged_head = _git("rev-parse", MERGED).decode().strip()
    table = [(k, v, SNAP_DIR, "contract") for k, v in SOURCES.items()] + \
            [(k, v, DATA_DIR, "data") for k, v in DATA.items()]
    for key, (owner, branch, path, snap, use), snap_dir, kind in table:
        if only and key not in only:
            continue
        ref = "origin/" + branch
        commit = _git("log", "-1", "--format=%H", ref, "--", path).decode().strip()
        if not commit:
            raise SystemExit("%s: %s has no commit touching %s" % (key, ref, path))
        data = _git("show", "%s:%s" % (commit, path))
        sha = hashlib.sha256(data).hexdigest()
        copy = snap_dir / snap
        in_tree = _show("HEAD", path)
        if in_tree is not None and hashlib.sha256(in_tree).hexdigest() == sha:
            out = ROOT / path
            copy.unlink(missing_ok=True)
        else:
            out = copy
            out.write_bytes(data)
        merged = _show(MERGED, path)
        entries[key] = {
            "kind": kind,
            "owner": owner,
            "branch": branch,
            "path": path,
            "commit": commit,
            "branch_head": _git("rev-parse", ref).decode().strip(),
            "snapshot": str(out.relative_to(ROOT)),
            "sha256": sha,
            "merged_tree": {"ref": MERGED, "head": merged_head,
                            "same_bytes": merged is not None and hashlib.sha256(merged).hexdigest() == sha},
            "used_for": use,
        }
        print("%s: %s@%s -> %s" % (key, path, commit[:7], out.relative_to(ROOT)))
    body = yaml.safe_dump({"entries": dict(sorted(entries.items()))}, sort_keys=False, width=110)
    REGISTRY.write_text(HEADER + body)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="+", choices=sorted(set(SOURCES) | set(DATA)))
    args = ap.parse_args(argv)
    pin(args.only)


if __name__ == "__main__":
    sys.exit(main())
