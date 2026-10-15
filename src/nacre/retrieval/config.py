"""Paths, contact details, source settings and .env keys for retrieval."""
import os
from pathlib import Path

import yaml

from nacre import _util


class Config:
    def __init__(self, root=None, env=None):
        self.root = Path(root) if root else _util.repo_root()
        self.corpus = self.root / "lit" / "corpus"
        self.records_path = self.corpus / "records.jsonl"
        self.cache_dir = self.corpus / "cache"
        self.fulltext_dir = self.corpus / "fulltext"
        self.gaps_path = self.root / "lit" / "instrument_gaps.csv"
        conf = self.root / "configs" / "retrieval"
        self.contact = _load_yaml(conf / "contact.yaml")
        self.sources = _load_yaml(conf / "sources.yaml")
        self.env = dict(env) if env is not None else _load_env(self.root / ".env")

    @property
    def mailto(self):
        return self.contact.get("mailto", "")

    @property
    def user_agent(self):
        return "%s (mailto:%s)" % (self.contact.get("user_agent", "nacre-shell-retrieval"), self.mailto)

    def source(self, name):
        return self.sources.get(name) or {}

    def key(self, name):
        return (self.env.get(name) or "").strip() or None


def _load_yaml(path):
    if not Path(path).exists():
        return {}
    return yaml.safe_load(Path(path).read_text()) or {}


def _load_env(path):
    """Process environment overlaid on a plain KEY=VALUE .env file."""
    out = {}
    p = Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip("'\"")
    for k, v in os.environ.items():
        if v:
            out[k] = v
    return out
