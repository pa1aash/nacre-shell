"""nacre preprint macros: sources.yaml to numbers.tex, with provenance and mock handling."""
import json
import subprocess

import pytest
import yaml

from nacre.preprint import macros, paths
from preprint_helpers import REPO, write


def _tree(tmp_path, spec, doc):
    root = tmp_path / "r"
    write(root / "results" / "x.json", json.dumps(doc))
    write(root / "preprint" / "generated" / "sources.yaml", yaml.safe_dump({"macros": spec}))
    return root


def test_generated_files_are_git_ignored_not_tracked():
    tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "preprint/generated"],
                             capture_output=True, text=True, check=True).stdout.split()
    assert not [f for f in tracked if f.endswith(".tex")]
    assert "preprint/generated/sources.yaml" in tracked
    for name in ("numbers", "front", "authors", "credit", "declarations"):
        p = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", "preprint/generated/%s.tex" % name])
        assert p.returncode == 0, name


def test_numbers_generation_is_deterministic_and_content_keyed(tmp_path):
    spec = {"NumA": {"source": "results/x.json", "key": "a", "format": "d"}}
    root = _tree(tmp_path, spec, {"a": 3, "other": 1})
    first = macros.render(root)
    assert macros.render(root) == first
    write(root / "results" / "x.json", json.dumps({"a": 3, "other": 2, "more": [1]}))
    assert macros.render(root) == first                      # unconsumed part of a result file
    spec2 = dict(spec, NumUnused={"source": "results/x.json", "key": "other", "format": "d"})
    write(root / "preprint" / "generated" / "sources.yaml", yaml.safe_dump({"macros": spec2, "schemas": {"z": 1}}))
    assert macros.render(root) != first                      # a new consumed macro
    write(root / "preprint" / "generated" / "sources.yaml", yaml.safe_dump({"macros": spec, "schemas": {"z": 2}}))
    assert macros.render(root) == first                      # unconsumed block of sources.yaml
    write(root / "results" / "x.json", json.dumps({"a": 4}))
    changed = macros.render(root)
    assert changed != first and "value: 4" in changed        # consumed value
    assert "blob" not in changed


def test_real_and_mock_macros_and_provenance(tmp_path):
    root = _tree(tmp_path, {
        "NumReal": {"source": "results/x.json", "key": "a/b", "format": ".2f", "unit": r"\mathrm{J}"},
        "NumMock": {"source": "results/x.json", "key": "a/list/1", "format": "d", "mock": True},
    }, {"a": {"b": 1.234, "list": [7, 42]}})
    text = macros.render(root)
    assert r"\newcommand{\NumReal}{\nacreNum{1.23}{\mathrm{J}}}" in text
    assert r"\newcommand{\NumMock}{\nacreMockNum{NumMock}{42}{}}" in text
    assert "source: results/x.json  key: a/b" in text
    assert "value: 1.234" in text and "digest" in text.splitlines()[1]
    assert "% \\NumMock  [mock]" in text


def test_scientific_format():
    assert macros.format_value(0.000123, "sci:2") == r"1.23\times10^{-4}"
    assert macros.format_value(9.999, "sci:1") == r"1.0\times10^{1}"
    assert macros.format_value(12345, ",d") == "12{,}345"


@pytest.mark.parametrize("spec,doc,needle", [
    ({"NumX": {"source": "results/x.json", "key": "a/missing", "format": ".1f"}}, {"a": {}}, "no element"),
    ({"NumX": {"source": "results/none.json", "key": "a", "format": ".1f"}}, {"a": 1}, "not found"),
    ({"NumX": {"source": "results/x.json", "key": "a", "format": ".1f"}}, {"a": "text"}, "not a number"),
    ({"NumX": {"source": "results/x.json", "key": "a", "format": ".1f"}}, {"a": float("nan")}, "not finite"),
    ({"bad1": {"source": "results/x.json", "key": "a", "format": ".1f"}}, {"a": 1}, "letters only"),
    ({"NumX": {"source": "results/x.json", "key": "a"}}, {"a": 1}, "missing format"),
])
def test_failures_are_reported(tmp_path, spec, doc, needle):
    root = _tree(tmp_path, spec, doc)
    with pytest.raises(macros.MacroError, match=needle):
        macros.render(root)


def test_every_source_resolves_and_mock_sources_are_marked():
    data = macros.load_sources(REPO)
    for name, spec in data["macros"].items():
        if "/mock/" in spec["source"]:
            assert spec.get("mock") is True, name
        if spec.get("mock"):
            assert spec.get("real_source"), name


def test_cli_registers_every_preprint_command():
    from nacre.cli import build_parser
    parser = build_parser()
    for cmd in ("macros", "declarations", "lint-numbers", "lint-scope", "prepare", "guard"):
        args = parser.parse_args(["preprint", cmd])
        assert callable(args.func), cmd


def test_yaml_sources_patterns_and_reducers(tmp_path):
    root = tmp_path / "r"
    write(root / "configs" / "t.yaml", "decision:\n  p: {primary: 0.9, sweep: [0.6, 0.9, 0.99]}\n"
          "  sizing: {cap: '2**20 base draws', wall: '6 h per run'}\n")
    write(root / "lit" / "log.md", "# Record\n\n## Other\n\n| 1 | 2026-09-30 |\n\n## Query log\n\n"
          "| # | Date |\n|---|---|\n| Q1 | 2026-10-16 |\n| Q2 | 2026-10-14 |\n\n## After\n\n| Q9 | 2026-11-02 |\n"
          "There are 20 000 joint draws.\n")
    spec = {
        "NumP": {"source": "configs/t.yaml", "key": "decision/p/primary", "format": "g"},
        "NumPHigh": {"source": "configs/t.yaml", "key": "decision/p/sweep/2", "format": "g"},
        "NumCap": {"source": "configs/t.yaml", "key": "decision/sizing/cap", "pattern": r"^([0-9]+\*\*[0-9]+)",
                   "format": "power"},
        "NumWall": {"source": "configs/t.yaml", "key": "decision/sizing/wall", "pattern": r"^([0-9]+) h",
                    "format": "d", "unit": r"\mathrm{h}"},
        "NumMonth": {"source": "lit/log.md", "section": "Query log", "pattern": r"\| ([0-9-]{10}) \|",
                     "reduce": "max", "format": "date:%B %Y"},
        "NumFirst": {"source": "lit/log.md", "section": "Query log", "pattern": r"\| ([0-9-]{10}) \|",
                     "reduce": "min", "format": "date:%d %B"},
        "NumCount": {"source": "lit/log.md", "section": "Query log", "pattern": r"\| (Q[0-9]+) \|",
                     "reduce": "count", "format": "d"},
        "NumDraws": {"source": "lit/log.md", "pattern": r"There are ([0-9][0-9 ]*[0-9]) joint", "format": ","},
    }
    write(root / "preprint" / "generated" / "sources.yaml", yaml.safe_dump({"macros": spec}))
    text = macros.render(root)
    assert r"\newcommand{\NumP}{\nacreNum{0.9}{}}" in text
    assert r"\newcommand{\NumPHigh}{\nacreNum{0.99}{}}" in text
    assert r"\newcommand{\NumCap}{\nacreNum{2^{20}}{}}" in text
    assert r"\newcommand{\NumWall}{\nacreNum{6}{\mathrm{h}}}" in text
    assert r"\newcommand{\NumMonth}{\nacreText{October 2026}}" in text   # the section only: not November
    assert r"\newcommand{\NumFirst}{\nacreText{14 October}}" in text
    assert r"\newcommand{\NumCount}{\nacreNum{2}{}}" in text
    assert r"\newcommand{\NumDraws}{\nacreNum{20{,}000}{}}" in text
    assert "section: Query log" in text and "reduce: max" in text


def test_text_values_are_escaped_and_mock_text_is_marked(tmp_path):
    root = _tree(tmp_path, {
        "NumName": {"source": "results/x.json", "key": "a", "format": "text"},
        "NumMockName": {"source": "results/x.json", "key": "a", "format": "text", "mock": True},
    }, {"a": "v1_2 & 50%"})
    text = macros.render(root)
    assert r"\newcommand{\NumName}{\nacreText{v1\_2 \& 50\%}}" in text
    assert r"\newcommand{\NumMockName}{\nacreMockText{NumMockName}{v1\_2 \& 50\%}}" in text


@pytest.mark.parametrize("spec,needle", [
    ({"NumX": {"source": "lit/a.md", "format": "d"}}, "needs pattern"),
    ({"NumX": {"source": "results/x.json", "format": "d"}}, "needs key"),
    ({"NumX": {"source": "lit/a.md", "pattern": "(z+)", "format": "d"}}, "matches nothing"),
    ({"NumX": {"source": "lit/a.md", "pattern": "x", "format": "d"}}, "exactly one group"),
    ({"NumX": {"source": "lit/a.md", "pattern": "(x)", "section": "Nope", "format": "d"}}, "no heading"),
    ({"NumX": {"source": "lit/a.md", "pattern": "(x)", "reduce": "mean", "format": "d"}}, "reduce must be"),
    ({"NumX": {"source": "lit/a.md", "pattern": "(x)", "format": "date:%Y"}}, "not an ISO date"),
    ({"NumX": {"source": "lit/a.md", "pattern": "(x)", "format": "power"}}, "not a power"),
    ({"NumX": {"source": "results/x.json", "key": "a", "pattern": "(x)", "format": "d"}}, "pattern needs text"),
])
def test_pattern_failures_are_reported(tmp_path, spec, needle):
    root = _tree(tmp_path, spec, {"a": 1})
    write(root / "lit" / "a.md", "## Head\n\nx\n")
    with pytest.raises(macros.MacroError, match=needle):
        macros.render(root)


def test_method_conventions_come_from_the_registered_authority_copy():
    """Methods conventions (p_cred and its sweep, m_cos and its sweeps, p_deg, the sizing rule) are
    read from configs/preprint/thresholds.yaml, the copy of theory/thresholds.md (rule R-thr)."""
    data = macros.load_sources(REPO)["macros"]
    for name in ("NumPcred", "NumPcredSweepLow", "NumPcredSweepHigh", "NumPdeg", "NumMcos",
                 "NumMcosSweepLow", "NumMcosSweepHigh", "NumSizingBandHalfWidth", "NumSizingSobolHalfWidth",
                 "NumSizingDrawCap", "NumSizingWallClockCap", "NumSizingChunk"):
        assert data[name]["source"] == "configs/preprint/thresholds.yaml", name
        assert not data[name].get("mock"), name
    conv = yaml.safe_load((REPO / "configs" / "preprint" / "thresholds.yaml").read_text())["decision"]["conventions"]
    values = macros.render(REPO)
    assert r"\NumPcred}{\nacreNum{%g}{}}" % conv["p_cred"]["primary"] in values
    assert r"\NumMcosSweepHigh}{\nacreNum{%g}{}}" % conv["m_cos"]["sweep"][-1] in values


def test_novelty_search_month_spans_one_month():
    """The Introduction prints one month; every designed query of the log must fall in it."""
    spec = macros.load_sources(REPO)["macros"]["NumNoveltySearchMonth"]
    text = macros.section_text((REPO / spec["source"]).read_text(encoding="utf-8"), spec["section"])
    first = macros.extract(text, spec["pattern"], "min")
    last = macros.extract(text, spec["pattern"], "max")
    assert first[:7] == last[:7]
