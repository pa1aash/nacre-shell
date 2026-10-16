"""Frozen literature inputs of the final runs: a verbatim subset of W1's lit/params.yaml and of
the evidence rows it cites, at a pinned commit.

lit/params.yaml is lane p0-w1's file and reaches this branch only through the integrator. The
runs therefore read it from the git object `<params_sha>:lit/params.yaml` and keep a snapshot
of the entries they use in results/preprint/pourbaix/inputs/params_<sha7>.json. The snapshot
holds each entry exactly as W1 wrote it (no value is retyped), the git blob id and the sha256
of the source bytes. `verify_snapshot` re-reads the git object, when the local object store
has it, and checks every entry; the runs refuse a snapshot that disagrees.

    uv run python -m nacre.pourbaix.inputs snapshot --params-sha 680a44b2efdb94694b25f5317ddc3d73db2f117c
"""
import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import yaml

from nacre.pourbaix import provenance
from nacre.pourbaix.paths import POURBAIX_RESULTS, REPO

INPUTS_DIR = POURBAIX_RESULTS / "inputs"
PARAMS_PATH = "lit/params.yaml"
EVIDENCE_PATH = "lit/evidence_table.csv"

# Keys the final runs read (R-slurry, R-cell, the gas-reference benchmark and the anchor).
KEYS = [
    # R-slurry axes, design axes and carbonate system
    "ph_slurry", "ph_slurry_modified", "e_she_slurry", "acc_offset", "a_ca_slurry", "c_bulk_slurry",
    "a_co3_slurry", "dic_slurry", "a_w_slurry", "t_slurry", "t_drying_primary", "t_drying_secondary",
    "ionic_strength_slurry", "pk1_carbonic", "pk2_carbonic", "log10_ksp_calcite", "log10_ksp_acc",
    "framing", "formation_energy_mae", "dfg_corundum", "dfg_boehmite", "dfg_gibbsite",
    # R-cell
    "e_cell_min", "e_cell_max", "al_onset_ffree", "t_cell", "electrolyte_salts", "electrolyte_solvents",
    "electrolyte_water_content", "gas_reference_schemes", "al_phases", "window_margin",
    "solvation_ca_vs_li", "solvation_al_vs_li", "transfer_free_energy_li_water_pc",
    "dfg_ca_no3_2", "dfg_cacl2", "dfg_caso4", "dfg_al2_so4_3", "dfg_licl", "dfg_lino3", "dfg_li2so4",
    "dfg_liclo4_aq", "dfg_al_no3_3", "dfg_ca_clo4_2", "dfg_al_clo4_3", "dfg_alcl3",
    "li2co3_oxidation_onset",
    # gas-reference benchmark
    "drg_caco3_decomposition", "drh_caco3_decomposition", "dfg_caco3_calcite", "dfg_caco3_aragonite",
    "dfg_cao", "dfg_co2_g",
    # anchor (protocol test and binding cycle)
    "m_seq_method_error", "dg_hyd_ca_marcus", "dg_hyd_ca_tissandier", "dg_bind_ca_acetate",
    "log10_k_ca_carboxylate", "water_density",
]

# Evidence rows read beyond the sources of KEYS: the DFT protocol benchmarks (task D) and the
# comparators named in the keys used here.
EXTRA_ROWS = ["TE-061", "TE-062", "TE-063", "TE-064", "TE-065", "TE-066", "TE-067", "TE-068",
              "TE-069", "TE-070", "TE-071", "TE-075", "TE-081", "TE-082", "TE-083", "TE-087",
              "TI-011", "TI-053", "TI-052", "TI-084", "TI-090", "TF-045", "TF-046", "TF-047",
              "TF-050", "TF-051", "TD-054"]


class SnapshotError(RuntimeError):
    pass


def _blob(sha, path):
    text = provenance.git_object(sha, path)
    if text is None:
        return None
    return text


def _blob_id(sha, path):
    rc, out = provenance._git("rev-parse", "%s:%s" % (sha, path))
    return out.strip() if rc == 0 else None


def snapshot_path(params_sha):
    return INPUTS_DIR / ("params_%s.json" % params_sha[:7])


def build_snapshot(params_sha):
    """Snapshot of KEYS (and the evidence rows they cite) from the git objects at params_sha."""
    text = _blob(params_sha, PARAMS_PATH)
    ev_text = _blob(params_sha, EVIDENCE_PATH)
    if text is None or ev_text is None:
        raise SnapshotError("%s:%s or %s is not in the local object store; "
                            "git fetch origin preprint/p0-w1 first" % (params_sha, PARAMS_PATH, EVIDENCE_PATH))
    doc = yaml.safe_load(text)
    missing = [k for k in KEYS if k not in doc["params"]]
    if missing:
        raise SnapshotError("params at %s lacks keys %s" % (params_sha, missing))
    entries = {k: doc["params"][k] for k in KEYS}
    want = set(EXTRA_ROWS)
    for e in entries.values():
        want |= set(e.get("sources") or [])
        for opt in (e.get("prior") or {}).get("options") or []:
            want |= set(opt.get("sources") or [])
    rows = {r["row_id"]: r for r in csv.DictReader(io.StringIO(ev_text)) if r["row_id"] in want}
    absent = sorted(want - set(rows))
    if absent:
        raise SnapshotError("evidence rows %s not in %s at %s" % (absent, EVIDENCE_PATH, params_sha))
    return {
        "what": "verbatim subset of lit/params.yaml and lit/evidence_table.csv (lane p0-w1) used by "
                "the P0-W5.2 runs; no value is retyped",
        "params_sha": params_sha,
        "params": {"path": PARAMS_PATH, "blob": _blob_id(params_sha, PARAMS_PATH),
                   "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                   "meta": doc.get("meta"), "mock": doc.get("mock")},
        "evidence": {"path": EVIDENCE_PATH, "blob": _blob_id(params_sha, EVIDENCE_PATH),
                     "sha256": hashlib.sha256(ev_text.encode("utf-8")).hexdigest()},
        "entries": entries,
        "rows": dict(sorted(rows.items())),
    }


def write_snapshot(params_sha):
    snap = build_snapshot(params_sha)
    path = snapshot_path(params_sha)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snap, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_snapshot(params_sha, check_git=True):
    """The snapshot for params_sha; checked against the git objects when they are available."""
    path = snapshot_path(params_sha)
    if not path.is_file():
        raise SnapshotError("no snapshot %s; run `python -m nacre.pourbaix.inputs snapshot`" % path)
    snap = json.loads(path.read_text(encoding="utf-8"))
    if snap["params_sha"] != params_sha:
        raise SnapshotError("snapshot %s is for %s, not %s" % (path, snap["params_sha"], params_sha))
    if check_git:
        problems = verify_snapshot(snap)
        if problems:
            raise SnapshotError("snapshot disagrees with the git objects: %s" % problems[:3])
    return snap


def verify_snapshot(snap):
    """Problems found comparing a snapshot with the git objects ([] when equal or unavailable)."""
    sha = snap["params_sha"]
    text = _blob(sha, PARAMS_PATH)
    if text is None:
        return []
    problems = []
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != snap["params"]["sha256"]:
        problems.append("params sha256 differs")
    doc = yaml.safe_load(text)
    for k, v in snap["entries"].items():
        if doc["params"].get(k) != v:
            problems.append("entry %s differs" % k)
    ev = _blob(sha, EVIDENCE_PATH)
    if ev is not None:
        rows = {r["row_id"]: r for r in csv.DictReader(io.StringIO(ev))}
        for rid, r in snap["rows"].items():
            if rows.get(rid) != r:
                problems.append("row %s differs" % rid)
    return problems


class Params:
    """Read access to a snapshot: entries by key and evidence rows by row id."""

    def __init__(self, snap):
        self.snap = snap
        self.sha = snap["params_sha"]

    def entry(self, key):
        try:
            return self.snap["entries"][key]
        except KeyError as exc:
            raise SnapshotError("key %s is not in the snapshot (add it to inputs.KEYS)" % key) from exc

    def value(self, key):
        return self.entry(key)["value"]

    def unit(self, key):
        return self.entry(key)["unit"]

    def range(self, key):
        return self.entry(key)["range"]

    def row(self, row_id):
        try:
            return self.snap["rows"][row_id]
        except KeyError as exc:
            raise SnapshotError("row %s is not in the snapshot" % row_id) from exc

    def cite(self, key):
        """Short citation of a key: its status and source rows."""
        e = self.entry(key)
        return {"key": key, "status": e["status"], "sources": list(e.get("sources") or []),
                "params_sha": self.sha}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m nacre.pourbaix.inputs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("snapshot", help="write the snapshot from the git objects")
    s.add_argument("--params-sha", required=True)
    v = sub.add_parser("verify", help="check a snapshot against the git objects")
    v.add_argument("--params-sha", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "snapshot":
        path = write_snapshot(args.params_sha)
        print(path.relative_to(REPO).as_posix())
        return 0
    snap = json.loads(snapshot_path(args.params_sha).read_text(encoding="utf-8"))
    problems = verify_snapshot(snap)
    print("snapshot OK" if not problems else "\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
