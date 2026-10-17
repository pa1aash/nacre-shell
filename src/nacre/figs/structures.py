"""The RDKit structure set: SMILES from shared definitions, drawn as vector SVG and PDF.

figures/rdkit/structures.yaml lists the structures and where each SMILES comes from; nothing
is typed here. Drawings follow the RSC chemical-structure settings in figures/style/rsc_spec.yaml
(applied: bond length, bond width, double-bond space, atom-label size) and the element colours
of figures/style/palette.yaml; the label font is the figure font (applied.font_family).

RDKit draws atom labels as glyph outlines, and the PDF is converted from the SVG by MuPDF, in
which one SVG unit is one point. The only marks are bonds and the element symbols RDKit draws
as part of a structure (with charges); there is no other annotation.
"""
import json
from functools import lru_cache
from pathlib import Path

import yaml

from nacre.figs import paths, style

FONT_SIZE_PER_PT = 1.0  # RDKit fixedFontSize is the em size in SVG units (checked against the font metrics in tests)
PADDING_PT = 2.0


def rdkit_dir(root):
    return paths(root)["root"] / "figures" / "rdkit"


def out_dir(root):
    return paths(root)["out"] / "rdkit"


@lru_cache(maxsize=4)
def _table(path):
    return yaml.safe_load(Path(path).read_text())["structures"]


def table(root):
    return _table(str(rdkit_dir(root) / "structures.yaml"))


# ------------------------------------------------------------------------------- sources

def _pubchem(root, cid):
    rec = json.loads((rdkit_dir(root) / "sources" / ("pubchem_cid%d.json" % cid)).read_text())
    return rec["PropertyTable"]["Properties"][0]["SMILES"]


def _beta_1_4_repeat_unit(mol):
    """beta-(1->4) repeat unit of a glucopyranose-type residue: the anomeric O1 becomes the
    attachment point of C1 (it belongs to the next residue as its O4) and O4 gains the second
    attachment point. O1 is replaced in place, so the stereo tags at C1 keep their meaning.
    """
    from rdkit import Chem
    patt = Chem.MolFromSmarts(
        "[OX2;R]1[CX4;R]([OX2H1;!R])[CX4;R]([NX3;!R])[CX4;R]([OX2H1;!R])[CX4;R]([OX2H1;!R])[CX4;R]1[CH2][OX2H1]")
    hits = mol.GetSubstructMatches(patt)
    if len(hits) != 1:
        raise ValueError("expected one glucopyranose residue, found %d" % len(hits))
    o1, o4 = hits[0][2], hits[0][8]
    rw = Chem.RWMol(mol)
    rw.ReplaceAtom(o1, Chem.Atom(0))
    star = rw.AddAtom(Chem.Atom(0))
    rw.AddBond(o4, star, Chem.BondType.SINGLE)
    rw.GetAtomWithIdx(o4).SetNoImplicit(True)
    rw.GetAtomWithIdx(o4).SetNumExplicitHs(0)
    out = rw.GetMol()
    Chem.SanitizeMol(out)
    return out


DERIVATIONS = {"beta_1_4_repeat_unit": _beta_1_4_repeat_unit}


def smiles(name, root):
    """(SMILES, provenance string) of a structure, from its declared source."""
    e = table(root)[name]
    src = e["source"]
    if src == "shared_ligand":
        from nacre.anchor.builders import LIGANDS
        return LIGANDS[e["ligand"]][0], "nacre.anchor.builders.LIGANDS[%r]" % e["ligand"]
    if src == "shared_oligomer":
        from nacre.structures import oligomer
        n = oligomer.DEFAULTS["n_units"] if e["n_units"] == "default" else int(e["n_units"])
        return oligomer.dhi_chain_smiles(n), "nacre.structures.oligomer.dhi_chain_smiles(%d)" % n
    if src == "pubchem":
        return _pubchem(root, e["cid"]), "PubChem CID %d (figures/rdkit/sources)" % e["cid"]
    raise ValueError("%s: unknown source %r" % (name, src))


def molecule(name, root):
    """RDKit molecule of a structure with deterministic 2D coordinates."""
    from rdkit import Chem
    from rdkit.Chem import rdDepictor
    smi, _ = smiles(name, root)
    mol = Chem.MolFromSmiles(smi)
    derive = table(root)[name].get("derive")
    if derive:
        mol = DERIVATIONS[derive](mol)
    rdDepictor.SetPreferCoordGen(True)
    rdDepictor.Compute2DCoords(mol)
    return mol


# ------------------------------------------------------------------------------- drawing

def _settings(root):
    a = style.applied(root)
    return {
        "bond_pt": float(a["structure_bond_length"]["value"]),
        "width_pt": float(a["structure_bond_width"]["value"]),
        "double_space": float(a["structure_double_bond_space"]["value"]),
        "font_pt": float(a["structure_label_font_size"]["value"]),
    }


def font_file(root):
    """The label font file: the first installed face of the figure-font chain (style.font)."""
    return style.font(root)["file"]


def _palette_rgb(root):
    from rdkit.Chem import GetPeriodicTable
    pt = GetPeriodicTable()
    out = {}
    for sym, e in style.palette(root)["elements"].items():
        out[pt.GetAtomicNumber(sym)] = tuple(float(x) for x in e["srgb"])
    out[6] = (0.0, 0.0, 0.0)  # skeletal carbon is drawn in the text colour, as bonds
    return out


def svg(name, root):
    """SVG text of one structure at RSC structure settings (1 SVG unit = 1 pt)."""
    from rdkit.Chem.Draw import rdMolDraw2D
    s = _settings(root)
    mol = molecule(name, root)
    d = rdMolDraw2D.MolDraw2DSVG(-1, -1)
    o = d.drawOptions()
    o.fixedBondLength = s["bond_pt"]
    o.bondLineWidth = s["width_pt"]
    o.scaleBondWidth = False
    o.multipleBondOffset = s["double_space"]
    o.fixedFontSize = int(round(s["font_pt"] * FONT_SIZE_PER_PT))
    o.minFontSize = o.maxFontSize = o.fixedFontSize
    o.fontFile = font_file(root)
    o.clearBackground = False
    o.padding = 0.0
    o.additionalAtomLabelPadding = 0.05
    o.dummiesAreAttachments = True
    o.includeMetadata = False
    o.setAtomPalette(_palette_rgb(root))
    d.DrawMolecule(mol)
    d.FinishDrawing()
    return d.GetDrawingText()


def svg_to_pdf(svg_text, pdf_path):
    """Convert with MuPDF and save without dates or a random document id (byte-reproducible)."""
    import pymupdf
    src = pymupdf.open(stream=svg_text.encode("utf-8"), filetype="svg")
    pdf = pymupdf.open("pdf", src.convert_to_pdf())
    pdf.set_metadata({})
    pdf.save(str(pdf_path), garbage=4, deflate=True, no_new_id=True)


def pdf_to_png(pdf_path, png_path, dpi):
    import pymupdf
    with pymupdf.open(str(pdf_path)) as doc:
        pix = doc[0].get_pixmap(dpi=dpi, alpha=False)
        pix.save(str(png_path))


def build_all(root, cvd=True, log=print):
    """Write figures/out/rdkit/<name>.svg/.pdf/.png (+ CVD simulations); return manifest records."""
    import hashlib
    od = out_dir(root)
    od.mkdir(parents=True, exist_ok=True)
    dpi = int(style.applied(root)["raster_dpi"]["value"])
    records = {}
    for name, e in table(root).items():
        if e.get("standalone", True) is False:
            continue
        text = svg(name, root)
        sv, pdf, png = od / (name + ".svg"), od / (name + ".pdf"), od / (name + ".png")
        sv.write_text(text)
        svg_to_pdf(text, pdf)
        pdf_to_png(pdf, png, dpi)
        outs = [sv, pdf, png]
        if cvd:
            from nacre.figs import cvd as cvdmod
            cdir = od / "cvd"
            cdir.mkdir(exist_ok=True)
            outs += cvdmod.simulate_png(png, cdir, name, dpi)
        smi, prov = smiles(name, root)
        records[name] = {"smiles": smi, "source": prov, "derive": table(root)[name].get("derive"),
                         "font": style.font_record(root),
                         "outputs": {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                     for p in outs}}
        log("rdkit %s: ok" % name)
    return records
