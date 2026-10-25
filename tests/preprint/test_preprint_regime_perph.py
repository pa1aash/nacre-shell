"""Per-pH minimum doses, the dose qualifier, the nucleation wording and the Methods disclosures (PH-W8.2e)."""
import csv
import json
import re
import shutil

import pytest

from nacre.preprint import macros, paths, regime_table as rt
from preprint_helpers import REPO

GEN = paths.generated(REPO)
PAPER = paths.paper(REPO)


def _read(*parts):
    return (PAPER.joinpath(*parts)).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def rows():
    with (GEN / rt.OUT_CSV).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def docs():
    return rt.read_inputs(REPO)[0]


@pytest.fixture(scope="module")
def rendered():
    text = macros.render(REPO)
    return dict(re.findall(r"\\newcommand\{\\(Num[A-Za-z]+)\}\{\\nacre(?:Num|Text)\{([^}]*)\}", text))


def test_per_ph_table_has_every_phase_at_every_acid_ph(docs):
    rows_ = rt.perph_rows_parts(docs)
    assert len(rows_) == len(rt.PERPH_ROWS) * len(rt.perph_phs(docs, "acid")) == 8 * 5
    labels = [r[0] for r in rows_ if r[0]]
    assert len(labels) == 8
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "\\newcommand{\\nacreRegimePerPh}" in tex and "\\newcommand{\\nacreRegimeReruns}" in tex
    assert tex.count("\\NumRegPhPassHap") == 5


def test_per_ph_numbers_are_the_file_numbers(docs, rendered):
    with (REPO / rt.INPUTS["perph"]).open(encoding="utf-8", newline="") as fh:
        src = [r for r in csv.DictReader(fh) if r["grid"] == "acid" and r["phase"] == "HAp" and r["source"] == "frozen"]
    assert len(src) == 5
    for r in src:
        lt = rt.lettered(float(r["pH"]))
        assert rendered["NumRegPhPassHap" + lt] == r["n_passing"]
        assert rendered["NumRegPhFracHap" + lt] == "%.3f" % float(r["passing_fraction"])
    assert rendered["NumRegPhGridFourFive"] == "4.5"


def test_every_first_pass_entry_names_its_minimum_dose(rows):
    for rid in ("calcite", "aragonite", "acc", "hap", "acp", "btcp"):
        text = [r for r in rows if r["row_id"] == rid and r["column"] == "acid"][0]["text"]
        assert re.search(r"suitable against dissolution from pH [0-9.]+", text)
        assert "lowest passing Ca_T" in text and re.search(r"Ca_T [0-9.e+-]+", text), rid
        if rid in ("hap", "acp", "btcp"):
            assert "lowest passing" in text and "P_T" in text and "mol dm^-3" in text
        # at 0.01 mol dm^-3 or above the entry says so
        nums = [float(x) for x in re.findall(r"(?:Ca_T|P_T) ([0-9.]+e[+-][0-9]+)", text)]
        assert nums and (max(nums) >= rt.HIGH_DOSE) == (rt.HIGH_TEXT in text), rid


def test_high_dose_rule_on_the_per_ph_rows(docs):
    rows_ = rt.perph_rows_parts(docs)
    phs = rt.perph_phs(docs, "acid")
    expect = []
    for key, csvname, _label, src in rt.PERPH_ROWS:
        for ph in phs:
            r = rt.perph_row(docs, "acid", src, csvname, ph)
            expect.append("--" if not r["n_pass"] else ("yes" if max(v for v in (r["ca"], r["p"]) if v is not None) >= 0.01 else "no"))
    got = [r[8][0] if isinstance(r[8], list) else r[8] for r in rows_]
    assert got == expect and "yes" in got and "no" in got


def test_dose_qualifier_wording(rows):
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    body = " ".join(l for l in tex.splitlines() if not l.startswith("%"))
    assert "comparable to the order of the sourced additive doses" in body
    for m in re.finditer(r"\bequal\b", body):
        assert body[m.start() - 4:m.start()] == "not ", body[m.start() - 40:m.start() + 20]
    assert "p_total_slurry" not in body and "h3po4" not in body
    assert not re.search(r"suitable against dissolution from pH~\\NumRegAcidFirst\w+\{\}\s*(?:up)?\s*&", body)


def test_f3_macros_are_the_file_numbers(docs, rendered):
    f3 = json.loads((REPO / rt.INPUTS["f3"]).read_text(encoding="utf-8"))
    gsl = f3["gamma_sl_J_m2"]["admitted_draws"]
    assert rendered["NumNucGslQFive"] == "%.3g" % (gsl["q05"] * 1000)
    assert rendered["NumNucGslMedian"] == "%.3g" % (gsl["q50"] * 1000)
    assert rendered["NumNucGslMax"] == "%.3g" % (gsl["max"] * 1000)
    assert rendered["NumNucMassSourced"] == "0.29" and rendered["NumNucMassDesignMax"] == "3.4"
    assert rendered["NumNucLinkFalsified"] == "24" and rendered["NumNucLinkDesigns"] == "36" and rendered["NumNucLinkInconclusive"] == "12"
    assert rendered["NumSobolNucHalfWidth"] == "0.098" and rendered["NumSobolNucTarget"] == "0.02"


def test_f3_sentence_and_forbidden_words():
    res = " ".join(re.sub(r"%.*", "", l) for l in _read("sections", "results.tex").splitlines())
    res = " ".join(res.split())
    for frag in ("For a solid phosphate nucleus on a hydrophilic template, a contact angle below 90 degrees requires $\\gsn$ below $\\gsl$, which lies between "
                 "\\NumNucGslQFive\\ and \\NumNucGslQNinetyFive\\ (median \\NumNucGslMedian; admitted draws span \\NumNucGslMin\\ to \\NumNucGslMax).",
                 "The registered ignorance prior puts \\NumNucMassSourced\\ of its mass there under the sourced calcite",
                 "and at most \\NumNucMassDesignMax\\ over the design points with enough admitted draws, whatever",
                 "(its support widens with",
                 "would decide it.",
                 "The nucleation half of the model failed its retrodiction (\\NumRetroCorrect\\ of \\NumRetroUsableCases\\ against \\NumRetroPassCount), "
                 "so this is a model statement, not evidence that templated nucleation is impossible.",
                 "falsified within the registered model at \\NumNucLinkFalsified\\ of \\NumNucLinkDesigns\\ design points; the other \\NumNucLinkInconclusive\\ are inconclusive."):
        assert frag in res, frag
    assert "cannot" not in res
    assert res.count("impossible") == 1 and res.index("impossible") > res.index("so this is a model statement")
    for m in re.finditer(r"(?<!not )falsified", res):    # "not falsified" defines the word open (W3.8 R1-1), not a verdict
        assert "within the registered model" in res[m.start() - 80:m.start() + 60]


def test_methods_f2_f4_f5_wording():
    meth = " ".join(re.sub(r"%.*", "", l) for l in _read("sections", "methods.tex").splitlines())
    meth = " ".join(meth.split())
    assert "The production run of the phosphate dissolution test crossed total calcium and total phosphate independently on one decade grid" in meth
    assert "the apatite ratios \\NumRatioTcp\\ and \\NumRatioHap\\ do not occur in it" in meth
    assert "A ratio grid was run as a separate, labelled run beside the production run" in meth and "ratio-grid run, with total phosphate" not in meth
    assert "The verdicts are unchanged: \\NumRatioVerdictSame\\ of \\NumRatioVerdictTotal\\" in meth
    assert "\\NumRatioGroupsDiffer\\ differ in the lowest passing $\\mathrm{Ca_T}$ only" in meth
    assert "the ratio itself on a ratio line" in meth
    assert "the grid state of maximum $\\Omega$ for that phase and state" in meth
    assert "moved from pH \\NumCtlPhFrom\\ to pH \\NumCtlPhTo\\ after a dry run, an output seen before the choice" in meth
    assert "leaves every cell of the original keys unchanged (\\NumCtlCellsMoved\\ cells moved)" in meth   # review m12
    assert "so they are indicative and the Shapley effects carry the ranking" in meth and "\\NumSobolNucHalfWidth" in meth


def test_si_reruns_and_sensitivity(rendered):
    si = " ".join(re.sub(r"%.*", "", l) for l in _read("si", "main_si.tex").splitlines())
    tex = (GEN / rt.OUT_TEX).read_text(encoding="utf-8")
    assert "byte-identical to the nominal ladder, so no verdict changes at" in tex
    assert "\\nacreRegimeSensNote{}" in si and "\\nacreRegimeReruns" in si and "\\nacreRegimePerPh" in si
    assert "brushite" in si.lower() and "are a deviation from the frozen production" in si
    assert rendered["NumRegRerunBrushiteAcidRerun"] == "85" and rendered["NumRegRerunBrushiteAcidCells"] == "540"
    assert rendered["NumRegRerunBrushiteAlkalineRerun"] == "3"
    assert rendered["NumCtlCellsMoved"] == "0" and rendered["NumCtlPhFrom"] == "12" and rendered["NumCtlPhTo"] == "7.65"
    low = tex.lower()
    assert "feasible" not in low.replace("\\newcommand", "")


def test_planted_disagreement_between_frozen_and_rerun_rows_is_refused(tmp_path, docs):
    root = tmp_path / "repo"
    for rel in list(rt.INPUTS.values()) + ["preprint/generated/sources.yaml"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    perph = root / rt.INPUTS["perph"]
    lines = perph.read_text(encoding="utf-8").splitlines()
    k = [i for i, l in enumerate(lines) if l.startswith("acid,rerun,HAp,4.5,")][0]
    cols = lines[k].split(",")
    cols[5] = str(int(cols[5]) + 1)
    lines[k] = ",".join(cols)
    perph.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(rt.RegimeTableError, match="differ"):
        rt.generate(root)


# ---------------------------------------------------------------- ratio grid (PH-W8.2g)

def _sci(text):
    m = re.match(r"([0-9.]+)\\times10\^\{(-?[0-9]+)", text)
    return float(m.group(1) + "e" + m.group(2))


def _mant_exp(v):
    import math
    e = math.floor(math.log10(v))
    return round(v / 10 ** e, 1), e


def _ratio_csv():
    with (REPO / rt.INPUTS["perph3"]).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def test_second_column_group_is_the_ratio_grid_file(docs, rendered):
    rows_ = rt.perph_rows_parts(docs)
    assert all(len(r) == 13 for r in rows_) and len(rt.PERPH_HEAD) == 13
    src = {(r["grid"], r["source"], r["phase"], float(r["pH"])): r for r in _ratio_csv()}
    for key, phase, ratio in (("hap", "HAp", "1.67"), ("btcp", "b-TCP", "1.5"), ("brushite", "brushite", "1")):
        for ph in rt.perph_phs(docs, "acid"):
            r = src[("acid", "ratio_" + ratio, phase, ph)]
            lt, nm = rt.lettered(ph), rt.pascal(key)
            assert _sci(rendered["NumRegPhStoichCa" + nm + lt]) == pytest.approx(float(r["min_passing_Ca_T_mol_dm3"]), rel=0.5)
            assert rendered["NumRegPhStoichP" + nm + lt].startswith("%.1f\\times10^{%d" % tuple(_mant_exp(float(r["min_passing_P_T_mol_dm3"]))))
    for r in rows_:
        if r[0] in ("calcite", "aragonite", "ACC", "ACP") or r[0].startswith("OCP"):
            assert [c[0] for c in r[9:]] == ["--"] * 4


def test_own_ratio_minima_are_the_stated_doses(rendered):
    want = {"HapSlurry": ("1e-05", "6.0e-06", "10.0"), "HapAcid": ("1e-04", "6.0e-05", "8.5"),
            "BtcpSlurry": ("1e-04", "6.7e-05", "10.0"), "BtcpAcid": ("1e-03", "6.7e-04", "7.5"),
            "BrushiteSlurry": ("1e-01", "1.0e-01", "10.0"), "BrushiteAcid": ("1e-02", "1.0e-02", "5.5")}
    for k, (ca, p, ph) in want.items():
        got = [rendered["NumRegOwn%s%s" % (k, q)] for q in ("Ca", "P", "Ph")]
        assert got[2] == ph
        assert [_sci(g) for g in got[:2]] == [float(ca), float(p)], (k, got)
    assert rendered["NumRegPhGridFourFive"] == "4.5"


def test_first_pass_cells_name_both_doses(rows):
    for rid, ratio in (("hap", "1.67"), ("btcp", "1.5")):
        text = [r for r in rows if r["row_id"] == rid and r["column"] == "acid"][0]["text"]
        assert "on the crossed grid" in text and "at its own Ca:P of " + ratio + ", lowest passing Ca_T" in text, text
        assert text.count("lowest passing Ca_T") == 2 and text.count("P_T") == 2 and rt.HIGH_TEXT in text
    acp = [r for r in rows if r["row_id"] == "acp" and r["column"] == "acid"][0]["text"]
    assert "own Ca:P" not in acp


def test_ratio_grid_text_is_plain_and_scoped():
    si = " ".join(re.sub(r"%.*", "", l) for l in _read("si", "main_si.tex").splitlines())
    si = " ".join(si.split())
    assert "a ratio-grid run is pending" not in si
    assert "lie well below the order of the sourced additive doses" in si and "the comparison is of order only" in si
    assert "stays a high-dose phase at the low-pH end" in si
    assert "the lowest passing dose of the apatites is at or above \\NumRegHighDose, on the crossed grid" in si   # review M9: the flag names its threshold
    mine = si[si.index("The production run crossed"):si.index("on the crossed grid. ")]
    assert "equal" not in mine and not re.search(r"suitable against dissolution from pH", si)


def test_planted_ratio_grid_disagreement_is_refused(tmp_path):
    root = tmp_path / "repo"
    for rel in list(rt.INPUTS.values()) + ["preprint/generated/sources.yaml"]:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, root / rel)
    path = root / rt.INPUTS["perph3"]
    lines = path.read_text(encoding="utf-8").splitlines()
    k = [i for i, l in enumerate(lines) if l.startswith("acid,crossed,HAp,4.5,")][0]
    cols = lines[k].split(",")
    cols[5] = str(int(cols[5]) + 1)
    lines[k] = ",".join(cols)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(rt.RegimeTableError, match="differs from the per-pH table"):
        rt.generate(root)


def test_carbonate_acid_sentence_names_the_grid_points_inside_the_sourced_range():
    """PH-W8.9 (G8): Section 4.2 names the grid points inside the sourced range, by macro, not 'sourced slurries'."""
    text = (PAPER / "sections" / "results.tex").read_text(encoding="utf-8")
    assert "not in sourced acid-adjusted slurries" not in text
    assert (r"and not at the grid points inside the sourced range (pH \NumRegPhGridSixFive, "
            r"\NumRegPhGridSevenFive\ and \NumRegPhGridEightFive)") in text
