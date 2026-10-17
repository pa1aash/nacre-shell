"""The templates conform to the owners' contracts: pins are intact and the transcriptions match."""
import json
import re

import pytest
from figs_helpers import REPO

from nacre.figs import schema, upstream

PINS = ["results_schema", "thresholds", "retro_schema", "retro_cases", "symbols",
        "retro_results", "screen_table_r2", "screen_ignorance"]


@pytest.mark.parametrize("key", PINS)
def test_every_pin_matches_its_sha256(key):
    upstream.snapshot_bytes(key, REPO)  # raises on a mismatch


def test_registry_names_owner_commit_and_path():
    for key in PINS:
        e = upstream.entry(key, REPO)
        assert re.fullmatch(r"[0-9a-f]{40}", e["commit"]), key
        assert e["owner"] in {"p0-w2", "p0-w3", "p0-w4"} and e["path"], key
        assert e["kind"] in {"contract", "data"} and "same_bytes" in e["merged_tree"], key


def test_tampered_pin_is_refused(tmp_path, monkeypatch):
    e = dict(upstream.entry("thresholds", REPO))
    e["sha256"] = "0" * 64
    monkeypatch.setitem(upstream.registry(REPO), "thresholds", e)
    with pytest.raises(upstream.UpstreamError, match="sha256"):
        upstream.snapshot_bytes("thresholds", REPO)


def _example_record():
    """The JSON example of SCHEMA.md section 5 (pinned owner text)."""
    text = upstream.load("retro_schema", REPO)
    block = re.search(r"## 5\. Result record.*?```json\n(.*?)```", text, re.S).group(1)
    return json.loads(block)


def test_retro_transcription_has_exactly_the_owners_fields():
    ex = _example_record()
    sch, _ = schema.resolve("figures/src/schemas/retro_results_v1.schema.json", REPO)
    assert set(sch["properties"]) == set(ex)
    assert set(sch["required"]) == set(ex)
    case = sch["$defs"]["case"]
    assert set(case["properties"]) == set(ex["cases"][0]) == set(case["required"])
    assert set(sch["properties"]["summary"]["properties"]) == set(ex["summary"])
    assert set(sch["properties"]["provenance"]["properties"]) == set(ex["provenance"])
    assert set(sch["$defs"]["interval"]["properties"]) == set(ex["cases"][0]["delta"])
    assert set(case["properties"]["verdict"]["enum"]) == set(ex["cases"][0]["verdict"].split(" | "))


def test_retro_transcription_terminations_follow_the_owner_table():
    text = upstream.load("retro_schema", REPO)
    row = next(line for line in text.splitlines() if line.startswith("| `termination`"))
    owner = set(re.findall(r"`([a-z]+)`", row.split("|")[2]))
    sch, _ = schema.resolve("figures/src/schemas/retro_results_v1.schema.json", REPO)
    assert set(sch["$defs"]["case"]["properties"]["termination"]["enum"]) == owner


def test_retro_mock_uses_the_usable_cases_of_the_pinned_list():
    cases = [c for c in upstream.load("retro_cases", REPO)["cases"] if c["status"] == "usable"]
    mock = json.loads((REPO / "figures/src/mock/retro_results.json").read_text())
    assert [c["id"] for c in mock["cases"]] == [c["id"] for c in cases]
    assert [c["observed_relation"] for c in mock["cases"]] == [c["outcome"]["relation"] for c in cases]


def test_owner_schema_rejects_a_scheme_row_without_status():
    sch = upstream.load("results_schema", REPO)
    doc = json.loads((REPO / "figures/src/mock/screen_c5.json").read_text())
    assert schema.validate(doc, sch) == []
    del doc["claims"]["C5"]["tests"]["C5c_ox"]["scheme_table"][0]["status"]
    assert schema.validate(doc, sch)


@pytest.mark.parametrize("key", ["screen_table_r2", "screen_ignorance"])
def test_pinned_screen_documents_conform_to_the_pinned_schema(key):
    sch = upstream.load("results_schema", REPO)
    assert schema.validate(json.loads(upstream.snapshot_bytes(key, REPO)), sch) == []


def test_pinned_retro_record_conforms_to_the_transcription():
    sch, _ = schema.resolve("figures/src/schemas/retro_results_v1.schema.json", REPO)
    assert schema.validate(json.loads(upstream.snapshot_bytes("retro_results", REPO)), sch) == []


def test_fig5_reads_the_c3a_edge_from_the_thresholds_copy():
    from nacre.figs import build
    mod = build.load_template(REPO / "figures/src/fig5.py")
    aux = build.load_aux(REPO, mod, mock=True)
    m = mod.c3a_edge_cos(aux["thresholds"][0], aux["params"][0])
    assert m == aux["params"][0]["thresholds"]["C3"]["margin_cos_theta"]["value"]


def test_symbol_titles_come_from_the_register():
    from nacre.figs.symbols import axis_title, symbol
    assert symbol("Omega_bulk", REPO) == "$%s$" % upstream.symbols(REPO)["Omega_bulk"]["latex"]
    assert axis_title("theta", REPO, unit="°").endswith("(°)")
    with pytest.raises(KeyError):
        symbol("no_such_symbol", REPO)


def test_drift_reports_a_differing_owner_file(tmp_path, monkeypatch):
    e = dict(upstream.entry("thresholds", REPO))
    (tmp_path / "x.yaml").write_text("changed\n")
    e["path"] = str(tmp_path / "x.yaml")
    monkeypatch.setitem(upstream.registry(REPO), "thresholds", e)
    assert any(k == "thresholds" for k, _m in upstream.drift(REPO))
