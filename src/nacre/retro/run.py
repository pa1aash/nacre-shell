"""The retrodiction run (P0-W2.3): predictions, swap check, permutation null and the result record.

Predictions and the swap check come from nacre.screen.retro (the W4 entry point) under contract
v3. This module adds what criterion.md fixes on top of it:
  * the frozen-input check: cases.yaml and criterion.md must be byte-identical to the
    fixed-before-run commit, and lit/params.yaml to the parameter tag (p0-cp3);
  * the permutation null of cp3 R9 (criterion.md section 4, condition 5): surface input sets are
    shuffled across the test and reference slots, within studies and across studies, only between
    surfaces of the same interface mapping; it is descriptive and never gates;
  * exact tallies (incorrect, inconclusive and undetermined kept apart; all three are misses);
  * provenance and one ledger line in jobs/ledger/p0-w2.jsonl.
"""
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from nacre.screen import retro

CASES = Path("preprint/retrodiction/cases.yaml")
CRITERION = Path("preprint/retrodiction/criterion.md")
PARAMS = Path("lit/params.yaml")
CONTRACT = Path("theory/contract.yaml")
RESULTS = Path("preprint/retrodiction/results/results.json")
LEDGER = Path("jobs/ledger/p0-w2.jsonl")
SCHEMES = ("within_study", "across_studies")


class RunError(RuntimeError):
    """A precondition of the run fails (BLOCKED): frozen bytes differ, dirty tree, missing key."""


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ preparation


def prepare_all(cases_path, params_path, draws, seed):
    """The usable cases prepared exactly as nacre.screen.retro.run_cases prepares them.

    Returns (usable, prepared, root): prepared[i] = (shared, test, ref, mapping) on the same seed
    streams, so the deltas reproduce the record draw by draw; root is the seed sequence after the
    per-case spawns, from which the permutation streams are taken.
    """
    doc = yaml.safe_load(Path(cases_path).read_bytes())
    table = yaml.safe_load(Path(params_path).read_text(encoding="utf-8")) if params_path else None
    root = np.random.SeedSequence(seed)
    usable = [c for c in doc["cases"] if c.get("status") == "usable"]
    prepared = []
    for case, seq in zip(usable, root.spawn(len(usable))):
        prepared.append(retro.prepare(case, doc, table, draws, np.random.default_rng(seq)))
    return usable, prepared, root


def _verdict(case, shared, test, ref, mapping):
    return retro.evaluate_case(case, shared, test, ref, mapping)["verdict"]


# ------------------------------------------------------------------ permutation null


def slot_groups(usable, prepared, scheme):
    """Exchangeable slots: (case index, 'test' | 'reference') grouped by mapping, and by study if within."""
    groups = {}
    for i, (case, (_, _, _, mapping)) in enumerate(zip(usable, prepared)):
        key = (case["study"], mapping) if scheme == "within_study" else (mapping,)
        groups.setdefault(key, []).extend([(i, "test"), (i, "reference")])
    return groups


def permutation_null(usable, prepared, scheme, n_perm, rng):
    """Number of correct verdicts under n_perm shuffles of the surface input sets (cp3 R9, descriptive)."""
    if scheme not in SCHEMES:
        raise ValueError("scheme must be one of %s" % (SCHEMES,))
    groups = slot_groups(usable, prepared, scheme)
    counts = np.zeros(n_perm, dtype=int)
    for p in range(n_perm):
        assign = {}
        for slots in groups.values():
            sets = [prepared[i][1] if side == "test" else prepared[i][2] for i, side in slots]
            for slot, j in zip(slots, rng.permutation(len(slots))):
                assign[slot] = sets[j]
        for i, (case, (shared, _, _, mapping)) in enumerate(zip(usable, prepared)):
            counts[p] += _verdict(case, shared, assign[(i, "test")], assign[(i, "reference")], mapping) == "correct"
    return counts


def describe_null(counts, observed, n_cases):
    q = np.quantile(counts, (0.025, 0.5, 0.975))
    return {"n_perm": int(counts.size), "median": float(q[1]), "range95": [float(q[0]), float(q[2])],
            "mean": float(counts.mean()), "fraction_ge_observed": float(np.mean(counts >= observed)),
            "counts": np.bincount(counts, minlength=n_cases + 1).tolist(), "descriptive": True}


# ------------------------------------------------------------------ evaluation


def evaluate(cases_path, params_path, criterion_path=None, draws=20000, seed=0, n_perm=2000):
    """The result record of every usable case (no git, no writing): retro.run_cases plus criterion.md."""
    rec = retro.run_cases(cases_path, params_path, draws=draws, seed=seed, n_perm=0, criterion_path=criterion_path)
    usable, prepared, root = prepare_all(cases_path, params_path, draws, seed)
    for r, case, (shared, test, ref, mapping) in zip(rec["cases"], usable, prepared):
        again = retro.evaluate_case(case, shared, test, ref, mapping)
        if again["delta"] != r["delta"]:
            raise RunError("%s: the re-prepared draws do not reproduce the record" % case["id"])
        r["label"] = "%s vs %s (%s)" % (case["test"]["label"], case["reference"]["label"], case["study"])
        r["nonfinite_fraction"] = float(np.mean(~np.isfinite(again["_delta"])))
    s, n = rec["summary"], len(rec["cases"])
    tally = {v: sum(r["verdict"] == v for r in rec["cases"]) for v in ("correct", "incorrect", "inconclusive",
                                                                       "undetermined")}
    s.update(tally)
    s["misses"] = n - tally["correct"]
    s["misses_by_case"] = {r["id"]: r["verdict"] for r in rec["cases"] if r["verdict"] != "correct"}
    perm_seqs = root.spawn(len(SCHEMES))
    s["permutation_null"] = {
        scheme: describe_null(permutation_null(usable, prepared, scheme, n_perm, np.random.default_rng(seq)),
                              tally["correct"], n)
        for scheme, seq in zip(SCHEMES, perm_seqs)} if n_perm else None
    if s["permutation_null"]:
        s["permutation_null"]["rule"] = "cp3 R9: descriptive control, does not gate (criterion.md section 4.5)"
    return rec


# ------------------------------------------------------------------ the frozen run


def _git(root, *args):
    from nacre import _util
    return _util.git(root, *args, check=True).stdout


def _git_bytes(root, rev, path):
    import subprocess
    p = subprocess.run(["git", "-C", str(root), "show", "%s:%s" % (rev, path)], capture_output=True)
    if p.returncode != 0:
        raise RunError("%s is not in %s" % (path, rev))
    return p.stdout


def check_frozen(root, fixed_sha, params_tag):
    """criterion.md section 4.1-4.2: frozen bytes and a clean tree; returns the provenance mapping."""
    root = Path(root)
    if _git(root, "status", "--porcelain").strip():
        raise RunError("the working tree is not clean")
    for path in (CASES, CRITERION):
        if (root / path).read_bytes() != _git_bytes(root, fixed_sha, path):
            raise RunError("%s differs from the fixed-before-run commit %s" % (path, fixed_sha))
    params = (root / PARAMS).read_bytes()
    if params != _git_bytes(root, params_tag, PARAMS):
        raise RunError("%s differs from tag %s" % (PARAMS, params_tag))
    return {"git_sha": _git(root, "rev-parse", "HEAD").strip(), "git_dirty": False,
            "criterion_sha": _git(root, "rev-parse", fixed_sha).strip(),
            "contract_sha": _git(root, "log", "-1", "--format=%H", "--", str(CONTRACT)).strip(),
            "contract_sha256": "sha256:" + _sha256((root / CONTRACT).read_bytes()),
            "params_tag": params_tag, "params_tag_sha": _git(root, "rev-list", "-n", "1", params_tag).strip(),
            "params_file_hash": "sha256:" + _sha256(params)}


def run(root, fixed_sha, params_tag="p0-cp3", draws=20000, seed=0, n_perm=2000, session="P0-W2.3"):
    """Run the frozen set once, write the record and one ledger line; returns the record."""
    root = Path(root)
    prov = check_frozen(root, fixed_sha, params_tag)
    started = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rec = evaluate(root / CASES, root / PARAMS, root / CRITERION, draws=draws, seed=seed, n_perm=n_perm)
    rec["fixed_before_run_commit"] = prov["criterion_sha"]
    rec["provenance"] = prov
    rec["session"] = session
    out = root / RESULTS
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rec, indent=1) + "\n", encoding="utf-8")
    line = {"kind": "retrodiction", "run": "retro-v1", "session": session, "mock": False,
            "git_sha": prov["git_sha"], "git_dirty": False, "criterion_sha": prov["criterion_sha"],
            "contract_sha": prov["contract_sha"], "params_sha": prov["params_tag_sha"],
            "params_file_hash": prov["params_file_hash"], "draws": draws, "seed": seed, "n_perm": n_perm,
            "started_utc": started,
            "finished_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "outputs": [{"path": str(RESULTS), "sha256": _sha256(out.read_bytes())}]}
    with (root / LEDGER).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")
    return rec
