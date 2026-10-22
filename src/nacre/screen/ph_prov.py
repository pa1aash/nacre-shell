"""Provenance and guards of the PH-W4.2 production runs (frozen inputs at tag p0-cp5).

Every production document of the redirected study records, besides the shared fields of nacre.screen.run: the code sha (git_sha),
the params sha, the sha256 of the thresholds block (version 8), the sha256 of symbol_bindings.yaml (the file and its header hash),
the gap tables' sha256, the sha256 of the K1 ladder (ladder_v3.csv), the contract v6 sha and the commit of tag p0-cp5. The ladder
hash is checked against the frozen value before any output: a different ladder stops the run (BLOCKED).
"""
import hashlib
import json
import subprocess
from pathlib import Path

from nacre.screen import thresholds as thr

FREEZE_TAG = "p0-cp5"
LADDER = Path("results") / "preprint" / "pourbaix" / "ph_w52" / "ladder_v3.csv"
LADDER_SHA256 = "595636ef1c7cfd774e27040f7a60f5f32ff7e55569525a7a84e009ef37354d6b"
BINDINGS = Path("configs") / "preprint" / "symbol_bindings.yaml"
GAP_TABLES = (Path("configs") / "preprint" / "gap_resolution.yaml", Path("configs") / "preprint" / "gap_resolution_ph.yaml")
THRESHOLDS_BLOCK_VERSION = 8
HEADER_PREFIX = "# sha256 of this file with this line removed: "
LEDGER = Path("jobs") / "ledger" / "p0-w4.jsonl"


class Frozen(RuntimeError):
    """A frozen input differs from its registered value: the run stops."""


def sha256_file(path):
    """Plain hex sha256 of the raw bytes of a file."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tagged(hexdigest):
    """The 'sha256:<hex>' form of the results schema."""
    return "sha256:" + hexdigest


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()


def bindings_header_hash(path):
    """(recorded hash, recomputed hash) of symbol_bindings.yaml: the sha256 of the file with the hash line removed."""
    lines = Path(path).read_text(encoding="utf-8").splitlines(keepends=True)
    idx = [i for i, ln in enumerate(lines) if ln.startswith(HEADER_PREFIX)]
    if len(idx) != 1:
        raise Frozen("%s must hold exactly one header hash line" % path)
    body = "".join(lines[:idx[0]] + lines[idx[0] + 1:])
    return lines[idx[0]][len(HEADER_PREFIX):].strip(), hashlib.sha256(body.encode("utf-8")).hexdigest()


def check_frozen(root):
    """Raise Frozen unless the ladder hash, the bindings header hash and the freeze tag are as registered."""
    root = Path(root)
    got = sha256_file(root / LADDER)
    if got != LADDER_SHA256:
        raise Frozen("ladder_v3.csv sha256 %s differs from the frozen %s" % (got, LADDER_SHA256))
    rec, calc = bindings_header_hash(root / BINDINGS)
    if rec != calc:
        raise Frozen("symbol_bindings.yaml header hash %s does not match its body %s" % (rec, calc))
    if not _git(root, "tag", "-l", FREEZE_TAG):
        raise Frozen("tag %s is missing" % FREEZE_TAG)
    return True


def extra(root):
    """The PH-W4.2 provenance fields (all optional in the results schema)."""
    root = Path(root)
    th = root / thr.COPY
    block = thr.split_copy(th.read_text(encoding="utf-8"))[1] if th.exists() else None
    rec, calc = bindings_header_hash(root / BINDINGS) if (root / BINDINGS).exists() else (None, None)
    tag = _git(root, "rev-list", "-n", "1", FREEZE_TAG) or None
    return {
        "thresholds_block_version": THRESHOLDS_BLOCK_VERSION if block else None,
        "thresholds_block_sha256": tagged(hashlib.sha256(block.encode("utf-8")).hexdigest()) if block else None,
        "symbol_bindings_file": BINDINGS.as_posix() if (root / BINDINGS).exists() else None,
        "symbol_bindings_hash": tagged(sha256_file(root / BINDINGS)) if (root / BINDINGS).exists() else None,
        "symbol_bindings_header_hash": tagged(calc) if calc else None,
        "gap_table_hashes": {p.as_posix(): tagged(sha256_file(root / p)) for p in GAP_TABLES if (root / p).exists()} or None,
        "ladder_file": LADDER.as_posix() if (root / LADDER).exists() else None,
        "ladder_hash": tagged(sha256_file(root / LADDER)) if (root / LADDER).exists() else None,
        "checkpoint_tag": FREEZE_TAG if tag else None,
        "checkpoint_tag_commit": tag,
    }


def ledger_append(root, session, prov, config, config_hash, outputs, note=None):
    """Append one production record to jobs/ledger/p0-w4.jsonl (the standard ledger line of nacre.screen.run)."""
    root = Path(root)
    line = {"kind": "screen", "session": session, "git_sha": prov["git_sha"], "git_dirty": prov["git_dirty"],
            "config": config, "config_hash": config_hash, "params_hash": prov.get("prior_file_hash"),
            "thresholds_hash": prov.get("thresholds_hash"), "contract_sha": prov.get("contract_sha"), "mock": False,
            "outputs": [{"path": Path(o).resolve().relative_to(root.resolve()).as_posix(),
                         "sha256": sha256_file(o)} for o in outputs]}
    if note:
        line["note"] = note
    ledger = root / LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")
    return line
