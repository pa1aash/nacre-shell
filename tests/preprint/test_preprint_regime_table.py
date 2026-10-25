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
    layout = re.compile(r"\\multicolumn\{[0-9]+\}|\\cmidrule\(lr\)\{[0-9]+-[0-9]+\}|\[[0-9.]+pt\]")   # column counts, column ranges and rule skips are layout, not numbers
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
    assert excluded and all("\\nacreExcludedMark{}" in l or "\\nacreDissolutionMark{}" in l for l in excluded)
    # an exclusion against dissolution (K2) carries its own mark, never the tier-one footnote (review M8, W3.8 R6-8)
    for r in rows:
        if r["column"] == "acid" and "excluded" in r["text"]:
            assert "excluded against dissolution" in r["text"], r["row_id"]
    assert "\\nacreDissolutionMark{} Excluded against dissolution (thermodynamic, $K_2$" in tex


def test_row_labels_match_the_rulings(rows):
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "nacre-type" not in tex.lower()
    labels = {r["row_id"]: r["row_label"] for r in rows}
    assert labels["aragonite"] == "aragonite (dissolution stability only; formation unsupported at slurry pH and room temperature)"
    assert labels["calcite"].startswith("calcite (suitable against dissolution, a necessary condition, in [") and labels["calcite"].endswith("])")
    # the passing region is named by its Ca_T bound, not by the box of the grid (review B2, claims_redirect 11h)
    assert "Ca_T >= 1e-04 mol dm^-3, 216 cells, plus 2 cells at 1e-05" in labels["calcite"]
    assert "218 of 324 cells: Ca_T >= 1e-04" in _cell(rows, "calcite", "slurry")["text"]
    assert tex.count("calcite (suitable against dissolution, a necessary condition, in [") == 1
    assert [r["row_id"] for r in rows if r["column"] == "slurry"] == [r[0] for r in rt.ROWS]
    assert labels["carbonate_ctl"] == "carbonate (K1 control)"


def test_cells_follow_the_data_and_the_rulings(rows):
    assert _cell(rows, "brushite", "C_hi")["text"] == "excluded above 4.43 V"
    assert _cell(rows, "brushite", "C_mid")["text"] == "open"
    # a K2 cell whose control fails reads inconclusive, never open (claims_redirect 11d, amendment rule 4)
    assert _cell(rows, "ocp", "slurry")["text"] == "inconclusive (control fails)" and _cell(rows, "ocp", "acid")["words"] == "inconclusive"
    for rid in ("brushite", "atcp", "li_ortho"):
        assert _cell(rows, rid, "slurry")["words"] == "undetermined"
    assert "[note b]" in _cell(rows, "brushite", "slurry")["text"] and "[note b]" not in _cell(rows, "li_ortho", "slurry")["text"]
    # below the first pass: excluded where every cell is falsified, open where none passes and some are inconclusive;
    # cp6 F9: the lowest run is named by its grid pH values, never as "below pH x"
    below = "excluded against dissolution at pH 4.5 and 5.5 (every cell dissolves; lower passivation window, below the sourced range); "
    for rid, ph, lead in (("calcite", "6.5", below), ("aragonite", "6.5", below),
                          ("acc", "8.5", below + "inconclusive at pH 6.5 and 7.5; "), ("acp", "5.5", "inconclusive at pH 4.5; ")):
        c = _cell(rows, rid, "acid")
        assert c["marker"] == "split by pH (alternative b)" and "[split by pH (alternative b)]" in c["text"]
        assert c["text"].startswith(lead + "suitable against dissolution from pH %s up" % ph)
    for rid in ("hap", "btcp"):
        assert _cell(rows, rid, "acid")["text"].startswith("suitable against dissolution from pH 4.5")
    assert _cell(rows, "carbonate_ctl", "C_hi")["words"] == "excluded" and _cell(rows, "carbonate_ctl", "C_lo")["words"] == "open"
    assert _cell(rows, "hap", "C_mid")["words"] == "excluded; excluded"
    # edge rule of thresholds block v10: robust threshold and edge sensitivity within the tolerance (ruling 2)
    for rid in ("hap", "btcp"):
        assert _cell(rows, rid, "C_mid")["text"].startswith(
            "crystalline: excluded at 4.3 V; edge-sensitive at 4.2 (crossover within 50 mV); amorphous: excluded (by the bound")
    assert _cell(rows, "atcp", "C_mid")["text"].startswith("crystalline: excluded; amorphous: excluded (by the bound")
    # pass counts above the first passing pH use the cells of those pH values (claims_redirect 11d, comparator window iv)
    assert "68 of 162 cells from that pH up" in _cell(rows, "calcite", "acid")["text"]
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


# ------------------------------------------------------------------ I17a: the amorphous cells (contract v8, block v11)
AMORPHOUS_ROWS = {"acp": "ACP", "hap": "HAp", "btcp": "b-TCP", "atcp": "a-TCP"}
BOUND_LABEL = "excluded (by the bound dG_g-to-c >= 0, against the crystalline reference plus water)"


def test_amorphous_label_is_read_from_the_thresholds_copy():
    import yaml
    copy = yaml.safe_load((REPO / rt.INPUTS["thresholds"]).read_text(encoding="utf-8"))
    assert copy["screen_ph"]["w36"]["regime_table"]["amorphous_rows"]["cell_word_excluded"] == BOUND_LABEL


def test_amorphous_cells_follow_the_crystalline_reference_row(rows):
    """Excluded by the bound at C_mid and C_hi where the crystalline row is excluded, undetermined at C_lo (ACP names it)."""
    for rid in AMORPHOUS_ROWS:
        for col in ("C_mid", "C_hi"):
            c = _cell(rows, rid, col)
            assert c["words"] == "excluded; excluded" and c["text"].count(BOUND_LABEL) == 1, (rid, col)
        assert BOUND_LABEL not in _cell(rows, rid, "C_lo")["text"]
    assert _cell(rows, "acp", "C_lo")["text"].endswith("amorphous: undetermined")


def test_every_changed_amorphous_cell_cites_its_crystalline_reference_row(rows):
    changed = [r for r in rows if BOUND_LABEL in r["text"]]
    assert sorted((r["row_id"], r["column"]) for r in changed) == sorted(
        (rid, col) for rid in AMORPHOUS_ROWS for col in ("C_mid", "C_hi"))
    ladder = rt.INPUTS["ladder"]
    for r in changed:
        assert "crystalline reference row %s, slurry (%s)" % (AMORPHOUS_ROWS[r["row_id"]], ladder) in r["note"], r["row_id"]
        assert ladder in r["source_files"].split("; ") and "dG_g-to-c >= 0 (I17a)" in r["note"]
        assert "framing crystalline" in r["note"]           # the crystalline reading it was derived from


def test_other_amorphous_readings_are_not_changed_by_the_bound(rows):
    """Brushite, Ca2P2O7, OCP and the aluminium phosphates carry no excluded-by-bound word; the glass rows keep theirs."""
    for rid in ("brushite", "ocp", "ca_pyro", "ca_meta_glass", "al_ortho", "al_meta", "al_polyp", "lipo3n", "baked", "li_ortho"):
        for col in ("C_lo", "C_mid", "C_hi"):
            assert "by the bound" not in _cell(rows, rid, col)["text"], (rid, col)


def test_the_legend_states_the_rule_and_the_old_wording_is_gone():
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "where its crystalline row is excluded, and undetermined otherwise" in tex
    assert "not yet registered" not in tex and "I17a not registered" not in (GEN / rt.OUT_CSV).read_text(encoding="utf-8")


def test_a_reference_row_that_is_not_excluded_gives_an_undetermined_amorphous_word():
    row = {"phase": "HAp", "E_ub_V": "4.0674", "margin_V": "0.1244", "k1_class_lfp": "inconclusive"}
    label = BOUND_LABEL
    assert rt.amorphous_word(row, "C_lo", [4.1], label, {"C_lo": "undetermined"}) == "undetermined"
    with pytest.raises(rt.RegimeTableError, match="disagrees"):
        rt.amorphous_word(row, "C_lo", [4.1], label, {"C_lo": "falsified (bound)"})


def test_every_amorphous_lowest_class_cell_reads_undetermined_explicitly(rows):
    for rid in ("hap", "btcp", "atcp"):
        assert _cell(rows, rid, "C_lo")["text"] == "crystalline: open; amorphous: undetermined"
    assert _cell(rows, "acp", "C_lo")["text"] == "beta-TCP reference: open; amorphous: undetermined"


def test_table_and_prose_agree_on_the_amorphous_cells(rows):
    # C12 of PH-W3.9: a cell that reads excluded by the bound is matched by prose naming the same bound and reference;
    # a cell that reads undetermined is never called excluded in prose.
    prose = " ".join((REPO / "preprint/paper/sections" / f).read_text() for f in ("results.tex", "discussion.tex", "design.tex"))
    flat = re.sub(r"\s+", " ", prose)
    by_bound = [r for r in rows if r["column"] in ("C_mid", "C_hi") and "excluded (by the bound" in r["text"]]
    assert {r["row_id"] for r in by_bound} == set(AMORPHOUS_ROWS)
    assert "$\\Delta G_{\\mathrm{g}\\to\\mathrm{c}}\\ge0$ against the crystalline reference of the same composition plus liquid water" in flat
    assert "At the lowest class (\\NumClassLo) the crystalline rows are open and the amorphous framing of every phosphate stays undetermined" in flat
    assert "undetermined: the bound" not in flat and "a reading not yet registered" not in flat
    assert not any("excluded" in r["text"].split("amorphous:")[-1] for r in rows if r["column"] == "C_lo" and r["row_id"] in AMORPHOUS_ROWS)


def test_no_acid_cell_states_a_sharp_threshold_below_a_grid_point():
    # cp6 F9: the acid grid has points only at its pH values, so no cell says "below pH"
    with (GEN / rt.OUT_CSV).open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert not [r["row_id"] for r in rows if "below pH" in r["text"]]
    assert "below pH" not in (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
