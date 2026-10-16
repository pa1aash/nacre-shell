"""Run provenance, ledger records and checks against the other lanes' schemas.

The `provenance` block follows W4's results schema (configs/preprint/results_schema.json at
cc50fc0, $defs/provenance) field by field. W4's `prior_file` is the run configuration here,
since the Pourbaix runs have no prior file. `provenance_pourbaix` carries what W4's block has no
room for: the cache hash, the Materials Project database version and the library versions.
"""
import datetime as dt
import hashlib
import json
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from nacre.pourbaix import cache
from nacre.pourbaix.paths import REPO

W4_SCHEMA = ("cc50fc0", "configs/preprint/results_schema.json")
W6_SCHEMA = ("origin/preprint/p0-w6", "figures/src/schemas/fig7_pourbaix.schema.json")
W3_CONTRACT = ("b5a944cd335eb0a8d2e708b4391c9ad82ad31dc3", "theory/contract.yaml")
# Day 2 (P0-W5.2): schema v2 with the C5 section (D4), contract v2, W3's thresholds and the
# Fig 7 schema at the commits read in this session.
W4_SCHEMA_V2 = ("16fe14d4454fd1b4b79ed8454a557b6d68aa7b88", "configs/preprint/results_schema.json")
W3_CONTRACT_V2 = ("5811a6b2b82565a2d7e991987eee6ab4f167959e", "theory/contract.yaml")
W3_THRESHOLDS = ("800d5ea", "theory/thresholds.md")
W6_SCHEMA_PIN = ("6bcb801", "figures/src/schemas/fig7_pourbaix.schema.json")
LIBS = ["pymatgen", "mp-api", "emmet-core", "numpy", "scipy", "rdkit", "ase", "pyyaml"]


def utc_now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(*args):
    p = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)
    return p.returncode, p.stdout


def git_sha():
    return _git("rev-parse", "HEAD")[1].strip()


def git_dirty():
    """True when tracked files differ from HEAD (untracked run outputs do not count)."""
    return bool(_git("status", "--porcelain", "--untracked-files=no")[1].strip())


def git_object(rev, path):
    """Text of `rev:path` from the local object store, or None if it is not available."""
    rc, out = _git("show", "%s:%s" % (rev, path))
    return out if rc == 0 else None


def lib_versions():
    out = {}
    for n in LIBS:
        try:
            out[n] = version(n)
        except PackageNotFoundError:
            out[n] = None
    return out


def block(config_meta):
    """(W4-conformant provenance, extra Pourbaix provenance)."""
    m = cache.manifest()
    w4 = {"git_sha": git_sha(), "git_dirty": git_dirty(), "config_hash": config_meta["config_hash"],
          "prior_file": config_meta["path"], "prior_file_hash": config_meta["file_hash"],
          "contract_sha": W3_CONTRACT[0]}
    extra = {"cache_dir": cache.CACHE_DIR.relative_to(REPO).as_posix(),
             "cache_hash": cache.cache_hash(), "mp_database_version": m["mp_database_version"],
             "mp_thermo_types": m["thermo_types"], "library_versions": lib_versions(),
             "contract": {"sha": W3_CONTRACT[0], "path": W3_CONTRACT[1], "function": "E_window"},
             "w4_schema": {"rev": W4_SCHEMA[0], "path": W4_SCHEMA[1]},
             "w6_schema": {"rev": W6_SCHEMA[0], "path": W6_SCHEMA[1]}}
    return w4, extra


def validate_against(rev_path, instance, subschema=None):
    """Validate `instance` against a schema read from git. Returns a dict with errors or a skip."""
    import jsonschema

    text = git_object(*rev_path)
    if text is None:
        return {"checked": False, "reason": "schema %s:%s not in the local object store" % rev_path}
    schema = json.loads(text)
    if subschema:
        schema = {**schema["$defs"][subschema], "$defs": schema.get("$defs", {})}
    v = jsonschema.Draft202012Validator(schema)
    errs = sorted(v.iter_errors(instance), key=lambda e: list(e.absolute_path))
    return {"checked": True, "schema": "%s:%s" % rev_path, "subschema": subschema,
            "valid": not errs,
            "errors": [{"path": "/".join(str(p) for p in e.absolute_path) or "(root)",
                        "message": e.message[:300]} for e in errs]}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ledger_append(ledger, record):
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
