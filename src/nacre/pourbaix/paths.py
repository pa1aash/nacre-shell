"""Repository paths used by the Pourbaix and window code."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
POURBAIX_RESULTS = REPO / "results" / "preprint" / "pourbaix"
CACHE_DIR = POURBAIX_RESULTS / "cache"
CONFIG_DIR = POURBAIX_RESULTS / "config"
CHARTER_REGIMES = REPO / "charter" / "regimes.yaml"
LIT_PARAMS = REPO / "lit" / "params.yaml"


def rel(path):
    """Repository-relative POSIX path of `path`."""
    return Path(path).resolve().relative_to(REPO).as_posix()
