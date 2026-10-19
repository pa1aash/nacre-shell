"""Thresholds copy: configs/preprint/thresholds.yaml equals the block of theory/thresholds.md (R-thr)."""
from pathlib import Path

import pytest

from nacre.screen import thresholds as thr

ROOT = Path(__file__).resolve().parents[2]
SHA = "a" * 40
SOURCE = """# Thresholds

Prose that is not copied.

```yaml
not: this one
```

```thresholds
links:
  nucleate:
    quantity: f_theta
    edges: [0.5, 0.8]
```

More prose.
"""


def test_block_is_extracted_and_copied_verbatim_under_a_header():
    text = thr.make_copy(SOURCE, SHA)
    assert text.startswith("# Machine-readable copy")
    sha, body = thr.split_copy(text)
    assert sha == SHA
    assert body == "links:\n  nucleate:\n    quantity: f_theta\n    edges: [0.5, 0.8]\n"
    assert thr.equal(SOURCE, text)


@pytest.mark.parametrize("source", [SOURCE.replace("```thresholds", "```yaml"),
                                    SOURCE + "\n```thresholds\nx: 1\n```\n"])
def test_source_must_hold_exactly_one_thresholds_block(source):
    with pytest.raises(thr.ThresholdsMismatch, match="exactly one"):
        thr.extract_block(source)


def test_an_edited_copy_is_detected():
    text = thr.make_copy(SOURCE, SHA).replace("0.8", "0.85")
    with pytest.raises(thr.ThresholdsMismatch):
        thr.equal(SOURCE, text)


def test_copy_needs_a_full_source_sha_and_valid_yaml():
    with pytest.raises(ValueError):
        thr.make_copy(SOURCE, "abc123")
    with pytest.raises(Exception):
        thr.make_copy(SOURCE.replace("edges: [0.5, 0.8]", "edges: [0.5, 0.8"), SHA)


def test_loader_returns_the_rule_and_its_source(tmp_path):
    p = tmp_path / "thresholds.yaml"
    p.write_text(thr.make_copy(SOURCE, SHA), encoding="utf-8")
    t = thr.load_thresholds(p)
    assert t["source_sha"] == SHA and t["rule"]["links"]["nucleate"]["edges"] == [0.5, 0.8]
    with pytest.raises(thr.ThresholdsNotFrozen):
        thr.load_thresholds(tmp_path / "missing.yaml")


def test_committed_copy_equals_theory_thresholds():
    # the authority is theory/thresholds.md at the copy's source commit; on this lane branch the
    # tree may still hold an earlier version of the same file, never a diverging one
    sha, tree_sha = thr.check_against_authority(ROOT)
    assert sha and tree_sha
    rule = thr.load_thresholds(ROOT / thr.COPY)["rule"]
    assert rule["version"] == 4 and rule["contract_version"] == 4
