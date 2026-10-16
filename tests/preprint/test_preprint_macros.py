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


def test_committed_numbers_tex_is_up_to_date():
    assert paths.numbers_tex(REPO).read_text(encoding="utf-8") == macros.render(REPO)


def test_real_and_mock_macros_and_provenance(tmp_path):
    root = _tree(tmp_path, {
        "NumReal": {"source": "results/x.json", "key": "a/b", "format": ".2f", "unit": r"\mathrm{J}"},
        "NumMock": {"source": "results/x.json", "key": "a/list/1", "format": "d", "mock": True},
    }, {"a": {"b": 1.234, "list": [7, 42]}})
    text = macros.render(root)
    sha = subprocess.run(["git", "hash-object", str(root / "results" / "x.json")],
                         capture_output=True, text=True, check=True).stdout.strip()
    assert r"\newcommand{\NumReal}{\nacreNum{1.23}{\mathrm{J}}}" in text
    assert r"\newcommand{\NumMock}{\nacreMockNum{NumMock}{42}{}}" in text
    assert "source: results/x.json  blob %s" % sha in text
    assert "% \\NumMock  [mock]" in text
    assert "key: a/b" in text


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
