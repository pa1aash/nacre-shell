"""Anchor DFT protocol: PROTOCOL.md is generated from the W1 rows, and the committed protocol
test is internally consistent (offline)."""
import json

import pytest

from nacre.anchor import protocol, protocol_test

SUMMARY = protocol_test.OUT / "summary.json"


def test_protocol_md_is_the_generated_text():
    assert protocol.PROTOCOL_MD.read_text(encoding="utf-8") == protocol.markdown()


def test_protocol_cites_the_ca_benchmark_rows():
    text = protocol.PROTOCOL_MD.read_text(encoding="utf-8")
    for rid in ("TE-061", "TE-062", "TE-063", "TE-067", "TE-070"):
        assert rid in text
    assert "10.1021/acs.jpcb.0c11077" in text


def _summary():
    if not SUMMARY.is_file():
        pytest.skip("protocol test not run")
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


def test_cycle_terms_add_up_and_waters_balance():
    c = _summary()["cycle"]
    assert c["status"] == "ok"
    assert sum(c["terms_J_per_mol"].values()) == pytest.approx(c["dG_bind_J_per_mol"], abs=1e-6)
    assert c["stoichiometry"] == {"reactants": 2, "products": 2, "released_waters": 2}
    assert c["terms_J_per_mol"]["dG_1atm_to_1M"] == pytest.approx(0.0, abs=1e-9)


def test_minima_and_determinism_recorded():
    s = _summary()
    assert all(r["xtb"]["n_imaginary"] == 0 for r in s["species"].values())
    assert s["determinism"]["deterministic"] is True
    assert s["crest"]["status"] == "ok"
