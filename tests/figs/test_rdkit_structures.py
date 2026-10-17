"""The RDKit structure set: shared SMILES, RSC structure settings, vector output, no annotation."""
import math
import re

import pytest
from figs_helpers import REPO

from nacre.figs import structures as S
from nacre.figs import style

STANDALONE = [n for n, e in S.table(REPO).items() if e.get("standalone", True)]
REQUIRED = {"catechol", "catecholate_monoanion", "catecholate_dianion", "quinone", "oligomer", "acetate",
            "chitosan_unit"}


def test_the_set_holds_every_required_structure():
    assert REQUIRED <= set(STANDALONE)


def test_no_smiles_is_typed_in_the_table():
    text = (REPO / "figures/rdkit/structures.yaml").read_text()
    assert not re.search(r"^\s*smiles\s*:", text, re.M)


def test_shared_structures_use_the_shared_definitions():
    from nacre.anchor.builders import LIGANDS
    from nacre.structures import oligomer
    assert S.smiles("catecholate_dianion", REPO)[0] == LIGANDS["catecholate_dianion"][0]
    assert S.smiles("acetate", REPO)[0] == LIGANDS["acetate"][0]
    assert S.smiles("oligomer", REPO)[0] == oligomer.dhi_chain_smiles(oligomer.DEFAULTS["n_units"])


def test_fetched_catechol_is_the_parent_of_the_shared_catecholates():
    from rdkit import Chem
    from rdkit.Chem.MolStandardize import rdMolStandardize
    parent = Chem.MolToSmiles(Chem.MolFromSmiles(S.smiles("catechol", REPO)[0]))
    un = rdMolStandardize.Uncharger()
    for name in ("catecholate_monoanion", "catecholate_dianion"):
        mol = un.uncharge(Chem.MolFromSmiles(S.smiles(name, REPO)[0]))
        assert Chem.MolToSmiles(mol) == parent, name


def test_chitosan_unit_is_glucosamine_with_two_attachment_points():
    from rdkit.Chem import rdMolDescriptors
    mol = S.molecule("chitosan_unit", REPO)
    assert sum(1 for a in mol.GetAtoms() if a.GetAtomicNum() == 0) == 2
    assert rdMolDescriptors.CalcMolFormula(mol).startswith("C6H")
    assert sum(1 for a in mol.GetAtoms() if a.GetSymbol() == "N") == 1


def test_derivation_refuses_a_non_pyranose():
    from rdkit import Chem
    with pytest.raises(ValueError):
        S.DERIVATIONS["beta_1_4_repeat_unit"](Chem.MolFromSmiles("OCCO"))


@pytest.mark.parametrize("name", STANDALONE)
def test_drawing_follows_the_rsc_structure_settings(name):
    import pymupdf
    a = style.applied(REPO)
    pdf = REPO / "figures/out/rdkit" / (name + ".pdf")
    with pymupdf.open(pdf) as doc:
        page = doc[0]
        assert page.get_text().strip() == "" and page.get_fonts() == []
        strokes = [d for d in page.get_drawings() if d.get("type") == "s"]
        assert {round(d["width"], 3) for d in strokes} == {float(a["structure_bond_width"]["value"])}
        lengths = [math.dist(it[1], it[2]) for d in strokes for it in d["items"] if it[0] == "l"]
    assert max(lengths) == pytest.approx(float(a["structure_bond_length"]["value"]), abs=0.6)


def _label_height(pdf):
    import pymupdf
    with pymupdf.open(pdf) as doc:
        return max(d["rect"].height for d in doc[0].get_drawings() if d.get("type") == "f")


def _cap_o(font_path, size):
    from matplotlib.ft2font import FT2Font
    ft = FT2Font(font_path)
    ft.set_size(size, 72)
    g = ft.load_char(ord("O"))
    return (g.bbox[3] - g.bbox[1]) / 64.0


def test_atom_labels_are_set_at_the_rsc_label_size(tmp_path):
    # Drawn now with whichever face of the chain is installed and measured against that face, so
    # the test holds for Arial, Helvetica or Liberation Sans alike (lane note N18).
    size = float(style.applied(REPO)["structure_label_font_size"]["value"])
    pdf = tmp_path / "catechol.pdf"
    S.svg_to_pdf(S.svg("catechol", REPO), pdf)
    assert _label_height(pdf) == pytest.approx(_cap_o(S.font_file(REPO), size), rel=0.08)


def test_committed_structures_are_release_drawings():
    import json
    recs = json.loads((REPO / "figures/out/manifest.json").read_text())["rdkit"]
    release = style.font_chain(REPO)[0]
    assert set(recs) == set(STANDALONE)
    for name, rec in recs.items():
        assert rec["font"]["family"] == release and rec["font"]["release"] is True, name


def test_drawing_is_reproducible():
    name = "acetate"
    first = S.svg(name, REPO)
    assert S.svg(name, REPO) == first
    # The committed drawing is a release (Arial) drawing; it is compared byte for byte only
    # where that face is the one installed. Elsewhere the outlines differ by design.
    if style.font(REPO)["release"]:
        assert first == (REPO / "figures/out/rdkit" / (name + ".svg")).read_text()
