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
