"""Results summary of a screen run, conforming to configs/preprint/results_schema.json."""
import hashlib
import json
import subprocess
import time
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "configs" / "preprint" / "results_schema.json"


def config_hash(config):
    """sha256 of the canonical JSON of a run configuration (sorted keys, compact)."""
    blob = json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(blob).hexdigest()


def git_state(root):
    """(HEAD sha, dirty flag) of the repository at root."""
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True,
                         text=True, check=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain"],
                                capture_output=True, text=True, check=True).stdout.strip())
    return sha, dirty


def provenance(root, config, prior_set, contract_sha=None):
    sha, dirty = git_state(root)
    prior_path = Path(prior_set.path)
    try:
        rel = prior_path.resolve().relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        rel = prior_path.as_posix()
    return {"git_sha": sha, "git_dirty": dirty, "config_hash": config_hash(config),
            "prior_file": rel, "prior_file_hash": prior_set.sha256, "contract_sha": contract_sha}


SCHEMA_VERSION = "2"


def build(regimes, prov, mock, stability=None, required_precision=None):
    """Assemble a results document (schema v2); regimes and/or stability must be given."""
    doc = {"schema_version": SCHEMA_VERSION, "mock": bool(mock),
           "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "provenance": prov}
    if regimes is not None:
        doc["regimes"] = regimes
    if stability is not None:
        doc["stability"] = stability
    if required_precision is not None:
        doc["required_precision"] = required_precision
    return doc


def load_schema(path=SCHEMA_PATH):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(summary, schema=None):
    """Raise jsonschema.ValidationError unless summary conforms to the results schema."""
    import jsonschema
    jsonschema.validate(summary, schema or load_schema())


def write(summary, path):
    validate(summary)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
