"""The retargeted skeleton (PH-W8.1): section files, briefs, outline, figure and table labels, F4/F6/F8 wording."""
import re

import pytest
import yaml

from nacre.preprint import macros, paths
from preprint_helpers import REPO

PAPER = paths.paper(REPO)
SECTIONS = ["abstract", "introduction", "design", "methods", "results", "predictions", "discussion", "declarations"]
BRIEF_HEADINGS = ["Purpose", "Figures and tables", "Macros needed", "Claims carried", "Supplying lanes"]
FIGURES = ["hero", "pathway", "conditions", "ladder", "phmap", "nucmap", "precision", "heatmap", "alsalt", "k1panel"]
TABLES = ["candidates", "parameters", "thermo", "thresholds", "baselines", "retrodiction"]


def _brief(name):
    return (PAPER / "briefs" / (name + ".md")).read_text(encoding="utf-8")


def _flat(text):
    return " ".join(text.replace("*", "").split())


@pytest.fixture(scope="module")
def claims():
    return yaml.safe_load(paths.claims_yaml(REPO).read_text(encoding="utf-8"))["claims"]


def test_main_inputs_the_new_sections_in_order():
    main = (PAPER / "main.tex").read_text(encoding="utf-8")
    order = [m for m in re.findall(r"\\input\{sections/(\w+)\}", main)]
    assert order == SECTIONS
    for gone in ("inputs", "outlook"):
        assert not (PAPER / "sections" / (gone + ".tex")).exists()
        assert not (PAPER / "briefs" / (gone + ".md")).exists()
    assert "\\input{sections/model}" in (PAPER / "sections" / "design.tex").read_text(encoding="utf-8")


def test_one_brief_per_section_with_the_required_parts():
    briefs = {f.stem for f in (PAPER / "briefs").glob("*.md")}
    assert briefs == set(SECTIONS) | {"si"}
    for name in SECTIONS + ["si"]:
        text = _brief(name)
        for h in BRIEF_HEADINGS:
            assert re.search(r"^## " + re.escape(h), text, re.M), (name, h)
        assert "Length target" in text and ("Physical argument" in text or "## Order" in text or name in ("declarations", "si", "predictions")), name


def test_results_subsections_follow_the_outline():
    text = (PAPER / "sections" / "results.tex").read_text(encoding="utf-8")
    heads = re.findall(r"\\subsection\{([^}]*)\}", text)
    assert heads == ["The regime map", "Processing-stage dissolution stability and the acid-adjusted comparator",
                     "The carbonate control and the $K_1$ exclusion map", "Phosphates and the condensed and aluminium phosphates",
                     "Nucleation and templating as model statements", "The required-precision map", "The baselines"]
    design = (PAPER / "sections" / "design.tex").read_text(encoding="utf-8")
    assert re.findall(r"\\subsection\{([^}]*)\}", design) == ["The four conditions", "The route layer"]
    assert "\\subsection{Templating thermodynamics}" in (PAPER / "sections" / "model.tex").read_text(encoding="utf-8")
    assert "\\section{Discussion and limits}" in (PAPER / "sections" / "discussion.tex").read_text(encoding="utf-8")


def test_carbonate_text_is_marked_with_the_source_comment():
    for name, n in (("introduction", 1), ("methods", 1), ("model", 1), ("results", 1), ("design", 1)):
        text = (PAPER / "sections" / (name + ".tex")).read_text(encoding="utf-8")
        assert text.count("% carbonate control (frozen)") >= n, name


def test_every_claim_id_in_a_brief_exists_and_every_new_claim_is_carried(claims):
    ids = {c["id"] for c in claims}
    all_text = ""
    for name in SECTIONS + ["si"]:
        text = _brief(name)
        all_text += text
        for cid in re.findall(r"CL-[A-Z]\d{2}", text):
            assert cid in ids, (name, cid)
    for c in claims:
        if c["origin"] == "redirect" and c["section"] in SECTIONS:
            text = _brief(c["section"])
            carried = text.split("## Claims carried", 1)[1].split("\n## ", 1)[0]
            assert c["id"] in carried or _in_range(c["id"], carried) or c["section"] == "abstract", (c["section"], c["id"])


def _in_range(cid, text):
    letter, num = cid[3], int(cid[4:])
    for m in re.finditer(r"CL-%s(\d{2}) to CL-%s(\d{2})" % (letter, letter), text):
        if int(m.group(1)) <= num <= int(m.group(2)):
            return True
    return False


def test_labels_figures_and_tables_are_named_in_the_outline():
    outline = (PAPER / "outline.md").read_text(encoding="utf-8")
    for f in FIGURES:
        assert "`fig:%s`" % f in outline, f
    for t in TABLES:
        assert "`tab:%s`" % t in outline, t


def test_results_brief_carries_the_stage_field_and_conversion_rows():
    text = _flat(_brief("results"))
    assert "STAGE" in text and "slurry-stage (brushite, ACP, HAp)" in text
    assert "cell-stage (Ca2P2O7, Ca(PO3)2, AlPO4, Al(PO3)3)" in text
    assert "conversion-step rows" in text and "one per precursor-to-cell-stage pair" in text
    assert "never presents K1 for a condensed phase and K2 to K4 for an orthophosphate as one film" in text
    assert "STAGE" in _flat(_brief("design")) and "never presented as one film" in _flat(_brief("design"))


def test_f6_is_in_the_abstract_and_introduction_briefs():
    for name in ("abstract", "introduction"):
        text = _flat(_brief(name))
        assert "hydroxyapatite" in text.lower() or "HAp" in text
        assert "near carbonate" in text or "near that of carbonate" in text, name
        assert "solid-salt sink" in text and "tier one" in text or "tier one" in text, name
        assert "calcium orthophosphates only" in text, name
        assert "condensed and aluminium phosphates decide" in text, name
        assert "NumOnsetBoneLow" in text and "NumOnsetBoneHigh" in text, name


def test_f8_prior_art_is_stated_plainly_in_the_introduction_brief():
    text = _flat(_brief("introduction"))
    # PH-W8.2c: the claim scope is a metal plate (example: aluminium foil), not aluminium foil
    assert "Al(x)M(y)PO4 and Al(x)M(y)(PO3)3 on a metal plate (example: aluminium foil) are claimed" in text
    assert "recites no film formula" in text
    assert "US 8,252,463" in text and "US 8,821,969" in text
    assert "four qualifiers" in text and "in situ" in text


def test_numbers_are_not_typed_in_the_briefs_for_the_onset_ladder():
    for name in ("abstract", "introduction", "results", "predictions"):
        assert not re.search(r"\b[34]\.\d\d\b", _brief(name)), name      # no onset value typed; macros only


def test_registered_macros_named_in_briefs_exist():
    registered = set(macros.load_sources(REPO)["macros"])
    for name in SECTIONS:
        text = _brief(name)
        part = text.split("## Macros needed", 1)[1].split("\n## ", 1)[0]
        if name == "declarations":
            continue
        for m in re.findall(r"`(Num[A-Za-z0-9]+)`", part):
            if m in {"NumK1HApLow", "NumK1HApHigh"}:
                continue
            line = [l for l in re.split(r"(?<=\.)\s", part) if m in l]
            planned = any("planned" in l or "reserved" in l for l in line) or "Planned" in part or "planned" in part
            assert m in registered or planned, (name, m)


def test_title_macro_is_the_working_title():
    track = yaml.safe_load(paths.track_yaml(REPO).read_text(encoding="utf-8"))["meta"]["title_working"]
    assert " ".join(track.split()) == ("Thermodynamic screening of nacre- and bone-inspired barriers for "
                                       "aluminium current collectors in fluorine-free lithium-ion cells")
    from nacre.preprint import declarations
    assert " ".join(track.split()) in declarations.front_matter(REPO)
