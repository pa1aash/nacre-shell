"""The generated regime table (PH-W8.2b): reproducible, traceable, in the registered vocabulary, scope-clean."""
import csv
import hashlib
import json
import re
import shutil

import pytest

from nacre.preprint import lint_numbers, lint_scope, macros, paths, regime_table as rt
from preprint_helpers import REPO

GEN = paths.generated(REPO)
FORBIDDEN = re.compile(r"\b(works|protects?|prevents?|self-heals?|outperforms?|nacre-type|falsified|fails at high voltage)\b", re.I)


@pytest.fixture(scope="module")
def rows():
    with (GEN / rt.OUT_CSV).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _cell(rows, rid, col):
    return [r for r in rows if r["row_id"] == rid and r["column"] == col][0]


def _tree(tmp_path):
    root = tmp_path / "repo"
    for rel in list(rt.INPUTS.values()) + ["preprint/generated/sources.yaml"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    return root


def test_regeneration_is_byte_identical():
    assert rt.check(REPO) == []
    first, second = rt.generate(REPO), rt.generate(REPO)
    assert {p: t for p, t in first.items()} == {p: t for p, t in second.items()}
    assert (GEN / rt.OUT_TEX).read_bytes() == first[GEN / rt.OUT_TEX].encode("utf-8")


def test_every_cell_traces_to_a_file_and_its_sha256(rows):
    shas = {rel: hashlib.sha256((REPO / rel).read_bytes()).hexdigest() for rel in rt.INPUTS.values()}
    inputs = json.loads((GEN / rt.OUT_JSON).read_text(encoding="utf-8"))["inputs"]
    assert inputs == shas
    assert len(rows) == 5 * len(rt.ROWS)
    for r in rows:
        files, hashes = r["source_files"], r["source_sha256"]
        if r["words"]:
            assert files, (r["row_id"], r["column"])
            for f, h in zip(files.split("; "), hashes.split("; ")):
                assert shas[f] == h
        else:
            assert not files and r["text"] in ("--", "route criteria")


def test_planted_wrong_cell_fails(tmp_path):
    root = _tree(tmp_path)
    for p, text in rt.generate(root).items():
        p.write_text(text, encoding="utf-8", newline="\n")
    assert rt.check(root) == []
    tex = root / "preprint" / "generated" / rt.OUT_TEX
    tex.write_text(tex.read_text(encoding="utf-8").replace("excluded\\nacreExcludedMark{} & excluded", "open & excluded", 1),
                   encoding="utf-8", newline="\n")
    assert [p.name for p in rt.check(root)] == [rt.OUT_TEX]
    # a changed ladder no longer matches the hash the production outputs were made from
    ladder = root / rt.INPUTS["ladder"]
    ladder.write_text(ladder.read_text(encoding="utf-8").replace("HAp,crystalline,slurry,ALL", "HAp,crystalline,slurry,ALL ", 1),
                      encoding="utf-8", newline="\n")
    with pytest.raises(rt.RegimeTableError, match="sha256"):
        rt.generate(root)


def test_a_planted_class_verdict_that_contradicts_the_bracket_is_refused(tmp_path):
    root = _tree(tmp_path)
    docs, shas = rt.read_inputs(root)
    row = rt.ladder_row(docs["ladder"], "HAp", "crystalline", "slurry")
    row["k1_class_42_43"] = "inconclusive"
    with pytest.raises(rt.RegimeTableError, match="falsifies"):
        rt.k1_class(row, rt.LADDER_COL["C_mid"], rt.edges_of(docs["thresholds"])["C_mid"])


def test_no_forbidden_wording_and_scope_clean(rows):
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    body = "\n".join(l for l in tex.splitlines() if not l.startswith("%"))
    cells = " ".join(r["text"] + " " + r["row_label"] for r in rows)
    assert not FORBIDDEN.search(cells)
    assert not re.search(r"\b(works|protects?|prevents?|self-heals?|outperforms?|nacre-type)\b", body, re.I)
    assert "fails at high voltage" not in tex
    rs, warn = lint_scope.rules(REPO), lint_scope.warn_rules(REPO)
    assert {r for r, _ in warn} >= {"SG29W", "SG30W"}
    blocks = lint_scope._blocks_tex(tex.splitlines())
    assert lint_scope.check_text_blocks(blocks, rt.OUT_TEX, rs, lint_scope.allowlist(REPO), warn) == []
    allow = lint_numbers.allowlist(REPO)
    layout = re.compile(r"\\multicolumn\{[0-9]+\}|\[[0-9.]+pt\]")   # column counts and rule skips are layout, not numbers
    leftover = [(l, re.findall(r"[0-9][0-9.,]*", lint_numbers.scrub(layout.sub(" ", l), allow))) for l in body.splitlines()]
    assert [x for x in leftover if x[1]] == []


def test_vocabulary_footnote_and_kinetic_sentence(rows):
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "\\NumExcludedNote" in tex and "Kinetic stabilisation is not ruled out for phosphates" in tex
    assert "tier-two class B records exist in \\ce{LiPF6} electrolytes, not in fluorine-free ones" in tex
    for r in rows:
        for w in filter(None, r["words"].split("; ")):
            assert w in rt.VOCAB, (r["row_id"], w)
        if "excluded" in r["text"]:
            assert r["column"] != "slurry"
    excluded = [l for l in tex.splitlines() if "excluded" in l and l.startswith(("calcite", "carbonate", "HAp", "ACP", "$"))]
    assert excluded and all("\\nacreExcludedMark{}" in l for l in excluded)


def test_row_labels_match_the_rulings(rows):
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "nacre-type" not in tex.lower()
    labels = {r["row_id"]: r["row_label"] for r in rows}
    assert labels["aragonite"] == "aragonite (dissolution stability only; formation unsupported at slurry pH and room temperature)"
    assert labels["calcite"].startswith("calcite (suitable against dissolution, a necessary condition, in [") and labels["calcite"].endswith("])")
    assert "218 of 324" in labels["calcite"]
    assert tex.count("calcite (suitable against dissolution, a necessary condition, in [") == 1
    assert [r["row_id"] for r in rows if r["column"] == "slurry"] == [r[0] for r in rt.ROWS]
    assert labels["carbonate_ctl"] == "carbonate (K1 control)"


def test_cells_follow_the_data_and_the_rulings(rows):
    assert _cell(rows, "brushite", "C_hi")["text"] == "excluded above 4.43 V"
    assert _cell(rows, "brushite", "C_mid")["text"] == "open"
    assert _cell(rows, "ocp", "slurry")["words"] == "open" and _cell(rows, "ocp", "acid")["words"] == "open"
    for rid in ("brushite", "atcp", "li_ortho"):
        assert _cell(rows, rid, "slurry")["words"] == "undetermined"
    assert "[note b]" in _cell(rows, "brushite", "slurry")["text"] and "[note b]" not in _cell(rows, "li_ortho", "slurry")["text"]
    for rid, ph in (("calcite", "6.5"), ("aragonite", "6.5"), ("acc", "8.5"), ("acp", "5.5")):
        c = _cell(rows, rid, "acid")
        assert c["marker"] == "split by pH (alternative b)" and "[split by pH (alternative b)]" in c["text"]
        assert c["text"].startswith("excluded below pH %s; suitable against dissolution from pH %s up" % (ph, ph))
    for rid in ("hap", "btcp"):
        assert _cell(rows, rid, "acid")["text"].startswith("suitable against dissolution from pH 4.5")
    assert _cell(rows, "carbonate_ctl", "C_hi")["words"] == "excluded" and _cell(rows, "carbonate_ctl", "C_lo")["words"] == "open"
    assert _cell(rows, "hap", "C_mid")["words"] == "excluded"
    assert _cell(rows, "ca_pyro", "slurry")["text"] == "route criteria"
    assert _cell(rows, "baked", "C_hi")["words"] == "undetermined"


def test_the_macro_block_is_current_and_renders():
    text = macros.render(REPO)
    assert re.search(r"\\newcommand\{\\NumRegCrossBrushiteHi\}\{\\nacreNum\{4\.43\}\{\\mathrm\{V\}\}\}", text)
    assert r"\newcommand{\NumRegAcidFirstCalcite}{\nacreNum{6.5}{}}" in text
    assert r"\newcommand{\NumRegGridId}{\nacreText{g1}}" in text
    block = (GEN / "sources.yaml").read_text(encoding="utf-8")
    assert rt.BLOCK_BEGIN in block and rt.BLOCK_END in block


def test_cli_and_results_wiring():
    from nacre.cli import build_parser
    assert callable(build_parser().parse_args(["preprint", "regime-table"]).func)
    results = (paths.paper(REPO) / "sections" / "results.tex").read_text(encoding="utf-8")
    assert "\\input{../generated/regime_table}" in results and "\\label{tab:regime}" in results
    caption = re.search(r"\\caption\{(.*?)\}\\label\{tab:regime\}", results, re.S).group(1)
    assert len(re.sub(r"\\[A-Za-z]+", "", caption).split()) <= 70
    assert not re.search(r"[0-9]", re.sub(r"\$[^$]*\$|\\[A-Za-z]+", "", caption))
